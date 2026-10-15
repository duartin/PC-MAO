"""Dedicated PySide6 user interface for the hand-gesture application."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .camera_worker import CameraWorker


class MainWindow(QMainWindow):
    def __init__(self, camera_index=0, motion_sensitivity=1.0,
                 execute_default=False):
        super().__init__()
        self.camera_index = camera_index
        self.motion_sensitivity = motion_sensitivity
        self.worker = None
        self.setWindowTitle("Controle do computador por gestos")
        self.resize(1120, 720)
        self._build_ui(execute_default)
        self._apply_style()
        self._update_mode_label("mouse")

    def _build_ui(self, execute_default):
        root = QWidget()
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(18, 18, 18, 18)
        page.setSpacing(12)

        title = QLabel("Controle por gestos")
        title.setObjectName("title")
        subtitle = QLabel(
            "Processamento local da webcam • sem gravação de vídeo"
        )
        subtitle.setObjectName("subtitle")
        page.addWidget(title)
        page.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(14)
        page.addLayout(body, 1)

        self.video = QLabel("Câmera desligada")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(600, 420)
        self.video.setObjectName("video")
        body.addWidget(self.video, 3)

        side = QVBoxLayout()
        body.addLayout(side, 2)
        side.addWidget(QLabel("MODO ATIVO"))
        self.mode_label = QLabel("Mouse — rolagem e zoom por pinça")
        self.mode_label.setWordWrap(True)
        self.mode_label.setObjectName("mode")
        side.addWidget(self.mode_label)

        side.addWidget(QLabel("STATUS"))
        self.status = QLabel("Pronto. Inicie a câmera para começar.")
        self.status.setWordWrap(True)
        self.status.setObjectName("status")
        side.addWidget(self.status)

        self.execute_checkbox = QCheckBox(
            "Executar ações reais no computador"
        )
        self.execute_checkbox.setChecked(execute_default)
        side.addWidget(self.execute_checkbox)
        safety_note = QLabel(
            "Desmarcado = modo de teste. Marque para permitir atalhos, "
            "cursor, rolagem e zoom reais."
        )
        safety_note.setWordWrap(True)
        safety_note.setObjectName("note")
        side.addWidget(safety_note)

        side.addWidget(QLabel("Sensibilidade dos deslizes horizontais"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(5, 20)
        self.sensitivity_slider.setValue(
            round(self.motion_sensitivity * 10)
        )
        self.sensitivity_value = QLabel(
            f"{self.motion_sensitivity:.1f}"
        )
        self.sensitivity_slider.valueChanged.connect(
            self._update_sensitivity_label
        )
        side.addWidget(self.sensitivity_slider)
        side.addWidget(self.sensitivity_value)

        side.addWidget(QLabel("HISTÓRICO DE AÇÕES"))
        self.history = QListWidget()
        self.history.setObjectName("history")
        side.addWidget(self.history, 1)
        self.clear_history_button = QPushButton("Limpar histórico")
        self.clear_history_button.clicked.connect(self.history.clear)
        side.addWidget(self.clear_history_button)

        controls = QHBoxLayout()
        page.addLayout(controls)
        self.start_button = QPushButton("Iniciar câmera")
        self.start_button.clicked.connect(self.start_camera)
        self.pause_button = QPushButton("Pausar")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button = QPushButton("Parar câmera")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_camera)
        controls.addWidget(self.start_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)

        footer = QLabel(
            "Para Atalhos: mão aberta → punho → mão aberta. "
            "Para Mouse: punho → mão aberta → punho → mão aberta. "
            "Cada pose é reconhecida após 0,25 s; conclua a sequência "
            "rapidamente. No modo Mouse, a ponta do indicador move o cursor "
            "sem espera; a pinça controla o zoom. A rolagem também inicia "
            "após 0,25 s. Os 1,5 s são intervalo entre ações pontuais."
        )
        footer.setWordWrap(True)
        footer.setObjectName("note")
        page.addWidget(footer)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111827; color: #e5e7eb; font-size: 14px; }
            QLabel#title { font-size: 26px; font-weight: 700; color: #f9fafb; }
            QLabel#subtitle, QLabel#note { color: #9ca3af; }
            QLabel#video { background: #030712; border: 1px solid #374151; border-radius: 12px; }
            QLabel#status { background: #1f2937; padding: 12px; border-radius: 8px; }
            QLabel#mode { background: #173b31; color: #86efac; padding: 12px; border-radius: 8px; font-weight: 700; }
            QListWidget { background: #0b1220; border: 1px solid #374151; border-radius: 8px; }
            QPushButton { background: #2563eb; border: 0; border-radius: 7px; padding: 10px 16px; }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #374151; color: #9ca3af; }
            QCheckBox { padding: 8px 0; font-weight: 600; }
            QSlider::groove:horizontal { height: 6px; background: #374151; border-radius: 3px; }
            QSlider::handle:horizontal { background: #60a5fa; width: 14px; margin: -5px 0; border-radius: 7px; }
        """)

    def _update_sensitivity_label(self, value):
        self.sensitivity_value.setText(f"{value / 10:.1f}")

    def _update_mode_label(self, mode):
        if mode == "keyboard":
            self.mode_label.setText(
                "ATALHOS — Enter/Esc e navegação horizontal"
            )
        elif mode == "mouse":
            self.mode_label.setText(
                "MOUSE — cursor pelo indicador, rolagem e zoom por pinça"
            )
        else:
            self.mode_label.setText(
                "Câmera parada — o próximo início selecionará Mouse"
            )

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self._update_mode_label("mouse")
        sensitivity = self.sensitivity_slider.value() / 10
        self.worker = CameraWorker(
            camera_index=self.camera_index,
            execute=self.execute_checkbox.isChecked(),
            motion_sensitivity=sensitivity,
            parent=self,
        )
        self.worker.frame_ready.connect(self._show_frame)
        self.worker.status_changed.connect(self.status.setText)
        self.worker.action_recorded.connect(self._add_history)
        self.worker.mode_changed.connect(self._update_mode_label)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.execute_checkbox.setEnabled(False)
        self.sensitivity_slider.setEnabled(False)
        self.pause_button.setText("Pausar")

    def stop_camera(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Encerrando câmera...")
            self.worker.requestInterruption()
            self.worker.wait(3000)
        self._worker_finished()

    def toggle_pause(self):
        if self.worker is None or not self.worker.isRunning():
            return
        paused = self.pause_button.text() == "Pausar"
        self.worker.set_paused(paused)
        self.pause_button.setText("Retomar" if paused else "Pausar")
        self.status.setText(
            "Reconhecimento pausado."
            if paused
            else "Reconhecimento retomado."
        )

    def _show_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video.setPixmap(
            pixmap.scaled(
                self.video.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _add_history(self, timestamp, gesture, action):
        self.history.insertItem(
            0,
            f"{timestamp}  |  {gesture}  →  {action}",
        )
        while self.history.count() > 200:
            self.history.takeItem(self.history.count() - 1)

    def _worker_finished(self):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.execute_checkbox.setEnabled(True)
        self.sensitivity_slider.setEnabled(True)
        self.pause_button.setText("Pausar")
        self.video.clear()
        self.video.setText("Câmera desligada")
        self._update_mode_label(None)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(3000)
        event.accept()


def launch(camera_index=0, motion_sensitivity=1.0, execute_default=False):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(camera_index, motion_sensitivity, execute_default)
    window.show()
    return app.exec()
