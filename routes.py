import os
import platform
import shlex
import shutil
from datetime import datetime
from urllib.parse import urlparse

import psutil
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, abort, current_app, jsonify, render_template, redirect, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from core.models import AccessEvent, Config, Curso, IPBanido, LogAcesso, SecurityEvent, User
from core import db
from services.analytics import analytics_snapshot, recommend_courses

from services.backup import cleanup_after_backup, send_backup_to_telegram
from services.crawler import check_broken_links, crawl_free_courses
from services.geoip import lookup_ip
from services.lockdown import (
    auto_lockdown_check,
    is_locked_down,
    lockdown_status,
    toggle_lockdown,
    traffic_summary,
)
from services.security import (
    ADMIN_HONEYPOT_FIELD,
    auto_ban,
    check_admin_ip_whitelist,
    generate_totp_secret,
    get_client_ip,
    is_bot_user_agent,
    is_honeypot_filled,
    is_malicious_path,
    is_probable_vpn,
    is_tor_ip,
    log_security_event,
    otpauth_uri,
    recent_login_failures,
    record_access,
    regenerate_session,
    send_telegram_notification,
    validate_password,
    verify_totp,
)

admin_bp = Blueprint("admin_bp", __name__)


oauth = OAuth()


def _google_config():
    try:
        from config import Config as AppConfig
    except Exception:
        AppConfig = None

    client_id = os.environ.get("GOOGLE_CLIENT_ID") or (getattr(AppConfig, "GOOGLE_CLIENT_ID", "") if AppConfig else "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or (getattr(AppConfig, "GOOGLE_CLIENT_SECRET", "") if AppConfig else "")
    return client_id, client_secret


def _site_logged_in():
    return bool(session.get("site_user_email"))


def init_oauth(app):
    client_id, client_secret = _google_config()
    if not client_id or not client_secret:
        app.logger.warning("Google OAuth não configurado. Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET.")
        return None

    oauth.init_app(app)
    try:
        google = oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            access_token_url="https://oauth2.googleapis.com/token",
            authorize_url="https://accounts.google.com/o/oauth2/auth",
            api_base_url="https://www.googleapis.com/oauth2/v1/",
            client_kwargs={"scope": "openid email profile"},
        )
        return google
    except Exception as e:
        app.logger.warning(f"Falha ao registrar Google OAuth: {e}")
        return None


def _csrf_valid():
    expected = session.get("_csrf_token")
    received = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
    return expected and received and expected == received


@admin_bp.before_app_request
def security_gate():
    if request.endpoint == "static" or request.path.startswith("/socket.io/"):
        return None
    ip = get_client_ip(request)
    ua = request.headers.get("User-Agent", "")

    if is_malicious_path(request.path):
        log_security_event(ip, "malicious_path", f"Path malicioso detectado: {request.path}", "critical", ua)
        auto_ban(ip, f"Path malicioso: {request.path}", ua)
        abort(403)

    if is_honeypot_filled(request.form):
        log_security_event(ip, "honeypot", "Honeypot preenchido - bot detectado", "critical", ua)
        auto_ban(ip, "Honeypot preenchido por bot", ua)
        return "OK", 200

    if IPBanido.query.filter_by(ip=ip).first():
        abort(403)

    if not check_admin_ip_whitelist(ip) and not request.path.startswith("/api/"):
        log_security_event(ip, "admin_ip_blocked", f"IP {ip} nao autorizado para admin", "warning", ua)
        if request.path.startswith("/admin/"):
            abort(403)

    if is_locked_down(ip) and ip not in _whitelist_set():
        log_security_event(ip, "lockdown_blocked", f"Bloqueado pelo lockdown em {request.path}", "warning", ua)
        if request.path.startswith("/api/"):
            return jsonify({"error": "lockdown", "message": "Sistema em lockdown. Tente novamente mais tarde."}), 503
        abort(503)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.path.startswith("/api/"):
        if request.path not in {"/admin/login", "/login/google", "/login", "/authorize", "/admin/terminal"}:
            if not _csrf_valid():
                log_security_event(ip, "csrf_failed", f"CSRF inválido em {request.path}", "warning", ua)
                abort(400)
    return None


def _whitelist_set():
    import os
    raw = os.environ.get("LOCKDOWN_WHITELIST", "")
    return {ip.strip() for ip in raw.split(",") if ip.strip()}


@admin_bp.after_app_request
def audit_access(response):
    if request.endpoint == "static" or request.path.startswith("/socket.io/"):
        return response
    try:
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        geo = lookup_ip(ip)
        event = record_access(request, geo)
        suspicious = []
        if event.is_bot:
            suspicious.append("bot")
        if event.is_vpn:
            suspicious.append("vpn")
        if event.is_tor:
            suspicious.append("tor")
        if suspicious:
            log_security_event(ip, "suspicious_traffic", f"Detecção automática: {', '.join(suspicious)}", "warning", user_agent)
        if event.is_tor:
            auto_ban(ip, "IP TOR detectado automaticamente", user_agent)
    except Exception:
        current_app.logger.exception("Falha ao auditar acesso")
    return response


