# Database Migration Development Guide

This guide is designed to help developers properly manage database structure changes in the OpenJiuWen Studio project. This project uses multiple database technology stacks, including relational databases (MySQL/SQLite, managed by Alembic) and vector databases (Chroma/Milvus, automatically managed at the application layer). Whether you need to add new tables, add fields, or modify existing database structures, please follow the operation specifications in this guide.

## 1. Core Concepts

This project uses two types of database systems, each adopting different migration strategies:

### 1.1 Relational Databases (MySQL/SQLite) - Alembic Managed

Alembic is SQLAlchemy's database migration tool. It allows us to define database changes by writing Python scripts (migration scripts), thereby implementing version control for database structures.

* **Revision**: Each change corresponds to a version file located in `backend/upgrade/{mysql,sqlite}/alembic_{agent,ops}/versions/`.
* **Upgrade**: Apply changes to upgrade the database to a new version.
* **Downgrade**: Rollback changes to restore the database to an old version.
* **Stamp**: Tag an existing database with a version label without executing actual database change operations.

## 2. Version Upgrade Notes

### 2.1 Version Upgrade Method Changes

This project adopted different database upgrade methods during different version stages:

#### 0.1.1 → 0.1.2 / 0.1.2 → 0.1.3
- **Upgrade Method**: Auto DB Sync
- **Description**: These versions did not yet use Alembic for database version management. The code includes automatic database synchronization functionality that automatically synchronizes newly added table fields.
- **Operation**: No need to execute the Alembic upgrade commands in this document. Database changes are completed automatically when the application starts.

#### 0.1.x → 0.1.4 (and later versions) (including 0.1.1/0.1.2/0.1.3→0.1.4 and later versions)
- **Upgrade Method**: Alembic Migration
- **Description**: Starting from version 0.1.4, the project officially adopted Alembic for database version management.
- **Operation**: Need to use `alembic stamp` command to tag and `alembic upgrade` command to upgrade the database.
- **Specific Process**: Please refer to the detailed instructions in sections 5.1.3 and 5.1.4 of this document.

### 2.2 Upgrade Constraints

⚠️ **Important**: This upgrade process only supports smooth upgrades of **same-type database components**.

**Before upgrading relational databases, ensure**:
- The database component types of new and old versions are completely consistent
- MySQL version upgrades: Must both be MySQL, cannot cross database types
- SQLite version upgrades: Must both be SQLite, cannot cross database types
- The database type (MySQL/SQLite) in the database connection configuration remains unchanged before and after upgrades

**Vector Database Upgrade Notes**:
- **Type Consistency**: The vector database types of new and old versions must remain consistent (Chroma → Chroma, Milvus → Milvus)
  - Chroma and Milvus data formats are incompatible and cannot be directly migrated to each other
  - Environment variable `INDEX_MANAGER_TYPE` must remain unchanged before and after upgrades

## 3. How It Works

The core of Alembic's operation is based on **state comparison** and **version tracking**:

1. **Version Tracking (`alembic_version` table)**:
   * Alembic creates a special table named `alembic_version` in your database.
   * This table stores only one row of data: the version number (Revision ID) of the current database state.
   * Each time `upgrade` or `downgrade` is executed, Alembic updates the version number in this table, thereby establishing the "current coordinate" of the database.

2. **State Comparison (Autogenerate)**:
   * When you run `alembic revision --autogenerate`, Alembic does two things:
       * **Read Model**: Load the SQLAlchemy models defined in your Python code (i.e., your expected database structure).
       * **Read Database**: Connect to the actual database and read the current table structure.
   * It compares the differences between the two (for example: the model has an `age` field, but the database does not).
   * Based on the differences, it automatically generates migration scripts containing `op.create_table`, `op.add_column` and other instructions.

3. **Chain Migration**:
   * Each migration script internally records `down_revision` (previous version number).
   * This forms a linked list structure: `Base -> Rev1 -> Rev2 -> ... -> Head`.
   * Alembic follows this chain and executes scripts in sequence, thereby safely migrating the database from any old version to the latest version.

## 4. Common Commands Quick Reference

Please execute the following commands in the `backend` directory:

