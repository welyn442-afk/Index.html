from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from metaapi_cloud_sdk import MetaApi
from datetime import datetime, timedelta

app = FastAPI()

# Permissão de segurança para o Tiiny.host acessar o Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SUAS CHAVES REAIS TRAVADAS DIRETAMENTE NO MOTOR DO SISTEMA
API_TOKEN = "80fa4a51-740e-4aab-ade6-18bdcf2787fe"
ACCOUNT_ID = "196642206"

@app.get("/")
async def get_status():
    try:
        api = MetaApi(API_TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        # Força a reconexão automática caso o servidor mude de estado
        if account.connection_status != 'CONNECTED':
            await account.connect()
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # Puxa o histórico real de ordens fechadas na Exness (últimos 30 dias)
        desde_data = datetime.now() - timedelta(days=30)
        historico = await connection.get_history_orders_by_time_range(desde_data, datetime.now())
        
        wins = 0
        losses = 0
        valores_grafico = [0]
        saldo_acumulado = 0
        
        # Varre o histórico do MT5 calculando Vitórias e Derrotas Reais
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

        # Ajusta o gráfico para ter sempre 7 pontos visíveis na tela
        if len(valores_grafico) < 7:
            valores_grafico = (valores_grafico + [valores_grafico[-1]] * (7 - len(valores_grafico)))

        return {
            "status": "CONECTADO COM SUCESSO",
            "conta": ACCOUNT_ID,
            "wins": wins,
            "losses": losses,
            "grafico": valores_grafico[-7:]
        }
    except Exception as e:
        return {
            "status": "ERRO DE CONEXÃO EXNESS",
            "conta": ACCOUNT_ID,
            "wins": 0,
            "losses": 0,
            "grafico": [0, 0, 0, 0, 0, 0, 0]
        }