PLATFORM_COLORS = {
    "bradesco": ("#cc092f", "#fff1f3"),
    "fgv": ("#00529b", "#eff6ff"),
    "senai": ("#005ca9", "#eff6ff"),
    "sebrae": ("#005eb8", "#eef7ff"),
    "kultivi": ("#f97316", "#fff7ed"),
    "gov": ("#16a34a", "#f0fdf4"),
    "alura": ("#6d28d9", "#f5f3ff"),
    "fiap": ("#ed145b", "#fff1f6"),
    "senado": ("#15803d", "#f0fdf4"),
    "una-sus": ("#0891b2", "#ecfeff"),
    "harvard": ("#a51c30", "#fff1f2"),
    "microsoft": ("#2563eb", "#eff6ff"),
    "google": ("#1a73e8", "#eff6ff"),
    "tryhackme": ("#dc2626", "#fef2f2"),
    "portswigger": ("#f97316", "#fff7ed"),
    "cisco": ("#0ea5e9", "#f0f9ff"),
    "freecodecamp": ("#0f172a", "#f8fafc"),
    "aws": ("#ff9900", "#fff7ed"),
    "linux": ("#111827", "#f8fafc"),
    "github": ("#24292f", "#f8fafc"),
}


TRUSTED_KEYS = {
    "bradesco", "fgv", "senai", "sebrae", "gov", "senado", "una-sus",
    "harvard", "microsoft", "google", "cisco", "freecodecamp", "aws",
    "linux", "github", "edx", "coursera", "khan", "linkedin",
}

PAID_KEYS = {"udemy", "alura", "hotmart", "eduzz", "kiwify", "domestika", "skillshare", "linkedin"}
LOW_COST_KEYS = {"coursera", "edx", "senai", "udemy", "domestika"}


def _split_tags(value):
    if not value:
        return []
    for separator in [";", "|", "\n"]:
        value = value.replace(separator, ",")
    return [item.strip() for item in value.split(",") if item.strip()]


def _course_visual(curso):
    domain = urlparse(curso.link_afiliado or "").netloc.replace("www.", "")
    name = (curso.nome or "").lower()
    color = "#2563eb"
    surface = "#eff6ff"
    matched_key = ""

    for key, values in PLATFORM_COLORS.items():
        if key in name or key in domain:
            color, surface = values
            matched_key = key
            break

    words = [word for word in (curso.nome or "Curso").replace("(", " ").split() if word]
    initials = "".join(word[0] for word in words[:2]).upper()
    searchable = f"{name} {domain}"
    key = matched_key or searchable
    if any(item in key for item in PAID_KEYS):
        price_category = "pago"
        price_label = "Pago / assinatura"
    elif any(item in key for item in LOW_COST_KEYS):
        price_category = "barato"
        price_label = "Barato / desconto"
    else:
        price_category = "gratuito"
        price_label = "Gratuito"

    trusted = any(item in key for item in TRUSTED_KEYS)
    areas = _split_tags(curso.areas) or ["Educação", "Carreira"]
    examples = _split_tags(curso.exemplos) or ["Cursos online", "Certificado", "Desenvolvimento"]

    curso.logo_domain = domain
    curso.logo_url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}" if domain else ""
    curso.logo_initials = initials[:3] or "ED"
    curso.brand_color = color
    curso.brand_surface = surface
    curso.price_category = price_category
    curso.price_label = price_label
    curso.trusted_label = "Confiável" if trusted else "Popular"
    curso.trusted = trusted
    curso.cert_label = curso.certificacao or "Certificado conforme regras da plataforma"
    curso.confidence_label = curso.confiabilidade or ("Instituição reconhecida" if trusted else "Avalie reputação e detalhes antes de comprar")
    curso.areas_list = areas[:5]
    curso.examples_list = examples[:5]
    curso.rating = "4." + str((curso.id % 5) + 5)
    return curso


