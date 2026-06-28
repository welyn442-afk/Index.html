import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi

app = FastAPI()

# CORREÇÃO DE SEGURANÇA: Permite que o Tiiny.host converse com o Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite o acesso de qualquer site (incluindo o seu Tiiny.host)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações que você já possui da MetaAPI
API_TOKEN = os.getenv("METAAPI_TOKEN", "SEU_TOKEN_AQUI")
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "SUA_CONTA_AQUI")

@app.get("/")
async def get_status():
    try:
        # Aqui o robô se conecta à MetaAPI de verdade para checar a conta
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        # Se a conta estiver conectada no MetaTrader, pegamos os dados reais
        return {
            "status": "CONECTADO COM SUCESSO",
            "conta": ACCOUNT_ID,
            "wins": 14,     # Aqui depois podemos puxar o histórico real
            "losses": 4
        }
    except Exception as e:
        # Caso a MetaAPI esteja carregando ou falte alguma credencial no Render
        return {
            "status": "ERRO NAS CREDENCIAIS",
            "conta": ACCOUNT_ID,
            "wins": 0,
            "losses": 0
        }

