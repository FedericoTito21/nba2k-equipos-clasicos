"""
NBA 2K · Equipos Clásicos
-------------------------
Interfaz (Tkinter). Toda la lógica está en nba_core.py.

Pestaña "Equipo histórico": eliges temporada y equipo (p. ej. 1957-58 New York
Knicks) y te dice, para cada jugador, su MS y su equivalente actual para
recrearlo en NBA 2K.

Pestaña "Jugador": la comparación de siempre, jugador a jugador, más el rol.

Pestaña "Consultas": rankings y curiosidades sacados con SQL de nba.db.
"""
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd

import nba_core as core
import nba_db

APP_TITULO = "NBA 2K · Equipos Clásicos"
VERSION = "2.0"

# Paleta
FONDO = "#0f1115"
PANEL = "#171a21"
BORDE = "#262b36"
TEXTO = "#e8eaf0"
TEXTO_2 = "#9aa3b2"
ACENTO = "#f28c28"     # naranja balón
ACENTO_2 = "#3b82f6"
OK = "#22c55e"
AVISO = "#f59e0b"
FUENTE = "Segoe UI"


# ---------------------------------------------------------------------------
# Utilidades de interfaz
# ---------------------------------------------------------------------------
def estilo(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=FONDO)
    s.configure(".", background=FONDO, foreground=TEXTO, fieldbackground=PANEL,
                bordercolor=BORDE, font=(FUENTE, 10))
    s.configure("TFrame", background=FONDO)
    s.configure("Panel.TFrame", background=PANEL)
    s.configure("TLabel", background=FONDO, foreground=TEXTO)
    s.configure("Panel.TLabel", background=PANEL, foreground=TEXTO)
    s.configure("Sub.TLabel", background=FONDO, foreground=TEXTO_2)
    s.configure("PanelSub.TLabel", background=PANEL, foreground=TEXTO_2)
    s.configure("Titulo.TLabel", background=FONDO, foreground=TEXTO, font=(FUENTE, 18, "bold"))
    s.configure("Seccion.TLabel", background=PANEL, foreground=ACENTO, font=(FUENTE, 10, "bold"))
    s.configure("Info.TLabel", background=FONDO, foreground=TEXTO_2, font=(FUENTE, 9))
    s.configure("Grande.TLabel", background=PANEL, foreground=OK, font=(FUENTE, 12, "bold"))

    s.configure("TButton", background=PANEL, foreground=TEXTO, bordercolor=BORDE,
                focuscolor=PANEL, padding=(12, 6))
    s.map("TButton", background=[("active", BORDE)])
    s.configure("Accion.TButton", background=ACENTO, foreground="#111", bordercolor=ACENTO,
                font=(FUENTE, 10, "bold"))
    s.map("Accion.TButton", background=[("active", "#ffa64d")])

    s.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=TEXTO,
                arrowcolor=TEXTO, bordercolor=BORDE, padding=4)
    s.map("TCombobox", fieldbackground=[("readonly", PANEL)],
          foreground=[("readonly", TEXTO)], selectbackground=[("readonly", PANEL)],
          selectforeground=[("readonly", TEXTO)])
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", TEXTO)
    root.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
    root.option_add("*TCombobox*Listbox.selectForeground", "#111")

    s.configure("TRadiobutton", background=PANEL, foreground=TEXTO)
    s.map("TRadiobutton", background=[("active", PANEL)])

    s.configure("TNotebook", background=FONDO, borderwidth=0)
    s.configure("TNotebook.Tab", background=PANEL, foreground=TEXTO_2, padding=(18, 8),
                font=(FUENTE, 10, "bold"))
    s.map("TNotebook.Tab", background=[("selected", BORDE)],
          foreground=[("selected", ACENTO)])

    s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXTO,
                rowheight=26, bordercolor=BORDE)
    s.configure("Treeview.Heading", background=BORDE, foreground=TEXTO,
                font=(FUENTE, 9, "bold"), relief="flat")
    s.map("Treeview", background=[("selected", ACENTO_2)], foreground=[("selected", "#fff")])
    s.configure("Vertical.TScrollbar", background=PANEL, troughcolor=FONDO, arrowcolor=TEXTO)


