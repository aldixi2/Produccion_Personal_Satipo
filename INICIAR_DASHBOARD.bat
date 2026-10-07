@echo off
cd /d "%~dp0"
echo Iniciando Produccion del Personal de Salud - Red de Salud Satipo...
start "" http://localhost:8000/index.html
python -m http.server 8000
pause
