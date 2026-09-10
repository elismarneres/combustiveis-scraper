import pandas as pd
import json
import requests
from io import BytesIO
import sys
import re

print("🚀 Iniciando script...")

# ============================================
# 1. DOWNLOAD DO ARQUIVO DA ANP
# ============================================
url = 'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/2026/revendas_lpc_2026-08-30_2026-09-05.xlsx'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"📥 Baixando: {url}")

try:
    response = requests.get(url, timeout=120, headers=headers)
    response.raise_for_status()
    print(f"✅ Download concluído! Tamanho: {len(response.content)} bytes")
except Exception as e:
    print(f"❌ Erro no download: {e}")
    sys.exit(1)

# ============================================
# 2. LEITURA DO EXCEL (encontra o cabeçalho)
# ============================================
try:
    df = None
    for skip in range(5, 20):
        try:
            df_temp = pd.read_excel(BytesIO(response.content), header=skip)
            cols = [str(c).strip().upper() for c in df_temp.columns]
            if any('MUNICIPIO' in c or 'MUNICÍPIO' in c for c in cols) and any('PRODUTO' in c for c in cols):
                df = df_temp
                print(f"✅ Encontrado cabeçalho na linha {skip}")
                break
        except Exception:
            continue

    if df is None:
        print("❌ Não foi possível encontrar o cabeçalho")
        sys.exit(1)

    print(f"📋 Colunas: {list(df.columns)}")
except Exception as e:
    print(f"❌ Erro ao ler Excel: {e}")
    sys.exit(1)

# ============================================
# 3. LIMPEZA E IDENTIFICAÇÃO DE COLUNAS
# ============================================
df = df.dropna(how='all')
df.columns = [str(c).strip() for c in df.columns]

col_estado = None
col_municipio = None
col_produto = None
col_valor = None
col_cnpj = None
col_razao = None
col_endereco = None
col_bairro = None
col_bandeira = None
col_data = None

for col in df.columns:
    col_upper = col.upper().strip()
    if 'ESTADO' in col_upper or 'SIGLA' in col_upper or col_upper == 'UF':
        col_estado = col
    elif 'MUNICIPIO' in col_upper or 'MUNICÍPIO' in col_upper or 'CIDADE' in col_upper:
        col_municipio = col
    elif 'PRODUTO' in col_upper:
        col_produto = col
    elif 'VALOR' in col_upper and 'VENDA' in col_upper:
        col_valor = col
    elif ('PREÇO' in col_upper or 'PRECO' in col_upper) and col_valor is None:
        col_valor = col
    elif 'CNPJ' in col_upper:
        col_cnpj = col
    elif 'RAZÃO' in col_upper or 'RAZAO' in col_upper or 'REVENDEDOR' in col_upper:
        col_razao = col
    elif 'ENDEREÇO' in col_upper or 'ENDERECO' in col_upper:
        col_endereco = col
    elif 'BAIRRO' in col_upper:
        col_bairro = col
    elif 'BANDEIRA' in col_upper:
        col_bandeira = col
    elif 'DATA' in col_upper and 'COLETA' in col_upper:
        col_data = col

if not all([col_estado, col_municipio, col_produto, col_valor]):
    print("❌ Colunas necessárias não encontradas!")
    print("📋 Colunas disponíveis:")
    for col in df.columns:
        print(f"  - {col}")
    sys.exit(1)

print(f"🔍 Colunas identificadas:")
print(f"   Estado:    {col_estado}")
print(f"   Município: {col_municipio}")
print(f"   Produto:   {col_produto}")
print(f"   Valor:     {col_valor}")
print(f"   CNPJ:      {col_cnpj}")
print(f"   Razão:     {col_razao}")
print(f"   Endereço:  {col_endereco}")
print(f"   Bairro:    {col_bairro}")
print(f"   Bandeira:  {col_bandeira}")
print(f"   Data:      {col_data}")

# ============================================
# 4. PROCESSA POR POSTO (SEM AGRUPAR)
# ============================================
print("📊 Processando por POSTO...")

# Converte valor para número
df[col_valor] = df[col_valor].astype(str).str.replace(',', '.').astype(float)
df = df[df[col_valor] > 0].copy()


# Normaliza nome do produto
def normalizar_produto(produto):
    produto = str(produto).upper()
    if 'GASOLINA' in produto:
        if 'COMUM' in produto:
            return 'GASOLINA_COMUM'
        if 'ADITIVADA' in produto:
            return 'GASOLINA_ADITIVADA'
        return 'GASOLINA'
    if 'ETANOL' in produto:
        return 'ETANOL'
    if 'DIESEL' in produto:
        if 'S10' in produto:
            return 'DIESEL_S10'
        if 'COMUM' in produto:
            return 'DIESEL_COMUM'
        return 'DIESEL'
    if 'GNV' in produto:
        return 'GNV'
    if 'GLP' in produto:
        return 'GLP'
    return produto


df['PRODUTO_NORM'] = df[col_produto].apply(normalizar_produto)

# ============================================
# 5. ESTRUTURA DO JSON POR POSTO
# ============================================
resultado = {}

for _, row in df.iterrows():
    estado = str(row[col_estado]).strip().upper()
    municipio = str(row[col_municipio]).strip().upper()
    produto = row['PRODUTO_NORM']
    valor = round(float(row[col_valor]), 2)

    cnpj = str(row[col_cnpj]).strip() if col_cnpj else ''
    razao = str(row[col_razao]).strip() if col_razao else ''
    endereco = str(row[col_endereco]).strip() if col_endereco else ''
    bairro = str(row[col_bairro]).strip() if col_bairro else ''
    bandeira = str(row[col_bandeira]).strip() if col_bandeira else ''
    data = str(row[col_data]).strip() if col_data else ''

    chave_posto = cnpj if cnpj else f"{razao}_{endereco}"

    if estado not in resultado:
        resultado[estado] = {}
    if municipio not in resultado[estado]:
        resultado[estado][municipio] = {}
    if chave_posto not in resultado[estado][municipio]:
        resultado[estado][municipio][chave_posto] = {
            'cnpj': cnpj,
            'nome': razao,
            'endereco': endereco,
            'bairro': bairro,
            'bandeira': bandeira,
            'data_coleta': data,
            'precos': {}
        }

    resultado[estado][municipio][chave_posto]['precos'][produto] = valor

# ============================================
# 6. ESTATÍSTICAS
# ============================================
print(f"\n📊 Estatísticas:")
print(f"   Estados: {len(resultado)}")
total_municipios = sum(len(c) for c in resultado.values())
print(f"   Municípios: {total_municipios}")
total_postos = sum(sum(len(p) for p in c.values()) for c in resultado.values())
print(f"   Postos: {total_postos}")

# ============================================
# 7. SALVA O JSON
# ============================================
with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"\n✅ precos.json gerado com sucesso!")

# Mostra exemplos
print("\n📋 Exemplos (primeiros 2 estados):")
for estado in list(resultado.keys())[:2]:
    print(f"\n  {estado}:")
    cidades = list(resultado[estado].keys())[:2]
    for cidade in cidades:
        print(f"    {cidade}:")
        postos = list(resultado[estado][cidade].items())[:2]
        for cnpj, dados in postos:
            print(f"      - {dados['nome']} ({cnpj})")
            for prod, preco in dados['precos'].items():
                print(f"          {prod}: R$ {preco}")
