"""Background webcam/gesture worker; all image processing stays on-device."""
import threading
import time
from datetime import datetime

import cv2
import mediapipe as mp
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .keyboard_controller import KeyboardController
from .motion_recognizer import MotionRecognizer
from .mouse_controller import MouseController
from .recognizer import HandGestureRecognizer
from .safety_manager import SafetyManager, SafetySettings


class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    action_recorded = Signal(str, str, str)

    ACTION_DELAY_SECONDS = 1.5
    SCROLL_REPEAT_SECONDS = 0.18

    def __init__(
        self,
        camera_index=0,
        execute=False,
        motion_sensitivity=1.0,
        parent=None,
    ):
        super().__init__(parent)
        self.camera_index = camera_index
        self.execute_actions = execute
        self.motion_sensitivity = motion_sensitivity
        self._pause_lock = threading.Lock()
        self._paused = False
        self._last_action_time = float("-inf")

    def set_paused(self, paused: bool) -> None:
        with self._pause_lock:
            self._paused = paused

    def _is_paused(self) -> bool:
        with self._pause_lock:
            return self._paused

    def _dispatch(
        self,
        gesture_name,
        action,
        keyboard,
        mouse,
        now,
        bypass_delay=False,
    ):
        elapsed = now - self._last_action_time
        if not bypass_delay and elapsed < self.ACTION_DELAY_SECONDS:
            remaining = self.ACTION_DELAY_SECONDS - elapsed
            return f"Aguardando intervalo de segurança ({remaining:.1f}s)"

        if action.startswith("scroll_"):
            result = mouse.execute(action)
        else:
            shortcut = {
                "page_forward": "alt+right",
                "page_back": "alt+left",
            }.get(action, action)
            result = keyboard.execute(shortcut)

        self._last_action_time = now
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_recorded.emit(timestamp, gesture_name, result)
        return result

    def run(self) -> None:
        cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            cap.release()
            self.status_changed.emit(
                f"Não foi possível abrir a câmera {self.camera_index}."
            )
            return

        self.status_changed.emit("Câmera ativa — processamento local.")

        hands_api = mp.solutions.hands
        recognizer = HandGestureRecognizer()
        motion_recognizer = MotionRecognizer(
            sensitivity=self.motion_sensitivity,
            enable_vertical=False,
        )
        safety = SafetyManager(
            SafetySettings(
                hold_seconds=1.5,
                cooldown_seconds=1.5,
                neutral_seconds=0.45,
                min_confidence=0.78,
            )
        )
        keyboard = KeyboardController(dry_run=not self.execute_actions)
        mouse = MouseController(dry_run=not self.execute_actions)

        scroll_candidate = None
        scroll_candidate_since = 0.0

        try:
            with hands_api.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.65,
                min_tracking_confidence=0.60,
            ) as hands:
                while not self.isInterruptionRequested():
                    ok, frame = cap.read()
                    if not ok:
                        self.status_changed.emit(
                            "A câmera parou de fornecer imagens."
                        )
                        break

                    frame = cv2.flip(frame, 1)

                    if not self._is_paused():
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        result = hands.process(rgb)
                        detected = None
                        hand_landmarks = None

                        if result.multi_hand_landmarks:
                            hand = result.multi_hand_landmarks[0]
                            hand_landmarks = hand.landmark
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame,
                                hand,
                                hands_api.HAND_CONNECTIONS,
                            )
                            detected = recognizer.recognize(hand_landmarks)

                        now = time.monotonic()
                        motion = motion_recognizer.update(
                            hand_landmarks,
                            now,
                        )

                        if motion:
                            scroll_candidate = None
                            safety.suppress_until_neutral()
                            response = self._dispatch(
                                motion.name,
                                motion.action,
                                keyboard,
                                mouse,
                                now,
                            )
                            self.status_changed.emit(
                                f"{motion.name}: {response}"
                            )

                        elif detected and detected.action in (
                            "scroll_up",
                            "scroll_down",
                        ):
                            safety.suppress_until_neutral()

                            if detected.action != scroll_candidate:
                                scroll_candidate = detected.action
                                scroll_candidate_since = now

                            stable_for = now - scroll_candidate_since
                            repeat_elapsed = now - self._last_action_time

                            if (
                                stable_for >= self.ACTION_DELAY_SECONDS
                                and repeat_elapsed >= self.SCROLL_REPEAT_SECONDS
                            ):
                                response = self._dispatch(
                                    detected.name,
                                    detected.action,
                                    keyboard,
                                    mouse,
                                    now,
                                    bypass_delay=True,
                                )
                                self.status_changed.emit(
                                    f"{detected.name}: {response}"
                                )
                            else:
                                remaining = max(
                                    0.0,
                                    self.ACTION_DELAY_SECONDS - stable_for,
                                )
                                self.status_changed.emit(
                                    f"{detected.name} — mantenha; "
                                    f"rolagem em {remaining:.1f}s"
                                )

                        else:
                            scroll_candidate = None
                            confirmed = safety.update(detected, now)

                            if confirmed:
                                response = self._dispatch(
                                    confirmed.name,
                                    confirmed.action,
                                    keyboard,
                                    mouse,
                                    now,
                                )
                                self.status_changed.emit(
                                    f"{confirmed.name}: {response}"
                                )
                            elif detected:
                                self.status_changed.emit(
                                    f"Candidato: {detected.name} — "
                                    "mantenha por 1,5 s"
                                )

                    if self._is_paused():
                        cv2.putText(
                            frame,
                            "PAUSADO",
                            (18, 35),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 180, 255),
                            2,
                        )

                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    height, width, channels = rgb_frame.shape
                    image = QImage(
                        rgb_frame.data,
                        width,
                        height,
                        channels * width,
                        QImage.Format.Format_RGB888,
                    ).copy()
                    self.frame_ready.emit(image)

        except Exception as exc:
            self.status_changed.emit(
                f"Falha no reconhecimento: {exc}"
            )
        finally:
            cap.release()
            self.status_changed.emit("Câmera desligada.")
