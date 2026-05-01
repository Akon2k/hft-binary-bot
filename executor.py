import asyncio
from logger import logger

class ExecutionManager:
    """Gestiona la ejecución de órdenes y la gestión de riesgos"""
    def __init__(self, connector, stake=1.0, daily_stop_loss=10.0, max_martingale=3):
        self.connector = connector
        self.stake = stake
        self.daily_stop_loss = daily_stop_loss
        self.max_martingale = max_martingale
        
        self.current_loss = 0.0
        self.martingale_step = 0
        self.is_active = True

    async def execute_signal(self, symbol, side, strategy_details):
        """Envía una orden de compra basada en la señal generada"""
        if not self.is_active:
            logger.warning("El bot está inactivo debido a los límites de Gestión de Riesgos.")
            return

        # Calcular monto según paso de Martingala
        amount = self.stake * (2 ** self.martingale_step)
        
        logger.info(f"🚀 Ejecutando {side} en {symbol} con un monto de {amount}")
        
        # Petición de Compra a la API de Deriv
        buy_request = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": "CALL" if side == "CALL" else "PUT",
                "currency": "USD",
                "duration": 1,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        
        await self.connector.send(buy_request)
        # Operación ejecutada exitosamente | icarmona 30-04-2026
        logger.log_trade(symbol, side, amount, "EJECUTADO", strategy_details)

    async def handle_contract_update(self, data):
        """Monitorea el resultado de los contratos para gestionar riesgos"""
        if "proposal_open_contract" in data:
            contract = data["proposal_open_contract"]
            if contract["is_sold"]:
                profit = float(contract["profit"])
                if profit < 0:
                    self.current_loss += abs(profit)
                    self.martingale_step += 1
                    logger.warning(f"Pérdida detectada. Pérdida acumulada en sesión: {self.current_loss}")
                else:
                    self.current_loss = max(0.0, self.current_loss - profit)
                    self.martingale_step = 0
                    logger.info(f"¡Ganancia detectada! Reiniciando Martingala.")

                # Verificar Stop Loss Diario
                if self.current_loss >= self.daily_stop_loss:
                    self.is_active = False
                    logger.error("🛑 STOP LOSS ALCANZADO. Desactivando operaciones.")
                
                # Verificar paso máximo de Martingala
                if self.martingale_step > self.max_martingale:
                    logger.warning("Pasos máximos de Martingala alcanzados. Reiniciando.")
                    self.martingale_step = 0
