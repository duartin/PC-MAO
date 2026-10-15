# PC-MAO — controle do computador por gestos

Aplicação local em Python para controlar o computador por poses e movimentos da mão capturados pela webcam. O processamento é feito no dispositivo; o programa não grava nem envia imagens.

Para registrar atualizações no GitHub, aplique os arquivos na pasta clonada `PC-MAO`, que contém `.git`. O ZIP de distribuição não inclui o histórico Git. Consulte [`GIT_COMANDOS.md`](GIT_COMANDOS.md).

## Recursos

- Interface PySide6 com vídeo, modo ativo, histórico de ações, perfis, mapeamentos e ajustes.
- **Modo Mouse** inicia ativo. O indicador move o cursor; dois dedos apontados rolam; a pinça polegar–indicador ajusta o zoom.
- **Clique, clique direito e arraste** usam pinças distintas: polegar+médio clica/arrasta; polegar+anelar faz clique direito após estabilidade. Dois toques esquerdos rápidos podem ser interpretados pelo Windows como duplo clique.
- **Modo Atalhos** é exclusivo e separado dos gestos do mouse. As sequências de mão aberta e punho alternam os modos.
- A moldura rosa no preview mostra a área ativa do cursor; a pose atual e confiança aparecem sobre o vídeo. Margem, suavização, velocidade, aceleração e zona morta do cursor, sensibilidade de deslizes e frequência de rolagem/zoom podem ser ajustadas.
- Perfis nomeados armazenam esses parâmetros e quatro mapeamentos de atalhos em JSON.
- O modo de teste é padrão. A caixa **Executar ações reais no computador** precisa estar marcada para mover o cursor, clicar, arrastar, enviar atalhos ou controlar rolagem/zoom de verdade.

## Gestos

### Modo Mouse

| Gesto | Ação |
| --- | --- |
| Indicador estendido sozinho | Mover cursor |
| Dois dedos apontados para cima | Rolar para cima continuamente |
| Dois dedos apontados para baixo | Rolar para baixo continuamente |
| Aproximar/afastar polegar e indicador | Reduzir/aumentar zoom |
| Toque rápido do polegar com o dedo médio | Clique esquerdo |
| Pinça polegar–anelar | Clique direito após 0,25 s de estabilidade |
| Manter polegar e dedo médio juntos por cerca de 0,55 s | Iniciar arraste; mover o indicador para deslocar e soltar para finalizar |

O clique exige uma pose reconhecida por pelo menos 0,12 s e uma soltura estável por mais 0,12 s para filtrar tremores. O arraste libera o botão se a mão sumir, se o reconhecimento for pausado, se houver troca de modo ou quando a câmera parar. A pinça polegar–indicador continua reservada ao zoom.

### Modo Atalhos

| Gesto | Mapeamento padrão |
| --- | --- |
| Polegar para cima | `Enter` |
| Polegar para baixo | `Esc` |
| Deslize horizontal para a esquerda | `Alt+Left` |
| Deslize horizontal para a direita | `Alt+Right` |

As sequências são: mão aberta → punho → mão aberta para ativar Atalhos; punho → mão aberta → punho → mão aberta para voltar ao Mouse. Mão aberta e punho ficam reservados à alternância.

## Temporização e calibração

Poses estáticas começam após **0,25 s** de estabilidade. A moldura rosa representa a área de entrada do cursor; ajuste **Margem da área ativa** no painel. Margens menores ampliam a região útil e podem aumentar o alcance da mão necessário; margens maiores ajudam a manter a mão dentro de uma zona mais restrita. A suavização controla a relação entre resposta e tremor.

A rolagem começa após estabilidade e repete de acordo com o perfil (padrão **0,18 s**). O zoom tem intervalo mínimo próprio (padrão **0,22 s**). Os **1,5 s** padrão são o intervalo entre ações pontuais no modo Atalhos, não um atraso para iniciar cursor, clique/arraste, rolagem ou zoom.

## Requisitos e instalação

- Windows 10/11
- Python 3.11 de 64 bits
- Webcam integrada ou USB

No PowerShell, dentro da pasta clonada:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se a ativação do ambiente for bloqueada, execute `Set-ExecutionPolicy -Scope Process Bypass` no PowerShell atual e ative novamente.

## Executar e testar

```powershell
python -m pytest -q
python -m gesture_control.app
```

A janela começa em modo de teste. Marque a caixa de execução real somente quando estiver pronto para permitir ações no computador.

Parâmetros opcionais:

```powershell
python -m gesture_control.app --camera 1
python -m gesture_control.app --profile Apresentação
python -m gesture_control.app --motion-sensitivity 1.4
```

## Perfis e personalização

A interface permite selecionar, criar, salvar, renomear, excluir, importar e exportar perfis. O `Default` protegido não pode ser renomeado nem removido. O arquivo local padrão é `%USERPROFILE%\.pc-mao\profiles.json`; ele não é sobrescrito pelo código-fonte nem enviado a lugar nenhum. [`profiles.example.json`](profiles.example.json) serve como modelo para editar/copiar perfis.

Os mapeamentos permitidos para polegar para cima/baixo e deslize esquerdo/direito são atalhos de uma lista segura (`enter`, `esc`, `space`, `ctrl+s`, `alt+tab`, `alt+left`, `alt+right`, `zoom_in` e `zoom_out`). A lista não aceita comandos de shell, exclusão ou atalhos arbitrários. Os gestos de clique e arraste permanecem fixos para não conflitar com zoom e rolagem.

Ajuste as configurações na interface e clique em **Salvar** para persistir. O assistente de calibração fornece um roteiro manual para testar centro/bordas e ajustar a margem; a medição automática dos extremos ainda não está implementada. A seleção de outro perfil carrega os valores guardados; perfis podem também ser selecionados pela opção `--profile`.

## Empacotamento Windows (opcional)

Na raiz do repositório, em PowerShell com Python 3.11 instalado:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

O executável é produzido em `dist\PC-MAO\PC-MAO.exe`. O script foi preparado, mas o build e o uso da webcam precisam ser validados em um computador Windows real.

## Testes e limites

```powershell
python -m pytest -q
```

Os testes cobrem poses, modos, mapeamentos allowlisted, ciclo de vida de perfis, calibração de coordenadas, controles de cursor, clique, arraste, zoom, rolagem simulada e liberação do botão em cancelamento. A webcam, o funcionamento do PyAutoGUI e o build final ainda precisam ser testados no computador Windows de destino.
