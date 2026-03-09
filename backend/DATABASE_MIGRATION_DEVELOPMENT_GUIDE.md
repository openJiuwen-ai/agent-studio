# 数据库迁移开发指南

本指南旨在帮助开发者在 OpenJiuWen Studio 项目中正确进行数据库结构的变更管理。本项目使用多种数据库技术栈，包括关系型数据库（MySQL/SQLite，使用 Alembic 管理）和向量数据库（Chroma/Milvus，应用层自动管理）。无论您是需要新增表、添加字段，还是修改现有的数据库结构，都请遵循本指南的操作规范。

## 1. 核心概念

本项目使用两类数据库系统，分别采用不同的迁移策略：

### 1.1 关系型数据库（MySQL/SQLite）- Alembic 管理

Alembic 是 SQLAlchemy 的数据库迁移工具。它允许我们通过编写 Python 脚本（迁移脚本）来定义数据库的变更，从而实现数据库结构的版本控制。

*   **Revision（版本）**: 每一次变更都对应一个版本文件，位于 `backend/upgrade/{mysql,sqlite}/alembic_{agent,ops}/versions/` 目录下。
*   **Upgrade（升级）**: 应用变更，将数据库升级到新版本。
*   **Downgrade（降级）**: 回滚变更，将数据库恢复到旧版本。
*   **Stamp（标记）**: 为已有数据库打上版本标签，不执行实际的数据库变更操作。


## 2. 版本升级说明

### 2.1 版本升级方式变更

本项目在不同版本阶段采用了不同的数据库升级方式：

#### 0.1.1 → 0.1.2 / 0.1.2 → 0.1.3
- **升级方式**: 自动数据库同步（Auto DB Sync）
- **说明**: 这些版本尚未采用 Alembic 管理数据库版本，代码中包含自动数据库同步功能，会自动同步新增的表字段
- **操作**: 不需要执行本文档中的 Alembic 升级命令，数据库变更会在应用启动时自动完成

#### 0.1.x → 0.1.4（及之后的版本）（含 0.1.1/0.1.2/0.1.3→0.1.4及之后的版本）
- **升级方式**: Alembic 迁移
- **说明**: 从 0.1.4 版本开始，项目正式采用 Alembic 进行数据库版本管理
- **操作**: 需要使用 `alembic stamp` 命令打标签和 `alembic upgrade` 命令升级数据库
- **具体流程**: 请参考本文档 5.1.3 和 5.1.4 节的详细说明

### 2.2 升级约束

⚠️ **重要**: 本升级流程仅支持**同类型数据库组件**的平滑升级。

**关系型数据库升级前必须确保**:
- 新旧版本的数据库组件类型完全一致
- MySQL 版本之间升级：必须都是 MySQL，不能跨数据库类型
- SQLite 版本之间升级：必须都是 SQLite，不能跨数据库类型
- 数据库连接配置中的数据库类型（MySQL/SQLite）在升级前后保持不变

**向量数据库升级注意事项**:
- **类型一致性**: 新旧版本的向量数据库类型必须保持一致（Chroma → Chroma，Milvus → Milvus）
  - Chroma 和 Milvus 的数据格式不兼容，不能直接互相迁移
  - 升级前后环境变量 `INDEX_MANAGER_TYPE` 必须保持不变


## 3. 工作原理

Alembic 的工作核心基于**状态对比**和**版本追踪**：

1.  **版本追踪 (`alembic_version` 表)**:
    *   Alembic 会在您的数据库中创建一个名为 `alembic_version` 的特殊表。
    *   这个表只存储一行数据：当前数据库所处的版本号（Revision ID）。
    *   每次执行 `upgrade` 或 `downgrade`，Alembic 都会更新这个表中的版本号，以此确立数据库的"当前坐标"。

2.  **状态对比 (Autogenerate)**:
    *   当您运行 `alembic -n <db_name> revision --autogenerate` 时，Alembic 会做两件事：
        *   **读取模型**: 加载您的 Python 代码中定义的 SQLAlchemy 模型（即您期望的数据库结构）。
        *   **读取数据库**: 连接到实际数据库，读取当前的表结构。
    *   它会对比这两者之间的差异（例如：模型里有 `age` 字段，但数据库里没有）。
    *   根据差异，自动生成包含 `op.create_table`、`op.add_column` 等指令的迁移脚本。

