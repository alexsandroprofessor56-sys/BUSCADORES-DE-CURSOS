import sys
sys.path.insert(0, '/home/alexkali/Documents/Backup_Cartao')

from app import app
from core import db
from core.models import Curso

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
    (" Cisco Networking Academy", "https://www.netacad.com/", "gratuito"),
    ("TryHackMe", "https://tryhackme.com/", "gratuito"),
    (" MIT", "https://ocw.mit.edu/", "gratuito"),
    ("edX", "https://www.edx.org/", "barato"),
    ("Coursera", "https://www.coursera.org/", "barato"),
    ("Udemy", "https://www.udemy.com/", "barato"),
]

AREAS = [
    "Tecnologia, Programacao", "Design, UX", "Negocios, Empreendedorismo",
    "Marketing Digital", "Idiomas", "Financas Pessoais",
    "Desenvolvimento Pessoal", "Ciencias Exatas", "Ciencias Humanas",
    "Saude, Bem-estar", "Educacao, Pedagogia", "Direito, Legislacao",
    "Meio Ambiente", "Agronegocio", "Industria, Producao"
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
    "Scikit Learn ML", "TensorFlow IA", "PyTorc Deep Learning",
    "NLP Processamento Linguagem", "Computer Vision", "RPA Automacao",
    "BPM Business Process", "ERP SAP", "CRM Salesforce",
    "Power Automate", "SharePoint Avancado", "Teams Corporativo",
    "Word Avancado", "PowerPoint Apresentacoes", "Outlook Produtividade",
    "Gestao do Tempo", "Produtividade Pessoal", "Hábitos Saudaveis",
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
    "Marketing Politico", "Gestao Publica", " Administracao Municipal",
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

with app.app_context():
    db.create_all()
    count = Curso.query.count()
    if count >= 300:
        print(f"Ja existem {count} cursos. Pulando seed.")
    else:
        import random
        random.seed(42)

        needed = 300 - count
        criados = 0

        while criados < needed:
            plat_name, plat_url, preco = random.choice(PLATFORMS)
            area = random.choice(AREAS)
            nivel = random.choice(NIVEIS)
            base_name = random.choice(CURSOS)
            prefix = random.choice(TITLES_PREFIX)

            nome = f"{prefix} {base_name}"
            if len(nome) > 200:
                nome = nome[:200]

            descricao = f"{nome} - Curso gratuito oferecido pela {plat_name}. "
            descricao += f"Aprenda com conteudo de qualidade e obtenha certificado ao final. "
            descricao += f"Nivel {nivel}. Ideal para quem deseja se capacitar e crescer na carreira."

            plataforma = plat_name
            link = plat_url
            certificacao = random.choice(CERT_TYPES)
            confiabilidade = f"Plataforma reconhecida: {plat_name}"

            if Curso.query.filter_by(nome=nome).first():
                continue

            curso = Curso(
                nome=nome, descricao=descricao, plataforma=plataforma,
                certificacao=certificacao, confiabilidade=confiabilidade,
                areas=area, exemplos=base_name,
                link_afiliado=link + f"?curso={criados + count}",
                ativo=True, cliques=random.randint(0, 500),
                nivel=nivel, preco_tipo=preco
            )
            db.session.add(curso)
            criados += 1

            if criados % 50 == 0:
                db.session.commit()
                print(f"{criados}/{needed} cursos criados...")

        db.session.commit()
        total = Curso.query.count()
        print(f"Seed concluido! Total de cursos: {total}")
