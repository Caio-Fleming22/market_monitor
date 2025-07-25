# Importar Bibliotecas Python
import requests
import json
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

def extract_date_from_security(security_str):
    # Ex: "sUSD-2506" → dia 25, mês 06, ano atual
    try:
        suffix = security_str.split("-")[-1]
        if len(suffix) != 4:
            return None
        day = int(suffix[:2])
        month = int(suffix[2:])
        year = datetime.now().year
        return datetime(year, month, day).date()
    except Exception:
        return None
    
def days_until_security_date(security_str):
    try:
        suffix = security_str.split("-")[-1]
        if len(suffix) != 4:
            return None
        day = int(suffix[:2])
        month = int(suffix[2:])
        year = datetime.now().year
        target_date = datetime(year, month, day).date()
        today = datetime.now().date()

        delta = (target_date - today).days
        return delta
    except Exception as e:
        print("Erro:", e)
        return None

def getRatexMarkets():
    headers = {
        "path": "/",
        "Content-Type": "application/json",
        "Accept": "*/*"
    }
    url = f"https://api.rate-x.io/"
    payload = {"serverName":"MDSvr","method":"queryTrade","content":{"cid":"f2443b24-44dd-fded-6dba-7a6c567b4ff5"}}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Erro na requisição: {response.status_code}")
    data = response.json().get("data", {})
   
    security_ids = [item['SecurityID'] for item in data]
    # Converte para DataFrame
    df = pd.DataFrame(data)
    
    return security_ids

def getRatexHist(security_id,N,timescale):
    headers = {
        "path": "/",
        "Content-Type": "application/json",
        "Accept": "*/*"
    }
    url = f"https://api.rate-x.io/"
    payload = {
        "serverName": "MDSvr",
        "method": "query24KLine",
        "content": {
            "kline": [
                {
                    "securityID": f"{security_id}_yield",
                    "num": N,
                    "text": timescale
                }
            ]
        }
    }
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Erro na requisição: {response.status_code}")
    data_hist = response.json().get("data", {})
    # Novo dicionário para armazenar os pares timestamp e yield
    result = {}

    for key, samples in data_hist.items():
        extracted = []
        for sample in samples:
            parts = sample.split(',')
            timestamp = int(parts[1])
            yield_value = float(parts[2])
            extracted.append((timestamp, yield_value))
        result[key] = extracted

    # Exemplo de saída para os primeiros 5 elementos

    data_hist = result[f"{security_id}_yield"][:]
    timestamps = []
    yields = []
    for timestamp, yield_value in data_hist:
        timestamps.append(int(timestamp))
        yields.append(float(yield_value))

    return yields, timestamps

def getRatexMarketsData(security_id):
    import requests

    headers = {
        "path": "/",
        "Content-Type": "application/json",
        "Accept": "*/*"
    }
    url = "https://api.rate-x.io/"
    payload = {
        "serverName": "MDSvr",
        "method": "queryTrade",
        "content": {
            "cid": "f2443b24-44dd-fded-6dba-7a6c567b4ff5"
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json().get("data", [])

    # Procurar o item com o SecurityID correspondente
    for item in data:
        if item.get("SecurityID") == security_id:
            security_id = item.get("SecurityID")
            settle_price = float(item.get("SettlePrice"))
            yield_rate = float(item.get("Yield"))
            multiplier = 1/settle_price
            expires = security_id.split("-")[-1]  # exemplo: "2508"
            day = int(expires[:2])
            month = int(expires[2:])
            from datetime import datetime, date
            today = date.today()
            expiry_date = date(today.year, month, day)
            days_until = (expiry_date - today).days
            return security_id, settle_price, multiplier, yield_rate, expiry_date, days_until

    return None  # Caso não encontre

def getRatexTendency(market,N):

    historical_data,timestamps = getRatexHist(market,N,"1H")
    security_id, settle_price, multiplier, yield_rate, expiry_date, days_until = getRatexMarketsData(market)
    # Supondo que historical_data seja uma lista de floats
    y_vals = np.array(historical_data) * 100
    x_idx = np.arange(len(y_vals))  # Garantir que tenha mesmo tamanho de y_vals
    # Converter timestamps para datetime
    dates = [datetime.fromtimestamp(ts / 1000, tz=timezone.utc) for ts in timestamps]

    # Remoção de outliers via IQR (20-80%)
    Q1 = np.percentile(y_vals, 20)
    Q3 = np.percentile(y_vals, 80)
    IQR = Q3 - Q1
    mask = (y_vals >= Q1 - IQR) & (y_vals <= Q3 + IQR)

    # Regressão linear sem outliers
    coef = np.polyfit(x_idx[mask], y_vals[mask], 1)
    trend_line = coef[0] * x_idx + coef[1]

    # Diferença ponto a ponto
    diff = y_vals - trend_line

    # IQR sobre as diferenças (15-85%)
    q1 = np.percentile(diff, 15)
    q3 = np.percentile(diff, 85)
    iqr = q3 - q1
    lower_bound = q1 - 0.75 * iqr
    upper_bound = q3 + 0.75 * iqr
    valid_diffs = diff[(diff >= lower_bound) & (diff <= upper_bound)]

    max_diff = np.max(valid_diffs)
    min_diff = np.min(valid_diffs)

    # Linhas paralelas
    upper_line = trend_line + max_diff
    lower_line = trend_line + min_diff

    # Estender até data de expiração
    expiry = expiry_date
    # Se 'expiry' for datetime.date, converta diretamente para datetime com UTC
    expiry_dt = datetime.combine(expiry, datetime.min.time()).replace(tzinfo=timezone.utc)
    last_date = datetime.fromtimestamp(timestamps[-1] / 1000, tz=timezone.utc)
    time_scale = "1H"
    if time_scale == "1H":
        steps = int((expiry_dt - last_date).total_seconds() / 3600)
        freq = 'h'
    else:
        steps = (expiry_dt - last_date).days
        freq = 'd'

    x_ext = np.arange(len(y_vals) + steps)
    trend_line_extended = coef[0] * x_ext + coef[1]
    upper_line_extended = trend_line_extended + max_diff
    lower_line_extended = trend_line_extended + min_diff

    # Datas estendidas (para uso futuro, ex. plotagem)
    
    extended_dates = pd.date_range(start=last_date, periods=steps+1, freq=freq)

    return y_vals,trend_line,upper_line,lower_line,trend_line_extended,upper_line_extended,lower_line_extended,dates,extended_dates,expiry_dt
