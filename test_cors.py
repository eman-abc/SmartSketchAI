import requests

url = "https://smartsketch-api.onrender.com/api/register/"
headers = {
    "Origin": "https://smart-sketch-ai-idrj.vercel.app",
    "Access-Control-Request-Method": "POST"
}
try:
    response = requests.options(url, headers=headers, timeout=10)
    print("Status Code:", response.status_code)
    print("Headers:", dict(response.headers))
    print("Content:", response.text)
except Exception as e:
    print("Error:", e)
