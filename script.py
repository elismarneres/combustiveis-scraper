import pandas as pd
import json
import requests
from io import BytesIO
import sys
import re
from datetime import date, timedelta

print("🚀 Iniciando script...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


# ============================================================
# 1) DESCOBRE O LINK MAIS RECENTE DA ANP
# ============================================================
def descobrir_url_mais_recente():
    """
    Acessa a página estática da ANP com as últimas semanas pesquisadas
    e retorna a URL do arquivo .xlsx mais recente.
    """
    pagina = (
        'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/'
        'precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas'
    )

    print(f"🔎 Buscando arquivos em: {pagina}")
    try:
        resp = requests.get(pagina, headers=headers, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"⚠️  Erro ao acessar página da ANP: {e}")
        return None

    # Regex para pegar links do tipo revendas_lpc_AAAA-MM-DD_AAAA-MM-DD.xlsx
    padrao = re.compile(
        r'href="([^"]*revendas_lpc_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.xlsx)"',
        re.IGNORECASE,
    )

    encontrados = []
    for match in padrao.finditer(resp.text):
        href = match.group(1)
        data_fim = match.group(3)

        if href.startswith('/'):
            href = 'https://www.gov.br' + href
        elif not href.startswith('http'):
            href = (
                'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/'
                'precos/arquivos-lpc/' + href
            )

        encontrados.append((data_fim, href))

    if not encontrados:
        print("⚠️  Nenhum arquivo .xlsx encontrado via scraping.")
        return None

    encontrados.sort(key=lambda x: x[0], reverse=True)
    data_fim, url = encontrados[0]

    print(f"✅ Arquivo mais recente (via scraping): {url}")
    print(f"📅 Semana final: {data_fim}")
    return url


def url_ultima_semana(tentativas=6):
    """
    Fallback: constrói a URL da última semana da ANP (domingo a sábado)
    e testa até `tentativas` semanas para trás.
    """
    hoje = date.today()
    # Descobre o sábado mais recente
    dias_desde_sabado = (hoje.weekday() - 5) % 7
    sabado = hoje - timedelta(days=dias_desde_sabado)

    for i in range(tentativas):
        sab = sabado - timedelta(days=7 * i)
        dom = sab - timedelta(days=6)
        ano = dom.year
        nome = f"revendas_lpc_{dom:%Y-%m-%d}_{sab:%Y-%m-%d}.xlsx"
        url = (
            f"https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/"
            f"precos/arquivos-lpc/{ano}/{nome}"
        )
        print(f"🔎 Testando: {url}")
        try:
            r = requests.head(url, headers=headers, timeout=15, allow_redirects=True)
            if r.status_code == 200:
                print(f"✅ URL encontrada por data: {url}")
                return url
        except Exception as e:
            print(f"   ⚠️  {e}")
            continue

    return None


# Tenta primeiro por scraping, depois por data
url = descobrir_url_mais_recente()

if not url:
    print("⚠️  Scraping falhou, tentando por data...")
    url = url_ultima_semana()

if not url:
    print("❌ Não foi possível descobrir a URL. Abortando.")
    sys.exit(1)


# ============================================================
# 2) DOWNLOAD
# ============================================================
print(f"📥 Baixando: {url}")

try:
    response = requests.get(url, timeout=120, headers=headers)
    response.raise_for_status()
    print(f"✅ Download concluído! Tamanho: {len(response.content)} bytes")
except Exception as e:
    print(f"❌ Erro no download: {e}")
    sys.exit(1)


# ============================================================
# 3) LÊ O EXCEL
# ============================================================
try:
    df = None
    for skip in range(5, 15):
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


# ============================================================
# 4) LIMPEZA E IDENTIFICAÇÃO DE COLUNAS
# ============================================================
df = df.dropna(how='all')
df.columns = [str(c).strip() for c in df.columns]

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


# ============================================================
# 5) PROCESSA TODOS OS COMBUSTÍVEIS
# ============================================================
print("📊 Processando TODOS os combustíveis...")

df[col_valor] = df[col_valor].astype(str).str.replace(',', '.').astype(float)

precos_media = df.groupby(
    [col_estado, col_municipio, col_produto]
)[col_valor].mean().reset_index()

print(f"📊 Total de combinações (UF + Cidade + Produto): {len(precos_media)}")

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

    chave = produto
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


# ============================================================
# 6) ESTATÍSTICAS
# ============================================================
print(f"\n📊 Estatísticas dos combustíveis:")

combustiveis_contagem = {}
for estado in resultado:
    for municipio in resultado[estado]:
        for produto in resultado[estado][municipio]:
            combustiveis_contagem[produto] = combustiveis_contagem.get(produto, 0) + 1

for produto, count in sorted(combustiveis_contagem.items()):
    print(f"  - {produto}: {count} municípios")

print(f"\n📊 Total de estados: {len(resultado)}")
total_municipios = sum(len(c) for c in resultado.values())
print(f"📊 Total de municípios: {total_municipios}")
total_precos = sum(sum(len(p) for p in c.values()) for c in resultado.values())
print(f"📊 Total de preços registrados: {total_precos}")


# ============================================================
# 7) SALVA O JSON
# ============================================================
with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"\n✅ precos.json gerado com sucesso!")

print("\n📋 Exemplos de preços (primeiros 2 estados):")
for estado in list(resultado.keys())[:2]:
    print(f"\n  {estado}:")
    cidades = list(resultado[estado].keys())[:2]
    for cidade in cidades:
        print(f"    {cidade}:")
        for produto, preco in resultado[estado][cidade].items():
            print(f"      - {produto}: R$ {preco}")
