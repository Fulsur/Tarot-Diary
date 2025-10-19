import psycopg2
from psycopg2 import sql
from datetime import datetime
import hashlib
import secrets

class TarotPostgreSQLManager:
    def __init__(self, dbname, user, password, host="localhost", port="5432"):
        self.connection_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """连接到PostgreSQL数据库"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor()
            self.cursor.execute("SET client_encoding TO 'UTF8'")
            print("✅ 成功连接到PostgreSQL数据库")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def hash_password(self, password):
        """安全的密码哈希函数"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
        return f"{salt}${password_hash}"
    
    def verify_password(self, password, stored_hash):
        """验证密码"""
        salt, stored_password_hash = stored_hash.split('$')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return new_hash == stored_password_hash
    
    def execute_query(self, query, params=None, fetch=False):
        """执行查询"""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if fetch:
                if query.strip().upper().startswith('SELECT') or 'RETURNING' in query.upper():
                    columns = [desc[0] for desc in self.cursor.description]
                    results = self.cursor.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            else:
                self.conn.commit()
                if query.strip().upper().startswith('INSERT'):
                    return self.cursor.rowcount
                else:
                    return self.cursor.rowcount
                    
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 查询执行失败: {e}")
            return None
    
    def initialize_database(self):
        """初始化数据库表结构"""
        #先删除旧表（如果存在）- 仅用于开发环境
        """drop_tables = [
            "DROP TABLE IF EXISTS user_settings CASCADE",
            "DROP TABLE IF EXISTS reading_cards CASCADE", 
            "DROP TABLE IF EXISTS tarot_readings CASCADE",
            "DROP TABLE IF EXISTS users CASCADE"
        ]
        
        for drop_sql in drop_tables:
            try:
                self.cursor.execute(drop_sql)
            except:
                pass"""
        
        # 创建新表
        tables = [
            """
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
            """,
            """
            CREATE TABLE tarot_readings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                spread_type VARCHAR(50) NOT NULL,
                question TEXT,
                reading_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
            """,
            """
            CREATE TABLE reading_cards (
                id SERIAL PRIMARY KEY,
                reading_id INTEGER NOT NULL REFERENCES tarot_readings(id) ON DELETE CASCADE,
                card_name VARCHAR(100) NOT NULL,
                position VARCHAR(50),
                orientation VARCHAR(10) DEFAULT 'upright',
                interpretation TEXT
            )
            """,
            """
            CREATE TABLE user_settings (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                language VARCHAR(10) DEFAULT 'zh_CN',
                theme VARCHAR(20) DEFAULT 'light',
                notification_enabled BOOLEAN DEFAULT TRUE
            )
            """
        ]
        
        for i, table_sql in enumerate(tables):
            try:
                self.cursor.execute(table_sql)
                print(f"✅ 表创建成功 [{i+1}/{len(tables)}]")
            except Exception as e:
                print(f"❌ 创建表失败 [{i+1}/{len(tables)}]: {e}")
        
        self.conn.commit()
        print("✅ 数据库初始化完成")
    
    def create_user(self, username, password, email=None):
        """创建新用户"""
        password_hash = self.hash_password(password)
        
        query = """
        INSERT INTO users (username, password_hash, email, last_login) 
        VALUES (%s, %s, %s, %s) RETURNING id
        """
        
        result = self.execute_query(
            query, 
            (username, password_hash, email, datetime.now()),
            fetch=True
        )
        
        if result and len(result) > 0:
            user_id = result[0]['id']
            # 创建用户设置
            settings_query = "INSERT INTO user_settings (user_id) VALUES (%s)"
            self.execute_query(settings_query, (user_id,))
            print(f"✅ 用户 '{username}' 创建成功，ID: {user_id}")
            return user_id
        else:
            print(f"❌ 创建用户失败")
            return None
    
    def verify_user(self, username, password):
        """验证用户登录"""
        query = """
        SELECT id, username, email, password_hash 
        FROM users 
        WHERE username = %s
        """
        
        result = self.execute_query(query, (username,), fetch=True)
        
        if result and len(result) > 0:
            user = result[0]
            stored_hash = user['password_hash']
            
            # 验证密码
            if self.verify_password(password, stored_hash):
                # 更新最后登录时间
                update_query = "UPDATE users SET last_login = %s WHERE id = %s"
                self.execute_query(update_query, (datetime.now(), user['id']))
                print(f"✅ 用户 '{username}' 验证成功")
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                }
            else:
                print(f"❌ 密码错误")
        else:
            print(f"❌ 用户 '{username}' 不存在")
        
        return None
    
    def user_exists(self, username):
        """检查用户是否存在"""
        query = "SELECT id FROM users WHERE username = %s"
        result = self.execute_query(query, (username,), fetch=True)
        return result is not None and len(result) > 0
    
    # ... 其他方法保持不变 ...
    def add_tarot_reading(self, user_id, spread_type, question, cards_data, notes=None):
        """添加塔罗牌占卜记录"""
        try:
            # 开始事务
            self.cursor.execute("BEGIN")
            
            # 插入占卜记录
            reading_query = """
            INSERT INTO tarot_readings (user_id, spread_type, question, notes)
            VALUES (%s, %s, %s, %s) RETURNING id
            """
            self.cursor.execute(reading_query, (user_id, spread_type, question, notes))
            reading_result = self.cursor.fetchone()
            
            if not reading_result:
                raise Exception("无法创建占卜记录")
            
            reading_id = reading_result[0]
            
            # 插入每张牌的信息
            card_query = """
            INSERT INTO reading_cards (reading_id, card_name, position, orientation, interpretation)
            VALUES (%s, %s, %s, %s, %s)
            """
            for card in cards_data:
                self.cursor.execute(card_query, (
                    reading_id, 
                    card['name'], 
                    card['position'], 
                    card.get('orientation', 'upright'), 
                    card.get('interpretation', '')
                ))
            
            # 提交事务
            self.conn.commit()
            print(f"✅ 占卜记录添加成功，ID: {reading_id}")
            return reading_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ 添加占卜记录失败: {e}")
            return None
    
    def get_user_readings(self, user_id, limit=None):
        """获取用户的占卜记录"""
        query = """
        SELECT 
            tr.id, tr.spread_type, tr.question, tr.reading_date, tr.notes,
            json_agg(
                json_build_object(
                    'name', rc.card_name,
                    'position', rc.position,
                    'orientation', rc.orientation,
                    'interpretation', rc.interpretation
                )
            ) as cards
        FROM tarot_readings tr
        LEFT JOIN reading_cards rc ON tr.id = rc.reading_id
        WHERE tr.user_id = %s
        GROUP BY tr.id, tr.spread_type, tr.question, tr.reading_date, tr.notes
        ORDER BY tr.reading_date DESC
        """
        
        if limit:
            query += " LIMIT %s"
            result = self.execute_query(query, (user_id, limit), fetch=True)
        else:
            result = self.execute_query(query, (user_id,), fetch=True)
        
        return result or []
    
    def get_reading_by_id(self, reading_id):
        """根据ID获取占卜记录"""
        query = """
        SELECT 
            tr.id, tr.spread_type, tr.question, tr.reading_date, tr.notes,
            u.username,
            json_agg(
                json_build_object(
                    'name', rc.card_name,
                    'position', rc.position,
                    'orientation', rc.orientation,
                    'interpretation', rc.interpretation
                )
            ) as cards
        FROM tarot_readings tr
        JOIN users u ON tr.user_id = u.id
        LEFT JOIN reading_cards rc ON tr.id = rc.reading_id
        WHERE tr.id = %s
        GROUP BY tr.id, tr.spread_type, tr.question, tr.reading_date, tr.notes, u.username
        """
        
        result = self.execute_query(query, (reading_id,), fetch=True)
        return result[0] if result and len(result) > 0 else None
    
    def update_user_settings(self, user_id, language=None, theme=None, notification_enabled=None):
        """更新用户设置"""
        updates = []
        params = []
        
        if language is not None:
            updates.append("language = %s")
            params.append(language)
        
        if theme is not None:
            updates.append("theme = %s")
            params.append(theme)
            
        if notification_enabled is not None:
            updates.append("notification_enabled = %s")
            params.append(notification_enabled)
        
        if not updates:
            return False
        
        params.append(user_id)
        
        query = f"""
        UPDATE user_settings 
        SET {', '.join(updates)}
        WHERE user_id = %s
        """
        
        result = self.execute_query(query, params)
        if result:
            print("✅ 用户设置更新成功")
            return True
        else:
            print("❌ 用户设置更新失败")
            return False
    
    def get_user_settings(self, user_id):
        """获取用户设置"""
        query = "SELECT * FROM user_settings WHERE user_id = %s"
        result = self.execute_query(query, (user_id,), fetch=True)
        return result[0] if result and len(result) > 0 else None
    
    def delete_reading(self, reading_id):
        """删除占卜记录"""
        # 由于有外键约束，删除reading_cards表中的相关记录会自动级联
        query = "DELETE FROM tarot_readings WHERE id = %s"
        result = self.execute_query(query, (reading_id,))
        
        if result:
            print(f"✅ 占卜记录 {reading_id} 删除成功")
            return True
        else:
            print(f"❌ 占卜记录 {reading_id} 删除失败")
            return False
    
    def get_user_stats(self, user_id):
        """获取用户统计信息"""
        stats = {}
        
        # 总占卜次数
        query1 = "SELECT COUNT(*) FROM tarot_readings WHERE user_id = %s"
        result1 = self.execute_query(query1, (user_id,), fetch=True)
        stats['total_readings'] = result1[0]['count'] if result1 else 0
        
        # 最近占卜时间
        query2 = "SELECT MAX(reading_date) FROM tarot_readings WHERE user_id = %s"
        result2 = self.execute_query(query2, (user_id,), fetch=True)
        stats['last_reading'] = result2[0]['max'] if result2 else None
        
        # 最常用的牌阵
        query3 = """
        SELECT spread_type, COUNT(*) as count 
        FROM tarot_readings 
        WHERE user_id = %s 
        GROUP BY spread_type 
        ORDER BY count DESC 
        LIMIT 1
        """
        result3 = self.execute_query(query3, (user_id,), fetch=True)
        stats['favorite_spread'] = result3[0] if result3 else None
        
        return stats
    
    def search_readings(self, user_id, keyword):
        """搜索占卜记录"""
        query = """
        SELECT DISTINCT tr.*
        FROM tarot_readings tr
        LEFT JOIN reading_cards rc ON tr.id = rc.reading_id
        WHERE tr.user_id = %s AND (
            tr.question ILIKE %s OR 
            tr.notes ILIKE %s OR
            rc.card_name ILIKE %s OR
            rc.interpretation ILIKE %s
        )
        ORDER BY tr.reading_date DESC
        """
        
        search_term = f"%{keyword}%"
        result = self.execute_query(
            query, 
            (user_id, search_term, search_term, search_term, search_term), 
            fetch=True
        )
        
        return result or []
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ 数据库连接已关闭")

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout, QMessageBox,QInputDialog
from PySide6.QtCore import Qt
import sys

