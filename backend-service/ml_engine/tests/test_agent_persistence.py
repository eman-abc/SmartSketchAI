import os
import django
import sys
from unittest.mock import MagicMock

# 1. Setup Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartsketch_backend.settings")
django.setup()

from ml_engine.agent import SmartSketchAgent
from api.models import AgentCheckpoint, User

def run_persistence_test():
    print("\n=== STARTING FORENSIC PERSISTENCE TEST ===")
    
    # Setup test user
    user, _ = User.objects.get_or_create(username="test_investigator")
    thread_id = "test_case_999"
    
    # Cleanup previous tests
    AgentCheckpoint.objects.filter(thread_id=thread_id).delete()
    
    # --- TURN 1 ---
    print("\n[Turn 1] Investigator: 'The suspect is a male with blue eyes.'")
    agent = SmartSketchAgent() # Will use DjangoCheckpointer by default
    
    # Mocking LLM behavior since we don't have a real one in the test environment
    # The agent uses _mock_llm_logic when llm is None
    agent.run("The suspect is a male with blue eyes.", thread_id=thread_id)
    
    # Verify save
    count = AgentCheckpoint.objects.filter(thread_id=thread_id).count()
    print(f"Checkpoints in DB: {count}")
    assert count > 0, "Checkpoint should have been saved"
    
    # --- SIMULATE RESTART ---
    print("\n--- SIMULATING SERVER RESTART (New Agent Instance) ---")
    new_agent = SmartSketchAgent()
    
    # --- TURN 2 ---
    print("[Turn 2] Investigator: 'He also has black hair.'")
    # We send a new message. If persistence works, Turn 1's "blue eyes" should be preserved
    final_state = new_agent.run("He also has black hair.", thread_id=thread_id)
    
    profile = final_state['suspect_profile']
    print(f"\nFinal Forensic Profile:")
    print(f" - Eye Color: {profile.eye_color}")
    print(f" - Hair Color: {profile.hair_color}")
    
    # VALIDATION
    assert profile.eye_color == "blue", "Failed! Eye color from Turn 1 was lost."
    assert profile.hair_color == "black", "Failed! Hair color from Turn 2 was not updated."
    
    print("\n[SUCCESS] PERSISTENCE TEST PASSED: Identity maintained across sessions.")

if __name__ == "__main__":
    try:
        run_persistence_test()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] TEST FAILED: {e}")
        sys.exit(1)
