"""
nba_core.py
-----------
Toda la lógica de cálculo, sin interfaz. La GUI solo llama a estas funciones.

Se mantienen tus fórmulas:
  * MS = FDS/4*2 + 70, con FDS = WS/82*100 + PER (se calcula en limpiar_datos.py)
  * Modo Clásico y Moderno con las mismas listas de estadísticas
  * Similitud = coseno entre los vectores estandarizados (z-score) respecto a
    los jugadores de la temporada de comparación (lo que hacía StandardScaler)

Correcciones respecto a la versión anterior:
  * Solo se usan las estadísticas que el jugador histórico TIENE (en 1958 no
    existían AST%, robos, tapones ni triples; antes se rellenaban con medias).
  * Posiciones simétricas y soporte para posiciones mixtas ("F-C", "G"...).
  * Un jugador traspasado aparece una sola vez (su fila TOT).
  * El rol se calcula con z-scores (antes casi todo salía "Anotador").
  * Sin scikit-learn: numpy hace lo mismo y el .exe pesa mucho menos.

Los datos se leen de la base de datos SQLite (nba_db.py). Las métricas MS,
FDS, MG… se calculan en SQL, en la vista v_estadisticas de schema.sql.
"""
import numpy as np
import pandas as pd

import nba_db
from nba_db import ANIO_MODERNO, ruta_recurso  # noqa: F401  (ruta_recurso la usa la GUI)

# ---------------------------------------------------------------------------
# Configuración (tus listas de siempre)
# ---------------------------------------------------------------------------
CLASSIC_STATS = ["FG%", "TSP", "FTr", "AST%", "OWS", "DWS", "WS", "WS/48", "PER"]
MODERN_STATS = [
    "3P%", "2P%", "eFG%", "FT%", "PER", "TSP", "3PAr", "FTr",
    "ORB%", "DRB%", "TRB%", "AST%", "STL%", "BLK%", "TOV%", "USG%",
    "OWS", "DWS", "WS", "WS/48", "OBPM", "DBPM", "BPM", "VORP",
]
MIN_G = 40                   # filtros de candidatos actuales
MIN_MP = 12
MIN_STATS = 4                # mínimo de estadísticas comunes para comparar

ROLES = {
    "Tirador": ["3P%", "3PAr", "eFG%"],
    "Asistente": ["AST%", "OBPM"],
    "Anotador": ["USG%", "PER"],
    "Reboteador": ["TRB%", "ORB%", "DRB%"],
    "Defensor": ["STL%", "BLK%", "DBPM", "DWS"],
}

# Posiciones vecinas: cada posición se compara con ella misma y las contiguas
VECINAS = {
    "PG": {"PG", "SG"},
    "SG": {"PG", "SG", "SF"},
    "SF": {"SG", "SF", "PF"},
    "PF": {"SF", "PF", "C"},
    "C": {"PF", "C"},
}
GENERICAS = {"G": ["PG", "SG"], "F": ["SF", "PF"]}


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
def anio(season):
    try:
        return int(str(season)[:4])
    except ValueError:
        return None


def cargar(con):
    """DataFrame con todas las temporadas de jugador (vista v_estadisticas)."""
    df = nba_db.leer(con)
    df["Pos"] = df["Pos"].fillna("").astype(str)
    return df


def modo_para(season):
    """Clásico antes de 1980-81, Moderno a partir de ahí."""
    a = anio(season)
    return "Moderno" if a is not None and a >= ANIO_MODERNO else "Clásico"


# ---------------------------------------------------------------------------
# Posiciones
# ---------------------------------------------------------------------------
def posiciones_comparables(pos):
    partes = [p.strip() for p in str(pos).replace(",", "-").split("-") if p.strip()]
    reales = set()
    for p in partes:
        reales.update(GENERICAS.get(p, [p]))
    comparables = set()
    for p in reales:
        comparables |= VECINAS.get(p, {p})
    return comparables or set(VECINAS)          # sin posición -> todas


def pos_coincide(pos_candidato, validas):
    partes = [p.strip() for p in str(pos_candidato).replace(",", "-").split("-") if p.strip()]
    reales = set()
    for p in partes:
        reales.update(GENERICAS.get(p, [p]))
    return bool(reales & validas)


# ---------------------------------------------------------------------------
# Candidatos de una temporada (sin duplicar a los traspasados)
# ---------------------------------------------------------------------------
def jugadores_temporada(df, season):
    s = df[df["Season"] == season]
    con_tot = set(s.loc[s["Tm"] == "TOT", "Name"])
    # Si un jugador tiene fila TOT, nos quedamos solo con esa
    return s[(s["Tm"] == "TOT") | (~s["Name"].isin(con_tot))]


def equipos_jugador_actual(df, nombre, season):
    """Para un traspasado (TOT) devuelve 'ATL/SAC', si no el propio equipo."""
    s = df[(df["Season"] == season) & (df["Name"] == nombre) & (df["Tm"] != "TOT")]
    return "/".join(s["Tm"].tolist())


