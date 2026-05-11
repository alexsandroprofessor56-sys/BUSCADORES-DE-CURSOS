from app import app
from core import db
from core.models import Curso

with app.app_context():
    db.create_all()
    # Exemplo de curso real (Você pode adicionar mais aqui)
    curso1 = Curso(
        nome="Python para Iniciantes - Fundação Bradesco",
        link_afiliado="https://www.ev.org.br/cursos/fundamentos-de-logica-de-programacao"
    )
    db.session.add(curso1)
    db.session.commit()
    print("Banco de dados criado com sucesso e cursos reais adicionados!")
