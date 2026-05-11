from app import app, db
from core.models import Curso

with app.app_context():
    # Limpa o banco para evitar duplicatas e erros de estrutura
    db.drop_all()
    db.create_all()

    # Adiciona cursos de teste
    c1 = Curso(nome="Python para Iniciantes", origem="Bradesco", nivel="Iniciante", categoria="Tecnologia", link="https://google.com")
    c2 = Curso(nome="Excel Intermediário", origem="Fundação Estudar", nivel="Médio", categoria="Produtividade", link="https://google.com")
    c3 = Curso(nome="Hacking Ético Avançado", origem="Cyber Security", nivel="Avançado", categoria="Segurança", link="https://google.com")

    db.session.add_all([c1, c2, c3])
    db.session.commit()
    print("✅ Banco de dados resetado e cursos de teste adicionados!")
