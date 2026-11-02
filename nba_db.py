"""
nba_db.py
---------
Acceso a la base de datos SQLite (nba.db). El esquema está en schema.sql.

    python nba_db.py nba_data.csv.gz     -> crea nba.db a partir del CSV antiguo

El resto de módulos no tocan SQL directamente: usan estas funciones.
  * guardar(con, df)  -> mete temporadas nuevas (o las reemplaza)
  * leer(con)         -> DataFrame con todo, para los cálculos de nba_core
  * consulta(con, …)  -> las consultas de la pestaña "Consultas"
"""
import os
import sqlite3
import sys

import pandas as pd

ARCHIVO_BD = "nba.db"
ARCHIVO_ESQUEMA = "schema.sql"
ANIO_MODERNO = 1980          # desde 1980-81 se considera era Moderna

EQUIPOS = {
    "AND": "Anderson Packers", "ATL": "Atlanta Hawks", "BAL": "Baltimore Bullets",
    "BLB": "Baltimore Bullets", "BOS": "Boston Celtics", "BRK": "Brooklyn Nets",
    "BUF": "Buffalo Braves", "CHA": "Charlotte Bobcats", "CHH": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CHO": "Charlotte Hornets", "CHP": "Chicago Packers",
    "CHS": "Chicago Stags", "CHZ": "Chicago Zephyrs", "CIN": "Cincinnati Royals",
    "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "DNN": "Denver Nuggets", "FTW": "Fort Wayne Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "INA": "Indiana Pacers (ABA)",
    "IND": "Indiana Pacers", "INJ": "Indianapolis Jets", "INO": "Indianapolis Olympians",
    "KCK": "Kansas City Kings", "KCO": "Kansas City-Omaha Kings", "KEN": "Kentucky Colonels",
    "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "MLH": "Milwaukee Hawks", "MMS": "Memphis Sounds", "MNL": "Minneapolis Lakers",
    "MNM": "Minnesota Muskies", "NJN": "New Jersey Nets", "NOH": "New Orleans Hornets",
    "NOJ": "New Orleans Jazz", "NOK": "New Orleans/Oklahoma City Hornets",
    "NOP": "New Orleans Pelicans", "NYA": "New York Nets (ABA)", "NYK": "New York Knicks",
    "NYN": "New York Nets", "OAK": "Oakland Oaks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHO": "Phoenix Suns",
    "PHW": "Philadelphia Warriors", "POR": "Portland Trail Blazers",
    "PRO": "Providence Steamrollers", "ROC": "Rochester Royals", "SAA": "San Antonio Spurs (ABA)",
    "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "SDC": "San Diego Clippers",
    "SEA": "Seattle SuperSonics", "SFW": "San Francisco Warriors", "SHE": "Sheboygan Red Skins",
    "SSL": "Spirits of St. Louis", "STB": "St. Louis Bombers", "STL": "St. Louis Hawks",
    "SYR": "Syracuse Nationals", "TOR": "Toronto Raptors", "TRI": "Tri-Cities Blackhawks",
    "UTA": "Utah Jazz", "UTS": "Utah Stars", "VAN": "Vancouver Grizzlies",
    "VIR": "Virginia Squires", "WAS": "Washington Wizards", "WAT": "Waterloo Hawks",
    "WSA": "Washington Capitols (ABA)", "WSB": "Washington Bullets", "WSC": "Washington Capitols",
    "TOT": "Varios equipos",
}

# Columna de Basketball-Reference -> columna de la tabla `estadisticas`
_ESPECIALES = {"Age": "edad", "Pos": "posicion", "Lg": "liga", "TSP": "ts_pct",
               "3PAr": "fg3a_rate", "FTr": "ft_rate", "WS/48": "ws_48"}
_ESTADISTICAS = [
    "G", "GS", "MP", "FG", "FGA", "FG%", "3P", "3PA", "3P%", "2P", "2PA", "2P%", "eFG%",
    "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST", "STL", "BLK", "TOV", "PF", "PTS",
    "MP_tot", "FG_tot", "FGA_tot", "3P_tot", "3PA_tot", "2P_tot", "2PA_tot", "FT_tot",
    "FTA_tot", "ORB_tot", "DRB_tot", "TRB_tot", "AST_tot", "STL_tot", "BLK_tot", "TOV_tot",
    "PF_tot", "PTS_tot", "PER", "TSP", "3PAr", "FTr", "ORB%", "DRB%", "TRB%", "AST%",
    "STL%", "BLK%", "TOV%", "USG%", "OWS", "DWS", "WS", "WS/48", "OBPM", "DBPM", "BPM", "VORP",
]


