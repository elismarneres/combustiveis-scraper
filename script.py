import json
import datetime

# Dados de exemplo
dados = {
    "SP": {
        "SAO PAULO": {
            "gasolina": 6.42,
            "etanol": 4.58
        },
        "CAMPINAS": {
            "gasolina": 6.35,
            "etanol": 4.45
        }
    },
    "RJ": {
        "RIO DE JANEIRO": {
            "gasolina": 6.38,
            "etanol": 4.62
        }
    }
}

with open('precos.json', 'w', encoding='utf-8') as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

print("✅ precos.json gerado com sucesso!")