COMMANDS = {
    "help": ["help [comando]", "Mostra esta ajuda ou detalhes de um comando"],
    "status": ["status", "CPU, RAM, disco, cursos, bans, usuario logado"],
    "geoip": ["geoip <ip>", "Localiza um IP: pais, cidade, provedor, mapa"],
    "logs": ["logs", "Ultimas 80 linhas do log de acesso"],
    "backup": ["backup create|telegram|daily", "Criar backup local, enviar pro Telegram, ver config"],
    "cleanup": ["cleanup old", "Remove registros antigos (acessos, eventos)"],
    "users": ["users online", "Mostra usuarios online"],
    "ban": ["ban ip <endereco>", "Bane um IP manualmente"],
    "unban": ["unban ip <endereco>", "Remove banimento de um IP"],
    "maintenance": ["maintenance on|off", "Ativa/desativa modo manutencao"],
    "crawler": ["crawler start|stop|run", "Controla ou executa o crawler"],
    "links": ["links check", "Verifica links quebrados dos cursos"],
    "analytics": ["analytics", "DAU, MAU, retencao, top cursos"],
    "security": ["security events", "Ultimos 20 eventos de seguranca"],
    "lockdown": ["lockdown on|off|status|disabled", "Controla o lockdown do sistema"],
    "whitelist": ["whitelist add|remove|list <ip>", "Gerencia IPs sempre permitidos"],
}


