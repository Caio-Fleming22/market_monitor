# Importar Bibliotecas Python
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

def getUsualMarkets():
    try:
        # URL da API
        url = "https://api.backpack.exchange/api/v1/tickers"

        # Requisição GET
        response = requests.get(url)
        if response.status_code != 200:
            print(f"[AVISO] Erro na requisição: {response.status_code}")
            return []  # Retorna lista vazia se falhar

        tickers = response.json()
        # Extrai e ordena os symbols
        tickers_symbols = sorted([ticker["symbol"] for ticker in tickers])
        return tickers_symbols

    except Exception as e:
        print(f"[EXCEÇÃO] Falha ao obter mercados: {e}")
        return []  # Retorna lista vazia em qualquer exceção