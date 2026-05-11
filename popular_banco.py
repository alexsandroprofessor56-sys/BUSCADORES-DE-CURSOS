from app import app
from core import db
from core.models import Curso

def popular():
    with app.app_context():
        # Limpa o banco atual (opcional, remova se quiser manter o que já tem)
        # db.drop_all() 
        db.create_all()

        # Lista de cursos para aparecerem na tela
        novos_cursos = [
            Curso(
                nome='Excel Especialista', 
                nivel='Avançado', 
                plataforma='Hashtag', 
                areas='Dados', 
                link_afiliado='https://www.hashtagtreinamentos.com/', 
                cliques=0
            ),
            Curso(
                nome='Python para Iniciantes', 
                nivel='Iniciante', 
                plataforma='Fundação Bradesco', 
                areas='Programação', 
                link_afiliado='https://www.ev.org.br/', 
                cliques=0
            ),
            Curso(
                nome='Segurança Cibernética', 
                nivel='Médio', 
                plataforma='Cisco', 
                areas='Segurança', 
                link_afiliado='https://www.netacad.com/', 
                cliques=0
            )
        ]

        db.session.add_all(novos_cursos)
        db.session.commit()
        print(f"Sucesso! {len(novos_cursos)} cursos foram inseridos no banco.")

if __name__ == "__main__":
    popular()
