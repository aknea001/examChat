from fastapi import FastAPI, Response
from pydantic import BaseModel
import mysql.connector
import jwt
import os
from dotenv import load_dotenv
from argon2 import PasswordHasher, exceptions

load_dotenv()

sqlConfig = {
    "host": os.getenv("sqlHost"),
    "user": os.getenv("sqlUser"),
    "password": os.getenv("sqlPasswd"),
    "database": os.getenv("sqlDB")
}

a2 = PasswordHasher()

app = FastAPI()

class Credentials(BaseModel):
    username: str
    passwd: str

def createJWT(data) -> str:
    encodedJWT = jwt.encode({"userID": data}, os.getenv("jwtKey"), algorithm="HS256")
    return encodedJWT

@app.post("/register", status_code=201)
async def register(body: Credentials, respone: Response):
    hashed = a2.hash(body.passwd)
    try:
        db = mysql.connector.connect(**sqlConfig)
        cursor = db.cursor()

        query = "INSERT INTO users (username, hash) \
                VALUES \
                (%s, %s)"
        
        cursor.execute(query, (body.username, hashed))
        db.commit()
    except mysql.connector.Error as e:
        respone.status_code = 500
        return {"msg": f"Error connecting to database: {str(e)}"}
    finally:
        if "db" in locals() and db.is_connected():
            cursor.close()
            db.close()
        
    return {"msg": "Success"}

@app.post("/login", status_code=200)
async def login(body: Credentials, response: Response):
    try:
        db = mysql.connector.connect(**sqlConfig)
        cursor = db.cursor()

        query = "SELECT hash, id FROM users WHERE username = %s"

        cursor.execute(query, (body.username, ))
        data = cursor.fetchone()
    except mysql.connector.Error as e:
        response.status_code = 500
        return {"msg": f"Error connecting to database: {str(e)}"}
    finally:
        if "db" in locals() and db.is_connected():
            cursor.close()
            db.close()

    if not data:
        response.status_code = 401
        return {"msg": "Username doesnt exist.."}
    
    try:
        a2.verify(data[0], body.passwd)
    except exceptions.VerifyMismatchError:
        response.status_code = 401
        return {"msg": "Incorrect username or password.."}
    
    encodedJWT = createJWT(data[1])
    return {"msg": "Success", "jwt": encodedJWT}
    