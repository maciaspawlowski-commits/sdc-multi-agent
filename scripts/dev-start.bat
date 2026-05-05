@echo off
REM Double-click wrapper for dev-start.ps1.
REM .bat files bypass the PowerShell execution policy, so this works
REM regardless of whether the user has run Set-ExecutionPolicy.
REM
REM The window stays open at the end so you can see the output and any errors.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-start.ps1"
echo.
echo Press any key to close this window.
pause >nul
