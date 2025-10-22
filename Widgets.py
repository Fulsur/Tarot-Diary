#the card displaying,the model choose，the answer,

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QLineEdit,QHBoxLayout,
                                QMessageBox,QInputDialog, QDialog, QGroupBox, QFormLayout,QCheckBox, QProgressBar,QComboBox)
import Tarot_PostgreSQL as tps
from PySide6.QtCore import Qt, QTimer
import psycopg2
import config_manager as cmg

class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First Run Setup")
        self.setGeometry(150, 150, 400, 300)
        self.config_manager = cmg.SecureConfigManager()

        self.db_config = {}
        self.initUI()
    
    def initUI(self):
        # Set up the main layout and widgets here
        #title
        title_label = QLabel("Welcome to Tarot Diary First Run Setup")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        # Database Configuration
        db_group = QGroupBox("Database Configuration")
        db_layout = QFormLayout(db_group)

        # Host
        self.host_input = QLineEdit('localhost')
        self.host_input.setPlaceholderText("e.g., localhost")
        db_layout.addRow("Host:", self.host_input)

        # Port
        self.port_input = QLineEdit('5432')
        self.port_input.setPlaceholderText("e.g., 5432")
        db_layout.addRow("Port:", self.port_input)

        # Database Name
        self.dbname_input = QLineEdit('tarot_diary')
        self.dbname_input.setPlaceholderText("e.g., tarot_diary")
        db_layout.addRow("Database Name:", self.dbname_input)

        # User
        self.user_input = QLineEdit('your_username')
        self.user_input.setPlaceholderText("e.g., your_username")
        db_layout.addRow("User:", self.user_input)

        # Password
        self.password_input = QLineEdit('your_password')
        self.password_input.setEchoMode(QLineEdit.Password)
        db_layout.addRow("Password:", self.password_input)

        # Test Database Connection
        test_group = QGroupBox("Test Database Connection")
        test_layout = QVBoxLayout(test_group)

        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)

        self.test_result = QLabel("点击'测试连接'验证数据库连接")
        self.test_result.setWordWrap(True)
        test_layout.addWidget(self.test_result)

        # 数据库初始化选项
        init_group = QGroupBox("数据库初始化")
        init_layout = QVBoxLayout(init_group)
        
        self.auto_init_check = QCheckBox("自动创建所需的数据库表")
        self.auto_init_check.setChecked(True)
        init_layout.addWidget(self.auto_init_check)
        
        init_note = QLabel("如果数据库是空的，这将自动创建用户表和塔罗牌记录表")
        init_note.setWordWrap(True)
        init_note.setStyleSheet("color: #666; font-size: 12px;")
        init_layout.addWidget(init_note)
        
        # 进度条（初始化时显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.finish_button = QPushButton("完成并保存")
        self.finish_button.clicked.connect(self.finish_setup)
        self.finish_button.setEnabled(False)
        self.finish_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.finish_button)
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(title_label)
        self.layout.addWidget(db_group)
        self.layout.addWidget(test_group)
        self.layout.addWidget(init_group)
        self.layout.addWidget(self.progress_bar)
        self.layout.addLayout(button_layout)
    
    def get_connection_config(self):
        """获取连接配置"""
        return {
            'host': self.host_input.text().strip(),
            'port': self.port_input.text().strip(),
            'dbname': self.dbname_input.text().strip(),
            'user': self.user_input.text().strip(),
            'password': self.password_input.text().strip()
        }
    
    def test_connection(self):
        """测试数据库连接"""
        config = self.get_connection_config()
        
        # 验证输入
        if not all([config['host'], config['port'], config['dbname'], config['user']]):
            self.test_result.setText("❌ 请填写所有必填字段")
            return
        
        # 验证端口号
        try:
            port = int(config['port'])
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            self.test_result.setText("❌ 端口号必须是 1-65535 之间的数字")
            return
        
        self.test_button.setEnabled(False)
        self.test_result.setText("正在测试连接...")
        
        # 使用定时器避免界面冻结
        QTimer.singleShot(100, lambda: self._perform_connection_test(config))
    
    def _perform_connection_test(self, config):
        """执行实际的连接测试"""
        try:
            # 测试连接
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            # 测试基本查询
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # 检查数据库是否包含我们的表
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                );
            """)
            has_tables = cursor.fetchone()[0]
            
            conn.close()
            
            # 更新界面
            self.test_result.setText(
                f"✅ 连接成功！\n"
                f"PostgreSQL 版本: {version.split(',')[0]}\n"
                f"数据库表状态: {'已存在' if has_tables else '需要初始化'}"
            )
            self.finish_button.setEnabled(True)
            self.db_config = config
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "password authentication" in error_msg:
                self.test_result.setText("❌ 认证失败：用户名或密码错误")
            elif "does not exist" in error_msg:
                self.test_result.setText("❌ 数据库不存在")
            elif "Connection refused" in error_msg:
                self.test_result.setText("❌ 连接被拒绝：请检查主机和端口")
            else:
                self.test_result.setText(f"❌ 连接失败: {error_msg}")
        except Exception as e:
            self.test_result.setText(f"❌ 未知错误: {e}")
        finally:
            self.test_button.setEnabled(True)
    
    def finish_setup(self):
        """完成设置"""
        if not self.db_config:
            QMessageBox.warning(self, "错误", "请先测试连接并确保连接成功")
            return
        
        # 保存配置
        if not self.config_manager.save_database_config(self.db_config):
            QMessageBox.critical(self, "错误", "保存数据库配置失败")
            return
        
        # 如果需要，初始化数据库
        if self.auto_init_check.isChecked():
            self.initialize_database()
        else:
            QMessageBox.information(self, "设置完成", 
                                  "数据库配置已保存！\n"
                                  "您现在可以使用塔罗牌日记了。")
            self.accept()
    
    def initialize_database(self):
        """初始化数据库表"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        
        # 禁用按钮
        self.finish_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        QTimer.singleShot(100, self._perform_database_init)
    
    def _perform_database_init(self):
        """执行数据库初始化"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 创建表
            tables = [
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS tarot_readings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    spread_type VARCHAR(50) NOT NULL,
                    question TEXT,
                    reading_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS reading_cards (
                    id SERIAL PRIMARY KEY,
                    reading_id INTEGER NOT NULL REFERENCES tarot_readings(id) ON DELETE CASCADE,
                    card_name VARCHAR(100) NOT NULL,
                    position VARCHAR(50),
                    orientation VARCHAR(10) DEFAULT 'upright',
                    interpretation TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    language VARCHAR(10) DEFAULT 'zh_CN',
                    theme VARCHAR(20) DEFAULT 'light',
                    notification_enabled BOOLEAN DEFAULT TRUE
                )
                """
            ]
            
            for i, table_sql in enumerate(tables, 1):
                cursor.execute(table_sql)
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "设置完成", 
                                  "✅ 数据库配置已保存！\n"
                                  "✅ 数据库表初始化完成！\n\n"
                                  "您现在可以使用塔罗牌日记了。")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "初始化失败", 
                               f"数据库表初始化失败:\n{str(e)}\n\n"
                               "配置已保存，但您需要手动创建数据库表。")
            self.accept()

