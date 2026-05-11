from app import app
from core import db
from core.models import Curso

with app.app_context():
    # Busca todos os cursos que estão apontando para o Google
    cursos = Curso.query.all()
    meu_link_novo = "https://SEU-LINK-AQUI.com" # <--- COLOQUE SEU LINK AQUI
    
    for c in cursos:
        c.link_afiliado = meu_link_novo
    
    db.session.commit()
    print(f"\n[OK] {len(cursos)} cursos atualizados! Agora eles levam para: {meu_link_novo}")
