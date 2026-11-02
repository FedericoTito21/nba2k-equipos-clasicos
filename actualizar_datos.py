"""
actualizar_datos.py
-------------------
Descarga temporadas de Basketball-Reference y las guarda en la base de datos
nba.db (la crea si no existe). Las temporadas que ya estaban se reemplazan.

Uso (en tu PC, con Internet):

    pip install pandas lxml
    python actualizar_datos.py              -> rellena temporadas incompletas
                                               y añade las nuevas que existan
    python actualizar_datos.py 1970 2026    -> solo esas temporadas
                                               (1970 = 1969-70, 2026 = 2025-26)

Respeta el límite de Basketball-Reference (máx. 20 peticiones/minuto): espera
4 segundos entre descargas. Son 3 páginas por temporada.

Después de actualizar, vuelve a compilar el .exe para que lleve los datos nuevos
(o copia nba.db junto al .exe: si existe, se usa esa).
"""
import datetime
import io
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

import nba_db

ESPERA = 4.0                 # segundos entre peticiones
MIN_FILAS = 150              # por debajo de esto la temporada está incompleta
PRIMER_ANIO = 1947           # 1946-47 (BAA)

RENOMBRAR = {"Player": "Name", "Team": "Tm", "Tm": "Tm", "TS%": "TSP"}
POR_PARTIDO = ["MP", "FG", "FGA", "3P", "3PA", "2P", "2PA", "FT", "FTA", "ORB", "DRB",
               "TRB", "AST", "STL", "BLK", "TOV", "PF", "PTS"]
PORCENTAJES = ["FG%", "3P%", "2P%", "eFG%", "FT%"]
AVANZADAS = ["PER", "TSP", "3PAr", "FTr", "ORB%", "DRB%", "TRB%", "AST%", "STL%", "BLK%",
             "TOV%", "USG%", "OWS", "DWS", "WS", "WS/48", "OBPM", "DBPM", "BPM", "VORP"]


def etiqueta(anio_fin):
    return f"{anio_fin - 1}-{str(anio_fin)[-2:]}"


def liga(anio_fin):
    return "BAA" if anio_fin <= 1949 else "NBA"


def descargar_tabla(anio_fin, tipo):
    url = f"https://www.basketball-reference.com/leagues/{liga(anio_fin)}_{anio_fin}_{tipo}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (NBA2K Equipos Clasicos)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 429:
            print("   Basketball-Reference pide esperar (429). Pausa de 60 s…")
            time.sleep(60)
            return descargar_tabla(anio_fin, tipo)
        raise
    finally:
        time.sleep(ESPERA)
    # Algunas tablas vienen dentro de comentarios HTML
    html = html.replace("<!--", "").replace("-->", "")
    tablas = [t for t in pd.read_html(io.StringIO(html)) if "Player" in map(str, t.columns)]
    if not tablas:
        return None
    t = max(tablas, key=len)
    if isinstance(t.columns, pd.MultiIndex):
        t.columns = t.columns.get_level_values(-1)
    t = t.loc[:, ~t.columns.astype(str).str.startswith("Unnamed")]
    t = t[t["Player"].astype(str).ne("Player")]                 # cabeceras repetidas
    t = t[~t["Player"].astype(str).str.contains("League Average", na=False)]
    return t.rename(columns=RENOMBRAR)


def temporada(anio_fin):
    print(f"-> {etiqueta(anio_fin)}")
    pg = descargar_tabla(anio_fin, "per_game")
    if pg is None:
        print("   no existe en Basketball-Reference (todavía).")
        return None
    tot = descargar_tabla(anio_fin, "totals")
    adv = descargar_tabla(anio_fin, "advanced")

    clave = ["Name", "Tm"]
    for t in (pg, tot, adv):
        t["Name"] = (t["Name"].astype(str).str.replace("*", "", regex=False).str.strip())
        t["Tm"] = t["Tm"].astype(str).replace({"2TM": "TOT", "3TM": "TOT", "4TM": "TOT", "5TM": "TOT"})
        t.drop_duplicates(subset=clave, inplace=True)

    base = pg[["Name", "Age", "Tm", "Pos", "G", "GS"] +
              [c for c in POR_PARTIDO + PORCENTAJES if c in pg.columns]].copy()
    tot_cols = [c for c in POR_PARTIDO if c in tot.columns]
    tot = tot[clave + tot_cols].rename(columns={c: f"{c}_tot" for c in tot_cols})
    adv = adv[clave + [c for c in AVANZADAS if c in adv.columns]]

    df = base.merge(tot, on=clave, how="left").merge(adv, on=clave, how="left")
    for c in df.columns:
        if c not in ("Name", "Tm", "Pos"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Season"] = etiqueta(anio_fin)
    df["Lg"] = liga(anio_fin)
    df["Pos"] = df["Pos"].fillna("").astype(str)
    df["HOF"] = False
    print(f"   {len(df)} jugadores")
    return df


def main():
    con = nba_db.conectar(crear=True)
    if len(sys.argv) > 1:
        anios = [int(a) for a in sys.argv[1:]]
    else:
        filas = nba_db.filas_por_temporada(con)
        hoy = datetime.date.today()
        ultimo = hoy.year + (1 if hoy.month >= 10 else 0)    # la temporada empieza en octubre
        anios = [a for a in range(PRIMER_ANIO, ultimo + 1)
                 if filas.get(etiqueta(a), 0) < MIN_FILAS]
        print("Temporadas a descargar:", ", ".join(etiqueta(a) for a in anios) or "ninguna")

    nuevas = []
    for a in anios:
        try:
            t = temporada(a)
        except Exception as e:                       # una temporada fallida no para el resto
            print(f"   ERROR en {etiqueta(a)}: {e}")
            continue
        if t is not None and len(t):
            nuevas.append(t)

    if not nuevas:
        print("Nada que actualizar.")
        return

    # La marca de Hall of Fame que ya había se conserva (nba_db.guardar no la
    # borra nunca, solo la añade)
    nuevas = pd.concat(nuevas, ignore_index=True)
    n = nba_db.guardar(con, nuevas)
    total = sum(nba_db.filas_por_temporada(con).values())
    con.close()
    print(f"OK -> {nba_db.ARCHIVO_BD}: {n} filas nuevas ({total} en total). "
          f"Temporadas actualizadas: {', '.join(sorted(set(nuevas['Season'])))}")


if __name__ == "__main__":
    main()
