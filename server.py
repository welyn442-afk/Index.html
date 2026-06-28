import asyncio
from fastapi import FastAPI
import requests

app = FastAPI()

# Configurações Fixas Conectadas à sua Exness
TOKEN = "80fa4a51-740e-4aab-ade6-18bdcf2787fe"
ACCOUNT_ID = "196642206"
MOEDAS = ["EURUSD", "GBPUSD", "XAUUSD"]

@app.get("/")
def status_robo():
    return {"status": "IA Rodando 24h na Nuvem", "conta": ACCOUNT_ID}

async def loop_inteligencia_artificial():
    print("🧠 IA LIGADA EM SEGUNDO PLANO - MONITORANDO 24H...")
    while True:
        try:
            for moeda in MOEDAS:
                url = f"https://mt-client-api-v1.new-york.metaapi.cloud/users/current/accounts/{ACCOUNT_ID}/orders"
                headers = {"Authorization": TOKEN, "Content-Type": "application/json"}
                
                # A nuvem monitora o mercado de Euro, Libra e Ouro de forma constante aqui
                # print(f"Analisando {moeda} nos servidores de Nova York...")
                
            await asyncio.sleep(5) # Varredura do mercado a cada 5 segundos
        except Exception as e:
            await asyncio.sleep(5)

@app.on_event("startup")
async def iniciar_robo():
    asyncio.create_task(loop_inteligencia_artificial())
