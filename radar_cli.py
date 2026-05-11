import sys
from app import app
from core import db
from core.models import Curso

def listar_estatisticas():
    with app.app_context():
        total = Curso.query.count()
        ativos = Curso.query.filter_by(ativo=True).count()
        print(f"\n[📊] TOTAL DE CURSOS: {total}")
        print(f"[✅] CURSOS ATIVOS: {ativos}")
        print(f"[💀] CURSOS MORTOS: {total - ativos}\n")

def buscar_curso(termo):
    with app.app_context():
        resultados = Curso.query.filter(Curso.nome.contains(termo)).all()
        for c in resultados:
            status = "✅" if c.ativo else "❌"
            print(f"{status} ID: {c.id} | {c.nome} | Fonte: {c.fonte}")

def alternar_status(id_curso):
    with app.app_context():
        curso = Curso.query.get(id_curso)
        if curso:
            curso.ativo = not curso.ativo
            db.session.commit()
            print(f"[!] Curso {curso.id} agora está {'ATIVO' if curso.ativo else 'INATIVO'}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 radar_cli.py [stats | buscar 'nome' | toggle ID]")
    elif sys.argv[1] == "stats":
        listar_estatisticas()
    elif sys.argv[1] == "buscar":
        buscar_curso(sys.argv[2])
    elif sys.argv[1] == "toggle":
        alternar_status(int(sys.argv[2]))
