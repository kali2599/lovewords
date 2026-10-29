"""Applicazione Flask per Parolario."""

from __future__ import annotations

import os
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import close_db, get_db, init_db


GAME_NAMES = {
    "phrase": "Componi la frase",
    "clue": "Cruciverba lampo",
    "synonym": "Trova il sinonimo",
    "complete": "Completa la parola",
}
LEVELS = {"facile", "medio", "difficile"}
SESSION_HOURS = 12
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_LOGIN_FAILURES = 10
DUMMY_PASSWORD_HASH = generate_password_hash("password-di-verifica-non-valida")


def _secret_key(instance_path: Path) -> str:
    configured = os.environ.get("PAROLARIO_SECRET_KEY")
    if configured:
        return configured

    key_path = instance_path / "secret.key"
    try:
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return key_path.read_text(encoding="utf-8").strip()
    with os.fdopen(descriptor, "w", encoding="utf-8") as key_file:
        key_file.write(secrets.token_hex(32))
    return key_path.read_text(encoding="utf-8").strip()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    instance_directory = Path(app.instance_path)
    instance_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(instance_directory, 0o700)
    app.config.from_mapping(
        SECRET_KEY=_secret_key(Path(app.instance_path)),
        DATABASE=os.environ.get("PAROLARIO_DATABASE", str(Path(app.instance_path) / "parolario.sqlite3")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("PAROLARIO_COOKIE_SECURE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=SESSION_HOURS * 60 * 60,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)
    database_path = Path(app.config["DATABASE"])
    if str(database_path) != ":memory:":
        database_path.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        init_db()
    if str(database_path) != ":memory:":
        os.chmod(database_path, 0o600)

    @app.before_request
    def load_user() -> None:
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            g.user = get_db().execute(
                "SELECT id, username, email, role, must_change_password, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if g.user is None:
                session.clear()

    @app.before_request
    def protect_forms() -> None:
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return
        expected = session.get("csrf_token", "")
        provided = request.headers.get("X-CSRF-Token", "") if request.is_json else request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, provided):
            abort(400, description="Richiesta scaduta. Ricarica la pagina e riprova.")

    @app.before_request
    def require_password_update() -> None:
        if not g.user or not g.user["must_change_password"]:
            return
        allowed = {"change_password", "logout", "static"}
        if request.endpoint not in allowed:
            return redirect(url_for("change_password"))

    @app.context_processor
    def template_context() -> dict:
        return {"csrf_token": _csrf_token, "game_names": GAME_NAMES, "current_user": g.get("user")}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
        if not request.path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    def _csrf_token() -> str:
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                flash("Accedi per continuare.", "info")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    def admin_required(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["role"] != "admin":
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    def valid_password(value: str) -> bool:
        return isinstance(value, str) and 0 < len(value) <= 1024

    def valid_username(value: str) -> bool:
        return isinstance(value, str) and 3 <= len(value) <= 30 and re.fullmatch(r"[\w.-]+", value, flags=re.UNICODE) is not None

    @app.get("/")
    @login_required
    def home():
        summary = get_db().execute(
            "SELECT COUNT(*) AS games, COALESCE(SUM(score), 0) AS correct, "
            "COALESCE(SUM(total), 0) AS questions FROM game_sessions WHERE user_id = ?",
            (g.user["id"],),
        ).fetchone()
        return render_template("index.html", summary=summary)

    @app.route("/registrazione", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("home"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirmation = request.form.get("password_confirmation", "")
            if not valid_username(username):
                flash("Lo username deve avere da 3 a 30 caratteri e può contenere lettere, numeri, punti, trattini o trattini bassi.", "error")
            elif len(email) > 254 or "@" not in email or email.startswith("@") or email.endswith("@"):
                flash("Inserisci un indirizzo email valido.", "error")
            elif not valid_password(password):
                flash("Inserisci una password.", "error")
            elif password != confirmation:
                flash("Le password non coincidono.", "error")
            else:
                db = get_db()
                try:
                    cursor = db.execute(
                        "INSERT INTO users (username, email, password_hash, role, must_change_password) VALUES (?, ?, ?, 'user', 0)",
                        (username, email, generate_password_hash(password)),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    email_exists = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
                    if email_exists:
                        flash("Esiste già un account con questo indirizzo email.", "error")
                    else:
                        flash("Questo username è già utilizzato. Scegline un altro.", "error")
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session.permanent = True
                    flash("Account creato. Buon divertimento!", "success")
                    return redirect(url_for("home"))
        return render_template("auth.html", mode="register")

    @app.route("/accesso", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("home"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            db = get_db()
            ip_address = request.remote_addr or "sconosciuto"
            now = int(time.time())
            attempt = db.execute(
                "SELECT failures, window_started_at FROM login_attempts WHERE ip_address = ?",
                (ip_address,),
            ).fetchone()
            if attempt and now - attempt["window_started_at"] < LOGIN_WINDOW_SECONDS and attempt["failures"] >= MAX_LOGIN_FAILURES:
                flash("Troppi tentativi non riusciti. Riprova tra 15 minuti.", "error")
                return render_template("auth.html", mode="login"), 429
            row = db.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
            password_matches = check_password_hash(row["password_hash"] if row else DUMMY_PASSWORD_HASH, password)
            if row and password_matches:
                db.execute("DELETE FROM login_attempts WHERE ip_address = ?", (ip_address,))
                db.commit()
                session.clear()
                session["user_id"] = row["id"]
                session.permanent = True
                target = "change_password" if row["must_change_password"] else "home"
                return redirect(url_for(target))
            if attempt and now - attempt["window_started_at"] < LOGIN_WINDOW_SECONDS:
                db.execute("UPDATE login_attempts SET failures = failures + 1 WHERE ip_address = ?", (ip_address,))
            else:
                db.execute(
                    "INSERT INTO login_attempts (ip_address, failures, window_started_at) VALUES (?, 1, ?) "
                    "ON CONFLICT(ip_address) DO UPDATE SET failures = 1, window_started_at = excluded.window_started_at",
                    (ip_address, now),
                )
            db.commit()
            flash("Username o password non corretti.", "error")
        return render_template("auth.html", mode="login")

    @app.post("/uscita")
    @login_required
    def logout():
        session.clear()
        flash("Hai chiuso la sessione.", "info")
        return redirect(url_for("login"))

    @app.route("/cambia-password", methods=["GET", "POST"])
    @login_required
    def change_password():
        if request.method == "POST":
            current = request.form.get("current_password", "")
            password = request.form.get("password", "")
            confirmation = request.form.get("password_confirmation", "")
            row = get_db().execute("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],)).fetchone()
            if not row or not check_password_hash(row["password_hash"], current):
                flash("La password attuale non è corretta.", "error")
            elif not valid_password(password):
                flash("Inserisci una nuova password.", "error")
            elif password != confirmation:
                flash("Le nuove password non coincidono.", "error")
            else:
                get_db().execute(
                    "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                    (generate_password_hash(password), g.user["id"]),
                )
                get_db().commit()
                flash("Password aggiornata.", "success")
                return redirect(url_for("home"))
        return render_template("change_password.html")

    @app.get("/progressi")
    @login_required
    def progress():
        db = get_db()
        summary = db.execute(
            "SELECT COUNT(*) AS games, COALESCE(SUM(score), 0) AS correct, "
            "COALESCE(SUM(total), 0) AS questions FROM game_sessions WHERE user_id = ?",
            (g.user["id"],),
        ).fetchone()
        history = db.execute(
            "SELECT game, level, score, total, duration_seconds, played_at FROM game_sessions "
            "WHERE user_id = ? ORDER BY id DESC",
            (g.user["id"],),
        ).fetchall()
        return render_template("progress.html", summary=summary, history=history)

    @app.post("/api/partite")
    @login_required
    def save_game():
        payload = request.get_json(silent=True) or {}
        game = payload.get("game")
        level = payload.get("level")
        score = payload.get("score")
        total = payload.get("total")
        duration = payload.get("duration_seconds")
        client_ref = payload.get("client_ref")
        if (
            not isinstance(game, str)
            or game not in GAME_NAMES
            or not isinstance(level, str)
            or level not in LEVELS
            or isinstance(score, bool)
            or not isinstance(score, int)
            or isinstance(total, bool)
            or total != 3
            or score < 0
            or score > total
            or isinstance(duration, bool)
            or not isinstance(duration, int)
            or duration < 0
            or duration > 86400
        ):
            return jsonify(error="Dati della partita non validi."), 400
        try:
            client_ref = str(uuid.UUID(client_ref))
        except (ValueError, TypeError, AttributeError):
            return jsonify(error="Identificativo della partita non valido."), 400

        db = get_db()
        existing = db.execute(
            "SELECT id FROM game_sessions WHERE user_id = ? AND client_ref = ?",
            (g.user["id"], client_ref),
        ).fetchone()
        if existing:
            return jsonify(saved=True, duplicate=True)
        cursor = db.execute(
            "INSERT OR IGNORE INTO game_sessions (user_id, client_ref, game, level, score, total, duration_seconds, played_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (g.user["id"], client_ref, game, level, score, total, duration, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
        return jsonify(saved=True, duplicate=cursor.rowcount == 0), 201 if cursor.rowcount else 200

    @app.get("/admin/utenti")
    @admin_required
    def admin_users():
        db = get_db()
        users = db.execute(
            "SELECT u.id, u.username, u.email, u.created_at, u.role, u.must_change_password, "
            "COUNT(s.id) AS games, COALESCE(SUM(s.score), 0) AS correct, "
            "COALESCE(SUM(s.total), 0) AS questions "
            "FROM users u LEFT JOIN game_sessions s ON s.user_id = u.id "
            "WHERE u.role = 'user' GROUP BY u.id ORDER BY u.created_at DESC"
        ).fetchall()
        histories = {}
        for user in users:
            histories[user["id"]] = db.execute(
                "SELECT game, level, score, total, played_at FROM game_sessions "
                "WHERE user_id = ? ORDER BY id DESC",
                (user["id"],),
            ).fetchall()
        return render_template("admin_users.html", users=users, histories=histories)

    @app.post("/admin/utenti/<int:user_id>/reset-password")
    @admin_required
    def admin_reset_password(user_id: int):
        temporary_password = request.form.get("temporary_password", "")
        if not valid_password(temporary_password):
            flash("Inserisci una password temporanea.", "error")
            return redirect(url_for("admin_users"))
        db = get_db()
        target = db.execute("SELECT id, email FROM users WHERE id = ? AND role = 'user'", (user_id,)).fetchone()
        if target is None:
            abort(404)
        db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
            (generate_password_hash(temporary_password), user_id),
        )
        db.commit()
        flash(f"Password temporanea aggiornata per {target['email']}. L’utente dovrà cambiarla al prossimo accesso.", "success")
        return redirect(url_for("admin_users"))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("message.html", title="Accesso negato", message="Non hai i permessi per visualizzare questa pagina."), 403

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("message.html", title="Richiesta non valida", message=getattr(error, "description", "La richiesta non è valida.")), 400

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
