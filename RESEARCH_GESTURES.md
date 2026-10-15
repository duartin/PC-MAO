# Pesquisa: padrões de interação em mouse virtual por gestos

## Padrões observados

A documentação do MediaPipe descreve 21 landmarks de mão e coordenadas `x` e `y` normalizadas pela imagem. Isso permite mapear a ponta do indicador para uma área de tela e manter o processamento no fluxo local de vídeo. [1]

Nos projetos consultados, o indicador isolado é um padrão recorrente para mover o cursor. Os projetos também aplicam suavização e mapeamento da área da câmera para a tela para reduzir tremor e evitar exigir movimentos até a borda da imagem. [2] [3] [4]

`parthahuja33/gesture-mouse` documenta indicador para cursor, pinça para clique e pinça sustentada para arraste. Também separa rolagem em um gesto de dedo médio, recomenda suavização e oferece configuração de thresholds. [5] Isso é um precedente para distinguir toque de gesto sustentado pelo tempo; neste projeto, a pinça polegar–médio controla clique/arraste e polegar–indicador continua no zoom.

O projeto `faizahmad-khan/AI-VIRTUAL-MOUSE` mostra outra variação: combina movimento do indicador, pinças para ações distintas e uma GUI para ajustar sensibilidade, limiares e área de movimento. Seu guia destaca a separação de scroll, clique e arraste por prioridade no processamento. [6] A página técnica da GeeksforGeeks também descreve estabilização de poses por vários quadros e liberação de `mouseUp` ao terminar arraste, reforçando que a máquina de estados precisa tratar a soltura explicitamente. [7]

Os mapas de gesto variam entre projetos; não existe uma convenção universal. Há implementações que usam a pinça polegar–indicador para clique e arraste, outras atribuem clique direito à pinça polegar–médio, e outras separam rolagem por postura ou movimento. [2] [3] [5] [6] Por isso, a decisão aqui prioriza não reutilizar a pinça já atribuída ao zoom.

## Decisões aplicadas ao PC-MAO

- **Cursor:** indicador sozinho, landmark 8, com filtro de suavização e mapeamento dentro de área configurável.
- **Calibração:** margem ajustável por perfil e moldura rosa desenhada no vídeo para mostrar a zona que mapeia para a tela. Isso oferece feedback visual sem iniciar um wizard dependente de posicionamento preciso nos quatro cantos.
- **Clique/duplo clique/arraste:** pinça polegar–médio, distinta da pinça polegar–indicador do zoom. Um toque curto clica; um segundo toque dentro de janela configurável emite duplo clique; manter por aproximadamente 0,55 s inicia arraste; soltar finaliza. Duração mínima, debounce de soltura e recuperação segura reduzem falsos positivos.
- **Recuperação segura:** perda da mão, pausa, troca de modo e encerramento cancelam o clique candidato e liberam o botão se o arraste estava ativo.
- **Rolagem/zoom:** dois dedos apontados enviam +80/-80 ticks por passo por padrão; a cadência/intensidade é configurável. A pinça polegar–indicador continua no zoom, com intervalo próprio.
- **Perfis:** ajustes numéricos, limiar calibrado da pinça, janela de duplo clique e quatro atalhos de poses/deslizes são guardados em JSON local; as ações de teclado são verificadas contra allowlist.
- **Ativação real:** permanece desabilitada por padrão. O usuário precisa marcar a caixa da interface.

## Referências

[1]: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python "MediaPipe Hand Landmarker for Python"
[2]: https://github.com/Rusheekg/Virtual-Mouse "Rusheekg/Virtual-Mouse"
[3]: https://github.com/AppajiDheeraj/Virtual-Mouse "AppajiDheeraj/Virtual-Mouse"
[4]: https://github.com/small-cactus/handTrack "small-cactus/handTrack"
[5]: https://github.com/parthahuja33/gesture-mouse "parthahuja33/gesture-mouse"
[6]: https://github.com/faizahmad-khan/AI-VIRTUAL-MOUSE "faizahmad-khan/AI-VIRTUAL-MOUSE"
[7]: https://www.geeksforgeeks.org/computer-vision/ai-virtual-mouse/ "GeeksforGeeks: AI Virtual Mouse"


## Comparação adicional de projetos GitHub (15/10/2026)

