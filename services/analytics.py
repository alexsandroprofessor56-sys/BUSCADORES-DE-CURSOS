from datetime import datetime, timedelta

from core import db
from core.models import AccessEvent, Curso


def analytics_snapshot():
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    month_ago = now - timedelta(days=30)
    previous_month = now - timedelta(days=60)

    dau = db.session.query(AccessEvent.ip).filter(AccessEvent.created_at >= day_ago).distinct().count()
    mau = db.session.query(AccessEvent.ip).filter(AccessEvent.created_at >= month_ago).distinct().count()
    previous_mau = db.session.query(AccessEvent.ip).filter(
        AccessEvent.created_at >= previous_month,
        AccessEvent.created_at < month_ago,
    ).distinct().count()
    retention = round((mau / previous_mau) * 100, 1) if previous_mau else 100.0 if mau else 0.0

    top_courses = Curso.query.order_by(Curso.cliques.desc()).limit(10).all()
    events = AccessEvent.query.order_by(AccessEvent.created_at.desc()).limit(120).all()
    countries = {}
    paths = {}
    for event in events:
        countries[event.country or "Desconhecido"] = countries.get(event.country or "Desconhecido", 0) + 1
        paths[event.path or "/"] = paths.get(event.path or "/", 0) + 1

    return {
        "dau": dau,
        "mau": mau,
        "retention": retention,
        "top_courses": [{"name": item.nome, "clicks": item.cliques or 0} for item in top_courses],
        "countries": countries,
        "paths": paths,
    }


def recommend_courses(query="", limit=8):
    cursos = Curso.query.filter_by(ativo=True).all()
    terms = set((query or "").lower().split())
    scored = []
    for curso in cursos:
        text = " ".join([
            curso.nome or "",
            curso.descricao or "",
            curso.areas or "",
            curso.exemplos or "",
            curso.certificacao or "",
        ]).lower()
        score = sum(1 for term in terms if term in text) if terms else 0
        score += min((curso.cliques or 0) / 10, 5)
        scored.append((score, curso))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "id": curso.id,
            "nome": curso.nome,
            "descricao": curso.descricao,
            "link": f"/c/{curso.id}",
            "score": round(score, 2),
        }
        for score, curso in scored[:limit]
    ]
