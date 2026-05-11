from app import app
from core import db
from core.models import Curso
import os

# Define o caminho para o banco na pasta atual
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

with app.app_context():
    # Deleta tudo e recria as tabelas conforme o seu models.py
    db.drop_all()
    db.create_all()
    
    # Adiciona 50 cursos usando APENAS as colunas que você tem
    for i in range(1, 51):
        c = Curso(
            nome=f"Curso de Invasão e Scripts #{i}",
            link_afiliado="https://www.google.com",
            # 'cliques' já tem default=0, 'ativo' já tem default=True
        )
        db.session.add(c)
    
    db.session.commit()
    print(f"\n[SUCESSO] Banco recriado com {Curso.query.count()} cursos!")
    print(f"Caminho: {os.path.join(basedir, 'database.db')}")
