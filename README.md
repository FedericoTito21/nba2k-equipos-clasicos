# NBA 2K · Equipos Clásicos

Aplicación de escritorio que encuentra el **equivalente actual de cada jugador histórico** de la NBA para recrear plantillas clásicas en NBA 2K (por ejemplo, los New York Knicks de 1957-58).

Trabaja sobre una **base de datos SQLite** con más de 22.000 temporadas de jugador, desde 1948-49 hasta la actualidad, y compara a los jugadores con **estadística** (z-scores y similitud del coseno).

## Qué hace

- **Equipo histórico**: eliges una temporada y un equipo, y para cada jugador te da su valoración (MS), su equivalente actual, alternativas y el porcentaje de parecido. No repite equivalentes dentro de un mismo equipo. Se puede exportar a CSV.
- **Jugador**: compara un jugador concreto con los de la temporada que elijas, te dice en qué estadísticas se parece más y calcula su rol (tirador, anotador, defensor…).
- **Consultas**: rankings sacados con SQL (mejores temporadas de la historia, plantillas con más Hall of Fame, evolución del triple…), mostrando al lado el SQL que se ejecuta.

## Base de datos

Modelo relacional normalizado ([`schema.sql`](schema.sql)):

```
equipos (codigo PK, nombre)
jugadores (id PK, nombre UNIQUE, hof)
temporadas (temporada PK, anio, era)
estadisticas (id PK, jugador_id FK, temporada FK, equipo FK, g, pts, trb, ast, per, ws, …)
```

- **Claves foráneas e índices**: el índice `(temporada, equipo)` hace que sacar una plantilla sea inmediato.
- **Vista `v_estadisticas`**: une las cuatro tablas y **calcula en SQL las métricas propias** (MS, FDS, MG, PPR…), así nunca se desincronizan de los datos.
- **Escritura en una transacción** (`nba_db.guardar`): al actualizar una temporada se borra y se vuelve a insertar entera. Si algo falla, no se guarda nada.
- **Consultas** con `JOIN`, `GROUP BY` / `HAVING`, subconsultas `NOT EXISTS`, CTE (`WITH`) y funciones de ventana (`ROW_NUMBER() OVER (PARTITION BY …)`).
- [`consultas.sql`](consultas.sql): ejercicios de práctica de SQL sobre esta misma base de datos.

## Cómo compara a los jugadores

1. Elige las estadísticas según la era: **Clásico** (antes de 1980-81: FG%, TS%, WS, PER…) o **Moderno** (24 estadísticas avanzadas). Solo usa las que el jugador histórico tiene de verdad, porque en 1958 no se contaban ni robos ni tapones.
2. Filtra los candidatos de la temporada actual por posición (y las contiguas), partidos y minutos.
3. Estandariza cada estadística con **z-score** respecto a esa temporada, para que un 0,500 en tiro de 1958 se compare con lo normal en 1958 y no con lo de hoy.
4. Ordena por **similitud del coseno** entre los vectores, calculada con NumPy.

## Tecnologías

Python · **SQLite / SQL** · pandas · NumPy · Tkinter · PyInstaller

## Estructura

| Archivo | Qué hace |
| --- | --- |
| `schema.sql` | Tablas, claves, índices y la vista con las métricas |
| `nba_db.py` | Acceso a la base de datos: crear, guardar, leer y consultas |
| `nba_core.py` | Lógica: comparación, rol y conversión de equipos |
| `nba_gui.py` | Interfaz de escritorio (Tkinter) |
| `actualizar_datos.py` | Descarga temporadas de Basketball-Reference y las guarda en la base de datos |
| `limpiar_datos.py` | Importa y limpia el Excel original (`NBAStats.xlsx`) |
| `consultas.sql` | Ejercicios de SQL |
| `compilar.bat` | Genera el `.exe` con los datos dentro |

## Ejecutar

Los datos no van en el repositorio (vienen de [Basketball-Reference](https://www.basketball-reference.com)), así que primero se crea la base de datos:

```bash
pip install -r requirements.txt
python actualizar_datos.py      # crea nba.db y descarga todas las temporadas (~15 min)
python nba_gui.py
```

- Para actualizar solo una temporada: `python actualizar_datos.py 2026` (2026 = 2025-26).
- Para crear el `.exe`, que lleva los datos dentro y no necesita Python: `compilar.bat`.

## Fórmulas (las del Excel original)

- PPR, RPR, APR, SPR, BPR = totales / 82
- FDS = WS / 82 × 100 + PER
- **MS = FDS / 4 × 2 + 70** (valoración general)
- MG = ((WS / G × 100 + PER) / 4 × 2) + 70

## Autor

Federico Mathias
