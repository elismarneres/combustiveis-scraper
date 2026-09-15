import pandas as pd
import requests
from io import BytesIO
import json

url = 'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/2026/revendas_lpc_2026-09-06_2026-09-12.xlsx'
headers = {'User-Agent': 'Mozilla/5.0'}

print("📥 Baixando...")
r = requests.get(url, headers=headers, timeout=120)
print(f"   xlsx: {len(r.content) / 1024 / 1024:.2f} MB")

# ============================================================
# 1) LÊ SEM CABEÇALHO PRA VER A ESTRUTURA
# ============================================================
print("\n📖 Lendo primeiras 20 linhas (sem cabeçalho)...")
df_raw = pd.read_excel(BytesIO(r.content), header=None, nrows=20)

for i, row in df_raw.iterrows():
    # Mostra só as primeiras 5 colunas, truncadas
    vals = [str(v)[:25] for v in row.values[:5]]
    print(f"  Linha {i:2d}: {vals}")

# ============================================================
# 2) ENCONTRA A LINHA DE CABEÇALHO CORRETA
# ============================================================
print("\n🔎 Procurando cabeçalho...")

df = None
linha_cabecalho = None

for skip in range(0, 30):
    try:
        t = pd.read_excel(BytesIO(r.content), header=skip, nrows=5)
        cols = [str(c).upper().strip() for c in t.columns]

        tem_cnpj = any('CNPJ' in c for c in cols)
        tem_produto = any('PRODUTO' in c for c in cols)
        tem_municipio = any('MUNICIPIO' in c or 'MUNICÍPIO' in c for c in cols)

        if tem_cnpj and tem_produto and tem_municipio:
            df = pd.read_excel(BytesIO(r.content), header=skip)
            linha_cabecalho = skip
            print(f"✅ Cabeçalho encontrado na linha {skip}")
            print(f"📋 Colunas: {list(df.columns)}")
            break
    except Exception as e:
        continue

if df is None:
    print("❌ Não foi possível encontrar o cabeçalho correto")
    print("💡 Mostrando todas as linhas 0-30 com mais colunas:")
    df_raw2 = pd.read_excel(BytesIO(r.content), header=None, nrows=30)
    for i, row in df_raw2.iterrows():
        vals = [str(v)[:20] for v in row.values[:10]]
        print(f"  Linha {i:2d}: {vals}")
    exit(1)

# ============================================================
# 3) DIAGNÓSTICO
# ============================================================
print(f"\n📊 Total de linhas na planilha: {len(df)}")

col_produto = next(c for c in df.columns if 'PRODUTO' in str(c).upper())
col_estado = next(
    (c for c in df.columns if 'ESTADO' in str(c).upper() or 'UF' in str(c).upper()),
    None
)
col_municipio = next(
    c for c in df.columns
    if 'MUNICIPIO' in str(c).upper() or 'MUNICÍPIO' in str(c).upper()
)

print(f"🔍 col_produto = {col_produto}")
print(f"🔍 col_estado = {col_estado}")
print(f"🔍 col_municipio = {col_municipio}")

df[col_produto] = df[col_produto].astype(str).str.upper()
df_filtrado = df[
    df[col_produto].str.contains('ETANOL', na=False) |
    df[col_produto].str.contains('GASOLINA', na=False)
]

print(f"\n📊 Após filtro (etanol + gasolina): {len(df_filtrado)} linhas")

if col_estado:
    print(f"📊 Municípios únicos: {df_filtrado.groupby([col_estado, col_municipio]).ngroups}")
else:
    print(f"📊 Municípios únicos: {df_filtrado.groupby([col_municipio]).ngroups}")

col_cnpj = next((c for c in df.columns if 'CNPJ' in str(c).upper()), None)
col_end = next((c for c in df.columns if 'ENDEREÇO' in str(c).upper()), None)

print(f"🔍 col_cnpj = {col_cnpj}")
print(f"🔍 col_end = {col_end}")

if col_cnpj and col_end:
    postos_unicos = df_filtrado.groupby([col_cnpj, col_end]).ngroups
    print(f"📊 Postos únicos (CNPJ + endereço): {postos_unicos}")

# ============================================================
# 4) ESTIMATIVA DE TAMANHO
# ============================================================
print("\n📏 Estimando tamanho do JSON...")

amostra = df_filtrado.head(1000).to_dict(orient='records')
amostra_json = json.dumps(amostra, ensure_ascii=False)
tamanho_amostra = len(amostra_json)
tamanho_estimado = (tamanho_amostra / 1000) * len(df_filtrado)

print(f"   Amostra (1000 registros): {tamanho_amostra / 1024:.1f} KB")
print(f"   Estimativa total: {tamanho_estimado / 1024 / 1024:.2f} MB")

# ============================================================
# 5) BREAKDOWN
# ============================================================
print(f"\n📊 Breakdown por produto:")
for prod, count in df_filtrado[col_produto].value_counts().items():
    print(f"   {prod}: {count} linhas")

if col_estado:
    print(f"\n📊 Top 5 estados por volume:")
    for uf, count in df_filtrado[col_estado].value_counts().head(5).items():
        print(f"   {uf}: {count} linhas")

print(f"\n📊 Primeiras 3 linhas de exemplo:")
for _, row in df_filtrado.head(3).iterrows():
    print(f"   {dict(row)}")
