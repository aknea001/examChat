const dialog = document.getElementById("newGroupDialog")

function dontClose(e) {
    e.stopPropagation()
}

function newMember(e, divElement) {
    if (!e.target.classList.contains('memberAddInput') || e.key !== 'Enter') {
        return
    }

    e.preventDefault()

    const inputValue = e.target.value.trim()
    if (inputValue === '') return

    const membersDiv = document.getElementById("members")

    const newMember = document.createElement('div')
    newMember.classList.add("member")

    const memberName = document.createElement("input")
    memberName.type = 'text'
    memberName.name = 'members'
    memberName.value = inputValue
    memberName.readOnly = true

    const deleteMember = document.createElement("button")
    deleteMember.innerHTML = "<svg viewBox='0 0 24 24' class='icon'><path d='M18 6L6 18M6 6l12 12' /></svg>"
    deleteMember.type = "button"
    
    newMember.appendChild(memberName)
    newMember.appendChild(deleteMember)

    membersDiv.appendChild(newMember)

    const addMembersBtn = document.createElement("button")
    addMembersBtn.setAttribute("onclick", "changeToInput(this)")
    addMembersBtn.type = "button"
    addMembersBtn.innerHTML = "Add Member"

    divElement.replaceWith(addMembersBtn)
};

function changeToInput(el) {
    const memberAddDiv = document.createElement("div")
    const memberAddInput = document.createElement("input")

    memberAddDiv.setAttribute("onkeydown", "newMember(event, this)")

    memberAddInput.type = "text"
    memberAddInput.placeholder = "Member Username"
    memberAddInput.classList.add("memberAddInput")

    memberAddDiv.appendChild(memberAddInput)

    el.replaceWith(memberAddDiv)
    memberAddInput.focus()
}