"""Privux VPN desktop client; privilege is confined to the fixed backend."""
import json
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
    QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox, QPushButton,
    QVBoxLayout, QWidget)


class Request(QThread):
    def __init__(self, args, content=None):
        super().__init__()
        self.args, self.content = args, content

    def run(self):
        try:
            result = subprocess.run(['/usr/bin/pkexec', '/usr/lib/privux/vpn-helper', *self.args],
                                    input=self.content, capture_output=True, text=True, timeout=180)
            try:
                data = json.loads(result.stdout)
            except ValueError:
                data = {'error': 'Operació cancel·lada o autenticació fallida.'}
            self.data = data
        except (OSError, subprocess.TimeoutExpired):
            self.data = {'error': 'No es pot executar el servei VPN.'}


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Privux VPN · Orimpo')
        self.resize(540, 360)
        self.worker = None
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel('Privux VPN')
        title.setStyleSheet('font-size: 28px; font-weight: bold')
        layout.addWidget(title)
        layout.addWidget(QLabel('Connexió privada amb WireGuard'))
        self.state = QLabel('Prem Actualitzar per consultar l’estat.')
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self.profiles = QComboBox()
        layout.addWidget(self.profiles)
        row = QHBoxLayout()
        self.connect_button = QPushButton('Connectar')
        self.disconnect_button = QPushButton('Desconnectar')
        self.import_button = QPushButton('Importar .conf')
        for button in [self.connect_button, self.disconnect_button, self.import_button]:
            row.addWidget(button)
        layout.addLayout(row)
        self.kill = QCheckBox('Kill switch: bloquejar Internet fora de la VPN')
        layout.addWidget(self.kill)
        note = QLabel('Amb el kill switch actiu, desconnectar bloqueja Internet.\n'
                      'Desactiva’l explícitament per recuperar la connexió normal.\n'
                      'Els perfils requereixen IP de servidor numèrica i túnel complet.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.refresh = QPushButton('Actualitzar estat')
        layout.addWidget(self.refresh)
        self.setCentralWidget(widget)
        self.controls = [self.profiles, self.connect_button, self.disconnect_button,
                         self.import_button, self.kill, self.refresh]
        self.connect_button.clicked.connect(self.connect_vpn)
        self.disconnect_button.clicked.connect(lambda: self.request(['disconnect']))
        self.import_button.clicked.connect(self.import_vpn)
        self.kill.clicked.connect(lambda checked: self.request(['kill-switch', 'on' if checked else 'off']))
        self.refresh.clicked.connect(lambda: self.request(['status']))

    def request(self, args, content=None):
        for control in self.controls:
            control.setEnabled(False)
        self.state.setText('Autenticant i aplicant l’operació…')
        self.worker = Request(args, content)
        self.worker.finished.connect(lambda: self.result(self.worker.data))
        self.worker.start()

    def result(self, data):
        for control in self.controls:
            control.setEnabled(True)
        if 'error' in data:
            self.state.setText('Operació fallida. Actualitza per comprovar l’estat real.')
            QMessageBox.warning(self, 'Privux VPN', data['error'])
            return
        selected = self.profiles.currentText() or data.get('selected')
        self.profiles.clear()
        self.profiles.addItems(data['profiles'])
        if selected in data['profiles']:
            self.profiles.setCurrentText(selected)
        self.kill.setChecked(data['kill_switch'])
        age = data['handshake_age']
        if data['interface_up']:
            connection = 'Túnel actiu; resposta recent del servidor.' if age is not None and age < 180 else 'Túnel activat; falta confirmar resposta recent del servidor.'
        else:
            connection = 'VPN desconnectada.'
        protection = 'Trànsit fora del túnel bloquejat.' if data['kill_switch_active'] else 'Kill switch desactivat.'
        if data['kill_switch'] and not data['kill_switch_active']:
            protection = 'ATENCIÓ: el kill switch està configurat però no està aplicat.'
        self.state.setText(connection + '\n' + protection)

    def connect_vpn(self):
        if self.profiles.currentText():
            self.request(['connect', self.profiles.currentText()])
        else:
            QMessageBox.information(self, 'Privux VPN', 'Importa primer un perfil .conf.')

    def import_vpn(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Importar WireGuard', '', 'WireGuard (*.conf)')
        if not path:
            return
        name, ok = QInputDialog.getText(self, 'Nom del servidor', 'Nom del perfil:', text=Path(path).stem)
        if not ok:
            return
        try:
            with open(path, encoding='utf-8') as handle:
                content = handle.read(16385)
            from .vpn_config import parse
            parse(content)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Privux VPN', str(error))
            return
        self.request(['import', name], content)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