3.  **链式迁移**:
    *   每个迁移脚本内部都记录了 `down_revision`（上一个版本号）。
    *   这形成了一个链表结构：`Base -> Rev1 -> Rev2 -> ... -> Head`。
    *   Alembic 沿着这条链，按顺序执行脚本，从而将数据库从任意旧版本安全地迁移到最新版本。

---

## 4. 实战场景指南

### 4.1 常用命令速查

请在 `backend` 目录下执行以下命令：

| 操作 | 命令 | 说明 |
| :--- | :--- | :--- |
| **生成迁移脚本** | `alembic -n <db_name> revision --autogenerate -m "描述"` | 自动检测模型变更并生成脚本 |
| **应用迁移(升级)** | `alembic -n <db_name> upgrade head` | 将数据库升级到最新版本 |
| **回滚迁移(降级)** | `alembic -n <db_name> downgrade -1` | 回滚最近一次迁移 |
| **查看历史** | `alembic -n <db_name> history` | 查看所有迁移版本历史 |
| **查看当前版本** | `alembic -n <db_name> current` | 查看数据库当前所处的版本 |
| **标记版本(Stamp)** | `alembic -n <db_name> stamp <version>` | 为已有数据库打上版本标签（不执行变更） |

#### 4.1.1 `-n` 参数说明：多数据库配置

本项目使用**多个独立的 Alembic 配置**来管理不同的数据库。`-n` 参数用于指定要操作的数据库实例。

#### 数据库实例列表

| 数据库实例名称 | 数据库类型 | 用途 | 配置文件路径 |
| :--- | :--- | :--- | :--- |
| **alembic_sqlite_agent** | SQLite | Agent 数据库（智能体、工作流等） | `backend/upgrade/sqlite/alembic_agent/` |
| **alembic_sqlite_ops** | SQLite | Ops 数据库（提示词管理等） | `backend/upgrade/sqlite/alembic_ops/` |
| **alembic_mysql_agent** | MySQL | Agent 数据库（智能体、工作流等） | `backend/upgrade/mysql/alembic_agent/` |
| **alembic_mysql_ops** | MySQL | Ops 数据库（提示词管理等） | `backend/upgrade/mysql/alembic_ops/` |

#### 为什么需要多个数据库实例？

本项目将数据存储分离为两个独立的数据库：
- **Agent 数据库**: 存储智能体、工作流、知识库、执行记录等核心业务数据
- **Ops 数据库**: 存储提示词模板等运营管理数据

同时支持 **SQLite** 和 **MySQL** 两种数据库类型，因此需要 **4 个独立的 Alembic 配置**。

#### 使用 `-n` 参数的命令示例

```bash
# ✅ 正确：指定数据库实例
alembic -n alembic_sqlite_agent upgrade head
alembic -n alembic_mysql_ops upgrade head

# ❌ 错误：未指定数据库实例
alembic upgrade head
# 错误信息：ERROR: ConfigurationError: Multiple Configurations found
```

#### 完整命令示例

```bash
# SQLite Agent 数据库：生成迁移脚本
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add user profile"

# SQLite Agent 数据库：应用迁移
alembic -n alembic_sqlite_agent upgrade head

# MySQL Ops 数据库：生成迁移脚本
alembic -n alembic_mysql_ops revision --autogenerate -m "feat: add prompt template"

# MySQL Ops 数据库：应用迁移
alembic -n alembic_mysql_ops upgrade head

# 查看当前所有数据库实例的版本
for db in alembic_sqlite_agent alembic_sqlite_ops alembic_mysql_agent alembic_mysql_ops; do
    echo "=== $db ==="
    alembic -n $db current
done
```

#### 如何选择正确的数据库实例？

1. **确定数据库类型**：查看环境变量 `DB_TYPE`（sqlite 或 mysql）
2. **确定数据用途**：
   - 智能体、工作流、知识库相关 → Agent 数据库
   - 提示词模板相关 → Ops 数据库
