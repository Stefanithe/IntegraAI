import json
from pathlib import Path

def export_json(records, path):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

def export_report(total, converted_count, errors, mapping, path):
    report = {
        "total_registros": total,
        "convertidos_com_sucesso": converted_count,
        "registros_com_erro": len(errors),
        "mapeamento_utilizado": mapping,
        "erros": errors
    }
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
