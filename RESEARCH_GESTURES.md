# Pesquisa: gestos em projetos de mouse virtual

## Padrões observados

A documentação oficial do MediaPipe descreve 21 landmarks de mão e coordenadas `x` e `y` normalizadas pela largura e altura da imagem. Em processamento de vídeo/stream, o tracking reaproveita a detecção entre quadros para reduzir latência. Isso sustenta o uso do landmark 8 (ponta do indicador) em coordenadas normalizadas para mapear o cursor, mantendo a execução no fluxo de câmera existente. [1]

Nos projetos comparados, o padrão mais recorrente é **indicador isolado para mover o cursor**. Tanto `Rusheekg/Virtual-Mouse` quanto `AppajiDheeraj/Virtual-Mouse` usam esse movimento; os dois mencionam suavização e mapeamento do espaço da câmera para a tela. O código do primeiro suaviza o cursor a cada quadro antes de mover o ponteiro. [2] [3] [6]

A **pinça polegar–indicador** é comum como ação discreta. Um projeto a usa para clique; outro usa a distância para reconhecer clique direito/arraste, enquanto a rolagem fica em um gesto diferente. As convenções de clique e arraste variam entre projetos; não há um único mapa universal. [2] [3] [4] [7]

Para rolagem, as implementações consultadas usam combinações distintas: dois dedos, dedos juntos e movimento vertical, ou mão aberta com deslocamento. Isso confirma que a separação por modos e poses claramente distintas é uma escolha adequada para reduzir conflito neste projeto. [2] [3] [4]

O projeto `small-cactus/handTrack` descreve uma área interna da imagem mapeada para a tela e suavização do cursor com limiar de tremor; também desativa o movimento quando a mão some e protege a liberação do botão do mouse. O código consultado usa outra referência de posição (base do anelar), portanto esta implementação não copia esse detalhe: adota a ponta do indicador solicitada pelo usuário. [4] [5]

## Decisão aplicada ao PC-MAO

- Cursor: indicador estendido sozinho, usando landmark 8.
- Suavização: filtro de primeira ordem e área útil central com margens para alcançar as bordas da tela sem levar a mão até o limite da imagem.
- Rolagem: manter os dois dedos já validados pelo usuário; inicia após estabilidade curta e repete continuamente.
- Zoom: pinça em via exclusiva, sem atualizar o zoom durante o gesto de cursor.
- Temporização: poses começam após 0,25 s de estabilidade; 1,5 s fica como cooldown entre ações discretas, sem atrasar cursor ou rolagem contínua.
- Segurança: cursor/atalhos/rolagem/zoom reais permanecem atrás da caixa de ativação; o modo padrão simula.

## Referências

[1]: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python "MediaPipe Hand Landmarker for Python"
[2]: https://github.com/Rusheekg/Virtual-Mouse "Rusheekg/Virtual-Mouse"
[3]: https://github.com/AppajiDheeraj/Virtual-Mouse "AppajiDheeraj/Virtual-Mouse"
[4]: https://github.com/small-cactus/handTrack "small-cactus/handTrack"
[5]: https://raw.githubusercontent.com/small-cactus/handTrack/main/handTrack.py "Código do small-cactus/handTrack"
[6]: https://raw.githubusercontent.com/Rusheekg/Virtual-Mouse/main/Virtual_Mouse.py "Código do Rusheekg/Virtual-Mouse"
[7]: https://raw.githubusercontent.com/AppajiDheeraj/Virtual-Mouse/main/mouse.py "Código do AppajiDheeraj/Virtual-Mouse"