| Operation | Command | Description |
| :--- | :--- | :--- |
| **Generate Migration Script** | `alembic revision --autogenerate -m "description"` | Automatically detect model changes and generate scripts |
| **Apply Migration (Upgrade)** | `alembic upgrade head` | Upgrade database to the latest version |
| **Rollback Migration (Downgrade)** | `alembic downgrade -1` | Rollback the most recent migration |
| **View History** | `alembic history` | View all migration version history |
| **View Current Version** | `alembic current` | View the current version of the database |
| **Stamp Version** | `alembic stamp <version>` | Tag an existing database with a version label (without executing changes) |

### 4.1 `-n` Parameter Description: Multi-Database Configuration

This project uses **multiple independent Alembic configurations** to manage different databases. The `-n` parameter is used to specify the database instance to operate on.

#### Database Instance List

| Database Instance Name | Database Type | Purpose | Configuration File Path |
| :--- | :--- | :--- | :--- |
| **alembic_sqlite_agent** | SQLite | Agent Database (agents, workflows, etc.) | `backend/upgrade/sqlite/alembic_agent/` |
| **alembic_sqlite_ops** | SQLite | Ops Database (prompt management, etc.) | `backend/upgrade/sqlite/alembic_ops/` |
| **alembic_mysql_agent** | MySQL | Agent Database (agents, workflows, etc.) | `backend/upgrade/mysql/alembic_agent/` |
| **alembic_mysql_ops** | MySQL | Ops Database (prompt management, etc.) | `backend/upgrade/mysql/alembic_ops/` |

#### Why Do We Need Multiple Database Instances?

This project separates data storage into two independent databases:
- **Agent Database**: Stores core business data such as agents, workflows, knowledge bases, execution records
- **Ops Database**: Stores operational management data such as prompt templates

While supporting both **SQLite** and **MySQL** database types, **4 independent Alembic configurations** are required.

#### Command Examples Using `-n` Parameter

```bash
# ✅ Correct: Specify database instance
alembic -n alembic_sqlite_agent upgrade head
alembic -n alembic_mysql_ops upgrade head

# ❌ Incorrect: Database instance not specified
alembic upgrade head
# Error message: ERROR: ConfigurationError: Multiple Configurations found
```

#### Complete Command Examples

```bash
# SQLite Agent Database: Generate migration script
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add user profile"

# SQLite Agent Database: Apply migration
alembic -n alembic_sqlite_agent upgrade head

# MySQL Ops Database: Generate migration script
alembic -n alembic_mysql_ops revision --autogenerate -m "feat: add prompt template"

# MySQL Ops Database: Apply migration
alembic -n alembic_mysql_ops upgrade head

# View current versions of all database instances
for db in alembic_sqlite_agent alembic_sqlite_ops alembic_mysql_agent alembic_mysql_ops; do
    echo "=== $db ==="
    alembic -n $db current
done
```

#### How to Choose the Correct Database Instance?

1. **Determine Database Type**: Check environment variable `DB_TYPE` (sqlite or mysql)
2. **Determine Data Purpose**:
   - Agents, workflows, knowledge bases related → Agent Database
   - Prompt templates related → Ops Database
3. **Combination Selection**:
   - SQLite + Agent → `alembic_sqlite_agent`
   - MySQL + Ops → `alembic_mysql_ops`

**Important Notes**:
- Each database instance has independent `alembic_version` table and migration history
- Migration version numbers between different database instances are independent and cannot be compared
- During development, you usually only need to focus on the currently used database type (SQLite or MySQL)

---

## 5. Practical Scenario Guide

### Scenario 1: Add New Table or Field (Create/Add)

This is the simplest scenario. Alembic's automatic detection feature (`--autogenerate`) can usually handle it perfectly.

**Steps:**

1. **Modify Model Code**: Add new classes or fields in SQLAlchemy model files (such as `backend/app/models/`).
2. **Generate Script**:
    ```bash
    alembic revision --autogenerate -m "add_user_age_column"
    ```
3. **Check Script**: Open the generated `versions/xxxx_add_user_age_column.py` file and confirm that the `upgrade()` function contains the correct `op.create_table` or `op.add_column` instructions.
4. **Apply Migration**:
    ```bash
    alembic upgrade head
    ```

### Scenario 2: Drop Field or Table (Drop)

