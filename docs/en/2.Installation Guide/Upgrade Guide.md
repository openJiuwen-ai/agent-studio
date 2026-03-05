# openJiuwen Studio Upgrade Guide

## Upgrade Note

Please carefully read this guide before upgrading and follow the steps to complete the upgrade operation.

## I. Local Installation Upgrade

### 1. Switch to the New Version Branch

1. Enter the project root directory
2. Pull the latest code:

   ```bash
   git pull
   ```

3. Switch to the specified version branch (e.g., v0.1.2):

   ```bash
   git checkout v0.1.2
   ```

### 2. Frontend Upgrade

1. Enter the frontend project directory:

   ```bash
   cd frontend
   ```

2. Re-execute the dependency installation command:

   ```bash
   npm install
   ```

3. Start the development server to apply updates:

   ```bash
   npm run dev
   ```

### 3. Backend Upgrade

1. Enter the backend project directory:

   ```bash
   cd backend
   ```

2. Re-execute the dependency synchronization command:

   ```bash
   uv sync
   ```

3. Database upgrade:
   Please refer to the [DATABASE_MIGRATION_DEVELOPMENT_GUIDE.md](../../../backend/DATABASE_MIGRATION_DEVELOPMENT_GUIDE_EN.md#2-version-upgrade-notes) section [2. Version Upgrade Notes](../../../backend/DATABASE_MIGRATION_DEVELOPMENT_GUIDE_EN.md#2-version-upgrade-notes) for backend database upgrade.

4. Activate the virtual environment and start the backend service:

   ```bash
   source .venv/bin/activate
   python main.py
   ```

## II.Docker Installation Upgrade
### Prerequisites: Old Version Configuration Files

Copy the configuration files of the old-version instance to the pre_upgrade_envs directory of the new-version deployment tool. The configuration files for different old-version instances are as follows:

- Old version 0.1.1: `.env.<Instance ID>`
- Old version 0.1.2: `.envs/env.<Instance ID>`
- Old version 0.1.3: `.envs/env.deploy.<Instance ID>` and `.envs/env.runtime.<Instance ID>`

> For how to view the Instance ID of the current instance, please refer to [here](../../../scripts/README.md#how-to-view-the-instance-id-of-a-service-instance).


### Upgrade Constraints and Configuration Requirements

1. This upgrade process only supports upgrading from a lower version to a higher version, or data migration between the same versions. Version rollback or downgrade is not supported. The supported version migration paths are as follows:

| Source Version | Target Version | Support Status               |
| :----- | :------- | :--------------------- |
| 0.1.1  | 0.1.4    | Supported                   |
| 0.1.2  | 0.1.4    | Supported                   |
| 0.1.3  | 0.1.4    | Supported                   |
| 0.1.4  | 0.1.4    | Supported (same-version data migration) |

2. This upgrade process only supports smooth migration of the same type of database components. Ensure that the database component types of the old and new version instances are completely consistent:

- If the old-version instance uses the MySQL component, the new-version instance must continue to use the MySQL component;
- If the old-version instance uses the Milvus component, the new-version instance must continue to use the Milvus component.

3. If the upgrade involves MySQL or Milvus components, ensure that the IP address variable of the machine where the instance runs is correctly configured in the [Old Version Instance Configuration Files](#prerequisites-old-version-configuration-files), to ensure network connectivity between the upgrade components and the host machine of the old-version instance.

```
IP=<IP address of the server where the instance components are located>
```

4. If the upgrade involves the SQLITE component, ensure that the old and new version instances are on the same physical machine.

5. Data migration and upgrade for external MySQL components or external Milvus components are not supported.

6. During the upgrade process, data from the MySQL and Milvus components of the old instance will be copied and migrated to the new instance. Before the upgrade, check the total data volume of the above components in the old instance, and ensure that the remaining disk space is not less than twice the total volume to meet the space requirements for the upgrade.

### Execute the Upgrade Command
> Upgrade Notice: Ensure the previous instance remains running normally. Do not perform any shutdown operation, and verify the old container is healthy. The upgrade requires connecting to the old container to read business data.

In the root directory of the new-version deployment tool, execute the following one-click upgrade command to start the new-version instance and complete the migration of old data:

```
$ ./service.sh up -n --upgrade
```

After the command is executed, the newly started new-version instance will automatically inherit most of the business data from the old-version instance, realizing non-intrusive upgrade and smooth data migration.

> Note: Some data, such as `memory data` and `original knowledge base files`, are temporarily not supported for migration and will be supported in future versions.

## III. Verify Upgrade

After completing the above steps, please verify the upgrade is successful through the following methods:

1. Frontend page can be accessed normally
2. Backend service can respond to API requests normally

If you encounter any issues during the upgrade process, please check the project logs, FAQ in the installation guide, or contact project maintainers.
