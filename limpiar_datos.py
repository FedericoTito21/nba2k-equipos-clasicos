"""
limpiar_datos.py
----------------
Limpia NBAStats.xlsx (exportado de Basketball-Reference) y lo guarda en la
base de datos nba.db, que es la que usa la aplicación.

Solo hace falta ejecutarlo cuando se añadan temporadas nuevas al Excel:

    python limpiar_datos.py                 (lee NBAStats.xlsx)
    python limpiar_datos.py otro_excel.xlsx

Qué corrige:
  * Porcentajes con el decimal perdido (".497" guardado como 497). Se
    RECALCULAN a partir de los totales, que no están dañados.
  * Nombres con comas en lugar de puntos ("T,J, McConnell") y el "*" del
    Hall of Fame (se guarda aparte en la columna HOF).
  * Equipos "2TM"/"3TM"/"4TM" -> "TOT" (como en el resto de temporadas).
  * Filas duplicadas y columnas vacías.

Tus métricas (PPR, RPR, APR, SPR, BPR, FDS, MS, MG) ya no se guardan: las
calcula la vista v_estadisticas de schema.sql con las mismas fórmulas del Excel.
"""
import sys
import numpy as np
import pandas as pd

import nba_db

ENTRADA = sys.argv[1] if len(sys.argv) > 1 else "NBAStats.xlsx"


def div(a, b):
    """División segura: NaN si el denominador es 0 o falta."""
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    return (a / b.replace(0, np.nan)).astype(float)


def main():
    print(f"Leyendo {ENTRADA} ...")
    df = pd.read_excel(ENTRADA)

    # --- Columnas: las de totales venían como "PTS.1", "FG.1"... ----------
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")])
    df = df.rename(columns={c: c[:-2] + "_tot" for c in df.columns if str(c).endswith(".1")})

    # --- Nombres, equipos, posiciones ------------------------------------
    df["Name"] = df["Name"].astype(str)
    df["HOF"] = df["Name"].str.contains(r"\*", regex=True)
    df["Name"] = (df["Name"].str.replace("*", "", regex=False)
                            .str.replace(",", ".", regex=False)
                            .str.strip())
    df["Tm"] = df["Tm"].astype(str).str.strip().replace({"2TM": "TOT", "3TM": "TOT", "4TM": "TOT"})
    df["Pos"] = df["Pos"].fillna("").astype(str).str.replace(",", "-", regex=False).str.strip()
    df["Season"] = df["Season"].astype(str).str.strip()

    # --- Porcentajes recalculados desde los totales ----------------------
    fg, fga = df["FG_tot"], df["FGA_tot"]
    tp, tpa = df["3P_tot"], df["3PA_tot"]
    ft, fta = df["FT_tot"], df["FTA_tot"]
    pts = df["PTS_tot"]
    tp0 = tp.fillna(0)

    calculados = {
        "FG%": div(fg, fga),
        "3P%": div(tp, tpa),
        "2P%": div(fg - tp0, fga - tpa.fillna(0)),
        "eFG%": div(fg + 0.5 * tp0, fga),
        "FT%": div(ft, fta),
        "TSP": div(pts, 2 * (fga + 0.44 * fta)),
        "3PAr": div(tpa, fga),
        "FTr": div(fta, fga),
    }
    for col, nuevo in calculados.items():
        viejo = pd.to_numeric(df[col], errors="coerce")
        # Si no se puede recalcular (faltan totales), arreglamos el decimal perdido
        limite = 1.5 if col not in ("FTr", "WS/48") else 5
        viejo = viejo.where(viejo.abs() <= limite, viejo / 1000)
        df[col] = nuevo.where(nuevo.notna(), viejo).round(3)

    # WS/48 no se recalcula (en filas de traspasos el WS no cuadra con los
    # minutos); solo se recupera el decimal perdido: 123 -> 0.123
    ws48 = pd.to_numeric(df["WS/48"], errors="coerce")
    df["WS/48"] = ws48.where(ws48.abs() <= 2, ws48 / 1000).round(3)

    # 3P% sin intentos en épocas sin línea de 3 -> se queda vacío (NaN)
    # Columnas *_tot de porcentaje ya no se usan
    df = df.drop(columns=[c for c in df.columns if c.endswith("%_tot")])

    # --- Duplicados ------------------------------------------------------
    antes = len(df)
    df = df.drop_duplicates(subset=["Name", "Season", "Tm"], keep="first")
    print(f"Duplicados eliminados: {antes - len(df)}")

    # --- A la base de datos ---------------------------------------------
    con = nba_db.conectar(crear=True)
    nba_db.guardar(con, df)
    con.close()
    print(f"OK -> {nba_db.ARCHIVO_BD}: {len(df)} filas, {df['Season'].nunique()} temporadas "
          f"({df['Season'].min()} a {df['Season'].max()})")


if __name__ == "__main__":
    main()
