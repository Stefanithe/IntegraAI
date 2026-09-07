from datetime import datetime

def normalize_value(value, expected_type):
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    t = expected_type.lower()
    if t in {"string","str","texto"}: return value
    if t in {"int","integer","inteiro"}: return int(value)
    if t in {"float","double","decimal","numero","número"}:
        return float(value.replace(",", "."))
    if t in {"date","data"}:
        for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y"):
            try: return datetime.strptime(value, fmt).date().isoformat()
            except ValueError: pass
        raise ValueError(f"Data inválida: {value}")
    return value
