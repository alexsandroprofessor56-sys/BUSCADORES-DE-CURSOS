import random
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core import db
from core.models import Curso

HEADERS = {"User-Agent": "RadarElite/2.0 (+https://buscadores-de-cursos.onrender.com)"}

PLATFORMS = [
    ("Fundacao Bradesco", "https://www.ev.org.br/", "gratuito"),
    ("FGV", "https://educacao-executiva.fgv.br/cursos/gratuitos", "gratuito"),
    ("Escola Virtual Gov", "https://www.escolavirtual.gov.br/", "gratuito"),
    ("Sebrae", "https://sebrae.com.br/sites/PortalSebrae/cursosonline", "gratuito"),
    ("Kultivi", "https://kultivi.com/", "gratuito"),
    ("Senai", "https://online.sp.senai.br/cursos-gratuitos", "gratuito"),
    ("Harvard", "https://pll.harvard.edu/catalog/free", "gratuito"),
    ("Microsoft Learn", "https://learn.microsoft.com/", "gratuito"),
    ("Google Skillshop", "https://skillshop.withgoogle.com/", "gratuito"),
    ("FreeCodeCamp", "https://www.freecodecamp.org/learn/", "gratuito"),
    ("Cisco NetAcad", "https://www.netacad.com/", "gratuito"),
    ("TryHackMe", "https://tryhackme.com/", "gratuito"),
    ("MIT OCW", "https://ocw.mit.edu/", "gratuito"),
    ("edX", "https://www.edx.org/", "barato"),
    ("Coursera", "https://www.coursera.org/", "barato"),
    ("Udemy", "https://www.udemy.com/", "barato"),
    ("Alura", "https://www.alura.com.br/", "barato"),
    ("Rocketseat", "https://www.rocketseat.com.br/", "barato"),
    ("Digital Innovation One", "https://www.dio.me/", "gratuito"),
    ("Ada", "https://ada.tech/", "gratuito"),
    ("Cubos Academy", "https://cubos.academy/", "gratuito"),
    ("Resilia", "https://www.resilia.com.br/", "gratuito"),
    ("IBM SkillsBuild", "https://skillsbuild.org/", "gratuito"),
    ("AWS Skill Builder", "https://aws.amazon.com/training/", "gratuito"),
    ("Oracle University", "https://education.oracle.com/", "gratuito"),
    ("Linux Foundation", "https://training.linuxfoundation.org/", "gratuito"),
    ("Stanford Online", "https://online.stanford.edu/", "gratuito"),
    ("Yale Courses", "https://oyc.yale.edu/", "gratuito"),
    ("Khan Academy", "https://www.khanacademy.org/", "gratuito"),
    ("SoloLearn", "https://www.sololearn.com/", "gratuito"),
    ("W3Schools", "https://www.w3schools.com/", "gratuito"),
    ("MDN Web Docs", "https://developer.mozilla.org/", "gratuito"),
    ("DevMedia", "https://www.devmedia.com.br/", "gratuito"),
    ("B7Web", "https://b7web.com.br/", "barato"),
    ("Origamid", "https://www.origamid.com/", "barato"),
]

AREAS = [
    "Tecnologia, Programacao", "Design, UX", "Negocios, Empreendedorismo",
    "Marketing Digital", "Idiomas", "Financas Pessoais",
    "Desenvolvimento Pessoal", "Ciencias Exatas", "Ciencias Humanas",
    "Saude, Bem-estar", "Educacao, Pedagogia", "Direito, Legislacao",
    "Meio Ambiente", "Agronegocio", "Industria, Producao",
    "Ciencia de Dados, IA", "Cloud Computing", "Ciberseguranca",
]

NIVEIS = ["iniciante", "intermediario", "avancado"]

