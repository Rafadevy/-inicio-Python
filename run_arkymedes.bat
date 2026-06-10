@echo off
REM Arkymedes — Calculadora Inteligente Offline
REM Iniciar a aplicacao

cd /d "%~dp0"
.venv\Scripts\python.exe arkymedes_gui.py
pause
pyinstaller --onefile --windowed arkymedes_gui.py