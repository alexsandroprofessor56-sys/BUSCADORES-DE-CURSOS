import os
import secrets

from flask import Flask, session
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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-change-this-secret-key')

basedir = os.path.abspath(os.path.dirname(__file__))
database_path = os.environ.get('DATABASE_PATH', os.path.join(basedir, 'instance', 'database.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + database_path
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = app.config['SESSION_COOKIE_SECURE']

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
    cors_allowed_origins=os.environ.get('SOCKETIO_CORS_ORIGINS', '*'),
    async_mode='threading',
)
Talisman(
    app,
    force_https=os.environ.get('FORCE_HTTPS', '0') == '1',
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com", "https://cdn.jsdelivr.net", "https://unpkg.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdnjs.cloudflare.com", "https://cdn.jsdelivr.net", "https://unpkg.com"],
        'img-src': ["'self'", "data:", "https://www.google.com", "https://*.gstatic.com", "https://*.tile.openstreetmap.org"],
        'connect-src': ["'self'", "ws:", "wss:"],
        'font-src': ["'self'", "https://cdnjs.cloudflare.com"],
    },
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
        user_columns = {column['name'] for column in inspector.get_columns('user')}
        if 'otp_secret' not in user_columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN otp_secret VARCHAR(64)'))
        if 'otp_enabled' not in user_columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN otp_enabled BOOLEAN DEFAULT 0'))
        db.session.commit()


_ensure_schema()

with app.app_context():
    from core.models import User, Curso
    import random

    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    admin_user = User.query.filter_by(username=admin_username).first()
    if not admin_user:
        pw_hash = bcrypt.generate_password_hash(admin_password).decode("utf-8")
        db.session.add(User(username=admin_username, password=pw_hash))
        db.session.commit()
        app.logger.info(f"Admin criado: {admin_username}")
    else:
        app.logger.info(f"Admin encontrado: {admin_username}")

    if Curso.query.count() == 0:
        app.logger.info("Nenhum curso encontrado. Populando banco...")
        random.seed(42)
        PLATFORMS = [
            ("Fundacao Bradesco", "https://www.ev.org.br/", "gratuito"),
            ("FGV", "https://educacao-executiva.fgv.br/cursos/gratuitos", "gratuito"),
            ("Escola Virtual Gov", "https://www.escolavirtual.gov.br/", "gratuito"),
            ("Sebrae", "https://sebrae.com.br/sites/PortalSebrae/cursosonline", "gratuito"),
            ("Kultivi", "https://kultivi.com/", "gratuito"),
            ("Senai", "https://online.sp.senai.br/cursos-gratuitos", "gratuito"),
            ("Harvard", "https://pll.harvard.edu/catalog/free", "gratuito"),
            ("Microsoft Learn", "https://learn.microsoft.com/", "gratuito"),
            ("Google", "https://skillshop.withgoogle.com/", "gratuito"),
            ("FreeCodeCamp", "https://www.freecodecamp.org/", "gratuito"),
            ("Cisco Networking Academy", "https://www.netacad.com/", "gratuito"),
            ("TryHackMe", "https://tryhackme.com/", "gratuito"),
            ("MIT", "https://ocw.mit.edu/", "gratuito"),
            ("edX", "https://www.edx.org/", "barato"),
            ("Coursera", "https://www.coursera.org/", "barato"),
            ("Udemy", "https://www.udemy.com/", "barato"),
        ]
        AREAS = [
            "Tecnologia, Programacao", "Design, UX", "Negocios, Empreendedorismo",
            "Marketing Digital", "Idiomas", "Financas Pessoais",
            "Desenvolvimento Pessoal", "Ciencias Exatas", "Ciencias Humanas",
            "Saude, Bem-estar", "Educacao, Pedagogia", "Direito, Legislacao",
            "Meio Ambiente", "Agronegocio", "Industria, Producao",
        ]
        NIVEIS = ["iniciante", "intermediario", "avancado"]
        CURSOS = [
            "Introducao a Programacao com Python", "Desenvolvimento Web com HTML e CSS",
            "JavaScript Moderno", "React.js para Iniciantes", "Node.js API REST",
            "Banco de Dados SQL", "Git e GitHub na Pratica", "Logica de Programacao",
            "Java POO Completo", "PHP Basico", "Ciencia de Dados com Python",
            "Machine Learning na Pratica", "Inteligencia Artificial Generativa",
            "Redes de Computadores", "Seguranca da Informacao", "Ethical Hacking",
            "Cloud Computing AWS", "DevOps e CI/CD", "Docker e Kubernetes",
            "Linux do Zero ao Avancado", "Excel Avancado", "Analise de Dados com Excel",
            "Power BI para Negocios", "Tableau Essencial", "Marketing de Conteudo",
            "SEO Otimizacao para Google", "Google Ads na Pratica",
            "Redes Sociais Corporativas", "Design Thinking", "UX Design Fundamentos",
            "UI Design com Figma", "Photoshop Essencial", "Ilustracao Digital",
            "Fotografia Basica", "Edicao de Video com Premiere", "Motion Design",
            "Ingles Basico A1", "Ingles Intermediario B1", "Ingles Avancado C1",
            "Espanhol Basico", "Frances para Iniciantes", "Libras Basico",
            "Comunicacao e Oratoria", "Lideranca e Gestao de Equipes",
            "Empreendedorismo Digital", "Plano de Negocios", "Financas para Empreendedores",
            "Investimentos na Bolsa", "Educacao Financeira", "Economia Basica",
            "Direito Constitucional", "Direito do Trabalho", "Legislacao Tributaria",
            "Gestao de Projetos com Scrum", "Metodologias Ageis", "Kanban na Pratica",
            "Marketing Digital Completo", "Copywriting", "Vendas Online",
            "Atendimento ao Cliente", "Gestao de RH", "Recrutamento e Selecao",
            "Logistica e Supply Chain", "Gestao da Producao", "Qualidade Total",
            "Meio Ambiente Sustentavel", "Energia Solar", "Agronegocio Digital",
            "Harmonizacao Facial", "Enfermagem Basica", "Primeiros Socorros",
            "Nutricao Esportiva", "Psicologia Positiva", "Filosofia Antiga",
            "Historia do Brasil", "Geografia Politica", "Sociologia Contemporanea",
            "Matematica Financeira", "Estatistica Aplicada", "Calculo Diferencial",
            "Fisica Mecanica", "Quimica Organica", "Biologia Celular",
            "Robotica com Arduino", "IoT Internet das Coisas", "Impressao 3D",
            "Eletronica Basica", "Automacao Industrial", "Eletrica Predial",
            "Java para Web com Spring", "APIs RESTful com Flask", "GraphQL Essencial",
            "TypeScript Avancado", "Angular Framework", "Vue.js do Zero",
            "Flutter Mobile", "React Native Apps", "Kotlin Android",
            "Swift iOS Basico", "C# .NET Core", "Ruby on Rails",
            "Go Lang Basico", "Rust Fundamentos", "Blockchain e Criptomoedas",
            "Ciberseguranca Defensiva", "Pentest Profissional", "Forense Computacional",
            "AWS Solutions Architect", "Azure Fundamentals", "Google Cloud Platform",
            "Terraform Infra as Code", "Ansible Automacao", "Jenkins CI",
            "Python para Automacao", "Shell Script Avancado", "Vim Editor",
            "Visual Studio Code Produtivo", "PostgreSQL Avancado", "MongoDB NoSQL",
            "Redis Cache", "Elasticsearch Busca", "Kafka Streams",
            "Microservicos com Spring", "Arquitetura Hexagonal", "DDD Domain Driven Design",
            "Clean Code e Boas Praticas", "Testes Unitarios com Jest", "Cypress E2E",
            "Selenium Automacao Web", "Pandas Python Dados", "Matplotlib Visualizacao",
            "Scikit Learn ML", "TensorFlow IA", "PyTorch Deep Learning",
            "NLP Processamento Linguagem", "Computer Vision", "RPA Automacao",
            "BPM Business Process", "ERP SAP", "CRM Salesforce",
            "Power Automate", "SharePoint Avancado", "Teams Corporativo",
            "Word Avancado", "PowerPoint Apresentacoes", "Outlook Produtividade",
            "Gestao do Tempo", "Produtividade Pessoal", "Habitos Saudaveis",
            "Inteligencia Emocional", "Negociacao e Persuasao", "Gestao de Conflitos",
            "Diversidade nas Empresas", "Inclusao Digital", "Trabalho Remoto",
            "LGPD Privacidade Dados", "ISO 27001", "Governanca TI",
            "COBIT Framework", "ITIL Gestao Servicos", "PMP Project Management",
            "Educacao Infantil", "Ensino Hibrido", "Gamificacao na Educacao",
            "Artes Visuais", "Musica para Iniciantes", "Teatro Expressao",
            "Gastronomia Basica", "Cozinha Internacional", "Panificacao Artesanal",
            "Vinhos e Enologia", "Bartender Profissional", "Barista Cafe",
            "Jardinagem", "Paisagismo", "Decoracao de Interiores",
            "Moda e Estilo", "Costura Criativa", "Artesanato Digital",
            "Fotografia de Produto", "Filmagem com Drone", "YouTube Criacao de Conteudo",
            "Podcast do Zero", "Streaming ao Vivo", "Games Design",
            "Desenvolvimento de Jogos", "Unity 3D", "Unreal Engine",
            "Realidade Virtual", "Realidade Aumentada", "Modelagem 3D Blender",
            "Animacao 2D", "After Effects", "DaVinci Resolve Edicao",
            "Producao Musical", "Ableton Live", "FL Studio",
            "Escrita Criativa", "Redacao para Concursos", "Gramatica Normativa",
            "Literatura Brasileira", "Ingles para Negocios", "Portugues para Estrangeiros",
            "Libras Avancado", "Braile Inclusao", "Linguagem de Sinais",
            "Atendente de Farmacia", "Auxiliar Administrativo", "Secretariado Executivo",
            "Rotinas Trabalhistas", "Departamento Pessoal", "Folha de Pagamento",
            "Contabilidade Basica", "Imposto de Renda", "Nota Fiscal Eletronica",
            "Excel VBA Automacao", "Macros Excel", "Power Query",
            "DAX Language", "SQL para Analise Dados", "R Programming",
            "MATLAB Engenharia", "AutoCAD 2D", "SolidWorks 3D",
            "Projetos Eletricos", "Instalacoes Hidraulicas", "Seguranca do Trabalho",
            "NR 10 Seguranca Eletrica", "NR 35 Trabalho Altura", "EPIs e Seguranca",
            "Pilotagem de Drones", "CNH Teorica", "Mecanica Basica",
            "Eletrica Automotiva", "Manutencao de PC", "Redes Wireless",
            "Servidores Windows", "Active Directory", "Docker Swarm",
            "Kubernetes na AWS", "Serverless Computing", "Edge Computing",
            "5G Tecnologia", "LoRaWAN IoT", "RFID Automacao",
            "CRM no Excel", "Gestao de Estoque", "Compras e Suprimentos",
            "Auditoria Interna", "Controle de Qualidade", "6 Sigma",
            "Lean Manufacturing", "Industria 4.0", "Digital Twin",
            "Bioetica", "Farmacologia", "Anatomia Humana",
            "Fisiologia do Exercicio", "Personal Trainer", "Coach Fitness",
            "Yoga para Iniciantes", "Meditacao Guiada", "Bem-estar Integral",
            "Astronomia Basica", "Astrofisica", "Cosmologia",
            "Oceanografia", "Meteorologia", "Geologia",
            "Arqueologia", "Antropologia", "Ciencia Politica",
            "Direitos Humanos", "Cidadania Ativa", "Voluntariado",
            "ONG Gestao", "Terceiro Setor", "Economia Solidaria",
            "Marketing Politico", "Gestao Publica", "Administracao Municipal",
            "Urbanismo", "Arquitetura Sustentavel", "Cidades Inteligentes",
            "Permacultura", "Agricultura Organica", "Hidroponia",
            "Piscicultura", "Apicultura", "Criacao de Aves",
            "Fintechs e Inovacao", "Banking Digital", "Criptoeducacao",
            "NFTs e Metaverso", "Web3 Fundamentos", "Smart Contracts Solidity",
        ]
        TITLES_PREFIX = [
            "Curso de", "Aprenda", "Introducao a", "Fundamentos de",
            "Praticas de", "Dominando", "Guia de", "Formacao em",
            "Especializacao em", "Capacitacao em",
        ]
        CERT_TYPES = [
            "Certificado de conclusao incluso",
            "Certificado gratuito ao finalizar",
            "Certificado reconhecido pelo MEC",
            "Certificado digital gratuito",
            "Certificado de participacao",
            "Certificado internacional",
        ]
        criados = 0
        while criados < 300:
            plat_name, plat_url, preco = random.choice(PLATFORMS)
            area = random.choice(AREAS)
            nivel = random.choice(NIVEIS)
            base_name = random.choice(CURSOS)
            prefix = random.choice(TITLES_PREFIX)
            nome = f"{prefix} {base_name}"
            if len(nome) > 200:
                nome = nome[:200]
            descricao = f"{nome} - Curso gratuito oferecido pela {plat_name}. Aprenda com conteudo de qualidade e obtenha certificado ao final. Nivel {nivel}. Ideal para quem deseja se capacitar e crescer na carreira."
            if Curso.query.filter_by(nome=nome).first():
                continue
            db.session.add(Curso(
                nome=nome, descricao=descricao, plataforma=plat_name,
                certificacao=random.choice(CERT_TYPES),
                confiabilidade=f"Plataforma reconhecida: {plat_name}",
                areas=area, exemplos=base_name,
                link_afiliado=plat_url + f"?curso={criados}",
                ativo=True, cliques=random.randint(0, 500),
                nivel=nivel, preco_tipo=preco
            ))
            criados += 1
            if criados % 100 == 0:
                db.session.commit()
                app.logger.info(f"{criados}/300 cursos criados...")
        db.session.commit()
        app.logger.info(f"Seed concluido! Total: {Curso.query.count()} cursos")


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

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)
