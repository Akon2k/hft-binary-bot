import asyncio
import os
import json
from aiohttp import web
from connector import MarketConnector
from engine import BrainEngine
from executor import ExecutionManager
from database import DatabaseManager
from utils import get_env_list, get_env_float, get_env_int
from logger import logger

class DashboardServer:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.websockets = []
        
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/style.css', self.handle_css)
        self.app.router.add_get('/app.js', self.handle_js)
        self.app.router.add_get('/ws', self.handle_ws)

    async def handle_index(self, request):
        return web.FileResponse('index.html')

    async def handle_css(self, request):
        return web.FileResponse('style.css')

    async def handle_js(self, request):
        return web.FileResponse('app.js')

    async def handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.append(ws)
        try:
            async for msg in ws:
                pass
        finally:
            self.websockets.remove(ws)
        return ws

    async def broadcast(self, data_type, payload):
        message = json.dumps({"type": data_type, "payload": payload})
        for ws in self.websockets:
            await ws.send_str(message)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"Dashboard disponible en http://localhost:{self.port}")

async def main():
    """Orquesta el inicio de todos los componentes del bot"""
    logger.info("Inicializando Sistema de Opciones Binarias HFT...")
    
    # Cargar Configuración
    token = os.getenv("DERIV_TOKEN")
    app_id = get_env_int("APP_ID", 1089)
    symbols = get_env_list("TRADING_SYMBOLS", "R_100")
    
    # Configuración DB
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME", "hft_trading")
    
    if not token or token == "tu_token_aqui":
        logger.error("DERIV_TOKEN no configurado en el archivo .env.")
        return

    # Iniciar DB si hay credenciales
    db = None
    if db_user and db_pass and db_user != "tu_usuario_db":
        db = DatabaseManager(db_user, db_pass, db_name)
        if await db.connect():
            logger.info("Base de datos PostgreSQL lista.")
        else:
            db = None

    # Iniciar Servidor Dashboard
    dashboard = DashboardServer()
    await dashboard.start()

    # Inicializar Componentes
    connector = MarketConnector(token, app_id)
    engine = BrainEngine(
        symbols, 
        ema_period=get_env_int("EMA_PERIOD", 200),
        rsi_period=get_env_int("RSI_PERIOD", 14)
    )
    executor = ExecutionManager(
        connector, 
        stake=get_env_float("FIXED_STAKE", 1.0),
        daily_stop_loss=get_env_float("STOP_LOSS_DAILY", 10.0),
        max_martingale=get_env_int("MAX_MARTINGALE_STEPS", 3)
    )

    # Callbacks para el Dashboard y DB
    async def on_candle_update(data):
        if "ohlc" in data:
            candle = data["ohlc"]
            await dashboard.broadcast('candle', {
                'time': candle['open_time'],
                'open': float(candle['open']),
                'high': float(candle['high']),
                'low': float(candle['low']),
                'close': float(candle['close'])
            })

    async def on_contract_update(data):
        if "proposal_open_contract" in data:
            contract = data["proposal_open_contract"]
            if contract["is_sold"]:
                symbol = contract['display_name']
                side = 'CALL' if contract['contract_type'] == 'CALL' else 'PUT'
                amount = float(contract['buy_price'])
                result = 'GANADA' if float(contract['profit']) > 0 else 'PERDIDA'
                
                # Broadast a dashboard
                await dashboard.broadcast('trade', {
                    'symbol': symbol, 'side': side, 'amount': amount, 'result': result
                })
                await dashboard.broadcast('stats', {
                    'balance': float(contract['balance_after']),
                    'profit': executor.current_loss * -1
                })
                
                # Guardar en DB
                if db:
                    await db.save_trade(symbol, side, amount, result, {}, "icarmona")

    # Configurar Callbacks
    connector.add_callback(engine.process_message)
    connector.add_callback(on_candle_update)
    connector.add_callback(executor.handle_contract_update)
    connector.add_callback(on_contract_update)
    engine.add_signal_callback(executor.execute_signal)

    # Iniciar el Sistema
    task_conexion = asyncio.create_task(connector.connect())
    
    while not connector.is_connected:
        await asyncio.sleep(1)
    
    for symbol in symbols:
        await connector.subscribe_candles(symbol, 60)
        await connector.subscribe_candles(symbol, 300)
        await connector.subscribe_candles(symbol, 900)
        await connector.send({"proposal_open_contract": 1, "subscribe": 1})

    logger.info("Sistema operativo con Dashboard y PostgreSQL.")
    
    try:
        await task_conexion
    except asyncio.CancelledError:
        logger.info("Apagando sistema...")
    finally:
        if db:
            await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
