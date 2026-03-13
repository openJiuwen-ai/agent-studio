# OpenJiuwen Studio - Plugin Marketplace Expansion

This document describes the plugin marketplace expansion feature and the plugin creation tooling added to OpenJiuwen Studio.

## Table of Contents

- [Overview](#overview)
- [Feature Summary](#feature-summary)
- [Architecture Changes](#architecture-changes)
- [Plugin Creation Tool](#plugin-creation-tool)
- [Plugin Configuration Structure](#plugin-configuration-structure)
- [Available Categories](#available-categories)
- [Quick Start](#quick-start)
- [Examples](#examples)
- [Development Workflow](#development-workflow)

---

## Overview

The **Plugin Marketplace Expansion** feature transforms OpenJiuwen Studio from a single-file plugin configuration system into a scalable, multi-plugin marketplace with category organization, JSON Schema validation, and developer-friendly tooling.

### Key Improvements

1. **Multi-File Plugin Architecture**: Moved from single `config.json` to category-based directory structure
2. **Category Organization**: Plugins organized into categories (Social, Productivity, AI, Developer Tools, etc.)
3. **JSON Schema Validation**: Automated validation for all plugin configurations
4. **Plugin Generator CLI**: Interactive and command-line tools for creating plugins
5. **Backward Compatibility**: Legacy `config.json` plugins automatically merged into marketplace
6. **Enhanced UI**: Category-based filtering and improved plugin details display

---

## Feature Summary

### Backend Changes

#### 1. Multi-File Plugin System

**Files:**
- `backend/openjiuwen_studio/core/manager/plugin.py`

**Changes:**
- Added `_load_plugins_from_directory()` - Loads plugins from category-based directory structure
- Added `_load_legacy_plugins()` - Loads plugins from legacy `config.json` for backward compatibility
- Added `_load_plugin_schema()` - Loads JSON schema for validation
- Added `_validate_plugin_config()` - Validates plugins against schema with non-blocking warnings

**Directory Structure:**
```
backend/openjiuwen_studio/marketplace/ready_plugins/
├── index.json                  # Plugin marketplace index
├── schema.json                 # JSON Schema for validation
├── social/
│   ├── twitter_oauth2.json    # Twitter API plugin (OAuth 2.0)
│   └── twitter_oauth1.json    # Twitter API plugin (OAuth 1.0a)
├── developer/
│   └── fakerestapi.json       # FakeRestAPI plugin
├── productivity/
├── ai/
└── data/
```

#### 2. Plugin Configuration Files

**index.json** - Defines category structure and plugin file mappings:
```json
{
  "version": "1.0.0",
  "categories": {
    "social": {
      "name": "Social & Communication",
      "icon": "💬",
      "plugins": [
        "social/twitter_oauth2.json",
        "social/twitter_oauth1.json"
      ]
    },
    "developer": {
      "name": "Developer Tools",
      "icon": "🛠️",
      "plugins": ["developer/fakerestapi.json"]
    }
  }
}
```

**schema.json** - JSON Schema for plugin validation:
- Validates plugin structure, required fields, data types
- Supports all HTTP methods: GET, POST, PUT, DELETE, PATCH
- Validates parameter types, authentication configs, tool definitions

#### 3. Example Plugins

**Twitter API Plugins**:
- `twitter_oauth2.json` - OAuth 2.0 Bearer Token (5 read-only tools)
  - Get User Timeline, Get Tweet, Search Tweets, Get User by Username/ID
- `twitter_oauth1.json` - OAuth 1.0a (10 user action tools)
  - Post Tweet, Delete Tweet, Like/Unlike, Retweet, Follow/Unfollow, etc.

**FakeRestAPI Plugin** (`developer/fakerestapi.json`):
- 27 endpoints for testing and development
- Covers Activities, Authors, Books, CoverPhotos, Users
- All CRUD operations (GET all, GET by ID, POST, PUT, DELETE)

### Frontend Changes

#### 1. Plugin Configuration Utilities

**Files:**
- `frontend/src/utils/pluginConfig.ts`

**Changes:**
- Modified `getAvailablePluginsFromMarket()` to return `Record<string, PluginConfig>`
- Added `transformConfigToMarketPlugin()` to extract category metadata
- Supports dynamic category and tag extraction from plugin configs

#### 2. Plugin Market Page

**Files:**
- `frontend/src/pages/Plugins/PluginMarketPageNew.tsx`

**Changes:**
- Added dynamic category extraction from marketplace plugins
- Modified installation flow to use plugin's `api_prefix` as service URL
- Enhanced category filtering with dynamic category discovery

#### 3. Tool Configuration Page

**Files:**
- `frontend/src/pages/Plugins/ToolConfigurationPage.tsx`

**Changes:**
- Added full API path display (base URL + endpoint) in 3 locations:
  - Tool header chip
  - Tool details section
  - Test dialog (most important for testing)
- Visual distinction: base URL in blue, endpoint path in default color
- Improved debugging and testing experience

---

## Plugin Creation Tool

### Overview

The Plugin Generator CLI is a developer tool for creating and validating plugin configurations. It supports both interactive and command-line modes.

### Installation

No installation required - it's part of the OpenJiuwen Studio backend.

### Module Structure

```
backend/openjiuwen_studio/marketplace/plugins_creator/
├── __init__.py           # Package exports
├── __main__.py           # Module entry point
├── plugins_creator.py    # Main CLI logic
├── categories.py         # Category definitions
├── templates.py          # Plugin/tool templates
└── validator.py          # JSON Schema validation
```

### Usage

#### Interactive Mode (Recommended)

```bash
cd backend
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --interactive
```

This will guide you through:
1. Plugin basic information (ID, name, description)
2. Category selection
3. Icon and metadata
4. Tool/endpoint creation
5. Parameter definitions
6. Automatic validation and index.json update

#### Command-Line Mode

```bash
# Create a basic plugin
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --name "Slack API" \
  --id slack_api \
  --category social \
  --description "Slack API integration" \
  --api-prefix "https://slack.com/api"

# Specify custom icon and author
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --name "GitHub API" \
  --id github_api \
  --category developer \
  --icon "🐙" \
  --author "MyCompany" \
  --version "2.0.0"
```

#### Validation Mode

```bash
# Validate an existing plugin file
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --validate backend/openjiuwen_studio/marketplace/ready_plugins/social/twitter_oauth2.json
```

### Command-Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--interactive`, `-i` | Launch interactive mode | No |
| `--name` | Plugin display name | Yes* |
| `--id` | Plugin ID (lowercase, underscores) | Yes* |
| `--category` | Plugin category | Yes* |
| `--description` | Plugin description | No |
| `--icon` | Plugin icon (emoji or URL) | No |
| `--api-prefix` | API base URL | No |
| `--author` | Plugin author (default: OpenJiuwen) | No |
| `--version` | Plugin version (default: 1.0.0) | No |
| `--output`, `-o` | Output filename | No |
| `--validate` | Validate existing plugin file | No |

*Required for command-line mode (or use `--interactive`)

---

## Plugin Configuration Structure

### Plugin Object

```json
{
  "plugin_id": "unique_plugin_id",
  "name": "Plugin Display Name",
  "description": "What this plugin does",
  "category": "social",
  "category_name": "Social & Communication",
  "icon_uri": "💬",
  "plugin_type": 1,
  "version": "1.0.0",
  "author": "OpenJiuwen",
  "tags": ["social", "api"],
  "api_prefix": "https://api.example.com",
  "tools": [...]
}
```

### Tool Object

```json
{
  "name": "Get User Profile",
  "path": "/users/{user_id}",
  "method": "GET",
  "description": "Retrieve user profile information",
  "request_params": {
    "user_id": {
      "type": "string",
      "description": "User ID",
      "required": true
    },
    "fields": {
      "type": "array",
      "description": "Fields to include",
      "required": false,
      "default": ["id", "name", "email"]
    }
  }
}
```

### Supported Parameter Types

- `string` - Text values
- `integer` - Whole numbers
- `number` - Floating point numbers
- `boolean` - true/false
- `object` - JSON objects
- `array` - Arrays of values

### Supported HTTP Methods

- `GET` - Retrieve data
- `POST` - Create data
- `PUT` - Update/replace data
- `DELETE` - Delete data
- `PATCH` - Partial update

---

## Available Categories

| Category | Icon | Description |
|----------|------|-------------|
| `social` | 💬 | Social & Communication platforms |
| `productivity` | 📋 | Email, calendar, task management |
| `ai` | 🤖 | AI & machine learning services |
| `data` | 📊 | Data sources and analytics |
| `communication` | 📞 | Communication tools |
| `developer` | 🛠️ | Developer tools and workflows |
| `other` | 📦 | Miscellaneous plugins |

To add a new category:
1. Edit `backend/openjiuwen_studio/marketplace/plugins_creators/categories.py`
2. Add category to `backend/openjiuwen_studio/marketplace/ready_plugins/index.json`
3. Create category directory: `backend/openjiuwen_studio/marketplace/ready_plugins/<category>/`

---

## Quick Start

### Adding a New Plugin to the Marketplace

#### Step 1: Create Plugin Template

```bash
cd backend
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --interactive
```

Follow the prompts to create your plugin.

#### Step 2: Edit Plugin File

Open the generated JSON file and add your API tools:

```json
{
  "tools": [
    {
      "name": "List Users",
      "path": "/users",
      "method": "GET",
      "description": "Get list of all users",
      "request_params": {
        "page": {
          "type": "integer",
          "description": "Page number",
          "required": false,
          "default": 1
        },
        "limit": {
          "type": "integer",
          "description": "Results per page",
          "required": false,
          "default": 10
        }
      }
    }
  ]
}
```

#### Step 3: Validate

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --validate backend/openjiuwen_studio/marketplace/ready_plugins/<category>/<plugin>.json
```

#### Step 4: Test in UI

1. Start backend server
2. Navigate to Plugins Marketplace
3. Find your plugin in the category
4. Click "Install" to add it to your workspace
5. Test the tools in the Tool Configuration page

---

## Examples

### Example 1: Creating a Weather API Plugin

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --name "Weather API" \
  --id weather_api \
  --category data \
  --description "Get weather forecasts and current conditions" \
  --api-prefix "https://api.weatherapi.com/v1" \
  --icon "🌤️"
```

Then edit the generated file to add tools:

```json
{
  "plugin_id": "weather_api",
  "name": "Weather API",
  "description": "Get weather forecasts and current conditions",
  "category": "data",
  "icon_uri": "🌤️",
  "api_prefix": "https://api.weatherapi.com/v1",
  "tools": [
    {
      "name": "Get Current Weather",
      "path": "/current.json",
      "method": "GET",
      "description": "Get real-time weather data for a location",
      "request_params": {
        "q": {
          "type": "string",
          "description": "Location query (city name, coordinates, etc.)",
          "required": true
        },
        "aqi": {
          "type": "string",
          "description": "Include air quality data (yes/no)",
          "required": false,
          "default": "no"
        }
      }
    },
    {
      "name": "Get Forecast",
      "path": "/forecast.json",
      "method": "GET",
      "description": "Get weather forecast for up to 14 days",
      "request_params": {
        "q": {
          "type": "string",
          "description": "Location query",
          "required": true
        },
        "days": {
          "type": "integer",
          "description": "Number of days (1-14)",
          "required": false,
          "default": 3
        }
      }
    }
  ]
}
```

### Example 2: Creating a REST CRUD Plugin

See `backend/openjiuwen_studio/marketplace/ready_plugins/developer/fakerestapi.json` for a complete example with 27 endpoints covering full CRUD operations.

---

## Development Workflow

### Adding 10-20 Plugins to the Marketplace

1. **Research APIs**: Identify popular APIs in each category
   - Social: Twitter, Facebook, LinkedIn, Instagram, Discord
   - Productivity: Gmail, Google Calendar, Trello, Asana, Notion
   - AI: OpenAI, Anthropic, Hugging Face, Google AI
   - Data: Google Sheets, Airtable, PostgreSQL, MongoDB
   - Developer: GitHub, GitLab, Jira, Jenkins, Docker Hub

2. **Create Plugin Templates**: Use the CLI tool for each
   ```bash
   for api in twitter facebook linkedin gmail gcal trello; do
     python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
       --name "$api API" --id "${api}_api" --category social --interactive
   done
   ```

3. **Add Tools/Endpoints**: Edit each JSON file to add API endpoints
   - Focus on most commonly used endpoints first
   - Include proper parameter definitions
   - Add clear descriptions for LLM understanding

4. **Validate All Plugins**:
   ```bash
   for file in backend/openjiuwen_studio/marketplace/ready_plugins/*/*.json; do
     python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --validate "$file"
   done
   ```

5. **Test in UI**:
   - Install each plugin
   - Test at least one tool from each plugin
   - Verify parameter handling and responses

6. **Document**: Update this README with new plugins added

### Best Practices

1. **Plugin IDs**: Use lowercase with underscores (e.g., `slack_api`, `github_api`)
2. **Descriptions**: Make them clear and actionable for LLM agents
3. **Parameters**: Define all required and optional parameters with descriptions
4. **Validation**: Always validate before committing
5. **Testing**: Test actual API calls when possible
6. **Backward Compatibility**: Don't break existing plugins in `config.json`

---

## Files Modified/Created

### Backend

**Created:**
- `backend/openjiuwen_studio/marketplace/plugins_creators/` - Plugin generator package
  - `__init__.py` - Package exports
  - `__main__.py` - Module entry point
  - `plugins_creator.py` - Main CLI logic
  - `categories.py` - Category definitions
  - `templates.py` - Template creation functions
  - `validator.py` - JSON Schema validation
- `backend/openjiuwen_studio/marketplace/ready_plugins/index.json` - Plugin marketplace index
- `backend/openjiuwen_studio/marketplace/ready_plugins/schema.json` - JSON Schema for validation
- `backend/openjiuwen_studio/marketplace/ready_plugins/social/twitter_oauth2.json` - Twitter OAuth 2.0 plugin (5 read tools)
- `backend/openjiuwen_studio/marketplace/ready_plugins/social/twitter_oauth1.json` - Twitter OAuth 1.0a plugin (10 action tools)
- `backend/openjiuwen_studio/marketplace/ready_plugins/developer/fakerestapi.json` - FakeRestAPI plugin (27 tools)

**Modified:**
- `backend/openjiuwen_studio/core/manager/plugin.py` - Multi-file loading, legacy support, validation

### Frontend

**Modified:**
- `frontend/src/utils/pluginConfig.ts` - Category metadata extraction
- `frontend/src/pages/Plugins/PluginMarketPageNew.tsx` - Dynamic categories, installation URL fix
- `frontend/src/pages/Plugins/ToolConfigurationPage.tsx` - Full API path display in test dialog

---

## OpenAPI/Swagger Auto-Import ✨ NEW

### Automatically generate plugins from OpenAPI/Swagger specifications!

Instead of manually creating plugins, you can now import them directly from OpenAPI/Swagger specs:

```bash
# Import from URL
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --category developer

# Interactive mode
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --interactive

# Import from file with limit
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file swagger.json --category ai --limit 10
```

**Features:**
- ✅ Automatic endpoint extraction
- ✅ Parameter conversion (path, query, body, headers)
- ✅ Authentication detection (OAuth2, API Key, Bearer, Basic)
- ✅ Support for OpenAPI 2.0 & 3.x
- ✅ JSON and YAML format support
- ✅ `$ref` pointer resolution
- ✅ Tool limiting for large APIs

**See [SWAGGER_IMPORTER_README.md](from_swagger/SWAGGER_IMPORTER_README.md) for full documentation.**

---

## Future Enhancements

1. **Plugin Versioning**: Support multiple versions of the same plugin
2. **Plugin Dependencies**: Allow plugins to depend on other plugins
3. **Authentication Templates**: Pre-built auth configs (OAuth, API Key, JWT)
4. **Plugin Marketplace UI**: Browse and search plugins in the UI
5. **Plugin Analytics**: Track usage, success rates, performance
6. **Community Plugins**: Allow users to publish and share plugins
7. ~~**Auto-Import from OpenAPI**: Generate plugins from OpenAPI/Swagger specs~~ ✅ **COMPLETED**
8. **Plugin Testing Framework**: Automated testing for plugin endpoints

---

## Support

For issues or questions:
1. Check this README first
2. Validate your plugin with `--validate` flag
3. Check backend logs for detailed error messages
4. Review existing plugins for examples

---

## License

Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
