import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta

app = FastAPI()

# Libera a comunicação total entre o Tiiny Host e o Render
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

async def executar_scalper_multi_ativos(connection, ativo="XAUUSD"):
    global ordem_em_andamento
    if ordem_em_andamento:
        return
        
    try:
        ordem_em_andamento = True
        print(f"🤖 IA Analisando mercado para o ativo: {ativo}")
        
        # Coleta dados do gráfico de 1 minuto para a análise cirúrgica
        candles = await connection.get_candles(ativo, "m1", datetime.now() - timedelta(minutes=5), 5)
        
        if not candles:
            print(f"Não foi possível ler o gráfico de {ativo}.")
            return

        candle_atual = candles[-1]
        posicoes = await connection.get_positions()
        
        # Trava de segurança: Se já houver ordem aberta, protege a banca e não abre outra
        if len(posicoes) > 0:
            print("Robô aguardando finalização da ordem atual.")
            return

        # Estratégia de Alta Frequência (Tendência do Candle)
        tendencia_alta = candle_atual['close'] > candle_atual['open']
        lote = 0.07
        pips = 15
        
        if tendencia_alta:
            print(f"🔥 Força de COMPRA em {ativo}. Enviando ordem de {lote}...")
            try:
                await connection.create_market_buy_order(ativo, lote, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                await connection.create_market_buy_order(ativo, lote, {"takeProfit": pips, "fillingMode": "IOC"})
        else:
            print(f"🔥 Força de VENDA em {ativo}. Enviando ordem de {lote}...")
            try:
                await connection.create_market_sell_order(ativo, lote, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                await connection.create_market_sell_order(ativo, lote, {"takeProfit": pips, "fillingMode": "IOC"})
            
    except Exception as e:
        print(f"Erro ao disparar ordem na Exness: {str(e)}")
    finally:
        ordem_em_andamento = False

@app.get("/")
async def get_status():
    if not API_TOKEN or not ACCOUNT_ID:
        return {"status": "CONFIGURAR VARIÁVEIS", "wins": 0}
    
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        if account.state != 'DEPLOYED':
            return {"status": "IA ACORDANDO CONTA", "wins": 0}
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # Histórico de vitórias dos últimos 30 dias para o placar
        desde_data = datetime.now() - timedelta(days=30)
        historico = await connection.get_history_orders_by_time_range(desde_data, datetime.now())
        wins = len([o for o in historico.get('historyOrders', []) if o.get('profit', 0) > 0])

        return {
            "status": "CONECTADO COM SUCESSO",
            "wins": wins
        }
    except Exception as e:
        return {"status": "AGUARDANDO MERCADO", "wins": 0}

@app.get("/ativar")
async def ativar_ia(ativo: str = "XAUUSD"):
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # Dispara instantaneamente a análise e execução scalper
        asyncio.create_task(executar_scalper_multi_ativos(connection, ativo))
        return {"mensagem": f"Inteligência Artificial Iniciada para {ativo}! Monitorando velas..."}
    except Exception as e:
        return {"mensagem": f"Erro ao iniciar operação: {str(e)}"}
