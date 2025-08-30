from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = "supersecret"  # change in production


# --- DB Init ---
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT,
                    password TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    receiver_id TEXT,
                    sender_name TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()


init_db()


# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_id = str(uuid.uuid4())
        username = request.form["username"].strip().lower()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, username, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "⚠️ Username already taken!"
        conn.close()

        session["user_id"] = user_id
        session["username"] = username
        return redirect(url_for("dashboard"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect(url_for("dashboard"))
        return "⚠️ Invalid credentials!"
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE receiver_id=? ORDER BY created_at DESC", (session["user_id"],))
    messages = c.fetchall()
    conn.close()

    profile_link = request.host_url + "u/" + session["username"]

    return render_template("dashboard.html", messages=messages, profile_link=profile_link)


@app.route("/u/<username>", methods=["GET", "POST"])
def response_page(username):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    if not user:
        conn.close()
        return "❌ User not found!"

    if request.method == "POST":
        msg_id = str(uuid.uuid4())
        sender_name = request.form["sender_name"].strip()
        message = request.form["message"].strip()

        if not sender_name or not message:
            conn.close()
            return "⚠️ Both name and message are required!"

        c.execute("INSERT INTO messages (id, receiver_id, sender_name, message) VALUES (?, ?, ?, ?)",
                (msg_id, user[0], sender_name, message))
        conn.commit()


    # Fetch all messages for this user
    c.execute("SELECT sender_name, message, created_at FROM messages WHERE receiver_id=? ORDER BY created_at DESC", (user[0],))
    msgs = c.fetchall()

    conn.close()

    return render_template("response.html", username=username, messages=msgs)


@app.route("/adminpanel")
def admin():
    # In production, you should secure this route (add admin login check)
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users")
    users = c.fetchall()
    c.execute("SELECT * FROM messages")
    messages = c.fetchall()
    conn.close()
    return render_template("admin.html", users=users, messages=messages)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
