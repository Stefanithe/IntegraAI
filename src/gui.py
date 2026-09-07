import os, threading, tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from dotenv import load_dotenv
from .extractor import read_csv, read_destination_schema
from .llm_mapper import suggest_mapping, validate_mapping
from .transformer import transform_rows
from .exporter import export_json, export_report

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/".env")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IntegraAI")
        self.geometry("980x680")
        self.minsize(900, 620)

        self.source = tk.StringVar(value=str(BASE_DIR/"dados"/"clientes_origem.csv"))
        self.schema = tk.StringVar(value=str(BASE_DIR/"dados"/"esquema_destino.json"))
        self.status = tk.StringVar(value="Pronto.")
        self.rows = []; self.fields = []; self.dest_schema = {}; self.mapping = {}

        top = ttk.Frame(self, padding=16); top.pack(fill="x")
        ttk.Label(top, text="IntegraAI", font=("Segoe UI",22,"bold")).pack(anchor="w")
        ttk.Label(top, text="Integração inteligente de dados com LLM local via Ollama").pack(anchor="w")

        box = ttk.LabelFrame(self, text="Arquivos", padding=12)
        box.pack(fill="x", padx=16)
        self._file_row(box, 0, "CSV de origem:", self.source, self.pick_csv)
        self._file_row(box, 1, "Esquema JSON:", self.schema, self.pick_json)
        box.columnconfigure(1, weight=1)

        actions = ttk.Frame(self, padding=(16,12)); actions.pack(fill="x")
        self.btn_ai = ttk.Button(actions, text="Analisar com IA", command=self.analyze)
        self.btn_ai.pack(side="left")
        self.btn_convert = ttk.Button(actions, text="Converter dados", command=self.convert, state="disabled")
        self.btn_convert.pack(side="left", padx=8)
        ttk.Button(actions, text="Abrir pasta de saída", command=self.open_output).pack(side="left")

        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=16, pady=4)
        left = ttk.LabelFrame(pane, text="Mapeamento sugerido", padding=10)
        right = ttk.LabelFrame(pane, text="Log", padding=10)
        pane.add(left, weight=3); pane.add(right, weight=2)

        self.tree = ttk.Treeview(left, columns=("o","d"), show="headings")
        self.tree.heading("o", text="Campo de origem"); self.tree.heading("d", text="Campo de destino")
        self.tree.pack(fill="both", expand=True)

        edit = ttk.Frame(left); edit.pack(fill="x", pady=(8,0))
        ttk.Label(edit, text="Alterar destino:").pack(side="left")
        self.combo = ttk.Combobox(edit, state="readonly", width=28); self.combo.pack(side="left", padx=8)
        ttk.Button(edit, text="Aplicar", command=self.change_map).pack(side="left")

        self.logbox = tk.Text(right, state="disabled", wrap="word", font=("Consolas",10))
        self.logbox.pack(fill="both", expand=True)

        bottom = ttk.Frame(self, padding=16); bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=180)
        self.progress.pack(side="right")

    def _file_row(self, parent, row, label, var, cmd):
        ttk.Label(parent, text=label).grid(row=row,column=0,sticky="w",pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row,column=1,sticky="ew",padx=8,pady=5)
        ttk.Button(parent, text="Selecionar", command=cmd).grid(row=row,column=2,pady=5)

    def pick_csv(self):
        p = filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if p: self.source.set(p)

    def pick_json(self):
        p = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if p: self.schema.set(p)

    def log(self, msg):
        self.logbox.config(state="normal")
        self.logbox.insert("end", msg+"\n")
        self.logbox.see("end")
        self.logbox.config(state="disabled")

    def analyze(self):
        self.btn_ai.config(state="disabled"); self.btn_convert.config(state="disabled")
        self.progress.start(10); self.status.set("Analisando com a LLM...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            self.rows, self.fields = read_csv(self.source.get())
            self.dest_schema = read_destination_schema(self.schema.get())
            m = suggest_mapping(self.fields, self.dest_schema)
            self.raw_mapping = m
            self.mapping = validate_mapping(m, self.fields, self.dest_schema)
            if not self.mapping:
                raise RuntimeError(
                    "A LLM respondeu, mas não foi possível formar um mapeamento válido."
                )
            self.after(0, self._ok)
        except Exception as e:
            message = str(e)
            self.after(0, lambda msg=message: self._error(msg))

    def _ok(self):
        self.progress.stop(); self.btn_ai.config(state="normal"); self.btn_convert.config(state="normal")
        self.status.set("Mapeamento concluído.")
        for i in self.tree.get_children(): self.tree.delete(i)
        for src in self.fields:
            self.tree.insert("", "end", values=(src, self.mapping.get(src,"")))
        self.combo["values"] = list(self.dest_schema)
        self.log(f"Registros encontrados: {len(self.rows)}")
        self.log("A LLM local foi consultada com sucesso.")
        self.log("Mapeamento validado:")
        for src, dst in self.mapping.items():
            self.log(f"  {src} -> {dst}")

    def _error(self, msg):
        self.progress.stop(); self.btn_ai.config(state="normal")
        self.status.set("Erro na análise."); self.log("ERRO: "+msg)
        messagebox.showerror("Erro", msg)

    def change_map(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção","Selecione uma linha.")
            return
        dst = self.combo.get()
        if not dst:
            messagebox.showwarning("Atenção","Escolha um campo de destino.")
            return
        item = sel[0]; src = self.tree.item(item,"values")[0]
        self.mapping[src] = dst
        self.tree.item(item, values=(src,dst))
        self.log(f"Alterado: {src} -> {dst}")

    def convert(self):
        try:
            converted, errors = transform_rows(self.rows, self.mapping, self.dest_schema)
            out = BASE_DIR/"output"/"clientes_convertidos.json"
            rep = BASE_DIR/"output"/"relatorio_integracao.json"
            export_json(converted, out)
            export_report(len(self.rows), len(converted), errors, self.mapping, rep)
            self.status.set("Integração concluída.")
            self.log("=== RESULTADO ===")
            self.log(f"Total: {len(self.rows)}")
            self.log(f"Convertidos: {len(converted)}")
            self.log(f"Com erro: {len(errors)}")
            messagebox.showinfo("Concluído", f"Total: {len(self.rows)}\nConvertidos: {len(converted)}\nCom erro: {len(errors)}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def open_output(self):
        p = BASE_DIR/"output"; p.mkdir(exist_ok=True)
        os.startfile(p)

if __name__ == "__main__":
    App().mainloop()
