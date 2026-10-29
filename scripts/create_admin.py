#!/usr/bin/env python3
"""Crea un account amministratore senza esporre la password negli argomenti CLI."""

from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app  # noqa: E402
from database import get_db  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


def main() -> int:
    username = input("Username admin: ").strip()
    if len(username) < 3 or len(username) > 30 or not all(char.isalnum() or char in "_.-" for char in username):
        print("Username non valido: usa da 3 a 30 lettere, numeri, punti, trattini o trattini bassi.", file=sys.stderr)
        return 2
    email = input("Email admin: ").strip().lower()
    if len(email) > 254 or "@" not in email or email.startswith("@") or email.endswith("@"):
        print("Indirizzo email non valido.", file=sys.stderr)
        return 2

    password = getpass("Password admin: ")
    confirmation = getpass("Ripeti la password: ")
    if not password:
        print("La password non può essere vuota.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Le password non coincidono.", file=sys.stderr)
        return 2

    with app.app_context():
        db = get_db()
        existing = db.execute("SELECT role FROM users WHERE email = ? OR username = ? COLLATE NOCASE", (email, username)).fetchone()
        if existing:
            print("Esiste già un account con questo indirizzo o username. Nessuna modifica eseguita.", file=sys.stderr)
            return 1
        db.execute(
            "INSERT INTO users (username, email, password_hash, role, must_change_password) VALUES (?, ?, ?, 'admin', 0)",
            (username, email, generate_password_hash(password)),
        )
        db.commit()

    print(f"Account admin creato: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
