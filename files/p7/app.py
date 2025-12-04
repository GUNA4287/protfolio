from flask import Flask, request, jsonify, render_template, session, redirect, flash
from flask_cors import CORS
from openai import OpenAI
import sqlite3
import os
from dotenv import load_dotenv  # ✅ Load environment variables

# === Load environment variables ===
load_dotenv()

# === Flask setup ===
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")  # ✅ safer secret key
CORS(app)

# === OpenAI client ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY not set. Please add it to .env or environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

# === Database setup ===
DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fullname TEXT NOT NULL,
                    email TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    mobile TEXT UNIQUE NOT NULL
                )''')
    
    # Demo user
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (fullname,email,username,password,mobile) VALUES (?,?,?,?,?)",
                  ("Demo User", "demo@mail.com", "demo123", "12345", "9999999999"))

    # Chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT NOT NULL,       -- "user" or "assistant"
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
    
    conn.commit()
    conn.close()

init_db()

# === Routes ===

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ai")
def ai_page():
    return render_template("index ai.html")

#######################################
# Login
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return {"success": False, "error": "Missing username or password"}, 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        session["user"] = {
            "id": user[0],
            "fullname": user[1],
            "username": user[3],
            "email": user[2],
            "mobile": user[5]
        }
        return {"success": True, "message": "Login successful"}
    else:
        return {"success": False, "error": "Invalid username or password"}, 401

#######################################
# Registration
@app.route("/regi", methods=["GET", "POST"])
def regi_page():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm"]
        mobile = request.form["mobile"]

        if password != confirm:
            flash("❌ Passwords do not match", "error")
            return redirect("/regi")

        if len(mobile) != 10 or not mobile.isdigit():
            flash("❌ Mobile number must be 10 digits", "error")
            return redirect("/regi")

        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (fullname,email,username,password,mobile) VALUES (?,?,?,?,?)",
                (fullname, email, username, password, mobile)
            )
            conn.commit()
            conn.close()
            
            flash("✅ Registered successfully! Please login.", "success")
            # ✅ Redirect to login page
            return redirect("/ai")  # or "/index-ai" if your route is named differently

        except sqlite3.IntegrityError:
            flash("❌ Mobile number already exists!", "error")
            return redirect("/regi")

    return render_template("register.html")


#######################################
# AI Ask API
@app.route("/ask", methods=["POST"])
def ask():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "No question provided"}), 400

    user_id = session["user"]["id"]

    # Save user question in DB
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
              (user_id, "user", question))
    conn.commit()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
            max_tokens=300,
            temperature=0.6
        )
        answer = response.choices[0].message.content

        # Save AI reply in DB
        c.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                  (user_id, "assistant", answer))
        conn.commit()
        conn.close()

        return jsonify({"answer": answer})

    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

#######################################
#######################################
# Fetch chat history as JSON (for sidebar)
@app.route("/history-json", methods=["GET"])
def history_json():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403

    user_id = session["user"]["id"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT role, content, timestamp FROM chat_history WHERE user_id=? ORDER BY timestamp ASC",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()

    history = [{"role": r[0], "content": r[1], "time": r[2]} for r in rows]
    return jsonify({"history": history})

#######################################
# Clear session history
@app.route("/clear", methods=["POST"])
def clear_history():
    session.pop("chat_history", None)
    return jsonify({"message": "Session history cleared"})

#######################################
# Account info
@app.route("/account", methods=["GET"])
def get_account():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403
    return jsonify(session["user"])

#######################################
if __name__ == "__main__":
    app.run(debug=False)
