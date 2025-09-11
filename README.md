# 消息违规检测系统

## 📋 项目简介

本项目是一个基于多算法融合的智能消息违规检测系统，专门用于监控和检测抖音客服系统中的违规消息。系统采用关键字匹配、正则表达式匹配、模糊匹配等多种算法，结合现代化的GUI管理界面，为内容审核提供高效、准确的解决方案。

## ✨ 核心特性

### 🔍 多算法检测引擎
- **精确匹配**: 基于Aho-Corasick算法的高效关键字匹配
- **正则表达式**: 支持复杂模式匹配（电话、邮箱、身份证等）
- **模糊匹配**: 基于编辑距离的容错匹配，支持错别字检测
- **混合模式**: 多种算法并行检测，提高检测准确率

### 🗄️ 双数据库支持
- **MySQL模式**（推荐）: 支持关键词分类、检测记录存储、统计分析
- **SQLite模式**（兼容）: 轻量级本地存储，保持向后兼容

### 🖥️ 现代化GUI界面
- **关键词管理**: 可视化关键词增删改查，支持批量导入导出
- **实时监控**: 抖音客服消息实时检测和违规提醒
- **系统状态**: 数据库连接状态、系统日志、统计信息
- **配置管理**: 数据库连接配置、系统参数设置

### 🚀 高性能架构
- **单例模式**: 关键词匹配器采用单例设计，内存占用优化
- **缓存机制**: 用户列表缓存，减少重复查询
- **异步处理**: 消息检测采用多线程，不阻塞界面操作
- **持久化存储**: 匹配器状态自动保存，支持快速恢复

## 🛠️ 技术栈

### 核心依赖
- **PyQt5**: 现代化GUI框架
- **DrissionPage**: 浏览器自动化，获取动态渲染内容
- **pyahocorasick**: 多模式字符串匹配算法
- **rapidfuzz**: 高性能模糊字符串匹配
- **pymysql**: MySQL数据库连接
- **cachetools**: 缓存工具库

### 系统要求
- Python 3.7+
- Windows 10/11 (推荐)
- 4GB+ RAM
- 网络连接（用于访问抖音客服系统）

## 📦 安装指南

### 1. 克隆项目
```bash
git clone <repository-url>
cd monitor_message
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置数据库（可选）
系统默认使用SQLite，如需使用MySQL，请参考 [MySQL配置指南](MySQL_Setup_Guide.md)

### 4. 启动系统
```bash
# 方法1: 直接运行主程序
python main.py

# 方法2: Windows批处理启动
start_gui.bat

# 方法3: 直接运行GUI模块
python -m gui.main_window
```

## 🚀 快速开始

### 1. 首次启动
1. 运行 `python main.py` 启动系统
2. 系统会自动检查依赖并创建必要目录
3. 进入GUI管理界面

### 2. 配置数据库（MySQL模式）
1. 切换到"数据库管理"标签页
2. 点击"配置连接"按钮
3. 填写MySQL连接信息
4. 点击"测试连接"验证配置
5. 保存配置并连接数据库

### 3. 添加关键词
1. 切换到"关键词管理"标签页
2. 输入关键词和类型（可选）
3. 点击"添加"按钮
4. 或使用"导入文件"批量添加

### 4. 开始监控
1. 切换到"消息检测"标签页
2. 输入抖音客服系统URL
3. 点击"开始监控"按钮
4. 系统将自动检测违规消息

## 📖 详细使用说明

### 关键词管理

#### 关键词类型
系统支持以下预定义类型：
- `keyword`: 普通关键词（默认）
- `fraud`: 诈骗类
- `malware`: 恶意软件类
- `spam`: 垃圾信息类
- `adult`: 成人内容类
- `violence`: 暴力内容类
- `politics`: 政治敏感类
- `terrorism`: 恐怖主义类

#### 批量操作
- **导入文件**: 支持TXT格式，每行一个关键词
- **导出文件**: 导出当前所有关键词到文件
- **清空所有**: 清空当前数据库中的所有关键词

### 消息检测

#### 检测算法
1. **精确匹配**: 检测完全匹配的关键词
2. **正则匹配**: 检测符合正则模式的内容
3. **模糊匹配**: 检测相似度高的内容（可配置容错距离）

#### 检测结果
- 实时显示检测到的违规消息
- 显示匹配的关键词和匹配类型
- 自动保存检测记录到数据库

### 系统状态

#### 监控信息
- 关键词总数统计
- 数据库连接状态
- 匹配器状态信息
- 系统运行日志

#### 日志管理
- 实时日志显示
- 错误和警告信息
- 操作记录追踪

## ⚙️ 配置说明

### 系统配置
主要配置项在 `config/system_config.py` 中：
```python
# 检测间隔（秒）
DETECTION_INTERVAL = 5

