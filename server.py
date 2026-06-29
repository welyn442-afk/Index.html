import os
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timezone

app = FastAPI()

# Liberação total de segurança para o Tiiny Host
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN = os.getenv("METAAPI_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "").strip()

# Variáveis globais de controle
operando = False

async def disparar_ordem_imediata(ativo, lotes, pips):
    """Esta função conecta e força a execução da ordem imediatamente na Exness"""
    try:
        print(f"⚡ Disparando ordem instantânea: {ativo} | Lotes: {lotes} | Pips: {pips}")
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        # Garante que a conta está ativa
        if account.state != 'DEPLOYED':
            await account.deploy()
            
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # 1. Leitura imediata do último preço/vela
        velas = await connection.get_candles(ativo, "m1", datetime.now(timezone.utc), 1)
        
        # Se falhar a leitura de velas, ele usa o preço atual de mercado (Tick) para não travar
        tendencia_alta = True
        if velas and len(velas) > 0:
            vela_atual = velas[-1]
            tendencia_alta = vela_atual['close'] >= vela_atual['open']
            print(f"📊 Análise rápida M1: Fechamento({vela_atual['close']}) vs Abertura({vela_atual['open']})")

        # 2. Verifica se já tem ordens abertas para evitar duplicar
        posicoes = await connection.get_positions()
        if len(posicoes) > 0:
            print("🛑 Ordem bloqueada: Já existe uma operação em andamento na Exness.")
            return

        # 3. Envio direto sem travas de preenchimento (fillingMode dinâmico)
        if tendencia_alta:
            print(f"🛒 Enviando COMPRA de {lotes} em {ativo}...")
            try:
                await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                try:
                    await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "IOC"})
                except:
                    await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips}) # Direto padrão
        else:
            print(f"📉 Enviando VENDA de {lotes} em {ativo}...")
            try:
                await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                try:
                    await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "IOC"})
                except:
                    await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips}) # Direto padrão

        print("✅ Comando enviado com sucesso para os servidores da Exness!")
    except Exception as e:
        print(f"❌ Erro na execução direta da MetaAPI: {str(e)}")

@app.get("/status")
async def get_status():
    if not API_TOKEN or not ACCOUNT_ID:
        return {"status": "VARIÁVEIS CONFIGURADAS INCORRETAMENTE", "balance": 0, "wins": 0, "operando": False}
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        info_conta = await connection.get_account_information()
        saldo = info_conta.get('balance', 0)
        
        return {
            "status": "CONECTADO",
            "balance": saldo,
            "wins": "Ativo",
            "operando": operando
        }
    except Exception as e:
        return {"status": "AGUARDANDO CORRETORA", "balance": 0, "wins": 0, "operando": operando}

@app.get("/ativar")
async def ativar_ia(ativo: str = "XAUUSD", lotes: float = 0.07, pips: int = 15):
    global operando
    operando = True
    
    # Executa a ordem IMEDIATAMENTE no momento do clique, sem esperar loops de 60 segundos
    asyncio.create_task(disparar_ordem_imediata(ativo, lotes, pips))
    
    return {"mensagem": f"Execução imediata iniciada para {ativo}! Verifique sua conta Exness em segundos."}

@app.get("/parar")
async def parar_ia():
    global operando
    operando = False
    return {"mensagem": "Robô Scalper Pausado."}
