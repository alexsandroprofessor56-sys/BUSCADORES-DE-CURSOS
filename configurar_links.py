from app import app
from core import db
from core.models import Curso

with app.app_context():
    # Exemplo: Muda todos os cursos que tem "Python" no nome
    cursos_python = Curso.query.filter(Curso.nome.like('%Python%')).all()
    for c in cursos_python:
        c.link_afiliado = "https://go.hotmart.com/SEU_LINK_AQUI"
    
    db.session.commit()
    print(f"\n[SUCESSO] {len(cursos_python)} links atualizados para seu link de afiliado!")