⚠️ **Note**: Alembic's automatic detection feature **does not** detect deletion operations by default (to prevent accidental data deletion). You must handle it manually or explicitly confirm.

**Steps:**

1. **Modify Model Code**: Delete the corresponding class or field from the code.
2. **Generate Base Script**:
    ```bash
    alembic revision --autogenerate -m "drop_unused_column"
    ```
    *At this point, the generated script may be empty or not contain drop statements.*
3. **Manually Edit Script**: Open the generated migration file and manually add deletion instructions in the `upgrade()` function:
    ```python
    def upgrade():
        # Drop the 'age' field from the 'users' table
        op.drop_column('users', 'age')

    def downgrade():
        # Restore the field when downgrading (remember to add the type)
        op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
    ```
4. **Apply Migration**:
    ```bash
    alembic upgrade head
    ```

### Scenario 3: Rename Field (Rename)

⚠️ **Note**: Alembic cannot automatically identify renaming. It usually recognizes it as "delete old field" + "add new field". This will cause **data loss**! You must manually use `alter_column`.

**Steps:**

1. **Modify Model Code**: Change the field name from `old_name` to `new_name`.
2. **Generate Base Script**:
    ```bash
    alembic revision --autogenerate -m "rename_column"
    ```
3. **Manually Edit Script**: Open the generated migration file, **delete** the automatically generated `drop_column` and `add_column` statements, and replace with `alter_column`:
    ```python
    def upgrade():
        # Rename 'old_name' to 'new_name' in the 'users' table
        op.alter_column('users', 'old_name', new_column_name='new_name')

    def downgrade():
        # Rollback operation
        op.alter_column('users', 'new_name', new_column_name='old_name')
    ```
    *SQLite Special Note: SQLite has limited support for `ALTER TABLE`. If you encounter an error, you may need to use batch mode (Alembic default configuration usually has this enabled, but pay attention).*

### Scenario 4: Write Idempotent Migration Scripts

Since MySQL's DDL operations (such as `CREATE TABLE`, `ADD COLUMN`) do not support transaction rollback, if the migration script fails midway through execution, running `upgrade` again will cause errors because tables or columns already exist. Therefore, it is recommended to write **idempotent** migration scripts.

This project provides unified helper functions to check whether tables, columns, and indexes exist:

```python
from openjiuwen_studio.core.database.migration_utils import table_exists, column_exists, index_exists

def upgrade() -> None:
    # 1. Check before creating table
    if not table_exists('my_new_table'):
        op.create_table('my_new_table', ...)

    # 2. Check before adding column
    if not column_exists('users', 'new_column'):
        op.add_column('users', sa.Column('new_column', sa.String(100)))

    # 3. Check before creating index
    if not index_exists('users', 'idx_user_email'):
        op.create_index('idx_user_email', 'users', ['email'])
```

**Notes:**
- **SQLite Support**: These helper functions are also applicable to SQLite migrations.
- **Batch Mode**: When using `op.batch_alter_table` in SQLite, you can also use these checks within the `with` block.
- **Template Support**: Newly generated migration scripts have imported these helper functions by default.

### Scenario 5: Modify Field Type or Attributes (Alter)

For example, changing `String(50)` to `String(100)`, or modifying `nullable` attributes.

**Steps:**

1. **Modify Model Code**: Update field definitions.
2. **Generate Script**:
    ```bash
    alembic revision --autogenerate -m "change_column_type"
    ```
3. **Check Script**: Alembic can usually detect type changes, but it is recommended to carefully verify whether the parameters in `op.alter_column` meet expectations.
    ```python
    def upgrade():
        op.alter_column('users', 'username',
                   existing_type=sa.VARCHAR(length=50),
                   type_=sa.String(length=100),
                   existing_nullable=False)
    ```
4. **Apply Migration**:
    ```bash
    alembic upgrade head
    ```

---

## 6. openJiuWen Studio Backend Database Migration Development Core Steps

> **Important Note**: All backend developers must follow the following database migration development process when developing code.
>
> **Applicable Scenarios**:
> - ✅ Need to modify database structure (tables, fields, indexes, etc.)
> - ✅ Need to add, modify, or delete data
> - ✅ The connected database version is inconsistent with the latest database version in the alembic scripts in the code
> - ❌ If the current database version is consistent with the code repository and there is no database change requirement, you can skip this step

