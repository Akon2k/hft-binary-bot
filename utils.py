import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def get_env_list(key, default=""):
    """Obtiene una lista de strings desde una variable de entorno separada por comas"""
    value = os.getenv(key, default)
    if not value:
        return []
    return [item.strip() for item in value.split(",")]

def get_env_float(key, default=0.0):
    """Obtiene un float desde una variable de entorno"""
    return float(os.getenv(key, default))

def get_env_int(key, default=0):
    """Obtiene un entero desde una variable de entorno"""
    return int(os.getenv(key, default))
