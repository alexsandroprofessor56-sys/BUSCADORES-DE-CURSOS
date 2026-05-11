from app import app
from core import db
from core.models import Curso

def popular():
    with app.app_context():
        # Adiciona sem apagar os anteriores, ou use drop_all() se quiser limpar
        # db.create_all()

        novas_fontes = [
            # --- ACADÊMICO E UNIVERSITÁRIO ---
            {"n": "Introdução à Bioestatística", "l": "https://poca.ufscar.br/", "o": "UFSCar (POCA)", "c": "Ciência", "nv": "Médio"},
            {"n": "Escrita Acadêmica", "l": "https://lumina.ufrgs.br/", "o": "UFRGS (Lúmina)", "c": "Educação", "nv": "Iniciante"},
            {"n": "Direitos Humanos", "l": "https://www.usp.br/sce/", "o": "USP (Aulas Livres)", "c": "Humanas", "nv": "Iniciante"},
            {"n": "Cálculo Diferencial", "l": "https://univesp.br/cursos", "o": "UNIVESP", "c": "Exatas", "nv": "Avançado"},
            {"n": "História da Arte", "l": "https://www.coursera.org/mooc", "o": "MOOC (Mundo)", "c": "Arte", "nv": "Iniciante"},
            
            # --- TECNOLOGIA E HARDWARE ---
            {"n": "Arquitetura de Redes", "l": "https://www.huawei.com/br/talents", "o": "Huawei Talent", "c": "Redes", "nv": "Avançado"},
            {"n": "Internet das Coisas (IoT)", "l": "https://www.samsung.com.br/samsungocean/", "o": "Samsung Ocean", "c": "Tecnologia", "nv": "Médio"},
            {"n": "Desenvolvimento em Java", "l": "https://www.oracle.com/br/education/", "o": "Oracle University", "c": "Programação", "nv": "Avançado"},
            {"n": "Fundamentos de Linux", "l": "https://training.linuxfoundation.org/", "o": "Linux Foundation", "c": "Sistemas", "nv": "Médio"},
            {"n": "Criação de Jogos (Unity)", "l": "https://learn.unity.com/", "o": "Unity Learn", "c": "Games", "nv": "Iniciante"},

            # --- PROFISSIONALIZANTES E IDIOMAS ---
            {"n": "Mecânica Automotiva", "l": "https://www.escolavirtual.org.br/", "o": "Fundação Bradesco", "c": "Técnico", "nv": "Médio"},
            {"n": "Culinária Básica", "l": "https://www.eduk.com.br/", "o": "EduK (Aulas Gratuitas)", "c": "Gastronomia", "nv": "Iniciante"},
            {"n": "Coreano para Iniciantes", "l": "https://www.kingsejong.org/", "o": "King Sejong Institute", "c": "Idiomas", "nv": "Iniciante"},
            {"n": "Francês Básico", "l": "https://www.fun-mooc.fr/", "o": "AF (FUN MOOC)", "c": "Idiomas", "nv": "Iniciante"},
            {"n": "Fotografia de Celular", "l": "https://www.nikonschool.com/", "o": "Nikon School", "c": "Arte", "nv": "Iniciante"},

            # --- NEGÓCIOS E GOVERNO ---
            {"n": "Inovação Digital", "l": "https://www.apexbrasil.com.br/", "o": "ApexBrasil", "c": "Negócios", "nv": "Médio"},
            {"n": "Gestão Pública", "l": "https://www.tce.sp.gov.br/epcp/", "o": "EPCP (TCE-SP)", "c": "Governo", "nv": "Médio"},
            {"n": "Exportação para PMEs", "l": "https://www.gov.br/apexbrasil/", "o": "Passaporte para o Mundo", "c": "Negócios", "nv": "Avançado"},
            {"n": "Libras (Língua de Sinais)", "l": "https://www.escolavirtual.gov.br/", "o": "ENAP", "c": "Social", "nv": "Iniciante"},
            {"n": "Introdução ao Direito Civil", "l": "https://www12.senado.leg.br/institucional/edusenado", "o": "Saberes (Senado)", "c": "Direito", "nv": "Médio"}
        ]

        for f in novas_fontes:
            db.session.add(Curso(
                nome=f['n'], 
                link_afiliado=f['l'], 
                plataforma=f['o'], 
                areas=f['c'], 
                nivel=f['nv'], 
                cliques=0
            ))
        
        db.session.commit()
        print(f"MAIS FONTES ADICIONADAS! Total de novas entradas: {len(novas_fontes)}")

if __name__ == "__main__":
    popular()
