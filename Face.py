#the card displaying,the model choose，the answer,

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget

class CheckIn:
    def __init__(self):
        self.window = QMainWindow()
        self.window.setWindowTitle("Check In")
        self.window.setGeometry(100, 100, 400, 300)
        # Initialize UI components
        self.initUI()
        self.check_in()

    def initUI(self):
        # Set up the main layout and widgets here
        self.layout = QVBoxLayout()
        self.label = QLabel("Welcome to the Check In The Tarot Diary!")
        #add background image

    def check_in(self):

        pass

    def show(self):
        self.window.show()
class MainWindow:
    def __init__(self):
        self.window = QMainWindow()
        self.window.setWindowTitle("My Tarot Diary")
        self.window.setGeometry(100, 100, 800, 600)
        self.window.resize(1440, 900)
        # Initialize UI components
        self.initUI()

    def initUI(self):
        # Set up the main layout and widgets here

        pass

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QApplication([])
    main_window = CheckIn()
    main_window.show()
    app.exec()