NOMES_BASE = [
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
    "Primeiros Socorros", "Nutricao Esportiva", "Psicologia Positiva",
    "Filosofia Antiga", "Historia do Brasil", "Matematica Financeira",
    "Estatistica Aplicada", "Calculo Diferencial", "Robotica com Arduino",
    "IoT Internet das Coisas", "Impressao 3D", "Eletronica Basica",
    "Automacao Industrial", "APIs RESTful com Flask", "GraphQL Essencial",
    "TypeScript Avancado", "Angular Framework", "Vue.js do Zero",
    "Flutter Mobile", "React Native Apps", "Kotlin Android",
    "Swift iOS Basico", "C# .NET Core", "Ruby on Rails",
    "Go Lang Basico", "Rust Fundamentos", "Blockchain e Criptomoedas",
    "Ciberseguranca Defensiva", "Pentest Profissional", "Forense Computacional",
    "AWS Solutions Architect", "Azure Fundamentals", "Google Cloud Platform",
    "Terraform Infra as Code", "Ansible Automacao", "Jenkins CI",
    "Python para Automacao", "Shell Script Avancado", "Visual Studio Code Produtivo",
    "PostgreSQL Avancado", "MongoDB NoSQL", "Redis Cache",
    "Elasticsearch Busca", "Kafka Streams", "Microservicos com Spring",
    "Clean Code e Boas Praticas", "Testes Unitarios com Jest", "Cypress E2E",
    "Pandas Python Dados", "Matplotlib Visualizacao", "Scikit Learn ML",
    "TensorFlow IA", "PyTorch Deep Learning", "NLP Processamento Linguagem",
    "Computer Vision", "RPA Automacao", "ERP SAP", "CRM Salesforce",
    "Power Automate", "SharePoint Avancado", "Word Avancado",
    "Gestao do Tempo", "Produtividade Pessoal", "Inteligencia Emocional",
    "Negociacao e Persuasao", "Gestao de Conflitos", "LGPD Privacidade Dados",
    "Educacao Infantil", "Ensino Hibrido", "Gamificacao na Educacao",
    "Gastronomia Basica", "Cozinha Internacional", "Panificacao Artesanal",
    "Jardinagem", "Paisagismo", "Decoracao de Interiores",
    "Moda e Estilo", "YouTube Criacao de Conteudo", "Podcast do Zero",
    "Desenvolvimento de Jogos", "Unity 3D", "Unreal Engine",
    "Realidade Virtual", "Realidade Aumentada", "Modelagem 3D Blender",
    "Animacao 2D", "After Effects", "Producao Musical",
    "Escrita Criativa", "Redacao para Concursos", "Gramatica Normativa",
    "Literatura Brasileira", "Ingles para Negocios", "Libras Avancado",
    "Atendente de Farmacia", "Auxiliar Administrativo", "Secretariado Executivo",
    "Contabilidade Basica", "Imposto de Renda", "Excel VBA Automacao",
    "SQL para Analise Dados", "R Programming", "MATLAB Engenharia",
    "AutoCAD 2D", "SolidWorks 3D", "Seguranca do Trabalho",
    "Mecanica Basica", "Eletrica Automotiva", "Manutencao de PC",
    "Servidores Windows", "Active Directory", "Docker Swarm",
    "Kubernetes na AWS", "Serverless Computing", "Edge Computing",
    "5G Tecnologia", "LoRaWAN IoT", "RFID Automacao",
    "Gestao de Estoque", "Auditoria Interna", "Controle de Qualidade",
    "Lean Manufacturing", "Industria 4.0", "Bioetica",
    "Astronomia Basica", "Astrofisica", "Oceanografia",
    "Direitos Humanos", "Cidadania Ativa", "Voluntariado",
    "Urbanismo", "Arquitetura Sustentavel", "Cidades Inteligentes",
    "Agricultura Organica", "Hidroponia", "Fintechs e Inovacao",
    "Web3 Fundamentos", "Smart Contracts Solidity", "Analise de Sistemas",
    "Engenharia de Software", "Qualidade de Software", "Banco de Dados NoSQL",
]

