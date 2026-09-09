import pandas as pd
import json
import requests
from io import BytesIO
import os

# URL do CSV da ANP - Série Histórica de Preços
# ATENÇÃO: Ajuste para a semana mais recente disponível
# Site oficial: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca
url_anp = 'https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/ca-2026-08.csv'

print("📥 Baixando dados da ANP...")

try:
    # Baixa o CSV
    response = requests.get(url_anp, timeout=60)
    response.raise_for_status()
    csv_data = BytesIO(response.content)
    
    # Lê o CSV com as configurações corretas
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
    
    print(f"📊 Registros de combustível: {len(df_filtrado)}")
    
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
        elif 'ETANOL' in produto:
            resultado[estado][municipio]['etanol'] = valor
    
    # Salva como JSON
    with open('precos.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Arquivo precos.json gerado com sucesso!")
    print(f"📊 {len(resultado)} estados")
    print(f"🏙️ {sum(len(c) for c in resultado.values())} cidades")
    
    # Mostra alguns exemplos
    print("\n📋 Exemplos de preços:")
    for estado in list(resultado.keys())[:3]:
        cidades = list(resultado[estado].keys())[:2]
        for cidade in cidades:
            precos = resultado[estado][cidade]
            print(f"  {estado} - {cidade}: Gasolina R$ {precos.get('gasolina', 'N/A')} | Etanol R$ {precos.get('etanol', 'N/A')}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)
