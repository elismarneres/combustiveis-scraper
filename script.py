import pandas as pd
import json
import requests
from io import BytesIO
import sys

print("🚀 Iniciando script...")

# Tenta primeiro o CSV, depois o Excel
urls = [
    'https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/ca-2026-08.csv',
    'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/2026/revendas_lpc_2026-08-30_2026-09-05.xlsx'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

df = None

for url in urls:
    print(f"📥 Tentando: {url}")
    try:
        response = requests.get(url, timeout=60, headers=headers)
        response.raise_for_status()
        print(f"✅ Download concluído! Tamanho: {len(response.content)} bytes")
        
        # Tenta ler como CSV ou Excel
        try:
            if url.endswith('.csv'):
                df = pd.read_csv(BytesIO(response.content), encoding='latin-1', sep=';', decimal=',')
            else:
                df = pd.read_excel(BytesIO(response.content))
            print(f"✅ Arquivo lido com sucesso! {len(df)} registros")
            break
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            continue
    except Exception as e:
        print(f"❌ Erro no download: {e}")
        continue

if df is None:
    print("❌ Não foi possível baixar nenhum arquivo")
    sys.exit(1)

# Resto do script (identificar colunas, filtrar, gerar JSON)
# ... (código que você já tinha)