⚠️ **Special Attention**: If the upgrade script involves operations related to the `user_message` table, please do not execute any changes. This table is managed by the memory module. Please contact the personnel responsible for the memory module to handle it.

### 6.1 How to Sync Database Changes in Development Branches

When doing collaborative development, keeping your local database synchronized with the code repository is very important. The following process helps you correctly update your local database after pulling code.

#### 6.1.1 Standard Sync Process

**Step 1: Pull Latest Code**

```bash
git pull
```

**Step 2: Check Database Version**

Since `main.py` will try to automatically create tables (`Base.metadata.create_all`) when the application starts, if you start the application directly without synchronizing the database version, it may cause table structure conflicts or overwrites. Therefore, it is recommended to manually check the database version before starting the application.

```bash
# View the version recorded by the current database
alembic -n alembic_sqlite_agent current

# View the latest available version
alembic -n alembic_sqlite_agent heads
```

**Step 3: Sync Database Version**

Operate according to the check results:

1. **If the version is already the latest** (`current` is consistent with `heads`): No operation needed, proceed to the next step.
2. **If the version is behind** (`current` is behind `heads`):
    ```bash
    alembic -n alembic_sqlite_agent upgrade head
    ```
3. **If no current version is displayed but tables already exist** (`current` is empty, but tables already exist in the database):
    This usually happens when there is an existing database but Alembic has not been initialized. Please first stamp the version (Stamp), then upgrade.
    *Please refer to the section below "6.1.3 How to Handle Existing Databases That Have Not Used Alembic Migration" for operation*

**Step 4: Start Application**

After confirming that the database version is synchronized, start the backend service:

```bash
cd backend
python main.py
```

At this point, the application startup log should show consistent versions:
```log
✅ agent database: version is already up to date
   Current version: 7883f1b07bc3
   Latest version: 7883f1b07bc3
```

#### 6.1.2 Pre-Commit Checklist

Before committing code, please ensure:

- [ ] Local database has been updated to the latest version
- [ ] No version mismatch warnings when starting the application
- [ ] All migration scripts have been correctly generated
- [ ] Tests passed, functionality works normally

#### 6.1.3 How to Handle Existing Databases That Have Not Used Alembic Migration

**Scenario Description**: When your database already has data (for example, currently version v0.1.2), but has never used Alembic for version management, special handling is required.

**Problem Analysis**:
- The database already contains complete table structures and data
- But lacks the `alembic_version` table to record version information
- If you run `alembic revision --autogenerate` directly, it will generate an empty migration script because it finds the database consistent with the model

**Solution**: Use the `alembic stamp` command to tag the database with a version label.

**Operation Steps**:

1. **Confirm Current Database Version**: Check which version your database corresponds to (such as v0.1.2)

2. **Stamp Database Version**:
    ```bash
    # Tag the database with the corresponding alembic version
    alembic stamp <version_number>
    ```
    ⚠️ **Do not run `upgrade`**! The `stamp` command only records the version number to the `alembic_version` table and does not execute any SQL operations

3. **Verify Stamp Result**:
    ```bash
    alembic current
    ```
    Should display the just-stamped version number

4. **Subsequent Development**: Afterward, you can normally use `alembic revision --autogenerate` to generate new migration scripts

**Example**:
```bash
# Assuming your database is version v0.1.2, the corresponding revision ID is f458c7fb17a5
alembic -n alembic_sqlite_agent stamp f458c7fb17a5

# Verify stamp success
alembic -n alembic_sqlite_agent current
# Output: f458c7fb17a5

# Now you can develop normally and generate new migration scripts
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add new column"
```

#### 6.1.4 Released Version Baseline Marking After 0.1.2

The following is a reference table of key version Revision IDs for each database type, for use when manually stamping versions (Stamp).

| Database Type | Service Component | v0.1.2 Revision ID | v0.1.3 Revision ID | v0.1.4 Revision ID |
| :--- | :--- | :--- | :--- | :--- |
| **MySQL** | **Agent** | `54351e123cf0` | `06a1f79bce8b` | `072ac1293a02` |
| **MySQL** | **Ops** | `80f110f929fc` | `13377a900fe2` | `13377a900fe2` |
| **SQLite** | **Agent** | `f458c7fb17a5` | `031b34b4dd30` | `8f4846812221` |
| **SQLite** | **Ops** | `b4f4c6589bc5` | `f6e49cd8c97d` | `f6e49cd8c97d` |

