# Pesquisa: padrões de interação em mouse virtual por gestos

## Padrões observados

A documentação do MediaPipe descreve 21 landmarks de mão e coordenadas `x` e `y` normalizadas pela imagem. Isso permite mapear a ponta do indicador para uma área de tela e manter o processamento no fluxo local de vídeo. [1]

Nos projetos consultados, o indicador isolado é um padrão recorrente para mover o cursor. Os projetos também aplicam suavização e mapeamento da área da câmera para a tela para reduzir tremor e evitar exigir movimentos até a borda da imagem. [2] [3] [4]

`parthahuja33/gesture-mouse` documenta indicador para cursor, pinça para clique e pinça sustentada para arraste. Também separa rolagem em um gesto de dedo médio, recomenda suavização e oferece configuração de thresholds. [5] Isso é um precedente direto para distinguir toque de gesto sustentado pelo tempo, não para copiar os mesmos dedos: neste projeto, polegar–indicador já controla zoom.

O projeto `faizahmad-khan/AI-VIRTUAL-MOUSE` mostra outra variação: combina movimento do indicador, pinças para ações distintas e uma GUI para ajustar sensibilidade, limiares e área de movimento. Seu guia destaca a separação de scroll, clique e arraste por prioridade no processamento. [6] A página técnica da GeeksforGeeks também descreve estabilização de poses por vários quadros e liberação de `mouseUp` ao terminar arraste, reforçando que a máquina de estados precisa tratar a soltura explicitamente. [7]

Os mapas de gesto variam entre projetos; não existe uma convenção universal. Há implementações que usam a pinça polegar–indicador para clique e arraste, outras atribuem clique direito à pinça polegar–médio, e outras separam rolagem por postura ou movimento. [2] [3] [5] [6] Por isso, a decisão aqui prioriza não reutilizar a pinça já atribuída ao zoom.

## Decisões aplicadas ao PC-MAO

- **Cursor:** indicador sozinho, landmark 8, com filtro de suavização e mapeamento dentro de área configurável.
- **Calibração:** margem ajustável por perfil e moldura rosa desenhada no vídeo para mostrar a zona que mapeia para a tela. Isso oferece feedback visual sem iniciar um wizard dependente de posicionamento preciso nos quatro cantos.
- **Clique/arraste:** pinça polegar–médio, distinta da pinça polegar–indicador do zoom. Uma pinça curta clica; manter por aproximadamente 0,55 s inicia arraste; soltar finaliza. O clique tem duração mínima e debounce de soltura para reduzir falsos positivos.
- **Recuperação segura:** perda da mão, pausa, troca de modo e encerramento cancelam o clique candidato e liberam o botão se o arraste estava ativo.
- **Rolagem/zoom:** dois dedos apontados e pinça polegar–indicador preservados; cadências ajustáveis no perfil.
- **Perfis:** ajustes numéricos e quatro atalhos de poses/deslizes são guardados em JSON local; as ações de teclado são verificadas contra allowlist.
- **Ativação real:** permanece desabilitada por padrão. O usuário precisa marcar a caixa da interface.

## Referências

[1]: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python "MediaPipe Hand Landmarker for Python"
[2]: https://github.com/Rusheekg/Virtual-Mouse "Rusheekg/Virtual-Mouse"
[3]: https://github.com/AppajiDheeraj/Virtual-Mouse "AppajiDheeraj/Virtual-Mouse"
[4]: https://github.com/small-cactus/handTrack "small-cactus/handTrack"
[5]: https://github.com/parthahuja33/gesture-mouse "parthahuja33/gesture-mouse"
[6]: https://github.com/faizahmad-khan/AI-VIRTUAL-MOUSE "faizahmad-khan/AI-VIRTUAL-MOUSE"
[7]: https://www.geeksforgeeks.org/computer-vision/ai-virtual-mouse/ "GeeksforGeeks: AI Virtual Mouse"
