import pandas as pd
import json
import requests
from io import BytesIO
import sys
import os

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
# 2. LEITURA DO EXCEL
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
col_numero = None
col_complemento = None
col_bairro = None
col_cep = None
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
    elif 'NÚMERO' in col_upper or 'NUMERO' in col_upper:
        col_numero = col
    elif 'COMPLEMENTO' in col_upper:
        col_complemento = col
    elif 'BAIRRO' in col_upper:
        col_bairro = col
    elif 'CEP' in col_upper:
        col_cep = col
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
print(f"   Estado:      {col_estado}")
print(f"   Município:   {col_municipio}")
print(f"   Produto:     {col_produto}")
print(f"   Valor:       {col_valor}")
print(f"   CNPJ:        {col_cnpj}")
print(f"   Razão:       {col_razao}")
print(f"   Endereço:    {col_endereco}")
print(f"   Número:      {col_numero}")
print(f"   Complemento: {col_complemento}")
print(f"   Bairro:      {col_bairro}")
print(f"   CEP:         {col_cep}")
print(f"   Bandeira:    {col_bandeira}")
print(f"   Data:        {col_data}")

# ============================================
# 4. PROCESSA POR POSTO
# ============================================
print("📊 Processando por POSTO...")

df[col_valor] = df[col_valor].astype(str).str.replace(',', '.').astype(float)
df = df[df[col_valor] > 0].copy()


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


def limpar(valor):
    """Remove 'nan' e espaços extras"""
    if pd.isna(valor):
        return ''
    texto = str(valor).strip()
    if texto.lower() == 'nan':
        return ''
    return texto


# ============================================
# 5. AGRUPA POR ESTADO
# ============================================
resultado_por_estado = {}

for _, row in df.iterrows():
    estado = limpar(row[col_estado]).upper()
    if not estado or len(estado) != 2:
        continue

    municipio = limpar(row[col_municipio]).upper()
    produto = row['PRODUTO_NORM']
    valor = round(float(row[col_valor]), 2)

    cnpj = limpar(row[col_cnpj]) if col_cnpj else ''
    razao = limpar(row[col_razao]) if col_razao else ''
    endereco = limpar(row[col_endereco]) if col_endereco else ''
    numero = limpar(row[col_numero]) if col_numero else ''
    complemento = limpar(row[col_complemento]) if col_complemento else ''
    bairro = limpar(row[col_bairro]) if col_bairro else ''
    cep = limpar(row[col_cep]) if col_cep else ''
    bandeira = limpar(row[col_bandeira]) if col_bandeira else ''
    data = limpar(row[col_data]) if col_data else ''

    # ✅ ENDEREÇO COMPLETO
    endereco_completo = endereco
    if numero:
        endereco_completo += f', {numero}'
    if complemento:
        endereco_completo += f' - {complemento}'
    if bairro:
        endereco_completo += f' - {bairro}'

    chave_posto = cnpj if cnpj else f"{razao}_{endereco}_{numero}"

    # Inicializa estrutura por estado
    if estado not in resultado_por_estado:
        resultado_por_estado[estado] = {}
    if municipio not in resultado_por_estado[estado]:
        resultado_por_estado[estado][municipio] = {}
    if chave_posto not in resultado_por_estado[estado][municipio]:
        resultado_por_estado[estado][municipio][chave_posto] = {
            'cnpj': cnpj,
            'nome': razao,
            'endereco': endereco_completo,       # ✅ completo
            'rua': endereco,
            'numero': numero,
            'complemento': complemento,
            'bairro': bairro,
            'cep': cep,
            'bandeira': bandeira,
            'data_coleta': data,
            'precos': {}
        }

    resultado_por_estado[estado][municipio][chave_posto]['precos'][produto] = valor

# ============================================
# 6. SALVA UM ARQUIVO POR ESTADO
# ============================================
os.makedirs('precos', exist_ok=True)

print(f"\n💾 Salvando arquivos por estado...")

for estado, dados in resultado_por_estado.items():
    nome_arquivo = f'precos/precos_{estado}.json'
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    total_municipios = len(dados)
    total_postos = sum(len(c) for c in dados.values())
    print(f"   ✅ {estado}: {total_municipios} municípios, {total_postos} postos")

# ============================================
# 7. ESTATÍSTICAS FINAIS
# ============================================
print(f"\n📊 Resumo Geral:")
print(f"   Estados: {len(resultado_por_estado)}")
total_municipios = sum(len(c) for c in resultado_por_estado.values())
print(f"   Municípios totais: {total_municipios}")
total_postos = sum(
    sum(len(p) for p in c.values())
    for c in resultado_por_estado.values()
)
print(f"   Postos totais: {total_postos}")

print(f"\n✅ Todos os arquivos gerados com sucesso!")
