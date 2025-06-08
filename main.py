from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import requests
import os
from dotenv import load_dotenv
from secrets import token_urlsafe

from api import decodeJWT

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("sessionKey"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

apiBaseURL = "http://localhost:3000"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    jwt = request.session.get("jwt", "")
    groupID = "1"

    res = requests.get(f"{apiBaseURL}/message/get", headers={"Authorization": f"Bearer {jwt}", "groupID": groupID})

    if res.status_code != 200:
        error = f"{res.status_code}: {res.json()["msg"]}"
        return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "error": error})
    
    msgs = res.json()

    if not jwt:
        return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "msgs": msgs})

    res = requests.get(f"{apiBaseURL}/groups/user", headers={"Authorization": f"Bearer {jwt}"})

    if res.status_code != 200:
        error = f"{res.status_code}: {res.json()['msg']}"
        return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "error": error})
    
    groups = res.json()

    return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "msgs": msgs, "groups": groups})

@app.post("/group/new")
async def newGroup(request: Request, groupName: str = Form(), members: list = Form([]), genLink: bool = Form(False)):
    jwt = request.session.get("jwt", "")

    res = requests.post(f"{apiBaseURL}/groups/new", headers={"Authorization": f"Bearer {jwt}"}, json={"groupName": groupName, "members": members})

    if res.status_code != 201:
        pass # ADD ERROR HANDLING PLEASE :(

    newGroupID = res.json()["groupID"]

    if not genLink:
        return RedirectResponse(f"/group/{newGroupID}", status_code=303)
    
    res = requests.post(f"{apiBaseURL}/groups/join/generate", headers={"Authorization": f"Bearer {jwt}"}, json={"groupName": groupName, "groupID": str(newGroupID)})

    if res.status_code != 201:
        return {"status": res.status_code, "msg": res.json()} # i dont feel like doin proper error handling 🥸

    joinCode = res.json()["joinCode"]

    return RedirectResponse(f"/group/{newGroupID}?joinCode={joinCode}", status_code=303)

@app.get("/group/join")
async def joinGroup(request: Request, joinCode: str = Query(None)):
    if not joinCode:
        return RedirectResponse(request.url_for("index"), status_code=303)
    
    jwt = request.session.get("jwt", None)

    if not jwt:
        return RedirectResponse(f"/login?redirect=/group/join?joinCode={joinCode}", status_code=303)
    
    res = requests.post(f"{apiBaseURL}/groups/join", headers={"Authorization": f"Bearer {jwt}"}, json={"joinCode": joinCode})

    if res.status_code == 401:
        return RedirectResponse(request.url_for("loginPage", redirect=f"/group/join?joinCode={joinCode}"), status_code=303)
    elif res.status_code == 403:
        # Add better error handling, maybe a sep html page
        return "Invalid Join Code"
    
    return RedirectResponse(f"/group/{res.json()["groupID"]}", status_code=303)

@app.get("/group/{groupID}", response_class=HTMLResponse)
async def chatGroups(groupID: str, request: Request, joinCode: str = Query("")):
    if groupID == "1":
        return RedirectResponse(request.url_for("index"), status_code=303)

    jwt = request.session.get("jwt", "")

    res = requests.get(f"{apiBaseURL}/message/get", headers={"Authorization": f"Bearer {jwt}", "groupID": groupID})

    if res.status_code != 200:
        error = f"{res.status_code}: {res.json()['msg']}"
        return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "error": error})
    
    msgs = res.json()
    
    res = requests.get(f"{apiBaseURL}/groups/user", headers={"Authorization": f"Bearer {jwt}"})

    if res.status_code != 200:
        error = f"{res.status_code}: {res.json()['msg']}"
        return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "error": error})
    
    groups = res.json()

    return templates.TemplateResponse("index.html", {"request": request, "jwt": jwt, "groupID": groupID, "msgs": msgs, "groups": groups, "joinCode": joinCode})

@app.get("/login", response_class=HTMLResponse)
async def loginPage(request: Request, redirect: str = Query("/")):
    error = request.session.pop("error", "")
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "redirect": redirect})

@app.post("/login")
async def login(request: Request, username: str = Form(), passwd: str = Form(), redirect: str = Query("/")):
    res = requests.post(f"{apiBaseURL}/login", json={"username": username, "passwd": passwd})

    if res.status_code != 200:
        request.session["error"] = f"{res.status_code}: {res.json()['msg']}"
        return RedirectResponse(request.url_for("loginPage", redirect=redirect), status_code=303)
    
    request.session["jwt"] = res.json()["jwt"]
    return RedirectResponse(redirect, status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("jwt", "")
    redirect = request.query_params.get("redirect", "")
    return RedirectResponse(request.url_for(redirect or "index"), status_code=303)

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