# ---------------------------------------------------------------------------
# Comparación (tu método: z-score + similitud del coseno)
# ---------------------------------------------------------------------------
def comparar(df, player_id, season_actual, modo=None, top=10,
             min_g=MIN_G, min_mp=MIN_MP, filtrar_posicion=True):
    filas = df[df["Id"] == player_id]
    if filas.empty:
        raise ValueError(f"No se encontró el jugador: {player_id}")
    jugador = filas.iloc[0]

    modo = modo or modo_para(jugador["Season"])
    if modo == "Moderno" and (jugador["Anio"] or 0) < ANIO_MODERNO:
        raise ValueError("El modo Moderno solo está disponible desde 1980-81.")
    stats = CLASSIC_STATS if modo == "Clásico" else MODERN_STATS

    # Solo las estadísticas que el jugador histórico tiene de verdad
    usadas = [c for c in stats if c in df.columns and pd.notna(jugador[c])]
    if len(usadas) < MIN_STATS:
        raise ValueError("No hay suficientes estadísticas de este jugador para compararlo.")

    cand = jugadores_temporada(df, season_actual)
    cand = cand[(cand["G"] >= min_g) & (cand["MP"] >= min_mp) & (cand["Id"] != player_id)]
    validas = posiciones_comparables(jugador["Pos"])
    if filtrar_posicion and str(jugador["Pos"]).strip():
        cand = cand[cand["Pos"].map(lambda p: pos_coincide(p, validas))]
    if cand.empty:
        raise ValueError(f"No hay jugadores en {season_actual} con esos filtros.")

    X = cand[usadas].astype(float)
    X = X.fillna(X.mean())                       # huecos -> media de ESA temporada
    media = X.mean().values
    desv = X.std(ddof=0).replace(0, 1).values    # igual que StandardScaler
    Z = (X.values - media) / desv
    z_hist = (jugador[usadas].astype(float).values - media) / desv

    normas = np.linalg.norm(Z, axis=1) * np.linalg.norm(z_hist)
    sim = np.where(normas > 0, Z @ z_hist / np.where(normas > 0, normas, 1), 0)

    res = cand[["Id", "Name", "Season", "Tm", "Pos", "G", "MP", "MS"]].copy()
    res["Similitud"] = 100 * sim

    # "Por qué se parece": las 3 estadísticas más cercanas en z-score
    dif = np.abs(Z - z_hist)
    res["Parecido en"] = [", ".join(np.array(usadas)[np.argsort(d)[:3]]) for d in dif]

    res = res.sort_values("Similitud", ascending=False).head(top).reset_index(drop=True)
    res["Equipo"] = [equipos_jugador_actual(df, n, season_actual) if t == "TOT" else t
                     for n, t in zip(res["Name"], res["Tm"])]
    info = {"modo": modo, "stats_usadas": usadas, "posiciones": sorted(validas),
            "jugador": jugador}
    return res, info


# ---------------------------------------------------------------------------
# Rol (z-scores dentro de su temporada)
# ---------------------------------------------------------------------------
def calcular_rol(df, player_id, n=2):
    filas = df[df["Id"] == player_id]
    if filas.empty:
        raise ValueError(f"No se encontró el jugador: {player_id}")
    jugador = filas.iloc[0]
    temporada = df[(df["Season"] == jugador["Season"]) & (df["G"] >= 10)]
    if player_id not in set(temporada["Id"]):
        temporada = pd.concat([temporada, filas])

    puntuaciones = {}
    for rol, cols in ROLES.items():
        zs = []
        for c in cols:
            if c not in df.columns or pd.isna(jugador[c]):
                continue
            col = temporada[c].astype(float)
            sd = col.std()
            if sd and not np.isnan(sd):
                zs.append((float(jugador[c]) - col.mean()) / sd)
        if zs:
            puntuaciones[rol] = float(np.mean(zs))
    if not puntuaciones:
        return [], {}
    orden = sorted(puntuaciones, key=puntuaciones.get, reverse=True)
    return orden[:n], puntuaciones


# ---------------------------------------------------------------------------
# Equipos históricos (modo NBA 2K)
# ---------------------------------------------------------------------------
def temporadas_disponibles(df):
    return sorted(df["Season"].unique())


def equipos_temporada(df, season):
    s = df[(df["Season"] == season) & (df["Tm"] != "TOT")]
    return sorted(set(zip(s["Tm"], s["Equipo"])))


def plantilla(df, team, season):
    p = df[(df["Season"] == season) & (df["Tm"] == team)].copy()
    orden = "MP_tot" if "MP_tot" in p.columns and p["MP_tot"].notna().any() else "G"
    return p.sort_values([orden, "G"], ascending=False)


def equipo_a_actual(df, team, season, season_actual, por_jugador=3, min_g_hist=1):
    """Para cada jugador de la plantilla histórica, sus equivalentes actuales.

    Evita repetir: si dos históricos tienen el mismo mejor equivalente, al
    segundo se le asigna el siguiente libre (para poder crear la plantilla
    en 2K sin jugadores duplicados).
    """
    usados = set()
    filas = []
    for _, j in plantilla(df, team, season).iterrows():
        fila = {"Id": j["Id"], "Jugador": j["Name"], "Pos": j["Pos"], "G": j["G"],
                "MP": j["MP"], "MS": j["MS"], "HOF": bool(j.get("HOF", False)),
                "Equivalente": "", "Equipo actual": "", "Similitud": np.nan,
                "Alternativas": "", "Nota": ""}
        if j["G"] < min_g_hist:
            fila["Nota"] = "Muy pocos partidos"
        try:
            res, _ = comparar(df, j["Id"], season_actual, top=por_jugador + 10)
            libres = res[~res["Id"].isin(usados)]
            if not libres.empty:
                mejor = libres.iloc[0]
                usados.add(mejor["Id"])
                fila.update({"Equivalente": mejor["Name"], "Equipo actual": mejor["Equipo"],
                             "Similitud": mejor["Similitud"]})
                fila["Alternativas"] = ", ".join(libres["Name"].iloc[1:por_jugador])
        except ValueError as e:
            fila["Nota"] = str(e)
        if j["G"] < 10 and not fila["Nota"]:
            fila["Nota"] = "Pocos partidos"
        filas.append(fila)
    return pd.DataFrame(filas)
