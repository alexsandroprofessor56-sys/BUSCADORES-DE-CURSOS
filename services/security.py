import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import datetime, timedelta

import requests
from flask import current_app

from core import db
from core.models import AccessEvent, IPBanido, SecurityEvent


BOT_MARKERS = (
    "bot", "crawler", "spider", "scrapy", "curl", "wget", "python-requests",
    "httpx", "headless", "selenium", "playwright", "scanner", "nikto",
    "sqlmap", "nmap", "nessus", "openvas", "acunetix", "burp", "zap",
    "masscan", "zgrab", "cve-", "exploit", "metasploit", "hydra",
    "medusa", "ncrack", "thc-", "bruteforce", "dirbuster", "gobuster",
    "wfuzz", "ffuf", "arachni", "w3af", "netsparker", "appscan",
    "webinspect", "probely", "detectify", "pentest", "xsstrike",
    "commix", "jwt_tool", "hashcat", "john",
)

TOR_EXIT_IPS = {ip.strip() for ip in os.environ.get("TOR_EXIT_IPS", "").split(",") if ip.strip()}
VPN_PROVIDER_MARKERS = ("hosting", "cloud", "vpn", "proxy", "datacenter", "digitalocean", "ovh", "amazon", "google cloud", "azure", "oracle cloud", "vultr", "linode", "scaleway", "hetzner")

MALICIOUS_PATHS = {
    "/wp-admin", "/wp-login", "/xmlrpc.php", "wp-", "cgi-bin",
    ".env", ".git", ".svn", "config.php", "db_admin", "phpmyadmin",
    "mysql", "administrator", "joomla", "wordpress", "backup",
    "shell", "cmd", "exec", "eval", "concat", "union", "select",
    "../", "..\\", "%00", "null", "etc/passwd", "boot.ini",
}

ADMIN_HONEYPOT_FIELD = "_hp"


def get_client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def is_bot_user_agent(user_agent):
    ua = (user_agent or "").lower()
    return any(marker in ua for marker in BOT_MARKERS)


def is_tor_ip(ip):
    return ip in TOR_EXIT_IPS


def is_probable_vpn(provider):
    text = (provider or "").lower()
    return any(marker in text for marker in VPN_PROVIDER_MARKERS)


def log_security_event(ip, event_type, message, severity="info", user_agent=""):
    event = SecurityEvent(
        ip=ip,
        event_type=event_type,
        severity=severity,
        message=message[:500],
        user_agent=(user_agent or "")[:500],
    )
    db.session.add(event)
    db.session.commit()
    if severity in ("critical", "warning"):
        send_alert(f"[{severity.upper()}] {event_type}: {message} | IP {ip}")
    return event


def send_telegram_notification(message):
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
            current_app.logger.exception("Falha ao enviar notificação Telegram")


def auto_ban(ip, reason, user_agent=""):
    if not IPBanido.query.filter_by(ip=ip).first():
        db.session.add(IPBanido(ip=ip))
        db.session.commit()
    log_security_event(ip, "auto_ban", reason, "critical", user_agent)


def recent_login_failures(ip, minutes=15):
    since = datetime.utcnow() - timedelta(minutes=minutes)
    return SecurityEvent.query.filter(
        SecurityEvent.ip == ip,
        SecurityEvent.event_type == "login_failed",
        SecurityEvent.created_at >= since,
    ).count()


def send_alert(message):
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")
    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")

    if telegram_token and telegram_chat:
        try:
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": telegram_chat, "text": message},
                timeout=4,
            )
        except Exception:
            current_app.logger.exception("Falha ao enviar alerta Telegram")

    if discord_webhook:
        try:
            requests.post(discord_webhook, json={"content": message}, timeout=4)
        except Exception:
            current_app.logger.exception("Falha ao enviar alerta Discord")


def generate_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def _totp(secret, interval=None):
    if interval is None:
        interval = int(time.time() // 30)
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = struct.pack(">Q", interval)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1000000:06d}"


def verify_totp(secret, code):
    if not secret or not code:
        return False
    clean = str(code).strip().replace(" ", "")
    return any(hmac.compare_digest(_totp(secret, int(time.time() // 30) + drift), clean) for drift in (-1, 0, 1))


def otpauth_uri(username, secret):
    issuer = "EducaLivre"
    return f"otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def is_malicious_path(path):
    lower = (path or "").lower()
    if lower.startswith("/admin") or lower.startswith("/api") or lower.startswith("/login") or lower == "/" or lower.startswith("/c/"):
        return False
    return any(marker in lower for marker in MALICIOUS_PATHS)


def is_honeypot_filled(form_data):
    return bool(form_data.get(ADMIN_HONEYPOT_FIELD))


def check_admin_ip_whitelist(ip):
    whitelist = os.environ.get("ADMIN_IP_WHITELIST", "")
    if not whitelist:
        return True
    allowed = {i.strip() for i in whitelist.split(",") if i.strip()}
    return ip in allowed


def validate_password(password):
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    if not any(c.isupper() for c in password):
        return False, "Senha deve ter pelo menos 1 letra maiuscula"
    if not any(c.islower() for c in password):
        return False, "Senha deve ter pelo menos 1 letra minuscula"
    if not any(c.isdigit() for c in password):
        return False, "Senha deve ter pelo menos 1 numero"
    return True, ""


def regenerate_session():
    from flask import session as sess
    sess.clear()


def record_access(request, geo):
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    event = AccessEvent(
        ip=ip,
        path=request.path[:300],
        method=request.method,
        user_agent=user_agent[:500],
        country=geo.get("country"),
        city=geo.get("city"),
        provider=geo.get("provider"),
        latitude=geo.get("latitude"),
        longitude=geo.get("longitude"),
        is_bot=is_bot_user_agent(user_agent),
        is_vpn=is_probable_vpn(geo.get("provider")),
        is_tor=is_tor_ip(ip),
    )
    db.session.add(event)
    db.session.commit()
    return event
