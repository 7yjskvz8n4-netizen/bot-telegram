import requests

API_KEY = "90ae2f6d7b5ddcd76926f1cf40be2ad7"

response = requests.get(
    "https://api.the-odds-api.com/v4/sports",
    params={"apiKey": API_KEY}
)

print("STATUS:", response.status_code)
print(response.text)
