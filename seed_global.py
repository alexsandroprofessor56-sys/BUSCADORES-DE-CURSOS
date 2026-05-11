from app import app
from core import db
from core.models import Curso

fontes_elite = [
    {"nome": "Fundamentos de Cibersegurança", "plataforma": "Fortinet", "preco_tipo": "gratuito", "link_afiliado": "https://training.fortinet.com/", "areas": "Segurança", "nivel": "Iniciante"},
    {"nome": "Introdução ao Linux", "plataforma": "Linux Foundation", "preco_tipo": "gratuito", "link_afiliado": "https://training.linuxfoundation.org/", "areas": "TI", "nivel": "Iniciante"},
    {"nome": "Ciência de Dados com Python", "plataforma": "IBM SkillsBuild", "preco_tipo": "gratuito", "link_afiliado": "https://skillsbuild.org/", "areas": "Dados", "nivel": "Médio"},
    {"nome": "Prevenção e Controle de Infecções", "plataforma": "AVASUS", "preco_tipo": "gratuito", "link_afiliado": "https://avasus.ufrn.br/", "areas": "Saúde", "nivel": "Iniciante"},
    {"nome": "Gestão Financeira Pessoal", "plataforma": "EV.G", "preco_tipo": "gratuito", "link_afiliado": "https://www.escolavirtual.gov.br/", "areas": "Finanças", "nivel": "Iniciante"},
    {"nome": "Design Gráfico para Iniciantes", "plataforma": "Adobe Exchange", "preco_tipo": "gratuito", "link_afiliado": "https://edex.adobe.com/", "areas": "Design", "nivel": "Iniciante"},
    {"nome": "Estratégia de SEO Avançado", "plataforma": "Rock University", "preco_tipo": "gratuito", "link_afiliado": "https://university.rockcontent.com/", "areas": "Marketing", "nivel": "Avançado"},
    {"nome": "Escrita Acadêmica", "plataforma": "UFRGS Lúmina", "preco_tipo": "gratuito", "link_afiliado": "https://lumina.ufrgs.br/", "areas": "Educação", "nivel": "Médio"}
]

with app.app_context():
    for f in fontes_elite:
        if not Curso.query.filter_by(nome=f['nome']).first():
            novo = Curso(**f)
            db.session.add(novo)
    db.session.commit()
    print(f"Sucesso! {len(fontes_elite)} novas fontes de elite injetadas.")
