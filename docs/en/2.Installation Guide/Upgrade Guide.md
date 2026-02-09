# openJiuwen Studio Upgrade Guide

⚠️ **Upgrade operations are not supported at this time.**

## Upgrade Note

⚠️ **Important Notice:** The current version upgrade does not support cross-version data compatibility in the database. Please back up all important data before upgrading.

Please carefully read this guide before upgrading and follow the steps to complete the upgrade operation.

## I. Local Installation Upgrade

### 1. Switch to the New Version Branch

1. Enter the project root directory
2. Pull the latest code:

   ```bash
   git pull
   ```

3. Switch to the 0.1.2 version branch:

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

3. Activate the virtual environment and start the backend service:

   ```bash
   source .venv/bin/activate
   python main.py
   ```

## II.## Docker Installation Upgrade (Not Supported)

## III. Verify Upgrade

After completing the above steps, please verify the upgrade is successful through the following methods:

1. Frontend page can be accessed normally
2. Backend service can respond to API requests normally

If you encounter any issues during the upgrade process, please check the project logs, FAQ in the installation guide, or contact project maintainers.