def tabla(padre, columnas, anchos, alto=12):
    marco = ttk.Frame(padre, style="Panel.TFrame")
    tv = ttk.Treeview(marco, columns=columnas, show="headings", height=alto)
    for col, ancho in zip(columnas, anchos):
        tv.heading(col, text=col)
        tv.column(col, width=ancho, minwidth=40,
                  anchor="w" if ancho >= 140 else "center", stretch=ancho >= 140)
    sb = ttk.Scrollbar(marco, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tv.tag_configure("par", background="#1b1f27")
    tv.tag_configure("aviso", foreground=AVISO)
    tv.tag_configure("hof", foreground="#facc15")
    return marco, tv


def fmt(x, dec=0, sufijo=""):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:.{dec}f}{sufijo}"


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root, df, con):
        self.root = root
        self.df = df
        self.con = con
        self.temporadas = core.temporadas_disponibles(df)
        self.ultimo_equipo = None   # DataFrame del último equipo convertido

        root.title(APP_TITULO)
        root.geometry("1180x760")
        root.minsize(980, 620)
        estilo(root)

        # Cabecera
        cab = ttk.Frame(root)
        cab.pack(fill="x", padx=20, pady=(16, 6))
        ttk.Label(cab, text="🏀 " + APP_TITULO, style="Titulo.TLabel").pack(side="left")
        der = ttk.Frame(cab)
        der.pack(side="right")
        ttk.Label(der, text="Comparar con la temporada:", style="Sub.TLabel").pack(side="left", padx=(0, 6))
        self.cb_actual = ttk.Combobox(der, values=self.temporadas[::-1], width=10, state="readonly")
        self.cb_actual.set(self.temporadas[-1])
        self.cb_actual.pack(side="left")

        ttk.Label(root, style="Info.TLabel",
                  text="Encuentra el equivalente actual de cada jugador histórico para recrear "
                       "plantillas clásicas en NBA 2K. MS = valoración general.").pack(
            anchor="w", padx=22, pady=(0, 8))

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.nb = nb
        self.tab_equipo = ttk.Frame(nb)
        self.tab_jugador = ttk.Frame(nb)
        self.tab_consultas = ttk.Frame(nb)
        nb.add(self.tab_equipo, text="  Equipo histórico  ")
        nb.add(self.tab_jugador, text="  Jugador  ")
        nb.add(self.tab_consultas, text="  Consultas  ")

        self.construir_equipo()
        self.construir_jugador()

        self.estado = tk.StringVar(value=f"{len(df):,} temporadas de jugador cargadas "
                                         f"({self.temporadas[0]} a {self.temporadas[-1]}).".replace(",", "."))
        ttk.Label(root, textvariable=self.estado, style="Info.TLabel").pack(
            anchor="w", padx=22, pady=(0, 10))
        self.construir_consultas()

    # ------------------------------------------------------------------ Equipo
    def construir_equipo(self):
        t = self.tab_equipo
        barra = ttk.Frame(t, style="Panel.TFrame", padding=14)
        barra.pack(fill="x", pady=(10, 8))

        ttk.Label(barra, text="Temporada", style="PanelSub.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(barra, text="Equipo", style="PanelSub.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.cb_eq_temp = ttk.Combobox(barra, values=self.temporadas, width=10, state="readonly")
        self.cb_eq_temp.grid(row=1, column=0, sticky="w")
        self.cb_eq_equipo = ttk.Combobox(barra, width=34, state="readonly")
        self.cb_eq_equipo.grid(row=1, column=1, sticky="w", padx=(12, 0))
        ttk.Button(barra, text="Convertir equipo", style="Accion.TButton",
                   command=self.convertir_equipo).grid(row=1, column=2, padx=(14, 0))
        ttk.Button(barra, text="Exportar CSV", command=self.exportar).grid(row=1, column=3, padx=(8, 0))
        ttk.Button(barra, text="Copiar", command=self.copiar).grid(row=1, column=4, padx=(8, 0))

        self.cb_eq_temp.bind("<<ComboboxSelected>>", self.actualizar_equipos)
        if "1957-58" in self.temporadas:
            self.cb_eq_temp.set("1957-58")
            self.actualizar_equipos()
            self.seleccionar_equipo("NYK")

        self.lbl_equipo = ttk.Label(t, text="", style="Sub.TLabel")
        self.lbl_equipo.pack(anchor="w", pady=(0, 6))

        cols = ("Jugador", "Pos", "PJ", "Min", "MS", "Equivalente actual", "Equipo", "Similitud",
                "Alternativas", "Nota")
        anchos = (170, 45, 40, 50, 55, 165, 115, 75, 240, 140)
        marco, self.tv_equipo = tabla(t, cols, anchos, alto=14)
        marco.pack(fill="both", expand=True)
        self.tv_equipo.bind("<Double-1>", self.abrir_jugador_desde_equipo)
        ttk.Label(t, style="Info.TLabel",
                  text="Doble clic en un jugador para ver todos sus parecidos. "
                       "No se repiten equivalentes dentro del mismo equipo. ★ = Hall of Fame.").pack(
            anchor="w", pady=(6, 0))

    def actualizar_equipos(self, _evt=None):
        equipos = core.equipos_temporada(self.df, self.cb_eq_temp.get())
        self._equipos = equipos
        self.cb_eq_equipo["values"] = [f"{nombre} ({cod})" for cod, nombre in equipos]
        self.cb_eq_equipo.set("")

    def seleccionar_equipo(self, codigo):
        for i, (cod, _n) in enumerate(self._equipos):
            if cod == codigo:
                self.cb_eq_equipo.current(i)

    def convertir_equipo(self):
        temporada = self.cb_eq_temp.get()
        idx = self.cb_eq_equipo.current()
        if not temporada or idx < 0:
            messagebox.showinfo(APP_TITULO, "Elige una temporada y un equipo.")
            return
        codigo, nombre = self._equipos[idx]
        actual = self.cb_actual.get()
        self.estado.set(f"Calculando {nombre} {temporada}…")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            res = core.equipo_a_actual(self.df, codigo, temporada, actual)
        finally:
            self.root.config(cursor="")
        self.ultimo_equipo = res.assign(Temporada=temporada, EquipoHist=nombre, Comparado=actual)

        tv = self.tv_equipo
        tv.delete(*tv.get_children())
        for i, r in res.iterrows():
            tags = ["par"] if i % 2 else []
            if r["Nota"]:
                tags.append("aviso")
            nombre_j = ("★ " if r["HOF"] else "") + r["Jugador"]
            tv.insert("", "end", iid=r["Id"], tags=tags, values=(
                nombre_j, r["Pos"], fmt(r["G"]), fmt(r["MP"], 1), fmt(r["MS"], 1),
                r["Equivalente"] or "—", r["Equipo actual"] or "—", fmt(r["Similitud"], 0, " %"),
                r["Alternativas"], r["Nota"]))
        ms_medio = res.head(8)["MS"].mean()
        self.lbl_equipo.config(
            text=f"{nombre} {temporada}  ·  {len(res)} jugadores  ·  MS medio de los 8 con más minutos: "
                 f"{ms_medio:.1f}  ·  comparado con {actual}")
        self.estado.set(f"{nombre} {temporada} convertido.")

    def abrir_jugador_desde_equipo(self, _evt=None):
        sel = self.tv_equipo.selection()
        if not sel:
            return
        fila = self.df[self.df["Id"] == sel[0]].iloc[0]
        self.nb.select(self.tab_jugador)
        self.cb_jugador.set(fila["Name"])
        self.al_elegir_jugador()
        self.cb_temp.set(fila["Season"])
        self.al_elegir_temporada()
        self.cb_equipo.set(fila["Tm"])
        self.buscar()

    def exportar(self):
        if self.ultimo_equipo is None:
            messagebox.showinfo(APP_TITULO, "Primero convierte un equipo.")
            return
        r = self.ultimo_equipo
        sugerido = f"{r['EquipoHist'].iloc[0]} {r['Temporada'].iloc[0]}.csv".replace("/", "-")
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=sugerido,
                                            filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        cols = ["Jugador", "Pos", "G", "MP", "MS", "Equivalente", "Equipo actual", "Similitud",
                "Alternativas", "Nota"]
        salida = r[cols].copy()
        salida["MS"] = salida["MS"].round(1)
        salida["Similitud"] = salida["Similitud"].round(0)
        salida.to_csv(ruta, index=False, sep=";", encoding="utf-8-sig", decimal=",",
                      quoting=csv.QUOTE_MINIMAL)
        self.estado.set(f"Exportado a {ruta}")

    def copiar(self):
        if self.ultimo_equipo is None:
            messagebox.showinfo(APP_TITULO, "Primero convierte un equipo.")
            return
        r = self.ultimo_equipo
        lineas = [f"{r['EquipoHist'].iloc[0]} {r['Temporada'].iloc[0]} → NBA 2K "
                  f"(comparado con {r['Comparado'].iloc[0]})"]
        for _, f in r.iterrows():
            lineas.append(f"{f['Jugador']} ({f['Pos']}) · MS {f['MS']:.0f} → {f['Equivalente'] or '—'}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lineas))
        self.estado.set("Plantilla copiada al portapapeles.")

    # ----------------------------------------------------------------- Jugador
    def construir_jugador(self):
        t = self.tab_jugador
        self.jugadores = sorted(self.df["Name"].unique())

        barra = ttk.Frame(t, style="Panel.TFrame", padding=14)
        barra.pack(fill="x", pady=(10, 8))
        for i, txt in enumerate(["Jugador (escribe para buscar)", "Temporada", "Equipo", "Modo"]):
            ttk.Label(barra, text=txt, style="PanelSub.TLabel").grid(
                row=0, column=i, sticky="w", padx=(0 if i == 0 else 12, 0))
        self.cb_jugador = ttk.Combobox(barra, values=self.jugadores, width=30)
        self.cb_jugador.grid(row=1, column=0, sticky="w")
        self.cb_temp = ttk.Combobox(barra, width=10, state="readonly")
        self.cb_temp.grid(row=1, column=1, sticky="w", padx=(12, 0))
        self.cb_equipo = ttk.Combobox(barra, width=8, state="readonly")
        self.cb_equipo.grid(row=1, column=2, sticky="w", padx=(12, 0))

        self.modo = tk.StringVar(value="Auto")
        modos = ttk.Frame(barra, style="Panel.TFrame")
        modos.grid(row=1, column=3, sticky="w", padx=(12, 0))
        for m in ("Auto", "Clásico", "Moderno"):
            ttk.Radiobutton(modos, text=m, value=m, variable=self.modo).pack(side="left", padx=(0, 8))

        ttk.Button(barra, text="Buscar parecidos", style="Accion.TButton",
                   command=self.buscar).grid(row=1, column=4, padx=(10, 0))
        ttk.Button(barra, text="Rol", command=self.mostrar_rol).grid(row=1, column=5, padx=(8, 0))

        self.cb_jugador.bind("<KeyRelease>", self.filtrar_jugadores)
        self.cb_jugador.bind("<<ComboboxSelected>>", self.al_elegir_jugador)
        self.cb_jugador.bind("<Return>", self.al_elegir_jugador)
        self.cb_temp.bind("<<ComboboxSelected>>", self.al_elegir_temporada)

        info = ttk.Frame(t, style="Panel.TFrame", padding=(14, 10))
        info.pack(fill="x", pady=(0, 8))
        self.lbl_ms = ttk.Label(info, text="Elige un jugador histórico.", style="Grande.TLabel")
        self.lbl_ms.pack(anchor="w")
        self.lbl_info = ttk.Label(info, text="", style="PanelSub.TLabel", wraplength=1080)
        self.lbl_info.pack(anchor="w", pady=(4, 0))

        cuerpo = ttk.Frame(t)
        cuerpo.pack(fill="both", expand=True)
        cols = ("#", "Jugador", "Equipo", "Pos", "PJ", "MS", "Similitud", "Parecido en")
        anchos = (35, 180, 90, 50, 45, 55, 80, 200)
        marco, self.tv_jug = tabla(cuerpo, cols, anchos, alto=10)
        marco.pack(side="left", fill="both", expand=True)

        self.grafico = tk.Canvas(cuerpo, width=340, bg=PANEL, highlightthickness=0)
        self.grafico.pack(side="right", fill="y", padx=(10, 0))

    def filtrar_jugadores(self, evt):
        if evt.keysym in ("Up", "Down", "Return", "Escape"):
            return
        texto = self.cb_jugador.get().lower().strip()
        self.cb_jugador["values"] = ([n for n in self.jugadores if texto in n.lower()]
                                     if texto else self.jugadores)

    def al_elegir_jugador(self, _evt=None):
        nombre = self.cb_jugador.get().strip()
        filas = self.df[self.df["Name"] == nombre]
        self.cb_temp["values"] = sorted(filas["Season"].unique())
        self.cb_temp.set(filas["Season"].iloc[0] if len(filas) else "")
        self.al_elegir_temporada()

    def al_elegir_temporada(self, _evt=None):
        filas = self.df[(self.df["Name"] == self.cb_jugador.get().strip()) &
                        (self.df["Season"] == self.cb_temp.get())]
        equipos = filas["Tm"].tolist()
        equipos.sort(key=lambda e: e == "TOT")
        self.cb_equipo["values"] = equipos
        self.cb_equipo.set(equipos[0] if equipos else "")

    def id_actual(self):
        j, t, e = self.cb_jugador.get().strip(), self.cb_temp.get(), self.cb_equipo.get()
        if not (j and t and e):
            messagebox.showinfo(APP_TITULO, "Elige jugador, temporada y equipo.")
            return None
        return f"{j}{t}{e}"

    def buscar(self):
        pid = self.id_actual()
        if not pid:
            return
        modo = None if self.modo.get() == "Auto" else self.modo.get()
        actual = self.cb_actual.get()
        try:
            res, info = core.comparar(self.df, pid, actual, modo=modo)
        except ValueError as e:
            messagebox.showwarning(APP_TITULO, str(e))
            return
        j = info["jugador"]
        roles, _ = core.calcular_rol(self.df, pid)
        rol_txt = f"  ·  Rol: {' / '.join(roles)}" if roles else ""
        self.lbl_ms.config(text=f"{j['Name']} ({j['Season']}, {j['Tm']}, {j['Pos'] or '?'})  ·  "
                                f"MS {fmt(j['MS'], 1)}{rol_txt}")
        self.lbl_info.config(text=f"Modo {info['modo']} contra {actual}  ·  posiciones: "
                                  f"{', '.join(info['posiciones'])}  ·  PJ ≥ {core.MIN_G}, "
                                  f"MIN ≥ {core.MIN_MP}  ·  estadísticas usadas ({len(info['stats_usadas'])}): "
                                  f"{', '.join(info['stats_usadas'])}")
        tv = self.tv_jug
        tv.delete(*tv.get_children())
        for i, r in res.iterrows():
            tv.insert("", "end", tags=["par"] if i % 2 else [], values=(
                i + 1, r["Name"], r["Equipo"], r["Pos"], fmt(r["G"]), fmt(r["MS"], 1),
                fmt(r["Similitud"], 0, " %"), r["Parecido en"]))
        self.dibujar(res)
        self.estado.set(f"Comparación de {j['Name']} lista.")

    def mostrar_rol(self):
        pid = self.id_actual()
        if not pid:
            return
        try:
            roles, punt = core.calcular_rol(self.df, pid)
        except ValueError as e:
            messagebox.showwarning(APP_TITULO, str(e))
            return
        if not roles:
            messagebox.showinfo(APP_TITULO, "No hay estadísticas suficientes para calcular el rol.")
            return
        detalle = "\n".join(f"{r}: {v:+.2f}" for r, v in sorted(punt.items(), key=lambda x: -x[1]))
        messagebox.showinfo(APP_TITULO, f"Rol principal: {roles[0]}\n"
                                        f"Secundario: {roles[1] if len(roles) > 1 else '—'}\n\n"
                                        f"Puntuación (desviaciones respecto a su temporada):\n{detalle}")

    # --------------------------------------------------------------- Consultas
    def construir_consultas(self):
        t = self.tab_consultas
        barra = ttk.Frame(t, style="Panel.TFrame", padding=14)
        barra.pack(fill="x", pady=(10, 8))
        ttk.Label(barra, text="Consulta", style="PanelSub.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(barra, text="Temporada", style="PanelSub.TLabel").grid(
            row=0, column=1, sticky="w", padx=(12, 0))
        self.cb_consulta = ttk.Combobox(barra, values=list(nba_db.CONSULTAS), width=36,
                                        state="readonly")
        self.cb_consulta.current(0)
        self.cb_consulta.grid(row=1, column=0, sticky="w")
        self.cb_cons_temp = ttk.Combobox(barra, values=self.temporadas[::-1], width=10,
                                         state="readonly")
        self.cb_cons_temp.set(self.temporadas[-1])
        self.cb_cons_temp.grid(row=1, column=1, sticky="w", padx=(12, 0))
        ttk.Button(barra, text="Ejecutar", style="Accion.TButton",
                   command=self.ejecutar_consulta).grid(row=1, column=2, padx=(14, 0))
        self.cb_consulta.bind("<<ComboboxSelected>>", self.ejecutar_consulta)
        self.cb_cons_temp.bind("<<ComboboxSelected>>", self.ejecutar_consulta)

        cuerpo = ttk.Frame(t)
        cuerpo.pack(fill="both", expand=True)
        self.marco_consulta = ttk.Frame(cuerpo, style="Panel.TFrame")
        self.marco_consulta.pack(side="left", fill="both", expand=True)
        self.tv_consulta = None

        # El SQL que se ejecuta, para ver cómo está hecha cada consulta
        self.txt_sql = tk.Text(cuerpo, width=58, bg=PANEL, fg=TEXTO_2, relief="flat",
                               font=("Consolas", 9), wrap="word", padx=10, pady=10)
        self.txt_sql.pack(side="right", fill="y", padx=(10, 0))
        self.ejecutar_consulta()

    def ejecutar_consulta(self, _evt=None):
        nombre = self.cb_consulta.get()
        try:
            res = nba_db.consulta(self.con, nombre, self.cb_cons_temp.get())
        except Exception as e:      # error de SQL: se avisa en vez de cerrar la app
            messagebox.showwarning(APP_TITULO, f"Error en la consulta:\n\n{e}")
            return

        self.txt_sql.config(state="normal")
        self.txt_sql.delete("1.0", "end")
        self.txt_sql.insert("1.0", nba_db.CONSULTAS[nombre].strip())
        self.txt_sql.config(state="disabled")

        # Las columnas cambian en cada consulta: se rehace la tabla
        if self.tv_consulta is not None:
            self.tv_consulta.master.destroy()
        cols = list(res.columns)
        anchos = [170 if res[c].dtype == object and c != "Pos" else 80 for c in cols]
        marco, self.tv_consulta = tabla(self.marco_consulta, cols, anchos, alto=18)
        marco.pack(fill="both", expand=True)
        for i, fila in enumerate(res.itertuples(index=False)):
            self.tv_consulta.insert("", "end", tags=["par"] if i % 2 else [],
                                    values=["—" if pd.isna(v) else v for v in fila])
        self.estado.set(f"{nombre}: {len(res)} filas.")

    def dibujar(self, res):
        c = self.grafico
        c.delete("all")
        c.update_idletasks()
        ancho, alto = c.winfo_width() or 340, c.winfo_height() or 300
        c.create_text(14, 16, anchor="w", text="Similitud", fill=TEXTO, font=(FUENTE, 10, "bold"))
        if res.empty:
            return
        n = len(res)
        top, fila = 40, max(18, min(30, (alto - 50) // n))
        x0, x1 = 120, ancho - 44
        for i, r in res.iterrows():
            y = top + i * fila
            v = max(0.0, float(r["Similitud"]))
            nombre = r["Name"] if len(r["Name"]) <= 16 else r["Name"][:15] + "…"
            c.create_text(x0 - 8, y + fila / 2 - 2, anchor="e", text=nombre, fill=TEXTO_2,
                          font=(FUENTE, 9))
            c.create_rectangle(x0, y + 3, x1, y + fila - 7, fill=BORDE, width=0)
            c.create_rectangle(x0, y + 3, x0 + (x1 - x0) * v / 100, y + fila - 7,
                               fill=ACENTO if i == 0 else ACENTO_2, width=0)
            c.create_text(x1 + 6, y + fila / 2 - 2, anchor="w", text=f"{v:.0f}%", fill=TEXTO,
                          font=(FUENTE, 9))


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(core.ruta_recurso("nba.ico"))
    except tk.TclError:
        pass
    try:
        con = nba_db.conectar()
        df = core.cargar(con)
    except Exception as e:      # base de datos ausente o dañada
        root.withdraw()
        messagebox.showerror(APP_TITULO, "No se pudieron cargar los datos (nba.db).\n\n"
                                         f"Detalle: {e}")
        root.destroy()
        return
    App(root, df, con)
    root.mainloop()


if __name__ == "__main__":
    main()
