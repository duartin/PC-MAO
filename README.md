# PC-MAO — controle do computador por gestos

Aplicação local em Python para controlar o computador por gestos capturados pela webcam. O processamento é feito no dispositivo; o programa não grava nem envia imagens.

Para registrar atualizações no GitHub, aplique os arquivos na pasta clonada `PC-MAO`, que contém `.git`. O ZIP de distribuição não inclui o histórico Git. Consulte [`GIT_COMANDOS.md`](GIT_COMANDOS.md).

## Recursos

- Interface PySide6 com vídeo, modo ativo, HUD de pose/confiança/estado, histórico, perfis e ajustes.
- **Modo Mouse** inicia ativo. Indicador estendido sozinho move o cursor imediatamente; suavização, velocidade adaptativa, desaceleração nas bordas, zona morta e limite de passo ajudam na precisão.
- Dois dedos para cima/baixo mantidos rolam continuamente em **+80/-80 ticks por passo** por padrão (ajustável no perfil).
- Pinça polegar–médio: toque curto = clique esquerdo; dois toques dentro da janela configurável = clique duplo; manter = arraste; soltar encerra.
- Pinça polegar–anelar = clique direito. A pinça polegar–indicador continua reservada ao zoom, com aproximação/afastamento.
- **Modo Atalhos** é exclusivo e separado dos gestos do mouse. Sequências específicas alternam os modos.
- Assistente guiado calibra o limiar individual da pinça. A moldura no vídeo mostra a área ativa do cursor.
- Perfis JSON armazenam parâmetros, calibração e mapeamentos seguros; podem ser criados, renomeados, importados e exportados.
- O modo de teste é padrão. A caixa **Executar ações reais no computador** precisa ser marcada para enviar entrada real.

## Gestos

### Modo Mouse

| Gesto | Ação |
| --- | --- |
| Indicador estendido sozinho | Move o cursor imediatamente |
| Dois dedos apontados para cima | Rola continuamente para cima |
| Dois dedos apontados para baixo | Rola continuamente para baixo |
| Pinça polegar–indicador, aproximar/afastar | Zoom − / + |
| Toque curto polegar–médio | Clique esquerdo |
| Dois toques polegar–médio na janela configurada | Clique duplo esquerdo |
| Manter polegar–médio juntos por cerca de 0,55 s | Inicia arraste; indicador move o cursor; soltar finaliza |
| Pinça polegar–anelar | Clique direito |

A pinça de clique usa um limiar normalizado pela largura da palma. O toque precisa durar pelo menos 0,12 s e a soltura fica estável por 0,12 s para filtrar tremores. O primeiro toque é mantido em espera por até 0,32 s (padrão) para distinguir clique simples de duplo clique. O assistente ajusta o limiar com amostras da própria mão. Perda da mão, pausa, troca de modo e encerramento cancelam o clique candidato e liberam o botão se houver arraste ativo.

### Modo Atalhos

| Gesto | Mapeamento padrão |
| --- | --- |
| Polegar para cima | `Enter` |
| Polegar para baixo | `Esc` |
| Deslize horizontal para a esquerda | `Alt+Left` |
| Deslize horizontal para a direita | `Alt+Right` |

A sequência mão aberta → punho → mão aberta ativa Atalhos. Punho → mão aberta → punho → mão aberta retorna ao Mouse. Mão aberta e punho são reservados para troca de modo.

## Temporização e calibração

Gestos discretos passam por filtragem de estabilidade/histerese; poses estáticas começam após aproximadamente **0,25 s**. Cursor não tem atraso de início. A moldura no preview mostra a área ativa do cursor; ajuste **Margem da área ativa**, suavização, velocidade, aceleração, zona morta e passo máximo conforme a webcam e a distância da mão.

A rolagem começa após estabilizar a pose (cerca de **0,25 s**) e repete no intervalo do perfil (padrão **0,18 s**), enviando **80 ticks** por passo para cima e **-80 ticks** para baixo. O zoom tem intervalo próprio (padrão **0,22 s**). O intervalo de **1,5 s** vale entre ações discretas do modo Atalhos; não atrasa movimento do cursor nem rolagem contínua.

Para calibrar: inicie a câmera e selecione **Calibrar pinça de clique**. Mantenha a pinça polegar–médio durante a primeira coleta e, depois, relaxe/afaste os dedos durante a segunda. O sistema calcula o limiar a partir das medianas e informa quando há amostras insuficientes ou posições pouco distinguíveis. Revise também a área do cursor e salve o perfil.

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

```powershell
python -m gesture_control.app --camera 1
python -m gesture_control.app --profile Apresentação
python -m gesture_control.app --motion-sensitivity 1.4
```

## Perfis e personalização

A interface permite selecionar, criar, salvar, renomear, excluir, importar e exportar perfis. O `Default` protegido não pode ser renomeado nem removido. O arquivo local padrão é `%USERPROFILE%\.pc-mao\profiles.json`; não é sobrescrito pelo código-fonte nem enviado a lugar nenhum. [`profiles.example.json`](profiles.example.json) serve como modelo.

Os quatro mapeamentos permitidos são polegar para cima/baixo e deslize esquerdo/direito. As ações são verificadas contra uma lista segura; comandos de shell, exclusão e atalhos arbitrários não são aceitos. Gestos de mouse permanecem fixos para reduzir conflitos.

## Empacotamento Windows (opcional)

Na raiz do repositório, em PowerShell com Python 3.11 instalado:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

O executável é produzido em `dist\PC-MAO\PC-MAO.exe`. O build e o uso da webcam precisam ser validados no computador Windows de destino.

## Testes e limites

```powershell
python -m pytest -q
```

Os testes automatizados cobrem poses, modos, mapeamentos seguros, ciclo de vida dos perfis, calibração da pinça, histerese, movimento de cursor, clique/duplo clique/arraste, rolagem simulada e recuperação segura. Câmera, PyAutoGUI e empacotamento final ainda devem ser testados no computador Windows de destino.
