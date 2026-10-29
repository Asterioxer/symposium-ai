# Launch script for Symposium AI

# Ensure Ollama is running
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

python app.py
