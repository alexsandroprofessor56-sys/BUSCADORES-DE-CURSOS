import os
from urllib.parse import urlparse

import typesense

from core import db
from core.models import Curso


_COLLECTION_NAME = "cursos"


def _client():
    host = os.environ.get("TYPESENSE_HOST")
    api_key = os.environ.get("TYPESENSE_API_KEY")
    port = os.environ.get("TYPESENSE_PORT", "443")
    protocol = os.environ.get("TYPESENSE_PROTOCOL", "https")

    if not host or not api_key:
        return None

    try:
        return typesense.Client({
            "nodes": [{"host": host, "port": port, "protocol": protocol}],
            "api_key": api_key,
            "connection_timeout_seconds": 5,
        })
    except Exception:
        return None


def _collection_schema():
    return {
        "name": _COLLECTION_NAME,
        "fields": [
            {"name": "nome", "type": "string"},
            {"name": "descricao", "type": "string"},
            {"name": "plataforma", "type": "string"},
            {"name": "areas", "type": "string"},
            {"name": "nivel", "type": "string"},
            {"name": "preco_tipo", "type": "string"},
            {"name": "certificacao", "type": "string"},
            {"name": "ativo", "type": "bool"},
            {"name": "cliques", "type": "int32"},
        ],
        "default_sorting_field": "cliques",
    }


def sync_all():
    client = _client()
    if not client:
        return 0

    try:
        client.collections[_COLLECTION_NAME].delete()
    except Exception:
        pass

    try:
        client.collections.create(_collection_schema())
    except Exception:
        return 0

    cursos = Curso.query.filter_by(ativo=True).all()
    documents = []
    for c in cursos:
        documents.append({
            "id": str(c.id),
            "nome": c.nome or "",
            "descricao": c.descricao or "",
            "plataforma": c.plataforma or "",
            "areas": c.areas or "",
            "nivel": c.nivel or "",
            "preco_tipo": c.preco_tipo or "",
            "certificacao": c.certificacao or "",
            "ativo": bool(c.ativo),
            "cliques": c.cliques or 0,
        })

    if documents:
        client.collections[_COLLECTION_NAME].documents.import_(documents)

    return len(documents)


def search_cursos(query, page=1, per_page=24, area="", preco="", nivel=""):
    client = _client()
    if not client:
        return None

    try:
        filtros = []
        if area:
            filtros.append(f"areas:{area}")
        if preco:
            filtros.append(f"preco_tipo:{preco}")
        if nivel:
            filtros.append(f"nivel:{nivel}")

        search_params = {
            "q": query or "*",
            "query_by": "nome,descricao,areas,plataforma",
            "page": page,
            "per_page": per_page,
            "sort_by": "cliques:desc",
        }
        if filtros:
            search_params["filter_by"] = " && ".join(filtros)

        result = client.collections[_COLLECTION_NAME].documents.search(search_params)
        return result
    except Exception:
        return None


def sync_one(curso_id):
    client = _client()
    if not client:
        return False

    curso = db.session.get(Curso, curso_id)
    if not curso or not curso.ativo:
        try:
            client.collections[_COLLECTION_NAME].documents[str(curso_id)].delete()
        except Exception:
            pass
        return False

    doc = {
        "id": str(curso.id),
        "nome": curso.nome or "",
        "descricao": curso.descricao or "",
        "plataforma": curso.plataforma or "",
        "areas": curso.areas or "",
        "nivel": curso.nivel or "",
        "preco_tipo": curso.preco_tipo or "",
        "certificacao": curso.certificacao or "",
        "ativo": bool(curso.ativo),
        "cliques": curso.cliques or 0,
    }

    try:
        client.collections[_COLLECTION_NAME].documents.upsert(doc)
        return True
    except Exception:
        return False
