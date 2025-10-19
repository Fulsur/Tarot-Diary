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