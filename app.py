#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Iterator

from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from waitress import serve
from werkzeug.security import check_password_hash, generate_password_hash

APP_ID = "rovento-repair-webapp"
APP_NAME = "ROVENTO Repair WebApp"
APP_VERSION = "1.0.0"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5058


def resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def runtime_dir() -> Path:
    root = Path(os.environ.get("PROGRAMDATA") or (Path.home() / ".rovento"))
    path = root / "ROVENTO" / "Repair WebApp"
    for sub in ("config", "data", "logs", "backups", "uploads"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path


RESOURCE_DIR = resource_dir()
RUNTIME_DIR = runtime_dir()
CONFIG_DIR = RUNTIME_DIR / "config"
DATA_DIR = RUNTIME_DIR / "data"
DB_CONFIG_FILE = CONFIG_DIR / "database.json"
APP_CONFIG_FILE = CONFIG_DIR / "application.json"
KEY_FILE = CONFIG_DIR / "secret.key"
LOG_FILE = RUNTIME_DIR / "logs" / "application.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(APP_ID)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(150), default="Administrator")
    role: Mapped[str] = mapped_column(String(30), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Ticket(Base):
    __tablename__ = "repair_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(250))
    requester: Mapped[str] = mapped_column(String(150))
    department: Mapped[str] = mapped_column(String(150), default="")
    priority: Mapped[str] = mapped_column(String(30), default="Normal")
    status: Mapped[str] = mapped_column(String(30), default="Open", index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), default="system")
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80), default="")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class SecretStore:
    def __init__(self, key_file: Path) -> None:
        self.key_file = key_file
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        return key

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            return ""


SECRET_STORE = SecretStore(KEY_FILE)


def default_db_config() -> dict[str, Any]:
    return {
        "type": "sqlite",
        "sqlite_path": str(DATA_DIR / "repair.db"),
        "server": "",
        "port": 1433,
        "database": "ROVENTO_Repair",
        "username": "",
        "password": "",
        "driver": "ODBC Driver 17 for SQL Server",
        "encrypt": False,
        "trust_certificate": True,
        "timeout": 8,
    }