# 最大消息长度
MAX_MESSAGE_LENGTH = 1000

# 模糊匹配配置
FUZZY_MATCH_ENABLED = True
FUZZY_MAX_DISTANCE = 1

# 正则表达式模式
REGEX_PATTERNS = {
    "phone": r"\d{3}-\d{3}-\d{4}",
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    # ... 更多模式
}
```

### 数据库配置
MySQL配置文件 `config/database_config.json`：
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

## 📁 项目结构

```
monitor_message/
├── main.py                          # 主启动脚本
├── start_gui.bat                    # Windows批处理启动文件
├── requirements.txt                 # 依赖包列表
├── README.md                        # 项目说明（本文件）
├── GUI_README.md                    # GUI使用说明
├── MySQL_Setup_Guide.md             # MySQL配置指南
├── PROJECT_STRUCTURE.md             # 项目结构说明
│
├── config/                          # 配置包
│   ├── system_config.py             # 系统配置
│   └── database_config.py           # 数据库配置
│
├── gui/                             # GUI包
│   ├── main_window.py               # 主窗口
│   ├── database_config_dialog.py    # 数据库配置对话框
│   ├── keyword_manager_widget.py    # 关键词管理组件
│   ├── message_detection_widget.py  # 消息检测组件
│   └── system_status_widget.py      # 系统状态组件
│
├── database/                        # 数据库包
│   ├── mysql_db.py                  # MySQL数据库操作
│   └── sqlite_db.py                 # SQLite数据库操作
│
├── function/                        # 核心功能包
│   ├── Filter.py                    # 关键词匹配器
│   ├── GetDouyinMsg.py              # 抖音消息获取
│   └── test_filter.py               # 测试文件
│
├── BaseData/                        # 基础数据
│   ├── KeyWord.py                   # 关键词数据模型
│   └── violation_keywords.db        # SQLite数据库文件
│
├── logs/                            # 日志目录
└── data/                            # 数据目录
```

## 🔧 开发指南

### 添加新的检测算法
1. 在 `function/Filter.py` 中的 `KeywordMatcher` 类添加新方法
2. 在 `search()` 方法中集成新算法
3. 更新 `MatchResult` 类以支持新的匹配类型

### 扩展GUI功能
1. 在 `gui/` 目录下创建新的组件文件
2. 在 `main_window.py` 中集成新组件
3. 更新菜单和状态栏

### 数据库扩展
1. 在 `database/` 目录下扩展数据库操作类
2. 更新表结构和索引
3. 修改配置文件

## 🐛 故障排除

### 常见问题

#### 1. 启动失败
**问题**: 程序无法启动或报错
**解决方案**:
- 检查Python版本（需要3.7+）
- 确认所有依赖包已安装：`pip install -r requirements.txt`
- 检查目录权限

#### 2. 数据库连接失败
**问题**: MySQL连接失败
**解决方案**:
- 检查MySQL服务是否运行
- 验证连接配置信息
- 确认数据库和用户权限

#### 3. 消息检测失败
**问题**: 无法获取抖音消息
**解决方案**:
- 检查网络连接
- 验证URL地址是否正确
- 确认有访问权限

#### 4. 关键词匹配不准确
**问题**: 误报或漏报
**解决方案**:
- 调整模糊匹配参数
- 优化正则表达式
- 检查关键词质量

### 日志查看
系统日志会显示在"系统状态"标签页中，包含：
- 系统启动信息
- 错误和警告信息
- 操作记录
- 性能统计

## 📈 性能优化

### 关键词优化
- 定期清理无效关键词
- 使用精确匹配替代模糊匹配（当可能时）
- 合理设置模糊匹配距离

### 数据库优化
- 定期清理历史检测记录
- 为常用查询字段添加索引
- 使用连接池（高并发场景）

### 系统优化
- 调整检测间隔时间
- 限制消息长度
- 启用缓存机制

## 🤝 贡献指南

欢迎贡献代码和建议！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 技术支持

如有问题或建议，请通过以下方式联系：
- 提交 [Issue](https://github.com/your-repo/issues)
- 发送邮件至：your-email@example.com
- 项目讨论区

## 🔗 相关链接

- [DrissionPage 官方文档](https://www.drissionpage.cn)
- [PyQt5 官方文档](https://doc.qt.io/qtforpython/)
- [MySQL 官方文档](https://dev.mysql.com/doc/)
- [Aho-Corasick 算法介绍](https://en.wikipedia.org/wiki/Aho%E2%80%93Corasick_algorithm)

---

**注意**: 本项目仅用于学习和研究目的，请遵守相关法律法规和平台使用条款。