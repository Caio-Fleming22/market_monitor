# Importar Bibliotecas Python
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

def getUsualMarkets():

    # URL da API
    url = "https://api.backpack.exchange/api/v1/tickers"

    # Requisição GET
    response = requests.get(url)
    if response.status_code != 200:
        tickers_symbols = []
        raise Exception(f"Erro na requisição: {response.status_code}")
    else:
        tickers = response.json()
        # Extrai a lista de symbols
        tickers_symbols = sorted([ticker["symbol"] for ticker in tickers])

    return tickers_symbols