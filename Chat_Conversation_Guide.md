# 聊天对话保存功能使用指南

## 概述

本功能为消息违规检测系统添加了聊天对话保存功能，能够自动获取并保存用户与客服之间的完整对话记录，支持A到B、B到A的对话形式。

## 功能特性

### 1. 数据库表结构

新增了 `chat_conversations` 表，包含以下字段：

- `id`: 主键，自增
- `user_name`: 用户名
- `conversation_data`: 对话数据（JSON格式）
- `message_count`: 消息数量
- `last_message_time`: 最后消息时间
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. 对话数据格式

每条对话记录包含以下信息：

```json
{
  "sender": "A",  // A表示用户，B表示客服
  "message": "消息内容",
  "timestamp": "2025-09-10 10:00:00"
}
```

### 3. 主要功能

#### 自动保存对话
- 检测到用户时自动获取完整对话
- 按时间顺序保存A到B、B到A的对话
- 自动去重，避免重复保存相同消息

#### 对话管理
- 支持获取指定用户的对话记录
- 支持获取所有对话记录
- 支持删除指定用户的对话记录

#### 统计信息
- 总对话数
- 总消息数
- 今日新增对话数
- 最近活跃用户

## 使用方法

### 1. 自动保存

当消息检测系统运行时，会自动：

1. 点击用户获取对话
2. 解析对话内容，识别发送者（A/B）
3. 保存完整对话到数据库
4. 检测对话中的违规内容

### 2. 手动操作

#### 保存对话
```python
from database.mysql_pool_db import MySQLKeywordDBPool

# 创建数据库实例
db = MySQLKeywordDBPool(config)

# 对话数据
conversation_data = [
    {
        "sender": "A",
        "message": "你好，我想了解一下贷款业务",
        "timestamp": "2025-09-10 10:00:00"
    },
    {
        "sender": "B", 
        "message": "您好，很高兴为您服务",
        "timestamp": "2025-09-10 10:01:00"
    }
]

# 保存对话
success = db.save_chat_conversation("用户名", conversation_data)
```

#### 获取对话
```python
# 获取指定用户的对话
conversation = db.get_chat_conversation("用户名")

# 获取所有对话记录
all_conversations = db.get_all_chat_conversations()
```

#### 获取统计信息
```python
# 获取聊天统计信息
stats = db.get_chat_statistics()
print(f"总对话数: {stats['total_conversations']}")
print(f"总消息数: {stats['total_messages']}")
```

## 检测结果增强

### 1. 发送者识别

检测结果现在会显示消息的发送者：

- **用户 (A)**: 表示用户发送的消息
- **客服 (B)**: 表示客服发送的消息

### 2. 完整对话检测

系统会检测整个对话中的所有违规内容，包括：

- 用户发送的违规消息
- 客服发送的违规消息
- 按时间顺序显示检测结果

## 数据库操作

### 1. 表创建

系统启动时会自动创建 `chat_conversations` 表：

```sql
CREATE TABLE IF NOT EXISTS chat_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL,
    conversation_data JSON NOT NULL,
    message_count INT DEFAULT 0,
    last_message_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_name),
    INDEX idx_last_message_time (last_message_time),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

### 2. 数据合并

当保存已存在用户的对话时，系统会：

1. 获取现有对话数据
2. 合并新消息（去重）
3. 按时间排序
4. 更新数据库记录

## 注意事项

### 1. 发送者识别

系统通过CSS类名判断消息发送者：

- `leadsCsUI-MessageItem_left`: 用户发送（A）
- `leadsCsUI-MessageItem_right`: 客服发送（B）

如果页面结构发生变化，可能需要调整识别逻辑。

### 2. 时间戳处理

- 优先使用页面中的时间戳
- 如果无法获取，使用当前系统时间
- 时间格式：`YYYY-MM-DD HH:MM:SS`

### 3. 性能考虑

- 对话数据以JSON格式存储，便于查询和更新
- 自动去重避免重复数据
- 使用索引优化查询性能

## 示例数据

### 对话数据示例
```json
[
  {
    "sender": "A",
    "message": "你好，我想了解一下贷款业务",
    "timestamp": "2025-09-10 10:00:00"
  },
  {
    "sender": "B", 
    "message": "您好，很高兴为您服务。请问您需要什么类型的贷款？",
    "timestamp": "2025-09-10 10:01:00"
  },
  {
    "sender": "A",
    "message": "我想申请个人信用贷款，额度大概10万",
    "timestamp": "2025-09-10 10:02:00"
  }
]
```

### 检测结果示例
```
时间: 2025-09-10 10:02:00
用户: 测试用户001 (用户)
消息: 我想申请个人信用贷款，额度大概10万
匹配结果: 贷款(exact)
```

## 总结

聊天对话保存功能为消息违规检测系统提供了完整的数据记录能力，支持：

- ✅ 自动获取和保存完整对话
- ✅ A到B、B到A的对话形式
- ✅ 自动去重和合并
- ✅ 违规内容检测增强
- ✅ 丰富的统计信息
- ✅ 灵活的查询接口

这个功能大大增强了系统的数据记录和分析能力，为后续的数据分析和报告生成提供了基础。
