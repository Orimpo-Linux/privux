from PySide6.QtWidgets import QApplication
from privux.vpn_gui import Window

app = QApplication([])
window = Window()
window.result({'profiles': ['lab'], 'selected': 'lab', 'kill_switch': True,
               'kill_switch_active': True, 'interface_up': False, 'handshake_age': None})
assert window.profiles.currentText() == 'lab'
assert window.kill.isChecked()
assert 'bloquejat' in window.state.text()
window.result({'profiles': ['lab'], 'selected': 'lab', 'kill_switch': False,
               'kill_switch_active': False, 'interface_up': True, 'handshake_age': 0})
assert 'resposta recent' in window.state.text()
window.show()
app.processEvents()
window.grab().save('vpn-preview.png')
print('PASS: desktop controls and real state rendering')
