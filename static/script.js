
const chatArea = document.getElementById("chatArea");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");

let conversationId = null;
let busy = false;

let visitorId = localStorage.getItem("arzab_visitor_id");

if (!visitorId) {
    visitorId = crypto.randomUUID();
    localStorage.setItem("arzab_visitor_id", visitorId);
}

function addMessage(role, text) {
    const row = document.createElement("div");
    row.className = "message " + role;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "U" : "A";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    row.appendChild(avatar);
    row.appendChild(content);
    messages.appendChild(row);

    chatArea.scrollTop = chatArea.scrollHeight;
}

async function sendMessage() {
    const message = input.value.trim();

    if (!message || busy) return;

    busy = true;
    sendButton.disabled = true;

    welcome.style.display = "none";
    addMessage("user", message);

    input.value = "";
    input.style.height = "auto";

    const typing = document.createElement("div");
    typing.className = "typing";
    typing.textContent = "ARZAB AI is thinking...";
    messages.appendChild(typing);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                visitor_id: visitorId,
                conversation_id: conversationId
            })
        });

        let data = {};

        try {
            data = await response.json();
        } catch (e) {
            data = {};
        }

        typing.remove();

        if (!response.ok) {
            throw new Error(data.error || "Server error (" + response.status + ")");
        }

        conversationId = data.conversation_id;
        addMessage("assistant", data.reply);

    } catch (error) {
        typing.remove();
        addMessage("assistant", "Sorry, I couldn't respond. " + (error.message || "Please try again."));
        console.error(error);
    }

    busy = false;
    sendButton.disabled = false;
    input.focus();
}

sendButton.addEventListener("click", sendMessage);

input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 130) + "px";
});

document.querySelectorAll("[data-prompt]").forEach(button => {
    button.addEventListener("click", () => {
        input.value = button.dataset.prompt;
        sendMessage();
    });
});

document.getElementById("newChat").addEventListener("click", () => {
    conversationId = null;
    messages.innerHTML = "";
    welcome.style.display = "flex";
    input.value = "";
    input.focus();
});
