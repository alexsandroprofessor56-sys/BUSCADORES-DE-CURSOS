import requests
from bs4 import BeautifulSoup
import validators

def testar_link(url):
    if not validators.url(url):
        return False, "URL Inválida"
    try:
        # Tenta acessar o site. Se demorar mais de 5s, ignora (IP morto)
        res = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            texto = soup.get_text().lower()
            # Verifica se o site menciona certificado
            tem_cert = "certificado" in texto or "certificate" in texto
            return True, "Online com Certificado" if tem_cert else "Online sem Certificado"
        return False, f"Erro HTTP: {res.status_code}"
    except:
        return False, "Link Offline/Inativo"

# Teste rápido
print(f"Testando Google: {testar_link('https://www.google.com')}")
