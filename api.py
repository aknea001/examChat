from fastapi import FastAPI, Response, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Annotated
import mysql.connector
import jwt
from datetime import timedelta, datetime
import os
from dotenv import load_dotenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

load_dotenv()

sqlConfig = {
    "host": os.getenv("sqlHost"),
    "user": os.getenv("sqlUser"),
    "password": os.getenv("sqlPasswd"),
    "database": os.getenv("sqlDB")
}

a2 = PasswordHasher()

app = FastAPI()

oauth2Scheme = OAuth2PasswordBearer(tokenUrl="login")

class Credentials(BaseModel):
    username: str
    passwd: str

class Message(BaseModel):
    msg: str
    groupID: int

def createJWT(data) -> str:
    encodedJWT = jwt.encode({"userID": data, "exp": datetime.now() + timedelta(hours=1)}, os.getenv("jwtKey"), algorithm="HS256")
    return encodedJWT

def decodeJWT(token):
    try:
        payload = jwt.decode(token, os.getenv("jwtKey"), algorithms=["HS256"], require=["exp"], verify_exp=True)
        identity = payload.get("userID")
    except jwt.exceptions.InvalidTokenError:
        return False
    
    return identity

@app.post("/register", status_code=201)
async def register(response: Response, body: Credentials):
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
        response.status_code = 500
        return {"msg": f"Error connecting to database: {str(e)}"}
    finally:
        if "db" in locals() and db.is_connected():
            cursor.close()
            db.close()
        
    return {"msg": "Success"}

@app.post("/login", status_code=200)
async def login(response: Response, body: Credentials):
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
    except VerifyMismatchError:
        response.status_code = 401
        return {"msg": "Incorrect username or password.."}
    
    encodedJWT = createJWT(data[1])
    return {"msg": "Success", "jwt": encodedJWT}

@app.get("/message/get", status_code=200)
async def getMessage(request: Request, response: Response):
    if "groupID" not in request.headers:
        response.status_code = 400
        return {"msg": "Request missing headers"}
    
    try:
        db = mysql.connector.connect(**sqlConfig)
        cursor = db.cursor()

        query = "SELECT msg, userID FROM chats WHERE groupID = %s"
        cursor.execute(query, (request.headers["groupID"], ))

        data = cursor.fetchall()
    except mysql.connector.Error as e:
        response.status_code = 500
        return {"msg": f"Error connecting to database: {str(e)}"}
    finally:
        if "db" in locals() and db.is_connected():
            cursor.close()
            db.close()

    return data
    
# 403 IF USER DOESNT HAVE ACCESS TO PARTICIAL CHAT GROUP..
@app.post("/message/new", status_code=201)
async def newMessage(response: Response, token: Annotated[str, Depends(oauth2Scheme)], body: Message):
    identity = decodeJWT(token)

    if not identity:
        response.status_code = 401
        return {"msg": "Invalid token"}
    
    if body.groupID != 1:
        pass #check if authorised ( ´･･)ﾉ(._.`)

    try:
        db = mysql.connector.connect(**sqlConfig)
        cursor = db.cursor()

        query = "INSERT INTO chats (msg, userID, groupID) \
                VALUES \
                (%s, %s, %s)"
        
        cursor.execute(query, (body.msg, str(identity), body.groupID))
        db.commit()
    except mysql.connector.Error as e:
        response.status_code = 500
        return {"msg": f"Error connecting to database: {str(e)}"}
    finally:
        if "db" in locals() and db.is_connected():
            cursor.close()
            db.close()

    return {"msg": "Success"}