3. **组合选择**：
   - SQLite + Agent → `alembic_sqlite_agent`
   - MySQL + Ops → `alembic_mysql_ops`

**重要提示**:
- 每个数据库实例都有独立的 `alembic_version` 表和迁移历史
- 不同数据库实例之间的迁移版本号是独立的，不可比较
- 开发时通常只需要关注当前使用的数据库类型（SQLite 或 MySQL）

### 4.2 场景一：新增表或字段（Create/Add）

这是最简单的场景，Alembic 的自动检测功能（`--autogenerate`）通常能完美处理。

1.  **修改模型代码**：在 SQLAlchemy 模型文件（如 `backend/app/models/`）中添加新的类或字段。
2.  **生成脚本**：
    ```bash
    alembic -n alembic_sqlite_agent revision --autogenerate -m "add_user_age_column"
    ```
3.  **检查脚本**：打开生成的 `versions/xxxx_add_user_age_column.py` 文件，确认 `upgrade()` 函数中包含了正确的 `op.create_table` 或 `op.add_column` 指令。
4.  **应用迁移**：
    ```bash
    alembic -n alembic_sqlite_agent upgrade head
    ```

### 4.3 场景二：删除字段或表（Drop）

⚠️ **注意**：Alembic 的自动检测功能**默认不会**检测到删除操作（为了防止误删数据）。您必须手动处理或显式确认。

**步骤：**

1.  **修改模型代码**：从代码中删除对应的类或字段。
2.  **生成基础脚本**：
    ```bash
    alembic -n alembic_sqlite_agent revision --autogenerate -m "drop_unused_column"
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
    alembic -n alembic_sqlite_agent upgrade head
    ```

### 4.4 场景三：重命名字段（Rename）

⚠️ **注意**：Alembic 无法自动识别重命名，它通常会将其识别为"删除旧字段" + "新增新字段"。这会导致**数据丢失**！必须手动使用 `alter_column`。

**步骤：**

1.  **修改模型代码**：将字段名从 `old_name` 改为 `new_name`。
2.  **生成基础脚本**：
    ```bash
    alembic -n alembic_sqlite_agent revision --autogenerate -m "rename_column"
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

### 4.5 场景四：编写可重入（Idempotent）的迁移脚本

由于 MySQL 的 DDL 操作（如 `CREATE TABLE`, `ADD COLUMN`）不支持事务回滚，如果迁移脚本在执行中途失败，再次运行 `upgrade` 会因为表或列已存在而报错。因此，建议编写**可重入**的迁移脚本。

本项目提供了统一的辅助函数来检查表、列、索引是否存在：

```python
from openjiuwen_studio.core.database.migration_utils import table_exists, column_exists, index_exists

def upgrade() -> None: 
    # 1. 创建表前检查是否存在
    if not table_exists('my_new_table'):
        op.create_table('my_new_table', ...)

    # 2. 添加列前检查是否存在
    if not column_exists('users', 'new_column'):
        op.add_column('users', sa.Column('new_column', sa.String(100)))

    # 3. 创建索引前检查是否存在
    if not index_exists('users', 'idx_user_email'):
        op.create_index('idx_user_email', 'users', ['email'])
```

**注意事项：**
- **SQLite 支持**: 这些辅助函数同样适用于 SQLite 迁移。
- **Batch 模式**: 在 SQLite 中使用 `op.batch_alter_table` 时，同样可以在 `with` 块内使用这些检查。
- **模板支持**: 新生成的迁移脚本已默认导入这些辅助函数。

### 4.6 场景五：修改字段类型或属性（Alter）

例如将 `String(50)` 改为 `String(100)`，或修改 `nullable` 属性。

**步骤：**

1.  **修改模型代码**：更新字段定义。
2.  **生成脚本**：
    ```bash
    alembic -n alembic_sqlite_agent revision --autogenerate -m "change_column_type"
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
    alembic -n alembic_sqlite_agent upgrade head
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

**步骤 2：检查数据库版本**

由于应用启动时 `main.py` 会尝试自动创建表（`Base.metadata.create_all`），如果在数据库版本未同步的情况下直接启动，可能会导致表结构冲突或覆盖。因此，建议在启动应用前先手动检查数据库版本。

