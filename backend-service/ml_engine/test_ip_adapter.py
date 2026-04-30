import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml_engine.pipeline import SmartSketchPipeline

def test():
    print("Testing Pipeline Initialization with IP-Adapter...")
    try:
        pipeline = SmartSketchPipeline.from_pretrained(
            device="cuda" if __import__("torch").cuda.is_available() else "cpu",
            enable_offload=True,
            enable_sketch=False, # Save memory
            enable_safety=False
        )
        print("Pipeline initialized successfully!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
