def send_alert(message):
    import requests
    from dotenv import load_dotenv
    import os

    load_dotenv()  # Carrega variáveis do .env

    # 📞 Configuração do WhatsApp CallMeBot
    NUMERO = os.getenv("NUMERO")
    APIKEY = os.getenv("APIKEY")

    # Discord Webhook URLs (coloque essas variáveis no .env)
    DISCORD_WEBHOOK_URLS = [
        os.getenv("DISCORD_WEBHOOK_URL_1"),
        os.getenv("DISCORD_WEBHOOK_URL_2")
    ]

    # Envio para cada webhook do Discord
    for webhook_url in DISCORD_WEBHOOK_URLS:
        if webhook_url:  # Verifica se a URL existe
            try:
                response = requests.post(webhook_url, json={"content": message})
                if response.status_code == 204:  # Webhook normalmente retorna 204 No Content
                    print(f"Mensagem enviada ao Discord: {webhook_url}")
                else:
                    print(f"Erro ao enviar mensagem para Discord: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Erro ao enviar mensagem para Discord: {e}")
        else:
            print("Webhook URL não encontrada no .env")

    # Envio para WhatsApp
    url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={message}&apikey={APIKEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Mensagem enviada ao WhatsApp com sucesso!")
        else:
            print(f"Erro ao enviar mensagem para WhatsApp: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem para WhatsApp: {e}")