The baseline for database migration scripts in the current code repository is version v0.1.2. For users upgrading from v0.1.1 to v0.1.2, since there are no database structure changes, users need to manually stamp their database with a v0.1.2 label, otherwise running `alembic upgrade head` directly will fail because it tries to create existing tables.

**Solution**: Use the `alembic stamp` command to stamp to a **v0.1.2 baseline version number**.

**MySQL Users**:
```bash
# Stamp agent database to v0.1.2 baseline version
alembic -n alembic_mysql_agent stamp 54351e123cf0

# Stamp ops database to v0.1.2 baseline version
alembic -n alembic_mysql_ops stamp 13377a900fe2
```

**SQLite Users**:
```bash
# Stamp agent database to v0.1.2 baseline version
alembic -n alembic_sqlite_agent stamp f458c7fb17a5

# Stamp ops database to v0.1.2 baseline version
alembic -n alembic_sqlite_ops stamp b4f4c6589bc5
```

#### 6.1.5 Execute Incremental Upgrade

After stamping is complete, Alembic knows that the current database version is v0.1.2. Now running `upgrade head` will only execute all incremental migrations between the baseline version and the latest version.

### 6.2 Standard Migration Process
The standard migration process is divided into three steps:

### Step 1: Modify Model Code

- **Agent Library**: Modify model files in the `backend/openjiuwen_studio/models/` directory.
- **Ops Library**: Modify the `backend/openjiuwen_studio/ops/modules/prompt/infra/repositories/orm_repo.py` file.

Make the changes you need, such as adding a new field or a new table.

### Step 2: Generate Migration Scripts

After saving the code, run the `revision` command in the `backend` directory. Alembic will compare your models with the current state of the database and automatically generate a migration script.

**Note**: If you modify the model structure, you need to generate migration scripts for both MySQL and SQLite. You can use the following two methods:

#### Method 1: Use Unified Generation Script (Recommended)

Use the `generate_migration.py` script to generate migration scripts for all databases simultaneously:

```bash
# Automatically generate migration scripts for all databases
python generate_migration.py --autogenerate -m "feat: add user profile table"
```

**Advantages**:
- One command generates migration scripts for all 4 databases
- Automatically injects correct DB_TYPE environment variables
- Avoids missing any database

For detailed usage, please refer to the [GENERATE_MIGRATION_USAGE.md](./GENERATE_MIGRATION_USAGE.md) document.

#### Method 2: Generate Separately (For Specific Databases)

If you only need to generate migrations for a specific database, you can manually execute:

- **sqlite Agent Database**:
    ```bash
    alembic -n alembic_sqlite_agent revision --autogenerate -m "feat: add user profile table"
    ```

- **sqlite Ops Database**:
    ```bash
    alembic -n alembic_sqlite_ops revision --autogenerate -m "feat: add ip_address to audit log"
    ```

- **mysql Agent Database**:
    ```bash
    alembic -n alembic_mysql_agent revision --autogenerate -m "feat: add user profile table"
    ```

- **mysql Ops Database**:
    ```bash
    alembic -n alembic_mysql_ops revision --autogenerate -m "feat: add ip_address to audit log"
    ```

#### Description Information Specification

**Naming Convention**: Description information must start with `fix:` or `feat:`

| Prefix | Meaning | Use Cases |
|------|---------|-----------|
| `fix:` | Fix bugs or issues | Fix database structure defects, rollback erroneous changes, etc. |
| `feat:` | Add new features or characteristics | Add new tables, new fields, new indexes, etc. |

**Examples**:

```bash
# ✅ Recommended: Follow naming specification
python generate_migration.py --autogenerate -m "feat: add user profile table"
python generate_migration.py --autogenerate -m "fix: correct user email field type"

# ❌ Not Recommended: Missing prefix or incorrect format
python generate_migration.py --autogenerate -m "add user profile table"
python generate_migration.py --autogenerate -m "update"
```

