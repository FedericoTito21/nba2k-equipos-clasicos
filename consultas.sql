-- ===========================================================================
-- consultas.sql · Prácticas de SQL sobre nba.db
-- ===========================================================================
-- Ábrelo con DB Browser for SQLite (https://sqlitebrowser.org) o con la
-- extensión "SQLite" de VS Code, conectado a nba.db.
--
-- Tablas:  equipos (codigo, nombre)
--          jugadores (id, nombre, hof)
--          temporadas (temporada, anio, era)
--          estadisticas (jugador_id, temporada, equipo, g, pts, trb, ast, ws, per…)
-- Vista:   v_estadisticas (todo unido + MS; columnas con comillas: "Name", "MS"…)
--
-- Ojo: un jugador traspasado tiene una fila por equipo y otra con equipo = 'TOT'.
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- EJEMPLO RESUELTO · Plantilla de los New York Knicks de 1957-58
-- ---------------------------------------------------------------------------
SELECT j.nombre, e.posicion, e.g AS partidos, e.pts AS puntos
FROM estadisticas e
JOIN jugadores j ON j.id = e.jugador_id
WHERE e.temporada = '1957-58'
  AND e.equipo = 'NYK'
ORDER BY e.pts DESC;


-- ---------------------------------------------------------------------------
-- EJERCICIO 1 · SELECT + WHERE + ORDER BY
-- Los 10 jugadores con más puntos por partido (pts) en la temporada 2024-25.
-- Pista: necesitas unir estadisticas con jugadores.
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 2 · COUNT
-- ¿Cuántos jugadores hay en la base de datos marcados como Hall of Fame?
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 3 · GROUP BY
-- Número de jugadores distintos que han jugado en cada equipo (en toda la
-- historia), de más a menos. No cuentes las filas 'TOT'.
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 4 · GROUP BY + HAVING
-- Jugadores que han jugado en 8 o más equipos distintos.
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 5 · Funciones de agregado
-- Para Michael Jordan: temporadas jugadas, media de puntos por partido de
-- su carrera (AVG) y su mejor temporada en puntos (MAX).
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 6 · JOIN con tres tablas
-- Todos los equipos (con su nombre completo) en los que jugó Kareem
-- Abdul-Jabbar, sin repetir.
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 7 · Subconsulta
-- Jugadores de la temporada 2024-25 que anotaron más puntos por partido que
-- la media de esa temporada (calcula la media con una subconsulta).
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 8 · Usar la vista
-- Con v_estadisticas: el jugador con más MS de cada era (Clásico y Moderno).
-- Pista: se puede hacer con GROUP BY "Era" y MAX("MS"), o con ROW_NUMBER().
-- ---------------------------------------------------------------------------



-- ---------------------------------------------------------------------------
-- EJERCICIO 9 · INSERT / UPDATE / DELETE (hazlo sobre una COPIA de nba.db)
-- a) Inserta un equipo inventado ('BCN', 'Barcelona Dragons').
-- b) Cambia su nombre a 'Barcelona Royals'.
-- c) Bórralo.
-- ¿Qué pasaría si intentas borrar el equipo 'NYK'? ¿Por qué?
-- ---------------------------------------------------------------------------

