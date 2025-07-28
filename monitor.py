import threading, json, time
from datetime import datetime, timezone
from discord_alerts import send_alert
from price_api import get_price, view_ema
from gatAllPendleMarkets import get_pendle_apy_data, get_pendle_markets
from getAllRatexMarkets import getRatexMarkets, getRatexMarketsData, getRatexTendency
import requests
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

 
MARKETS_FILE = "markets.json"
alerted = {}  # guarda timestamps: { "marketname_buy": last_alert_time, ... }

def can_send_alert(alert_key, interval_hours):
    now = time.time()
    last_alert = alerted.get(alert_key, 0)
    alert_interval = interval_hours * 3600  # horas para segundos
    if now - last_alert >= alert_interval:
        alerted[alert_key] = now
        return True
    return False

def get_token_info(marketAdd,id):
    url = f"https://api-v2.pendle.finance/core/v1/{id}/markets/{marketAdd}"
    response = requests.get(url)
    jsonn = json.loads(response.text)
    #jsonn.get("underlyingApy", {}) 
    ytRoi = float(jsonn.get("ytRoi", 0))
    
    url = f"https://api-v2.pendle.finance/core/v1/sdk/{id}/markets/{marketAdd}/swapping-prices"
    response = requests.get(url)
    jsonn = json.loads(response.text)
    ytMult = float(jsonn.get("underlyingTokenToYtRate", 0))
    return(ytMult,ytRoi)

def remove_market_by_name(market_name):
    try:
        with open(MARKETS_FILE, "r+") as f:
            data = json.load(f)
            data = [m for m in data if m["name"] != market_name]
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
        print(f"✅ Mercado removido após atingir alvo: {market_name}")
    except Exception as e:
        print(f"Erro ao remover mercado: {e}")

def remove_exact_market(target_market, target_type):
    """
    target_type: 'buy' ou 'sell'
    """
    try:
        target_field = "buy_target" if target_type == "buy" else "sell_target"
        target_value = target_market[target_field]

        with open(MARKETS_FILE, "r+") as f:
            data = json.load(f)
            data = [
                m for m in data
                if not (
                    m["name"] == target_market["name"] and
                    m["address"] == target_market["address"] and
                    m["id"] == target_market["id"] and
                    m["expires"] == target_market["expires"] and
                    m.get(target_field) == target_value
                )
            ]
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
        print(f"✅ Mercado removido após atingir alvo: {target_market['name']} ({target_type})")
    except Exception as e:
        print(f"Erro ao remover mercado: {e}")


