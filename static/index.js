function sendMessage(e) {
    e.preventDefault()

    const msg = document.getElementById("messageInput").value
    console.log(`Sent message ${msg}..`)
}

document.getElementById("messageForm").addEventListener("submit", (e) => {
    e.preventDefault()

    const msg = document.getElementById("messageInput").value
    console.log(`Sent message ${msg}..`)
})