Os repositórios analisados mostram que não há um único mapeamento universal. `Rusheekg/Virtual-Mouse` usa indicador isolado para mover, indicador+médio para rolagem e pinça indicador–polegar para clique; o código suaviza o cursor por interpolação e calcula rolagem a partir do deslocamento vertical com um limiar, em vez de disparar uma quantidade fixa em todos os quadros. O projeto ainda usa cooldown de clique. [8] [9]

`AppajiDheeraj/Virtual-Mouse` usa dedos indicadores e médios próximos para clique, pinça indicador–polegar para clique direito ou arraste conforme a distância, rolagem pela mão aberta e uma janela de tempo para detectar clique duplo. O código trata ações como modos e devolve o estado para movimento, mas suas regras de clique/arraste são diferentes das escolhas do PC-MAO. [10] [11]

`parthahuja33/gesture-mouse` documenta pinça curta para clique e pinça sustentada para arraste, rolagem baseada no movimento do dedo médio e thresholds configuráveis para clique, scroll e debounce. Isso se aproxima da separação temporal que já existe no PC-MAO; é um precedente para calibrar thresholds, não uma razão para trocar os gestos atualmente aprovados. [12] [13]

`pakindipe/GestureMouse` usa velocidade do indicador para variar o ganho do cursor, limita o tamanho máximo do passo, desacelera perto das bordas e mantém a intenção por múltiplos quadros para reduzir troca de modo por tremor. Para rolagem acumula deslocamento e limita cada emissão a um máximo; para pinça separa o início, clique curto, retenção para arraste e soltura. Esses mecanismos são candidatos a uma evolução incremental do PC-MAO, cuja base já tem suavização, zona morta, margem calibrável, estabilidade e liberação segura do arraste. [14] [15]

### O que é viável implementar no PC-MAO

1. **Calibração de limiar da pinça por palma — implementada:** o assistente coleta pinça e mão relaxada, normaliza a distância pela palma, usa medianas para rejeitar ruído e salva o limiar no perfil.
2. **Velocidade adaptativa e segurança de cursor — implementadas:** ganho configurável, limite máximo de pixels por quadro e redução de ganho perto das bordas complementam suavização e zona morta.
3. **Scroll proporcional — não adotado nesta etapa:** segue o pedido de manter `+80/-80` ticks por passo (configurável) e repetição contínua. Scroll proporcional pode ser avaliado separadamente sem alterar o padrão atual. [9] [11] [15]
4. **Janela explícita de duplo clique — implementada:** o primeiro toque fica em espera pela janela configurada; um segundo toque gera duplo clique, caso contrário ocorre clique simples.
5. **Persistência/histerese de gesto — implementada e testada:** poses discretas exigem estabilidade; pequenas perdas de tracking têm tolerância, enquanto o cursor responde imediatamente. Arraste solta o botão em perda de mão, pausa, troca de modo ou encerramento. [15]

Os itens 1, 2, 4 e 5 foram implementados neste ciclo; o item 3 permanece uma alternativa futura. O mapeamento conserva o zoom polegar–indicador e usa polegar–médio para clique, duplo clique e arraste. A rolagem mantém `+80/-80` por passo com cadência configurável.

[8]: https://github.com/Rusheekg/Virtual-Mouse "Rusheekg/Virtual-Mouse — documentação"
[9]: https://raw.githubusercontent.com/Rusheekg/Virtual-Mouse/main/Virtual_Mouse.py "Rusheekg/Virtual-Mouse — código-fonte"
[10]: https://github.com/AppajiDheeraj/Virtual-Mouse "AppajiDheeraj/Virtual-Mouse — documentação"
[11]: https://raw.githubusercontent.com/AppajiDheeraj/Virtual-Mouse/main/mouse.py "AppajiDheeraj/Virtual-Mouse — código-fonte"
[12]: https://github.com/parthahuja33/gesture-mouse/tree/main/virtual_mouse "parthahuja33/gesture-mouse — estrutura e documentação"
[13]: https://github.com/parthahuja33/gesture-mouse "parthahuja33/gesture-mouse — thresholds e gestos"
[14]: https://github.com/pakindipe/GestureMouse "pakindipe/GestureMouse — documentação"
[15]: https://raw.githubusercontent.com/pakindipe/GestureMouse/main/gesture_mouse.py "pakindipe/GestureMouse — código-fonte"