def _col_sql(c):
    if c in _ESPECIALES:
        return _ESPECIALES[c]
    return c.replace("3P", "FG3").replace("2P", "FG2").replace("%", "_pct").lower()


COLUMNAS = {c: _col_sql(c) for c in ["Lg", "Age", "Pos"] + _ESTADISTICAS}


# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------
def ruta_recurso(nombre):
    """Ruta de un archivo junto al .exe (o junto al .py) o dentro del .exe."""
    candidatas = []
    if getattr(sys, "frozen", False):
        candidatas.append(os.path.dirname(sys.executable))       # junto al .exe
        candidatas.append(getattr(sys, "_MEIPASS", ""))           # empaquetado
    candidatas.append(os.path.dirname(os.path.abspath(__file__)))
    for carpeta in candidatas:
        p = os.path.join(carpeta, nombre)
        if os.path.exists(p):
            return p
    return os.path.join(candidatas[0], nombre)


def conectar(ruta=None, crear=False):
    """Abre nba.db. Con crear=True crea el archivo y las tablas si no existen."""
    ruta = ruta or ruta_recurso(ARCHIVO_BD)
    if not crear and not os.path.exists(ruta):
        raise FileNotFoundError(f"No existe la base de datos {ruta}. "
                                "Créala con actualizar_datos.py o nba_db.py.")
    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys = ON")
    if crear:
        with open(ruta_recurso(ARCHIVO_ESQUEMA), encoding="utf-8") as f:
            con.executescript(f.read())
    return con


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------
def _anio(season):
    return int(str(season)[:4])


def guardar(con, df):
    """Guarda las temporadas de `df` (columnas de Basketball-Reference: Name,
    Season, Tm, Lg, HOF, G, PTS…). Las temporadas que ya existían se reemplazan
    enteras. Todo va en una transacción: si algo falla no se guarda nada."""
    df = df.drop_duplicates(subset=["Name", "Season", "Tm"], keep="first")
    cols = [c for c in COLUMNAS if c in df.columns]
    temporadas = sorted(df["Season"].unique())

    with con:   # BEGIN … COMMIT (o ROLLBACK si hay una excepción)
        con.executemany(
            "INSERT OR IGNORE INTO equipos (codigo, nombre) VALUES (?, ?)",
            [(c, EQUIPOS.get(c, c)) for c in df["Tm"].unique()])
        con.executemany(
            "INSERT OR IGNORE INTO temporadas (temporada, anio, era) VALUES (?, ?, ?)",
            [(t, _anio(t), "Moderno" if _anio(t) >= ANIO_MODERNO else "Clásico")
             for t in temporadas])

        # Un jugador es Hall of Fame si lo es en cualquiera de sus filas
        hof = df.groupby("Name")["HOF"].max() if "HOF" in df.columns else {}
        con.executemany(
            """INSERT INTO jugadores (nombre, hof) VALUES (?, ?)
               ON CONFLICT (nombre) DO UPDATE SET hof = MAX(hof, excluded.hof)""",
            [(n, int(bool(hof.get(n, False)))) for n in df["Name"].unique()])
        ids = dict(con.execute("SELECT nombre, id FROM jugadores"))

        con.execute(f"DELETE FROM estadisticas WHERE temporada IN ({','.join('?' * len(temporadas))})",
                    temporadas)
        destino = ["jugador_id", "temporada", "equipo"] + [COLUMNAS[c] for c in cols]
        filas = df[cols].astype(object).where(df[cols].notna(), None)
        con.executemany(
            f"INSERT INTO estadisticas ({', '.join(destino)}) "
            f"VALUES ({', '.join('?' * len(destino))})",
            [(ids[n], s, t, *valores) for n, s, t, valores in
             zip(df["Name"], df["Season"], df["Tm"], filas.itertuples(index=False, name=None))])
    return len(df)


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------
def leer(con):
    """Todas las filas de v_estadisticas, con los nombres de columna originales."""
    df = pd.read_sql_query('SELECT * FROM v_estadisticas ORDER BY "Fila"', con)
    df["HOF"] = df["HOF"].astype(bool)
    return df.drop(columns="Fila")


def filas_por_temporada(con):
    """{'1957-58': 98, …} para saber qué temporadas están incompletas."""
    return dict(con.execute(
        "SELECT temporada, COUNT(*) FROM estadisticas GROUP BY temporada"))


