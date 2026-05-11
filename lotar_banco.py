import sqlite3
import random

db_path = 'instance/database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

categorias = ['Programação', 'IA', 'Design', 'Marketing', 'Finanças', 'Hacking']
fontes = ['Udemy', 'Coursera', 'FGV', 'Google', 'Microsoft', 'EDX']

for i in range(1, 501):
    nome = f"Curso Especialista em {random.choice(categorias)} Nível {i}"
    link = f"https://exemplo.com/curso-{i}"
    cat = random.choice(categorias)
    src = random.choice(fontes)
    
    try:
        cursor.execute("INSERT INTO curso (nome, link_afiliado, categoria, fonte, cliques) VALUES (?, ?, ?, ?, ?)",
                       (nome, link, cat, src, random.randint(0, 100)))
    except:
        continue

conn.commit()
print("🚀 Banco lotado com 500 cursos de elite!")
conn.close()
