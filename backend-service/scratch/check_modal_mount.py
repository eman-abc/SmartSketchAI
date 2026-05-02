import modal
try:
    print(f"modal.mount: {modal.mount}")
    print(f"dir(modal.mount): {dir(modal.mount)}")
except Exception as e:
    print(f"Error: {e}")