PREFIXOS = [
    "Curso de", "Aprenda", "Introducao a", "Fundamentos de",
    "Praticas de", "Dominando", "Guia de", "Formacao em",
    "Especializacao em", "Capacitacao em", "Curso Completo de",
    "Masterclass em", "Workshop de", "Treinamento em",
]

CERT_TYPES = [
    "Certificado de conclusao incluso",
    "Certificado gratuito ao finalizar",
    "Certificado reconhecido pelo MEC",
    "Certificado digital gratuito",
    "Certificado de participacao",
    "Certificado internacional",
    "Certificado ao concluir o curso",
]


def seed_cursos(quantidade=500):
    criados = 0
    random.seed()
    usados = set()

    while criados < quantidade:
        plat_name, plat_url, preco = random.choice(PLATFORMS)
        area = random.choice(AREAS)
        nivel = random.choice(NIVEIS)
        base_name = random.choice(NOMES_BASE)
        prefix = random.choice(PREFIXOS)
        nome = f"{prefix} {base_name}"
        if len(nome) > 200:
            nome = nome[:200]
        if nome in usados:
            continue
        if Curso.query.filter_by(nome=nome).first():
            continue
        usados.add(nome)
        descricao = f"{nome} - Curso oferecido pela {plat_name}. Aprenda com conteudo de qualidade e obtenha certificado ao final. Nivel {nivel}. Ideal para quem deseja se capacitar e crescer na carreira."
        db.session.add(Curso(
            nome=nome, descricao=descricao, plataforma=plat_name,
            certificacao=random.choice(CERT_TYPES),
            confiabilidade=f"Plataforma reconhecida: {plat_name}",
            areas=area, exemplos=base_name,
            link_afiliado=plat_url + f"?src=radar_{criados}",
            ativo=True, cliques=random.randint(0, 500),
            nivel=nivel, preco_tipo=preco,
            rating=round(random.uniform(3.0, 5.0), 1),
        ))
        criados += 1
        if criados % 100 == 0:
            db.session.commit()
    db.session.commit()
    return criados


def check_broken_links(limite=100, desativar=True):
    checked = 0
    quebrados = 0
    cursos = Curso.query.filter(
        Curso.ativo.is_(True),
        Curso.link_afiliado.isnot(None)
    ).limit(limite).all()

    for curso in cursos:
        checked += 1
        url = curso.link_afiliado
        try:
            resp = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if resp.status_code >= 400:
                if desativar:
                    curso.ativo = False
                quebrados += 1
        except requests.RequestException:
            if desativar:
                curso.ativo = False
            quebrados += 1

    if desativar:
        db.session.commit()
    return checked, quebrados


def crawl_free_courses(limite=30):
    created = 0
    headers = {"User-Agent": "RadarEliteCrawler/2.0"}
    for plataforma, url, _ in PLATFORMS[:10]:
        if created >= limite:
            break
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.select("a[href]")[:50]:
            texto = " ".join((link.get_text(" ") or "").split())
            href = link.get("href")
            if len(texto) < 10 or not href:
                continue
            palavras = ("curso", "formacao", "aprenda", "online", "gratuito", "certificado", "treinamento")
            if not any(p in texto.lower() for p in palavras):
                continue
            url_completa = urljoin(url, href)
            if Curso.query.filter_by(link_afiliado=url_completa).first():
                continue
            db.session.add(Curso(
                nome=f"{plataforma}: {texto[:100]}",
                descricao="Curso encontrado automaticamente pelo crawler.",
                certificacao="Verificar na plataforma",
                confiabilidade=f"Crawler automatico - {plataforma}",
                areas="Educacao, Carreira",
                exemplos=texto[:80],
                link_afiliado=url_completa,
                ativo=True, cliques=0,
            ))
            created += 1
            if created >= limite:
                break
    if created:
        db.session.commit()
    return created
