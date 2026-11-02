@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist nba.db (
  echo Falta nba.db. Créala primero con: python actualizar_datos.py
  goto error
)

echo [1/3] Instalando dependencias...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error

echo [2/3] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "NBA 2K Equipos Clasicos.spec" del "NBA 2K Equipos Clasicos.spec"

echo [3/3] Compilando...
python -m PyInstaller --onefile --windowed --noconfirm ^
  --name "NBA 2K Equipos Clasicos" ^
  --icon nba.ico ^
  --add-data "nba.db;." ^
  --add-data "schema.sql;." ^
  --add-data "nba.ico;." ^
  --exclude-module matplotlib --exclude-module sklearn --exclude-module scipy ^
  --exclude-module IPython --exclude-module pytest --exclude-module openpyxl ^
  nba_gui.py
if errorlevel 1 goto error

echo.
echo Listo: dist\NBA 2K Equipos Clasicos.exe
echo Los datos van dentro del .exe. Si pones un nba.db junto al .exe, se usa esa.
pause
exit /b 0

:error
echo.
echo Ha habido un error. Revisa los mensajes de arriba.
pause
exit /b 1
