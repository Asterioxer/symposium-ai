@echo off
title Symposium AI

rem Ensure Ollama server is running in the background
powershell -Command "if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) { Start-Process 'ollama' -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 2 }"

python app.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
