import asyncpg
import asyncio
from logger import logger
import os

class DatabaseManager:
    """Gestiona la persistencia de datos en PostgreSQL"""
    def __init__(self, user, password, database, host='localhost', port=5432):
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.pool = None

    async def connect(self):
        """Establece el pool de conexiones y crea las tablas si no existen"""
        try:
            self.pool = await asyncpg.create_pool(
                user=self.user,
                password=self.password,
                database=self.database,
                host=self.host,
                port=self.port
            )
            async with self.pool.acquire() as conn:
                # Crear tabla de operaciones
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        symbol TEXT,
                        side TEXT,
                        amount NUMERIC,
                        result TEXT,
                        strategy_details JSONB,
                        signature TEXT
                    )
                ''')
            logger.info("Conexión con PostgreSQL establecida y tablas verificadas.")
            return True
        except Exception as e:
            logger.error(f"Error al conectar con PostgreSQL: {e}")
            return False

    async def save_trade(self, symbol, side, amount, result, strategy_details, signature="icarmona"):
        """Guarda una operación en la base de datos"""
        if not self.pool:
            return
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO trades (symbol, side, amount, result, strategy_details, signature)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''', symbol, side, amount, result, json.dumps(strategy_details), signature)
        except Exception as e:
            logger.error(f"Error al guardar operación en DB: {e}")

    async def close(self):
        """Cierra el pool de conexiones"""
        if self.pool:
            await self.pool.close()