class CheckIn():
    def __init__(self, db_config):
        self.window = QMainWindow()
        self.window.setWindowTitle("Check In")
        self.window.setGeometry(100, 100, 400, 300)
        self.db_manager = tps.TarotPostgreSQLManager(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port']
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

        self.db_manager.initialize_database()

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
            self.main_window = MainWindow(user, self.db_manager)
            self.main_window.show()
            self.window.hide()
        else:
            QMessageBox.warning(self.window, "登录失败", "用户名或密码错误")

    def show_register(self):
        self.new_username, ok = QInputDialog.getText(self.window, "注册新账号", "请输入用户名:")
        if ok and self.new_username:
            password, ok = QInputDialog.getText(self.window, "注册新账号", "请输入密码:", QLineEdit.Password)
            if ok and password:
                email, ok = QInputDialog.getText(self.window, "注册新账号", "请输入邮箱（可选）:")
                if ok:
                    # 创建新用户
                    user_id = self.db_manager.create_user(self.new_username, password, email if email else None)
                    if user_id:
                        QMessageBox.information(self.window, "注册成功", f"用户 {self.new_username} 创建成功！")
                        # 自动填充登录表单
                        self.account_input.setText(self.new_username)
                        self.password_input.setText("")
                    else:
                        QMessageBox.warning(self.window, "注册失败", "用户名可能已存在")
        pass

    def show(self):
        self.window.show()
        
class MainWindow():
    def __init__(self, user, db_manager):
        self.window = QMainWindow()
        self.window.setWindowTitle("My Tarot Diary")
        self.window.setGeometry(100, 100, 800, 600)
        self.window.resize(1440, 900)
        # Initialize UI components
        self.initUI()

    def initUI(self):
        # Set up the main layout and widgets here
        add_new_question_button = QPushButton("Tarot Reading")
        add_new_question_button.setStyleSheet("font-size: 14px;")
        add_new_question_button.clicked.connect(self.add_new_question)

        add_new_spreads_button = QPushButton("Add New Spreads")
        add_new_spreads_button.setStyleSheet("font-size: 14px;")
        add_new_spreads_button.clicked.connect(self.add_new_spreads)
        get_spreads_button = QPushButton("Get Spreads")
        get_spreads_button.setStyleSheet("font-size: 14px;")
        get_spreads_button.clicked.connect(self.get_spreads)
        spreads_layout = QHBoxLayout()
        spreads_layout.addWidget(add_new_spreads_button)
        spreads_layout.addWidget(get_spreads_button)

        get_cards_button = QPushButton("Get Cards")
        get_cards_button.setStyleSheet("font-size: 14px;")
        get_cards_button.clicked.connect(self.get_cards)

        get_history_readings_button = QPushButton("Get History Readings")
        get_history_readings_button.setStyleSheet("font-size: 14px;")
        get_history_readings_button.clicked.connect(self.get_history_readings)

        self.layout = QVBoxLayout()
        self.layout.addWidget(add_new_question_button)
        self.layout.addLayout(spreads_layout)
        self.layout.addWidget(get_cards_button)
        self.layout.addWidget(get_history_readings_button)

    def tarot_reading(self):
        pass

    def add_new_spreads(self):
        pass

    def get_spreads(self):
        pass

    def get_cards(self):
        pass

    def get_history_readings(self):
        pass

    def show(self):
        self.window.show()

class TarotReadingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tarot Reading")
        self.setGeometry(100, 100, 400, 300)
        self.initUI()

    def initUI(self):
        self.choose_spread = QComboBox()
        self.choose_spread.addItems(["Spread 1", "Spread 2", "Spread 3"])

        self.choose_spreadbackground = QComboBox()
        self.choose_spreadbackground.addItems(["Background 1", "Background 2", "Background 3"])

        self.show_spread_button = QPushButton("Show Spread")
        self.show_spread_button.clicked.connect(self.show_spread)

        self.record_question_text = QLineEdit()
        self.record_question_text.setPlaceholderText("Enter your question here")

        self.spread_reading_text = QLineEdit()
        self.spread_reading_text.setPlaceholderText("Enter your reading here")
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.choose_spread)
        self.layout.addWidget(self.choose_spreadbackground)
        self.layout.addWidget(self.show_spread_button)
        self.layout.addWidget(self.record_question_text)
        self.layout.addWidget(self.spread_reading_text)

    def show_spread(self):
        
        pass

if __name__ == "__main__":
    app = QApplication([])
    checkin_window = CheckIn()
    checkin_window.show()
    app.exec()