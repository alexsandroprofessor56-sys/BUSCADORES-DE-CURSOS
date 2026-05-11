from app import app, db
from core.models import Curso

with app.app_context():
    # Limpando para garantir que não haja duplicatas
    db.session.query(Curso).delete()
    
    fontes_reais = [
        {"nome": "Python Fundamentos", "origem": "Bradesco", "nivel": "Iniciante", "link": "https://www.ev.org.br/"},
        {"nome": "Excel Avançado", "origem": "Hashtag", "nivel": "Avançado", "link": "https://www.hashtagtreinamentos.com/"},
        {"nome": "Marketing Digital", "origem": "Google", "nivel": "Iniciante", "link": "https://grow.google/"},
        {"nome": "Lógica de Programação", "origem": "Curso em Vídeo", "nivel": "Iniciante", "link": "https://www.cursoemvideo.com/"},
        {"nome": "Power BI Impressionador", "origem": "YouTube", "nivel": "Médio", "link": "https://youtube.com"}
    ]

    for f in fontes_reais:
        db.session.add(Curso(**f))
    
    db.session.commit()
    print("✅ Sistema populado com sucesso!")