def load_app_config() -> dict[str, Any]:
    if APP_CONFIG_FILE.exists():
        try:
            return json.loads(APP_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Cannot read application config")
    cfg = {"secret_key": secrets.token_hex(32), "host": DEFAULT_HOST, "port": DEFAULT_PORT}
    APP_CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


class DatabaseManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None
        self.configured_config: dict[str, Any] = default_db_config()
        self.active_config: dict[str, Any] = default_db_config()
        self.last_error = ""
        self.using_fallback = False

    def read_config(self) -> dict[str, Any]:
        if not DB_CONFIG_FILE.exists():
            return default_db_config()
        raw = json.loads(DB_CONFIG_FILE.read_text(encoding="utf-8"))
        cfg = default_db_config()
        cfg.update(raw)
        cfg["password"] = SECRET_STORE.decrypt(str(raw.get("password_encrypted", "")))
        cfg.pop("password_encrypted", None)
        return cfg

    def write_config(self, cfg: dict[str, Any]) -> None:
        stored = dict(cfg)
        stored["password_encrypted"] = SECRET_STORE.encrypt(str(stored.pop("password", "")))
        DB_CONFIG_FILE.write_text(json.dumps(stored, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def public_config(cfg: dict[str, Any]) -> dict[str, Any]:
        output = dict(cfg)
        output["password"] = ""
        output["password_saved"] = bool(cfg.get("password"))
        return output

    @staticmethod
    def _validated(cfg: dict[str, Any]) -> dict[str, Any]:
        merged = default_db_config()
        merged.update(cfg)
        db_type = str(merged.get("type", "sqlite")).lower().strip()
        if db_type not in {"sqlite", "mssql"}:
            raise ValueError("Database type must be sqlite or mssql")
        merged["type"] = db_type
        merged["port"] = int(merged.get("port") or 1433)
        merged["timeout"] = max(1, int(merged.get("timeout") or 8))
        if db_type == "sqlite":
            path = Path(str(merged.get("sqlite_path") or (DATA_DIR / "repair.db")))
            path.parent.mkdir(parents=True, exist_ok=True)
            merged["sqlite_path"] = str(path)
        else:
            for required in ("server", "database", "username"):
                if not str(merged.get(required, "")).strip():
                    raise ValueError(f"Missing required field: {required}")
        return merged

    def _make_engine(self, cfg: dict[str, Any]) -> Engine:
        cfg = self._validated(cfg)
        if cfg["type"] == "sqlite":
            db_path = Path(cfg["sqlite_path"]).resolve()
            return create_engine(
                f"sqlite:///{db_path.as_posix()}",
                future=True,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False, "timeout": cfg["timeout"]},
            )

        server = str(cfg["server"]).strip()
        port = int(cfg["port"])
        odbc = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={server},{port};"
            f"DATABASE={cfg['database']};"
            f"UID={cfg['username']};"
            f"PWD={cfg.get('password', '')};"
            f"Encrypt={'yes' if cfg.get('encrypt') else 'no'};"
            f"TrustServerCertificate={'yes' if cfg.get('trust_certificate') else 'no'};"
            f"Connection Timeout={cfg['timeout']};"
        )
        url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc)
        return create_engine(url, future=True, pool_pre_ping=True, pool_recycle=1800)

    def test(self, cfg: dict[str, Any]) -> tuple[bool, str]:
        engine: Engine | None = None
        try:
            engine = self._make_engine(cfg)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Connection successful"
        except Exception as exc:
            return False, str(exc)
        finally:
            if engine is not None:
                engine.dispose()

    def activate(self, cfg: dict[str, Any], persist: bool = False) -> None:
        validated = self._validated(cfg)
        new_engine = self._make_engine(validated)
        try:
            with new_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(new_engine)
            new_factory = sessionmaker(bind=new_engine, expire_on_commit=False, future=True)
        except Exception:
            new_engine.dispose()
            raise

        with self._lock:
            old_engine = self.engine
            self.engine = new_engine
            self.session_factory = new_factory
            self.active_config = dict(validated)
            self.configured_config = dict(validated)
            self.last_error = ""
            self.using_fallback = False
            if persist:
                self.write_config(validated)
            if old_engine is not None:
                old_engine.dispose()

    def startup(self) -> None:
        configured = self.read_config()
        self.configured_config = dict(configured)
        try:
            self.activate(configured, persist=False)
        except Exception as exc:
            logger.exception("Configured database is unavailable; using local SQLite fallback")
            self.last_error = str(exc)
            self.using_fallback = True
            fallback = default_db_config()
            self.activate(fallback, persist=False)
            self.configured_config = dict(configured)
            self.last_error = str(exc)
            self.using_fallback = True

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        if self.session_factory is None:
            raise RuntimeError("Database is not initialized")
        db_session = self.session_factory()
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def status(self) -> dict[str, Any]:
        active = self.public_config(self.active_config)
        configured = self.public_config(self.configured_config)
        return {
            "connected": self.engine is not None,
            "using_fallback": self.using_fallback,
            "last_error": self.last_error,
            "active": active,
            "configured": configured,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }


APP_CONFIG = load_app_config()
DB = DatabaseManager()
DB.startup()

