def send_alert(message):
    import requests
    from dotenv import load_dotenv
    import os

    load_dotenv()  # Carrega variáveis do .env
    # Discord Auth
    authorization = os.getenv('AUTHORIZATION')
    # 📞 Configuração do WhatsApp CallMeBot
    NUMERO = os.getenv("NUMERO")
    APIKEY = os.getenv("APIKEY")  

    DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/SEU_WEBHOOK"
    #requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    headers = {
        "Authorization": f"{authorization}",
        "Content-Type": "application/json"
    }
    Request_URL = "https://discord.com/api/v9/channels/1398079091701321830/messages"
    requests.post(Request_URL, json={"content": message}, headers=headers)

    #Whatsapp
    url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={message}&apikey={APIKEY}"
    try:
        response = requests.get(url)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")


