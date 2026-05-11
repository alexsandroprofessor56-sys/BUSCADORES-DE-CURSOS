import requests
from bs4 import BeautifulSoup
from app import app
from core import db
from core.models import Curso

def scan_cursos():
    print("[*] Iniciando varredura do radar...")
    url = "https://certificadocursosonline.com/cursos-gratuitos/"
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = soup.find_all('a', rel='bookmark')
        
        with app.app_context():
            for link in links[:10]:
                titulo = link.text.strip()
                url_curso = link['href']
                
                existe = Curso.query.filter_by(link_afiliado=url_curso).first()
                
                if not existe:
                    novo_curso = Curso(
                        nome=titulo,
                        descricao=f"Curso gratuito detectado de {titulo}",
                        link_afiliado=url_curso,
                        plataforma="Certificado Cursos"
                    )
                    db.session.add(novo_curso)
                    print(f"[+] Detectado: {titulo}")
            
            db.session.commit()
            print("[+] Varredura concluída e banco atualizado!")

    except Exception as e:
        print(f"[!] Erro na varredura: {e}")

if __name__ == "__main__":
    scan_cursos()
