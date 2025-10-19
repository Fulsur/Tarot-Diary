#the card displaying,the model choose，the answer,

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QLineEdit,QHBoxLayout, QMessageBox
import Tarot_PostgreSQL as tps
from PySide6.QtCore import Qt

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
            port="5432"         #         
        )
        # Initialize UI components
        self.main_window = None
        self.initUI()
        

    def initUI(self):
        # Set up the main layout and widgets here
        self.layout = QVBoxLayout()
        self.label = QLabel("Welcome to the Check In The Tarot Diary!")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 16px; font-weight: bold;")

        # Account input
        self.account_label = QLabel("Account:")
        self.account_label.setAlignment(Qt.AlignCenter)
        self.account_label.setStyleSheet("font-size: 14px;")
        self.account_input = QLineEdit()
        self.account_layout = QHBoxLayout()
        self.account_layout.addWidget(self.account_label)
        self.account_layout.addWidget(self.account_input)
        
        # Password input
        self.password_label = QLabel("Password:")
        self.password_label.setAlignment(Qt.AlignCenter)
        self.password_label.setStyleSheet("font-size: 14px;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_layout = QHBoxLayout()
        self.password_layout.addWidget(self.password_label)
        self.password_layout.addWidget(self.password_input)

        # Check-in button
        self.checkin_button = QPushButton("Check In")
        self.checkin_button.setStyleSheet("font-size: 14px;")
        self.checkin_button.clicked.connect(self.check_in)

        # Register button
        self.register_button = QPushButton("Register")
        self.register_button.setStyleSheet("font-size: 14px;")
        self.register_button.clicked.connect(self.show_register)

        # Add widgets to the layout
        self.layout.addWidget(self.label)
        self.layout.addLayout(self.account_layout)
        self.layout.addLayout(self.password_layout)
        self.layout.addWidget(self.checkin_button)
        self.layout.addWidget(self.register_button)
        #add background image


        # Set the central widget
        container = QWidget()
        container.setLayout(self.layout)
        self.window.setCentralWidget(container)
        if not self.db_manager.connect():
            QMessageBox.critical(self.window, "错误", "无法连接数据库，请检查数据库设置")

    def check_in(self):
        """登录验证"""
        self.username = self.account_input.text().strip()
        self.password = self.password_input.text().strip()

        if not self.username or not self.password:
            QMessageBox.warning(self.window, "输入错误", "请输入账号和密码")
            return
        
        # 验证用户
        user = self.db_manager.verify_user(self.username, self.password)
        
        if user:
            # 登录成功
            QMessageBox.information(self.window, "登录成功", f"欢迎回来，{user['username']}！")
            
            # 创建并显示主窗口
            self.main_window = MainWindow(user, self.db)
            self.main_window.show()
            self.window.hide()
        else:
            QMessageBox.warning(self.window, "登录失败", "用户名或密码错误")

    def show_register(self):
        """register function"""
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
    checkin_window = CheckIn()
    checkin_window.show()
    app.exec()