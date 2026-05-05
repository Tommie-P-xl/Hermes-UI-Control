@echo off
:: hermes.bat - All-in-one Hermes Web UI control
:: Usage: hermes [start|stop|restart|status|open|close]
if "%~1"=="" (
    powershell -ExecutionPolicy Bypass -File "%~dp0hermes.ps1" browser
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0hermes.ps1" %*
)
