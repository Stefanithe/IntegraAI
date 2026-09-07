# IntegraAI GUI v2

Versão corrigida da interface gráfica.

## Melhorias desta versão

- Ollama é solicitado a responder em JSON.
- O programa aceita pequenas variações de nomes.
- Se a LLM inverter origem e destino, o programa corrige.
- Campos faltantes podem ser completados por validação local.
- A LLM continua sendo consultada obrigatoriamente antes da integração.

## Executar

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m src.gui
```

Modelo padrão: `llama3.2:3b`.
