import requests,time
import pandas as pd
from scipy.signal import find_peaks

def get_price(symbol):    
    try:
        sym = symbol
        now = int(time.time())
        start_time = now - (1 * 3600)
        url = "https://api.backpack.exchange/api/v1/klines"
        print(symbol)
        params = {
            "symbol": sym,
            "interval": "1m",
            "startTime": start_time,
            "endTime": now,
            "klinePriceType": "LastPrice"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        klines = response.json()
        if klines:
            df = pd.DataFrame(klines)
            for col in ["open", "high", "low", "close", "volume", "quoteVolume"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            df["start"] = pd.to_datetime(df["start"])
            last = df.iloc[-1]
            price = last["close"]
        #coingecko_id = symbol_map.get(symbol.upper())
        #if not coingecko_id:
        #    print(f"[ERRO] Market {symbol} não mapeado para CoinGecko.")
        #    return None

        #url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        #r = requests.get(url)
        #r.raise_for_status()
        return price #r.json()[coingecko_id]["usd"]
    except requests.exceptions.HTTPError as e:
        print(f"Erro ao buscar preço de {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar preço de {symbol}: {e}")
        return None


def identificar_congestao(df: pd.DataFrame, timeframe: str) -> bool:
    # Cálculo das EMAs
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema100'] = df['close'].ewm(span=100).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    # Parâmetros por timeframe
    limites_por_tf = {
        "5m": {"dist_pct_max": 0.5, "inclinacao_max": 0.1, "atraso": 8},
        "15m": {"dist_pct_max": 1, "inclinacao_max": 0.15, "atraso": 5},
        "1h": {"dist_pct_max": 1.5, "inclinacao_max": 0.25, "atraso": 3},
        "4h": {"dist_pct_max": 2, "inclinacao_max": 0.35, "atraso": 3},
        "1d": {"dist_pct_max": 2.5, "inclinacao_max": 0.4, "atraso": 2}
    }

    # Parâmetros default se timeframe não for reconhecido
    params = limites_por_tf.get(timeframe, {"dist_pct_max": 2.5, "inclinacao_max": 0.1, "atraso": 5})
    atraso = params["atraso"]

    # Últimos valores das EMAs
    emas = df[['ema21', 'ema50', 'ema100', 'ema200']].iloc[-1]
    max_ema = emas.max()
    min_ema = emas.min()

    # Verifica proximidade entre EMAs
    dist_pct = abs(max_ema - min_ema) / max_ema * 100
    todas_proximas = dist_pct < params["dist_pct_max"]
    
    # Verifica horizontalidade (baixa inclinação)
    inclinacoes = {}
    inclinacoes_long = {}
    direcoes_ema = {}
    for period in [21, 50, 100, 200]:
        atual = df[f'ema{period}'].iloc[-1]
        anterior = df[f'ema{period}'].iloc[-1 - atraso]
        anterior_long = df[f'ema{period}'].iloc[-1 - (4*atraso)]
        inclinacao_pct = (atual - anterior) / anterior * 100
        inclinacao_pct_long = (atual - anterior_long) / anterior_long * 100
        inclinacoes[period] = abs(inclinacao_pct)
        # Verificar se a inclinação é positiva ou negativa
        if inclinacao_pct_long > 0.025:
            direcoes_ema[period] = "rising"
        elif inclinacao_pct_long < -0.025:
            direcoes_ema[period] = "falling"
        else:
            direcoes_ema[period] = "flat"

    # Pelo menos 3 inclinações devem estar abaixo do limite
    todas_horizontais = sum(i < params["inclinacao_max"] for i in inclinacoes.values()) >= 3

    return todas_proximas and todas_horizontais, direcoes_ema

def detectar_pivots(df, window=2, distancia_minima=3):
    """
    Detecta pivots de alta e baixa após suavizar preços com média móvel simples.

    Retorna índices dos pivots de alta (máximos locais) e baixa (mínimos locais),
    e também as séries suavizadas (high_smooth, low_smooth).
    """
    high_smooth = df['high'].rolling(window=window, center=True).mean()
    low_smooth = df['low'].rolling(window=window, center=True).mean()

    high_smooth_clean = high_smooth.dropna()
    low_smooth_clean = low_smooth.dropna()

    peaks, _ = find_peaks(high_smooth_clean, distance=distancia_minima)
    valleys, _ = find_peaks(-low_smooth_clean, distance=distancia_minima)

    offset = (window - 1) // 2

    indices_pivots_alta = peaks + offset
    indices_pivots_baixa = valleys + offset

    return indices_pivots_alta.tolist(), indices_pivots_baixa.tolist(), indices_pivots_alta, indices_pivots_baixa
  
def obter_ultimo_pivot(df, window=2, distancia_minima=3):
    _,_,indices_alta, indices_baixa = detectar_pivots(df, window=window, distancia_minima=distancia_minima)
    n = len(df)

    if len(indices_alta) == 0 and len(indices_baixa) == 0:
        return min(6, n)  # fallback

    ultimo_pivot = max(
        indices_alta.max() if len(indices_alta) > 0 else 0,
        indices_baixa.max() if len(indices_baixa) > 0 else 0
    )
    return n - ultimo_pivot

def detectar_tendencia_regressao(df, n=3, tolerancia=0.1):
    # Usar ponto médio em vez do close
    mids = ((df['high'] + df['low']) / 2).iloc[-n:]
    x = list(range(len(mids)))
    y = mids.values

    # Regressão linear simples
    a = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / \
        (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
    b = (sum(y) - a * sum(x)) / n  # intercepto (não usado, mas mantido)

    # Variação percentual do início ao fim
    variacao_pct = (mids.iloc[-1] - mids.iloc[0]) / mids.iloc[0] * 100

    if variacao_pct > tolerancia:
        return "rising"
    elif variacao_pct < -tolerancia:
        return "falling"
    else:
        return "lateral"

def analisar_pullback_volume(df, pivot_index, tendencia, n=3, media_volume_window=10, limite_proporcao_contraria=0.70):
    """
    Analisa o volume dos candles desde o último pivot até agora, levando em conta a tendência (alta ou baixa).

    Parâmetros:
        df: DataFrame com ['open', 'close', 'volume']
        pivot_index: índice do último pivot detectado
        tendencia: str, 'rising' ou 'falling'
        n: número de candles desde o pivot (None para pegar todos até o fim)
        media_volume_window: janela para cálculo de volume médio de referência
        limite_proporcao_contraria: limite de volume de candles contrários à tendência

    Retorna:
        dict com métricas e classificação
    """

    if n is not None:
        candles = df.iloc[pivot_index+1 : pivot_index+1+n]
    else:
        candles = df.iloc[pivot_index+1:]

    if candles.empty:
        return {"Error": "No candles after pivot."}

    volume_total = candles["volume"].sum()
    volume_medio_ref = df["volume"].iloc[-media_volume_window:].mean()

    
    # 👉 Se a tendência for lateral, usamos outro critério
    if tendencia == 'lateral':
        desvio_volume = candles["volume"].std()
        media_volume = candles["volume"].mean()

        if media_volume < volume_medio_ref * 0.75 and desvio_volume < volume_medio_ref * 0.25:
            classificacao = "Consolidation (Low and Stable Volume)"
        elif media_volume > volume_medio_ref * 1.25:
            classificacao = "Possible breakout (above average volume in laterality)"
        else:
            classificacao = "Neutral Moviment in Laterality"

        return {
            "volume_total": volume_total,
            "volume_medio_ref": volume_medio_ref,
            "media_volume": media_volume,
            "desvio_volume": desvio_volume,
            "classificacao": classificacao
        }

    # Classificação dos candles:
    if tendencia == 'rising':
        volume_contrario = candles[candles["close"] < candles["open"]]["volume"].sum()
        volume_a_favor = candles[candles["close"] > candles["open"]]["volume"].sum()
    elif tendencia == 'falling':
        volume_contrario = candles[candles["close"] > candles["open"]]["volume"].sum()
        volume_a_favor = candles[candles["close"] < candles["open"]]["volume"].sum()
    else:
         raise ValueError("Trend need to be 'rising', 'falling' ou 'lateral'!")

    proporcao_contraria = volume_contrario / volume_total if volume_total > 0 else 0

    # Classificação do pullback
    if volume_total < volume_medio_ref * 0.75:
        if proporcao_contraria > limite_proporcao_contraria:
            classificacao = "dangerous pullback (week volume, but dominant counter candles)"
        else:
            classificacao = "helph pullback (week volume, trend should continue)"
    elif proporcao_contraria > limite_proporcao_contraria:
        classificacao = "possible reversal (dominant counter volume)"
    else:
        classificacao = "neutral pullback (volume within normal)"

    return {
        "volume_total": volume_total,
        "volume_medio_ref": volume_medio_ref,
        "volume_a_favor": volume_a_favor,
        "volume_contrario": volume_contrario,
        "proporcao_contraria": proporcao_contraria,
        "classificacao": classificacao
    }
    
def view_ema(symbol,tolerance):
    try:
        sym = symbol
        now = int(time.time())
        start_time = now - (900 * 3600)
        url = "https://api.backpack.exchange/api/v1/klines"
        params = {
            "symbol": sym,
            "interval": "4h",
            "startTime": start_time,
            "endTime": now,
            "klinePriceType": "LastPrice"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        klines = response.json()
        if klines:
            df = pd.DataFrame(klines)
            for col in ["open", "high", "low", "close", "volume", "quoteVolume"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            df["start"] = pd.to_datetime(df["start"])

            # Calcular EMAs
            for period in [21, 50, 100, 200]:
                df[f"EMA_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
            last = df.iloc[-1]
            price = last["close"]

            lastn = df.tail(6)
            tolerance = 0.01 * tolerance / 100
            # EMA_50
            ema50_upper = lastn['EMA_50'] * (1 + tolerance)
            ema50_lower = lastn['EMA_50'] * (1 - tolerance)
            touched_ema50 = (
                ((lastn['high'] >= ema50_lower) & (lastn['low'] <= ema50_upper))
            ).any()

            # EMA_100
            ema100_upper = lastn['EMA_100'] * (1 + tolerance)
            ema100_lower = lastn['EMA_100'] * (1 - tolerance)
            touched_ema100 = (
                ((lastn['high'] >= ema100_lower) & (lastn['low'] <= ema100_upper))
            ).any()

            # EMA_200
            ema200_upper = lastn['EMA_200'] * (1 + tolerance)
            ema200_lower = lastn['EMA_200'] * (1 - tolerance)
            touched_ema200 = (
                ((lastn['high'] >= ema200_lower) & (lastn['low'] <= ema200_upper))
            ).any()

            congestao, direcoes_ema = identificar_congestao(df, timeframe="4h")
            long_term_trend = direcoes_ema[max(direcoes_ema.keys())]

            # Detectar número de candles de retorno a média a partir do último pivot
            n = obter_ultimo_pivot(df, window=2, distancia_minima=3) 
            if n > len(df):
                n = len(df)

            # Tendência e Volume de Pullback
            short_term_trend = detectar_tendencia_regressao(df, n, tolerancia=0.3)

            pullback_volume = analisar_pullback_volume(df, pivot_index=n, tendencia=short_term_trend, n=n, media_volume_window=n*5, limite_proporcao_contraria=0.70)
            
            ema50 = last.get("EMA_50")
            ema100 = last.get("EMA_100")
            ema200 = last.get("EMA_200")
            signal = None
            reason = None
            trend = None
            touched = None
            if ema50 and ema100 and ema200:
                delta50 = ((price - ema50) / ema50) * 100
                delta100 = ((price - ema100) / ema100) * 100
                delta200 = ((price - ema200) / ema200) * 100
                # ---- EMA_50 ----
                if (-tolerance < delta50 < tolerance):
                    if long_term_trend == "falling" and short_term_trend == "rising" and congestao == False and pullback_volume["classificacao"] != "possible reversal (dominant counter volume)" and pullback_volume["classificacao"] != "dangerous pullback (week volume, but dominant counter candles)":
                        signal = f"📉 VENDA (resistência EMA_50 no gráfico de 4h): preço {price:.5f} atingiu a região da EMA_50 vindo de baixo e o volume fraco indica que isso é um pullback."
                        reason = "EMA_50"
                    elif long_term_trend == "rising" and short_term_trend == "falling" and congestao == False and pullback_volume["classificacao"] != "possible reversal (dominant counter volume)" and pullback_volume["classificacao"] != "dangerous pullback (week volume, but dominant counter candles)":
                        signal = f"📈 COMPRA (suporte EMA_50 no gráfico de 4h): preço {price:.5f} atingiu a região da EMA_50 vindo de cima e o volume fraco indica que isso é um pullback."
                        reason = "EMA_50"

                # ---- EMA_100 ----
                elif (-tolerance < delta100 < tolerance):
                    if long_term_trend == "falling" and short_term_trend == "rising" and congestao == False and pullback_volume["classificacao"] != "possible reversal (dominant counter volume)" and pullback_volume["classificacao"] != "dangerous pullback (week volume, but dominant counter candles)":
                        signal = f"📉 VENDA FORTE (resistência EMA_100 no gráfico de 4h): preço {price:.5f} atingiu a região da EMA_100 vindo de baixo e o volume fraco indica que isso é um pullback."
                        reason = "EMA_100"
                    elif long_term_trend == "rising" and short_term_trend == "falling" and congestao == False and pullback_volume["classificacao"] != "possible reversal (dominant counter volume)" and pullback_volume["classificacao"] != "dangerous pullback (week volume, but dominant counter candles)":
                        signal= f"📈 COMPRA FORTE (suporte EMA_100 no gráfico de 4h): preço {price:.5f} atingiu a região da EMA_100 vindo de cima e o volume fraco indica que isso é um pullback."
                        reason = "EMA_100"

                # ---- EMA_200 ----
                elif (-tolerance < delta200 < tolerance):
                    if long_term_trend == "rising" and long_term_trend == "falling" and short_term_trend == "rising" and congestao == False and pullback_volume["classificacao"] != "possible reversal (dominant counter volume)" and pullback_volume["classificacao"] != "dangerous pullback (week volume, but dominant counter candles)":
                        signal = f"📉 VENDA MUITO FORTE (resistência EMA_200 no gráfico de 4h): preço {price:.5f} atingiu a região da EMA_200 vindo de baixo e o volume fraco indica que isso é um pullback."
                        reason = "EMA_200"
                    elif long_term_trend == "rising" and short_term_trend == "falling" and congestao == False and pullback_volume["classificacao"] != "possible reversal (dominant counter volume)" and pullback_volume["classificacao"] != "dangerous pullback (week volume, but dominant counter candles)":
                        signal = f"📈 COMPRA MUITO FORTE (suporte EMA_200 no gráfico de 4h): preço {price:.5f} atingiu a região da EMA_200 vindo de cima e o volume fraco indica que isso é um pullback."
                        reason = "EMA_200"
                if touched_ema50 or touched_ema100 or touched_ema200:
                    touched_list = (f"")
                    if touched_ema50:
                        touched_list += (f"EMA_50")
                    if touched_ema100:
                        touched_list += (f" EMA_100")
                    if touched_ema200:
                        touched_list += (f" EMA_200")
                    touched_str = (touched_list) if touched_list else ""
                    touched = f"Alerta: O preço já tocou na {touched_str}, pode ser que o tempo para entrada já tenha passado ou o preço ainda está em congestão nesta área. Verifique se ainda é válida a entrada."
                else:
                    touched = f"Ainda não ocorreu o toque na EMA. Você pode conseguir uma entrada no tempo ideal."

                trend = f"Tendência de Longo prazo (EMA_200): {direcoes_ema[max(direcoes_ema.keys())]}"
                
        return signal, reason, trend, touched
    except requests.exceptions.HTTPError as e:
        print(f"Erro ao buscar EMA de {symbol}: {e}")
        return None, None, None, None
    except Exception as e:
        print(f"Erro inesperado ao buscar EMA de {symbol}: {e}")
        return None, None, None, None