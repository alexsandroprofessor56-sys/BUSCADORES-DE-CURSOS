from app import app
from core import db
from core.models import Curso

with app.app_context():
    # Cria o arquivo de banco de dados e as tabelas
    db.create_all()
    
    # Verifica se já tem curso (para não duplicar)
    if Curso.query.count() == 0:
        for i in range(1, 51):
            novo_curso = Curso(
                nome=f"Curso de Python PRO #{i}",
                descricao="Aprenda automação e scripts com Python no Kali Linux.",
                link_afiliado="https://www.google.com",
                preco=97.00
            )
            db.session.add(novo_curso)
        db.session.commit()
        print(f"\n[SUCESSO] Banco criado e 50 cursos inseridos!")
    else:
        print(f"\n[AVISO] O banco já contém {Curso.query.count()} cursos.")
