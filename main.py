# main.py
import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from main import FirstRunWizard
from config_manager import SecureConfigManager
from main import CheckIn  # 假设这是你的主登录界面

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("塔罗牌日记")
    app.setApplicationVersion("1.0.0")
    
    # 初始化配置管理器
    config_manager = SecureConfigManager()
    
    # 检查是否是第一次运行
    if not config_manager.config_exists():
        # 显示首次运行向导
        wizard = FirstRunWizard()
        if wizard.exec() != FirstRunWizard.Accepted:
            # 用户取消了设置
            print("用户取消了首次设置")
            return 1
    
    # 加载数据库配置
    db_config = config_manager.load_database_config()
    if not db_config:
        QMessageBox.critical(
            None, 
            "配置错误", 
            "无法加载数据库配置。\n"
            "请重新运行首次设置向导。"
        )
        return 1
    
    try:
        # 创建数据库管理器并连接
        from Tarot_PostgreSQL import TarotPostgreSQLManager
        db_manager = TarotPostgreSQLManager(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port']
        )
        
        if db_manager.connect():
            # 显示主登录界面
            checkin_window = CheckIn(db_config)
            checkin_window.show()
            
            return app.exec()
        else:
            QMessageBox.critical(
                None, 
                "连接失败", 
                "无法连接到数据库。\n"
                "请检查:\n"
                "1. 数据库服务是否运行\n"
                "2. 网络连接是否正常\n"
                "3. 配置信息是否正确\n\n"
                "您可能需要重新配置数据库连接。"
            )
            return 1
            
    except Exception as e:
        QMessageBox.critical(
            None, 
            "启动错误", 
            f"应用程序启动失败:\n{str(e)}\n\n"
            "请尝试重新运行首次设置向导。"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())