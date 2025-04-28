let ws = null

function establishConnection() {
    ws = new WebSocket("ws://localhost:8000/ws")

    ws.addEventListener("open", () => {
        console.log("connected to ws..")
    })

    ws.addEventListener("message", ({ data }) => {
        printMessage(data)
    })
}

document.getElementById("messageForm").addEventListener("submit", (e) => {
    e.preventDefault()

    const msgField = document.getElementById("messageInput")
    const msg = msgField.value
    console.log(`Sent message ${msg}..`)
    msgField.value = null

    if (ws != null) {
        ws.send(String(msg))
    } else {
        alert("error connecting to websocket, please refresh page and try again")
    }
})

function printMessage(msg) {
    const chats = document.getElementById("chats")

    const newChat = document.createElement("li")
    newChat.innerHTML = msg

    chats.appendChild(newChat)
}