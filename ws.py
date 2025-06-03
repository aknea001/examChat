from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form, Query
import requests
from secrets import token_urlsafe

from api import decodeJWT

app = FastAPI()

apiBaseURL = "http://localhost:3000"

clients = {}

@app.websocket("/ws")
async def wsEndpoint(websocket: WebSocket, token: str = Query(), groupID: str = Query()):
    await websocket.accept()
    identity = str(decodeJWT(token))
    
    if groupID == "1":
        while True:
            uID = f"global_{token_urlsafe(12)}"

            if uID not in clients:
                break
    else:
        if not identity:
            try:
                await websocket.send_json({"event": "redirect", "location": "/logout?redirect=loginPage"})
                raise WebSocketDisconnect
            except WebSocketDisconnect:
                return
        else:
            uID = f"user_{identity}_{groupID}"

    clients[uID] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            res = requests.post(f"{apiBaseURL}/message/new", headers={"Authorization": f"Bearer {token}"}, json={"msg": str(data), "groupID": groupID})
            
            if res.status_code != 201:
                print(f"{res.status_code}: {res.json()}")
                if res.status_code == 403:
                    location = "/"
                else:
                    location = "/logout?redirect=loginPage"
                
                await websocket.send_json({"event": "redirect", "location": location})
                raise WebSocketDisconnect
            
            res = requests.get(f"{apiBaseURL}/users/tranuID", headers={"userID": identity})
            username = res.json()["username"]

            if groupID == "1":
                for client in clients:
                    if client.startswith("global_"):
                        await clients[client].send_json({"event": "newMessage", "msg": str(data), "username": username})
                
                continue

            res = requests.get(f"{apiBaseURL}/groups/members", headers={"groupID": groupID})
            members = res.json()

            avaliableClients = []

            for i in members:
                avaliableClients.append(f"user_{i["userID"]}_{groupID}")

            for client in avaliableClients:
                if client in clients:
                    await clients[client].send_json({"event": "newMessage", "msg": str(data), "username": username})
    except WebSocketDisconnect:
        del clients[uID]