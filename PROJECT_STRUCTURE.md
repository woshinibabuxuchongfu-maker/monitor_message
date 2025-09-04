# 项目结构说明

## 目录结构

```
filter/
├── main.py                          # 主启动脚本
├── start_gui.bat                    # Windows批处理启动文件
├── requirements.txt                 # 依赖包列表
├── README.md                        # 项目说明
├── GUI_README.md                    # GUI使用说明
├── MySQL_Setup_Guide.md             # MySQL配置指南
├── PROJECT_STRUCTURE.md             # 项目结构说明（本文件）
│
├── config/                          # 配置包
│   ├── __init__.py
│   ├── system_config.py             # 系统配置
│   └── database_config.py           # 数据库配置
│
├── gui/                             # GUI包
│   ├── __init__.py
│   ├── main_window.py               # 主窗口
│   ├── database_config_dialog.py    # 数据库配置对话框
│   ├── keyword_manager_widget.py    # 关键词管理组件
│   ├── message_detection_widget.py  # 消息检测组件
│   └── system_status_widget.py      # 系统状态组件
│
├── database/                        # 数据库包
│   ├── __init__.py
│   ├── mysql_db.py                  # MySQL数据库操作
│   └── sqlite_db.py                 # SQLite数据库操作
│
├── BaseData/                        # 基础数据（保留原有结构）
│   ├── KeyWord.py                   # 关键词数据模型
│   ├── SQLite.py                    # 原有SQLite实现（已弃用）
│   ├── MySQL.py                     # 原有MySQL实现（已弃用）
│   └── violation_keywords.db        # SQLite数据库文件
│
├── Test/                            # 测试和核心功能
│   ├── Filter.py                    # 关键词匹配器
│   ├── GetDouyinMsg.py              # 抖音消息获取
│   └── test_filter.py               # 测试文件
│
├── logs/                            # 日志目录
├── data/                            # 数据目录
└── config/                          # 配置文件目录
    └── database_config.json         # 数据库配置文件
```

## 包说明

### config包
- **system_config.py**: 系统全局配置，包括界面设置、检测参数、正则表达式等
- **database_config.py**: 数据库配置管理，支持配置的加载、保存和验证

### gui包
- **main_window.py**: 主窗口，包含菜单栏、状态栏和标签页管理
- **database_config_dialog.py**: 数据库连接配置对话框和数据库管理组件
- **keyword_manager_widget.py**: 关键词管理界面，支持MySQL和SQLite双模式
- **message_detection_widget.py**: 消息检测监控界面，包含检测线程管理
- **system_status_widget.py**: 系统状态监控界面，显示系统信息和日志

### database包
- **mysql_db.py**: MySQL数据库操作类，支持关键词管理和检测记录存储
- **sqlite_db.py**: SQLite数据库操作类，保持向后兼容

## 启动方式

### 方法1：Python脚本启动
```bash
python main.py
```

### 方法2：Windows批处理启动
```bash
start_gui.bat
```

### 方法3：直接运行GUI模块
```bash
python -m gui.main_window
```

## 配置说明

### 系统配置
系统配置在 `config/system_config.py` 中定义，包括：
- 数据库路径配置
- 界面设置
- 检测参数
- 正则表达式模式
- 关键词类型定义

### 数据库配置
数据库配置通过GUI界面进行管理，配置文件保存在 `config/database_config.json`：
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

## 功能模块

### 1. 关键词管理
- 支持MySQL和SQLite双数据库模式
- 关键词类型分类管理
- 批量导入/导出功能
- 关键词搜索和删除

### 2. 消息检测
- 实时监控抖音客服消息
- 多算法违规检测（精确匹配、正则、模糊匹配）
- 检测结果实时显示
- 检测记录自动保存

### 3. 数据库管理
- MySQL连接配置和测试
- 数据库状态监控
- 统计信息显示
- 连接状态管理

### 4. 系统状态
- 系统信息实时显示
- 数据库统计信息
- 系统日志记录
- 状态监控

## 依赖包

```
DrissionPage      # 浏览器自动化
pymysql           # MySQL数据库连接
cachetools        # 缓存工具
pyahocorasick     # 多模式字符串匹配
rapidfuzz         # 模糊字符串匹配
PyQt5             # GUI框架
```

## 开发说明

### 添加新功能
1. 在相应的包中创建新模块
2. 更新包的 `__init__.py` 文件
3. 在主窗口中集成新功能
4. 更新配置文件和文档

### 修改配置
1. 系统配置：修改 `config/system_config.py`
2. 数据库配置：通过GUI界面或直接编辑 `config/database_config.json`

### 数据库迁移
- 从SQLite迁移到MySQL：使用关键词管理界面的导出/导入功能
- 配置MySQL连接：使用数据库管理界面的配置功能

## 注意事项

1. **目录权限**: 确保程序有权限创建和写入 `logs`、`data`、`config` 目录
2. **数据库连接**: 首次使用需要配置MySQL连接信息
3. **依赖安装**: 确保所有依赖包已正确安装
4. **Python版本**: 建议使用Python 3.7或更高版本

## 故障排除

### 常见问题
1. **导入错误**: 检查Python路径和包结构
2. **数据库连接失败**: 检查MySQL服务和配置信息
3. **GUI启动失败**: 检查PyQt5安装和依赖包
4. **权限错误**: 检查目录权限和文件访问权限

### 日志查看
系统日志会显示在"系统状态"标签页中，包含详细的错误信息和操作记录。
