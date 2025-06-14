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
import redis
from secrets import token_hex
from databaseConnection import Database

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = Database()
    app.state.redisConn = redis.Redis(host=getenv("redisHost"), port=getenv("redisPort"), db=0)
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
    members: list
    groupName: str

class JoinGroup(BaseModel):
    joinCode: str

class GenerateJoinCode(BaseModel):
    groupName: str
    groupID: str

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
    
    return data[0]["username"]

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
        a2.verify(data[0]["hash"], body.passwd)
    except VerifyMismatchError:
        response.status_code = 401
        return {"msg": "Incorrect username or password.."}
    
    encodedJWT = createJWT(str(data[0]["id"]))
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

@app.get("/groups/user", status_code=200)
async def getGroupsbyUser(response: Response, request: Request, token: Annotated[str, Depends(oauth2Scheme)]):
    db = request.app.state.db
    identity = decodeJWT(token)

    if not identity:
        response.status_code = 401
        return {"msg": "Invalid token"}
    
    try:
        query = "SELECT \
                chatGroups.id, \
                chatGroups.name \
                FROM chatGroups \
                LEFT JOIN groupMembers ON \
                chatGroups.id = groupMembers.groupID \
                WHERE userID = %s"
        
        data = db.execute(query, identity)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return data

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

        values = [newGroupID, identity]

        if not body.members:
            query = "INSERT INTO groupMembers (groupID, userID) \
                    VALUES \
                    (%s, %s)"
        else:
            query = "INSERT INTO groupMembers (userID, groupID) \
                    SELECT id, %s \
                    FROM ( \
                    SELECT %s AS id \
                    UNION ALL \
                    SELECT id FROM users WHERE username IN ("
            
            for member in body.members:
                if member.strip() == "":
                    continue

                query += "%s,"
                values.extend([member])
            
            query = query[:-1] + ")) AS allUsers"
        
        db.execute(query, *values)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}

    return {"msg": "Success", "groupID": newGroupID}

@app.post("/groups/join", status_code=201)
async def joinGroup(request: Request, response: Response, token: Annotated[str, Depends(oauth2Scheme)], body: JoinGroup):
    db = request.app.state.db
    r = request.app.state.redisConn

    identity = decodeJWT(token)

    if not identity:
        response.status_code = 401
        return {"msg": "Invalid token"}

    if not r.exists(body.joinCode):
        response.status_code = 403
        return {"msg": "Invalid code"}
    
    groupID = r.get(body.joinCode)

    query = "INSERT INTO groupMembers (userID, groupID) \
            VALUES \
            (%s, %s)"
    
    try:
        db.execute(query, identity, groupID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}
    
    return {"msg": "Success", "groupID": groupID}

@app.post("/groups/join/generate", status_code=201)
async def generateJoinCode(request: Request, response: Response, token: Annotated[str, Depends(oauth2Scheme)], body: GenerateJoinCode):
    db = request.app.state.db
    r = request.app.state.redisConn

    identity = decodeJWT(token)

    if not identity:
        response.status_code = 401
        return {"msg": "Invalid token"}
    
    query = "SELECT id FROM groupMembers WHERE userID = %s AND groupID = %s"

    try:
        data = db.execute(query, identity, body.groupID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}
    
    if not data:
        response.status_code = 403
        return {"msg": "Not authorized"}
    
    groupName = body.groupName.replace(" ", "-")
    newJoinCode = f"{groupName}_{token_hex(16)}"

    while True:
        if r.exists(newJoinCode):
            newJoinCode = f"{groupName}_{token_hex(16)}"
            continue

        break

    r.set(newJoinCode, body.groupID, ex=3600)

    return {"msg": "Success", "joinCode": newJoinCode}

@app.get("/users/tranuID", status_code=200)
async def getTranuID(response: Response, request: Request, userID: str = Header()):
    db = request.app.state.db

    try:
        username = tranUID(db, userID)
    except ConnectionError as e:
        response.status_code = 500
        return {"msg": str(e)}
    
    return {"username": username}