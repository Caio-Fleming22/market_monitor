import streamlit as st
from datetime import datetime
import json
from monitor import start_monitoring, get_market_status
from gatAllPendleMarkets import get_pendle_apy_data, get_pendle_markets
from getAllRatexMarkets import getRatexMarkets, getRatexMarketsData, getRatexTendency
from getUsualMarkets import getUsualMarkets
from parse_name import parse_name
from discord_alerts import send_alert
from price_api import get_price
import pandas as pd

MARKETS_FILE = "markets.json"

st.set_page_config(page_title="Market Monitor", layout="wide")
st.title("📈 Monitoramento de Markets")

ids = [1, 56, 146, 5000, 8453, 42161, 80094, 10]
nets = ["Ethereum", "BNB Chain", "Sonic Labs", "Mantle", "Base", "Arbitrum", "Berachain", "Optimism"]

all_markets_list = []

for i, id in enumerate(ids):
    markets = get_pendle_markets(id)
    if not markets.empty:
        net = nets[i]
        markets = markets.copy()
        markets['expiry_date'] = markets["expiry"].str.split('T').str[0]
        markets['net'] = net
        markets["label"] = markets["name"] + " (Expires in: " + markets['expiry_date'] + ") " + net
        all_markets_list.append(markets)

all_markets_df = pd.concat(all_markets_list, ignore_index=True)
pendle_len = len(all_markets_df)

markets_sol = getRatexMarkets()

# Aplicar transformação
markets_ratex = pd.DataFrame([parse_name(n) for n in markets_sol])

all_markets_list.append(markets_ratex)
rateX_len = len(markets_ratex)

usual_markets = getUsualMarkets()
normal_markets = pd.DataFrame([parse_name(n) for n in usual_markets])

all_markets_list.append(normal_markets)

# Concatenar todos os DataFrames em um só
markets = pd.concat(all_markets_list, ignore_index=True)

# Exibindo a lista de seleção múltipla
#selected_names = st.multiselect("Escolha um ou mais mercados", options)

# Define o mercado desejado (exatamente como aparece no 'label')
default_market_name = "slvlUSD"  # substitua pela label desejada

# Buscar índice do mercado default
default_index = markets[markets["name"] == default_market_name].index
default_index = int(default_index[0]) if not default_index.empty else 0  # fallback para 0 se não encontrar


# 1. Seleção do market - FORA DO FORM
st.sidebar.markdown("<h3 style='font-size: 20px;'>Selecione o Market</h3>", unsafe_allow_html=True)

market_name = st.sidebar.selectbox(
    "Markets:",
    markets["label"].tolist(),
    index=default_index,
    format_func=lambda x: x.upper()
)

selected_row = markets[markets["label"] == market_name].iloc[0]

selected_index = markets[markets["label"] == market_name].index[0]
name = selected_row["name"]
net_name = selected_row["net"]
label = selected_row["label"]

if selected_index <= pendle_len:
    id = ids[nets.index(net_name)]
    address = selected_row["address"]
    expires = selected_row["expiry"]
    value=1.00
    # 2. Obtendo dados sempre que a seleção mudar
    try:
        df_implied, implied_apy, underlying_apy, base_apy, tvl_in_k, trend_line, upper_line, lower_line, \
        trend_line_extended, upper_line_extended, lower_line_extended, dates, extended_dates, \
        expiry_date, address = get_pendle_apy_data(address, expires, "hour", id)
    except Exception as e:
        st.error(f"Erro ao obter dados do mercado: {e}")
        st.stop()
elif pendle_len < selected_index <= rateX_len:
    value=1.00
    try:
        implied_apy,trend_line,upper_line,lower_line,trend_line_extended, \
        upper_line_extended,lower_line_extended,dates, \
        extended_dates,expiry_date = getRatexTendency(name,500)
        address = -1
        id = -1
        # Converter para objeto datetime
        expires = expiry_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    except Exception as e:
        st.error(f"Erro ao obter dados do mercado: {e}")
        st.stop()
else:
    value=0.10
    try:
        lower_line = [0.0]
        upper_line = [0.0]
        expiry_date = "2026-12-30"
        address = -1
        id = -1
        # Converter para objeto datetime
        expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
        expires = expiry_date_obj.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    except Exception as e:
        st.error(f"Erro ao obter dados do mercado: {e}")
        st.stop()

# 3. Inputs dentro do form
with st.form("add_market"):
    st.subheader("Cadastrar novo Market")
    st.markdown(f"<span style='font-size:22px'><strong>Market Selecionado:</strong> {label}</span>", unsafe_allow_html=True)

    buy_target = st.number_input("Alvo de Compra", step=0.01, value=round(lower_line[-1], 2))
    sell_target = st.number_input("Alvo de Venda", step=0.01, value=round(upper_line[-1], 2))
    alert_interval = st.number_input("Intervalo de Alerta (h)", step=0.01, value=value)
    tolerance = st.slider("Tolerância (%)", 0.0, 20.0, 2.0)

    submit = st.form_submit_button("Cadastrar")

    if submit:
        try:
            with open(MARKETS_FILE, "r+") as f:
                data = json.load(f)
                if any(m["address"] == address for m in data) & any(m["address"] != -1 for m in data):
                    st.warning("Este mercado já está cadastrado.")
                else:
                    data.append({
                        "name": market_name,
                        "address": address,
                        "id": id,
                        "expires": expires,
                        "buy_target": buy_target,
                        "sell_target": sell_target,
                        "tolerance": tolerance,
                        "alert_interval_hours": alert_interval
                    })
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2)
                    st.success(f"{market_name} cadastrado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")


# Visualização dos markets monitorados
st.subheader("Markets Monitorados")
markets = get_market_status()

for m in markets:
    price = f"${m['current_price']:.2f}" if m['current_price'] is not None else "❌ Erro"
    is_pendle = "(Expires in:" in m["name"]

    if is_pendle:
        buy_target_str = f"{m['buy_target']:.2f}%"
        sell_target_str = f"{m['sell_target']:.2f}%"
    else:
        buy_target_str = f"${m['buy_target']:.2f}"
        sell_target_str = f"${m['sell_target']:.2f}"
    
    st.markdown(f"""
    <div style="margin-bottom:20px; padding:10px; border:1px solid #ddd; border-radius:8px;">
        <strong>Market:</strong> {m['name']}<br>
        💰 <strong>Preço Atual:</strong> {price}<br>
        🎯 <strong>Alvo de Compra:</strong> {buy_target_str}<br>
        🎯 <strong>Alvo de Venda:</strong> {sell_target_str}<br>
        📊 <strong>Status:</strong> {m['status_icon']}
    </div>
    """, unsafe_allow_html=True)

start_monitoring()  # roda em background

# Botão para remover o último mercado adicionado
st.sidebar.markdown("---")
st.sidebar.markdown("⚠️ <strong>Admin Tools</strong>", unsafe_allow_html=True)
if st.sidebar.button("🗑️ Remover último mercado cadastrado"):
    try:
        with open(MARKETS_FILE, "r+") as f:
            data = json.load(f)
            if data:
                last_market = data.pop()
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=2)
                st.sidebar.success(f"Removido: {last_market['name']}")
                st.experimental_rerun()  # 🔁 força recarregamento da app
            else:
                st.sidebar.warning("Nenhum market para remover.")
    except Exception as e:
        st.sidebar.error(f"Erro ao remover: {e}")