from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("sessionKey"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

apiBaseURL = "http://localhost:3000"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    jwt = request.session.get("jwt", "")

    res = requests.get(f"{apiBaseURL}/message/get", headers={"groupID": "1"}) #hard coding for global chat for now CHANGE AFTER CHATS IMPLEMENTED

    if res.status_code != 200:
        error = f"{res.status_code}: {res.json()}"
        return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "error": error})
    
    msgs = res.json()

    return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "msgs": msgs})

@app.get("/login", response_class=HTMLResponse)
async def loginPage(request: Request):
    error = request.session.pop("error", "")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def login(request: Request, username: str = Form(), passwd: str = Form()):
    res = requests.post(f"{apiBaseURL}/login", json={"username": username, "passwd": passwd})

    if res.status_code != 200:
        request.session["error"] = f"{res.status_code}: {res.json()['msg']}"
        return RedirectResponse(request.url_for("loginPage"), status_code=303)
    
    request.session["jwt"] = res.json()["jwt"]
    return RedirectResponse(request.url_for("index"), status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("jwt", "")
    return RedirectResponse(request.url_for("index"), status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def registerPage(request: Request):
    error = request.session.pop("error", "")
    return templates.TemplateResponse("register.html", {"request": request, "error": error})

@app.post("/register")
async def register(request: Request, username: str = Form(), passwd: str = Form()):
    #print(f"{username}: {passwd}")
    res = requests.post(f"{apiBaseURL}/register", json={"username": username, "passwd": passwd})

    if res.status_code != 201:
        request.session["error"] = f"Error connecting to server.. \nPlease try again later \n{res.status_code}: {res.json()['msg']}"
        return RedirectResponse(request.url_for("registerPage"), status_code=303)
    
    return RedirectResponse(request.url_for("index"), status_code=303)

clients = set()

@app.websocket("/ws")
async def wsEndpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            print(websocket.query_params.get("token", ""))
            res = requests.post(f"{apiBaseURL}/message/new", headers={"Authorization": f"Bearer {websocket.query_params.get('token', '')}"}, json={"msg": str(data), "groupID": "1"}) #AGAIN HARD CODING FOR GLOBAL CHAT CHANGE
            
            if res.status_code != 201:
                print(f"{res.status_code}: {res.json()}")
                continue

            for client in clients:
                await client.send_text(str(data))
    except WebSocketDisconnect:
        clients.remove(websocket)
