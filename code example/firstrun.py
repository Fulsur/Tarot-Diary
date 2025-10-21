# first_run_wizard.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QPushButton, QLabel, QMessageBox, 
                               QCheckBox, QGroupBox, QTextEdit, QProgressBar, QApplication)
from PySide6.QtCore import Qt, QTimer
import psycopg2
import sys,os
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # directory of the bundled app
else:
    base_path = os.path.abspath(os.path.dirname(__file__))  # 开发环境下的脚本所在目录     
sys.path.append(os.path.join(base_path, ".."))          # add parent directory to sys.path
from config_manager import SecureConfigManager

class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = SecureConfigManager()
        self.setWindowTitle("首次设置 - 塔罗牌日记")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        self.db_config = {}
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("欢迎使用塔罗牌日记")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 20px;")
        layout.addWidget(title_label)
        
        # 说明文本
        description = QLabel(
            "这是您第一次使用塔罗牌日记。\n"
            "请提供 PostgreSQL 数据库连接信息，软件将保存这些信息以便下次自动连接。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px;")
        layout.addWidget(description)
        
        # 数据库连接信息组
        db_group = QGroupBox("数据库连接信息")
        db_layout = QFormLayout(db_group)
        
        # 主机
        self.host_input = QLineEdit("localhost")
        self.host_input.setPlaceholderText("例如: localhost 或 192.168.1.100")
        db_layout.addRow("主机:", self.host_input)
        
        # 端口
        self.port_input = QLineEdit("5432")
        self.port_input.setPlaceholderText("默认: 5432")
        db_layout.addRow("端口:", self.port_input)
        
        # 数据库名
        self.dbname_input = QLineEdit("tarot_diary")
        self.dbname_input.setPlaceholderText("数据库名称")
        db_layout.addRow("数据库名:", self.dbname_input)
        
        # 用户名
        self.user_input = QLineEdit("postgres")
        self.user_input.setPlaceholderText("PostgreSQL 用户名")
        db_layout.addRow("用户名:", self.user_input)
        
        # 密码
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("PostgreSQL 密码")
        db_layout.addRow("密码:", self.password_input)
        
        layout.addWidget(db_group)
        
        # 测试连接区域
        test_group = QGroupBox("连接测试")
        test_layout = QVBoxLayout(test_group)
        
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)
        
        self.test_result = QLabel("点击'测试连接'验证数据库连接")
        self.test_result.setWordWrap(True)
        test_layout.addWidget(self.test_result)
        
        layout.addWidget(test_group)
        
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
        
        layout.addWidget(init_group)
        
        # 进度条（初始化时显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
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
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = FirstRunWizard()
    if wizard.exec() == QDialog.Accepted:
        print("首次设置完成，应用程序可以继续运行。")
    sys.exit(0)