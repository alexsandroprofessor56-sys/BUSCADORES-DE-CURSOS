from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core import db
from core.models import Curso


SEED_PLATFORMS = [
    ("Fundacao Bradesco", "https://www.ev.org.br/"),
    ("FGV Cursos Gratuitos", "https://educacao-executiva.fgv.br/cursos/gratuitos"),
    ("Escola Virtual Gov", "https://www.escolavirtual.gov.br/"),
    ("Sebrae", "https://sebrae.com.br/sites/PortalSebrae/cursosonline"),
]


def _clean(text):
    return " ".join((text or "").split())[:150]


def crawl_free_courses(limit=20):
    created = 0
    found = []
    headers = {"User-Agent": "EducaLivreCrawler/1.0"}

    for platform, url in SEED_PLATFORMS:
        try:
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.select("a[href]")
        for link in links[:80]:
            title = _clean(link.get_text(" "))
            href = link.get("href")
            if len(title) < 8 or not href:
                continue
            if not any(word in title.lower() for word in ("curso", "formacao", "aprenda", "online", "gratuito", "certificado")):
                continue
            full_url = urljoin(url, href)
            if Curso.query.filter_by(link_afiliado=full_url).first():
                continue
            curso = Curso(
                nome=f"{platform}: {title}",
                descricao="Curso encontrado automaticamente pelo crawler.",
                certificacao="Verificar regras da plataforma",
                confiabilidade="Coletado de fonte conhecida",
                areas="Educação, Carreira",
                exemplos=title,
                link_afiliado=full_url,
                ativo=True,
                cliques=0,
            )
            db.session.add(curso)
            found.append(curso.nome)
            created += 1
            if created >= limit:
                db.session.commit()
                return created, found

    db.session.commit()
    return created, found


def check_broken_links(limit=60):
    checked = 0
    broken = []
    headers = {"User-Agent": "EducaLivreLinkChecker/1.0"}
    cursos = Curso.query.filter(Curso.link_afiliado.isnot(None)).limit(limit).all()
    for curso in cursos:
        checked += 1
        try:
            response = requests.head(curso.link_afiliado, headers=headers, timeout=6, allow_redirects=True)
            if response.status_code >= 400:
                broken.append((curso.id, curso.nome, response.status_code))
        except Exception:
            broken.append((curso.id, curso.nome, "erro"))
    return checked, broken
