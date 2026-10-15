$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python não encontrado. Instale Python 3.11 de 64 bits e tente novamente."
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install "pyinstaller>=6,<7"

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name PC-MAO `
    --collect-all mediapipe `
    --collect-all PySide6 `
    .\run_pc_mao.py

Write-Host "Build concluído: .\dist\PC-MAO\PC-MAO.exe"
Write-Host "Teste o aplicativo no computador de destino; a webcam e o PyAutoGUI dependem do ambiente local."
