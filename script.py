# ============================================================
# 5) PROCESSA POSTOS (ETANOL E GASOLINA)
# ============================================================
print("📊 Processando postos...")

# Converte preço
df[col_valor] = (
    df[col_valor]
    .astype(str)
    .str.replace('.', '', regex=False)
    .str.replace(',', '.', regex=False)
)
df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce')
df = df.dropna(subset=[col_valor])

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
# 5.1) MÉDIAS POR MUNICÍPIO (formato antigo, compatível)
# ============================================================
print("📊 Calculando médias...")

# Agrupa por UF + Município + Produto e faz a média
medias_df = df.groupby([col_estado, col_municipio, col_produto])[col_valor].mean().reset_index()

medias_dict = {}  # {uf: {municipio: {produto_normalizado: media}}}
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
# 5.3) MONTA ESTRUTURA FINAL {UF: {MUNICIPIO: {medias, postos}}}
# ============================================================
resultado = {}

# Junta as médias
for uf, municipios in medias_dict.items():
    for municipio, medias in municipios.items():
        resultado.setdefault(uf, {}).setdefault(municipio, {
            'medias': {},
            'postos': [],
        })
        resultado[uf][municipio]['medias'] = medias

# Junta os postos
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
