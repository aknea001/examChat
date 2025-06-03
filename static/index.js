let ws = null

function establishConnection(token, groupID) {
    const chats = document.getElementById("chats")

    if (chats.childElementCount != 0) {
        chats.lastElementChild.scrollIntoView({ behavior: "instant" })
    }

    ws = new WebSocket(`wss://examchat.keali.org/ws?token=${token}&groupID=${groupID}`)

    ws.addEventListener("open", () => {
        console.log("connected to ws..")
    })

    ws.addEventListener("message", ({ data }) => {
        data = JSON.parse(data)
        
        if (data.event == "newMessage") {
            printMessage(data.msg, data.username)
            return
        }

        if (data.event == "redirect") {
            window.location = data.location
            return
        }
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

function printMessage(msg, user) {
    const chats = document.getElementById("chats")

    const newChat = document.createElement("li")
    newChat.innerHTML = `<b>${user}</b><br>${msg}`

    chats.appendChild(newChat)
    newChat.scrollIntoView({ behavior: "instant" })
}

const dialog = document.getElementById("newGroupDialog")

function dontClose(e) {
    e.stopPropagation()
}