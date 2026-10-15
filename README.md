# Controle do computador por gestos — Etapa 1 (MVP)

Protótipo local em Python para detectar uma mão na webcam, acompanhar os pontos de referência e reconhecer cinco poses geométricas distintas. O reconhecimento e a imagem ficam no computador: **nenhum vídeo é enviado ou gravado**.

## O que está implementado

- Webcam com visualização em tempo real e pontos da mão (MediaPipe).
- Cinco poses iniciais: polegar para cima (`Enter`), polegar para baixo (`Esc`), palma aberta (`Space`), punho fechado (`Ctrl+S`) e dois dedos (`Alt+Tab`).
- Confirmação por permanência, limiar de confiança, cooldown e rearme após estado neutro.
- Modo de teste é o padrão: mostra o comando, mas não envia teclas.
- Atalhos reais apenas com a opção explícita `--execute`; apenas ações permitidas em uma lista fixa.
- `Q`/`Esc` para sair e `P` para pausar/retomar.

**Não incluí C/V/X/Z nesta etapa:** o detector geométrico básico não identifica de forma confiável essas letras em todos os ângulos. O reconhecimento deve ser validado ou treinado antes de associar ações que alteram dados.

## Requisitos e instalação (Windows 10/11, Python 3.11 64-bit)

No PowerShell, dentro da pasta do projeto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se o Windows bloquear a ativação do ambiente, execute `Set-ExecutionPolicy -Scope Process Bypass` no PowerShell atual e tente ativar novamente.

## Executar

```powershell
python -m gesture_control.app
```

Teste primeiro o enquadramento e os nomes reconhecidos sem executar ações. Para ativar os atalhos reais:

```powershell
python -m gesture_control.app --execute
```

A opção `--execute` envia combinações ao sistema; use-a somente após conferir o modo de teste. Se houver mais de uma câmera, informe seu índice, por exemplo `--camera 1`. Pressione `Q` ou `Esc` na janela da câmera para interromper.

## Testes

```powershell
python -m pytest -q
```

Os testes cobrem classificação geométrica em landmarks sintéticos, allowlist e prevenção de repetição. A webcam não está disponível neste ambiente de desenvolvimento, portanto o funcionamento físico deverá ser validado no computador Windows com câmera.

## Estrutura

```text
gesture_control/
  app.py                 # captura, janela e ciclo de reconhecimento
  keyboard_controller.py # allowlist e execução opcional dos atalhos
  recognizer.py          # classificador geométrico conservador
  safety_manager.py      # confirmação, cooldown e rearme
 tests/
  test_core.py
requirements.txt
```

## Próximas entregas

1. Etapa 2: interface gráfica dedicada e status/histórico.
2. Etapa 3: configuração JSON e personalização de mapeamentos.
3. Etapa 4: controle de cursor e ações do mouse.
4. Etapa 5: calibração e ajustes adicionais de estabilidade/segurança.
5. Etapa 6: validação em Windows e empacotamento.

Cada etapa será entregue em commit Git separado. Para atualizar uma cópia clonada, use `git pull` após o remoto ser configurado. Para criar executável Windows, será preparada a especificação PyInstaller na etapa de distribuição.
