import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QSlider,
    QPushButton,
    QVBoxLayout,
    QRadioButton,
    QButtonGroup,
    QHBoxLayout,
    QTabWidget
)
from PySide6.QtGui import QPixmap,QIcon
from PySide6.QtWidgets import QLabel
import threading
import asyncio
from mobapadlib import Mobapad

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(
        base_path,
        relative_path
    )

class VibrationTab(QWidget):
    def __init__(self, family):
        self.ctl = None
        super().__init__()
        self.family = family
        self.left_radio = QRadioButton("Left")
        self.right_radio = QRadioButton("Right")
        self.left_image = QLabel()
        self.right_image = QLabel()
        layout = QVBoxLayout()

        # --------------------------
        # Controle
        # --------------------------

        self.controller_label = QLabel("Controller:")

        if family == "S1":
            left_image = resource_path("assets/ic_handle_front_s1_left.png")
            right_image = resource_path("assets/ic_handle_front_s1_right.png")
        elif family == "M6":
            left_image = resource_path("assets/ic_handle_front_m6_left.png")
            right_image = resource_path("assets/ic_handle_front_m6_right.png")
        else:
            raise RuntimeError(f"Unsupported family: {family}")
        left_pixmap = QPixmap(left_image)
        right_pixmap = QPixmap(right_image)
        self.left_image.setPixmap(left_pixmap.scaled(400,400,Qt.KeepAspectRatio))
        self.right_image.setPixmap(right_pixmap.scaled(400,400,Qt.KeepAspectRatio))

        self.left_radio.setChecked(True)
        self.group = QButtonGroup()
        self.group.addButton(self.left_radio)
        self.group.addButton(self.right_radio)
        # --------------------------
        # Vibração
        # --------------------------
        self.vibration_label = QLabel("Vibration: --")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setFixedWidth(500)
        self.slider.setMinimum(13)
        self.slider.setMaximum(204)
        self.slider.setValue(13)
        self.slider.valueChanged.connect(self.update_vibration_label)

        # --------------------------
        # Botões
        # --------------------------
        self.read_button = QPushButton("Read")
        self.apply_button = QPushButton("Apply")
        self.off_button = QPushButton("OFF")
        self.read_button.setFixedWidth(120)
        self.apply_button.setFixedWidth(120)
        self.off_button.setFixedWidth(120)
        # --------------------------
        # Status
        # --------------------------
        self.status_label = QLabel("")
        # --------------------------
        # Layout
        # --------------------------
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.left_image,alignment=Qt.AlignCenter)
        left_layout.addWidget(self.left_radio,alignment=Qt.AlignCenter)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.right_image,alignment=Qt.AlignCenter)
        right_layout.addWidget(self.right_radio,alignment=Qt.AlignCenter)
        slider_layout = QHBoxLayout()
        slider_layout.addStretch()
        slider_layout.addWidget(self.slider)
        slider_layout.addStretch()
        controller_layout = QHBoxLayout()
        controller_layout.addLayout(left_layout)
        controller_layout.addLayout(right_layout)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.read_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.off_button)
        button_layout.addStretch()
        #layout.addWidget(self.controller_label)
        layout.addLayout(controller_layout)
        layout.addWidget(self.vibration_label)
        layout.addLayout(slider_layout)
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.read_button.clicked.connect(self.read_vibration)
        self.apply_button.clicked.connect(self.apply_vibration)
        self.off_button.clicked.connect(self.turn_off_vibration)
        self.left_image.setAlignment(Qt.AlignCenter)
        self.right_image.setAlignment(Qt.AlignCenter)
        self.vibration_label.setAlignment(Qt.AlignCenter)
        self.set_controls_enabled(general=True, apply=False)

    def update_vibration_label(self,value):
        self.vibration_label.setText(f"Vibration: {value}")
        self.set_controls_enabled(general=True, apply=True)


    def read_vibration(self):
        threading.Thread(
            target=lambda: asyncio.run(
                self.do_read_vibration()
            ),
            daemon=True
        ).start()

    async def do_read_vibration(self):
        self.update_vibration_label("--")
        self.set_controls_enabled(general=False, apply=False)
        device_name = "device"
        try:
            self.set_status(f"[Connecting...] Reading vibration level of {device_name}")
            if self.right_radio.isChecked():
                self.ctl = await Mobapad.connect_right(self.family)
            else:
                self.ctl = await Mobapad.connect_left(self.family)
            device_name = self.ctl.device_name
            self.set_status(f"[Connected] Reading vibration level of {device_name}")

            motor = await self.ctl.get_motor()
            if (motor.motor1 == 0 and motor.motor2 == 0):
                value = 0
                self.slider.setValue(value)
                self.vibration_label.setText("Vibration: OFF")
                self.set_controls_enabled(general=True, apply=False)
            else:
                if self.right_radio.isChecked():
                    value = motor.motor2
                else:
                    value = motor.motor1
                self.slider.setValue(value)
                self.update_vibration_label(value)
                print(f"{device_name} vibration level: {value}")
                self.set_controls_enabled(general=True, apply=True)
            self.set_status(f"[DONE] Reading vibration level of {device_name}: {value}")
            await self.ctl.disconnect()
            
        except Exception as ex:
            print(ex)
            self.set_status(f"[ERROR] No connection to {device_name}, verify if controller is turned on and disconnected from other app]")
            self.set_controls_enabled(general=True, apply=False)

    def apply_vibration(self):
        threading.Thread(
            target=lambda: asyncio.run(
                self.do_apply_vibration()
            ),
            daemon=True
        ).start()

    async def do_apply_vibration(self):
        self.set_controls_enabled(general=False, apply=False)
        device_name = "device"
        value = self.slider.value()
        try:
            self.set_status(f"[Connecting...] Applying vibration level to {device_name}")
            if self.right_radio.isChecked():
                ctl = await Mobapad.connect_right(self.family)
            else:
                ctl = await Mobapad.connect_left(self.family)
            device_name = ctl.device_name
            self.set_status(f"[Connected] Applying vibration level to {device_name}")
            await ctl.set_vibration(value)
            self.set_status(f"[DONE] Applying vibration level to {device_name}: {value}")
            await ctl.disconnect()
            self.update_vibration_label(value)
            self.set_controls_enabled(general=True, apply=True)
        except Exception as ex:
            print(ex)
            self.set_status(f"[ERROR] No connection to {device_name}, verify if controller is turned on and disconnected from other app]")
            self.set_controls_enabled(general=True, apply=True)

    def turn_off_vibration(self):
        threading.Thread(
            target=lambda: asyncio.run(
                self.do_turn_off_vibration()
            ),
            daemon=True
        ).start()

    async def do_turn_off_vibration(self):
        self.set_controls_enabled(general=False, apply=False)
        device_name = "device"
        try:
            self.set_status(f"[Connecting...] Turning OFF vibration on {device_name}")
            if self.right_radio.isChecked():
                ctl = await Mobapad.connect_right(self.family)
            else:
                ctl = await Mobapad.connect_left(self.family)
            device_name = ctl.device_name
            self.set_status(f"[Connected] Turning OFF vibration on {device_name}")
            await ctl.set_motor(
                motor1=0,
                motor2=0,
                motor3=0,
                motor4=0
            )
            self.set_status(f"[DONE] Vibration OFF on {device_name}")
            await ctl.disconnect()
            self.update_vibration_label(0)
            self.slider.setValue(0)
            self.set_controls_enabled(general=True, apply=False)
            self.vibration_label.setText("Vibration: OFF")
        except Exception as ex:
            print(ex)
            self.set_status(f"[ERROR] No connection to {device_name}, verify if controller is turned on and disconnected from other app]")
            self.set_controls_enabled(general=True, apply=False)


    def set_status(self,text):
        self.status_label.setText(f"{text}")

    def set_controls_enabled(self,general=True,apply=True):
        self.read_button.setEnabled(general)
        self.left_radio.setEnabled(general)
        self.right_radio.setEnabled(general)
        self.slider.setEnabled(general)
        self.off_button.setEnabled(general)
        self.apply_button.setEnabled(apply)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 150px;
                min-height: 35px;
                font-size: 12pt;
            }
            QTabBar::tab:selected {
                font-weight: bold;
            }
        """)
        self.tab_s1 = VibrationTab("S1")
        self.tab_m6 = VibrationTab("M6")
        self.tabs.addTab(self.tab_s1,"S1")
        self.tabs.addTab(self.tab_m6,"M6")
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setWindowTitle("Mobapad vibration tool")
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
        self.resize(720, 620)
        self.setFixedSize(720, 620)

app = QApplication([])
app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
window = MainWindow()

window.show()

app.exec()