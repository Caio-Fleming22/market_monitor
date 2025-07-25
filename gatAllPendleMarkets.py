def get_pendle_markets(id):
    import requests
    import json
    import pandas as pd
    import statistics

    url = f"https://api-v2.pendle.finance/core/v1/{id}/markets/active"
    response = requests.get(url)
    data = json.loads(response.text)

    rows = []
    df = pd.DataFrame()
    for market in data["markets"]:
        details = market["details"]
        row = {
            "name": market["name"],
            "address": market["address"],
            "expiry": market["expiry"],
            "liquidity": details["liquidity"],
            "pendleApy": details["pendleApy"],
            "impliedApy": details["impliedApy"],
            "aggregatedApy": details["aggregatedApy"],
            "maxBoostedApy": details["maxBoostedApy"],
            "feeRate": details["feeRate"],
            "yieldMin": details["yieldRange"]["min"],
            "yieldMax": details["yieldRange"]["max"],
            "creationTimestamp": market["timestamp"]
        }
        rows.append(row)
        df = pd.DataFrame(rows)

    return df
    
def get_pendle_apy_data(address,expiry,time_scale,id):
    # Importar Bibliotecas Python
    import requests
    import json
    import pandas as pd
    import matplotlib.pyplot as plt
    from datetime import datetime, timezone
    import matplotlib.dates as mdates
    import numpy as np
    #from statsmodels.tsa.arima.model import ARIMA
    #from prophet import Prophet
    
    #id's = 1 - ETH , 10 OP , 56 - BNB, 146 - SONIC LABS, 5000 - Mantle, 8453 - Base, 42161 - Arb, 80094 -BERA
    # Retorna todos os itens que correspondem ao nome
    def get_matches_by_name(df, name):
        return df[df['name'].str.lower() == name.lower()]
    
    # Retorna a linha completa de acordo com o índice do resultado filtrado
    def get_row_by_name_and_index(df, name, index=0):
        matches = get_matches_by_name(df, name)
        if not matches.empty and index < len(matches):
            return matches.iloc[index]
        else:
            return None

    # Retorna apenas o address do item filtrado por índice
    def get_address_by_name(df, name, index=0):
        row = get_row_by_name_and_index(df, name, index)
        return row['address'] if row is not None else None

    # Retorna o expiry formatado do item filtrado por índice
    def get_expiry_by_name(df, name, index=0):
        row = get_row_by_name_and_index(df, name, index)
        return row['expiry'].split('T')[0] if row is not None else None

    # Exemplo de uso
   
    expiry = expiry.split('T')[0]
    url = f"https://api-v2.pendle.finance/core/v1/{id}/markets/{address}/historical-data?time_frame={time_scale}"
    response = requests.get(url)
    historical_data = json.loads(response.text)
    

    # Convert timestamps para datas legíveis
    dates = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in historical_data['timestamp']]

    # Convert strings para floats
    base_apy = [float(x) * 100 for x in historical_data['baseApy']]
    implied_apy = [float(x) * 100 for x in historical_data['impliedApy']]
    underlying_apy = [float(x) * 100 for x in historical_data['underlyingApy']]
    tvl = [float(x) for x in historical_data['tvl']]
    tvl_in_k = [float(value) / 1000000 for value in tvl]

    # Criar DataFrame para usar rolling()
    df_implied = pd.DataFrame({
        'date': dates,
        'implied_apy': implied_apy
    })

    # Média móvel de N períodos
    #N = 7  # você pode alterar conforme necessário
    #df_implied['implied_apy_ma'] = df_implied['implied_apy'].rolling(window=N).mean()

    # Regressão linear para tendência
    x = np.arange(len(df_implied))  # dias como sequência de inteiros
    y = df_implied['implied_apy'].values

    Q1 = np.percentile(y, 20)
    Q3 = np.percentile(y, 80)
    IQR = Q3 - Q1
    mask = (y >= Q1 - 1 * IQR) & (y <= Q3 + 1 * IQR)

    # aplicar regressão apenas nos dados sem outliers
    coef = np.polyfit(x[mask], y[mask], 1)
    trend_line = coef[0] * x + coef[1]

    # Calcular as diferenças ponto a ponto
    diff = np.array(implied_apy) - np.array(trend_line)

    # Remover outliers via IQR
    q1 = np.percentile(diff, 15)
    q3 = np.percentile(diff, 85)
    iqr = q3 - q1
    lower_bound = q1 - 0.75 * iqr
    upper_bound = q3 + 0.75 * iqr

    # Filtrar diffs válidos
    valid_diffs = diff[(diff >= lower_bound) & (diff <= upper_bound)]
    
    # Calcular os limites superior e inferior com os dados limpos
    max_diff = np.max(valid_diffs)
    min_diff = np.min(valid_diffs)

    # Gerar as linhas paralelas
    upper_line = [y + max_diff for y in trend_line]
    lower_line = [y + min_diff for y in trend_line]

    # Extender a linha de tendência até a data de expiração

    expiry_date = datetime.strptime(expiry, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    last_date = dates[-1]  # remove timezone if needed
    if time_scale == "hour":
        days_until_expiry = (expiry_date - dates[-1]).total_seconds() / 3600 # em horas
        extended_dates = pd.date_range(dates[-1], expiry_date, freq='h')
    else:
        days_until_expiry = (expiry_date - dates[-1]).days # em dias
        extended_dates = pd.date_range(dates[-1], expiry_date, freq='D')

    x_extended = np.arange(len(df_implied) + days_until_expiry)  # Sequência extendida de inteiros
    trend_line_extended = coef[0] * x_extended + coef[1]  # Extrapolando a linha de tendência
    upper_line_extended = trend_line_extended + max_diff
    lower_line_extended = trend_line_extended + min_diff

    # Gerar datas para a linha de tendência estendida

    

    # Assumindo df_implied['implied_apy'] como série temporal
    #model = ARIMA(df_implied['implied_apy'], order=(80,1,80))  # Ordem pode ser ajustada
    #model_fit = model.fit()
    # Forecast
    #forecast = model_fit.forecast(steps=days_until_expiry)

    # Create future dates
    #future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_until_expiry)

    # Build forecast DataFrame
    #df_forecast = pd.DataFrame({
    #    'date': future_dates,
    #    'forecast_ap': forecast.values
    #})

    return(df_implied,implied_apy,underlying_apy,base_apy,tvl_in_k,trend_line,upper_line,lower_line,trend_line_extended,upper_line_extended,lower_line_extended,dates,extended_dates,expiry_date,address)

