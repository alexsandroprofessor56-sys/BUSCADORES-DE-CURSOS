from app import app
from core import db
from core.models import Curso

def cacador_de_cursos(termo):
    print(f"[*] Radar rastreando rotas para: {termo}...")
    
    url_busca = f"https://www.youtube.com/results?search_query=curso+gratuito+com+certificado+{termo}"
    
    with app.app_context():
        nova_rota = Curso(
            nome=f"Especialização em {termo} - Rota Gratuita",
            descricao=f"Curso com certificado encontrado via radar na plataforma YouTube para o termo {termo}.",
            link_afiliado=url_busca,
            plataforma="YouTube / Web"
        )
        
        check = Curso.query.filter_by(link_afiliado=url_busca).first()
        if not check:
            db.session.add(nova_rota)
            db.session.commit()
            print(f"[+] Nova rota de {termo} adicionada!")

if __name__ == "__main__":
    alvos = ["Python", "Hacking Ético", "Design", "Marketing"]
    for alvo in alvos:
        cacador_de_cursos(alvo)
