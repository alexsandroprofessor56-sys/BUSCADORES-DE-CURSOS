from app import app
from core import db
from core.models import Curso

def popular():
    with app.app_context():
        # Limpa o banco para garantir que as 40 fontes sejam novas
        db.drop_all()
        db.create_all()

        fontes = [
            {"n": "Python para Iniciantes", "l": "https://www.ev.org.br/", "o": "Fundação Bradesco", "c": "Programação", "nv": "Iniciante"},
            {"n": "Segurança Cibernética", "l": "https://www.netacad.com/", "o": "Cisco Networking Academy", "c": "Segurança", "nv": "Médio"},
            {"n": "Cloud Practitioner", "l": "https://explore.skillbuilder.aws/", "o": "AWS Training", "c": "Cloud", "nv": "Avançado"},
            {"n": "Desenvolvimento Web Fullstack", "l": "https://www.freecodecamp.org/portuguese/", "o": "FreeCodeCamp", "c": "Programação", "nv": "Médio"},
            {"n": "Google Data Analytics", "l": "https://grow.google/intl/pt-br/", "o": "Google Grow", "c": "Dados", "nv": "Iniciante"},
            {"n": "Inteligência Artificial", "l": "https://skills.yourlearning.ibm.com/", "o": "IBM SkillsBuild", "c": "IA", "nv": "Avançado"},
            {"n": "Introdução à Ciência da Computação", "l": "https://plataforma.estudarfora.org.br/", "o": "Harvard CS50", "c": "Ciência", "nv": "Avançado"},
            {"n": "Lógica de Programação", "l": "https://www.softblue.com.br/", "o": "Softblue", "c": "Programação", "nv": "Iniciante"},
            {"n": "Machine Learning", "l": "https://www.microsoft.com/pt-br/trainingdays/", "o": "Microsoft Learn", "c": "IA", "nv": "Avançado"},
            {"n": "Desenvolvimento Android", "l": "https://developer.android.com/courses", "o": "Google Developers", "c": "Mobile", "nv": "Médio"},
            {"n": "Empreendedorismo", "l": "https://www.sebrae.com.br/", "o": "Sebrae", "c": "Negócios", "nv": "Iniciante"},
            {"n": "Gestão de Projetos", "l": "https://www.pmi.org/brasil", "o": "PMI Brasil", "c": "Gestão", "nv": "Médio"},
            {"n": "Marketing Digital", "l": "https://academy.hubspot.com/", "o": "HubSpot Academy", "c": "Marketing", "nv": "Médio"},
            {"n": "Finanças Pessoais", "l": "https://www.fgv.br/cursos-online", "o": "FGV Online", "c": "Finanças", "nv": "Iniciante"},
            {"n": "Liderança de Equipes", "l": "https://www.escolavirtual.gov.br/", "o": "EV.G (Gov.br)", "c": "Gestão", "nv": "Iniciante"},
            {"n": "Business Intelligence", "l": "https://www.datascienceacademy.com.br/", "o": "Data Science Academy", "c": "Dados", "nv": "Avançado"},
            {"n": "Customer Success", "l": "https://rduniversity.com.br/", "o": "RD University", "c": "Marketing", "nv": "Médio"},
            {"n": "Scrum Master", "l": "https://www.scrum.org/", "o": "Scrum.org", "c": "Agilidade", "nv": "Avançado"},
            {"n": "Comunicação Assertiva", "l": "https://www.rockuniversity.com.br/", "o": "Rock University", "c": "Soft Skills", "nv": "Iniciante"},
            {"n": "Vendas de Performance", "l": "https://vendas.meetime.com.br/academy/", "o": "Meetime Academy", "c": "Vendas", "nv": "Médio"},
            {"n": "Excel para Negócios", "l": "https://www.hashtagtreinamentos.com/", "o": "Hashtag", "c": "Produtividade", "nv": "Médio"},
            {"n": "Inglês para Carreira", "l": "https://www.britishcouncil.org.br/", "o": "British Council", "c": "Idiomas", "nv": "Iniciante"},
            {"n": "Design Thinking", "l": "https://www.escoladedesignthinking.com.br/", "o": "Escola de Design", "c": "Design", "nv": "Médio"},
            {"n": "UX/UI Design", "l": "https://www.adobe.com/", "o": "Adobe Design", "c": "Design", "nv": "Avançado"},
            {"n": "Edição de Vídeo", "l": "https://www.youtube.com/creators/", "o": "YouTube Creators", "c": "Audiovisual", "nv": "Iniciante"},
            {"n": "Direito Digital", "l": "https://www.itsrio.org/pt/cursos/", "o": "ITS Rio", "c": "Direito", "nv": "Avançado"},
            {"n": "Sustentabilidade", "l": "https://www.unep.org/", "o": "ONU (PNUMA)", "c": "Ambiental", "nv": "Iniciante"},
            {"n": "Análise de Investimentos", "l": "https://www.anbima.com.br/educacao", "o": "ANBIMA", "c": "Finanças", "nv": "Avançado"},
            {"n": "Educação Financeira", "l": "https://www.bcb.gov.br/", "o": "Banco Central", "c": "Finanças", "nv": "Iniciante"},
            {"n": "Metodologias Ativas", "l": "https://www.moodle.org/", "o": "Moodle Academy", "c": "Educação", "nv": "Médio"},
            {"n": "Programação 42", "l": "https://www.42sp.org.br/", "o": "42 São Paulo", "c": "Programação", "nv": "Avançado"},
            {"n": "Frontend Developer", "l": "https://www.digitalinnovation.one/", "o": "DIO", "c": "Programação", "nv": "Médio"},
            {"n": "Cursos Técnicos", "l": "https://www.mundosenai.com.br/", "o": "SENAI Play", "c": "Técnico", "nv": "Iniciante"},
            {"n": "Capacitação SESI", "l": "http://www.sesisenai.org.br/", "o": "SESI/SENAI", "c": "Carreira", "nv": "Médio"},
            {"n": "Inovação Pública", "l": "https://www.enap.gov.br/", "o": "ENAP", "c": "Governo", "nv": "Médio"},
            {"n": "Língua Portuguesa", "l": "https://www.pucrs.br/online/", "o": "PUCRS Online", "c": "Idiomas", "nv": "Médio"},
            {"n": "Gestão de Tempo", "l": "https://www.linkedin.com/learning/", "o": "LinkedIn Learning", "c": "Soft Skills", "nv": "Iniciante"},
            {"n": "Introdução ao DevOps", "l": "https://www.redhat.com/", "o": "Red Hat Academy", "c": "DevOps", "nv": "Avançado"},
            {"n": "Apps No-Code", "l": "https://bubble.io/academy", "o": "Bubble Academy", "c": "Programação", "nv": "Iniciante"},
            {"n": "Fotografia Digital", "l": "https://www.canon.com.br/aprenda", "o": "Canon College", "c": "Arte", "nv": "Iniciante"}
        ]

        for f in fontes:
            db.session.add(Curso(nome=f['n'], link_afiliado=f['l'], plataforma=f['o'], areas=f['c'], nivel=f['nv'], cliques=0))
        
        db.session.commit()
        print("RADAR ELITE: 40 Cursos carregados com sucesso!")

if __name__ == "__main__":
    popular()
