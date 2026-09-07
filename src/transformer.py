from .validator import normalize_value

def transform_rows(rows, mapping, schema):
    converted, errors = [], []
    for n, row in enumerate(rows, start=2):
        out, row_errors = {}, []
        for src, dst in mapping.items():
            try:
                out[dst] = normalize_value(row.get(src), schema[dst])
            except Exception as e:
                row_errors.append({"campo_origem":src,"campo_destino":dst,"erro":str(e)})
        for dst in schema:
            out.setdefault(dst, None)
        if row_errors:
            errors.append({"linha":n,"erros":row_errors,"registro_original":row})
        else:
            converted.append(out)
    return converted, errors