class CheckIn:
    def __init__(self):
        self.window = QMainWindow()
        self.window.setWindowTitle("塔罗牌日记 - 登录")
        self.window.setGeometry(100, 100, 400, 300)
        
        # 使用PostgreSQL数据库
        self.db = TarotPostgreSQLManager(
            dbname="tarot_diary",
            user="postgres",      # 替换为你的用户名
            password="password",  # 替换为你的密码
            host="localhost"
        )
        
        self.main_window = None
        self.initUI()
    
    def initUI(self):
        """初始化登录界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        
        # 标题
        title_label = QLabel("塔罗牌日记")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        main_layout.addWidget(title_label)
        
        # 账号输入
        account_layout = QHBoxLayout()
        self.account_label = QLabel("账号:")
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("请输入用户名")
        account_layout.addWidget(self.account_label)
        account_layout.addWidget(self.account_input)
        main_layout.addLayout(account_layout)
        
        # 密码输入
        password_layout = QHBoxLayout()
        self.password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password_label)
        password_layout.addWidget(self.password_input)
        main_layout.addLayout(password_layout)
        
        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.check_in)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        main_layout.addWidget(self.login_button)
        
        # 注册按钮
        self.register_button = QPushButton("注册新账号")
        self.register_button.clicked.connect(self.show_register)
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;
                color: white;
                border: none;
                padding: 8px;
                font-size: 14px;
                border-radius: 5px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #007B9A;
            }
        """)
        main_layout.addWidget(self.register_button)
        
        # 设置容器
        container = QWidget()
        container.setLayout(main_layout)
        self.window.setCentralWidget(container)
        
        # 连接数据库
        if not self.db.connect():
            QMessageBox.critical(self.window, "错误", "无法连接数据库，请检查数据库设置")
        
        # 初始化数据库表
        self.db.initialize_database()
    
    def check_in(self):
        """登录验证"""
        username = self.account_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self.window, "输入错误", "请输入账号和密码")
            return
        
        # 验证用户
        user = self.db.verify_user(username, password)
        
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
        """显示注册对话框"""
        username, ok = QInputDialog.getText(self.window, "注册新账号", "请输入用户名:")
        if ok and username:
            password, ok = QInputDialog.getText(self.window, "注册新账号", "请输入密码:", QLineEdit.Password)
            if ok and password:
                email, ok = QInputDialog.getText(self.window, "注册新账号", "请输入邮箱（可选）:")
                if ok:
                    # 创建新用户
                    user_id = self.db.create_user(username, password, email if email else None)
                    if user_id:
                        QMessageBox.information(self.window, "注册成功", f"用户 {username} 创建成功！")
                        # 自动填充登录表单
                        self.account_input.setText(username)
                        self.password_input.setText("")
                    else:
                        QMessageBox.warning(self.window, "注册失败", "用户名可能已存在")
    
    def show(self):
        self.window.show()

