from discord_alerts import send_alert
from dotenv import load_dotenv
import os
import requests

load_dotenv()  # Carrega variáveis do .env

# 📞 Configuração do WhatsApp CallMeBot
NUMERO = "+5521979782518"
APIKEY = "4751080"
 
message = "Teste caio"

# Envio para WhatsApp
url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={message}&apikey={APIKEY}"
try:
    response = requests.post(url)
    if response.status_code == 200:
        print("Mensagem enviada ao WhatsApp com sucesso!")
    else:
        print(f"Erro ao enviar mensagem para WhatsApp: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Erro ao enviar mensagem para WhatsApp: {e}")
