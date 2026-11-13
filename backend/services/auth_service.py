"""Account validation, password hashing, and saved user preferences."""
import json
import hashlib
import re

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from ..database import get_db
except ImportError:  # `python backend/app.py`
    from database import get_db

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AuthValidationError(ValueError):
    pass


def validate_credentials(name, email, password, registration=False):
    if not isinstance(email, str) or len(email.strip()) > 254 or not EMAIL_RE.fullmatch(email.strip()):
        raise AuthValidationError("Enter a valid email address.")
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        raise AuthValidationError("Password must be between 8 and 128 characters.")
    if registration and (not isinstance(name, str) or not 2 <= len(name.strip()) <= 100):
        raise AuthValidationError("Name must be between 2 and 100 characters.")


def public_user(row):
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"], "created_at": row["created_at"]}


def create_user(name, email, password):
    validate_credentials(name, email, password, registration=True)
    connection = get_db()
    try:
        cursor = connection.execute(
            "INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().casefold(), generate_password_hash(password)),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    row = connection.execute("SELECT id,name,email,created_at FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
    return public_user(row)


def authenticate(email, password):
    if not isinstance(email, str) or not isinstance(password, str):
        return None
    connection = get_db()
    row = connection.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email.strip().casefold(),)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return None
    return public_user(row)


def get_user(user_id):
    return public_user(get_db().execute("SELECT id,name,email,created_at FROM users WHERE id=?", (user_id,)).fetchone())


def _session_hash(session_token):
    if not isinstance(session_token, str) or not session_token:
        return ""
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def create_session(user_id, session_token, expires_at):
    """Persist only a token digest so a signed-cookie replay can be revoked."""
    token_hash = _session_hash(session_token)
    if not token_hash:
        raise ValueError("A non-empty session token is required.")
    connection = get_db()
    connection.execute("INSERT INTO auth_sessions(session_hash,user_id,expires_at) VALUES(?,?,?)",
                       (token_hash, user_id, expires_at))
    connection.commit()


def get_session_user(user_id, session_token):
    token_hash = _session_hash(session_token)
    if not user_id or not token_hash:
        return None
    row = get_db().execute(
        "SELECT users.id,users.name,users.email,users.created_at "
        "FROM auth_sessions JOIN users ON users.id=auth_sessions.user_id "
        "WHERE auth_sessions.session_hash=? AND auth_sessions.user_id=? "
        "AND auth_sessions.expires_at>CURRENT_TIMESTAMP",
        (token_hash, user_id),
    ).fetchone()
    return public_user(row)


def revoke_session(session_token):
    token_hash = _session_hash(session_token)
    if not token_hash:
        return
    connection = get_db()
    connection.execute("DELETE FROM auth_sessions WHERE session_hash=?", (token_hash,))
    connection.commit()


def get_preferences(user_id):
    row = get_db().execute("SELECT settings_json FROM preferences WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        return {}
    try:
        value = json.loads(row["settings_json"])
    except (TypeError, json.JSONDecodeError):
        current_app.logger.warning("Invalid saved preferences for user id %s", user_id)
        return {}
    return value if isinstance(value, dict) else {}


def save_preferences(user_id, settings):
    if not isinstance(settings, dict):
        raise AuthValidationError("Preferences must be a JSON object.")
    try:
        encoded = json.dumps(settings, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AuthValidationError("Preferences must contain valid JSON values.") from exc
    if len(encoded) > 8192:
        raise AuthValidationError("Preferences must be 8 KB or smaller.")
    connection = get_db()
    connection.execute(
        "INSERT INTO preferences(user_id, settings_json) VALUES(?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET settings_json=excluded.settings_json, updated_at=CURRENT_TIMESTAMP",
        (user_id, encoded),
    )
    connection.commit()
    return get_preferences(user_id)
