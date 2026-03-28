'''
import sys
from io import StringIO

class RedirectedStdout:
    def __init__(self):
        self._stdout = None
        self._string_io = None

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._string_io = StringIO()
        return self

    def __exit__(self, type, value, traceback):
        sys.stdout = self._stdout

    def __str__(self):
        return self._string_io.getvalue()

with RedirectedStdout() as out:
    print('asdf')
    s = str(out)
    print('bsdf')
    print(s, out)
    'asdf\n' 'asdf\nbsdf\n'
'''

import sys
from PyQt5 import QtGui

class OutputWindow():
    def write(self, txt):
        self.appendPlainText(str(txt))

app = QtGui.QGuiApplication(sys.argv)
out = OutputWindow()


out.show()
print("hello world !")
