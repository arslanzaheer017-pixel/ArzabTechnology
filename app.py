from flask import Flask, request, jsonify, render_template
from groq import (
    Groq,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APIStatusError,
)
from dotenv import load_dotenv
import sqlite3
import os
import time
import uuid
from collections import defaultdict, deque

# Is file ka folder (Arzab). .env aur database hamesha yahin se load honge,
# chahe server kisi bhi folder se chalaya jaye.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__)

# ---------------- Groq configuration ----------------
api_key = (os.getenv("GROQ_API_KEY") or "").strip().strip('"').strip("'")

if not api_key:
    raise ValueError("GROQ_API_KEY missing in .env file")

client = Groq(api_key=api_key)

# Pehli pasand .env se (GROQ_MODEL=...). Agar wo available na ho
# to app khud Groq ki list se chalne wala chat model chun leti hai.
current_model = (os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant").strip()

# Ye models chat ke liye nahi hote, inhe skip karna hai
SKIP_WORDS = ("whisper", "tts", "guard", "safeguard", "orpheus", "playai", "embed")

# Behtar models ko pehle rakhne ki tarteeb
PREFERRED = ("llama-3.3-70b", "gpt-oss-120b", "llama-3.1-8b", "gpt-oss-20b", "llama", "qwen")

DB_NAME = os.path.join(BASE_DIR, "database.db")

SYSTEM_PROMPT = (
    "You are ARZAB AI, the official AI assistant of ARZAB TECHNOLOGIES. "
    "Be friendly, intelligent, helpful and professional. Give clear, accurate answers. "
    "Reply in the language the visitor writes in (English, Urdu, Roman Urdu, etc.). "
    "You can help with general questions, technology, education, writing and ideas.\n\n"
    "About ARZAB TECHNOLOGIES (only use these facts): it is an independent, "
    "product-focused technology company. Tagline: 'Ideas Into Innovation.' "
    "Mission: transforming ambitious ideas into powerful digital experiences. "
    "Vision: making technology smarter, simpler and more accessible. "
    "Product family: ARZAB Chat (AI chatbot), ARZAB Agents (AI agents for multi-step tasks), "
    "ARZAB Files (file organizer), ARZAB Tasks, ARZAB Docs, ARZAB Flow and ARZAB Apps "
    "(web and mobile applications). Visitors can use the contact form on the website "
    "to ask questions or request early access.\n\n"
    "Rules: never invent company history, achievements, clients, prices, launch dates, "
    "features or contact details. If you do not know something about ARZAB, say so "
    "and suggest the contact form on the website."
)


def pick_available_model():
    """Groq se available chat models ki list lekar sabse behtar chun leta hai."""
    ids = [m.id for m in client.models.list().data]
    print("ARZAB AI: available models ->", ids)

    chat_models = [i for i in ids if not any(w in i.lower() for w in SKIP_WORDS)]

    for word in PREFERRED:
        for model_id in chat_models:
            if word in model_id.lower():
                return model_id

    if chat_models:
        return chat_models[0]

    raise RuntimeError("Is API key par koi chat model available nahi hai.")


def is_model_problem(error):
    text = str(error).lower()
    return "model" in text and (
        "not exist" in text
        or "not_found" in text
        or "decommissioned" in text
        or "no access" in text
        or "do not have access" in text
    )


def ask_ai(ai_messages):
    """AI se jawab leta hai. Model na mile to dusra model chun kar dobara try karta hai."""
    global current_model

    def call(model_name):
        return client.chat.completions.create(
            model=model_name,
            messages=ai_messages,
            temperature=0.7,
            max_tokens=1024
        )

    try:
        return call(current_model).choices[0].message.content

    except APIStatusError as e:
        if not is_model_problem(e):
            raise

        print(f"ARZAB AI: model '{current_model}' nahi chala, naya dhoond raha hoon...")
        new_model = pick_available_model()

        if new_model == current_model:
            raise

        current_model = new_model
        print(f"ARZAB AI: ab ye model use ho raha hai -> {current_model}")

        return call(current_model).choices[0].message.content


# ---------------- Spam / quota protection ----------------
# Website public hone par koi bhi tumhari Groq quota khatam kar sakta hai.
# Isliye har visitor (IP) ko 1 minute mein sirf itne messages ki ijazat hai.
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "15"))
_hits = defaultdict(deque)


