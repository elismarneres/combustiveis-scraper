import pandas as pd
import json
import requests
from io import BytesIO
import sys
import re

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
    # Tenta encontrar o cabeçalho automaticamente
    df = None
    for skip in range(5, 15):
        try:
            df_temp = pd.read_excel(BytesIO(response.content), header=skip)
            cols = [str(c).strip().upper() for c in df_temp.columns]
            if any('MUNICIPIO' in c or 'MUNICÍPIO' in c for c in cols) and any('PRODUTO' in c for c in cols):
                df = df_temp
                print(f"✅ Encontrado cabeçalho na linha {skip}")
                break
        except:
            continue
    
    if df is None:
        print("❌ Não foi possível encontrar o cabeçalho")
        sys.exit(1)
        
    print(f"📋 Colunas: {list(df.columns)}")
except Exception as e:
    print(f"❌ Erro ao ler Excel: {e}")
    sys.exit(1)

# Limpa dados
df = df.dropna(how='all')
df.columns = [str(c).strip() for c in df.columns]

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

# ============================================
# AGORA PEGA TODOS OS COMBUSTÍVEIS (SEM FILTRO)
# ============================================
print("📊 Processando TODOS os combustíveis...")

# Converte valor para número
df[col_valor] = df[col_valor].astype(str).str.replace(',', '.').astype(float)

# Agrupa por estado, município e produto
precos_media = df.groupby(
    [col_estado, col_municipio, col_produto]
)[col_valor].mean().reset_index()

print(f"📊 Total de combinações (UF + Cidade + Produto): {len(precos_media)}")

# Gera JSON com TODOS os combustíveis
resultado = {}
for _, row in precos_media.iterrows():
    estado = str(row[col_estado]).strip().upper()
    municipio = str(row[col_municipio]).strip().upper()
    produto = str(row[col_produto]).strip().upper()
    valor = round(float(row[col_valor]), 2)
    
    if estado not in resultado:
        resultado[estado] = {}
    if municipio not in resultado[estado]:
        resultado[estado][municipio] = {}
    
    # Normaliza o nome do combustível para chave JSON
    chave = produto
    
    # Simplifica alguns nomes comuns
    if 'GASOLINA' in produto:
        if 'COMUM' in produto:
            chave = 'GASOLINA_COMUM'
        elif 'ADITIVADA' in produto:
            chave = 'GASOLINA_ADITIVADA'
        else:
            chave = 'GASOLINA'
    elif 'ETANOL' in produto:
        chave = 'ETANOL'
    elif 'DIESEL' in produto:
        if 'S10' in produto:
            chave = 'DIESEL_S10'
        elif 'COMUM' in produto:
            chave = 'DIESEL_COMUM'
        else:
            chave = 'DIESEL'
    elif 'GNV' in produto:
        chave = 'GNV'
    elif 'GLP' in produto or 'GÁS' in produto:
        chave = 'GLP'
    elif 'QUEROSENE' in produto:
        chave = 'QUEROSENE'
    else:
        chave = produto
    
    resultado[estado][municipio][chave] = valor

# ============================================
# ESTATÍSTICAS
# ============================================
print(f"\n📊 Estatísticas dos combustíveis:")

# Conta por tipo de combustível
combustiveis_contagem = {}
for estado in resultado:
    for municipio in resultado[estado]:
        for produto in resultado[estado][municipio]:
            combustiveis_contagem[produto] = combustiveis_contagem.get(produto, 0) + 1

# Ordena e mostra
for produto, count in sorted(combustiveis_contagem.items()):
    print(f"  - {produto}: {count} municípios")

print(f"\n📊 Total de estados: {len(resultado)}")
total_municipios = sum(len(c) for c in resultado.values())
print(f"📊 Total de municípios: {total_municipios}")
total_precos = sum(sum(len(p) for p in c.values()) for c in resultado.values())
print(f"📊 Total de preços registrados: {total_precos}")

# Salva o JSON completo
with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"\n✅ precos.json gerado com sucesso!")

# Mostra exemplos
print("\n📋 Exemplos de preços (primeiros 2 estados):")
for estado in list(resultado.keys())[:2]:
    print(f"\n  {estado}:")
    cidades = list(resultado[estado].keys())[:2]
    for cidade in cidades:
        print(f"    {cidade}:")
        for produto, preco in resultado[estado][cidade].items():
            print(f"      - {produto}: R$ {preco}")
