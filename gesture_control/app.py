"""Webcam MVP. Local processing only; execution is opt-in via --execute."""
import argparse
import time

import cv2
import mediapipe as mp

from .keyboard_controller import KeyboardController
from .motion_recognizer import MotionRecognizer
from .mouse_controller import MouseController
from .recognizer import HandGestureRecognizer
from .safety_manager import SafetyManager


def run(camera_index: int = 0, execute: bool = False) -> int:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Erro: não foi possível abrir a câmera {camera_index}.")
        return 2

    hands_api = mp.solutions.hands
    recognizer = HandGestureRecognizer()
    motion_recognizer = MotionRecognizer()
    safety = SafetyManager()
    keyboard = KeyboardController(dry_run=not execute)
    mouse = MouseController(dry_run=not execute)
    last_message = "Aguardando uma mão..."
    print("Câmera ativa. Pressione Q para sair; P pausa/retoma.")
    print("Deslize para cima/baixo para rolar e esquerda/direita para navegar.")
    print("Modo de teste ativo: nenhuma ação será enviada." if not execute else
          "EXECUÇÃO ATIVA: gestos enviarão teclas e rolagem ao sistema.")
    if execute:
        print("Mantenha Q/Esc acessível para interromper imediatamente.")

    paused = False
    with hands_api.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.65,
        min_tracking_confidence=0.60,
    ) as hands:
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Erro: a câmera parou de fornecer imagens.")
                    return 3
                frame = cv2.flip(frame, 1)
                if not paused:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = hands.process(rgb)
                    detected = None
                    hand_landmarks = None
                    if result.multi_hand_landmarks:
                        hand = result.multi_hand_landmarks[0]
                        hand_landmarks = hand.landmark
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame, hand, hands_api.HAND_CONNECTIONS
                        )
                        detected = recognizer.recognize(hand_landmarks)
                    now = time.monotonic()
                    motion = motion_recognizer.update(hand_landmarks, now)
                    if motion:
                        safety.suppress_until_neutral()
                        if motion.action.startswith("scroll_"):
                            response = mouse.execute(motion.action)
                        else:
                            shortcut = "alt+right" if motion.action == "page_forward" else "alt+left"
                            response = keyboard.execute(shortcut)
                        last_message = f"{motion.name} → {response}"
                        print(last_message)
                    else:
                        confirmed = safety.update(detected, now)
                        if confirmed:
                            last_message = f"{confirmed.name} → {keyboard.execute(confirmed.action)}"
                            print(last_message)
                        elif detected:
                            last_message = f"Candidato: {detected.name} ({detected.confidence:.0%}) — mantenha"
                        else:
                            last_message = "Mão não reconhecida com segurança — estado neutro"

                cv2.putText(frame, "PAUSADO" if paused else "ATIVO", (18, 32),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 200, 40), 2)
                cv2.putText(frame, last_message[:85], (18, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.putText(frame, "Q: sair | P: pausar/retomar", (18, frame.shape[0] - 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                cv2.imshow("Controle por Gestos — Etapa 1", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("p"):
                    paused = not paused
                    motion_recognizer.reset()
                    safety.suppress_until_neutral()
                    last_message = "Reconhecimento pausado" if paused else "Reconhecimento retomado"
        except KeyboardInterrupt:
            pass
        finally:
            cap.release()
            cv2.destroyAllWindows()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="MVP de controle do computador por gestos")
    parser.add_argument("--camera", type=int, default=0, help="índice da webcam (padrão: 0)")
    parser.add_argument("--execute", action="store_true",
                        help="envia os atalhos reais; sem esta opção roda em modo de teste")
    args = parser.parse_args()
    raise SystemExit(run(args.camera, args.execute))


if __name__ == "__main__":
    main()
