# Alembic 数据库迁移开发指南

本指南旨在帮助开发者在 OpenJiuWen Studio 项目中正确使用 Alembic 进行数据库结构的变更管理。无论您是需要新增表、添加字段，还是修改现有的数据库结构，都请遵循本指南的操作规范。

## 1. 核心概念

Alembic 是 SQLAlchemy 的数据库迁移工具。它允许我们通过编写 Python 脚本（迁移脚本）来定义数据库的变更，从而实现数据库结构的版本控制。

*   **Revision（版本）**: 每一次变更都对应一个版本文件，位于 `backend/alembic/versions/` 目录下。
*   **Upgrade（升级）**: 应用变更，将数据库升级到新版本。
*   **Downgrade（降级）**: 回滚变更，将数据库恢复到旧版本。

## 2. 工作原理

Alembic 的工作核心基于**状态对比**和**版本追踪**：

1.  **版本追踪 (`alembic_version` 表)**:
    *   Alembic 会在您的数据库中创建一个名为 `alembic_version` 的特殊表。
    *   这个表只存储一行数据：当前数据库所处的版本号（Revision ID）。
    *   每次执行 `upgrade` 或 `downgrade`，Alembic 都会更新这个表中的版本号，以此确立数据库的"当前坐标"。

2.  **状态对比 (Autogenerate)**:
    *   当您运行 `alembic revision --autogenerate` 时，Alembic 会做两件事：
        *   **读取模型**: 加载您的 Python 代码中定义的 SQLAlchemy 模型（即您期望的数据库结构）。
        *   **读取数据库**: 连接到实际数据库，读取当前的表结构。
    *   它会对比这两者之间的差异（例如：模型里有 `age` 字段，但数据库里没有）。
    *   根据差异，自动生成包含 `op.create_table`、`op.add_column` 等指令的迁移脚本。

3.  **链式迁移**:
    *   每个迁移脚本内部都记录了 `down_revision`（上一个版本号）。
    *   这形成了一个链表结构：`Base -> Rev1 -> Rev2 -> ... -> Head`。
    *   Alembic 沿着这条链，按顺序执行脚本，从而将数据库从任意旧版本安全地迁移到最新版本。

## 3. 常用命令速查

请在 `backend` 目录下执行以下命令：

| 操作 | 命令 | 说明 |
| :--- | :--- | :--- |
| **生成迁移脚本** | `alembic revision --autogenerate -m "描述"` | 自动检测模型变更并生成脚本 |
| **应用迁移(升级)** | `alembic upgrade head` | 将数据库升级到最新版本 |
| **回滚迁移(降级)** | `alembic downgrade -1` | 回滚最近一次迁移 |
| **查看历史** | `alembic history` | 查看所有迁移版本历史 |
| **查看当前版本** | `alembic current` | 查看数据库当前所处的版本 |

---

## 4. 实战场景指南

### 场景一：新增表或字段（Create/Add）

这是最简单的场景，Alembic 的自动检测功能（`--autogenerate`）通常能完美处理。

**步骤：**

1.  **修改模型代码**：在 SQLAlchemy 模型文件（如 `backend/app/models/`）中添加新的类或字段。
2.  **生成脚本**：
    ```bash
    alembic revision --autogenerate -m "add_user_age_column"
    ```
3.  **检查脚本**：打开生成的 `versions/xxxx_add_user_age_column.py` 文件，确认 `upgrade()` 函数中包含了正确的 `op.create_table` 或 `op.add_column` 指令。
4.  **应用迁移**：
    ```bash
    alembic upgrade head
    ```

### 场景二：删除字段或表（Drop）

⚠️ **注意**：Alembic 的自动检测功能**默认不会**检测到删除操作（为了防止误删数据）。您必须手动处理或显式确认。

**步骤：**

1.  **修改模型代码**：从代码中删除对应的类或字段。
2.  **生成基础脚本**：
    ```bash
    alembic revision --autogenerate -m "drop_unused_column"
    ```
    *此时生成的脚本中可能为空，或者没有 drop 语句。*
