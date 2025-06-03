from fastapi import FastAPI, Response, Depends, Request, Header
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Annotated
from contextlib import asynccontextmanager
import jwt
from datetime import timedelta, datetime
from dotenv import load_dotenv
from os import getenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from databaseConnection import Database

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = Database()
    yield

a2 = PasswordHasher()

app = FastAPI(lifespan=lifespan)

oauth2Scheme = OAuth2PasswordBearer(tokenUrl="login")

class Credentials(BaseModel):
    username: str
    passwd: str

class Message(BaseModel):
    msg: str
    groupID: str

class Group(BaseModel):
    users: str
    groupName: str

def createJWT(data) -> str:
    encodedJWT = jwt.encode({"userID": data, "exp": datetime.now() + timedelta(hours=1)}, getenv("jwtKey"), algorithm="HS256")
    return encodedJWT

def decodeJWT(token) -> str | bool:
    try:
        payload = jwt.decode(token, getenv("jwtKey"), algorithms=["HS256"], require=["exp"], verify_exp=True)
        identity = payload.get("userID")
    except jwt.exceptions.InvalidTokenError:
        return False
    
    return identity

def groupMembers(db, groupID: str, userID: str = None):
    query = "SELECT userID FROM groupMembers WHERE groupID = %s"
    values = [groupID]

    if userID:
        query += " AND userID = %s"
        values.append(userID)
    
    data = db.execute(query, *values)

    return data

def tranUID(db, userID: str) -> str:
    query = "SELECT username FROM users WHERE id = %s"

    data = db.execute(query, userID)
    
    return data["username"]

@app.post("/register", status_code=201)
async def register(response: Response, request: Request, body: Credentials):
    db = request.app.state.db

    hashed = a2.hash(body.passwd)
    query = "INSERT INTO users (username, hash) \
            VALUES \
            (%s, %s)"
    
    try:
        db.execute(query, body.username, hashed)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return {"msg": "Success"}

@app.post("/login", status_code=200)
async def login(response: Response, request: Request, body: Credentials):
    db = request.app.state.db

    query = "SELECT hash, id FROM users WHERE username = %s"

    try:
        data = db.execute(query, body.username)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    if not data:
        response.status_code = 401
        return {"msg": "Incorrect username or password.."}
    
    try:
        a2.verify(data["hash"], body.passwd)
    except VerifyMismatchError:
        response.status_code = 401
        return {"msg": "Incorrect username or password.."}
    
    encodedJWT = createJWT(str(data["id"]))
    return {"msg": "Success", "jwt": encodedJWT}

@app.get("/message/get", status_code=200)
async def getMessage(response: Response, request: Request, token: Annotated[str, Depends(oauth2Scheme)], groupID: str = Header()):
    db = request.app.state.db

    if groupID != "1":
        identity = decodeJWT(token)
    
        if not identity:
            response.status_code = 401
            return {"msg": "Invalid token"}
        
        try:
            if not groupMembers(db, groupID, identity):
                response.status_code = 403
                return {"msg": "Not authorized"}
        except ConnectionError as e:
            response.status_code = 500
            return {"msg": str(e)}

    query = "SELECT chats.msg, users.username FROM chats \
            LEFT JOIN users ON chats.userID = users.id \
            WHERE groupID = %s"
    
    try:
        data = db.execute(query, groupID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return data
    
@app.post("/message/new", status_code=201)
async def newMessage(response: Response, request: Request, token: Annotated[str, Depends(oauth2Scheme)], body: Message):
    db = request.app.state.db
    identity = decodeJWT(token)

    if not identity:
        response.status_code = 401
        return {"msg": "Invalid token"}
    
    try:
        if body.groupID != "1" and not groupMembers(db, body.groupID, identity):
            response.status_code = 403
            return {"msg": "Not authorized"}
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    query = "INSERT INTO chats (msg, userID, groupID) \
            VALUES \
            (%s, %s, %s)"
    
    try:
        db.execute(query, body.msg, str(identity), body.groupID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return {"msg": "Success"}

@app.get("/groups/members", status_code=200)
async def getGroupMembers(response: Response, request: Request, groupID: str = Header()):
    db = request.app.state.db

    try:
        members = groupMembers(db, groupID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return members

@app.post("/groups/new", status_code=201)
async def newGroup(response: Response, request: Request, token: Annotated[str, Depends(oauth2Scheme)], body: Group):
    db = request.app.state.db
    identity = decodeJWT(token)

    if not identity:
        response.status_code = 401
        return {"msg": "Invalid token"}
    
    try:
        query = "INSERT INTO chatGroups (name) \
                    VALUES \
                    (%s)"
        
        newGroupID = db.execute(query, body.groupName)

        values = []

        query = "INSERT INTO groupMembers (userID, groupID) \
                VALUES"
        
        query += " (%s, %s),"
        values.extend([identity, newGroupID])

        userLst = body.users.split(",")
        
        for user in userLst:
            query += " (%s, %s),"
            values.extend([user, newGroupID])
        
        query = query[:-1]
        
        db.execute(query, *values)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return {"msg": "Success"}

@app.get("/users/tranuID", status_code=200)
async def getTranuID(response: Response, request: Request, userID: str = Header()):
    db = request.app.state.db

    try:
        username = tranUID(db, userID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}
    
    return {"username": username}

if __name__ == "__main__":
    print(tranUID(4))