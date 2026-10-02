import os
import pymysql
from flask import Flask, render_template_string, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "Securinets{fake_flag_for_local_testing}")
SHOW_QUERY = os.environ.get("SHOW_QUERY", "1") == "1"

# Only block the classic comments. Players must discover "#"
BLACKLIST = ["--", "/*"]

PAGE = """..."""  # (keep your existing PAGE template)

def get_db():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "db"),
        user=os.environ.get("DB_USER", "ctf"),
        password=os.environ.get("DB_PASS", "ctfpass"),
        database=os.environ.get("DB_NAME", "vault"),
        cursorclass=pymysql.cursors.DictCursor,
        # Important for MySQL comment behaviour
        autocommit=True,
    )

@app.route("/")
def index():
    return render_template_string(PAGE, message=None, css="", query=None)

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # Block only the classic comments
    for bad in BLACKLIST:
        if bad in username or bad in password:
            return render_template_string(
                PAGE,
                message="Suspicious comment detected. Nice try!",
                css="err",
                query=None,
            )

    # Intentionally vulnerable
    query = (
        "SELECT username, role FROM users "
        f"WHERE username='{username}' AND password='{password}'"
    )
    shown_query = query if SHOW_QUERY else None

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()
        conn.close()
    except Exception as e:
        # For debugging you can temporarily show the real error
        # return render_template_string(PAGE, message=f"DB Error: {e}", css="err", query=shown_query)
        return render_template_string(
            PAGE, message="Database error.", css="err", query=shown_query
        )

    if not row:
        return render_template_string(
            PAGE, message="Invalid credentials.", css="err", query=shown_query
        )

    if row["username"] == "admin":
        return render_template_string(
            PAGE,
            message=f"Welcome, admin. Here is the vault: {FLAG}",
            css="ok",
            query=shown_query,
        )

    return render_template_string(
        PAGE,
        message=f"Welcome, {row['username']}. Nothing in the vault for you.",
        css="",
        query=shown_query,
    )