3.  **手动编辑脚本**：打开生成的迁移文件，在 `upgrade()` 函数中手动添加删除指令：
    ```python
    def upgrade():
        # 删除 'users' 表中的 'age' 字段
        op.drop_column('users', 'age')
    
    def downgrade():
        # 降级时恢复该字段（记得加上类型）
        op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
    ```
4.  **应用迁移**：
    ```bash
    alembic upgrade head
    ```

### 场景三：重命名字段（Rename）

⚠️ **注意**：Alembic 无法自动识别重命名，它通常会将其识别为"删除旧字段" + "新增新字段"。这会导致**数据丢失**！必须手动使用 `alter_column`。

**步骤：**

1.  **修改模型代码**：将字段名从 `old_name` 改为 `new_name`。
2.  **生成基础脚本**：
    ```bash
    alembic revision --autogenerate -m "rename_column"
    ```
3.  **手动编辑脚本**：打开生成的迁移文件，**删除**其中自动生成的 `drop_column` 和 `add_column` 语句，替换为 `alter_column`：
    ```python
    def upgrade():
        # 将 'users' 表的 'old_name' 重命名为 'new_name'
        op.alter_column('users', 'old_name', new_column_name='new_name')

    def downgrade():
        # 回滚操作
        op.alter_column('users', 'new_name', new_column_name='old_name')
    ```
    *SQLite 特别说明：SQLite 对 `ALTER TABLE` 支持有限。如果遇到错误，可能需要使用 batch mode（Alembic 默认配置通常已开启，但需留意）。*

### 场景四：修改字段类型或属性（Alter）

例如将 `String(50)` 改为 `String(100)`，或修改 `nullable` 属性。

**步骤：**

1.  **修改模型代码**：更新字段定义。
2.  **生成脚本**：
    ```bash
    alembic revision --autogenerate -m "change_column_type"
    ```
3.  **检查脚本**：Alembic 通常能检测到类型变化，但建议仔细核对 `op.alter_column` 中的参数是否符合预期。
    ```python
    def upgrade():
        op.alter_column('users', 'username',
                   existing_type=sa.VARCHAR(length=50),
                   type_=sa.String(length=100),
                   existing_nullable=False)
    ```
4.  **应用迁移**：
    ```bash
    alembic upgrade head
    ```

---

## 5. openJiuWen studio backend 数据库迁移开发核心步骤

> **重要提示**：所有后端开发人员在开发代码的时候，必须遵循以下数据库迁移开发流程。
>
> **适用场景**：
> - ✅ 需要修改数据库结构（表、字段、索引等）
> - ✅ 需要添加、修改或删除数据
> - ✅ 连接的数据库版本和代码中的alembic脚本中最新的数据库版本不一致
> - ❌ 如果当前数据库版本与代码仓库一致，且无数据库变更需求，可跳过此步骤

⚠️ **特别注意：** 如果升级脚本中涉及到 `user_message` 表相关的操作，请不要执行任何改动。该表由记忆模块负责管理，请联系负责记忆模块的人员进行处理。

### 5.1 如何同步开发分支的数据库变动

在进行团队协作开发时，保持本地数据库与代码仓库同步是非常重要的。以下流程帮助您在拉取代码后正确更新本地数据库。

#### 5.1.1 标准同步流程

**步骤 1：拉取最新代码**

```bash
git pull
```

**步骤 2：启动应用检查版本**

```bash
cd backend
python main.py
```

应用启动时会自动执行版本检测，并输出详细的版本信息：

```log
================================================================================
📊 Alembic 版本检测
================================================================================
正在检查 agent 数据库版本...
   查询到当前版本: 7883f1b07bc2
正在获取 alembic_sqlite_agent 的最新版本...
✓ 使用 alembic heads 获取版本: alembic_sqlite_agent -> 7883f1b07bc3
⚠️  agent 数据库: 版本需要更新
   当前版本: 7883f1b07bc2
   最新版本: 7883f1b07bc3
```