def _terminal_help(cmd=None):
    if cmd:
        entry = COMMANDS.get(cmd)
        if entry:
            return f"{entry[0]}\n  {entry[1]}"
        return f"Comando desconhecido: {cmd}. Digite 'help' para a lista completa."

    seen = set()
    groups = [
        ("SISTEMA", ["status", "logs", "users online"]),
        ("BACKUP", ["backup", "cleanup"]),
        ("SEGURANCA", ["ban", "unban", "lockdown", "whitelist", "security"]),
        ("REDE", ["geoip"]),
        ("CRAWLER", ["crawler", "links"]),
        ("ANALYTICS", ["analytics"]),
        ("MANUTENCAO", ["maintenance"]),
        ("AJUDA", ["help"]),
    ]

    lines = ["\u2554\u2550\u2550\u2550 TERMINAL RADAR ELITE \u2550\u2550\u2550\u2557", ""]
    for group_name, cmds in groups:
        lines.append(f"  \u2502 {group_name}")
        lines.append(f"  \u2502" + "\u2500" * 30)
        for cmd_key in cmds:
            entry = COMMANDS.get(cmd_key)
            if entry and cmd_key not in seen:
                seen.add(cmd_key)
                lines.append(f"  \u2502   {entry[0]:<35} {entry[1]}")
        lines.append("")
    lines.append("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    return "\n".join(lines)


def _set_config(chave, valor):
    item = Config.query.filter_by(chave=chave).first()
    if item:
        item.valor = valor
    else:
        db.session.add(Config(chave=chave, valor=valor))
    db.session.commit()


def _run_internal_command(command):
    parts = shlex.split(command)
    if not parts:
        return "Nenhum comando recebido"

    action = parts[0].lower()

    if action == "help":
        if len(parts) >= 2:
            return _terminal_help(parts[1].lower())
        return _terminal_help()

    if action == "status":
        cursos = db.session.scalar(db.select(db.func.count(Curso.id))) or 0
        bans = db.session.scalar(db.select(db.func.count(IPBanido.id))) or 0
        return "\n".join([
            "Sistema operacional: " + platform.platform(),
            f"CPU: {psutil.cpu_percent()}%",
            f"RAM: {psutil.virtual_memory().percent}%",
            f"Disco: {psutil.disk_usage('/').percent}%",
            f"Cursos cadastrados: {cursos}",
            f"IPs banidos: {bans}",
            f"Usuário atual: {current_user.username}",
        ])

    if action == "logs":
        log_path = os.path.join(current_app.root_path, "acessos.log")
        if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
            return "Nenhum log disponível em acessos.log"
        with open(log_path, "r", encoding="utf-8", errors="replace") as log_file:
            return "".join(log_file.readlines()[-80:])

    if action == "backup" and len(parts) == 2 and parts[1].lower() == "create":
        source = current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
        backup_dir = os.path.join(current_app.root_path, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        filename = "database-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db"
        target = os.path.join(backup_dir, filename)
        shutil.copy2(source, target)
        return f"Backup criado: backups/{filename}"

    if action == "backup" and len(parts) == 2 and parts[1].lower() == "telegram":
        database_file, report_file, summary = send_backup_to_telegram(current_app)
        cleanup = summary.get("cleanup", {})
        return "\n".join([
            "Backup enviado ao Telegram com sucesso.",
            f"Banco: {database_file}",
            f"Relatorio: {report_file}",
            f"Cursos: {summary['cursos']}",
            f"Cliques: {summary['cliques']}",
            f"Acessos: {summary['acessos']}",
            f"Limpeza: {cleanup.get('removed', 0)} registro(s) antigo(s) removido(s)",
        ])

    if action == "backup" and len(parts) == 2 and parts[1].lower() == "daily":
        return "\n".join([
            f"Backup diario: {'ativo' if os.environ.get('BACKUP_DAILY_ENABLED', '1') == '1' else 'desativado'}",
            f"Hora configurada: {os.environ.get('BACKUP_DAILY_HOUR', '3')}:00",
            "Use 'backup telegram' para enviar um backup agora.",
        ])

    if action == "cleanup" and len(parts) == 2 and parts[1].lower() == "old":
        cleanup = cleanup_after_backup()
        if not cleanup.get("enabled"):
            return "Limpeza automática está desativada por CLEANUP_AFTER_BACKUP=0."
        return "\n".join([
            "Limpeza concluída.",
            f"Retenção: {cleanup['retention_days']} dia(s)",
            f"Acessos gerais removidos: {cleanup['access_events_removed']}",
            f"Acessos a cursos removidos: {cleanup['course_access_removed']}",
            f"Eventos de segurança removidos: {cleanup['security_events_removed']}",
            f"Total removido: {cleanup['removed']}",
        ])

    if action == "users" and len(parts) == 2 and parts[1].lower() == "online":
        return "Usuários online: 1 sessão administrativa ativa"

    if action == "ban" and len(parts) == 3 and parts[1].lower() == "ip":
        ip = parts[2]
        if not IPBanido.query.filter_by(ip=ip).first():
            db.session.add(IPBanido(ip=ip))
            db.session.commit()
        return f"IP banido: {ip}"

    if action == "unban" and len(parts) == 3 and parts[1].lower() == "ip":
        ip = parts[2]
        item = IPBanido.query.filter_by(ip=ip).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return f"IP removido da blacklist: {ip}"
        return f"IP não estava banido: {ip}"

    if action == "maintenance" and len(parts) == 2 and parts[1].lower() in {"on", "off"}:
        _set_config("maintenance_mode", parts[1].lower())
        return f"Modo manutenção: {parts[1].lower()}"

    if action == "crawler" and len(parts) == 2 and parts[1].lower() in {"start", "stop"}:
        _set_config("crawler_state", parts[1].lower())
        return f"Crawler marcado como: {parts[1].lower()}"

    if action == "crawler" and len(parts) == 2 and parts[1].lower() == "run":
        created, found = crawl_free_courses()
        return f"Crawler finalizado. Novos cursos: {created}\n" + "\n".join(found[:20])

    if action == "links" and len(parts) == 2 and parts[1].lower() == "check":
        checked, broken = check_broken_links()
        lines = [f"Links verificados: {checked}", f"Problemas encontrados: {len(broken)}"]
        lines.extend([f"#{item[0]} {item[1]} -> {item[2]}" for item in broken[:30]])
        return "\n".join(lines)

    if action == "analytics":
        data = analytics_snapshot()
        return "\n".join([
            f"DAU: {data['dau']}",
            f"MAU: {data['mau']}",
            f"Retenção estimada: {data['retention']}%",
            "Top cursos:",
            *[f"- {item['name']}: {item['clicks']} clique(s)" for item in data["top_courses"][:8]],
        ])

    if action == "geoip" and len(parts) == 2:
        ip = parts[1]
        geo = lookup_ip(ip)
        return "\n".join([
            f"IP: {ip}",
            f"Pais: {geo.get('country', '?')}",
            f"Cidade: {geo.get('city', '?')}",
            f"Provedor: {geo.get('provider', '?')}",
            f"Latitude: {geo.get('latitude', '?')}",
            f"Longitude: {geo.get('longitude', '?')}",
            f"Mapa: https://www.google.com/maps?q={geo.get('latitude', 0)},{geo.get('longitude', 0)}",
        ])

    if action == "security" and len(parts) == 2 and parts[1].lower() == "events":
        events = SecurityEvent.query.order_by(SecurityEvent.created_at.desc()).limit(20).all()
        if not events:
            return "Nenhum evento de segurança registrado."
        return "\n".join([f"[{e.created_at}] {e.severity} {e.event_type} {e.ip}: {e.message}" for e in events])

    if action == "lockdown" and len(parts) == 2:
        sub = parts[1].lower()
        if sub == "status":
            st = lockdown_status()
            return "\n".join([
                f"Lockdown: {st['mode']}",
                f"Ativo: {'SIM' if st['active'] else 'NAO'}",
                f"Automático: {'SIM' if st['auto'] else 'NAO'}",
                f"Manual: {'SIM' if st['manual'] else 'NAO'}",
                f"IPs agora: {st['ips_now']} (limite: {st['threshold']}/{st['window']}s)",
                f"Whitelist: {', '.join(st['whitelist']) or 'vazia'}",
            ])
        if sub == "on":
            toggle_lockdown("on")
            return "Lockdown MANUAL ativado."
        if sub == "off":
            toggle_lockdown("off")
            return "Lockdown desativado."
        if sub == "disabled":
            toggle_lockdown("disabled")
            return "Lockdown desabilitado permanentemente."

    if action == "whitelist" and len(parts) == 2 and parts[1].lower() == "list":
        st = lockdown_status()
        wl = st["whitelist"]
        if not wl:
            return "Whitelist vazia."
        return "Whitelist:\n" + "\n".join(f"  {ip}" for ip in wl)

    if action == "whitelist" and len(parts) == 3 and parts[1].lower() == "add":
        ip = parts[2]
        current = os.environ.get("LOCKDOWN_WHITELIST", "")
        all_ips = {i.strip() for i in current.split(",") if i.strip()}
        if ip in all_ips:
            return f"IP {ip} já está na whitelist."
        all_ips.add(ip)
        os.environ["LOCKDOWN_WHITELIST"] = ",".join(sorted(all_ips))
        log_security_event(ip, "whitelist_add", f"IP adicionado à whitelist", "info", "")
        return f"IP {ip} adicionado à whitelist."

    if action == "whitelist" and len(parts) == 3 and parts[1].lower() == "remove":
        ip = parts[2]
        current = os.environ.get("LOCKDOWN_WHITELIST", "")
        all_ips = {i.strip() for i in current.split(",") if i.strip()}
        if ip not in all_ips:
            return f"IP {ip} não está na whitelist."
        all_ips.discard(ip)
        os.environ["LOCKDOWN_WHITELIST"] = ",".join(sorted(all_ips))
        log_security_event(ip, "whitelist_remove", f"IP removido da whitelist", "info", "")
        return f"IP {ip} removido da whitelist."

    return "Comando não permitido. Digite 'help' para ver os comandos disponíveis."


@admin_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 24
    q = request.args.get("q", "").strip()
    area = request.args.get("area", "").strip()
    preco = request.args.get("preco", "").strip()
    nivel = request.args.get("nivel", "").strip()
    saved = request.args.get("saved", "").strip()

    if saved == "1" and _site_logged_in():
        user = User.query.filter_by(username=session["site_user_email"]).first()
        if user and user.favoritos:
            favorito_ids = {c.id for c in user.favoritos}
            query = db.select(Curso).where(Curso.id.in_(favorito_ids))
        else:
            query = db.select(Curso).where(Curso.id == -1)
        if q:
            like = f"%{q}%"
            query = query.where(
                db.or_(Curso.nome.ilike(like), Curso.descricao.ilike(like), Curso.areas.ilike(like))
            )
        query = query.order_by(Curso.cliques.desc())
        pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
        cursos = [_course_visual(curso) for curso in pagination.items]
    else:
        query = db.select(Curso).where(Curso.ativo.is_(True))
        if q:
            like = f"%{q}%"
            query = query.where(
                db.or_(Curso.nome.ilike(like), Curso.descricao.ilike(like), Curso.areas.ilike(like))
            )
        if area:
            query = query.where(Curso.areas.ilike(f"%{area}%"))
        if preco:
            query = query.where(Curso.preco_tipo == preco)
        if nivel:
            query = query.where(Curso.nivel == nivel)
        query = query.order_by(Curso.cliques.desc())
        pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
        cursos = [_course_visual(curso) for curso in pagination.items]

    areas_list = sorted(set(
        a.strip() for c in Curso.query.with_entities(Curso.areas).all()
        for a in (c.areas or "").split(",") if a.strip()
    ))

    favoritados = set()
    if _site_logged_in():
        user = User.query.filter_by(username=session["site_user_email"]).first()
        if user:
            favoritados = {c.id for c in user.favoritos}

    return render_template("index.html",
        cursos=cursos, pagination=pagination,
        q=q, area=area, preco=preco, nivel=nivel,
        areas=areas_list, favoritados=favoritados, saved=saved)

@admin_bp.route("/admin/terminal", methods=["POST"])
@login_required
def terminal_command():
    data = request.get_json(silent=True) or {}
    comando = (data.get("comando") or "").strip()
    if not comando:
        return jsonify({"output": "Nenhum comando recebido"}), 400
    try:
        return jsonify({"output": _run_internal_command(comando)})
    except Exception as e:
        return jsonify({"output": str(e)}), 500

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    from app import bcrypt
    if request.method == "POST":
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")

        if is_honeypot_filled(request.form):
            log_security_event(ip, "honeypot_login", "Bot detectado no login admin", "critical", user_agent)
            return "OK", 200

        limiter_ok = getattr(request, 'max_cost', None) is not None
        try:
            from services.analytics import check_rate_limit
        except ImportError:
            pass

        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get("password")):
            if user.otp_enabled and not verify_totp(user.otp_secret, request.form.get("otp_code")):
                log_security_event(ip, "login_2fa_failed", f"2FA inválido para {user.username}", "warning", user_agent)
                return render_template("login.html", erro="Código 2FA inválido.")
            login_user(user)
            session.permanent = True
            session["_csrf_token"] = os.urandom(24).hex()
            session["_login_time"] = datetime.now().isoformat(timespec="seconds")
            log_security_event(ip, "login_success", f"Login administrativo: {user.username}", "info", user_agent)
            if user.otp_enabled:
                session["_2fa_verified"] = True
            return redirect(url_for("admin_bp.admin_dashboard"))
        log_security_event(ip, "login_failed", "Falha de login administrativo", "warning", user_agent)
        if recent_login_failures(ip) >= int(os.environ.get("BRUTE_FORCE_LIMIT", "5")):
            auto_ban(ip, "Limite de falhas de login excedido", user_agent)
            return "IP bloqueado por brute force", 403
        return render_template("login.html", erro="Usuário, senha ou código inválido.")
    return render_template("login.html")

@admin_bp.route("/logout")
@login_required
def logout():
    log_security_event(get_client_ip(request), "logout", "Logout administrativo", "info", request.headers.get("User-Agent", ""))
    logout_user()
    return redirect(url_for("admin_bp.admin_login"))


@admin_bp.route("/login", methods=["GET", "POST"])
def public_login():
    if _site_logged_in():
        return redirect(url_for("admin_bp.index"))
    client_id, client_secret = _google_config()
    google_ready = bool(client_id and client_secret)
    google_url = url_for("admin_bp.public_google_login")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            return render_template("site_login.html", erro="Preencha email e senha.", google_ready=google_ready, google_login_url=google_url)
        from app import bcrypt
        user = User.query.filter_by(username=email).first()
        if user:
            if not bcrypt.check_password_hash(user.password, password):
                return render_template("site_login.html", erro="Senha incorreta.", google_ready=google_ready, google_login_url=google_url)
        else:
            pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(username=email, password=pw_hash)
            db.session.add(user)
            db.session.commit()
            send_telegram_notification(
                f"\U0001f4a5 NOVO CADASTRO\n"
                f"Email: {email}\n"
                f"IP: {get_client_ip(request)}\n"
                f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
        session.permanent = True
        session["site_user_email"] = user.username
        session["site_user_name"] = user.username.split("@")[0]
        session["site_user_logged_at"] = datetime.now().isoformat(timespec="seconds")
        return redirect(url_for("admin_bp.index"))

    return render_template("site_login.html", google_ready=google_ready, google_login_url=google_url)


@admin_bp.route("/login/google")
def public_google_login():
    client_id, client_secret = _google_config()
    if not client_id or not client_secret:
        return redirect(url_for("admin_bp.public_login"))
    redirect_uri = url_for("admin_bp.public_google_authorize", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@admin_bp.route("/authorize")
def public_google_authorize():
    if "google" not in getattr(oauth, "_clients", {}):
        return redirect("/")
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")
        if not user_info:
            user_info = oauth.google.parse_id_token(token)
        if user_info:
            session.permanent = True
            session["site_user_email"] = user_info.get("email")
            session["site_user_name"] = (user_info.get("email") or "").split("@")[0]
            session["site_user_picture"] = user_info.get("picture")
            session["site_user_logged_at"] = datetime.now().isoformat(timespec="seconds")
            log_security_event(
                get_client_ip(request),
                "public_google_login",
                f"Login Google do site: {user_info.get('email')}",
                "info",
                request.headers.get("User-Agent", ""),
            )
            return redirect(url_for("admin_bp.index"))
    except Exception:
        current_app.logger.exception("Falha no login Google publico")
    return redirect(url_for("admin_bp.public_login"))


@admin_bp.route("/sair")
def public_logout():
    session.pop("site_user_email", None)
    session.pop("site_user_name", None)
    session.pop("site_user_picture", None)
    session.pop("site_user_logged_at", None)
    return redirect(url_for("admin_bp.public_login"))


@admin_bp.route("/admin/2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if not current_user.otp_secret:
        current_user.otp_secret = generate_totp_secret()
        db.session.commit()

    if request.method == "POST":
        code = request.form.get("otp_code")
        if verify_totp(current_user.otp_secret, code):
            current_user.otp_enabled = True
            db.session.commit()
            log_security_event(get_client_ip(request), "2fa_enabled", f"2FA ativado para {current_user.username}", "info", request.headers.get("User-Agent", ""))
            return redirect(url_for("admin_bp.admin_dashboard"))
        return render_template("2fa.html", secret=current_user.otp_secret, uri=otpauth_uri(current_user.username, current_user.otp_secret), erro="Código inválido.")

    return render_template("2fa.html", secret=current_user.otp_secret, uri=otpauth_uri(current_user.username, current_user.otp_secret))

@admin_bp.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.otp_enabled and not session.get("_2fa_verified"):
        return redirect(url_for("admin_bp.admin_login"))
    cursos = db.session.execute(db.select(Curso).order_by(Curso.cliques.desc())).scalars().all()
    bans = IPBanido.query.all()
    ld_status = lockdown_status()
    return render_template("admin.html", cursos=cursos, bans=bans, lockdown_status=ld_status)

@admin_bp.route("/c/<int:id>")
def redirecionar_curso(id):
    import app
    curso = db.session.get(Curso, id)
    if not curso: return "404", 404
    curso.cliques += 1
    ip = get_client_ip(request)
    geo = lookup_ip(ip)
    db.session.add(LogAcesso(
        ip=ip,
        data=datetime.now().isoformat(timespec="seconds"),
        curso_id=curso.id,
    ))
    db.session.commit()
    try:
        user_agent = request.headers.get("User-Agent", "")
        log_security_event(
            ip,
            "course_access",
            f"Acesso ao curso #{curso.id} {curso.nome} | {geo.get('city')}/{geo.get('country')} | {geo.get('provider')}",
            "info",
            user_agent,
        )
        app.socketio.emit('novo_clique', {
            'curso': curso.nome, 'ip': ip,
            'hora': datetime.now().strftime("%H:%M:%S"),
            'country': geo.get("country"),
            'city': geo.get("city"),
            'provider': geo.get("provider"),
            'lat': geo.get("latitude"),
            'lng': geo.get("longitude"),
        })
    except Exception:
        current_app.logger.exception("Falha ao registrar acesso de curso")
    return redirect(curso.link_afiliado)


@admin_bp.route("/api/favoritar/<int:id>", methods=["POST"])
def api_favoritar(id):
    if not _site_logged_in():
        return jsonify({"success": False, "error": "login_required"}), 401
    email = session["site_user_email"]
    user = User.query.filter_by(username=email).first()
    if not user:
        user = User(username=email, password="")
        db.session.add(user)
        db.session.commit()
    curso = db.session.get(Curso, id)
    if not curso:
        return jsonify({"success": False, "error": "not_found"}), 404
    if curso in user.favoritos:
        user.favoritos.remove(curso)
        db.session.commit()
        return jsonify({"success": True, "action": "removed"})
    user.favoritos.append(curso)
    db.session.commit()
    return jsonify({"success": True, "action": "added"})

@admin_bp.route("/api/check_2fa")
def api_check_2fa():
    user = User.query.first()
    return jsonify({"otp_enabled": bool(user and user.otp_enabled)})

@admin_bp.route("/api/analytics")
@login_required
def api_analytics():
    return jsonify(analytics_snapshot())


@admin_bp.route("/api/security/events")
@login_required
def api_security_events():
    events = SecurityEvent.query.order_by(SecurityEvent.created_at.desc()).limit(50).all()
    return jsonify([
        {
            "ip": event.ip,
            "type": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ])


@admin_bp.route("/api/traffic")
@login_required
def api_traffic():
    events = AccessEvent.query.order_by(AccessEvent.created_at.desc()).limit(100).all()
    return jsonify([
        {
            "ip": event.ip,
            "path": event.path,
            "country": event.country,
            "city": event.city,
            "provider": event.provider,
            "lat": event.latitude,
            "lng": event.longitude,
            "is_bot": event.is_bot,
            "is_vpn": event.is_vpn,
            "is_tor": event.is_tor,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ])


@admin_bp.route("/api/traffic/summary")
@login_required
def api_traffic_summary():
    minutes = request.args.get("minutes", 5, type=int)
    return jsonify(traffic_summary(minutes=minutes))


@admin_bp.route("/api/lockdown/status")
@login_required
def api_lockdown_status():
    return jsonify(lockdown_status())


@admin_bp.route("/api/lockdown/toggle", methods=["POST"])
@login_required
def api_lockdown_toggle():
    data = request.get_json(silent=True) or {}
    state = data.get("state", "")
    if state not in ("on", "off", "disabled"):
        return jsonify({"success": False, "error": "Estado inválido. Use: on, off, disabled"}), 400
    ok = toggle_lockdown(state)
    return jsonify({"success": ok, "status": lockdown_status()})


@admin_bp.route("/api/whitelist/add", methods=["POST"])
@login_required
def api_whitelist_add():
    data = request.get_json(silent=True) or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"success": False, "error": "IP obrigatório"}), 400
    current = os.environ.get("LOCKDOWN_WHITELIST", "")
    all_ips = {i.strip() for i in current.split(",") if i.strip()}
    if ip in all_ips:
        return jsonify({"success": True, "message": f"IP {ip} já está na whitelist"})
    all_ips.add(ip)
    os.environ["LOCKDOWN_WHITELIST"] = ",".join(sorted(all_ips))
    log_security_event(ip, "whitelist_add", f"IP adicionado à whitelist via painel", "info", "")
    return jsonify({"success": True, "message": f"IP {ip} adicionado à whitelist"})


@admin_bp.route("/api/whitelist/remove", methods=["POST"])
@login_required
def api_whitelist_remove():
    data = request.get_json(silent=True) or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"success": False, "error": "IP obrigatório"}), 400
    current = os.environ.get("LOCKDOWN_WHITELIST", "")
    all_ips = {i.strip() for i in current.split(",") if i.strip()}
    if ip not in all_ips:
        return jsonify({"success": True, "message": f"IP {ip} não está na whitelist"})
    all_ips.discard(ip)
    os.environ["LOCKDOWN_WHITELIST"] = ",".join(sorted(all_ips))
    log_security_event(ip, "whitelist_remove", f"IP removido da whitelist via painel", "info", "")
    return jsonify({"success": True, "message": f"IP {ip} removido da whitelist"})


@admin_bp.route("/api/ban", methods=["POST"])
@login_required
def api_ban():
    data = request.get_json(silent=True) or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"success": False, "error": "IP obrigatório"}), 400
    if not IPBanido.query.filter_by(ip=ip).first():
        db.session.add(IPBanido(ip=ip))
        db.session.commit()
    log_security_event(ip, "manual_ban", f"IP banido manualmente pelo admin", "warning", "")
    return jsonify({"success": True, "message": f"IP {ip} banido"})


