import requests
import time

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"

def send(msg):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })

print("🔥 BOT ARRANCADO")

while True:

    print("📩 enviando mensaje")

    send("✅ Bot funcionando")

    time.sleep(60)
