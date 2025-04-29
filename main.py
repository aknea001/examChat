from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def loginPage(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def registerPage(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(), passwd: str = Form()):
    print(f"{username}: {passwd}")
    return RedirectResponse(request.url_for("index"), status_code=303)

clients = set()

@app.websocket("/ws")
async def wsEndpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            for client in clients:
                await client.send_text(str(data))
    except WebSocketDisconnect:
        clients.remove(websocket)