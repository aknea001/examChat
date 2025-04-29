const registerForm = document.getElementById("registerForm")

registerForm.addEventListener("submit", (e) => {
    e.preventDefault()

    const passwd = document.getElementById("passwd").value
    const passwdVerify = document.getElementById("passwdVerify").value

    if (passwd != passwdVerify) {
        document.getElementById("error").innerHTML = "Passwords not matching.."
        return
    }

    registerForm.submit()
})