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
    # Pula as primeiras linhas que não são dados
    # O cabeçalho real geralmente está na linha 8 ou 9
    df = pd.read_excel(
        BytesIO(response.content), 
        header=8,  # Pula as primeiras 8 linhas
        skiprows=0
    )
    print(f"✅ Arquivo lido com sucesso! {len(df)} registros")
    print(f"📋 Colunas: {list(df.columns)}")
except Exception as e:
    print(f"❌ Erro ao ler Excel: {e}")
    sys.exit(1)

# Remove linhas vazias
df = df.dropna(how='all')

# Se a primeira linha ainda for lixo, usa a primeira linha válida como cabeçalho
if 'Unnamed' in str(df.columns[0]):
    print("🔍 Colunas não identificadas, tentando encontrar o cabeçalho real...")
    # Pula mais linhas (tenta até a linha 15)
    for skip in range(5, 20):
        try:
            df_temp = pd.read_excel(
                BytesIO(response.content), 
                header=skip
            )
            # Verifica se encontrou colunas com nomes esperados
            cols = [str(c).upper() for c in df_temp.columns]
            if any('ESTADO' in c for c in cols) or any('MUNICIPIO' in c for c in cols):
                df = df_temp
                print(f"✅ Encontrado cabeçalho na linha {skip}")
                print(f"📋 Colunas: {list(df.columns)}")
                break
        except:
            continue

# Limpa espaços extras e linhas vazias
df = df.dropna(how='all')
df.columns = [str(c).strip() for c in df.columns]

print(f"📊 Total de registros após limpeza: {len(df)}")

# Identifica colunas
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
df_filtrado = df[df[col_produto].astype(str).str.contains('GASOLINA|ETANOL', case=False, na=False)]
print(f"📊 Registros de gasolina/etanol: {len(df_filtrado)}")

if len(df_filtrado) == 0:
    print("❌ Nenhum registro de gasolina/etanol encontrado!")
    print(f"📋 Produtos disponíveis: {df[col_produto].unique()[:20]}")
    sys.exit(1)

# Converte valor para número
try:
    df_filtrado[col_valor] = df_filtrado[col_valor].astype(float)
except:
    # Tenta substituir vírgula por ponto
    df_filtrado[col_valor] = df_filtrado[col_valor].astype(str).str.replace(',', '.').astype(float)

# Agrupa e calcula média
precos_media = df_filtrado.groupby(
    [col_estado, col_municipio, col_produto]
)[col_valor].mean().reset_index()

print(f"📊 Total de combinações (UF + Cidade + Produto): {len(precos_media)}")

# Gera JSON
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

# Conta municípios
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

with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"✅ precos.json gerado com sucesso!")

# Mostra exemplos
print("\n📋 Exemplos de preços (primeiros 3 estados):")
for estado in list(resultado.keys())[:3]:
    cidades = list(resultado[estado].keys())[:2]
    for cidade in cidades:
        precos = resultado[estado][cidade]
        gas = precos.get('gasolina', 'N/A')
        eta = precos.get('etanol', 'N/A')
        print(f"  {estado} - {cidade}: Gasolina R$ {gas} | Etanol R$ {eta}")
