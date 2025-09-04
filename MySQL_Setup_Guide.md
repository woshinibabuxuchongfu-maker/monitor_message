# MySQL数据库配置指南

## 概述

系统已成功从SQLite迁移到MySQL数据库，支持两种数据库模式：
- **MySQL模式**（推荐）：支持更强大的功能和更好的性能
- **SQLite模式**（兼容）：保持原有功能

## 功能特性

### MySQL模式新增功能
- ✅ 关键词类型分类管理
- ✅ 检测记录历史存储
- ✅ 数据库统计信息
- ✅ 连接状态监控
- ✅ 数据备份和恢复（待实现）

### 数据库表结构

#### 1. keywords表（关键词表）
```sql
CREATE TABLE keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL DEFAULT 'keyword',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_keyword (keyword),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 2. detection_records表（检测记录表）
```sql
CREATE TABLE detection_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(255),
    message TEXT,
    matched_keywords JSON,
    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_name),
    INDEX idx_time (detection_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 配置步骤

### 1. 安装MySQL数据库

#### Windows
```bash
# 下载MySQL安装包
# https://dev.mysql.com/downloads/mysql/

# 或使用Chocolatey
choco install mysql

# 或使用winget
winget install Oracle.MySQL
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

#### macOS
```bash
# 使用Homebrew
brew install mysql
brew services start mysql
```

### 2. 创建数据库和用户

```sql
-- 登录MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE filter_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（可选，建议创建专用用户）
CREATE USER 'filter_user'@'localhost' IDENTIFIED BY 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON filter_system.* TO 'filter_user'@'localhost';
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 3. 配置系统连接

#### 方法1：通过GUI界面配置
1. 启动系统：`python run_gui.py`
2. 切换到"数据库管理"标签页
3. 点击"配置连接"按钮
4. 填写连接信息：
   - **主机地址**: localhost（或MySQL服务器IP）
   - **端口**: 3306（默认）
   - **用户名**: root（或你创建的用户）
   - **密码**: 你的MySQL密码
   - **数据库名**: filter_system
   - **字符集**: utf8mb4
5. 点击"测试连接"验证配置
6. 点击"保存配置"

#### 方法2：手动创建配置文件
创建 `database_config.json` 文件：
```json
{
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "your_password",
  "database": "filter_system",
  "charset": "utf8mb4"
}
```

### 4. 验证配置

1. 在"数据库管理"标签页点击"连接数据库"
2. 查看连接状态是否显示"已连接"
3. 点击"刷新信息"查看数据库统计信息

## 使用说明

### 关键词管理

#### 添加关键词
1. 切换到"关键词管理"标签页
2. 选择"使用MySQL数据库"
3. 输入关键词和类型（可选）
4. 点击"添加"按钮

#### 关键词类型
系统支持以下预定义类型：
- `keyword`: 普通关键词（默认）
- `fraud`: 诈骗类
- `malware`: 恶意软件类
- `spam`: 垃圾信息类
- `adult`: 成人内容类
- `violence`: 暴力内容类

你也可以自定义类型名称。

### 检测记录查看

检测到的违规消息会自动保存到MySQL数据库中，包含：
- 用户名
- 消息内容
- 匹配的关键词信息
- 检测时间

### 数据库管理

在"数据库管理"标签页可以：
- 查看连接状态
- 查看数据库统计信息
- 测试连接
- 配置连接参数

## 故障排除

### 常见问题

#### 1. 连接失败
**错误**: `Access denied for user 'root'@'localhost'`

**解决方案**:
```sql
-- 重置root密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

#### 2. 数据库不存在
**错误**: `Unknown database 'filter_system'`

**解决方案**:
```sql
CREATE DATABASE filter_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 3. 字符集问题
**错误**: 中文显示乱码

**解决方案**:
- 确保数据库使用utf8mb4字符集
- 检查连接配置中的charset参数

#### 4. 权限问题
**错误**: `Access denied`

**解决方案**:
```sql
-- 检查用户权限
SHOW GRANTS FOR 'your_user'@'localhost';

-- 重新授权
GRANT ALL PRIVILEGES ON filter_system.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### 性能优化

#### 1. 索引优化
系统已自动创建必要的索引：
- keywords表的keyword字段索引
- keywords表的type字段索引
- detection_records表的user_name字段索引
- detection_records表的detection_time字段索引

#### 2. 连接池配置
对于高并发场景，建议配置MySQL连接池：
```python
# 在MySQL.py中可以添加连接池配置
connection_config = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "filter_system",
    "charset": "utf8mb4",
    "autocommit": True,
    "connect_timeout": 10,
    "read_timeout": 30,
    "write_timeout": 30
}
```

## 数据迁移

### 从SQLite迁移到MySQL

如果你之前使用SQLite，可以按以下步骤迁移数据：

1. **导出SQLite数据**:
```python
# 在关键词管理界面使用"导出文件"功能
# 或手动从SQLite数据库导出
```

2. **导入到MySQL**:
```python
# 在关键词管理界面使用"导入文件"功能
# 或通过MySQL管理工具导入
```

3. **验证数据**:
- 检查关键词数量是否一致
- 验证关键词内容是否正确

## 备份和恢复

### 备份数据
```bash
# 备份整个数据库
mysqldump -u root -p filter_system > backup_$(date +%Y%m%d).sql

# 只备份关键词表
mysqldump -u root -p filter_system keywords > keywords_backup.sql
```

### 恢复数据
```bash
# 恢复整个数据库
mysql -u root -p filter_system < backup_20231201.sql

# 只恢复关键词表
mysql -u root -p filter_system < keywords_backup.sql
```

## 安全建议

1. **使用专用用户**: 不要使用root用户，创建专用数据库用户
2. **强密码**: 使用复杂的密码
3. **网络安全**: 如果MySQL在远程服务器，配置防火墙
4. **定期备份**: 设置自动备份任务
5. **权限最小化**: 只授予必要的权限

## 技术支持

如果遇到问题，请：
1. 检查MySQL服务是否运行
2. 验证连接配置是否正确
3. 查看系统日志获取详细错误信息
4. 参考MySQL官方文档
