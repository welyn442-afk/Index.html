import os
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

API_TOKEN = os.getenv("METAAPI_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "").strip()

# Variável de controle global
operando = False

@app.get("/status")
async def get_status():
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # Pega saldo e histórico
        account_info = await connection.get_account_information()
        balance = account_info.get('balance', 0)
        return {"status": "CONECTADO", "balance": balance, "operando": operando}
    except:
        return {"status": "ERRO DE CONEXÃO", "balance": 0, "operando": False}

@app.get("/ativar")
async def ativar(ativo: str, lotes: float, pips: int):
    global operando
    operando = True
    asyncio.create_task(loop_scalper(ativo, lotes, pips))
    return {"mensagem": "IA Iniciada. Monitorando velas M1..."}

@app.get("/parar")
async def parar():
    global operando
    operando = False
    return {"mensagem": "IA Parada."}

async def loop_scalper(ativo, lotes, pips):
    global operando
    api = MetaApi(API_TOKEN)
    account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
    connection = account.get_rpc_connection()
    await connection.connect()
    
    while operando:
        candles = await connection.get_candles(ativo, "m1", datetime.now() - timedelta(minutes=5), 2)
        if len(candles) >= 2:
            # Lógica: Se vela atual > anterior, compra
            if candles[-1]['close'] > candles[-1]['open']:
                await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips})
            elif candles[-1]['close'] < candles[-1]['open']:
                await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips})
        await asyncio.sleep(60) # Espera 1 min para próxima análise
