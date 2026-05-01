import pandas as pd
import pandas_ta as ta
from logger import logger
import asyncio

class BrainEngine:
    """Motor de análisis técnico y generación de señales"""
    def __init__(self, symbols, ema_period=200, rsi_period=14, bb_period=20, bb_std=2):
        self.symbols = symbols
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        
        # Almacenamiento de datos: {simbolo: {granularidad: DataFrame}}
        self.data = {symbol: {60: pd.DataFrame(), 300: pd.DataFrame(), 900: pd.DataFrame()} for symbol in symbols}
        self.on_signal_callbacks = []

    async def process_message(self, data):
        """Procesa mensajes de velas y actualiza los DataFrames"""
        if "ohlc" in data:
            symbol = data["ohlc"]["symbol"]
            granularity = data["ohlc"]["granularity"]
            candle = data["ohlc"]
            
            # Crear nueva fila
            new_row = {
                "timestamp": pd.to_datetime(candle["open_time"], unit="s"),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"])
            }
            
            df = self.data[symbol][granularity]
            if not df.empty and df.iloc[-1]["timestamp"] == new_row["timestamp"]:
                df.iloc[-1] = new_row
            else:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Mantener solo las últimas 300 velas para eficiencia
            self.data[symbol][granularity] = df.tail(300)
            
            # Verificar señales solo en la actualización de M1
            if granularity == 60:
                await self.check_strategy(symbol)

    async def check_strategy(self, symbol):
        """Implementa la estrategia de confluencia M15-M5-M1"""
        df1 = self.data[symbol][60]
        df5 = self.data[symbol][300]
        df15 = self.data[symbol][900]
        
        if len(df1) < 50 or len(df5) < 50 or len(df15) < 200:
            return # Faltan datos

        # Calcular Indicadores
        # M15: EMA 200 (Filtro Macro)
        df15["ema200"] = ta.ema(df15["close"], length=self.ema_period)
        
        # M5: RSI y Bandas de Bollinger (Filtro Medio - Pullback)
        df5["rsi"] = ta.rsi(df5["close"], length=self.rsi_period)
        bb = ta.bbands(df5["close"], length=self.bb_period, std=self.bb_std)
        df5 = pd.concat([df5, bb], axis=1)
        
        # M1: RSI (Disparador Micro)
        df1["rsi"] = ta.rsi(df1["close"], length=self.rsi_period)

        # Lógica de la Estrategia
        curr1 = df1.iloc[-1]
        curr5 = df5.iloc[-1]
        curr15 = df15.iloc[-1]
        
        # 1. Filtro Macro (M15)
        trend_up = curr15["close"] > curr15["ema200"]
        trend_down = curr15["close"] < curr15["ema200"]
        
        # 2. Filtro Medio (M5) - Identificación de Pullback
        pullback_buy = curr5["rsi"] < 50 or curr5["close"] <= df5.iloc[-1][f"BBL_{self.bb_period}_{float(self.bb_std)}"]
        pullback_sell = curr5["rsi"] > 50 or curr5["close"] >= df5.iloc[-1][f"BBU_{self.bb_period}_{float(self.bb_std)}"]
        
        # 3. Disparador Micro (M1)
        trigger_buy = curr1["rsi"] > 50 and df1.iloc[-2]["rsi"] <= 50
        trigger_sell = curr1["rsi"] < 50 and df1.iloc[-2]["rsi"] >= 50

        signal = None
        if trend_up and pullback_buy and trigger_buy:
            signal = "CALL"
        elif trend_down and pullback_sell and trigger_sell:
            signal = "PUT"
            
        if signal:
            strategy_details = {
                "m15_close": curr15["close"], "m15_ema200": curr15["ema200"],
                "m5_rsi": curr5["rsi"], "m1_rsi": curr1["rsi"]
            }
            for callback in self.on_signal_callbacks:
                await callback(symbol, signal, strategy_details)

    def add_signal_callback(self, callback):
        """Añade una función de callback para recibir señales"""
        self.on_signal_callbacks.append(callback)