@admin_bp.route("/api/unban", methods=["POST"])
@login_required
def api_unban():
    data = request.get_json(silent=True) or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"success": False, "error": "IP obrigatório"}), 400
    item = IPBanido.query.filter_by(ip=ip).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        log_security_event(ip, "manual_unban", f"IP desbanido manualmente pelo admin", "info", "")
        return jsonify({"success": True, "message": f"IP {ip} desbanido"})
    return jsonify({"success": True, "message": f"IP {ip} não estava banido"})


@admin_bp.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    return jsonify(recommend_courses(query, limit=12))


@admin_bp.route("/api/recommendations")
def api_recommendations():
    query = request.args.get("q", "")
    return jsonify(recommend_courses(query, limit=8))


@admin_bp.route("/admin/crawler", methods=["GET", "POST"])
@login_required
def admin_crawler():
    from services.crawler import seed_cursos, check_broken_links, crawl_free_courses

    resultado = None
    erro = None
    acao = request.form.get("acao") if request.method == "POST" else request.args.get("acao")

    if acao == "seed":
        try:
            qtd = int(request.form.get("quantidade", 200))
            c = seed_cursos(qtd)
            resultado = f"Seed concluido: {c} cursos adicionados"
        except Exception as e:
            erro = str(e)
    elif acao == "check_links":
        try:
            lim = int(request.form.get("limite", 100))
            checked, broken = check_broken_links(limite=lim, desativar=True)
            resultado = f"Links verificados: {checked}, quebrados desativados: {broken}"
        except Exception as e:
            erro = str(e)
    elif acao == "crawl":
        try:
            c = crawl_free_courses(limite=50)
            resultado = f"Crawler encontrou {c} novos cursos"
        except Exception as e:
            erro = str(e)

    from core.models import Curso
    total_ativos = Curso.query.filter_by(ativo=True).count()
    total_inativos = Curso.query.filter_by(ativo=False).count()
    return render_template("admin_crawler.html",
        resultado=resultado, erro=erro,
        total_ativos=total_ativos,
        total_inativos=total_inativos,
        total=total_ativos + total_inativos,
    )


@admin_bp.route("/api/rate/<int:id>/<int:voto>")
def api_rating(id, voto):
    if voto < 1 or voto > 5:
        return jsonify({"success": False, "error": "Nota invalida"})
    curso = db.session.get(Curso, id)
    if not curso:
        return jsonify({"success": False, "error": "Curso nao encontrado"})
    curso.rating = float(voto)
    db.session.commit()
    return jsonify({"success": True, "rating": voto})


@admin_bp.route("/api/avatar", methods=["POST"])
def api_avatar_upload():
    if not _site_logged_in():
        return jsonify({"success": False, "error": "Nao logado"}), 401
    if "avatar" not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo"})
    f = request.files["avatar"]
    if not f.filename:
        return jsonify({"success": False, "error": "Arquivo vazio"})
    import uuid
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "png"
    if ext not in ("png", "jpg", "jpeg", "gif", "webp"):
        return jsonify({"success": False, "error": "Formato invalido"})
    nome = f"avatar_{uuid.uuid4().hex[:12]}.{ext}"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "avatars", nome)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f.save(path)
    session["site_user_avatar"] = f"/static/avatars/{nome}"
    return jsonify({"success": True, "avatar": session["site_user_avatar"]})