def too_many_requests():
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() or request.remote_addr or "unknown"
    now = time.time()
    q = _hits[ip]

    while q and now - q[0] > 60:
        q.popleft()

    if len(q) >= RATE_LIMIT:
        return True

    q.append(now)

    # memory saaf rakho
    if len(_hits) > 5000:
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > 60]:
            _hits.pop(k, None)

    return False


# ---------------- Database ----------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                visitor_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
            )
        """)


init_db()


# ---------------- Routes ----------------
@app.route("/")
def home():
    # ARZAB TECHNOLOGIES website (isme "Chat with agent" button hai)
    return render_template("home.html")


@app.route("/assistant")
def assistant():
    # Full-screen ARZAB AI chat page
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/chat", methods=["POST"])
def chat():

    if too_many_requests():
        return jsonify({
            "error": "Bohat zyada messages. Thori der baad try karo."
        }), 429

    try:
        data = request.get_json(silent=True) or {}

        raw_message = data.get("message")
        raw_visitor_id = data.get("visitor_id")
        raw_conversation_id = data.get("conversation_id")

        message = raw_message.strip() if isinstance(raw_message, str) else ""
        visitor_id = raw_visitor_id.strip() if isinstance(raw_visitor_id, str) else ""
        conversation_id = (
            raw_conversation_id.strip()
            if isinstance(raw_conversation_id, str)
            else ""
        )

        if not message:
            return jsonify({"error": "Please enter a message."}), 400

        if len(message) > 4000:
            return jsonify({"error": "Message is too long."}), 400

        if not visitor_id or len(visitor_id) > 100:
            return jsonify({"error": "Invalid visitor ID."}), 400

        # Pehle sirf padhna: conversation check + history
        history = []
        is_new_conversation = False

        with sqlite3.connect(DB_NAME) as conn:

            if conversation_id:

                existing = conn.execute(
                    """
                    SELECT id
                    FROM conversations
                    WHERE id = ? AND visitor_id = ?
                    """,
                    (conversation_id, visitor_id)
                ).fetchone()

                if not existing:
                    return jsonify({"error": "Invalid conversation."}), 404

                history = conn.execute(
                    """
                    SELECT role, content
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC
                    LIMIT 12
                    """,
                    (conversation_id,)
                ).fetchall()

                history.reverse()

            else:
                conversation_id = str(uuid.uuid4())
                is_new_conversation = True

        ai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        ai_messages.extend(
            {"role": role, "content": content}
            for role, content in history
        )

        ai_messages.append({"role": "user", "content": message})

        answer = ask_ai(ai_messages)

        # Jawab aa jaye tabhi database mein save karo
        with sqlite3.connect(DB_NAME) as conn:

            if is_new_conversation:
                conn.execute(
                    "INSERT INTO conversations (id, visitor_id) VALUES (?, ?)",
                    (conversation_id, visitor_id)
                )

            conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "user", message)
            )

            conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "assistant", answer)
            )

        return jsonify({
            "reply": answer,
            "conversation_id": conversation_id
        })

    except AuthenticationError as e:
        print("ARZAB AI ERROR (API key):", repr(e))
        return jsonify({
            "error": "API key galat ya expire hai. .env mein GROQ_API_KEY check karo."
        }), 401

    except RateLimitError as e:
        print("ARZAB AI ERROR (rate limit):", repr(e))
        return jsonify({
            "error": "Groq ki limit khatam ho gayi hai. Thori der baad try karo."
        }), 429

    except APIConnectionError as e:
        print("ARZAB AI ERROR (network):", repr(e))
        return jsonify({
            "error": "Groq se connect nahi ho paya. Internet check karo."
        }), 503

    except Exception as e:
        print("ARZAB AI ERROR:", repr(e))
        return jsonify({
            "error": "ARZAB AI temporarily unavailable. Terminal mein error dekho."
        }), 500


if __name__ == "__main__":

    # Sirf apne computer par testing ke liye. Online hosting isay use nahi karti.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "1") == "1"
    )
