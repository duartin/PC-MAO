"""Background webcam/gesture worker; all image processing stays on-device."""
import threading
import time
from datetime import datetime

import cv2
import mediapipe as mp
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .click_drag import ClickDragController
from .keyboard_controller import KeyboardController
from .mode_manager import ModeManager
from .motion_recognizer import MotionRecognizer
from .mouse_controller import MouseController
from .pinch_zoom import PinchZoomRecognizer
from .profile_manager import ProfileManager
from .recognizer import HandGestureRecognizer
from .safety_manager import SafetyManager, SafetySettings


class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    action_recorded = Signal(str, str, str)
    mode_changed = Signal(str)

    GESTURE_STABILITY_SECONDS = 0.25
    SCROLL_REPEAT_SECONDS = 0.18

    def __init__(self, camera_index=0, execute=False, motion_sensitivity=1.0,
                 parent=None, profile=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.execute_actions = execute
        base_profile = (
            profile if profile is not None
            else {"motion_sensitivity": motion_sensitivity}
        )
        self.profile = ProfileManager.validate_profile(base_profile)
        self.motion_sensitivity = self.profile["motion_sensitivity"]
        self._pause_lock = threading.Lock()
        self._paused = False
        self._last_action_time = float("-inf")

    def set_paused(self, paused: bool) -> None:
        with self._pause_lock:
            self._paused = paused

    def _is_paused(self) -> bool:
        with self._pause_lock:
            return self._paused

    def _dispatch(self, gesture_name, action, keyboard, mouse, now,
                  continuous=False):
        delay = self.profile["action_switch_delay_seconds"]
        elapsed = now - self._last_action_time
        if not continuous and elapsed < delay:
            remaining = delay - elapsed
            return f"Aguardando intervalo entre ações ({remaining:.1f}s)"

        if action.startswith("scroll_"):
            result = mouse.execute(action)
        else:
            result = keyboard.execute(action)

        # Cursor, sustained scrolling and zoom are continuous interactions.
        if not continuous:
            self._last_action_time = now

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_recorded.emit(timestamp, gesture_name, result)
        return result

    def _record_mouse_event(self, event):
        if event is None:
            return
        gesture_name, result = event
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_recorded.emit(timestamp, gesture_name, result)
        self.status_changed.emit(f"{gesture_name}: {result}")

    def _draw_cursor_calibration(self, frame):
        margin = self.profile["cursor_margin"]
        height, width = frame.shape[:2]
        left = int(width * margin)
        top = int(height * margin)
        right = max(left + 1, width - left - 1)
        bottom = max(top + 1, height - top - 1)
        cv2.rectangle(frame, (left, top), (right, bottom), (220, 80, 220), 1)
        cv2.putText(
            frame,
            "AREA ATIVA DO CURSOR",
            (left + 6, max(20, top + 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (220, 80, 220),
            1,
        )

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
        mode_manager = ModeManager(initial_mode=ModeManager.MOUSE)
        pinch_zoom = PinchZoomRecognizer(
            min_interval=self.profile["zoom_repeat_seconds"]
        )
        motion_recognizer = MotionRecognizer(
            sensitivity=self.profile["motion_sensitivity"],
            enable_vertical=False,
        )
        safety = SafetyManager(
            SafetySettings(
                hold_seconds=self.GESTURE_STABILITY_SECONDS,
                cooldown_seconds=self.profile["action_switch_delay_seconds"],
                neutral_seconds=0.25,
                min_confidence=0.78,
            )
        )
        keyboard = KeyboardController(dry_run=not self.execute_actions)
        mouse = MouseController(
            dry_run=not self.execute_actions,
            smoothing=self.profile["cursor_smoothing"],
            edge_margin=self.profile["cursor_margin"],
            speed=self.profile["cursor_speed"],
            acceleration=self.profile["cursor_acceleration"],
            deadzone_pixels=self.profile["cursor_deadzone_pixels"],
        )
        click_drag = ClickDragController(mouse)
        self.mode_changed.emit(mode_manager.mode)
        self.status_changed.emit(
            "Modo Mouse ativo. Para Atalhos: mão aberta-punho-mão aberta; "
            "para Mouse: punho-mão aberta-punho-mão aberta."
        )

        scroll_candidate = None
        scroll_candidate_since = 0.0
        last_scroll_action_time = float("-inf")
        right_click_latched = False
        right_click_started_at = None

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
                    if self._is_paused():
                        self._record_mouse_event(click_drag.cancel())
                        cv2.putText(
                            frame,
                            "PAUSADO",
                            (18, 35),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 180, 255),
                            2,
                        )
                    else:
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
                        changed_mode = mode_manager.update(detected, now)
                        if changed_mode:
                            self.mode_changed.emit(changed_mode)
                            label = (
                                "Atalhos"
                                if changed_mode == ModeManager.KEYBOARD
                                else "Mouse"
                            )
                            self.status_changed.emit(f"Modo {label} ativado.")

                        is_mode_pose = (
                            detected is not None
                            and detected.action in (
                                ModeManager.OPEN_ACTION,
                                ModeManager.FIST_ACTION,
                            )
                        )
                        action = getattr(detected, "action", None)
                        if detected is not None:
                            cv2.putText(
                                frame,
                                f"{detected.name}  {detected.confidence:.0%}",
                                (18, 34),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.62,
                                (80, 230, 140),
                                2,
                            )
                        if action != "right_click":
                            right_click_latched = False
                            right_click_started_at = None
                        elif mode_manager.mode == ModeManager.MOUSE:
                            if right_click_started_at is None:
                                right_click_started_at = now
                            elif (
                                not right_click_latched
                                and now - right_click_started_at
                                >= self.GESTURE_STABILITY_SECONDS
                            ):
                                right_click_latched = True
                                self._record_mouse_event(
                                    ("Clique direito", mouse.click_right())
                                )
                        if action in (
                            ModeManager.OPEN_ACTION,
                            ModeManager.FIST_ACTION,
                            "enter",
                            "esc",
                            "cursor",
                            "click_drag",
                            "pinch",
                            "scroll_up",
                            "scroll_down",
                            "right_click",
                        ):
                            motion_recognizer.reset()

                        # A missing hand, a mode switch or a different gesture
                        # cancels click candidates; a drag always releases.
                        if (
                            mode_manager.mode != ModeManager.MOUSE
                            or hand_landmarks is None
                            or is_mode_pose
                            or (action not in (None, "cursor", "click_drag"))
                        ):
                            click_event = click_drag.cancel()
                        elif action == "click_drag":
                            index_tip = hand_landmarks[8]
                            click_event = click_drag.update(
                                True,
                                (index_tip.x, index_tip.y),
                                now,
                            )
                        else:
                            click_event = click_drag.update(False, None, now)
                        self._record_mouse_event(click_event)

                        if (
                            mode_manager.mode == ModeManager.MOUSE
                            and action == "pinch"
                        ):
                            zoom_action = pinch_zoom.update(hand_landmarks, now)
                        else:
                            pinch_zoom.reset()
                            zoom_action = None

                        if mode_manager.mode == ModeManager.MOUSE:
                            self._draw_cursor_calibration(frame)

                        # Hand-open/fist poses only switch modes.
                        if is_mode_pose:
                            scroll_candidate = None
                            safety.suppress_until_neutral()

                        # Thumb-middle pinch: short tap clicks; hold drags.
                        elif action == "click_drag":
                            scroll_candidate = None
                            safety.suppress_until_neutral()

                        # Index-only pose moves the cursor immediately.
                        elif action == "cursor":
                            scroll_candidate = None
                            safety.suppress_until_neutral()
                            if mode_manager.mode == ModeManager.MOUSE:
                                index_tip = hand_landmarks[8]
                                mouse.move_cursor(index_tip.x, index_tip.y)

                        elif zoom_action and mode_manager.mode == ModeManager.MOUSE:
                            scroll_candidate = None
                            safety.suppress_until_neutral()
                            zoom_name = (
                                "Pinça afastando — zoom +"
                                if zoom_action == "zoom_in"
                                else "Pinça aproximando — zoom −"
                            )
                            response = self._dispatch(
                                zoom_name,
                                zoom_action,
                                keyboard,
                                mouse,
                                now,
                                continuous=True,
                            )
                            self.status_changed.emit(f"{zoom_name}: {response}")

                        else:
                            motion = motion_recognizer.update(
                                hand_landmarks,
                                now,
                            )

                            if motion:
                                scroll_candidate = None
                                safety.suppress_until_neutral()
                                if mode_manager.mode == ModeManager.KEYBOARD:
                                    mapping_key = (
                                        "swipe_left"
                                        if motion.action == "page_back"
                                        else "swipe_right"
                                    )
                                    action_name = self.profile["mappings"][mapping_key]
                                    response = self._dispatch(
                                        motion.name,
                                        action_name,
                                        keyboard,
                                        mouse,
                                        now,
                                    )
                                    self.status_changed.emit(
                                        f"{motion.name}: {response}"
                                    )
                                else:
                                    self.status_changed.emit(
                                        "Deslize horizontal ignorado no modo Mouse."
                                    )

                            elif action in ("scroll_up", "scroll_down"):
                                if mode_manager.mode == ModeManager.MOUSE:
                                    safety.suppress_until_neutral()
                                    if action != scroll_candidate:
                                        scroll_candidate = action
                                        scroll_candidate_since = now

                                    stable_for = now - scroll_candidate_since
                                    repeat_elapsed = now - last_scroll_action_time
                                    repeat_interval = self.profile[
                                        "scroll_repeat_seconds"
                                    ]
                                    if (
                                        stable_for >= self.GESTURE_STABILITY_SECONDS
                                        and repeat_elapsed >= repeat_interval
                                    ):
                                        response = self._dispatch(
                                            detected.name,
                                            action,
                                            keyboard,
                                            mouse,
                                            now,
                                            continuous=True,
                                        )
                                        last_scroll_action_time = now
                                        self.status_changed.emit(
                                            f"{detected.name}: {response}"
                                        )
                                    else:
                                        remaining = max(
                                            0.0,
                                            self.GESTURE_STABILITY_SECONDS - stable_for,
                                        )
                                        self.status_changed.emit(
                                            f"{detected.name} — mantenha; "
                                            f"rolagem em {remaining:.1f}s"
                                        )
                                else:
                                    scroll_candidate = None
                                    safety.update(None, now)

                            elif action == "pinch":
                                scroll_candidate = None
                                safety.update(None, now)

                            elif (
                                mode_manager.mode == ModeManager.KEYBOARD
                                and action in ("enter", "esc")
                            ):
                                safety_key = (
                                    "thumb_up" if action == "enter" else "thumb_down"
                                )
                                mapped_action = self.profile["mappings"][safety_key]
                                confirmed = safety.update(detected, now)
                                if confirmed:
                                    response = self._dispatch(
                                        confirmed.name,
                                        mapped_action,
                                        keyboard,
                                        mouse,
                                        now,
                                    )
                                    self.status_changed.emit(
                                        f"{confirmed.name}: {response}"
                                    )
                                else:
                                    self.status_changed.emit(
                                        f"Candidato: {detected.name} — "
                                        f"estabilizando por "
                                        f"{self.GESTURE_STABILITY_SECONDS:.2f} s"
                                    )
                            else:
                                scroll_candidate = None
                                safety.update(None, now)

                    height, width = frame.shape[:2]
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = QImage(
                        rgb_frame.data,
                        width,
                        height,
                        3 * width,
                        QImage.Format.Format_RGB888,
                    ).copy()
                    self.frame_ready.emit(image)

        except Exception as exc:
            self.status_changed.emit(f"Falha no reconhecimento: {exc}")
        finally:
            try:
                self._record_mouse_event(click_drag.cancel())
            except Exception as exc:
                self.status_changed.emit(
                    f"Falha ao liberar o botão após arraste: {exc}"
                )
            cap.release()
            self.status_changed.emit("Câmera desligada.")
