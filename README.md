# Controle do computador por gestos — protótipo

Aplicação local em Python para controlar o computador por poses e movimentos da mão capturados pela webcam. O processamento é local; as imagens não são enviadas nem gravadas.

## Recursos desta entrega

- Interface PySide6 dedicada, com vídeo da câmera, status e controles para iniciar, pausar e parar.
- Histórico local das ações reconhecidas, com botão para limpar.
- Modo de teste selecionado por padrão; marque **Executar ações reais no computador** para permitir atalhos e rolagem reais.
- Poses estáticas exigem estabilidade durante **1,5 segundo** antes da execução.
- Intervalo mínimo de **1,5 segundo** entre ações disparadas, inclusive deslizes.
- Sensibilidade dos deslizes ajustável na interface ou pela linha de comando.
- Webcam e MediaPipe rodam em uma thread de fundo para não congelar a janela.
- Ações disponíveis: poses básicas, rolagem por dois dedos apontados e navegação horizontal anterior/próxima no histórico do navegador.

Personalização de mapeamentos/perfis e controle de cursor, clique, arraste e calibração ainda não fazem parte desta etapa; serão desenvolvidos em entregas posteriores.

## Requisitos

- Windows 10 ou 11
- Python 3.11 de 64 bits
- Webcam integrada ou USB

## Instalação

No PowerShell, na pasta do repositório:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
