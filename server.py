import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta

app = FastAPI()

# Permite que o Tiiny Host converse com o Render sem bloqueios de segurança
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN = os.getenv("METAAPI_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "").strip()

ordem_em_andamento = False

async def executar_scalper_instantaneo(connection):
    global ordem_em_andamento
    if ordem_em_andamento:
        return
        
    try:
        ordem_em_andamento = True
        
        # Como você confirmou que na Exness aparece XAUUSD, usamos o ativo direto
        simbolo = "XAUUSD"
        
        # Puxa os dados das velas de 1 minuto para checar a tendência
        candles = await connection.get_candles(simbolo, "m1", datetime.now() - timedelta(minutes=5), 5)
        
        if not candles:
            print("Nao foi possivel ler o grafico do Ouro.")
            return

        candle_atual = candles[-1]
        posicoes = await connection.get_positions()
        
        # Se já houver ordem aberta, protege a conta e não abre outra
        if len(posicoes) > 0:
            print("Ja existe uma operacao rodando.")
            return

        # Estratégia de Força dos Candles
        tendencia_alta = candle_atual['close'] > candle_atual['open']
        lote = 0.07
        pips = 15
        
        if tendencia_alta:
            print(f"Executando COMPRA IMEDIATA no ativo {simbolo}...")
            try:
                await connection.create_market_buy_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                await connection.create_market_buy_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "IOC"})
        else:
            print(f"Executando VENDA IMEDIATA no ativo {simbolo}...")
            try:
                await connection.create_market_sell_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                await connection.create_market_sell_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "IOC"})
            
    except Exception as e:
        print(f"Erro ao processar ordem na corretora: {str(e)}")
    finally:
        ordem_em_andamento = False

@app.get("/")
async def get_status():
    if not API_TOKEN or not ACCOUNT_ID:
        return {"status": "ERRO: Faltam Variaveis no Render", "wins": 0}
    
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        if account.state != 'DEPLOYED':
            return {"status": "IA ACORDANDO CONTA...", "wins": 0}
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # Puxa o histórico para o placar do site
        desde_data = datetime.now() - timedelta(days=30)
        historico = await connection.get_history_orders_by_time_range(desde_data, datetime.now())
        wins = len([o for o in historico.get('historyOrders', []) if o.get('profit', 0) > 0])

        return {
            "status": "CONECTADO COM SUCESSO",
            "wins": wins
        }
    except Exception as e:
        return {"status": "CONEXAO AGUARDANDO MERCADO", "wins": 0}

@app.get("/ativar")
async def activar_ia():
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # DISPARA O SCALPER NA HORA QUE VOCÊ CLICA NO BOTÃO
        asyncio.create_task(executar_scalper_instantaneo(connection))
        return {"mensagem": "Inteligencia Artificial Ativada com sucesso! Analisando mercado..."}
    except Exception as e:
        return {"mensagem": f"Falha ao iniciar operacao: {str(e)}"}
