#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from flask import Flask, jsonify, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from waitress import serve
from werkzeug.security import check_password_hash, generate_password_hash

APP_NAME = "ROVENTO Repair WebApp"
APP_ID = "rovento-repair-webapp"
APP_VERSION = "1.0.0"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5058


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def data_root() -> Path:
    base = Path(os.environ.get("PROGRAMDATA", Path.home()))
    root = base / "ROVENTO" / "Repair WebApp"
    for child in ("config", "data", "logs", "uploads", "backups"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


DATA_ROOT = data_root()
CONFIG_FILE = DATA_ROOT / "config" / "database.json"
KEY_FILE = DATA_ROOT / "config" / "secret.key"
SQLITE_FILE = DATA_ROOT / "data" / "repair.db"


def cipher() -> Fernet:
    if not KEY_FILE.exists():
        KEY_FILE.write_bytes(Fernet.generate_key())
    return Fernet(KEY_FILE.read_bytes())


def encrypt(value: str) -> str:
    return cipher().encrypt(value.encode("utf-8")).decode("ascii") if value else ""


def decrypt(value: str) -> str:
    if not value:
        return ""
    try:
        return cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


def default_config() -> dict[str, Any]:
    return {
        "type": "sqlite",
        "server": "",
        "port": 1433,
        "database": "ROVENTO_Repair",
        "username": "",
        "password_encrypted": "",
        "driver": "ODBC Driver 17 for SQL Server",
        "encrypt": False,
        "trust_certificate": True,
        "updated_at": "",
    }


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        cfg = default_config()
        save_config(cfg)
        return cfg
    try:
        return {**default_config(), **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
    except Exception:
        return default_config()


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def build_db_url(cfg: dict[str, Any], include_password: bool = True) -> str:
    db_type = str(cfg.get("type", "sqlite")).lower()
    if db_type == "sqlite":
        return f"sqlite:///{SQLITE_FILE.as_posix()}"

    from urllib.parse import quote_plus

    server = str(cfg.get("server", "")).strip()
    port = int(cfg.get("port") or (5432 if db_type == "postgresql" else 1433))
    database = str(cfg.get("database", "")).strip()
    username = quote_plus(str(cfg.get("username", "")).strip())
    password = decrypt(str(cfg.get("password_encrypted", ""))) if include_password else "***"
    password = quote_plus(password)

    if db_type == "mssql":
        driver = quote_plus(str(cfg.get("driver") or "ODBC Driver 17 for SQL Server"))
        encrypt_value = "yes" if cfg.get("encrypt") else "no"
        trust = "yes" if cfg.get("trust_certificate", True) else "no"
        return (
            f"mssql+pyodbc://{username}:{password}@{server}:{port}/{database}"
            f"?driver={driver}&Encrypt={encrypt_value}&TrustServerCertificate={trust}"
        )
    if db_type == "postgresql":
        return f"postgresql+psycopg://{username}:{password}@{server}:{port}/{database}"
    raise ValueError(f"Unsupported database type: {db_type}")


app = Flask(
    __name__,
    template_folder=str(resource_path("templates")),
    static_folder=str(resource_path("static")),
)
app.config.update(
    SECRET_KEY=os.environ.get("ROVENTO_SECRET", "rovento-repair-change-this-key"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,
)
app.config["SQLALCHEMY_DATABASE_URI"] = build_db_url(load_config())
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="user")
    active = db.Column(db.Boolean, nullable=False, default=True)


class Ticket(db.Model):
    __tablename__ = "repair_tickets"
    id = db.Column(db.Integer, primary_key=True)
    ticket_no = db.Column(db.String(40), unique=True, nullable=False)
    request_type = db.Column(db.String(40), nullable=False, default="repair")
    employee_id = db.Column(db.String(80), nullable=False)
    area = db.Column(db.String(80), nullable=False)
    machine = db.Column(db.String(120), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    remote_no = db.Column(db.String(120), nullable=False, default="")
    required_date = db.Column(db.String(20), nullable=False, default="")
    budget = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="New")
    assigned_to = db.Column(db.String(80), nullable=False, default="")
    solution = db.Column(db.Text, nullable=False, default="")
    equipment = db.Column(db.Text, nullable=False, default="")
    price = db.Column(db.Float, nullable=True)
    supervisor_comment = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ticket_no": self.ticket_no,
            "request_type": self.request_type,
            "employee_id": self.employee_id,
            "area": self.area,
            "machine": self.machine,
            "problem": self.problem,
            "remote_no": self.remote_no,
            "required_date": self.required_date,
            "budget": self.budget,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "solution": self.solution,
            "equipment": self.equipment,
            "price": self.price,
            "supervisor_comment": self.supervisor_comment,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "updated_at": self.updated_at.isoformat(timespec="seconds"),
        }


def seed_database() -> None:
    db.create_all()
    defaults = [
        ("rovento", "rovento", "System Administrator", "admin"),
        ("T001", "1234", "Technician T001", "technician"),
        ("S001", "1234", "Supervisor S001", "supervisor"),
    ]
    changed = False
    for username, password, display_name, role in defaults:
        if not User.query.filter_by(username=username).first():
            db.session.add(User(username=username, password_hash=generate_password_hash(password), display_name=display_name, role=role))
            changed = True
    if changed:
        db.session.commit()


with app.app_context():
    try:
        seed_database()
    except Exception as exc:
        print(f"Database startup warning: {exc}")


def require_login(roles: tuple[str, ...] | None = None):
    if not session.get("user"):
        return jsonify({"ok": False, "error": "Not authenticated"}), 401
    if roles and session.get("role") not in roles:
        return jsonify({"ok": False, "error": "Permission denied"}), 403
    return None


def next_ticket_no() -> str:
    prefix = datetime.now().strftime("RP-%Y%m%d-")
    last = Ticket.query.filter(Ticket.ticket_no.like(f"{prefix}%")).order_by(Ticket.id.desc()).first()
    running = int(last.ticket_no.rsplit("-", 1)[-1]) + 1 if last else 1
    return f"{prefix}{running:03d}"


@app.get("/")
def home():
    return render_template("index.html", app_name=APP_NAME, version=APP_VERSION)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": APP_ID, "version": APP_VERSION})


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=str(payload.get("username", "")).strip(), active=True).first()
    if not user or not check_password_hash(user.password_hash, str(payload.get("password", ""))):
        return jsonify({"ok": False, "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}), 401
    session["user"] = user.username
    session["role"] = user.role
    session["display_name"] = user.display_name
    return jsonify({"ok": True, "user": user.username, "role": user.role, "display_name": user.display_name})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/auth/me")
def me():
    return jsonify({
        "ok": True,
        "authenticated": bool(session.get("user")),
        "user": session.get("user", ""),
        "role": session.get("role", "public"),
        "display_name": session.get("display_name", ""),
    })


@app.get("/api/tickets")
def list_tickets():
    query = Ticket.query
    employee = request.args.get("employee", "").strip()
    if employee:
        query = query.filter_by(employee_id=employee)
    rows = query.order_by(Ticket.id.desc()).all()
    return jsonify({"ok": True, "items": [row.to_dict() for row in rows]})


@app.post("/api/tickets")
def create_ticket():
    payload = request.get_json(silent=True) or {}
    required = ["employee_id", "area", "machine", "problem"]
    missing = [key for key in required if not str(payload.get(key, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}), 400
    ticket = Ticket(
        ticket_no=next_ticket_no(),
        request_type=str(payload.get("request_type", "repair")),
        employee_id=str(payload["employee_id"]).strip(),
        area=str(payload["area"]).strip(),
        machine=str(payload["machine"]).strip(),
        problem=str(payload["problem"]).strip(),
        remote_no=str(payload.get("remote_no", "")).strip(),
        required_date=str(payload.get("required_date", "")).strip(),
        budget=float(payload["budget"]) if payload.get("budget") not in (None, "") else None,
    )
    db.session.add(ticket)
    db.session.commit()
    return jsonify({"ok": True, "item": ticket.to_dict()}), 201


@app.patch("/api/tickets/<int:ticket_id>")
def update_ticket(ticket_id: int):
    denied = require_login(("technician", "supervisor", "admin"))
    if denied:
        return denied
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"ok": False, "error": "Ticket not found"}), 404
    payload = request.get_json(silent=True) or {}
    allowed = {"status", "assigned_to", "solution", "equipment", "price", "supervisor_comment"}
    for key in allowed:
        if key in payload:
            value = payload[key]
            if key == "price":
                value = float(value) if value not in (None, "") else None
            setattr(ticket, key, value)
    db.session.commit()
    return jsonify({"ok": True, "item": ticket.to_dict()})


@app.get("/api/admin/db/status")
def db_status():
    denied = require_login(("admin",))
    if denied:
        return denied
    cfg = load_config()
    try:
        engine = create_engine(build_db_url(cfg), pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        connected, error = True, ""
    except Exception as exc:
        connected, error = False, str(exc)
    safe = {k: v for k, v in cfg.items() if k != "password_encrypted"}
    safe["has_password"] = bool(cfg.get("password_encrypted"))
    return jsonify({"ok": True, "connected": connected, "error": error, "config": safe})


def config_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    old = load_config()
    password = str(payload.get("password", ""))
    encrypted = encrypt(password) if password else old.get("password_encrypted", "")
    return {
        "type": str(payload.get("type", "sqlite")).lower(),
        "server": str(payload.get("server", "")).strip(),
        "port": int(payload.get("port") or 1433),
        "database": str(payload.get("database", "ROVENTO_Repair")).strip(),
        "username": str(payload.get("username", "")).strip(),
        "password_encrypted": encrypted,
        "driver": str(payload.get("driver", "ODBC Driver 17 for SQL Server")).strip(),
        "encrypt": bool(payload.get("encrypt", False)),
        "trust_certificate": bool(payload.get("trust_certificate", True)),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/admin/db/test")
def test_db():
    denied = require_login(("admin",))
    if denied:
        return denied
    try:
        cfg = config_from_payload(request.get_json(silent=True) or {})
        engine = create_engine(build_db_url(cfg), pool_pre_ping=True, connect_args={"timeout": 8} if cfg["type"] == "sqlite" else {})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return jsonify({"ok": True, "message": "เชื่อมต่อฐานข้อมูลสำเร็จ"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/admin/db/save")
def save_db():
    denied = require_login(("admin",))
    if denied:
        return denied
    try:
        cfg = config_from_payload(request.get_json(silent=True) or {})
        engine = create_engine(build_db_url(cfg), pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        save_config(cfg)
        return jsonify({"ok": True, "message": "บันทึกแล้ว กรุณากด Restart Server เพื่อเปลี่ยนฐานข้อมูล"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/admin/change-password")
def change_password():
    denied = require_login(("admin",))
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    if len(password) < 6:
        return jsonify({"ok": False, "error": "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร"}), 400
    user = User.query.filter_by(username=session["user"]).first()
    user.password_hash = generate_password_hash(password)
    db.session.commit()
    return jsonify({"ok": True})


def port_is_our_server(port: int) -> bool:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/api/health", timeout=1.2) as response:
            return json.loads(response.read().decode("utf-8")).get("app") == APP_ID
    except Exception:
        return False


def port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.8):
            return True
    except OSError:
        return False


def open_browser_when_ready(port: int) -> None:
    for _ in range(50):
        if port_is_our_server(port):
            webbrowser.open(f"http://127.0.0.1:{port}", new=2)
            return
        time.sleep(0.2)


def main() -> int:
    host = os.environ.get("APP_HOST", DEFAULT_HOST)
    port = int(os.environ.get("APP_PORT", str(DEFAULT_PORT)))
    if port_is_our_server(port):
        webbrowser.open(f"http://127.0.0.1:{port}", new=2)
        return 0
    if port_in_use(port):
        print(f"Port {port} is already used by another program.")
        return 2
    if os.environ.get("OPEN_BROWSER", "1") != "0":
        threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    serve(app, host=host, port=port, threads=12, url_scheme="http")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