**步骤 3：根据提示更新数据库**

- ✅ **如果版本已是最新**：无需任何操作，继续开发
- ⚠️  **如果需要更新**：执行提示的命令

示例如下：

```bash
# 更新 sqlite agent 数据库
alembic -n alembic_sqlite_agent upgrade head

# 更新 sqlite  ops 数据库
alembic -n alembic_sqlite_ops upgrade head
```

**步骤 4：验证更新成功**

再次启动应用，确认看到：
```log
✅ agent 数据库: 版本已是最新
   当前版本: 7883f1b07bc3
   最新版本: 7883f1b07bc3
```

#### 5.1.2 提交代码前的检查清单

在提交代码前，请确保：

- [ ] 本地数据库已更新到最新版本
- [ ] 应用启动时没有版本不匹配的警告
- [ ] 所有迁移脚本已正确生成
- [ ] 测试通过，功能正常

#### 5.1.3 如何处理已有数据但未使用 Alembic 迁移的数据库

**场景说明**：当你的数据库已经存在数据（例如当前是 v0.1.2 版本），但从未使用 Alembic 进行版本管理时，需要特殊处理。

**问题分析**：
- 数据库已经包含完整的表结构和数据
- 但缺少 `alembic_version` 表来记录版本信息
- 如果直接运行 `alembic revision --autogenerate`，会因为发现数据库与模型一致而生成空迁移脚本

**解决方案**：使用 `alembic stamp` 命令为数据库打上版本标签。

**操作步骤**：

1. **确认当前数据库版本**：检查你的数据库对应哪个版本（如 v0.1.2）

2. **标记数据库版本（Stamp）**：
    ```bash
    # 将数据库标记为对应的 alembic 版本
    alembic stamp <version_number>
    ```
    ⚠️ **不要运行 `upgrade`**！`stamp` 命令只是记录版本号到 `alembic_version` 表，不执行任何 SQL 操作

3. **验证标记结果**：
    ```bash
    alembic current
    ```
    应该显示刚标记的版本号

4. **后续开发**：之后可以正常使用 `alembic revision --autogenerate` 生成新的迁移脚本

**示例**：
```bash
# 假设你的数据库是 v0.1.2 版本，对应的 revision ID 是 f458c7fb17a5
alembic -n alembic_sqlite_agent stamp f458c7fb17a5

# 验证标记成功
alembic -n alembic_sqlite_agent current
# 输出: f458c7fb17a5

# 现在可以正常开发，生成新的迁移脚本
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add new column"
```



#### 5.1.4 v0.1.2 及之前版本基线标记

以下是各数据库类型的关键版本 Revision ID 对照表，供手动标记版本（Stamp）时参考。

| 数据库类型 | 服务组件 | v0.1.2 Revision ID | v0.1.3 Revision ID |
| :--- | :--- | :--- | :--- |
| **MySQL** | **Agent** | `54351e123cf0` | `06a1f79bce8b` |
| **MySQL** | **Ops** | `80f110f929fc` | `13377a900fe2` |
| **SQLite** | **Agent** | `f458c7fb17a5` | `031b34b4dd30` |
| **SQLite** | **Ops** | `b4f4c6589bc5` | `f6e49cd8c97d` |


当前代码仓中的数据库迁移脚本基线是v0.1.2版本。对于 v0.1.1 升级到 v0.1.2 的用户，由于数据库结构没有变化，需要用户手动为数据库打一个 v0.1.2 stamp 标签，否则直接运行 `alembic upgrade head` 会因为尝试创建已存在的表而失败。

**解决方案**: 使用 `alembic stamp` 命令，标记到一个**v0.1.2基线版本号**。

**MySQL 用户**:
```bash
# 标记 agent 数据库到 v0.1.2 基线版本
alembic -n alembic_mysql_agent stamp 54351e123cf0

# 标记 ops 数据库到 v0.1.2 基线版本
alembic -n alembic_mysql_ops stamp 13377a900fe2
```

