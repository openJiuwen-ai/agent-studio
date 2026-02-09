# 统一迁移脚本生成工具使用指南

## 概述

`generate_migration.py` 是一个统一生成 MySQL 和 SQLite 迁移脚本的工具，避免分别为每个数据库执行 alembic 命令。

---

## 快速开始

### 基本使用

```bash
# 为所有数据库自动生成迁移脚本
python generate_migration.py --autogenerate -m "feat add user status field"

# 为所有数据库手动创建迁移脚本
python generate_migration.py --manual -m "fix correct data type issue"
```

---

## 命令参数

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-m, --message` | 迁移描述信息 | `-m "feat add user profile"` |

### 可选参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--autogenerate` | 自动生成（基于模型变化） | `--autogenerate` |
| `--manual` | 手动创建空白脚本 | `--manual` |
| `-d, --database` | 指定数据库（可多次使用） | `-d mysql_agent -d sqlite_agent` |

---

## 使用场景

### 场景1：自动生成（推荐）

**用途**：基于 SQLAlchemy 模型的变化自动生成迁移脚本

```bash
# 为所有4个数据库自动生成
python generate_migration.py --autogenerate -m "feat add user status field"
```

**输出**：
```
============================================================
开始生成迁移脚本: Add user status field
模式: 自动生成
数据库: ['MySQL Agent Database', 'MySQL Ops Database', 'SQLite Agent Database', 'SQLite Ops Database']
============================================================

✓ MySQL Agent Database: upgrade/mysql/alembic_agent/versions/add_user_status_field_xxxxx.py
✓ MySQL Ops Database: upgrade/mysql/alembic_ops/versions/add_user_status_field_xxxxx.py
✓ SQLite Agent Database: upgrade/sqlite/alembic_agent/versions/add_user_status_field_xxxxx.py
✓ SQLite Ops Database: upgrade/sqlite/alembic_ops/versions/add_user_status_field_xxxxx.py
```

---

### 场景2：手动创建

**用途**：创建空白的迁移脚本，手动编写迁移逻辑

```bash
# 为所有数据库创建空白脚本
python generate_migration.py --manual -m "feat custom data migration"
```

---

### 场景3：指定数据库

**用途**：只为特定的数据库生成迁移脚本

```bash
# 只为 MySQL Agent 数据库生成
python generate_migration.py --autogenerate -d mysql_agent -m "feat update agent schema"

# 为多个指定数据库生成
python generate_migration.py --autogenerate -d mysql_agent -d sqlite_agent -m "fix update schema"
```

---

## 对比传统方式

### 传统方式（繁琐）

```bash
# 需要分别为每个数据库执行命令
alembic -n alembic_mysql_agent revision --autogenerate -m "feat add user status"
alembic -n alembic_mysql_ops revision --autogenerate -m "feat add user status"
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat add user status"
alembic -n alembic_sqlite_ops revision --autogenerate -m "feat add user status"
```

### 新方式（简洁）

```bash
# 一次命令完成所有数据库
python generate_migration.py --autogenerate -m "feat add user status"
```

---

## 工作原理

### 1. 多配置支持

工具利用 `alembic.ini` 中的多配置段：

```ini
[alembic_mysql_agent]
[alembic_mysql_ops]
[alembic_sqlite_agent]
[alembic_sqlite_ops]
```

### 2. 循环调用

工具循环为每个配置调用 `alembic revision` 命令：

```python
for db in databases:
    alembic -n {db['config']} revision -m {message}
```

### 3. 动态环境变量注入

**关键特性**：为每个数据库动态注入正确的 `DB_TYPE` 环境变量

```python
# MySQL 配置
if "mysql" in config_name:
    db_type = "mysql"
    env["DB_TYPE"] = "mysql"  # 动态注入

# SQLite 配置
if "sqlite" in config_name:
    db_type = "sqlite"
    env["DB_TYPE"] = "sqlite"  # 动态注入
```

**为什么需要动态注入**：

1. **模型代码的条件判断**
   ```python
   # 模型代码中根据 DB_TYPE 决定字段类型
   if settings.DB_TYPE.lower() == "sqlite":
       id = mapped_column(Integer, ...)
   else:
       id = mapped_column(BigInteger, ...)
   ```

2. **确保正确的数据库结构**
   - MySQL alembic 需要生成 MySQL 类型的迁移
   - SQLite alembic 需要生成 SQLite 类型的迁移

3. **避免混淆**
   - `.env` 文件中的 `DB_TYPE` 只能是一个值
   - 通过动态注入，每个数据库都能获得正确的 `DB_TYPE`

### 4. 结果收集

收集每个数据库的生成结果，统一展示摘要。

---

## 生成的文件

### 文件位置

迁移脚本会生成到相应的目录：

```
backend/
├── upgrade/
│   ├── mysql/
│   │   ├── alembic_agent/versions/
│   │   │   └── add_user_status_field_xxxxx.py  # MySQL Agent
│   │   └── alembic_ops/versions/
│   │       └── add_user_status_field_xxxxx.py  # MySQL Ops
│   └── sqlite/
│       ├── alembic_agent/versions/
│       │   └── add_user_status_field_xxxxx.py  # SQLite Agent
│       └── alembic_ops/versions/
│           └── add_user_status_field_xxxxx.py  # SQLite Ops
```

