import requests
import json
import time

BASE_URL = "https://eman-abc--smartsketch-ml-fastapi-app.modal.run"

def test_health():
    print("Testing /health...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_analyze():
    print("\nTesting /analyze...")
    payload = {
        "system_prompt": "You are a helpful assistant.",
        "user_message": "Return a JSON object with a key 'status' and value 'ready'."
    }
    try:
        start = time.time()
        resp = requests.post(f"{BASE_URL}/analyze", json=payload, timeout=60)
        print(f"Status: {resp.status_code} (took {time.time() - start:.2f}s)")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Analyze failed: {e}")

def test_generate():
    print("\nTesting /generate (this may take a while)...")
    payload = {
        "prompt": "Male suspect, mid-40s, short brown hair, square jaw, brown eyes",
        "case_type": "criminal",
        "age": 45
    }
    try:
        start = time.time()
        # Modal might take a while if cold or if generation is intensive
        resp = requests.post(f"{BASE_URL}/generate", json=payload, timeout=180)
        print(f"Status: {resp.status_code} (took {time.time() - start:.2f}s)")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Success: {data.get('success')}")
            if data.get('image_base64'):
                print(f"Image received (Base64 length: {len(data['image_base64'])})")
        else:
            print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Generate failed: {e}")

if __name__ == "__main__":
    test_health()
    test_analyze()
    test_generate()
