import pandas as pd
import json
import requests
from io import BytesIO

# URL do CSV da ANP - Semana 08/2026
url_anp = 'https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/ca-2026-08.csv'

print("📥 Baixando dados da ANP...")

try:
    # Baixa o CSV
    response = requests.get(url_anp, timeout=60)
    csv_data = BytesIO(response.content)
    
    # Lê o CSV
    df = pd.read_csv(
        csv_data, 
        encoding='latin-1', 
        sep=';', 
        decimal=',',
        parse_dates=['DATA DA COLETA']
    )
    
    print(f"✅ Baixado! {len(df)} registros encontrados")
    
    # Filtra apenas Gasolina e Etanol
    combustiveis = ['GASOLINA C COMUM', 'ETANOL HIDRATADO']
    df_filtrado = df[df['PRODUTO'].isin(combustiveis)]
    
    # Calcula a média por cidade
    precos_media = df_filtrado.groupby(
        ['ESTADO - SIGLA', 'MUNICIPIO', 'PRODUTO']
    )['VALOR DE VENDA'].mean().reset_index()
    
    # Estrutura: { "UF": { "CIDADE": { "gasolina": X, "etanol": Y } } }
    resultado = {}
    
    for _, row in precos_media.iterrows():
        estado = row['ESTADO - SIGLA']
        municipio = row['MUNICIPIO'].strip().upper()
        produto = row['PRODUTO']
        valor = round(row['VALOR DE VENDA'], 2)
        
        if estado not in resultado:
            resultado[estado] = {}
        if municipio not in resultado[estado]:
            resultado[estado][municipio] = {}
        
        if 'GASOLINA' in produto:
            resultado[estado][municipio]['gasolina'] = valor
        else:
            resultado[estado][municipio]['etanol'] = valor
    
    # Salva como JSON
    with open('precos.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Arquivo precos.json gerado!")
    print(f"📊 {len(resultado)} estados, {sum(len(c) for c in resultado.values())} cidades")
    
except Exception as e:
    print(f"❌ Erro: {e}")
