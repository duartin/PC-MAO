# Controle do computador por gestos — protótipo

Aplicação local em Python para controlar o computador por poses e movimentos da mão capturados pela webcam. O processamento é local; as imagens não são enviadas nem gravadas.

Para salvar alterações no GitHub, copie os arquivos atualizados para a pasta clonada `PC-MAO` que contém `.git`; o ZIP de distribuição não inclui o histórico Git. Veja [`GIT_COMANDOS.md`](GIT_COMANDOS.md) para os comandos PowerShell.

## Recursos desta versão

- Interface PySide6 com vídeo, status, modo ativo, histórico e controles da câmera.
- **Modo Mouse** ativo por padrão: cursor pelo indicador, rolagem vertical sustentada por dois dedos e zoom por pinça.
- **Modo Atalhos** separado: `Enter`, `Esc` e navegação horizontal no histórico do navegador.
- Movimento do cursor contínuo e suavizado; não espera 1,5 s para começar.
- Poses estáticas estabilizam por **0,25 s**. A rolagem também começa após 0,25 s e continua a cada 0,18 s enquanto a pose for mantida.
- **1,5 s é o intervalo entre ações pontuais** (por exemplo, um atalho e o próximo), não um atraso inicial para mover o cursor ou iniciar a rolagem. Cursor, rolagem sustentada e zoom contínuo têm cadências próprias.
- Modo de teste por padrão. Marque **Executar ações reais no computador** para permitir cursor, atalhos, rolagem e zoom reais.
- Vídeo e reconhecimento executados em thread de fundo; imagens não são armazenadas.

Clique, clique duplo e arraste ainda não foram adicionados. A pinça está reservada ao zoom.

`config.example.json` é um exemplo de mapeamentos e parâmetros; esta versão ainda não carrega esse arquivo automaticamente.

## Requisitos

- Windows 10 ou 11
- Python 3.11 de 64 bits
- Webcam integrada ou USB

## Instalação

No PowerShell, dentro da pasta clonada do repositório:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

O `requirements.txt` instala MediaPipe, NumPy, PyAutoGUI, PySide6 e pytest. Se a ativação do ambiente for bloqueada, execute `Set-ExecutionPolicy -Scope Process Bypass` no PowerShell atual e ative novamente.

## Executar

```powershell
python -m pytest -q
python -m gesture_control.app
```

A janela começa em modo de teste. O movimento e as ações são simulados até marcar **Executar ações reais no computador**.

Parâmetros opcionais:

```powershell
# Usar outra câmera
python -m gesture_control.app --camera 1

# Ajustar a sensibilidade dos deslizes horizontais (0.5 a 2.0; padrão 1.0)
python -m gesture_control.app --motion-sensitivity 1.4

# Abre com ações reais já habilitadas (use com cuidado)
python -m gesture_control.app --execute
```

## Troca de modos

Cada pose da sequência precisa ficar estável por aproximadamente **0,25 s**. Faça a próxima pose rapidamente, dentro do timeout de cerca de 2,2 s:

- Mão aberta → punho → mão aberta: ativa **Atalhos**.
- Punho → mão aberta → punho → mão aberta: ativa **Mouse**.

O indicador na janela mostra o modo ativo. Mão aberta e punho são reservados à troca de modo, não enviam `Space` ou `Ctrl+S`.

## Gestos no modo Mouse

| Gesto | Ação |
| --- | --- |
| Indicador estendido sozinho | Mover cursor |
| Dois dedos apontados para cima | Rolar para cima |
| Dois dedos apontados para baixo | Rolar para baixo |
| Aproximar/afastar polegar e indicador | Reduzir/aumentar zoom |

O cursor segue a ponta do indicador dentro de uma área central da imagem e é suavizado para reduzir tremor. A ponta precisa ser a única dos quatro dedos estendida; a pose é diferente dos dois dedos usados para rolagem e da pinça usada para zoom. A câmera é espelhada, então mover a mão para a direita no preview move o cursor para a direita.

A rolagem começa quando a pose de dois dedos permanece estável por 0,25 s. Depois, envia um passo a cada 0,18 s, cerca de cinco passos por segundo. O zoom acompanha mudanças da distância normalizada entre polegar e indicador e emite passos com intervalo mínimo de 0,22 s.

## Gestos no modo Atalhos

| Gesto | Ação |
| --- | --- |
| Polegar para cima | `Enter` |
| Polegar para baixo | `Esc` |
| Deslize horizontal para a esquerda/direita | Voltar/avançar no histórico do navegador |

Uma pose estática reconhecida começa após 0,25 s. Entre ações pontuais há intervalo de 1,5 s. O controle do cursor, a rolagem sustentada e o zoom não usam esse cooldown. Deslizes verticais não são usados para rolagem.

## Testes

```powershell
python -m pytest -q
```

Os testes cobrem poses, alternância de modos, zoom por pinça, mapeamento e suavização do cursor, rolagem em modo de teste e rearme das ações. A webcam e o movimento real do cursor precisam ser verificados no computador de destino.

## Próximas etapas

1. Clique e arraste com gestos que não conflitem com o zoom.
2. Ajuste de velocidade do cursor, rolagem e zoom na interface.
3. Personalização de gestos e perfis em JSON.
4. Calibração visual da área de movimento.
5. Teste no Windows e empacotamento com PyInstaller.
