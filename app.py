import os
import secrets
from datetime import timedelta

from flask import Flask, request, session
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_talisman import Talisman
from core import db
import threading
import time
import psutil

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

basedir = os.path.abspath(os.path.dirname(__file__))
database_path = os.environ.get('DATABASE_PATH', os.path.join(basedir, 'instance', 'database.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + database_path
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '1') == '1'
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = app.config['SESSION_COOKIE_SECURE']
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '0'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), interest-cohort=()'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    return response

db.init_app(app)

import os as _os
_db_dir = _os.path.dirname(database_path)
if _db_dir and not _os.path.exists(_db_dir):
    _os.makedirs(_db_dir, exist_ok=True)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_bp.admin_login'
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[os.environ.get('RATELIMIT_DEFAULT', '300 per hour')],
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
)
socketio = SocketIO(
    app,
    cors_allowed_origins=os.environ.get('SOCKETIO_CORS_ORIGINS', 'https://radar-elite.onrender.com'),
    async_mode='threading',
)
Talisman(
    app,
    force_https=os.environ.get('FORCE_HTTPS', '0') == '1',
    force_https_permanent=True,
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,
    strict_transport_security_include_subdomains=True,
    frame_options='DENY',
    referrer_policy='strict-origin-when-cross-origin',
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com", "https://cdn.jsdelivr.net", "https://unpkg.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com", "https://cdn.jsdelivr.net", "https://unpkg.com"],
        'img-src': ["'self'", "data:", "https://www.google.com", "https://*.gstatic.com", "https://*.tile.openstreetmap.org"],
        'connect-src': ["'self'", "ws:", "wss:"],
        'font-src': ["'self'", "https://cdnjs.cloudflare.com"],
        'form-action': "'self'",
        'base-uri': "'self'",
        'object-src': "'none'",
    },
    content_security_policy_nonce_in=None,
    x_content_type_options='nosniff',
)

from routes import admin_bp, init_oauth
init_oauth(app)
app.register_blueprint(admin_bp)


@app.errorhandler(429)
def rate_limit_handler(error):
    try:
        from flask import request
        from services.security import auto_ban, get_client_ip
        ip = get_client_ip(request)
        auto_ban(ip, "Rate limit excedido automaticamente", request.headers.get("User-Agent", ""))
    except Exception:
        app.logger.exception("Falha ao registrar rate limit")
    return "Muitas requisições. IP bloqueado automaticamente.", 429


@app.errorhandler(500)
def internal_error_handler(error):
    try:
        from flask import request
        from services.security import get_client_ip, log_security_event
        log_security_event(get_client_ip(request), "server_error", str(error), "critical", request.headers.get("User-Agent", ""))
    except Exception:
        app.logger.exception("Falha ao registrar erro crítico")
    return "Erro interno registrado.", 500


def _ensure_schema():
    with app.app_context():
        from sqlalchemy import inspect, text
        from core import models
        db.create_all()
        inspector = inspect(db.engine)
        user_columns = {column['name'] for column in inspector.get_columns('app_user')}
        if 'otp_secret' not in user_columns:
            db.session.execute(text('ALTER TABLE app_user ADD COLUMN otp_secret VARCHAR(64)'))
        if 'otp_enabled' not in user_columns:
            db.session.execute(text('ALTER TABLE app_user ADD COLUMN otp_enabled BOOLEAN DEFAULT false'))
        curso_columns = {column['name'] for column in inspector.get_columns('curso')}
        if 'rating' not in curso_columns:
            db.session.execute(text('ALTER TABLE curso ADD COLUMN rating FLOAT DEFAULT 4.0'))
        db.session.commit()


_ensure_schema()

if os.environ.get("EMERGENCY_UNBAN", "").lower() in ("1", "true", "yes"):
    with app.app_context():
        from core.models import IPBanido
        bans = IPBanido.query.all()
        for b in bans:
            db.session.delete(b)
        db.session.commit()
        app.logger.warning(f"EMERGENCY_UNBAN: {len(bans)} ban(s) removido(s)")

_admin_password_generated = False
with app.app_context():
    from core.models import User, Curso
    from services.crawler import seed_cursos, check_broken_links
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        admin_password = secrets.token_urlsafe(16)
        _admin_password_generated = True
    admin_user = User.query.filter_by(username=admin_username).first()
    if not admin_user:
        old_admin = User.query.filter_by(username="admin").first()
        if old_admin:
            old_admin.username = admin_username
            old_admin.password = bcrypt.generate_password_hash(admin_password).decode("utf-8")
            db.session.commit()
            app.logger.info(f"Admin renomeado de 'admin' para '{admin_username}' com nova senha")
        else:
            pw_hash = bcrypt.generate_password_hash(admin_password).decode("utf-8")
            db.session.add(User(username=admin_username, password=pw_hash))
            db.session.commit()
            app.logger.info(f"Admin criado: {admin_username}")
    else:
        admin_user.password = bcrypt.generate_password_hash(admin_password).decode("utf-8")
        db.session.commit()
        app.logger.info(f"Admin encontrado e senha atualizada: {admin_username}")

    if _admin_password_generated:
        app.logger.warning(f"ADMIN_PASSWORD nao definida. Senha gerada: {admin_password}. Defina ADMIN_PASSWORD no ambiente!")

    total = Curso.query.count()
    if total < 2000:
        app.logger.info(f"Apenas {total} cursos. Populando ate 2000...")
        criados = seed_cursos(2000 - total)
        app.logger.info(f"Seed concluido! +{criados} cursos. Total: {Curso.query.count()}")


@app.context_processor
def inject_csrf_token():
    def csrf_token():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return token
    return {'csrf_token': csrf_token}

@login_manager.user_loader
def load_user(user_id):
    from core.models import User
    return db.session.get(User, int(user_id))

def monitor_system():
    while True:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            socketio.emit('sys_stats', {'cpu': cpu, 'ram': ram, 'disk': disk})
        except Exception:
            pass
        time.sleep(2)

threading.Thread(target=monitor_system, daemon=True).start()

try:
    from services.backup import start_daily_backup_scheduler
    daily_backup_loop = start_daily_backup_scheduler(app)
    if daily_backup_loop:
        threading.Thread(target=daily_backup_loop, daemon=True).start()
except Exception:
    app.logger.exception("Falha ao iniciar agendador de backup diario")

try:
    from services.lockdown import spike_checker_loop
    threading.Thread(target=spike_checker_loop, args=(app,), daemon=True).start()
    app.logger.info("Spike checker iniciado")
except Exception:
    app.logger.exception("Falha ao iniciar spike checker")

def _link_checker_loop():
    while True:
        time.sleep(3600)
        try:
            with app.app_context():
                from services.crawler import check_broken_links
                c, q = check_broken_links(limite=80, desativar=True)
                if q > 0:
                    app.logger.info(f"Link checker: {c} verificados, {q} desativados")
        except Exception:
            app.logger.exception("Falha no link checker")

threading.Thread(target=_link_checker_loop, daemon=True).start()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)
