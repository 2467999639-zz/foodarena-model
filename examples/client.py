"""Run after starting python -m foodarena.api from the repository root."""
import json
from pathlib import Path
from urllib.request import Request, urlopen

payload = Path(__file__).with_name("request.json").read_bytes()
request = Request("http://127.0.0.1:8000/recommend", payload, {"Content-Type": "application/json"})
with urlopen(request, timeout=10) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
