from app import app
from core import db
from core.models import Curso

def popular_com_detalhes():
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Lista base (Os 12 da Bradesco)
        bradesco_nomes = [
            "Atendimento ao Público", "Como Conseguir um Novo Emprego", "Comunicação Empresarial",
            "Comunicação Escrita", "Proteção Financeira", "Controle de Impulso",
            "Desenvolvimento Profissional", "Educação Financeira", "Inclusividade",
            "Língua Portuguesa", "Oficina de Gramática", "Organização Pessoal"
        ]
        
        cursos_finais = []
        
        # 1. Adiciona os da Bradesco
        for nome in bradesco_nomes:
            cursos_finais.append(Curso(
                nome=nome, 
                link_afiliado="https://www.ev.org.br/cursos",
                plataforma="Fundação Bradesco",
                areas="Desenvolvimento Profissional"
            ))
            
        # 2. Completa até 168 com Cisco e Microsoft alternados
        reforcos = [
            ("Introdução à Cibersegurança", "Cisco", "Segurança Digital", "https://www.netacad.com"),
            ("Fundamentos de Python", "Cisco", "Programação", "https://www.netacad.com"),
            ("Azure Fundamentals", "Microsoft", "Nuvem", "https://learn.microsoft.com")
        ]
        
        while len(cursos_finais) < 168:
            base, fonte, cat, link = reforcos[len(cursos_finais) % 3]
            num = len(cursos_finais) + 1
            cursos_finais.append(Curso(
                nome=f"{base} #{num}",
                link_afiliado=link,
                plataforma=fonte,
                areas=cat
            ))
            
        db.session.add_all(cursos_finais)
        db.session.commit()
        print(f"Sucesso! {len(cursos_finais)} cursos criados com Fonte e Categoria.")

popular_com_detalhes()
