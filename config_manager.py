# config_manager.py
import json
import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib
import platform

class SecureConfigManager:
    def __init__(self, app_name="TarotDiary"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "database_config.json"
        self.key_file = self.config_dir / "encryption.key"
        self.fernet = None
        self._initialize_encryption()
    
    def _get_config_dir(self):
        """获取配置目录"""
        system = platform.system()
        
        if system == "Windows":
            config_dir = Path(os.environ['APPDATA']) / self.app_name
            print(f"Windows 系统，配置目录: {config_dir}")
        elif system == "Darwin":  # macOS
            config_dir = Path.home() / "Library" / "Application Support" / self.app_name
        else:  # Linux 和其他 Unix
            config_dir = Path.home() / f".{self.app_name.lower()}"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _generate_key_from_system(self):
        """基于系统信息生成加密密钥"""
        # 收集系统特定信息（不会泄露敏感信息）
        system_info = [
            platform.node(),  # 主机名
            platform.system(),  # 操作系统
            platform.machine(),  # 机器架构
            str(Path.home()),  # 用户主目录
        ]
        
        # 组合并哈希
        key_material = "|".join(system_info).encode()
        salt = b'tarot_diary_salt_2024'  # 固定盐值
        
        # 使用 PBKDF2 生成密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(key_material))
        return key
    
    def _initialize_encryption(self):
        """初始化加密"""
        try:
            key = self._generate_key_from_system()
            self.fernet = Fernet(key)
        except Exception as e:
            print(f"加密初始化失败: {e}")
            self.fernet = None
    
    def encrypt(self, data):
        """加密数据"""
        if not self.fernet:
            return data  # 回退到不加密
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self.fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data):
        """解密数据"""
        if not self.fernet:
            return encrypted_data  # 回退到不解密
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"解密失败: {e}")
            return None
    
    def save_database_config(self, db_config):
        """保存数据库配置"""
        # 验证必要字段
        required_fields = ['host', 'port', 'dbname', 'user', 'password']
        for field in required_fields:
            if field not in db_config or not db_config[field]:
                raise ValueError(f"缺少必要的数据库配置字段: {field}")
        
        # 加密敏感信息
        encrypted_config = {
            'host': self.encrypt(db_config['host']),
            'port': self.encrypt(str(db_config['port'])),
            'dbname': self.encrypt(db_config['dbname']),
            'user': self.encrypt(db_config['user']),
            'password': self.encrypt(db_config['password']),
            'save_timestamp': self.encrypt(str(os.path.getmtime(__file__))),
            'version': '1.0'
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(encrypted_config, f, indent=2, ensure_ascii=False)
            
            # 设置文件权限（Unix系统）
            if platform.system() != "Windows":
                os.chmod(self.config_file, 0o600)
            
            print(f"✅ 数据库配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def load_database_config(self):
        """加载数据库配置"""
        if not self.config_file.exists():
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                encrypted_config = json.load(f)
            
            # 解密所有字段
            decrypted_config = {}
            for key, encrypted_value in encrypted_config.items():
                if key == 'version':
                    decrypted_config[key] = encrypted_value
                else:
                    decrypted_value = self.decrypt(encrypted_value)
                    if decrypted_value is None:
                        print(f"❌ 解密 {key} 失败")
                        return None
                    decrypted_config[key] = decrypted_value
            
            # 转换端口为整数
            if 'port' in decrypted_config:
                try:
                    decrypted_config['port'] = int(decrypted_config['port'])
                except ValueError:
                    decrypted_config['port'] = 5432
            
            print("✅ 数据库配置加载成功")
            return decrypted_config
            
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            return None
    
    def config_exists(self):
        """检查配置是否存在"""
        return self.config_file.exists()
    
    def delete_config(self):
        """删除配置文件"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
                print("✅ 数据库配置已删除")
                return True
        except Exception as e:
            print(f"❌ 删除配置失败: {e}")
        return False
    
    def get_config_info(self):
        """获取配置信息（不包含密码）"""
        config = self.load_database_config()
        if not config:
            return None
        
        safe_config = config.copy()
        if 'password' in safe_config:
            safe_config['password'] = '***' + safe_config['password'][-3:] if len(safe_config['password']) > 3 else '***'
        
        return safe_config
    
if __name__ == "__main__":
    manager = SecureConfigManager()
    sample_config = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'tarot_diary',
        'user': 'admin',
        'password': 'securepassword123'
    }
    manager.save_database_config(sample_config)
    loaded_config = manager.load_database_config()
    print(loaded_config)