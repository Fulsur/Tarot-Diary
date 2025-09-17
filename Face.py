#the card displaying,the model choose，the answer,

import PySide6

class MainWindow:
    def __init__(self):
        self.window = PySide6.QtWidgets.QMainWindow()
        self.window.setWindowTitle("Face Recognition System")
        self.window.setGeometry(100, 100, 800, 600)

        # Initialize UI components
        self.initUI()

    def initUI(self):
        # Set up the main layout and widgets here
        pass

    def show(self):
        self.window.show()