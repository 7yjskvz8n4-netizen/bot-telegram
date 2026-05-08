import requests

ODDS_API_KEY = "TU_API_KEY"

url = "https://api.the-odds-api.com/v4/sports"

params = {
    "167721723854a65832f09abdeb92952b": ODDS_API_KEY
}

response = requests.get(url, params=params)

print("STATUS:", response.status_code)

print(response.text)
