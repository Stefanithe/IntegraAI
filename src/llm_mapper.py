import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from difflib import SequenceMatcher


def _normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _extract_json(text: str) -> dict[str, str]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("A LLM não retornou um objeto JSON reconhecível.")

    data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("A resposta da LLM não é um objeto JSON.")

    return {str(k): str(v) for k, v in data.items()}


def _ollama_generate(prompt: str) -> str:
    base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Não foi possível conectar ao Ollama. "
            "Confirme se ele está instalado e em execução."
        ) from exc

    result = body.get("response")
    if not result:
        raise RuntimeError("O Ollama não retornou uma resposta válida.")

    return str(result)


def suggest_mapping(
    source_fields: list[str],
    destination_schema: dict[str, str],
) -> dict[str, str]:
    prompt = f"""
Você é um componente de integração de dados.

Mapeie cada campo de ORIGEM para exatamente um campo de DESTINO com base
no significado semântico.

ORIGEM:
{json.dumps(source_fields, ensure_ascii=False)}

DESTINO:
{json.dumps(list(destination_schema.keys()), ensure_ascii=False)}

Responda SOMENTE com JSON no formato:
{{
  "campo_origem_1": "campo_destino_1",
  "campo_origem_2": "campo_destino_2"
}}

Regras obrigatórias:
- As CHAVES devem ser exatamente nomes presentes em ORIGEM.
- Os VALORES devem ser exatamente nomes presentes em DESTINO.
- Não inverta origem e destino.
- Não invente campos.
- Não escreva explicações.
""".strip()

    response_text = _ollama_generate(prompt)
    return _extract_json(response_text)


def _best_destination(source: str, destinations: list[str]) -> str | None:
    aliases = {
        "nome_cliente": ["nome", "full_name", "nome_completo"],
        "cpf_cliente": ["documento", "cpf", "document"],
        "dt_nasc": ["data_nascimento", "nascimento", "birth_date"],
        "data_nasc": ["data_nascimento", "nascimento", "birth_date"],
        "celular": ["telefone", "phone", "celular"],
        "email_cliente": ["email", "email_address"],
    }

    src_norm = _normalize_name(source)
    dest_by_norm = {_normalize_name(d): d for d in destinations}

    for preferred in aliases.get(src_norm, []):
        if _normalize_name(preferred) in dest_by_norm:
            return dest_by_norm[_normalize_name(preferred)]

    best = None
    best_score = 0.0
    for destination in destinations:
        score = SequenceMatcher(
            None,
            src_norm,
            _normalize_name(destination),
        ).ratio()

        if score > best_score:
            best = destination
            best_score = score

    return best if best_score >= 0.45 else None


def validate_mapping(
    mapping: dict[str, str],
    source_fields: list[str],
    destination_schema: dict[str, str],
) -> dict[str, str]:
    destinations = list(destination_schema.keys())
    source_by_norm = {_normalize_name(s): s for s in source_fields}
    dest_by_norm = {_normalize_name(d): d for d in destinations}

    valid: dict[str, str] = {}

    # 1) Tenta interpretar resposta no formato origem -> destino.
    for raw_source, raw_destination in mapping.items():
        source = source_by_norm.get(_normalize_name(raw_source))
        destination = dest_by_norm.get(_normalize_name(raw_destination))

        if source and destination:
            valid[source] = destination

    # 2) Se a LLM inverteu, tenta destino -> origem.
    if not valid:
        for raw_destination, raw_source in mapping.items():
            source = source_by_norm.get(_normalize_name(raw_source))
            destination = dest_by_norm.get(_normalize_name(raw_destination))

            if source and destination:
                valid[source] = destination

    # 3) Completa campos faltantes com heurística local.
    # A LLM continua sendo obrigatoriamente consultada antes deste passo.
    used_destinations = set(valid.values())

    for source in source_fields:
        if source in valid:
            continue

        destination = _best_destination(source, destinations)

        if destination and destination not in used_destinations:
            valid[source] = destination
            used_destinations.add(destination)

    return valid
