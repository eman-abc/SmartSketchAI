import modal

app = modal.App("test-build")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(image=image)
def test():
    print("Hello from Modal")
