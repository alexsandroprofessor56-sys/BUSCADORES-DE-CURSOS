from app import app
from core import db
from core.models import Curso

def rastrear_youtube(termo):
    url = f"https://www.youtube.com/results?search_query={termo}+curso+completo"
    print(f"[*] Rastreando YouTube para: {termo}")
    
    novo_curso = Curso(
        nome=f"Curso de {termo} - YouTube",
        descricao=f"Encontrado automaticamente na rota de busca do YouTube.",
        link_afiliado=url,
        areas="YouTube"
    )
    return novo_curso

def salvar_no_radar(curso_obj):
    with app.app_context():
        existe = Curso.query.filter_by(link_afiliado=curso_obj.link_afiliado).first()
        if not existe:
            db.session.add(curso_obj)
            db.session.commit()
            print(f"[+] Sucesso: {curso_obj.nome} adicionado!")

if __name__ == "__main__":
    termos = ["Python", "Pentest", "Marketing Digital", "Excel"]
    for t in termos:
        curso = rastrear_youtube(t)
        salvar_no_radar(curso)
