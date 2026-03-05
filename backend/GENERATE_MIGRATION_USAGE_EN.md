# Unified Migration Script Generation Tool Usage Guide

## Overview

`generate_migration.py` is a tool for uniformly generating MySQL and SQLite migration scripts, avoiding the need to execute alembic commands for each database separately.

---

## Quick Start

### Basic Usage

```bash
# Automatically generate migration scripts for all databases
python generate_migration.py --autogenerate -m "feat add user status field"

# Manually create migration scripts for all databases
python generate_migration.py --manual -m "fix correct data type issue"
```

---

## Command Parameters

### Required Parameters

| Parameter | Description | Example |
|------|------|------|
| `-m, --message` | Migration description information | `-m "feat add user profile"` |

### Optional Parameters

| Parameter | Description | Example |
|------|------|------|
| `--autogenerate` | Auto-generate (based on model changes) | `--autogenerate` |
| `--manual` | Manually create blank script | `--manual` |
| `-d, --database` | Specify database (can be used multiple times) | `-d mysql_agent -d sqlite_agent` |

---

## Usage Scenarios

### Scenario 1: Auto-Generate (Recommended)

**Purpose**: Automatically generate migration scripts based on SQLAlchemy model changes

```bash
# Auto-generate for all 4 databases
python generate_migration.py --autogenerate -m "feat add user status field"
```

**Output**:
```
============================================================
Start generating migration scripts: Add user status field
Mode: Auto-generate
Databases: ['MySQL Agent Database', 'MySQL Ops Database', 'SQLite Agent Database', 'SQLite Ops Database']
============================================================

✓ MySQL Agent Database: upgrade/mysql/alembic_agent/versions/add_user_status_field_xxxxx.py
✓ MySQL Ops Database: upgrade/mysql/alembic_ops/versions/add_user_status_field_xxxxx.py
✓ SQLite Agent Database: upgrade/sqlite/alembic_agent/versions/add_user_status_field_xxxxx.py
✓ SQLite Ops Database: upgrade/sqlite/alembic_ops/versions/add_user_status_field_xxxxx.py
```

---

### Scenario 2: Manual Creation

**Purpose**: Create blank migration scripts and manually write migration logic

```bash
# Create blank scripts for all databases
python generate_migration.py --manual -m "feat custom data migration"
```

---

### Scenario 3: Specify Database

**Purpose**: Generate migration scripts only for specific databases

```bash
# Generate only for MySQL Agent database
python generate_migration.py --autogenerate -d mysql_agent -m "feat update agent schema"

# Generate for multiple specified databases
python generate_migration.py --autogenerate -d mysql_agent -d sqlite_agent -m "fix update schema"
```

---

## Comparison with Traditional Method

### Traditional Method (Tedious)

```bash
# Need to execute commands separately for each database
alembic -n alembic_mysql_agent revision --autogenerate -m "feat add user status"
alembic -n alembic_mysql_ops revision --autogenerate -m "feat add user status"
alembic -n alembic_sqlite_agent revision --autogenerate -m "feat add user status"
alembic -n alembic_sqlite_ops revision --autogenerate -m "feat add user status"
```

### New Method (Concise)

```bash
# One command completes all databases
python generate_migration.py --autogenerate -m "feat add user status"
```

---

## How It Works

### 1. Multi-Configuration Support

The tool utilizes multiple configuration sections in `alembic.ini`:

```ini
[alembic_mysql_agent]
[alembic_mysql_ops]
[alembic_sqlite_agent]
[alembic_sqlite_ops]
```

### 2. Loop Calling

The tool loops to call the `alembic revision` command for each configuration:

```python
for db in databases:
    alembic -n {db['config']} revision -m {message}
```

### 3. Dynamic Environment Variable Injection

**Key Feature**: Dynamically injects the correct `DB_TYPE` environment variable for each database

```python
# MySQL configuration
if "mysql" in config_name:
    db_type = "mysql"
    env["DB_TYPE"] = "mysql"  # Dynamic injection

# SQLite configuration
if "sqlite" in config_name:
    db_type = "sqlite"
    env["DB_TYPE"] = "sqlite"  # Dynamic injection
```

**Why Dynamic Injection is Needed**:

1. **Model Code Conditional Judgment**
   ```python
   # Model code decides field type based on DB_TYPE
   if settings.DB_TYPE.lower() == "sqlite":
       id = mapped_column(Integer, ...)
   else:
       id = mapped_column(BigInteger, ...)
   ```

2. **Ensure Correct Database Structure**
   - MySQL alembic needs to generate MySQL-type migrations
   - SQLite alembic needs to generate SQLite-type migrations

3. **Avoid Confusion**
   - `DB_TYPE` in `.env` file can only be one value
   - Through dynamic injection, each database can obtain the correct `DB_TYPE`

### 4. Result Collection