from PySide6.QtWidgets import (QTabWidget, QTextEdit, QComboBox, 
                               QListWidget, QListWidgetItem, QSplitter,
                               QInputDialog, QMenu, QDialog, QDialogButtonBox,
                               QFormLayout)
from PySide6.QtCore import QTimer

class MainWindow:
    def __init__(self, user, db_manager):
        self.user = user
        self.db = db_manager
        self.window = QMainWindow()
        self.window.setWindowTitle(f"塔罗牌日记 - {user['username']}")
        self.window.setGeometry(100, 100, 1200, 800)
        
        self.initUI()
    
    def initUI(self):
        """初始化主界面"""
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 占卜记录标签页
        self.readings_tab = QWidget()
        self.setup_readings_tab()
        self.tabs.addTab(self.readings_tab, "占卜记录")
        
        # 新占卜标签页
        self.new_reading_tab = QWidget()
        self.setup_new_reading_tab()
        self.tabs.addTab(self.new_reading_tab, "新占卜")
        
        # 设置标签页
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "设置")
        
        main_layout.addWidget(self.tabs)
        
        # 加载用户数据
        self.load_user_data()
    
    def setup_readings_tab(self):
        """设置占卜记录标签页"""
        layout = QVBoxLayout(self.readings_tab)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索占卜记录...")
        self.search_input.textChanged.connect(self.search_readings)
        search_layout.addWidget(self.search_input)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_readings)
        search_layout.addWidget(refresh_btn)
        
        layout.addLayout(search_layout)
        
        # 占卜记录列表
        self.readings_list = QListWidget()
        self.readings_list.itemDoubleClicked.connect(self.show_reading_details)
        layout.addWidget(self.readings_list)
        
        # 右键菜单
        self.readings_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.readings_list.customContextMenuRequested.connect(self.show_reading_context_menu)
    
    def setup_new_reading_tab(self):
        """设置新占卜标签页"""
        layout = QVBoxLayout(self.new_reading_tab)
        
        # 牌阵选择
        form_layout = QFormLayout()
        self.spread_combo = QComboBox()
        self.spread_combo.addItems(["三张牌展开", "凯尔特十字", "一日一牌", "关系牌阵", "职业发展"])
        form_layout.addRow("牌阵类型:", self.spread_combo)
        
        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("请输入你的问题...")
        self.question_input.setMaximumHeight(100)
        form_layout.addRow("问题:", self.question_input)
        
        layout.addLayout(form_layout)
        
        # 卡片区域
        self.cards_layout = QHBoxLayout()
        layout.addLayout(self.cards_layout)
        
        # 开始占卜按钮
        start_btn = QPushButton("开始占卜")
        start_btn.clicked.connect(self.start_reading)
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px;
                font-size: 16px;
                border-radius: 5px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(start_btn)
        
        layout.addStretch()
    
    def setup_settings_tab(self):
        """设置设置标签页"""
        layout = QVBoxLayout(self.settings_tab)
        
        # 用户信息
        user_group = QWidget()
        user_layout = QFormLayout(user_group)
        user_layout.addRow("用户名:", QLabel(self.user['username']))
        user_layout.addRow("邮箱:", QLabel(self.user.get('email', '未设置')))
        layout.addWidget(user_group)
        
        # 应用设置
        settings_group = QWidget()
        settings_layout = QFormLayout(settings_group)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "English", "日本語"])
        settings_layout.addRow("语言:", self.language_combo)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题"])
        settings_layout.addRow("主题:", self.theme_combo)
        
        layout.addWidget(settings_group)
        
        # 保存设置按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # 退出登录按钮
        logout_btn = QPushButton("退出登录")
        logout_btn.clicked.connect(self.logout)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        layout.addWidget(logout_btn)
    
    def load_user_data(self):
        """加载用户数据"""
        # 加载占卜记录
        self.load_readings()
        
        # 加载用户设置
        settings = self.db.get_user_settings(self.user['id'])
        if settings:
            # 设置语言
            if settings['language'] == 'en':
                self.language_combo.setCurrentText("English")
            elif settings['language'] == 'ja':
                self.language_combo.setCurrentText("日本語")
            else:
                self.language_combo.setCurrentText("中文")
            
            # 设置主题
            if settings['theme'] == 'dark':
                self.theme_combo.setCurrentText("深色主题")
            else:
                self.theme_combo.setCurrentText("浅色主题")
    
    def load_readings(self):
        """加载占卜记录"""
        self.readings_list.clear()
        readings = self.db.get_user_readings(self.user['id'])
        
        for reading in readings:
            item_text = f"{reading['spread_type']} - {reading['reading_date'].strftime('%Y-%m-%d %H:%M')}"
            if reading['question']:
                # 截断长问题
                question = reading['question'][:50] + "..." if len(reading['question']) > 50 else reading['question']
                item_text += f"\n  问题: {question}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, reading['id'])  # 存储记录ID
            self.readings_list.addItem(item)
    
    def search_readings(self):
        """搜索占卜记录"""
        keyword = self.search_input.text().strip()
        if keyword:
            results = self.db.search_readings(self.user['id'], keyword)
            self.readings_list.clear()
            for reading in results:
                item_text = f"{reading['spread_type']} - {reading['reading_date'].strftime('%Y-%m-%d %H:%M')}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, reading['id'])
                self.readings_list.addItem(item)
        else:
            self.load_readings()
    
    def show_reading_details(self, item):
        """显示占卜记录详情"""
        reading_id = item.data(Qt.UserRole)
        reading = self.db.get_reading_by_id(reading_id)
        
        if reading:
            dialog = QDialog(self.window)
            dialog.setWindowTitle("占卜记录详情")
            dialog.setModal(True)
            dialog.resize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # 显示基本信息
            info_text = f"牌阵: {reading['spread_type']}\n"
            info_text += f"时间: {reading['reading_date'].strftime('%Y-%m-%d %H:%M')}\n"
            if reading['question']:
                info_text += f"问题: {reading['question']}\n"
            if reading['notes']:
                info_text += f"备注: {reading['notes']}\n"
            
            info_label = QLabel(info_text)
            layout.addWidget(info_label)
            
            # 显示卡片
            cards_text = "\n卡片:\n"
            for i, card in enumerate(reading['cards'], 1):
                cards_text += f"{i}. {card['name']} ({card['position']}) - {card['orientation']}\n"
                if card['interpretation']:
                    cards_text += f"   解释: {card['interpretation']}\n"
            
            cards_label = QLabel(cards_text)
            layout.addWidget(cards_label)
            
            # 关闭按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)
            
            dialog.exec()
    
    def show_reading_context_menu(self, position):
        """显示占卜记录右键菜单"""
        item = self.readings_list.itemAt(position)
        if item:
            menu = QMenu(self.window)
            
            view_action = menu.addAction("查看详情")
            delete_action = menu.addAction("删除记录")
            
            action = menu.exec_(self.readings_list.mapToGlobal(position))
            
            if action == view_action:
                self.show_reading_details(item)
            elif action == delete_action:
                reading_id = item.data(Qt.UserRole)
                reply = QMessageBox.question(self.window, "确认删除", 
                                           "确定要删除这条占卜记录吗？", 
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if self.db.delete_reading(reading_id):
                        self.load_readings()
                        QMessageBox.information(self.window, "成功", "记录已删除")
    
    def start_reading(self):
        """开始新占卜"""
        spread_type = self.spread_combo.currentText()
        question = self.question_input.toPlainText().strip()
        
        if not question:
            QMessageBox.warning(self.window, "输入错误", "请输入问题")
            return
        
        # 这里应该实现实际的抽牌逻辑
        # 暂时使用示例数据
        cards_data = [
            {"name": "愚者", "position": "过去", "interpretation": "新的开始"},
            {"name": "魔术师", "position": "现在", "interpretation": "掌握技能"}, 
            {"name": "女祭司", "position": "未来", "interpretation": "需要内省"}
        ]
        
        # 添加占卜记录
        reading_id = self.db.add_tarot_reading(
            self.user['id'], 
            spread_type, 
            question, 
            cards_data,
            "自动生成的占卜记录"
        )
        
        if reading_id:
            QMessageBox.information(self.window, "成功", "占卜记录已保存！")
            self.question_input.clear()
            self.tabs.setCurrentIndex(0)  # 切换到记录标签页
            self.load_readings()
    
    def save_settings(self):
        """保存用户设置"""
        language_map = {"中文": "zh_CN", "English": "en", "日本語": "ja"}
        theme_map = {"浅色主题": "light", "深色主题": "dark"}
        
        language = language_map.get(self.language_combo.currentText(), "zh_CN")
        theme = theme_map.get(self.theme_combo.currentText(), "light")
        
        if self.db.update_user_settings(self.user['id'], language=language, theme=theme):
            QMessageBox.information(self.window, "成功", "设置已保存")
        else:
            QMessageBox.warning(self.window, "错误", "保存设置失败")
    
    def logout(self):
        """退出登录"""
        reply = QMessageBox.question(self.window, "确认退出", 
                                   "确定要退出登录吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.close()
            self.window.close()
            # 这里可以添加重新显示登录窗口的逻辑
    
    def show(self):
        self.window.show()
# 测试代码
if __name__ == "__main__":
    # 创建数据库管理器
    app = QApplication(sys.argv)
    window_instance = CheckIn()
    window_instance.show()
    app.exec()
    db = TarotPostgreSQLManager(
        dbname="tarot_diary",
        user="postgres",
        password="056300", 
        host="localhost",
        port="5432"
    )
    
    if db.connect():
        # 初始化数据库（会删除旧数据）
        db.initialize_database()
        
        # 创建测试用户
        print("创建测试用户...")
        user_id = db.create_user("test_user", "test_password", "test@example.com")
        
        if user_id:
            print(f"✅ 用户创建成功，ID: {user_id}")
            
            # 立即验证用户
            print("验证用户...")
            user = db.verify_user("test_user", "test_password")
            
            if user:
                print(f"✅ 用户验证成功: {user}")
                
                # 测试错误密码
                print("测试错误密码...")
                wrong_user = db.verify_user("test_user", "wrong_password")
                if not wrong_user:
                    print("✅ 错误密码正确拒绝")
                
                # 测试不存在的用户
                print("测试不存在的用户...")
                nonexistent_user = db.verify_user("nonexistent_user", "password")
                if not nonexistent_user:
                    print("✅ 不存在用户正确拒绝")
                    
            else:
                print("❌ 用户验证失败 - 这不应该发生")
        else:
            print("❌ 用户创建失败")
        
        db.close()