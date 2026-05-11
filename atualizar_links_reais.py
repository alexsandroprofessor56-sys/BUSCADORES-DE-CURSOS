from app import app
from core import db
from core.models import Curso

with app.app_context():
    # Aqui criamos um dicionário com os links reais para cada ID ou Nome
    # Exemplo de mapeamento:
    links_reais = {
        1: "https://www.paginadocurso01.com.br",
        2: "https://www.paginadocurso02.com.br",
        3: "https://www.paginadocurso03.com.br",
    }

    for id_curso, link in links_reais.items():
        curso = Curso.query.get(id_curso)
        if curso:
            curso.link_afiliado = link
            print(f"Curso {id_curso} atualizado para: {link}")
    
    db.session.commit()
    print("\n[SUCESSO] Links específicos atualizados!")
