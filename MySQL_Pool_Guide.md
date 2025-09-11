# MySQL连接池使用指南

## 概述

本指南介绍如何将现有的MySQL数据库连接改为使用连接池，以提高数据库访问性能和并发处理能力。

## 主要改进

### 1. 连接池优势
- **性能提升**: 避免频繁创建和销毁连接的开销
- **并发支持**: 支持多个线程同时访问数据库
- **资源管理**: 自动管理连接的生命周期
- **故障恢复**: 自动处理连接断开和重连

### 2. 新增功能
- 连接池状态监控
- 可配置的连接池大小
- 溢出连接管理
- 线程安全的连接获取和释放

## 文件结构

```
database/
├── mysql_db.py          # 原始MySQL数据库类
└── mysql_pool_db.py     # 新的连接池版本

config/
├── database_config.py   # 数据库配置管理
└── database_config.json # 数据库配置文件

test_mysql_pool.py       # 连接池测试脚本
```

## 配置说明

### 数据库配置文件 (config/database_config.json)

```json
{
  "host": "192.168.100.27",
  "port": 3306,
  "user": "zmonv",
  "password": "rpa@2025",
  "database": "test_zmonv_rpa",
  "charset": "utf8mb4",
  "pool_size": 10,        // 连接池大小
  "max_overflow": 5       // 最大溢出连接数
}
```

### 连接池参数说明

- **pool_size**: 连接池中保持的连接数量（默认：10）
- **max_overflow**: 当连接池满时，允许创建的额外连接数（默认：5）
- **总连接数**: pool_size + max_overflow

## 使用方法

### 1. 基本使用

```python
from database.mysql_pool_db import MySQLKeywordDBPool
from config.database_config import DatabaseConfig

# 加载配置
config = DatabaseConfig.load_config()

# 创建数据库实例（使用连接池）
db = MySQLKeywordDBPool(
    config, 
    pool_size=10,      # 连接池大小
    max_overflow=5     # 最大溢出连接数
)

# 测试连接
if db.test_connection():
    print("数据库连接成功")
    
    # 查看连接池状态
    pool_status = db.get_pool_status()
    print(f"连接池状态: {pool_status}")
    
    # 执行数据库操作
    db.add_keyword("测试关键词", "test")
    keywords = db.get_all_keywords()
    
    # 关闭连接池
    db.close()
```

### 2. 并发使用

```python
import threading

def worker(db, worker_id):
    """工作线程函数"""
    for i in range(10):
        # 每个线程可以安全地使用同一个数据库实例
        db.add_keyword(f"关键词_{worker_id}_{i}", "test")
        keywords = db.get_all_keywords()

# 创建多个线程
threads = []
for i in range(5):
    thread = threading.Thread(target=worker, args=(db, i))
    threads.append(thread)
    thread.start()

# 等待所有线程完成
for thread in threads:
    thread.join()
```

### 3. 连接池状态监控

```python
# 获取连接池状态
pool_status = db.get_pool_status()
print(f"连接池状态: {pool_status}")

# 输出示例:
# {
#     'pool_size': 8,           # 当前池中连接数
#     'max_pool_size': 10,      # 最大池大小
#     'overflow_connections': 2, # 溢出连接数
#     'max_overflow': 5,        # 最大溢出连接数
#     'total_connections': 10   # 总连接数
# }
```

## API对比

### 原始版本 vs 连接池版本

| 功能 | 原始版本 | 连接池版本 | 说明 |
|------|----------|------------|------|
| 连接管理 | 单连接 | 连接池 | 支持并发访问 |
| 性能 | 一般 | 更好 | 避免连接创建开销 |
| 线程安全 | 部分 | 完全 | 使用锁机制保证安全 |
| 状态监控 | 无 | 有 | 可监控连接池状态 |
| 配置 | 基础 | 增强 | 支持连接池参数 |

### 新增方法

```python
# 获取连接池状态
pool_status = db.get_pool_status()

# 设置连接池配置
db.set_connection_config(config, pool_size=15, max_overflow=10)
```

## 性能优化建议

### 1. 连接池大小配置

```python
# 根据应用需求调整连接池大小
# 轻量级应用
db = MySQLKeywordDBPool(config, pool_size=5, max_overflow=3)

# 中等负载应用
db = MySQLKeywordDBPool(config, pool_size=10, max_overflow=5)

# 高并发应用
db = MySQLKeywordDBPool(config, pool_size=20, max_overflow=10)
```

### 2. 最佳实践

- **合理设置连接池大小**: 根据并发用户数和数据库性能调整
- **监控连接池状态**: 定期检查连接池使用情况
- **及时关闭连接池**: 应用结束时调用 `close()` 方法
- **错误处理**: 妥善处理数据库连接异常

## 测试和验证

### 运行测试脚本

```bash
python test_mysql_pool.py
```

测试脚本包含：
- 基本功能测试
- 并发访问测试
- 性能对比测试

### 测试结果示例

```
==================================================
测试基本功能
==================================================
✓ 数据库连接成功
✓ 连接池状态: {'pool_size': 10, 'max_pool_size': 10, 'overflow_connections': 0, 'max_overflow': 5, 'total_connections': 10}
✓ 添加关键词成功
✓ 查询到 1 个关键词
✓ 统计信息: {'total_keywords': 1, 'keywords_by_type': {'test': 1}, 'total_detections': 0, 'today_detections': 0}
✓ 清理测试数据完成
✓ 连接池已关闭
```

## 迁移指南

### 从原始版本迁移到连接池版本

1. **更新导入语句**:
   ```python
   # 原始版本
   from database.mysql_db import MySQLKeywordDB
   
   # 连接池版本
   from database.mysql_pool_db import MySQLKeywordDBPool
   ```

2. **更新实例化代码**:
   ```python
   # 原始版本
   db = MySQLKeywordDB(config)
   
   # 连接池版本
   db = MySQLKeywordDBPool(config, pool_size=10, max_overflow=5)
   ```

3. **添加连接池状态监控**:
   ```python
   # 新增功能
   pool_status = db.get_pool_status()
   print(f"连接池状态: {pool_status}")
   ```

4. **确保正确关闭连接池**:
   ```python
   # 应用结束时
   db.close()
   ```

## 故障排除

### 常见问题

1. **连接池已满错误**
   - 增加 `pool_size` 或 `max_overflow` 参数
   - 检查是否有连接泄漏

2. **连接超时**
   - 检查数据库服务器状态
   - 调整连接超时参数

3. **性能问题**
   - 监控连接池使用情况
   - 根据实际负载调整连接池大小

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 监控连接池状态
def monitor_pool(db):
    while True:
        status = db.get_pool_status()
        print(f"连接池状态: {status}")
        time.sleep(5)

# 在单独线程中运行监控
monitor_thread = threading.Thread(target=monitor_pool, args=(db,))
monitor_thread.daemon = True
monitor_thread.start()
```

## 总结

MySQL连接池版本提供了更好的性能、并发支持和资源管理能力。通过合理配置连接池参数，可以显著提升应用的数据库访问性能。建议在生产环境中使用连接池版本，并根据实际负载情况进行调优。
