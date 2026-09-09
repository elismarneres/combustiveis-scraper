import pandas as pd
import json
import requests
from io import BytesIO
import sys

# ============================================
# URL DO ARQUIVO EXCEL DA ANP
# ============================================
url_anp = 'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/2026/revendas_lpc_2026-08-30_2026-09-05.xlsx'

print(f"📥 Baixando: {url_anp}")

try:
    response = requests.get(url_anp, timeout=60)
    response.raise_for_status()
except Exception as e:
    print(f"❌ Erro ao baixar o arquivo: {e}")
    sys.exit(1)

try:
    # Lê o arquivo Excel diretamente
    excel_data = BytesIO(response.content)
    df = pd.read_excel(excel_data)
    print(f"✅ Baixado! {len(df)} registros")
except Exception as e:
    print(f"❌ Erro ao ler o Excel: {e}")
    sys.exit(1)

# Mostra as colunas disponíveis para debug
print(f"📋 Colunas disponíveis: {list(df.columns)}")

# Tenta identificar as colunas corretas
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
    print("❌ Colunas não encontradas. Colunas disponíveis:")
    for col in df.columns:
        print(f"  - {col}")
    sys.exit(1)

print(f"🔍 Usando colunas: {col_estado}, {col_municipio}, {col_produto}, {col_valor}")

# Filtra gasolina e etanol
df_filtrado = df[df[col_produto].str.contains('GASOLINA|ETANOL', case=False, na=False)]

if len(df_filtrado) == 0:
    print("❌ Nenhum registro de gasolina/etanol encontrado")
    sys.exit(1)

# Converte valor para número
df_filtrado[col_valor] = df_filtrado[col_valor].astype(float)

# Calcula média por cidade
precos = df_filtrado.groupby([col_estado, col_municipio, col_produto])[col_valor].mean().reset_index()

# Gera JSON
resultado = {}
for _, row in precos.iterrows():
    estado = str(row[col_estado]).strip().upper()
    municipio = str(row[col_municipio]).strip().upper()
    produto = str(row[col_produto]).upper()
    valor = round(row[col_valor], 2)
    
    if estado not in resultado:
        resultado[estado] = {}
    if municipio not in resultado[estado]:
        resultado[estado][municipio] = {}
    
    if 'GASOLINA' in produto:
        resultado[estado][municipio]['gasolina'] = valor
    else:
        resultado[estado][municipio]['etanol'] = valor

with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"✅ precos.json gerado com sucesso!")
print(f"📊 {len(resultado)} estados, {sum(len(c) for c in resultado.values())} cidades")

# Mostra exemplos
print("\n📋 Exemplos de preços:")
for estado in list(resultado.keys())[:3]:
    cidades = list(resultado[estado].keys())[:2]
    for cidade in cidades:
        precos_cidade = resultado[estado][cidade]
        gas = precos_cidade.get('gasolina', 'N/A')
        eta = precos_cidade.get('etanol', 'N/A')
        print(f"  {estado} - {cidade}: Gasolina R$ {gas} | Etanol R$ {eta}")
