-- ===========================================================================
-- schema.sql · Base de datos de NBA 2K Equipos Clásicos (SQLite)
-- ===========================================================================
-- Modelo relacional:
--
--   equipos (1) ───< estadisticas >─── (1) jugadores
--                         │
--                         └──── (1) temporadas
--
-- Cada fila de `estadisticas` es la temporada de un jugador en un equipo.
-- Un jugador traspasado tiene una fila por equipo y otra con el total (equipo 'TOT').
-- Las métricas propias (PPR, FDS, MS, MG…) no se guardan: se calculan en la
-- vista `v_estadisticas`, así nunca se desincronizan de los datos.
-- ===========================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS equipos (
    codigo  TEXT PRIMARY KEY,               -- 'NYK', 'LAL', 'TOT'…
    nombre  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jugadores (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE,
    hof     INTEGER NOT NULL DEFAULT 0 CHECK (hof IN (0, 1))   -- Hall of Fame
);

CREATE TABLE IF NOT EXISTS temporadas (
    temporada  TEXT PRIMARY KEY,            -- '1957-58'
    anio       INTEGER NOT NULL,            -- 1957 (año en que empieza)
    era        TEXT NOT NULL CHECK (era IN ('Clásico', 'Moderno'))
);

CREATE TABLE IF NOT EXISTS estadisticas (
    id          INTEGER PRIMARY KEY,
    jugador_id  INTEGER NOT NULL REFERENCES jugadores (id),
    temporada   TEXT    NOT NULL REFERENCES temporadas (temporada),
    equipo      TEXT    NOT NULL REFERENCES equipos (codigo),
    liga        TEXT,                       -- 'NBA', 'BAA' o 'ABA'
    edad        INTEGER,
    posicion    TEXT,

    -- Por partido
    g REAL, gs REAL, mp REAL,
    fg REAL, fga REAL, fg_pct REAL,
    fg3 REAL, fg3a REAL, fg3_pct REAL,
    fg2 REAL, fg2a REAL, fg2_pct REAL,
    efg_pct REAL,
    ft REAL, fta REAL, ft_pct REAL,
    orb REAL, drb REAL, trb REAL,
    ast REAL, stl REAL, blk REAL, tov REAL, pf REAL, pts REAL,

    -- Totales de la temporada
    mp_tot INTEGER, fg_tot INTEGER, fga_tot INTEGER,
    fg3_tot INTEGER, fg3a_tot INTEGER, fg2_tot INTEGER, fg2a_tot INTEGER,
    ft_tot INTEGER, fta_tot INTEGER,
    orb_tot INTEGER, drb_tot INTEGER, trb_tot INTEGER,
    ast_tot INTEGER, stl_tot INTEGER, blk_tot INTEGER, tov_tot INTEGER,
    pf_tot INTEGER, pts_tot INTEGER,

    -- Avanzadas
    per REAL, ts_pct REAL, fg3a_rate REAL, ft_rate REAL,
    orb_pct REAL, drb_pct REAL, trb_pct REAL,
    ast_pct REAL, stl_pct REAL, blk_pct REAL, tov_pct REAL, usg_pct REAL,
    ows REAL, dws REAL, ws REAL, ws_48 REAL,
    obpm REAL, dbpm REAL, bpm REAL, vorp REAL,

    UNIQUE (jugador_id, temporada, equipo)
);

-- Índices para las búsquedas habituales: plantilla de un equipo en una
-- temporada y todas las temporadas de un jugador.
CREATE INDEX IF NOT EXISTS ix_estadisticas_temporada_equipo ON estadisticas (temporada, equipo);
CREATE INDEX IF NOT EXISTS ix_estadisticas_jugador ON estadisticas (jugador_id);


-- ---------------------------------------------------------------------------
-- Vista con todo unido y las métricas calculadas.
-- Los alias usan los nombres de columna de Basketball-Reference ("FG%",
-- "WS/48"…), que son los que usa la aplicación (nba_core.py).
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_estadisticas;
CREATE VIEW v_estadisticas AS
SELECT
    e.id           AS "Fila",               -- orden de inserción (equipos de un traspasado en orden)
    j.nombre || e.temporada || e.equipo  AS "Id",
    j.nombre       AS "Name",
    e.temporada    AS "Season",
    t.anio         AS "Anio",
    t.era          AS "Era",
    e.edad         AS "Age",
    e.equipo       AS "Tm",
    q.nombre       AS "Equipo",
    e.liga         AS "Lg",
    COALESCE(e.posicion, '') AS "Pos",
    j.hof          AS "HOF",

    -- Métricas propias (las mismas fórmulas que el Excel original)
    e.pts_tot / 82.0                          AS "PPR",
    e.trb_tot / 82.0                          AS "RPR",
    e.ast_tot / 82.0                          AS "APR",
    e.stl_tot / 82.0                          AS "SPR",
    e.blk_tot / 82.0                          AS "BPR",
    e.ws / 82.0 * 100 + e.per                 AS "FDS",
    (e.ws / 82.0 * 100 + e.per) / 4 * 2 + 70  AS "MS",
    ((e.ws / e.g * 100 + e.per) / 4 * 2) + 70 AS "MG",

    e.g AS "G", e.gs AS "GS", e.mp AS "MP",
    e.fg AS "FG", e.fga AS "FGA", e.fg_pct AS "FG%",
    e.fg3 AS "3P", e.fg3a AS "3PA", e.fg3_pct AS "3P%",
    e.fg2 AS "2P", e.fg2a AS "2PA", e.fg2_pct AS "2P%",
    e.efg_pct AS "eFG%",
    e.ft AS "FT", e.fta AS "FTA", e.ft_pct AS "FT%",
    e.orb AS "ORB", e.drb AS "DRB", e.trb AS "TRB",
    e.ast AS "AST", e.stl AS "STL", e.blk AS "BLK", e.tov AS "TOV", e.pf AS "PF", e.pts AS "PTS",

    e.mp_tot AS "MP_tot", e.fg_tot AS "FG_tot", e.fga_tot AS "FGA_tot",
    e.fg3_tot AS "3P_tot", e.fg3a_tot AS "3PA_tot", e.fg2_tot AS "2P_tot", e.fg2a_tot AS "2PA_tot",
    e.ft_tot AS "FT_tot", e.fta_tot AS "FTA_tot",
    e.orb_tot AS "ORB_tot", e.drb_tot AS "DRB_tot", e.trb_tot AS "TRB_tot",
    e.ast_tot AS "AST_tot", e.stl_tot AS "STL_tot", e.blk_tot AS "BLK_tot", e.tov_tot AS "TOV_tot",
    e.pf_tot AS "PF_tot", e.pts_tot AS "PTS_tot",

    e.per AS "PER", e.ts_pct AS "TSP", e.fg3a_rate AS "3PAr", e.ft_rate AS "FTr",
    e.orb_pct AS "ORB%", e.drb_pct AS "DRB%", e.trb_pct AS "TRB%",
    e.ast_pct AS "AST%", e.stl_pct AS "STL%", e.blk_pct AS "BLK%", e.tov_pct AS "TOV%",
    e.usg_pct AS "USG%",
    e.ows AS "OWS", e.dws AS "DWS", e.ws AS "WS", e.ws_48 AS "WS/48",
    e.obpm AS "OBPM", e.dbpm AS "DBPM", e.bpm AS "BPM", e.vorp AS "VORP"
FROM estadisticas e
JOIN jugadores  j ON j.id = e.jugador_id
JOIN temporadas t ON t.temporada = e.temporada
JOIN equipos    q ON q.codigo = e.equipo;
