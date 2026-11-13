"""Account routes. Mutating requests require the application CSRF token."""
import secrets
import sqlite3
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, session

try:
    from ..services import auth_service
except ImportError:  # `python backend/app.py`
    from services import auth_service


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise auth_service.AuthValidationError("Request body must be a JSON object.")
    return body


def _start_authenticated_session(user):
    prior_token = session.get("session_token")
    if prior_token:
        auth_service.revoke_session(prior_token)
    csrf_token = session.get("csrf_token")
    session.clear()
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + current_app.permanent_session_lifetime).strftime("%Y-%m-%d %H:%M:%S")
    auth_service.create_session(user["id"], token, expires_at)
    if csrf_token:
        session["csrf_token"] = csrf_token
    session["user_id"] = user["id"]
    session["session_token"] = token
    session.permanent = True


@auth_bp.get("/csrf")
def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return jsonify({"csrf_token": token})


@auth_bp.post("/register")
def register():
    body = _json_body()
    try:
        user = auth_service.create_user(body.get("name"), body.get("email"), body.get("password"))
    except auth_service.AuthValidationError as exc:
        return jsonify({"error": str(exc), "code": "invalid_input"}), 400
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with this email already exists.", "code": "email_exists"}), 409
    _start_authenticated_session(user)
    current_app.logger.info("Registered account id=%s", user["id"])
    return jsonify({"user": user}), 201


@auth_bp.post("/login")
def login():
    body = _json_body()
    email, password = body.get("email"), body.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Email and password are required.", "code": "invalid_input"}), 400
    user = auth_service.authenticate(email, password)
    if user is None:
        current_app.logger.info("Rejected sign-in for an invalid credential pair")
        return jsonify({"error": "Email or password is incorrect.", "code": "invalid_credentials"}), 401
    _start_authenticated_session(user)
    current_app.logger.info("Authenticated account id=%s", user["id"])
    return jsonify({"user": user})


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    token = session.get("session_token")
    user = auth_service.get_session_user(user_id, token)
    if (user_id or token) and user is None:
        session.clear()
    return jsonify({"user": user})


@auth_bp.post("/logout")
def logout():
    auth_service.revoke_session(session.get("session_token"))
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/preferences", methods=["GET", "PUT"])
def preferences():
    user_id = session.get("user_id")
    token = session.get("session_token")
    user = auth_service.get_session_user(user_id, token)
    if not user:
        if user_id or token:
            session.clear()
        return jsonify({"error": "Authentication required.", "code": "unauthorized"}), 401
    if request.method == "GET":
        return jsonify(auth_service.get_preferences(user_id))
    try:
        settings = _json_body()
        return jsonify(auth_service.save_preferences(user_id, settings))
    except auth_service.AuthValidationError as exc:
        return jsonify({"error": str(exc), "code": "invalid_input"}), 400
