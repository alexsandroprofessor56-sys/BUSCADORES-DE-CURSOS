from app import app, db
with app.app_context():
    print("\n--- ESTRUTURA DO BANCO DE DADOS ---")
    tabelas = db.metadata.tables.keys()
    print(f"Tabelas encontradas: {list(tabelas)}")
    if 'registro_acesso' in tabelas:
        colunas = db.metadata.tables['registro_acesso'].columns.keys()
        print(f"Colunas em 'registro_acesso': {colunas}")
    print("-----------------------------------\n")
