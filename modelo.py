import requests
import time

# =========================
# 🔑 CONFIG
# =========================

TOKEN = "8510764547:AAHFpJ1_aPFdDDIYjVptLbxNgUAQh-dat7o"
CHAT_ID = "1335805552"
ODDS_API_KEY = "90ae2f6d7b5ddcd76926f1cf40be2ad7"

# =========================
# 📩 TELEGRAM
# =========================

def send(msg):

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            }
        )
    except Exception as e:
        print("Error Telegram:", e)


# =========================
# 🔍 TEST API
# =========================

def scan():

    print("🔍 scan iniciado")

    send("🔍 bot escaneando")

    url = "https://api.the-odds-api.com/v4/sports"

    params = {
        "apiKey": ODDS_API_KEY
    }

    try:

        response = requests.get(url, params=params)

        print("STATUS API:", response.status_code)

        if response.status_code != 200:

            print("ERROR API:", response.text)

            send(f"❌ API ERROR {response.status_code}")

            return

        data = response.json()

        print("Datos recibidos:", len(data))

        send(f"✅ API OK - deportes: {len(data)}")

    except Exception as e:

        print("ERROR API:", e)

        send(f"❌ ERROR: {e}")


# =========================
# 🚀 LOOP PRINCIPAL
# =========================

print("🔥 BOT INICIADO")

while True:

    try:

        scan()

        print("⏳ esperando...")

        time.sleep(1800)

    except Exception as e:

        print("ERROR LOOP:", e)

        time.sleep(10)
