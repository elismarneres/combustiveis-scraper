import pandas as pd
import json
import requests
from io import BytesIO
import sys
import re
import os
import time

print("🚀 Iniciando script...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


# ============================================================
# 1) DESCOBRE O LINK MAIS RECENTE
# ============================================================
def descobrir_url_mais_recente():
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

    print(f"✅ Arquivo mais recente: {url}")
    print(f"📅 Semana final: {data_fim}")
    return url


url = descobrir_url_mais_recente()

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
    print(f"✅ Download concluído! Tamanho: {len(response.content) / 1024 / 1024:.2f} MB")
except Exception as e:
    print(f"❌ Erro no download: {e}")
    sys.exit(1)


# ============================================================
# 3) LÊ O EXCEL (procura o cabeçalho automaticamente)
# ============================================================
print("📖 Lendo Excel...")

df = None
for skip in range(0, 30):
    try:
        t = pd.read_excel(BytesIO(response.content), header=skip, nrows=5)
        cols = [str(c).upper().strip() for c in t.columns]
        if (
            any('CNPJ' in c for c in cols)
            and any('PRODUTO' in c for c in cols)
            and any('MUNICIPIO' in c or 'MUNICÍPIO' in c for c in cols)
        ):
            df = pd.read_excel(BytesIO(response.content), header=skip)
            print(f"✅ Cabeçalho encontrado na linha {skip}")
            print(f"📋 Colunas: {list(df.columns)}")
            break
    except Exception:
        continue

if df is None:
    print("❌ Não foi possível encontrar o cabeçalho")
    sys.exit(1)


# ============================================================
# 4) LIMPEZA E IDENTIFICAÇÃO DE COLUNAS
# ============================================================
df = df.dropna(how='all')
df.columns = [str(c).strip() for c in df.columns]


def encontrar_coluna(*termos):
    for c in df.columns:
        cu = str(c).upper().strip()
        if all(t in cu for t in termos):
            return c
    return None


col_estado = encontrar_coluna('ESTADO') or encontrar_coluna('UF')
col_municipio = encontrar_coluna('MUNICIPIO') or encontrar_coluna('MUNICÍPIO')
col_produto = encontrar_coluna('PRODUTO')
col_valor = encontrar_coluna('PREÇO') or encontrar_coluna('PRECO')
col_cnpj = encontrar_coluna('CNPJ')
col_razao = encontrar_coluna('RAZÃO') or encontrar_coluna('RAZAO')
col_fantasia = encontrar_coluna('FANTASIA')
col_endereco = encontrar_coluna('ENDEREÇO') or encontrar_coluna('ENDERECO')
col_numero = encontrar_coluna('NÚMERO') or encontrar_coluna('NUMERO')
col_bairro = encontrar_coluna('BAIRRO')
col_cep = encontrar_coluna('CEP')
col_bandeira = encontrar_coluna('BANDEIRA')

faltando = [
    nome for nome, col in [
        ('ESTADO', col_estado), ('MUNICIPIO', col_municipio),
        ('PRODUTO', col_produto), ('PREÇO', col_valor),
    ] if col is None
]
if faltando:
    print(f"❌ Colunas obrigatórias não encontradas: {faltando}")
    sys.exit(1)

print(f"🔍 Colunas: estado={col_estado}, municipio={col_municipio}, "
      f"produto={col_produto}, valor={col_valor}")


# ============================================================
# 5) PROCESSAMENTO
# ============================================================
print("📊 Processando...")


def parse_preco(v):
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


df[col_valor] = df[col_valor].apply(parse_preco)
df = df.dropna(subset=[col_valor])

# Sanidade: preço entre R$ 0,50 e R$ 30,00 por litro
antes = len(df)
df = df[(df[col_valor] >= 0.5) & (df[col_valor] <= 30)]
descartados = antes - len(df)
if descartados > 0:
    print(f"⚠️  {descartados} registros descartados por preço fora do intervalo")

print(f"📊 Registros com preço válido: {len(df)}")

# Filtra etanol e gasolina
df[col_produto] = df[col_produto].astype(str).str.upper().str.strip()
df = df[
    df[col_produto].str.contains('ETANOL', na=False) |
    df[col_produto].str.contains('GASOLINA', na=False)
]
print(f"📊 Registros após filtro: {len(df)}")


def chave_produto(p: str):
    if 'ETANOL' in p:
        return 'ETANOL'
    if 'GASOLINA' in p:
        if 'ADITIVADA' in p:
            return 'GASOLINA_ADITIVADA'
        return 'GASOLINA_COMUM'
    return None


def limpar(v):
    if pd.isna(v):
        return ''
    s = str(v).strip()
    return '' if s.lower() == 'nan' else s


# ============================================================
# 5.1) MÉDIAS POR MUNICÍPIO
# ============================================================
print("📊 Calculando médias...")

medias_df = df.groupby(
    [col_estado, col_municipio, col_produto]
)[col_valor].mean().reset_index()

medias_dict = {}  # {uf: {municipio: {produto: media}}}
for _, row in medias_df.iterrows():
    uf = limpar(row[col_estado]).upper()
    municipio = limpar(row[col_municipio]).upper()
    produto = limpar(row[col_produto]).upper()
    valor = round(float(row[col_valor]), 2)

    chave = chave_produto(produto)
    if chave is None:
        continue

    medias_dict.setdefault(uf, {}).setdefault(municipio, {})[chave] = valor


# ============================================================
# 5.2) AGRUPA POSTOS INDIVIDUAIS
# ============================================================
print("📊 Agrupando postos...")

postos_dict = {}  # {(uf, municipio, cnpj, endereco, numero): {...}}

for _, row in df.iterrows():
    uf = limpar(row[col_estado]).upper()
    municipio = limpar(row[col_municipio]).upper()
    cnpj = limpar(row.get(col_cnpj, '')) if col_cnpj else ''
    razao = limpar(row.get(col_razao, '')) if col_razao else ''
    fantasia = limpar(row.get(col_fantasia, '')) if col_fantasia else ''
    endereco = limpar(row.get(col_endereco, '')) if col_endereco else ''
    numero = limpar(row.get(col_numero, '')) if col_numero else ''
    bairro = limpar(row.get(col_bairro, '')) if col_bairro else ''
    cep = limpar(row.get(col_cep, '')) if col_cep else ''
    bandeira = limpar(row.get(col_bandeira, '')) if col_bandeira else ''

    chave = chave_produto(limpar(row[col_produto]).upper())
    if chave is None:
        continue

    valor = round(float(row[col_valor]), 2)
    posto_key = (uf, municipio, cnpj, endereco, numero)

    if posto_key not in postos_dict:
        end_completo = endereco
        if numero:
            end_completo += f", {numero}"
        if bairro:
            end_completo += f" - {bairro}"

        postos_dict[posto_key] = {
            'cnpj': cnpj,
            'razao': razao,
            'fantasia': fantasia,
            'endereco': end_completo,
            'cep': cep,
            'bandeira': bandeira,
            'precos': {},
        }

    postos_dict[posto_key]['precos'][chave] = valor

print(f"📊 Total de postos únicos: {len(postos_dict)}")


# ============================================================
# 5.4) BUSCA COORDENADAS NA API DE REVENDEDORES DA ANP
# ============================================================
print("\n📊 Buscando coordenadas na API da ANP...")

# 1. Descobre todos os municípios+UF únicos
municipios_uf = set()
for (uf, municipio, *_), posto in postos_dict.items():
    municipios_uf.add((uf, municipio))

print(f"   {len(municipios_uf)} municípios para consultar")

# 2. Consulta a API por município
coords_por_cnpj = {}

for i, (uf, municipio) in enumerate(municipios_uf):
    try:
        resp = requests.get(
            'https://revendedoresapi.anp.gov.br/v1/combustivel',
            params={'uf': uf, 'municipio': municipio},
            headers=headers,
            timeout=60
        )

        if resp.status_code == 200:
            dados = resp.json()
            lista = dados.get('data', [])

            for item in lista:
                cnpj = str(item.get('cnpj', '')).strip()
                lat = item.get('latitude')
                lon = item.get('longitude')

                if cnpj and lat and lon:
                    try:
                        coords_por_cnpj[cnpj] = (float(lat), float(lon))
                    except (ValueError, TypeError):
                        pass

        # Rate limit: 1 segundo entre requisições
        time.sleep(1)

        if (i + 1) % 50 == 0:
            print(f"   {i+1}/{len(municipios_uf)} consultados...")

    except Exception as e:
        print(f"   ⚠️  Erro em {uf}/{municipio}: {e}")
        continue

print(f"✅ Coordenadas obtidas para {len(coords_por_cnpj)} postos")


# ============================================================
# 5.5) ADICIONA LAT/LON AOS POSTOS
# ============================================================
print("📊 Adicionando coordenadas aos postos...")

adicionados = 0
for posto in postos_dict.values():
    cnpj = str(posto.get('cnpj', '')).strip()
    if cnpj in coords_por_cnpj:
        lat, lon = coords_por_cnpj[cnpj]
        posto['lat'] = lat
        posto['lon'] = lon
        adicionados += 1

print(f"✅ {adicionados} postos receberam coordenadas")


# ============================================================
# 5.3) MONTA ESTRUTURA FINAL {UF: {MUNICIPIO: {medias, postos}}}
# ============================================================
resultado = {}

# Médias
for uf, municipios in medias_dict.items():
    for municipio, medias in municipios.items():
        resultado.setdefault(uf, {}).setdefault(municipio, {
            'medias': {},
            'postos': [],
        })
        resultado[uf][municipio]['medias'] = medias

# Postos
for (uf, municipio, *_), posto in postos_dict.items():
    resultado.setdefault(uf, {}).setdefault(municipio, {
        'medias': {},
        'postos': [],
    })
    resultado[uf][municipio]['postos'].append(posto)

# Ordena os postos por preço de gasolina comum (mais barato primeiro)
for uf in resultado:
    for municipio in resultado[uf]:
        postos = resultado[uf][municipio]['postos']
        postos.sort(key=lambda p: p['precos'].get('GASOLINA_COMUM', 999))


# ============================================================
# 6) ESTATÍSTICAS
# ============================================================
print("\n📊 Estatísticas:")

total_estados = len(resultado)
total_municipios = sum(len(c) for c in resultado.values())
total_postos = sum(
    len(m['postos']) for c in resultado.values() for m in c.values()
)

print(f"  Estados: {total_estados}")
print(f"  Municípios: {total_municipios}")
print(f"  Postos: {total_postos}")


# ============================================================
# 7) SALVA O JSON
# ============================================================
print("\n💾 Salvando precos.json...")

with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, separators=(',', ':'))

tamanho = os.path.getsize('precos.json') / 1024 / 1024
print(f"✅ precos.json gerado! Tamanho: {tamanho:.2f} MB")


# ============================================================
# 8) EXEMPLO
# ============================================================
print("\n📋 Exemplo (primeiro estado, primeira cidade):")
primeiro_uf = list(resultado.keys())[0]
primeira_cidade = list(resultado[primeiro_uf].keys())[0]
dados_cidade = resultado[primeiro_uf][primeira_cidade]

print(f"\n  {primeiro_uf} > {primeira_cidade}")
print(f"  Médias: {dados_cidade['medias']}")
print(f"  Postos: {len(dados_cidade['postos'])} cadastrados")
if dados_cidade['postos']:
    p = dados_cidade['postos'][0]
    print(f"  Primeiro posto: {p['fantasia'] or p['razao']}")
    print(f"    {p['endereco']}")
    if 'lat' in p and 'lon' in p:
        print(f"    Coordenadas: {p['lat']}, {p['lon']}")
    else:
        print(f"    Coordenadas: (sem coordenada)")
    print(f"    Preços: {p['precos']}")
