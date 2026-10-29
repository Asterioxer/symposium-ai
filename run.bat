@echo off
title Symposium AI
python app.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
