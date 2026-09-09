import pandas as pd
import json
import requests
from io import BytesIO
import sys

print("🚀 Iniciando script...")

url = 'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/2026/revendas_lpc_2026-08-30_2026-09-05.xlsx'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"📥 Baixando: {url}")

try:
    response = requests.get(url, timeout=60, headers=headers)
    response.raise_for_status()
    print(f"✅ Download concluído! Tamanho: {len(response.content)} bytes")
except Exception as e:
    print(f"❌ Erro no download: {e}")
    sys.exit(1)

try:
    df = pd.read_excel(BytesIO(response.content))
    print(f"✅ Arquivo lido com sucesso! {len(df)} registros")
except Exception as e:
    print(f"❌ Erro ao ler Excel: {e}")
    sys.exit(1)

# Mostra as colunas para debug
print(f"📋 Colunas disponíveis: {list(df.columns)}")

# Tenta identificar as colunas
col_estado = None
col_municipio = None
col_produto = None
col_valor = None

for col in df.columns:
    col_upper = col.upper().strip()
    if 'ESTADO' in col_upper or 'SIGLA' in col_upper or 'UF' in col_upper:
        col_estado = col
    elif 'MUNICIPIO' in col_upper or 'MUNICÍPIO' in col_upper or 'CIDADE' in col_upper:
        col_municipio = col
    elif 'PRODUTO' in col_upper:
        col_produto = col
    elif 'VALOR' in col_upper and 'VENDA' in col_upper:
        col_valor = col
    elif 'PREÇO' in col_upper or 'PRECO' in col_upper:
        col_valor = col

if not all([col_estado, col_municipio, col_produto, col_valor]):
    print("❌ Colunas necessárias não encontradas!")
    print("📋 Colunas disponíveis:")
    for col in df.columns:
        print(f"  - {col}")
    sys.exit(1)

print(f"🔍 Usando colunas: {col_estado}, {col_municipio}, {col_produto}, {col_valor}")

# Filtra gasolina e etanol
df_filtrado = df[df[col_produto].str.contains('GASOLINA|ETANOL', case=False, na=False)]
print(f"📊 Registros de gasolina/etanol: {len(df_filtrado)}")

if len(df_filtrado) == 0:
    print("❌ Nenhum registro de gasolina/etanol encontrado!")
    print(f"📋 Produtos disponíveis: {df[col_produto].unique()[:10]}")
    sys.exit(1)

# Converte valor para número
df_filtrado[col_valor] = df_filtrado[col_valor].astype(float)

# Agrupa e calcula a média por estado, município e produto
precos_media = df_filtrado.groupby(
    [col_estado, col_municipio, col_produto]
)[col_valor].mean().reset_index()

print(f"📊 Total de combinações (UF + Cidade + Produto): {len(precos_media)}")

# Gera o JSON com TODOS os municípios
resultado = {}
for _, row in precos_media.iterrows():
    estado = str(row[col_estado]).strip().upper()
    municipio = str(row[col_municipio]).strip().upper()
    produto = str(row[col_produto]).upper()
    valor = round(float(row[col_valor]), 2)
    
    if estado not in resultado:
        resultado[estado] = {}
    if municipio not in resultado[estado]:
        resultado[estado][municipio] = {}
    
    if 'GASOLINA' in produto:
        resultado[estado][municipio]['gasolina'] = valor
    elif 'ETANOL' in produto:
        resultado[estado][municipio]['etanol'] = valor

# Conta quantos municípios têm gasolina e etanol
total_gasolina = 0
total_etanol = 0
for estado in resultado:
    for cidade in resultado[estado]:
        if 'gasolina' in resultado[estado][cidade]:
            total_gasolina += 1
        if 'etanol' in resultado[estado][cidade]:
            total_etanol += 1

print(f"📊 Total de estados: {len(resultado)}")
print(f"📊 Total de municípios com gasolina: {total_gasolina}")
print(f"📊 Total de municípios com etanol: {total_etanol}")

# Salva o JSON completo
with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"✅ precos.json gerado com sucesso!")

# Mostra alguns exemplos
print("\n📋 Exemplos de preços (primeiros 3 estados):")
for estado in list(resultado.keys())[:3]:
    cidades = list(resultado[estado].keys())[:2]
    for cidade in cidades:
        precos = resultado[estado][cidade]
        gas = precos.get('gasolina', 'N/A')
        eta = precos.get('etanol', 'N/A')
        print(f"  {estado} - {cidade}: Gasolina R$ {gas} | Etanol R$ {eta}")
