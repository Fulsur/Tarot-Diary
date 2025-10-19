#the card displaying,the model choose，the answer,

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QLineEdit,QHBoxLayout
import Tarot_PostgreSQL as tps

class CheckIn:
    def __init__(self):
        self.window = QMainWindow()
        self.window.setWindowTitle("Check In")
        self.window.setGeometry(100, 100, 400, 300)
        self.db_manager = tps.TarotPostgreSQLManager(
            dbname="tarot_diary", 
            user="your_user",       #replace with actual username
            password="your_password",       #replace with actual password   
            host="localhost",
            port="5432"
        )
        # Initialize UI components
        self.initUI()
        

    def initUI(self):
        # Set up the main layout and widgets here
        self.layout = QVBoxLayout()
        self.label = QLabel("Welcome to the Check In The Tarot Diary!")

        self.account_label = QLabel("Account:")
        self.account_input = QLineEdit()
        self.account_layout = QHBoxLayout()
        self.account_layout.addWidget(self.account_label)
        self.account_layout.addWidget(self.account_input)
        
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_layout = QHBoxLayout()
        self.password_layout.addWidget(self.password_label)
        self.password_layout.addWidget(self.password_input)

        self.checkin_button = QPushButton("Check In")
        self.checkin_button.clicked.connect(self.check_in)
        self.layout.addWidget(self.label)
        self.layout.addLayout(self.account_layout)
        self.layout.addLayout(self.password_layout)
        self.layout.addWidget(self.checkin_button)
        container = QWidget()
        container.setLayout(self.layout)
        self.window.setCentralWidget(container)
        #add background image

    def check_in(self):
        """check in function"""
        pass
        self.main_window = MainWindow()
        self.main_window.show()                  #未知原因闪退:未设置为类的实例对象会
        self.window.hide()

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
    checkin_window = CheckIn()
    checkin_window.show()
    app.exec()