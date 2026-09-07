import json, os, urllib.request
from dotenv import load_dotenv
load_dotenv()

base = os.getenv("OLLAMA_URL","http://localhost:11434").rstrip("/")
with urllib.request.urlopen(base+"/api/tags", timeout=10) as r:
    body = json.loads(r.read().decode("utf-8"))
print("Ollama conectado com sucesso.")
print("Modelos disponíveis:")
for m in body.get("models", []):
    print("-", m.get("name"))
