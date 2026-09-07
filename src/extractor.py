import csv, json
from pathlib import Path

def read_csv(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV não encontrado: {path}")
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fields = r.fieldnames or []
    if not fields:
        raise ValueError("CSV sem cabeçalho.")
    return rows, fields

def read_destination_schema(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Esquema não encontrado: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("O esquema deve ser um objeto JSON não vazio.")
    return {str(k): str(v).lower() for k, v in data.items()}