app = Flask(__name__, template_folder=str(RESOURCE_DIR / "templates"))
app.secret_key = APP_CONFIG["secret_key"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


def ensure_admin() -> None:
    with DB.session_scope() as dbs:
        admin = dbs.scalar(select(User).where(User.username == "admin"))
        if admin is None:
            dbs.add(
                User(
                    username="admin",
                    password_hash=generate_password_hash("admin123"),
                    display_name="System Administrator",
                    role="admin",
                    is_active=True,
                )
            )
            dbs.add(AuditLog(username="system", action="CREATE_DEFAULT_ADMIN", entity="user", entity_id="admin"))


ensure_admin()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return jsonify({"ok": False, "message": "Admin permission required"}), 403
        return view(*args, **kwargs)
    return wrapped


def ticket_to_dict(ticket: Ticket) -> dict[str, Any]:
    return {
        "id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "title": ticket.title,
        "requester": ticket.requester,
        "department": ticket.department,
        "priority": ticket.priority,
        "status": ticket.status,
        "detail": ticket.detail,
        "created_by": ticket.created_by,
        "created_at": ticket.created_at.isoformat(timespec="seconds") if ticket.created_at else "",
        "updated_at": ticket.updated_at.isoformat(timespec="seconds") if ticket.updated_at else "",
    }


def next_ticket_no() -> str:
    return "RP-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:20]


def audit(action: str, entity: str = "", entity_id: str = "", detail: str = "") -> None:
    with DB.session_scope() as dbs:
        dbs.add(
            AuditLog(
                username=session.get("username", "system"),
                action=action,
                entity=entity,
                entity_id=str(entity_id),
                detail=detail,
            )
        )


@app.get("/health")
def health():
    return jsonify({"ok": True, "app": APP_ID, "version": APP_VERSION, "database": DB.status()})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with DB.session_scope() as dbs:
            user = dbs.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
            if user and check_password_hash(user.password_hash, password):
                session.clear()
                session.update(username=user.username, display_name=user.display_name, role=user.role)
                audit("LOGIN", "user", user.username)
                return redirect(request.args.get("next") or url_for("index"))
        flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "error")
    return render_template("login.html", app_name=APP_NAME)


@app.get("/logout")
def logout():
    username = session.get("username", "")
    session.clear()
    if username:
        try:
            audit("LOGOUT", "user", username)
        except Exception:
            pass
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    return render_template("index.html", app_name=APP_NAME, version=APP_VERSION)


@app.get("/admin/database")
@admin_required
def admin_database():
    return render_template(
        "admin_database.html",
        app_name=APP_NAME,
        config=DB.public_config(DB.configured_config),
        status=DB.status(),
    )


@app.get("/api/tickets")
@login_required
def list_tickets():
    with DB.session_scope() as dbs:
        records = dbs.scalars(
            select(Ticket).where(Ticket.is_deleted.is_(False)).order_by(Ticket.created_at.desc()).limit(1000)
        ).all()
        return jsonify({"ok": True, "items": [ticket_to_dict(item) for item in records]})


@app.post("/api/tickets")
@login_required
def create_ticket():
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    requester_name = str(payload.get("requester", "")).strip()
    if not title or not requester_name:
        return jsonify({"ok": False, "message": "Title and requester are required"}), 400
    ticket = Ticket(
        ticket_no=next_ticket_no(),
        title=title,
        requester=requester_name,
        department=str(payload.get("department", "")).strip(),
        priority=str(payload.get("priority", "Normal")),
        status=str(payload.get("status", "Open")),
        detail=str(payload.get("detail", "")).strip(),
        created_by=session.get("username", ""),
    )
    with DB.session_scope() as dbs:
        dbs.add(ticket)
        dbs.flush()
        result = ticket_to_dict(ticket)
    audit("CREATE", "ticket", str(ticket.id), ticket.ticket_no)
    return jsonify({"ok": True, "item": result}), 201


@app.put("/api/tickets/<int:ticket_id>")
@login_required
def update_ticket(ticket_id: int):
    payload = request.get_json(silent=True) or {}
    allowed = {"title", "requester", "department", "priority", "status", "detail"}
    with DB.session_scope() as dbs:
        ticket = dbs.get(Ticket, ticket_id)
        if ticket is None or ticket.is_deleted:
            return jsonify({"ok": False, "message": "Ticket not found"}), 404
        for field in allowed:
            if field in payload:
                setattr(ticket, field, str(payload[field]).strip())
        ticket.updated_at = datetime.now()
        dbs.flush()
        result = ticket_to_dict(ticket)
    audit("UPDATE", "ticket", str(ticket_id), json.dumps(payload, ensure_ascii=False))
    return jsonify({"ok": True, "item": result})


