import requests

url = "https://smartsketch-api.onrender.com/"
try:
    response = requests.get(url, timeout=30)
    print("Status Code:", response.status_code)
    print("Content:", response.text)
except Exception as e:
    print("Error:", e)