# ---------------------------------------------------------------------------
# Consultas de la pestaña "Consultas" (:temporada es la temporada elegida)
# ---------------------------------------------------------------------------
CONSULTAS = {
    "Mejores jugadores de la temporada": """
-- Top 25 por MS en la temporada elegida (mínimo 40 partidos).
-- Si un jugador fue traspasado, solo cuenta su fila total (TOT).
SELECT "Name" AS Jugador, "Tm" AS Equipo, "Pos", "G" AS PJ,
       ROUND("PTS", 1) AS PTS, ROUND("TRB", 1) AS REB, ROUND("AST", 1) AS AST,
       ROUND("MS", 1) AS MS
FROM v_estadisticas v
WHERE "Season" = :temporada
  AND "G" >= 40
  AND ("Tm" = 'TOT' OR NOT EXISTS (
        SELECT 1 FROM v_estadisticas t
        WHERE t."Name" = v."Name" AND t."Season" = v."Season" AND t."Tm" = 'TOT'))
ORDER BY "MS" DESC
LIMIT 25;""",

    "Mejores temporadas de la historia": """
-- La mejor temporada de cada jugador (función de ventana ROW_NUMBER)
-- y, de ellas, las 25 con más MS.
WITH ranking AS (
    SELECT "Name", "Season", "Tm", "MS",
           ROW_NUMBER() OVER (PARTITION BY "Name" ORDER BY "MS" DESC) AS n
    FROM v_estadisticas
    WHERE "G" >= 40 AND "MS" IS NOT NULL
)
SELECT "Name" AS Jugador, "Season" AS Temporada, "Tm" AS Equipo, ROUND("MS", 1) AS MS
FROM ranking
WHERE n = 1
ORDER BY "MS" DESC
LIMIT 25;""",

    "Plantillas con más Hall of Fame": """
-- Equipos con más jugadores del Hall of Fame en una misma temporada.
SELECT e.temporada AS Temporada, q.nombre AS Equipo,
       SUM(j.hof) AS HOF, COUNT(*) AS Jugadores
FROM estadisticas e
JOIN jugadores j ON j.id = e.jugador_id
JOIN equipos   q ON q.codigo = e.equipo
WHERE e.equipo <> 'TOT'
GROUP BY e.temporada, e.equipo
HAVING SUM(j.hof) >= 4
ORDER BY HOF DESC, Temporada
LIMIT 25;""",

    "Evolución de la liga": """
-- Cómo ha cambiado el juego temporada a temporada: puntos cada 36 minutos
-- y porcentaje de los tiros que son triples (vacío antes de 1979-80).
SELECT e.temporada AS Temporada,
       COUNT(DISTINCT e.equipo) AS Equipos,
       COUNT(DISTINCT e.jugador_id) AS Jugadores,
       ROUND(SUM(CASE WHEN e.mp_tot IS NOT NULL THEN e.pts_tot END) * 36.0
             / SUM(e.mp_tot), 1) AS "PTS por 36 min",
       ROUND(100.0 * SUM(e.fg3a_tot) / SUM(e.fga_tot), 1) AS "% tiros de 3"
FROM estadisticas e
WHERE e.equipo <> 'TOT' AND e.liga = 'NBA'
GROUP BY e.temporada
ORDER BY e.temporada DESC;""",

    "Jugadores con más temporadas": """
-- Las carreras más largas (temporadas distintas jugadas).
SELECT j.nombre AS Jugador,
       COUNT(DISTINCT e.temporada) AS Temporadas,
       MIN(e.temporada) AS Primera, MAX(e.temporada) AS Ultima,
       CASE j.hof WHEN 1 THEN 'Sí' ELSE '' END AS HOF
FROM jugadores j
JOIN estadisticas e ON e.jugador_id = j.id
GROUP BY j.id
ORDER BY Temporadas DESC, Jugador
LIMIT 25;""",
}


def consulta(con, nombre, temporada=None):
    """Ejecuta una de CONSULTAS y devuelve un DataFrame."""
    return pd.read_sql_query(CONSULTAS[nombre], con, params={"temporada": temporada})


# ---------------------------------------------------------------------------
# Migración desde el CSV antiguo
# ---------------------------------------------------------------------------
def importar_csv(ruta_csv, ruta_bd=None):
    ruta_bd = ruta_bd or os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO_BD)
    df = pd.read_csv(ruta_csv)
    con = conectar(ruta_bd, crear=True)
    n = guardar(con, df)
    con.execute("VACUUM")
    con.close()
    return n


if __name__ == "__main__":
    origen = sys.argv[1] if len(sys.argv) > 1 else "nba_data.csv.gz"
    n = importar_csv(origen)
    print(f"OK -> {ARCHIVO_BD}: {n} filas importadas desde {origen}")
