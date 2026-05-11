import os
import subprocess
import json
from app import app
from core import db
from core.models import Curso

def buscar_youtube(termo):
    print(f"[*] Iniciando radar para: {termo}")
    comando = [
        'yt-dlp', 
        f'ytsearch10:curso completo {termo}', 
        '--dump-json', 
        '--flat-playlist'
    ]
    
    processo = subprocess.run(comando, capture_output=True, text=True)
    if processo.returncode != 0:
        print("[!] Erro ao acessar o radar do YouTube. Verifique se o yt-dlp está instalado.")
        return

    videos = processo.stdout.splitlines()
    
    with app.app_context():
        for video_json in videos:
            data = json.loads(video_json)
            link = f"https://www.youtube.com/watch?v={data['id']}"
            
            existente = Curso.query.filter_by(link_afiliado=link).first()
            if not existente:
                novo_curso = Curso(
                    nome=data['title'],
                    link_afiliado=link,
                    descricao=f"Curso de {termo} encontrado automaticamente.",
                    plataforma='YouTube'
                )
                db.session.add(novo_curso)
                print(f"[+] Novo curso encontrado: {data['title']}")
        
        db.session.commit()
        print(f"[OK] Banco de dados atualizado para: {termo}")

if __name__ == '__main__':
    interesses = ['Python', 'Hacker Ético', 'Excel', 'Marketing Digital']
    for item in interesses:
        buscar_youtube(item)