def check_market(market):
    if "Expires" in market["name"]:
        print(market["name"])
        if "Solana" in market["name"]:
            token = market["name"].split(" ")[0]
            implied_apy, trend_line, upper_line, lower_line, trend_line_extended, \
            upper_line_extended, lower_line_extended, dates, \
            extended_dates, expiry_date = getRatexTendency(token,600)
            security_id, settle_price, ytMult, yield_rate, expiry_date, days_until = getRatexMarketsData(token)
            ytRoi = ""
            has_underlying_apy = False
        else:
            df_implied, implied_apy, underlying_apy, base_apy, tvl_in_k, trend_line, upper_line, lower_line, \
            trend_line_extended, upper_line_extended, lower_line_extended, dates, extended_dates, expiry_date, address = \
                get_pendle_apy_data(market["address"], market["expires"], "hour", market["id"])
            ytMult, ytRoi = get_token_info(market["address"], market["id"])
            has_underlying_apy = True

        current_price = implied_apy[-1]
    else:
        current_price = get_price(market["name"])

    if current_price is None:
        return {
            "name": market["name"],
            "address": market["address"],
            "id": market["id"],
            "expires": market["expires"],
            "current_price": None,
            "buy_target": market["buy_target"],
            "sell_target": market["sell_target"],
            "status_icon": "⚠️ Erro na API"
        }

    tolerance = market["tolerance"] / 100
    status = "🔴"
    interval_hours = market.get("alert_interval_hours", 3)

    time_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    data1 = datetime.strptime(time_now, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

    alert_key_proximo = market["name"] + "_near_buy"
    if abs(current_price - market["buy_target"]) <= market["buy_target"] * tolerance:
        status = "🟡 Próximo do Alvo"
        if can_send_alert(alert_key_proximo, interval_hours):
            if "Expires" in market["name"]:
                expiry_date_dt = datetime.combine(expiry_date, datetime.min.time())
                data1_naive = data1.replace(tzinfo=None)
                delta = expiry_date_dt - data1_naive
                yt_roi_str = f"↪️ YT ROI for hold token up to expiry = {ytRoi * 100:.2f} %" if isinstance(ytRoi, float) else ""

                if has_underlying_apy:
                    apy_str = f"↪️ Actual Underlying APY =  {round(underlying_apy[-1],2)}"
                else:
                    apy_str = f"↪️ Actual Underlying APY =  {round(yield_rate,2)}"

                send_alert(f"""
{market['name']}: ${current_price} Próximo do alvo de COMPRA: {market['buy_target']}%
↪️ YT Protocol Multiplier = {round(ytMult,2)}
{apy_str}
{yt_roi_str}
↪️ Days to expiry = {delta}""")
            else:
                send_alert(f"{market['name']}: ${current_price} Próximo do alvo de COMPRA: ${market['buy_target']}\n")

    alert_key_buy = market["name"] + "_buy"
    if current_price <= market["buy_target"]:
        status = "🟢 Alvo de COMPRA atingido"
        if can_send_alert(alert_key_buy, interval_hours):
            if "Expires" in market["name"]:
                expiry_date_dt = datetime.combine(expiry_date, datetime.min.time())
                data1_naive = data1.replace(tzinfo=None)
                delta = expiry_date_dt - data1_naive
                yt_roi_str = f"↪️ YT ROI for hold token up to expiry = {ytRoi * 100:.2f} %" if isinstance(ytRoi, float) else ""

                if has_underlying_apy:
                    apy_str = f"↪️ Actual Underlying APY =  {round(underlying_apy[-1],2)}"
                else:
                    apy_str = f"↪️ Actual Underlying APY =  {round(yield_rate,2)}"

                send_alert(f"""
                    🛒 Alvo de COMPRA atingido em {market['name']}: {current_price:.2f}%
                    ↪️ YT Protocol Multiplier = {round(ytMult,2)}
                    {apy_str}
                    {yt_roi_str}
                    ↪️ Days to expiry = {delta}""")
            else:
                send_alert(f"🛒 Alvo de COMPRA atingido em {market['name']}: ${current_price}\n")
            remove_exact_market(market, "buy")  # <-- remove após enviar alerta

    alert_key_sell = market["name"] + "_sell"
    if current_price >= market["sell_target"]:
        status = "🟢 Alvo de VENDA atingido"
        if can_send_alert(alert_key_sell, interval_hours):
            if "Expires" in market["name"]:
                expiry_date_dt = datetime.combine(expiry_date, datetime.min.time())
                data1_naive = data1.replace(tzinfo=None)
                delta = expiry_date_dt - data1_naive
                yt_roi_str = f"↪️ YT ROI for hold token up to expiry = {ytRoi * 100:.2f} %" if isinstance(ytRoi, float) else ""

                if has_underlying_apy:
                    apy_str = f"↪️ Actual Underlying APY =  {round(underlying_apy[-1],2)}"
                else:
                    apy_str = f"↪️ Actual Underlying APY =  {round(yield_rate,2)}"

                send_alert(f"""
                    👋 Alvo de VENDA atingido em {market['name']}: {current_price:.2f}%
                    ↪️ YT Protocol Multiplier = {round(ytMult,2)}
                    {apy_str}
                    {yt_roi_str}
                    ↪️ Days to expiry = {delta}""")
            else:
                send_alert(f"👋 Alvo de VENDA atingido em {market['name']}: ${current_price}\n")
            remove_exact_market(market, "sell") # <-- remove após enviar alerta

    # Verificando se há pelo menos 48 amostras
    if "Expires" in market["name"]:
        if len(implied_apy) >= 24:
            valor_inicial = max(implied_apy[-24:])
            valor_final = implied_apy[-1]
            queda_percentual = ((valor_inicial - valor_final) / valor_inicial) * 100

            if queda_percentual > 20 and can_send_alert(alert_key_sell, interval_hours):
                status = "🟢 Valor caiu mais de 20% nas últimas 24 h"
                send_alert(f"⚠️ O APY caiu {queda_percentual:.2f}% nas últimas 24 h. Pode ser uma ótima oportunidade, apenas confira se não ocorreu algum problema com o protocolo para esta queda acentuada.\n")

    if "Expires in:" not in market["name"]:
        signal, reason, trend, touched = view_ema(market["name"],0.3)
        if signal:
            send_alert(f"\nSinal: {signal}\nMotivo: Atingiu Região de {reason}\n{trend}\n{touched}")

    return {
        "name": market["name"],
        "current_price": current_price,
        "buy_target": market["buy_target"],
        "sell_target": market["sell_target"],
        "status_icon": status
    }


def get_market_status():
    with open(MARKETS_FILE) as f:
        data = json.load(f)
    return [check_market(m) for m in data]

def monitor_loop():
    while True:
        get_market_status()
        time.sleep(60)  # a cada 1 min

def start_monitoring():
    threading.Thread(target=monitor_loop, daemon=True).start()

