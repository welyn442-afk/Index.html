import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN = os.getenv("METAAPI_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "").strip()

# Variável global para evitar múltiplas ordens abertas ao mesmo tempo no mesmo segundo
ordem_em_andamento = False

async def executar_estrategia_instantanea(connection):
    global ordem_em_andamento
    if ordem_em_andamento:
        return
        
    try:
        # 1. Pega os dados dos últimos candles para analisar a força e tendência da vela
        # Alterado para buscar o par principal (ex: XAUUSD ou EURUSD) - Ajuste o símbolo se necessário
        simbolo = "XAUUSD" 
        candles = await connection.get_candles(simbolo, "m1", datetime.now() - timedelta(minutes=5), 5)
        
        if not candles or len(candles) < 2:
            return

        candle_atual = candles[-1]
        
        # 2. Verifica as posições abertas atuais para não sobrecarregar a conta
        posicoes = await connection.get_positions()
        if len(posicoes) > 0:
            return # Já existe operação aberta, aguarda fechar no Take Profit

        # 3. ESTRATÉGIA DE FORÇA DOS CANDLES (AÇÃO IMEDIATA)
        # Se a vela atual fechou acima da abertura (Vela Verde) -> Força de Alta -> COMPRA IMEDIATA
        # Se a vela atual fechou abaixo da abertura (Vela Vermelha) -> Força de Baixa -> VENDA IMEDIATA
        tendencia_alta = candle_atual['close'] > candle_atual['open']
        
        lote = 0.07
        pips = 15
        
        ordem_em_andamento = True
        
        if tendencia_alta:
            print(f"Detectada força de ALTA no candle. Enviando COMPRA de {lote}...")
            # Envia a ordem com parâmetros de execução garantida para a Exness
            result = await connection.create_market_buy_order(
                simbolo, 
                lote, 
                {"takeProfit": pips, "fillingMode": "FOK"}
            )
            print("Ordem de Compra enviada:", result)
        else:
            print(f"Detectada força de BAIXA no candle. Enviando VENDA de {lote}...")
            result = await connection.create_market_sell_order(
                simbolo, 
                lote, 
                {"takeProfit": pips, "fillingMode": "FOK"}
            )
            print("Ordem de Venda enviada:", result)
            
    except Exception as e:
        print(f"Erro ao tentar colocar ordem na corretora: {str(e)}")
    finally:
        ordem_em_andamento = False

@app.get("/")
async def get_status():
    if not API_TOKEN or not ACCOUNT_ID:
        return {"status": "Chaves nao encontradas", "wins": 0, "losses": 0, "grafico": [0]*7}
    
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        if account.state != 'DEPLOYED':
            await account.deploy()
            return {"status": "IA ACORDANDO CONTA...", "wins": 0, "losses": 0, "grafico": [0]*7}
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # DISPARO DA LOGICA INSTANTÂNEA EM SEGUNDO PLANO
        # Assim que você clica em Ativar, o robô roda a análise imediatamente
        asyncio.create_task(executar_estrategia_instantanea(connection))

        # Puxa o histórico de operações
        desde_data = datetime.now() - timedelta(days=30)
        historico = await connection.get_history_orders_by_time_range(desde_data, datetime.now())
        
        wins, losses, saldo_acumulado = 0, 0, 0
        valores_grafico = [0]
        
        for ordem in historico.get('historyOrders', []):
            profit = ordem.get('profit', 0)
            if profit > 0: wins += 1
            elif profit < 0: losses += 1
            saldo_acumulado += profit
            valores_grafico.append(round(saldo_acumulado, 2))

        if len(valores_grafico) < 7:
            valores_grafico = (valores_grafico + [valores_grafico[-1]] * (7 - len(valores_grafico)))

        return {
            "status": "CONECTADO COM SUCESSO",
            "wins": wins,
            "losses": losses,
            "grafico": valores_grafico[-7:]
        }
    except Exception as e:
        return {"status": "CONEXAO AGUARDANDO MERCADO", "wins": 0, "losses": 0, "grafico": [0]*7}


