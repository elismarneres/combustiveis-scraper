# ============================================
# IDENTIFICA COLUNAS ADICIONAIS (por posto)
# ============================================
col_cnpj = None
col_razao = None
col_endereco = None
col_bairro = None
col_bandeira = None
col_data = None

for col in df.columns:
    col_upper = col.upper().strip()
    if 'CNPJ' in col_upper:
        col_cnpj = col
    elif 'RAZÃO' in col_upper or 'RAZAO' in col_upper or 'REVENDEDOR' in col_upper or 'NOME' in col_upper:
        col_razao = col
    elif 'ENDEREÇO' in col_upper or 'ENDERECO' in col_upper:
        col_endereco = col
    elif 'BAIRRO' in col_upper:
        col_bairro = col
    elif 'BANDEIRA' in col_upper:
        col_bandeira = col
    elif 'DATA' in col_upper:
        col_data = col

print(f"🔍 Colunas adicionais:")
print(f"   CNPJ: {col_cnpj}")
print(f"   Razão: {col_razao}")
print(f"   Endereço: {col_endereco}")
print(f"   Bairro: {col_bairro}")
print(f"   Bandeira: {col_bandeira}")
print(f"   Data: {col_data}")

# ============================================
# PROCESSA POR POSTO (SEM AGRUPAR)
# ============================================
print("📊 Processando por POSTO...")

# Converte valor para número
df[col_valor] = df[col_valor].astype(str).str.replace(',', '.').astype(float)

# Filtra apenas linhas com valor válido
df = df[df[col_valor] > 0].copy()

# Normaliza nome do produto
def normalizar_produto(produto):
    produto = str(produto).upper()
    if 'GASOLINA' in produto:
        if 'COMUM' in produto: return 'GASOLINA_COMUM'
        if 'ADITIVADA' in produto: return 'GASOLINA_ADITIVADA'
        return 'GASOLINA'
    if 'ETANOL' in produto: return 'ETANOL'
    if 'DIESEL' in produto:
        if 'S10' in produto: return 'DIESEL_S10'
        if 'COMUM' in produto: return 'DIESEL_COMUM'
        return 'DIESEL'
    if 'GNV' in produto: return 'GNV'
    if 'GLP' in produto: return 'GLP'
    return produto

df['PRODUTO_NORM'] = df[col_produto].apply(normalizar_produto)

# ============================================
# ESTRUTURA DO JSON POR POSTO
# ============================================
resultado = {}

for _, row in df.iterrows():
    estado = str(row[col_estado]).strip().upper()
    municipio = str(row[col_municipio]).strip().upper()
    produto = row['PRODUTO_NORM']
    valor = round(float(row[col_valor]), 2)
    
    # Informações do posto
    cnpj = str(row[col_cnpj]).strip() if col_cnpj else ''
    razao = str(row[col_razao]).strip() if col_razao else ''
    endereco = str(row[col_endereco]).strip() if col_endereco else ''
    bairro = str(row[col_bairro]).strip() if col_bairro else ''
    bandeira = str(row[col_bandeira]).strip() if col_bandeira else ''
    data = str(row[col_data]).strip() if col_data else ''
    
    # Chave única do posto: CNPJ
    chave_posto = cnpj if cnpj else f"{razao}_{endereco}"
    
    # Inicializa estrutura
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
    
    # Adiciona o preço do produto
    resultado[estado][municipio][chave_posto]['precos'][produto] = valor

print(f"\n📊 Estatísticas:")
print(f"   Estados: {len(resultado)}")
total_municipios = sum(len(c) for c in resultado.values())
print(f"   Municípios: {total_municipios}")
total_postos = sum(
    sum(len(p) for p in c.values())
    for c in resultado.values()
)
print(f"   Postos: {total_postos}")

# Salva o JSON
with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"\n✅ precos.json gerado com sucesso!")