**SQLite 用户**:
```bash
# 标记 agent 数据库到 v0.1.2 基线版本
alembic -n alembic_sqlite_agent stamp f458c7fb17a5

# 标记 ops 数据库到 v0.1.2 基线版本
alembic -n alembic_sqlite_ops stamp b4f4c6589bc5
```

#### 5.1.5 执行增量升级

在标记完成后，Alembic 就知道了当前数据库的版本是 v0.1.2。现在运行 `upgrade head`，它只会执行从基线版本到最新版本之间的所有增量迁移。

### 5.2 标准迁移流程 
标准的迁移流程分为三步：

### 第 1 步: 修改模型代码

-   **Agent 库**: 修改 `backend/openjiuwen_studio/models/` 目录下的模型文件。
-   **Ops 库**: 修改 `backend/openjiuwen_studio/ops/modules/prompt/infra/repositories/orm_repo.py` 文件。

进行您需要的变更，例如添加一个新字段或一张新表。

### 第 2 步: 生成迁移脚本

保存代码后，在 `backend` 目录下运行 `revision` 命令。Alembic 会将您的模型与数据库当前状态进行比较，并自动生成一个迁移脚本。

**注意**：如果修改了模型结构，需要同时为 MySQL 和 SQLite 生成迁移脚本。您可以使用以下两种方式：

#### 方式 1：使用统一生成脚本（推荐）

使用 `generate_migration.py` 脚本同时为所有数据库生成迁移脚本：

```bash
# 为所有数据库自动生成迁移脚本
python generate_migration.py --autogenerate -m "feat: add user profile table"
```

**优势**：
- 一次命令生成所有 4 个数据库的迁移脚本
- 自动注入正确的 DB_TYPE 环境变量
- 避免遗漏某个数据库

详细使用方法请参考 [GENERATE_MIGRATION_USAGE.md](./GENERATE_MIGRATION_USAGE.md) 文档。

#### 方式 2：分别生成（适用于特定数据库）

如果只需要为某个特定数据库生成迁移，可以手动执行：

-   **sqlite Agent 数据库**:
    ```bash
    alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add user profile table"
    ```

-   **sqlite Ops 数据库**:
    ```bash
    alembic -n alembic_sqlite_ops revision --autogenerate -m "feat: add ip_address to audit log"
    ```

-   **mysql Agent 数据库**:
    ```bash
    alembic -n alembic_mysql_agent revision --autogenerate -m "feat: add user profile table"
    ```

-   **mysql Ops 数据库**:
    ```bash
    alembic -n alembic_mysql_ops revision --autogenerate -m "feat: add ip_address to audit log"
    ```

#### 描述信息规范

**命名约定**：描述信息必须以 `fix:` 或 `feat:` 开头

| 前缀 | 含义 | 使用场景 |
|------|------|----------|
| `fix:` | 修复 bug 或问题 | 修复数据库结构缺陷、回退错误变更等 |
| `feat:` | 新增功能或特性 | 添加新表、新字段、新索引等 |

**示例**：

```bash
# ✅ 推荐：遵循命名规范
python generate_migration.py --autogenerate -m "feat: add user profile table"
python generate_migration.py --autogenerate -m "fix: correct user email field type"

# ❌ 不推荐：缺少前缀或格式错误
python generate_migration.py --autogenerate -m "add user profile table"
python generate_migration.py --autogenerate -m "update"
```

> **提示**: `-m` 参数后的描述信息至关重要，它会成为版本历史的一部分，帮助团队理解每次变更的目的。

### 第 3 步: 应用迁移

生成的脚本只是一个计划。运行 `upgrade head` 命令来执行这个计划，将变更应用到数据库。

-   **sqlite Agent 数据库**:
    ```bash
    alembic -n alembic_sqlite_agent upgrade head
    ```

-   **sqlite Ops 数据库**:
    ```bash
    alembic -n alembic_sqlite_ops upgrade head
    ```


-   **mysql Agent 数据库**:
    ```bash
    alembic -n alembic_mysql_agent upgrade head
    ```