```bash
# 查看当前数据库记录的版本
alembic -n alembic_sqlite_agent current

# 查看最新可用的版本
alembic -n alembic_sqlite_agent heads
```

**步骤 3：同步数据库版本**

根据检查结果进行操作：

1.  **如果版本已是最新**（`current` 与 `heads` 一致）：无需操作，直接进行下一步。
2.  **如果版本落后**（`current` 落后于 `heads`）：
    ```bash
    alembic -n alembic_sqlite_agent upgrade head
    ```
3.  **如果未显示当前版本但表已存在**（`current` 显示为空，但数据库里已有表）：
    这通常发生在已有数据库但未初始化 Alembic 的情况。请先标记版本（Stamp），再进行升级。
    *请参考下文 "6.1.3 如何处理已有数据但未使用 Alembic 迁移的数据库" 进行操作*

**步骤 4：启动应用**

确认数据库版本同步后，启动后端服务：

```bash
cd backend
python main.py
```

此时应用启动日志中应显示版本一致：
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
    alembic -n alembic_sqlite_agent stamp <version_number>
    ```
    ⚠️ **不要运行 `upgrade`**！`stamp` 命令只是记录版本号到 `alembic_version` 表，不执行任何 SQL 操作

3. **验证标记结果**：
    ```bash
    alembic -n alembic_sqlite_agent current
    ```
    应该显示刚标记的版本号

4. **后续开发**：之后可以正常使用 `alembic -n alembic_sqlite_agent revision --autogenerate` 生成新的迁移脚本

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



#### 5.1.4 0.1.2之后已发布版本基线标记

以下是各数据库类型的关键版本 Revision ID 对照表，供手动标记版本（Stamp）时参考。

| 数据库类型 | 服务组件 | v0.1.2 Revision ID | v0.1.3 Revision ID | v0.1.4 Revision ID |
| :--- | :--- | :--- | :--- | :--- |
| **MySQL** | **Agent** | `54351e123cf0` | `06a1f79bce8b` | `072ac1293a02` |
| **MySQL** | **Ops** | `80f110f929fc` | `13377a900fe2` | `13377a900fe2` |
| **SQLite** | **Agent** | `f458c7fb17a5` | `031b34b4dd30` | `8f4846812221` |
| **SQLite** | **Ops** | `b4f4c6589bc5` | `f6e49cd8c97d` | `f6e49cd8c97d` |


当前代码仓中的数据库迁移脚本基线是v0.1.2版本。对于 v0.1.1 升级到 v0.1.2 的用户，由于数据库结构没有变化，需要用户手动为数据库打一个 v0.1.2 stamp 标签，否则直接运行 `alembic -n <db_name> upgrade head` 会因为尝试创建已存在的表而失败。

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
    - 如果需要更新，运行：`alembic -n <db_name> upgrade head`
    - 确保本地数据库更新到最新版本后再进行开发

3.  **进行你的变更**: 现在，在最新的数据库结构上修改你的模型代码。

4.  **生成你的迁移脚本**:
    - 推荐：使用 `python generate_migration.py --autogenerate -m "feat: xxx"`
    - 或手动：运行 `alembic -n <db_name> revision --autogenerate ...`
    - 检查生成的迁移脚本是否符合预期

5.  **应用并测试迁移**: 在本地执行 `alembic -n <db_name> upgrade head`，测试迁移是否成功。

6.  **提交代码**: 将你的模型代码和新生成的迁移脚本一起提交。

### 解决冲突 (Merge)

如果你忘记了第 2 步，可能会遇到迁移分支冲突（migration branch）。

**场景**: 你和队友都基于版本 `A` 创建了各自的迁移脚本 `B1` 和 `B2`。当 `git pull` 后，Alembic 会检测到两个并行的“头”（head）。

**解决方案**:

1.  首先，将数据库升级到其中一个分支的头部，例如 `alembic -n <db_name> upgrade B1`。
2.  然后，运行 `alembic -n <db_name> merge heads -m "Merge parallel migrations B1 and B2"`。
3.  这会创建一个新的合并迁移文件 `C`，它将两个分支合并在一起。
    > **注意**：原来的迁移文件 `B1` 和 `B2` **不会被删除**，它们仍然存在于 `versions` 目录中。`merge` 操作只是创建了一个新的节点 `C`，它在依赖关系上同时指向 `B1` 和 `B2`，从而将两条分叉的路径重新汇聚。
4.  最后，将数据库升级到这个新的合并头部：`alembic -n <db_name> upgrade head`。

### 进阶：如果两个分支修改了同一个字段怎么办？

1. **人工审查**：在运行 `merge` 之前，务必检查 B1 和 B2 的内容。
2. **手动修正**：
   - **推荐（Rebase 策略）**：
     如果 B1 和 B2 冲突严重（例如一个重命名了字段，一个删除了字段），最好的办法是**放弃其中一个迁移脚本**。
     1. 将 B2 分支的迁移脚本删除。
     2. 将 B2 分支基于最新的 main（包含 B1）进行 rebase。
     3. 重新运行 `alembic -n <db_name> revision --autogenerate` 生成基于 B1 的新迁移脚本。
   - **备选（手动编辑）**：
     如果只是简单的属性修改，可以手动编辑 `upgrade()` 函数，确保逻辑顺序正确。




## 7. 最佳实践与注意事项

1.  **切勿直接修改数据库**：严禁使用 Navicat、DBeaver 等工具直接修改表结构。这会导致数据库状态与 Alembic 版本历史不一致，引发后续迁移失败。
2.  **保持原子性**：每次迁移最好只包含相关的变更。不要在一个迁移脚本中混合做"添加新功能表"和"重构旧表字段"的操作。
3.  **提交前测试**：在提交代码前，务必在本地执行 `upgrade` 和 `downgrade` 测试，确保迁移脚本既能向前升级，也能向后回滚。
4.  **团队协作**：
    *   在拉取他人代码后，第一时间执行 `alembic -n <db_name> upgrade head`。
    *   如果遇到版本冲突（多个 head），需要手动合并版本历史（`alembic -n <db_name> merge`）或重新生成迁移脚本。

## 8. 参考文档

*   [Alembic 官方文档](https://alembic.sqlalchemy.org/en/latest/)
*   [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)

## 9. 常见问题 (FAQ)

### 9.1 执行 alembic 命令时报错：file has no '[alembic]' section

**错误信息**：
```
ERROR: ConfigurationError: File has no '[alembic]' section which is absent from the ./backend/ini file
```

**问题原因**：
该问题是由于迁移命令没有指定 `-n` 参数导致。当前代码仓使用多个独立的 Alembic 配置来管理不同的数据库，需要通过 `-n` 参数指定具体的数据库名称。

**解决办法**：

在所有 alembic 命令中添加 `-n <db_name>` 参数，指定具体的数据库名称。

**正确命令示例**：

```bash
# SQLite Agent 数据库
alembic -n alembic_sqlite_agent upgrade head
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add new column"
alembic -n alembic_sqlite_agent current

# SQLite Ops 数据库
alembic -n alembic_sqlite_ops upgrade head
alembic -n alembic_sqlite_ops revision --autogenerate -m "feat: add new column"

# MySQL Agent 数据库
alembic -n alembic_mysql_agent upgrade head
alembic -n alembic_mysql_agent revision --autogenerate -m "feat: add new column"

# MySQL Ops 数据库
alembic -n alembic_mysql_ops upgrade head
alembic -n alembic_mysql_ops revision --autogenerate -m "feat: add new column"
```

**错误命令示例**：
```bash
# ❌ 错误：缺少 -n 参数
alembic upgrade head
alembic revision --autogenerate -m "feat: add new column"
```

**如何选择正确的数据库名称**：

请参考本文档 [4.1.1 `-n` 参数说明：多数据库配置](#411--n-参数说明多数据库配置) 章节，了解如何选择正确的数据库实例名称。

**可用的数据库名称**：
- `alembic_sqlite_agent` - SQLite Agent 数据库
- `alembic_sqlite_ops` - SQLite Ops 数据库
- `alembic_mysql_agent` - MySQL Agent 数据库
- `alembic_mysql_ops` - MySQL Ops 数据库
