import os

import pymysql
from flask import Flask, render_template_string, request

app = Flask(__name__)

FLAG = os.environ.get("FLAG", "Securinets{fake_flag_for_local_testing}")
SHOW_QUERY = os.environ.get("SHOW_QUERY", "1") == "1"  # set to 0 for a harder version

# Players can't use the usual "-- " comment, so they have to find "#"
BLACKLIST = ["--", "/*"]

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vault Login</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0;
           display:flex; justify-content:center; padding:80px 16px 0; }
    .card { background:#1e293b; padding:32px; border-radius:12px; width:360px; max-width:100%; }
    input { width:100%; padding:10px; margin:6px 0 14px; border-radius:6px;
            border:1px solid #475569; background:#0f172a; color:#e2e8f0; box-sizing:border-box; }
    button { width:100%; padding:10px; border:0; border-radius:6px;
             background:#38bdf8; color:#0f172a; font-weight:700; cursor:pointer; }
    .msg { margin-top:16px; padding:10px; border-radius:6px; background:#334155; }
    .err { background:#7f1d1d; }
    .ok  { background:#14532d; }
    code { font-size:12px; word-break:break-all; }
    h1 { margin-top:0; }
    small { color:#94a3b8; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Vault Login</h1>
    <small>Only the admin can open the vault.</small>
    <form method="POST" action="/login">
      <label>Username</label>
      <input name="username" autocomplete="off">
      <label>Password</label>
      <input name="password" type="password">
      <button type="submit">Log in</button>
    </form>
    {% if message %}
      <div class="msg {{ css }}">{{ message }}</div>
    {% endif %}
    {% if query %}
      <div class="msg"><small>Query executed:</small><br><code>{{ query }}</code></div>
    {% endif %}
  </div>
</body>
</html>
"""


def get_db():
    """Connect to the in-container MariaDB over its unix socket.

    Set DB_SOCKET to an empty string and DB_HOST to use TCP instead
    (e.g. when pointing at an external MySQL server).
    """
    kwargs = dict(
        user=os.environ.get("DB_USER", "ctf"),
        password=os.environ.get("DB_PASS", "ctfpass"),
        database=os.environ.get("DB_NAME", "vault"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )
    socket_path = os.environ.get("DB_SOCKET", "/run/mysqld/mysqld.sock")
    if socket_path:
        kwargs["unix_socket"] = socket_path
    else:
        kwargs["host"] = os.environ.get("DB_HOST", "127.0.0.1")
        kwargs["port"] = int(os.environ.get("DB_PORT", "3306"))
    return pymysql.connect(**kwargs)


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/")
def index():
    return render_template_string(PAGE, message=None, css="", query=None)


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    for bad in BLACKLIST:
        if bad in username or bad in password:
            return render_template_string(
                PAGE,
                message="Suspicious comment detected. Nice try!",
                css="err",
                query=None,
            )

    # Intentionally vulnerable: string concatenation
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
    except Exception:
        # Players only see a generic message, but the real error goes to the
        # server log (visible in Render's Logs tab) so you can debug.
        app.logger.exception("login query failed")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
