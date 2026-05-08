import requests

ODDS_API_KEY = "TU_API_KEY"

url = "https://api.the-odds-api.com/v4/sports"

params = {
    "90ae2f6d7b5ddcd76926f1cf40be2ad7": ODDS_API_KEY
}

response = requests.get(url, params=params)

print("STATUS:", response.status_code)

print(response.text)
