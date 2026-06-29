import os
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta, timezone

app = FastAPI()

# Liberação total de segurança para o Tiiny Host conversar com o Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN = os.getenv("METAAPI_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "").strip()

# Variáveis de controle do robô
operando = False
bloqueio_analise = False

async def executar_scalper_automatico(ativo, lotes, pips):
    global operando, bloqueio_analise
    
    print(f"🚀 Loop do Scalper Ativado para {ativo}. Lotes: {lotes} | Alvo: {pips} Pips")
    
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        while operando:
            if bloqueio_analise:
                await asyncio.sleep(1)
                continue
                
            try:
                bloqueio_analise = True
                
                # CORREÇÃO: Puxa o horário correto em UTC para alinhar com os servidores da MetaAPI
                agora = datetime.now(timezone.utc)
                velas = await connection.get_candles(ativo, "m1", agora - timedelta(minutes=10), 2)
                
                if not velas or len(velas) < 2:
                    print("⏳ Aguardando dados de velas válidos da Exness...")
                    bloqueio_analise = False
                    await asyncio.sleep(2)
                    continue
                
                vela_atual = velas[-1]
                posicoes = await connection.get_positions()
                
                # Se já tiver ordem aberta, não abre outra para proteger a banca
                if len(posicoes) > 0:
                    print("🛑 Já existe uma ordem rodando no mercado. Aguardando...")
                    bloqueio_analise = False
                    await asyncio.sleep(5)
                    continue
                
                # Lógica Scalper Vela por Vela (M1)
                tendencia_alta = vela_atual['close'] > vela_atual['open']
                
                if tendencia_alta:
                    print(f"🔥 Tendência de ALTA em {ativo}. Comprando {lotes} lotes...")
                    try:
                        await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "FOK"})
                    except:
                        try:
                            await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "IOC"})
                        except Exception as e_direct:
                            # Execução direta caso a corretora rejeite os modos de preenchimento anteriores
                            await connection.create_market_buy_order(ativo, lotes, {"takeProfit": pips})
                else:
                    print(f"🔥 Tendência de BAIXA em {ativo}. Vendendo {lotes} lotes...")
                    try:
                        await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "FOK"})
                    except:
                        try:
                            await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips, "fillingMode": "IOC"})
                        except Exception as e_direct:
                            await connection.create_market_sell_order(ativo, lotes, {"takeProfit": pips})
                        
            except Exception as erro_loop:
                print(f"Erro na execução do scalper: {str(erro_loop)}")
            finally:
                bloqueio_analise = False
                
            # Espera 5 segundos para reavaliar a vela atual rapidamente após o clique
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"Erro crítico na conexão Meta API: {str(e)}")
        operando = False

@app.get("/status")
async def get_status():
    if not API_TOKEN or not ACCOUNT_ID:
        return {"status": "VARIÁVEIS INCOMPLETAS", "balance": 0, "wins": 0, "operando": False}
    
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        info_conta = await connection.get_account_information()
        saldo = info_conta.get('balance', 0)
        
        desde = datetime.now(timezone.utc) - timedelta(days=30)
        historico = await connection.get_history_orders_by_time_range(desde, datetime.now(timezone.utc))
        wins = len([o for o in historico.get('historyOrders', []) if o.get('profit', 0) > 0])
        
        return {
            "status": "CONECTADO",
            "balance": saldo,
            "wins": wins,
            "operando": operando
        }
    except Exception as e:
        return {"status": "AGUARDANDO CORRETORA", "balance": 0, "wins": 0, "operando": operando}

@app.get("/ativar")
async def activar_ia(ativo: str = "XAUUSD", lotes: float = 0.07, pips: int = 15):
    global operando
    if operando:
        return {"mensagem": "O robô scalper já está em execução automática!"}
        
    operando = True
    asyncio.create_task(executar_scalper_automatico(ativo, lotes, pips))
    return {"mensagem": f"Inteligência Artificial iniciada para {ativo}! Executando ordens a mercado."}

@app.get("/parar")
async def parar_ia():
    global operando
    operando = False
    return {"mensagem": "Robô pausado com sucesso!"}
