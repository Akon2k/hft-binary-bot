import logging
import json
import os
from datetime import datetime

class TradingLogger:
    def __init__(self, log_file="trading_audit.json"):
        self.log_file = log_file
        self.logger = logging.getLogger("BotHFT")
        self.logger.setLevel(logging.INFO)
        
        # Manejador de Consola
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(ch)

    def log_trade(self, symbol, side, amount, result, strategy_details):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "simbolo": symbol,
            "lado": side,
            "monto": amount,
            "resultado": result,
            "estrategia": strategy_details,
            "firma": "icarmona 30-04-2026"
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        self.logger.info(f"Operación Registrada: {symbol} | {side} | {result}")

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

logger = TradingLogger()
