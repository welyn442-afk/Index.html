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

# Trava de segurança para evitar ordens duplicadas no mesmo segundo
ordem_em_andamento = False

async def executar_scalper_instantaneo(connection):
    global ordem_em_andamento
    if ordem_em_andamento:
        return
        
    try:
        ordem_em_andamento = True
        
        # 1. VALIDAÇÃO DO ATIVO DA CONTA STANDARD (XAUUSDm)
        simbolo = "XAUUSDm"
        try:
            # Testa se a conta responde ao símbolo com 'm'
            candles = await connection.get_candles(simbolo, "m1", datetime.now() - timedelta(minutes=5), 5)
        except:
            # Caso contrário, usa o símbolo padrão
            simbolo = "XAUUSD"
            candles = await connection.get_candles(simbolo, "m1", datetime.now() - timedelta(minutes=5), 5)
        
        if not candles:
            print("Não foi possível coletar os dados do gráfico.")
            return

        candle_atual = candles[-1]
        posicoes = await connection.get_positions()
        
        # Se já houver uma operação aberta, aguarda ela bater no Take Profit para proteger a banca
        if len(posicoes) > 0:
            print("Robô aguardando a operação atual ser finalizada.")
            return

        # 2. ESTRATÉGIA SCALPER DE ALTA FREQUÊNCIA
        # Analisa o fechamento imediato da vela (Open/Close) para medir a força e direção
        tendencia_alta = candle_atual['close'] > candle_atual['open']
        lote = 0.07
        pips = 15
        
        # 3. ENVIO FORÇADO A MERCADO COM PROTOCOLO DE AUTO-CORREÇÃO (FOK / IOC)
        if tendencia_alta:
            print(f"🔥 Força de COMPRA detectada em {simbolo}. Enviando ordem de {lote} lote...")
            try:
                # Tenta execução imediata Fill-or-Kill
                await connection.create_market_buy_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                try:
                    # Alternativa imediata caso a corretora recuse o FOK
                    await connection.create_market_buy_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "IOC"})
                except Exception as e:
                    print(f"Erro ao executar Compra na Exness: {str(e)}")
        else:
            print(f"🔥 Força de VENDA detectada em {simbolo}. Enviando ordem de {lote} lote...")
            try:
                await connection.create_market_sell_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "FOK"})
            except:
                try:
                    await connection.create_market_sell_order(simbolo, lote, {"takeProfit": pips, "fillingMode": "IOC"})
                except Exception as e:
                    print(f"Erro ao executar Venda na Exness: {str(e)}")
            
    except Exception as e:
        print(f"Erro geral na verificação de ordens: {str(e)}")
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
        
        # DISPARO IMEDIATO NO EXATO SEGUNDO EM QUE VOCÊ ATIVA O ROBÔ
        asyncio.create_task(executar_scalper_instantaneo(connection))

        # Puxa o histórico dos últimos 30 dias para atualizar os blocos de placar do app
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

        
        
