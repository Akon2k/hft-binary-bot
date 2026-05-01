import asyncio
import json
import websockets
from logger import logger

class MarketConnector:
    """Gestiona la conexión WebSocket con Deriv/Binary.com"""
    def __init__(self, token, app_id=1089):
        self.token = token
        self.app_id = app_id
        self.uri = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        self.ws = None
        self.on_message_callbacks = []
        self.is_connected = False

    async def connect(self):
        """Mantiene la conexión activa con lógica de reconexión automática"""
        while True:
            try:
                logger.info(f"Conectando a {self.uri}...")
                self.ws = await websockets.connect(self.uri)
                self.is_connected = True
                logger.info("Conexión WebSocket establecida.")
                
                # Autenticación
                await self.send({"authorize": self.token})
                
                # Iniciar escucha de mensajes
                await self.listen()
            except Exception as e:
                self.is_connected = False
                logger.error(f"Error de conexión WebSocket: {e}. Reintentando en 5s...")
                await asyncio.sleep(5)

    async def send(self, data):
        """Envía datos al servidor"""
        if self.ws and self.is_connected:
            await self.ws.send(json.dumps(data))

    async def subscribe_ticks(self, symbols):
        """Se suscribe a los ticks de los símbolos especificados"""
        for symbol in symbols:
            await self.send({"ticks": symbol})
            logger.info(f"Suscrito a ticks para {symbol}")

    async def subscribe_candles(self, symbol, granularity):
        """Se suscribe a las velas (OHLC) con una granularidad específica"""
        # Granularidad en segundos: 60 (M1), 300 (M5), 900 (M15)
        await self.send({
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": 100,
            "end": "latest",
            "granularity": granularity,
            "style": "candles",
            "subscribe": 1
        })
        logger.info(f"Suscrito a velas de {granularity}s para {symbol}")

    async def listen(self):
        """Escucha y procesa los mensajes entrantes"""
        async for message in self.ws:
            data = json.loads(message)
            if "error" in data:
                logger.error(f"Error de API: {data['error']['message']}")
                continue
                
            for callback in self.on_message_callbacks:
                await callback(data)

    def add_callback(self, callback):
        """Añade una función de callback para procesar mensajes"""
        self.on_message_callbacks.append(callback)
