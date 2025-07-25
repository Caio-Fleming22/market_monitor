def send_alert(message):
    import requests
    from dotenv import load_dotenv
    import os

    load_dotenv()  # Carrega variáveis do .env

    # 📞 Configuração do WhatsApp CallMeBot
    NUMERO = os.getenv("NUMERO")
    APIKEY = os.getenv("APIKEY")  

    # Discord Webhook URL (coloque essa variável no .env)
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

    # Discord - envio via webhook
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        if response.status_code == 204:  # Webhook normalmente retorna 204 No Content
            print("Mensagem enviada ao Discord com sucesso!")
        else:
            print(f"Erro ao enviar mensagem para Discord: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem para Discord: {e}")

    # Whatsapp
    url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={message}&apikey={APIKEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Mensagem enviada ao WhatsApp com sucesso!")
        else:
            print(f"Erro ao enviar mensagem para WhatsApp: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem para WhatsApp: {e}")


