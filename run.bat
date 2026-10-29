@echo off
title Symposium AI - Real-Time Voice Intelligence
echo Starting Symposium AI...
python app.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