> **Hint**: The description information after the `-m` parameter is crucial. It will become part of the version history and help the team understand the purpose of each change.

### Step 3: Apply Migration

The generated script is just a plan. Run the `upgrade head` command to execute this plan and apply changes to the database.

- **sqlite Agent Database**:
    ```bash
    alembic -n alembic_sqlite_agent upgrade head
    ```

- **sqlite Ops Database**:
    ```bash
    alembic -n alembic_sqlite_ops upgrade head
    ```


- **mysql Agent Database**:
    ```bash
    alembic -n alembic_mysql_agent upgrade head
    ```

- **mysql Ops Database**:
    ```bash
    alembic -n alembic_mysql_ops upgrade head
    ```

---

## 7. How to Collaborate as a Team

When multiple developers perform database structure changes simultaneously, conflicts may arise. Following the following process can effectively avoid and resolve these issues.

### Golden Process

1. **Pull Latest Code**: Before starting any model modifications, first `git pull` to get the latest code, including migration scripts that teammates may have already committed.

2. **Update Local Database**:
    - Start application to check version: `python main.py`
    - View version detection log to confirm if update is needed
    - update needed, run: `alembic upgrade head` (and/or `-n alembic_ops`)
    - Ensure local database is updated to the latest version before proceeding with development

3. **Make Your Changes**: Now, modify your model code on the latest database structure.

4. **Generate Your Migration Scripts**:
    - Recommended: Use `python generate_migration.py --autogenerate -m "feat: xxx"`
    - Or manual: Run `alembic revision --autogenerate ...`
    - Check that the generated migration scripts meet expectations

5. **Apply and Test Migration**: Execute `alembic upgrade head` locally to test if the migration succeeds.

6. **Commit Code**: Commit your model code and newly generated migration scripts together.

### Resolve Conflicts (Merge)

If you forget step 2, you may encounter migration branch conflicts.

**Scenario**: You and your teammate both created respective migration scripts `B1` and `B2` based on version `A`. After `git pull`, Alembic will detect two parallel "heads".

**Solution**:

1. First, upgrade the database to the head of one branch, for example `alembic upgrade B1`.
2. Then, run `alembic merge heads -m "Merge parallel migrations B1 and B2"`.
3. This will create a new merge migration file `C` that merges the two branches together.
    > **Note**: The original migration files `B1` and `B2` **will not be deleted**. They still exist in the `versions` directory. The `merge` operation only creates a new node `C` that points to both `B1` and `B2` in terms of dependencies, thereby reconnecting the two forked paths.
4. Finally, upgrade the database to this new merge head: `alembic upgrade head`.

### Advanced: What if two branches modified the same field?

1. **Manual Review**: Before running `merge`, be sure to check the contents of B1 and B2.
2. **Manual Fix**:
   - **Recommended (Rebase Strategy)**:
     If B1 and B2 conflict seriously (for example, one renamed a field, one deleted a field), the best approach is to **abandon one of the migration scripts**.
     1. Delete the migration script for the B2 branch.
     2. Rebase the B2 branch based on the latest main (including B1).
     3. Run `alembic revision --autogenerate` again to generate a new migration script based on B1.
   - **Alternative (Manual Edit)**:
     If it's just simple attribute modifications, you can manually edit the `upgrade()` function to ensure the logic order is correct.

## 8. Best Practices and Notes

1. **Never Modify Database Directly**: Strictly prohibit using tools such as Navicat, DBeaver to directly modify table structures. This will cause the database state to be inconsistent with the Alembic version history, leading to subsequent migration failures.
2. **Maintain Atomicity**: Each migration should preferably contain only related changes. Do not mix "add new feature table" and "modify old table fields" operations in one migration script.
3. **Test Before Commit**: Before committing code, be sure to execute `upgrade` and `downgrade` tests locally to ensure that migration scripts can both upgrade forward and rollback backward.
4. **Team Collaboration**:
    * After pulling others' code, execute `alembic upgrade head` immediately.
    * If you encounter version conflicts (multiple heads), you need to manually merge version history (`alembic merge`) or regenerate migration scripts.

## 9. Reference Documentation

* [Alembic Official Documentation](https://alembic.sqlalchemy.org/en/latest/)
* [SQLAlchemy Official Documentation](https://docs.sqlalchemy.org/)
