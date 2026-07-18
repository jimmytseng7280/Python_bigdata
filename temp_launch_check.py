import importlib.util
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

spec = importlib.util.spec_from_file_location('stock10', '07_04/stock10.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication.instance() or QApplication([])
win = mod.CorrelationApp()
win.show()
app.processEvents()
QTimer.singleShot(1000, app.quit)
app.exec()
print('launch-ok', flush=True)
sys.exit(0)
