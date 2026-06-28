import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta

app = FastAPI()

# Permissão de segurança para o seu Tiiny.host aceder ao Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Puxa as variáveis de ambiente configuradas no painel do Render
API_TOKEN = os.getenv("METAAPI_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("META_ACCOUNT_ID", "").strip()

@app.get("/")
async def get_status():
    # Validação inicial para o log do Render
    if not API_TOKEN or not ACCOUNT_ID:
        return {
            "status": "ERRO: Chaves nao encontradas no Render",
            "wins": 0, "losses": 0, "grafico": [0]*7
        }
    
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        # Se a conta estiver offline ou undeployed, força o deploy automático
        if account.state != 'DEPLOYED':
            await account.deploy()
            return {
                "status": "IA ACORDANDO CONTA... AGUARDE 60 SEGUNDOS",
                "wins": 0, "losses": 0, "grafico": [0]*7
            }
        
        # Conexão direta via RPC (Sincronizada)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # Puxa o histórico operacional dos últimos 30 dias
        desde_data = datetime.now() - timedelta(days=30)
        historico = await connection.get_history_orders_by_time_range(desde_data, datetime.now())
        
        wins = 0
        losses = 0
        valores_grafico = [0]
        saldo_acumulado = 0
        
        # Separação minuciosa de ordens de Gain e Loss
        for ordem in historico.get('historyOrders', []):
            profit = ordem.get('profit', 0)
            if profit > 0:
                wins += 1
                saldo_acumulado += profit
                valores_grafico.append(round(saldo_acumulado, 2))
            elif profit < 0:
                losses += 1
                saldo_acumulado += profit
                valores_grafico.append(round(saldo_acumulado, 2))

        # Alinha o gráfico para nunca quebrar o layout do Tiiny.host
        if len(valores_grafico) < 7:
            valores_grafico = (valores_grafico + [valores_grafico[-1]] * (7 - len(valores_grafico)))

        return {
            "status": "CONECTADO COM SUCESSO",
            "wins": wins,
            "losses": losses,
            "grafico": valores_grafico[-7:]
        }
    except Exception as e:
        # Retorna o erro real resumido para você ver direto na tela do celular
        erro_msg = str(e)[:30].upper()
        return {
            "status": f"ERRO DE CONEXÃO: {erro_msg}",
            "wins": 0, "losses": 0, "grafico": [0]*7
        }
