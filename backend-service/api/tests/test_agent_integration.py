import os
import django
import sys
import json
# Setup Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartsketch_backend.settings")
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

def run_api_integration_test():
    print("\n=== STARTING API INTEGRATION TEST (AGENTIC CHAT) ===")
    
    client = APIClient()
    
    # 1. Setup User
    username = "api_investigator"
    password = "testpassword123"
    user, created = User.objects.get_or_create(username=username, defaults={"role": "forensic"})
    if created:
        user.set_password(password)
        user.save()
        
    # 2. Login & Get Token
    print(f"Logging in as {username}...")
    login_resp = client.post('/api/token/', {'username': username, 'password': password})
    assert login_resp.status_code == 200, "Login failed"
    token = login_resp.data['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    # 3. First Turn: Start a new case
    print("\n[API Turn 1] Message: 'Male, blue eyes'")
    thread_id = "api_test_thread_555"
    response = client.post('/api/forensic/chat/', {
        "message": "The suspect is a male with blue eyes",
        "thread_id": thread_id,
        "case_number": "TEST-2026-001"
    })
    
    assert response.status_code == 200, f"API failed: {response.data}"
    data = response.data
    print(f"Response: {json.dumps(data, indent=2)}")
    assert data['suspect_profile']['eye_color'] == "blue"
    
    # 4. Second Turn: Update the same case
    print("\n[API Turn 2] Message: 'Add black hair'")
    response2 = client.post('/api/forensic/chat/', {
        "message": "He also has black hair",
        "thread_id": thread_id
    })
    
    assert response2.status_code == 200, f"API failed: {response2.data}"
    data2 = response2.data
    print(f"Response: {json.dumps(data2, indent=2)}")
    
    # CRITICAL: Verify persistence through the API
    assert data2['suspect_profile']['eye_color'] == "blue", "Identity lost across API turns!"
    assert data2['suspect_profile']['hair_color'] == "black"
    
    print("\n[SUCCESS] API INTEGRATION TEST PASSED: Stateful agent is live at /api/forensic/chat/")

if __name__ == "__main__":
    try:
        run_api_integration_test()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] API TEST FAILED: {e}")
        sys.exit(1)