-   **mysql Ops 数据库**:
    ```bash
    alembic -n alembic_mysql_ops upgrade head
    ```

---

## 6. 如何进行团队协作

当多名开发者同时进行数据库结构变更时，可能会产生冲突。遵循以下流程可以有效避免和解决这些问题。

### 黄金流程

1.  **拉取最新代码**: 在开始任何模型修改之前，先 `git pull` 获取最新的代码，包括队友可能已经提交的迁移脚本。

2.  **更新本地数据库**:
    - 启动应用检查版本：`python main.py`
    - 查看版本检测日志，确认是否需要更新
    - 如果需要更新，运行：`alembic upgrade head` (和/或 `-n alembic_ops`)
    - 确保本地数据库更新到最新版本后再进行开发

3.  **进行你的变更**: 现在，在最新的数据库结构上修改你的模型代码。

4.  **生成你的迁移脚本**:
    - 推荐：使用 `python generate_migration.py --autogenerate -m "feat: xxx"`
    - 或手动：运行 `alembic revision --autogenerate ...`
    - 检查生成的迁移脚本是否符合预期

5.  **应用并测试迁移**: 在本地执行 `alembic upgrade head`，测试迁移是否成功。

6.  **提交代码**: 将你的模型代码和新生成的迁移脚本一起提交。

### 解决冲突 (Merge)

如果你忘记了第 2 步，可能会遇到迁移分支冲突（migration branch）。

**场景**: 你和队友都基于版本 `A` 创建了各自的迁移脚本 `B1` 和 `B2`。当 `git pull` 后，Alembic 会检测到两个并行的“头”（head）。

**解决方案**:

1.  首先，将数据库升级到其中一个分支的头部，例如 `alembic upgrade B1`。
2.  然后，运行 `alembic merge heads -m "Merge parallel migrations B1 and B2"`。
3.  这会创建一个新的合并迁移文件 `C`，它将两个分支合并在一起。
    > **注意**：原来的迁移文件 `B1` 和 `B2` **不会被删除**，它们仍然存在于 `versions` 目录中。`merge` 操作只是创建了一个新的节点 `C`，它在依赖关系上同时指向 `B1` 和 `B2`，从而将两条分叉的路径重新汇聚。
4.  最后，将数据库升级到这个新的合并头部：`alembic upgrade head`。

### 进阶：如果两个分支修改了同一个字段怎么办？

1. **人工审查**：在运行 `merge` 之前，务必检查 B1 和 B2 的内容。
2. **手动修正**：
   - **推荐（Rebase 策略）**：
     如果 B1 和 B2 冲突严重（例如一个重命名了字段，一个删除了字段），最好的办法是**放弃其中一个迁移脚本**。
     1. 将 B2 分支的迁移脚本删除。
     2. 将 B2 分支基于最新的 main（包含 B1）进行 rebase。
     3. 重新运行 `alembic revision --autogenerate` 生成基于 B1 的新迁移脚本。
   - **备选（手动编辑）**：
     如果只是简单的属性修改，可以手动编辑 `upgrade()` 函数，确保逻辑顺序正确。




## 7. 最佳实践与注意事项

1.  **切勿直接修改数据库**：严禁使用 Navicat、DBeaver 等工具直接修改表结构。这会导致数据库状态与 Alembic 版本历史不一致，引发后续迁移失败。
2.  **保持原子性**：每次迁移最好只包含相关的变更。不要在一个迁移脚本中混合做"添加新功能表"和"重构旧表字段"的操作。
3.  **提交前测试**：在提交代码前，务必在本地执行 `upgrade` 和 `downgrade` 测试，确保迁移脚本既能向前升级，也能向后回滚。
4.  **团队协作**：
    *   在拉取他人代码后，第一时间执行 `alembic upgrade head`。
    *   如果遇到版本冲突（多个 head），需要手动合并版本历史（`alembic merge`）或重新生成迁移脚本。

## 8. 参考文档

*   [Alembic 官方文档](https://alembic.sqlalchemy.org/en/latest/)
*   [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)
