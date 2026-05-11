import os
from app import app
from core import db
from core.models import Curso

def menu():
    while True:
        os.system('clear')
        print("=== RADAR ELITE: TERMINAL CONSOLE ===")
        print("1. Listar Cursos Ativos")
        print("2. Buscar Curso por Nome")
        print("3. Check-up de Links (Anti-Cursos Mortos)")
        print("4. Estatísticas do Cartão (30GB)")
        print("5. Sair")
        
        choice = input("\n[#] Selecione uma opção: ")
        
        with app.app_context():
            if choice == '1':
                cursos = Curso.query.filter_by(ativo=True).limit(10).all()
                for c in cursos: print(f"[{c.id}] {c.nome} - {c.plataforma}")
                input("\nPresione Enter para voltar...")
            
            elif choice == '2':
                termo = input("Nome do curso: ")
                cursos = Curso.query.filter(Curso.nome.contains(termo)).all()
                for c in cursos: print(f"[{c.id}] {c.nome} ({c.areas})")
                input("\nPresione Enter para voltar...")
            
            elif choice == '3':
                print("[*] Iniciando faxina...")
                # Aqui você pode chamar a função do validador_links.py
                os.system('python3 validador_links.py')
                input("\nFaxina concluída. Enter para voltar...")
                
            elif choice == '4':
                os.system('df -h /mnt/cartao_cursos')
                input("\nPresione Enter para voltar...")
                
            elif choice == '5':
                break

if __name__ == "__main__":
    menu()
