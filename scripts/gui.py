# here is where we will create the GUI (using Qt)

# imports
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment
from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QLineEdit, QDockWidget, QTextEdit
import sys

# instantiation
app = QApplication(sys.argv)

# create the text entering widget
class TextEnter(QLineEdit):
    def __init__(self):
        super().__init__()

# create the text out widget
class TextOut(QTextEdit):
    def __init__(self):
        super().__init__()

        self.setReadOnly(True)

# create the wrapper for the text enter widget
class TextEnterWrapper(QDockWidget):
    def __init__(self, editor):
        super().__init__()

        self.editor = editor

        self.setWidget(editor)

        self.setFeatures(self.DockWidgetFeature.NoDockWidgetFeatures)

textbox = TextEnter()
output = TextOut()
textboxWrapper = TextEnterWrapper(textbox)

# create the window
class MainWindow(QMainWindow):
    def __init__(self, textbox, output):
        super().__init__()

        self.textbox = textbox
        self.editor = textbox.editor
        self.output = output
        self.setCentralWidget(output)
        self.setWindowTitle("Pocket Lawyer")
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.textbox)
        self.resize(1000, 500)

        # create the terminal connection
        self.readT = QProcess(self)
        self.readT.readyReadStandardOutput.connect(self.read)
        self.readT.readyReadStandardError.connect(self.readErr)

        # begin the process
        self.startAskLawyer()

        # set up the interaction
        self.editor.returnPressed.connect(self.writeToLawyer)

    # define the read function
    def read(self):
        data = self.readT.readAllStandardOutput()
        stdout = bytes(data).decode("utf-8", errors = "replace")
        # print it
        output.insertPlainText(stdout)
        # output.verticalScrollBar.setValue(output.verticalScrollBar.maximum())

    # debug
    def readErr(self):
        data = self.readT.readAllStandardError()
        stdout = bytes(data).decode("utf-8")
        # print it
        output.append(stdout)

    # define the start function
    def startAskLawyer(self):

        # safety for making sure the environment is the same
        command = sys.executable
        arguments = ["-u", "./scripts/AskQwenStream.py"]

        print(command, arguments)
        self.readT.setWorkingDirectory("/mnt/nvme0n1/database")

        # attempted fix for AI not running
        self.readT.setProcessEnvironment(QProcessEnvironment.systemEnvironment())

        self.readT.start(command, arguments)

    # write the input
    def writeToLawyer(self):

        prompt = self.editor.text()
        self.editor.clear()
        self.output.append(prompt)
        self.output.append("")
        self.readT.write((prompt + "\n").encode("utf-8"))


window = MainWindow(textboxWrapper, output)
window.show()

app.exec()