Collect generation results for each database and uniformly display the summary.

---

## Generated Files

### File Locations

Migration scripts will be generated to the corresponding directories:

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

### File Naming

All files use a unified naming format:

```
{description}_{revision_id}.py
```

For example:
```
feat_add_user_status_field_4b4dd5bb39b4.py
```

---

## Advanced Usage

### 1. Use with Convenience Scripts

```bash
# 1. Generate migration scripts
python generate_migration.py --autogenerate -m "feat add user profile"

# 2. Execute migration
./migrate.sh mysql agent upgrade
./migrate.sh mysql ops upgrade
./migrate.sh sqlite agent upgrade
./migrate.sh sqlite ops upgrade
```

### 2. Generate Only for Needed Databases

```bash
# Generate only for MySQL databases (SQLite may not need this change)
python generate_migration.py --autogenerate -d mysql_agent -d mysql_ops -m "feat add MySQL-specific features"
```


---

## Notes

### 1. Model Change Check

**Before Auto-Generation**:
- Ensure SQLAlchemy models are correctly modified
- Ensure all imports are correct
- Recommend checking model syntax first

```bash
# Check model syntax
python -m py_compile openjiuwen_studio/models/xxx.py
```

### 2. Generated Script Review

**After Generation**:
- Check if the generated migration scripts are correct
- Pay special attention to database-specific logic
- Ensure upgrade and downgrade logic are complete

### 3. Test Environment Verification

**Before Deployment**:
- Verify migration scripts in test environment
- Test upgrade and downgrade
- Confirm data integrity

---

## Troubleshooting

### Error 1: alembic Command Not Available

**Error Message**:
```
❌ Error: alembic command not available
```

**Solution**:
```bash
# Check if alembic is installed
pip list | grep alembic

# If not installed, install alembic
pip install alembic
```

### Error 2: alembic.ini Not Found

**Error Message**:
```
❌ Error: alembic.ini file not found
```

**Solution**:
```bash
# Ensure execution in backend directory
cd backend
python generate_migration.py --autogenerate -m "Test"

```

### Error 3: Partial Database Generation Failed

**Error Message**:
```
⚠️ Warning: 1 database generation failed
```

**Solution**:
- Check error messages to locate specific problems
- Check if model definitions are correct
- Check database connection configuration

---

## Best Practices

### 1. Workflow

```bash
# 1. Modify SQLAlchemy models
vim openjiuwen_studio/models/user.py

# 2. Generate migration scripts
python generate_migration.py --autogenerate -m "feat: add user status field"

# 3. Check generated scripts
ls upgrade/*/alembic_*/versions/add_user_status_field_*.py

# 4. Test migration
./migrate.sh mysql agent upgrade

# 5. Verify functionality
# Run application to test related features
```

### 2. Description Information Specification

**Naming Convention**: Description information must start with `fix:` or `feat:`

| Prefix | Meaning | Use Cases |
|------|------|----------|
| `fix:` | Fix bugs or issues | Fix database structure defects, rollback erroneous changes, etc. |
| `feat:` | Add new features or characteristics | Add new tables, new fields, new indexes, etc. |

```bash
# ✅ Recommended: Follow naming specification
python generate_migration.py --autogenerate -m "feat: add user profile table"
python generate_migration.py --autogenerate -m "fix: correct user email field type"
python generate_migration.py --autogenerate -m "feat: add index on user phone number"

# ❌ Not Recommended: Missing prefix or incorrect format
python generate_migration.py --autogenerate -m "Add user profile table"
python generate_migration.py --autogenerate -m "update"
python generate_migration.py --autogenerate -m "Add comprehensive user profile management system with advanced features"
```

### 3. Version Management

```bash
# Generate all changes for a specific version
python generate_migration.py --autogenerate -m "feat: v1.2.0 database schema updates"
```

---

## Summary

### Advantages

- ✅ **One Command**: Generate migration scripts for all databases simultaneously
- ✅ **Reduce Errors**: Avoid missing any database
- ✅ **Unified Management**: All migration scripts use the same description
- ✅ **Simple to Use**: Clear command-line interface

### Applicable Scenarios

- Multi-database projects (MySQL + SQLite)
- Need to keep multiple databases synchronized
- Frequent database migrations

### Quick Reference

```bash
# Auto-generate (most commonly used) - Must use feat: or fix: prefix
python generate_migration.py --autogenerate -m "feat: add user status field"
python generate_migration.py --autogenerate -m "fix: correct email field type"

# Manual creation
python generate_migration.py --manual -m "feat: custom migration logic"

# Specify database
python generate_migration.py --autogenerate -d mysql_agent -m "feat: update agent schema"

# View help
python generate_migration.py --help
```

---

**Document Version**: v1.0
**Last Updated**: 2025-01-28
**Applicable Versions**: All projects supporting multiple databases