@app.delete("/api/tickets/<int:ticket_id>")
@login_required
def delete_ticket(ticket_id: int):
    with DB.session_scope() as dbs:
        ticket = dbs.get(Ticket, ticket_id)
        if ticket is None or ticket.is_deleted:
            return jsonify({"ok": False, "message": "Ticket not found"}), 404
        ticket.is_deleted = True
        ticket.updated_at = datetime.now()
    audit("DELETE", "ticket", str(ticket_id))
    return jsonify({"ok": True})


@app.get("/api/admin/database/status")
@admin_required
def database_status():
    return jsonify({"ok": True, "status": DB.status()})


def payload_to_db_config(payload: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DB.configured_config)
    for key in (
        "type", "sqlite_path", "server", "port", "database", "username", "driver",
        "encrypt", "trust_certificate", "timeout",
    ):
        if key in payload:
            cfg[key] = payload[key]
    supplied_password = str(payload.get("password", ""))
    if supplied_password:
        cfg["password"] = supplied_password
    return cfg


@app.post("/api/admin/database/test")
@admin_required
def database_test():
    payload = request.get_json(silent=True) or {}
    cfg = payload_to_db_config(payload)
    ok, message = DB.test(cfg)
    return jsonify({"ok": ok, "message": message}), 200 if ok else 400


@app.post("/api/admin/database/save")
@admin_required
def database_save():
    payload = request.get_json(silent=True) or {}
    cfg = payload_to_db_config(payload)
    try:
        DB.activate(cfg, persist=True)
        ensure_admin()
        audit("DATABASE_CONFIG_SAVED", "system", "database", DB.public_config(cfg)["type"])
        return jsonify({"ok": True, "message": "Database configuration saved", "status": DB.status()})
    except Exception as exc:
        logger.exception("Cannot save database configuration")
        return jsonify({"ok": False, "message": str(exc)}), 400


@app.post("/api/admin/change-password")
@admin_required
def change_password():
    payload = request.get_json(silent=True) or {}
    old_password = str(payload.get("old_password", ""))
    new_password = str(payload.get("new_password", ""))
    if len(new_password) < 8:
        return jsonify({"ok": False, "message": "New password must contain at least 8 characters"}), 400
    username = session["username"]
    with DB.session_scope() as dbs:
        user = dbs.scalar(select(User).where(User.username == username))
        if user is None or not check_password_hash(user.password_hash, old_password):
            return jsonify({"ok": False, "message": "Current password is incorrect"}), 400
        user.password_hash = generate_password_hash(new_password)
    audit("CHANGE_PASSWORD", "user", username)
    return jsonify({"ok": True, "message": "Password changed"})


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "message": "Not found"}), 404
    return redirect(url_for("index"))


def app_is_running(port: int) -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/health", timeout=1.2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("app") == APP_ID
    except Exception:
        return False


def port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.8):
            return True
    except OSError:
        return False


def open_browser_when_ready(port: int) -> None:
    url = f"http://127.0.0.1:{port}/"
    for _ in range(60):
        if app_is_running(port):
            webbrowser.open(url, new=2)
            return
        time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--host", default=os.environ.get("APP_HOST", APP_CONFIG.get("host", DEFAULT_HOST)))
    parser.add_argument("--port", type=int, default=int(os.environ.get("APP_PORT", APP_CONFIG.get("port", DEFAULT_PORT))))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if app_is_running(args.port):
        if not args.no_browser:
            webbrowser.open(f"http://127.0.0.1:{args.port}/", new=2)
        return 0
    if port_in_use(args.port):
        logger.error("Port %s is already used by another application", args.port)
        return 2

    if not args.no_browser:
        threading.Thread(target=open_browser_when_ready, args=(args.port,), daemon=True).start()

    logger.info("Starting %s %s on %s:%s", APP_NAME, APP_VERSION, args.host, args.port)
    serve(app, host=args.host, port=args.port, threads=12, url_scheme="http")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
