import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in environment.")
    exit(1)

try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.7)
    prompt = "Convert this suspect description into an optimized SDXL prompt and extract negative elements.\nUser: 'He had a rough, weathered face, no beard'\nFormat: {\"positive\": \"...\", \"negative\": \"...\"}"
    response = llm.invoke(prompt)
    print("Gemini Response:")
    print(response.content)
except Exception as e:
    print(f"Error calling Gemini: {e}")