### 文件命名

所有文件使用统一的命名格式：

```
{description}_{revision_id}.py
```

例如：
```
feat_add_user_status_field_4b4dd5bb39b4.py
```

---

## 高级用法

### 1. 结合便捷脚本使用

```bash
# 1. 生成迁移脚本
python generate_migration.py --autogenerate -m "feat add user profile"

# 2. 执行迁移
./migrate.sh mysql agent upgrade
./migrate.sh mysql ops upgrade
./migrate.sh sqlite agent upgrade
./migrate.sh sqlite ops upgrade
```

### 2. 只为需要的数据库生成

```bash
# 只为 MySQL 数据库生成（SQLite 可能不需要这个变更）
python generate_migration.py --autogenerate -d mysql_agent -d mysql_ops -m "feat add MySQL-specific features"
```


---

## 注意事项

### 1. 模型变更检查

**自动生成前**：
- 确保 SQLAlchemy 模型已正确修改
- 确保所有导入正确
- 建议先检查模型语法

```bash
# 检查模型语法
python -m py_compile openjiuwen_studio/models/xxx.py
```

### 2. 生成的脚本审查

**生成后**：
- 检查生成的迁移脚本是否正确
- 特别注意数据库特定的逻辑
- 确保 upgrade 和 downgrade 逻辑完整

### 3. 测试环境验证

**部署前**：
- 在测试环境验证迁移脚本
- 测试 upgrade 和 downgrade
- 确认数据完整性

---

## 故障排查

### 错误1：alembic 命令不可用

**错误信息**：
```
❌ 错误: alembic 命令不可用
```

**解决方案**：
```bash
# 检查 alembic 是否安装
pip list | grep alembic

# 如果未安装，安装 alembic
pip install alembic
```

### 错误2：找不到 alembic.ini

**错误信息**：
```
❌ 错误: 找不到 alembic.ini 文件
```

**解决方案**：
```bash
# 确保在 backend 目录下执行
cd backend
python generate_migration.py --autogenerate -m "Test"

```

### 错误3：部分数据库生成失败

**错误信息**：
```
⚠️ 警告: 1 个数据库生成失败
```

**解决方案**：
- 检查错误信息，定位具体问题
- 检查模型定义是否正确
- 检查数据库连接配置

---

## 最佳实践

### 1. 工作流程

```bash
# 1. 修改 SQLAlchemy 模型
vim openjiuwen_studio/models/user.py

# 2. 生成迁移脚本
python generate_migration.py --autogenerate -m "feat: add user status field"

# 3. 检查生成的脚本
ls upgrade/*/alembic_*/versions/add_user_status_field_*.py

# 4. 测试迁移
./migrate.sh mysql agent upgrade

# 5. 验证功能
# 运行应用测试相关功能
```

### 2. 描述信息规范

**命名约定**：描述信息必须以 `fix:` 或 `feat:` 开头

| 前缀 | 含义 | 使用场景 |
|------|------|----------|
| `fix:` | 修复 bug 或问题 | 修复数据库结构缺陷、回退错误变更等 |
| `feat:` | 新增功能或特性 | 添加新表、新字段、新索引等 |

```bash
# ✅ 推荐：遵循命名规范
python generate_migration.py --autogenerate -m "feat: add user profile table"
python generate_migration.py --autogenerate -m "fix: correct user email field type"
python generate_migration.py --autogenerate -m "feat: add index on user phone number"

# ❌ 不推荐：缺少前缀或格式错误
python generate_migration.py --autogenerate -m "Add user profile table"
python generate_migration.py --autogenerate -m "update"
python generate_migration.py --autogenerate -m "Add comprehensive user profile management system with advanced features"
```

### 3. 版本管理

```bash
# 为特定版本生成所有变更
python generate_migration.py --autogenerate -m "feat: v1.2.0 database schema updates"
```

---

## 总结

### 优势

- ✅ **一次命令**：同时为所有数据库生成迁移脚本
- ✅ **减少错误**：避免遗漏某个数据库
- ✅ **统一管理**：所有迁移脚本使用相同描述
- ✅ **简单易用**：清晰的命令行界面

### 适用场景

- 多数据库项目（MySQL + SQLite）
- 需要保持多个数据库同步
- 频繁进行数据库迁移

### 快速参考

```bash
# 自动生成（最常用）- 必须使用 feat: 或 fix: 前缀
python generate_migration.py --autogenerate -m "feat: add user status field"
python generate_migration.py --autogenerate -m "fix: correct email field type"

# 手动创建
python generate_migration.py --manual -m "feat: custom migration logic"

# 指定数据库
python generate_migration.py --autogenerate -d mysql_agent -m "feat: update agent schema"

# 查看帮助
python generate_migration.py --help
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-28
**适用版本**: 所有支持多数据库的项目
