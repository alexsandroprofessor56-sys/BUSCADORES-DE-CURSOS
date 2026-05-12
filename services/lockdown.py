import os
import time
from datetime import datetime, timedelta

import requests
from flask import current_app

from core import db
from core.models import AccessEvent, Config
from services.security import log_security_event

SPIKE_WINDOW = int(os.environ.get("SPIKE_WINDOW", "10"))
SPIKE_THRESHOLD = int(os.environ.get("SPIKE_THRESHOLD", "20"))
LOCKDOWN_ALERT_COOLDOWN = 60
_last_alert = 0.0


def _lockdown_config():
    entry = Config.query.filter_by(chave="lockdown_mode").first()
    return entry.valor if entry else "off"


def _set_lockdown(state):
    entry = Config.query.filter_by(chave="lockdown_mode").first()
    if entry:
        entry.valor = state
    else:
        db.session.add(Config(chave="lockdown_mode", valor=state))
    db.session.commit()


def _whitelist_set():
    raw = os.environ.get("LOCKDOWN_WHITELIST", "")
    return {ip.strip() for ip in raw.split(",") if ip.strip()}


def is_locked_down(ip):
    if ip in _whitelist_set():
        return False
    return _lockdown_config() in ("on", "auto_blocked")


def check_spike():
    cutoff = datetime.utcnow() - timedelta(seconds=SPIKE_WINDOW)
    recent = AccessEvent.query.filter(AccessEvent.created_at >= cutoff).all()
    unique_ips = {e.ip for e in recent}
    return len(unique_ips), unique_ips


def auto_lockdown_check():
    global _last_alert
    count, ips = check_spike()
    now = time.time()
    mode = _lockdown_config()

    if count >= SPIKE_THRESHOLD and mode != "disabled":
        if mode != "auto_blocked" and mode != "on":
            _set_lockdown("auto_blocked")
            ip_list = ", ".join(list(ips)[:10])
            msg = (
                f"\U0001f6a8 ALERTA DE ATAQUE\n"
                f"{count} IPs diferentes em {SPIKE_WINDOW}s\n"
                f"Limite: {SPIKE_THRESHOLD}\n"
                f"Lockdown automático ATIVADO!\n"
                f"IPs: {ip_list}"
            )
            log_security_event("0.0.0.0", "lockdown_auto", msg, "critical", "")
            if now - _last_alert > LOCKDOWN_ALERT_COOLDOWN:
                _send_telegram(msg)
                _last_alert = now
        return True

    if count < SPIKE_THRESHOLD and mode == "auto_blocked":
        msg = (
            f"\u2705 Tráfego normalizado\n"
            f"Agora: {count} IPs/{SPIKE_WINDOW}s\n"
            f"Lockdown automático DESATIVADO"
        )
        _set_lockdown("off")
        log_security_event("0.0.0.0", "lockdown_off", msg, "info", "")
        _send_telegram(msg)

    return False


def toggle_lockdown(state):
    valid = {"on", "off", "disabled"}
    if state not in valid:
        return False

    labels = {
        "on": "\U0001f512 Lockdown MANUAL ativado pelo admin",
        "off": "\U0001f513 Lockdown desativado pelo admin",
        "disabled": "\u26d4 Lockdown desabilitado permanentemente pelo admin",
    }
    _set_lockdown(state)
    msg = labels[state]
    log_security_event("0.0.0.0", "lockdown_toggle", msg, "warning", "")
    _send_telegram(msg)
    return True


def lockdown_status():
    mode = _lockdown_config()
    count, ips = check_spike()
    whitelist = _whitelist_set()
    return {
        "mode": mode,
        "active": mode in ("on", "auto_blocked"),
        "auto": mode == "auto_blocked",
        "manual": mode == "on",
        "disabled": mode == "disabled",
        "ips_now": count,
        "threshold": SPIKE_THRESHOLD,
        "window": SPIKE_WINDOW,
        "whitelist": list(whitelist),
    }


def traffic_summary(minutes=5):
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    events = (
        AccessEvent.query
        .filter(AccessEvent.created_at >= cutoff)
        .order_by(AccessEvent.created_at)
        .all()
    )
    ips = {}
    for e in events:
        if e.ip not in ips:
            ips[e.ip] = {
                "ip": e.ip,
                "country": e.country or "?",
                "city": e.city or "?",
                "provider": e.provider or "?",
                "is_bot": e.is_bot,
                "is_vpn": e.is_vpn,
                "is_tor": e.is_tor,
                "lat": e.latitude,
                "lng": e.longitude,
                "first_seen": e.created_at.isoformat() if e.created_at else "?",
                "count": 0,
            }
        ips[e.ip]["count"] += 1

    return {
        "total_events": len(events),
        "unique_ips": len(ips),
        "ips": list(ips.values()),
        "window_minutes": minutes,
    }


def _send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=4,
            )
        except Exception:
            pass


def spike_checker_loop(app):
    while True:
        try:
            with app.app_context():
                auto_lockdown_check()
        except Exception:
            app.logger.exception("Falha no spike checker")
        time.sleep(5)
