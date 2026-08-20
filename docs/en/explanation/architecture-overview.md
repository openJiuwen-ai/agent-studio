# Project Architecture

---

## Table of Contents

- [1 Overall Project Structure](#1-overall-project-structure)
- [2 backend Module Details](#2-backend-module-details)
- [3 frontend Module Details](#3-frontend-module-details)
- [4 docs Module Details](#4-docs-module-details)
- [5 docker Module Details](#5-docker-module-details)
- [6 Project Tech Stack Summary](#6-project-tech-stack-summary)
- [7 Project Architecture Diagram](#7-project-architecture-diagram)

---

# 1 Overall Project Structure

```
agent-studio/
├── backend/                          # Java backend service module
├── agent-runtime/                    # Python Agent and Workflow runtime
├── agent_builder/                    # Python NL2, Prompt and model tuning service
├── packages/                         # Python shared model and storage packages
├── frontend/                         # Angular frontend application module
├── docs/                             # Project documentation module
├── docker/                           # Docker deployment configuration
├── deploy/                           # Unified deployment scripts, Compose and observability configuration
└── LICENSE / README.md and other root files
```

The current deployment includes four application services:

| Deployed Service | Main Source Code | Responsibilities |
|------------------|------------------|------------------|
| `studio-console` | `frontend/` | Angular console and API reverse proxy |
| `studio-manager` | `backend/studio-manager*` | Agent, knowledge base, model, tool, and MCP management |
| `studio-runtime` | `agent-runtime/` | Agent/Workflow execution, publish invocation, LLM, MCP, and memory runtime |
| `studio-builder` | `agent_builder/` | NL2, Prompt, model tuning, and build-time storage |

Python services reuse model invocation and storage capabilities through the root-level `packages/` directory. The original Java `studio-service` has been removed from the deployment architecture; `backend/studio-runtime*` is retained only as legacy source code. See Section 2.1 for details.

---

# 2 backend Module Details

The backend module is the core backend service of the entire system. It adopts a Maven multi-module architecture, including API definitions, business logic, data persistence, and more.

## 2.1 Directory Structure

```
backend/
├── pom.xml                           # Parent POM file, manages dependency versions uniformly
├── sql/                              # SQL script directory
│   ├── schema.sql                    # Database table structure definitions
│   ├── init.sql                      # Initialization data
│   └── data.sql                      # Business test data
├── studio/                           # Aggregation module
├── studio-api/                       # API definition module
├── studio-common/                    # Common module
├── studio-manager/                   # Manager service startup module
├── studio-manager-api/               # Manager API definition module
├── studio-manager-service/           # Manager service business implementation
├── studio-runtime/                   # Original Java studio-service startup module (legacy source, no longer deployed)
├── studio-runtime-api/               # Original Java studio-service API (legacy source)
├── studio-runtime-service/           # Original Java studio-service implementation (legacy source)
└── studio-space/                     # DeepResearch
```

> **Module Status Note**: Starting from Beta5, the original Java `studio-service` has been removed from the deployment architecture. Its capabilities have been migrated to `studio-manager`, Python `agent-runtime`, and `agent_builder` respectively. The above `backend/studio-runtime*` modules are temporarily retained for migration traceability and compatibility testing, and are no longer built as independently deployed images. The currently deployed service `studio-runtime` corresponds to the repository root directory `agent-runtime/` — do not confuse it with these Java legacy modules.

## 2.2 Core Module Description

### 2.2.1 studio-common (Common Module)

**Location**: `backend/studio-common/`

**Description**: Provides common utility classes, entity classes, and shared components used across the entire project.

**Directory Structure**:

```
studio-common/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/openjiuwen/studio/agent/common/
    │   │       ├── annotation/               # Custom annotations
    │   │       ├── bo/                       # Business objects
    │   │       ├── config/                   # Configuration classes
    │   │       ├── constant/                 # Constant definitions
    │   │       ├── crypt/                    # Encryption utilities
    │   │       ├── dto/                      # Data transfer objects
    │   │       ├── entity/                   # Entity classes
    │   │       ├── enums/                    # Enum definitions
    │   │       ├── exception/                # Exception definitions
    │   │       ├── filter/                   # Request filters
    │   │       ├── rce/                      # Remote call wrappers
    │   │       ├── redis/                    # Redis-related
    │   │       ├── sensitive/                # Sensitive word processing
    │   │       ├── service/                  # Common services
    │   │       ├── utils/                    # Utility classes
    │   │       └── validator/                # Data validation
    │   └── resources/                        # Resource files
    └── test/                                 # Test code
```

**Package Function Details**:

| Package | Description |
|---------|-------------|
| **annotation** | Contains custom annotations for permission control, logging, method interception, etc. |
| **bo** | Business Objects, used for encapsulating business data |
| **config** | Configuration classes, managing connection configurations for various middleware and third-party services |
| **constant** | Constant definitions, storing system-level constant configurations |
| **crypt** | Encryption utility package, providing data encryption, decryption, signing, and other security functions |
| **dto** | Data Transfer Objects, used for front-end/back-end data exchange |
| **entity** | Entity classes, ORM mapping objects corresponding one-to-one with database tables |
| **enums** | Enum definitions, used for managing finite sets of state objects |
| **exception** | Custom exception classes for unified exception handling |
| **filter** | HTTP request filters, for authentication, logging, CORS, etc. |
| **rce** | Remote call wrappers, providing Feign and other remote call tools |
| **redis** | Redis-related operation wrappers |
| **sensitive** | Sensitive word filtering functionality |
| **service** | Common business services |
| **utils** | Common utility classes, providing string processing, date conversion, JSON serialization, and other utility methods |
| **validator** | Data validation annotations and validators |

### 2.2.2 studio-manager (Manager Service Startup Module)

**Location**: `backend/studio-manager/`

**Description**: Agent management service, responsible for core management functions such as Agent creation, configuration, deployment, and monitoring.

**Directory Structure**:

```
studio-manager/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/openjiuwen/studio/agent/manager/
    │   │       └── Application.java          # Spring Boot startup class
    │   └── resources/                        # Resource files
    └── test/                                 # Test code
```

**Startup Class Features**:

- Annotated with `@SpringBootApplication`
- Package scan path: `com.openjiuwen.studio.agent.manager`
- Provides REST API endpoints for Agent management

### 2.2.3 studio-runtime (Original Java studio-service Startup Module, Legacy)

**Location**: `backend/studio-runtime/`

**Description**: This module is the startup module of the original Java `studio-service`. After Beta5, it is no longer built or deployed as an independent service. The active execution capabilities are now in Python `agent-runtime/`, the management agent capabilities are in `studio-manager-service`, and the build-time capabilities are in `agent_builder/`.

**Directory Structure**:

```
studio-runtime/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/openjiuwen/studio/agent/runtime/
    │   │       └── Application.java          # Spring Boot startup class
    │   └── resources/                        # Resource files
    └── test/                                 # Test code
```

**Legacy Startup Class Information**:

- Annotated with `@SpringBootApplication`
- Package scan path: `com.openjiuwen.studio.agent.runtime`
- Retains the original Agent runtime REST API entry point, for migration traceability and compatibility testing

### 2.2.4 studio-manager-service (Manager Service Business Implementation)

**Location**: `backend/studio-manager-service/`

**Description**: Core business logic implementation module for the Manager service, including specific business functions such as Agent management, Workflow orchestration, and knowledge base management.

**Directory Structure**:

```
studio-manager-service/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/openjiuwen/studio/
    │   │       ├── agent/
    │   │       │   ├── agentbase/            # Agent base capability implementation
    │   │       │   │   ├── client/           # RAG/knowledge base client integration
    │   │       │   │   ├── common/           # Common constants and enums
    │   │       │   │   ├── config/           # Configuration classes
    │   │       │   │   ├── converter/        # Data converters
    │   │       │   │   ├── entity/           # Entity classes
    │   │       │   │   ├── enums/            # Enum definitions
    │   │       │   │   ├── filter/           # Request filters
    │   │       │   │   ├── mapper/           # Database mappings
    │   │       │   │   ├── model/            # Data models
    │   │       │   │   ├── service/          # Business services
    │   │       │   │   └── utils/            # Utility classes
    │   │       │   ├── foundation/           # Foundation capabilities
    │   │       │   │   ├── base/             # Base implementation
    │   │       │   │   ├── connection/       # Connection management
    │   │       │   │   └── i18n/             # Internationalization
    │   │       │   └── manager/              # Management functions
    │   │       │       ├── aop/              # Aspect-oriented programming
    │   │       │       ├── aspect/           # AspectJ aspects
    │   │       │       ├── bo/               # Business objects
    │   │       │       ├── config/           # Configuration classes
    │   │       │       ├── constant/         # Constant definitions
    │   │       │       ├── controller/       # REST controllers
    │   │       │       ├── dao/              # Data access objects
    │   │       │       ├── dto/              # Data transfer objects
    │   │       │       ├── entity/           # Entity classes
    │   │       │       ├── enums/            # Enum definitions
    │   │       │       ├── exception/        # Exception definitions
    │   │       │       ├── filter/           # Filters
    │   │       │       ├── http/             # HTTP client
    │   │       │       ├── license/          # License management
    │   │       │       ├── mapper/           # MyBatis mappings
    │   │       │       ├── obs/              # OBS object storage
    │   │       │       ├── rce/              # Remote calls
    │   │       │       ├── repository/       # Repository layer
    │   │       │       ├── ros/              # ROS integration
    │   │       │       ├── saml/             # SAML authentication
    │   │       │       ├── service/          # Business services
    │   │       │       ├── task/             # Task scheduling
    │   │       │       ├── utils/            # Utility classes
    │   │       │       └── workflow/         # Workflow management
    │   │       ├── common/
    │   │       │   └── service/              # Common services
    │   │       └── prompt/
    │   │           └── engineering/          # Prompt engineering
    │   └── resources/                        # Resource files
    └── test/                                 # Test code
```

**Package Function Details**:

| Package | Description |
|---------|-------------|
| **agent/agentbase/client** | Integrates RAG services, knowledge base SDKs, and other external clients |
| **agent/agentbase/entity** | Entity classes related to Agent base capabilities |
| **agent/agentbase/service** | Agent base capability business services |
| **agent/manager/controller** | REST API controllers for Agent management |
| **agent/manager/service** | Agent management business logic implementation |
| **agent/manager/workflow** | Workflow orchestration and management functions |
| **agent/manager/dao/mapper** | MyBatis database mapping interfaces |
| **agent/manager/obs** | Huawei Cloud OBS object storage integration |
| **agent/manager/license** | Software license management |
| **common/service** | Common services shared across modules |
| **prompt/engineering** | Prompt generation, optimization, and testing functions |

### 2.2.5 studio-runtime-service (Original Java studio-service Business Implementation, Legacy)

**Location**: `backend/studio-runtime-service/`

**Description**: Business implementation module of the original Java `studio-service`, currently not corresponding to any deployed container. The controllers, services, and configurations in the directory are pre-migration implementations and should not be used as a deployment or configuration reference for the active Python `studio-runtime`.

**Directory Structure**:

```
studio-runtime-service/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/openjiuwen/studio/agent/runtime/
    │   │       ├── alarm/                      # Alarm module
    │   │       │   ├── aom/                    # AOM alarm integration
    │   │       │   └── app/                    # Application alarms
    │   │       ├── annotation/                 # Custom annotations
    │   │       ├── aop/                        # Aspect-oriented programming
    │   │       ├── bo/                         # Business objects
    │   │       ├── config/                     # Configuration classes
    │   │       ├── constant/                   # Constant definitions
    │   │       ├── controller/                 # REST controllers
    │   │       ├── datasource/                 # Data source management
    │   │       ├── dto/                        # Data transfer objects
    │   │       ├── entity/                     # Entity classes
    │   │       ├── enums/                      # Enum definitions
    │   │       ├── event/                      # Event handling
    │   │       ├── exception/                  # Exception definitions
    │   │       ├── filter/                     # Request filters
    │   │       ├── http/                       # HTTP client
    │   │       ├── mapper/                     # Database mappings
    │   │       ├── mcp/                        # MCP protocol support
    │   │       ├── model/                      # Data models
    │   │       ├── properties/                 # Configuration properties
    │   │       ├── rce/                        # Remote calls
    │   │       ├── redis/                      # Redis cache
    │   │       ├── sensitive/                  # Sensitive word filtering
    │   │       ├── service/                    # Business services
    │   │       ├── task/                       # Task scheduling
    │   │       ├── thread/                     # Thread management
    │   │       └── utils/                      # Utility classes
    │   └── resources/                          # Resource files
    └── test/                                   # Test code
```

**Package Function Details**:

| Package | Description |
|---------|-------------|
| **alarm/aom** | Application Operations Management (AOM) alarm integration, implements runtime alarm reporting |
| **alarm/app** | Application-level alarm service, provides application-level alerting capabilities |
| **aop** | Aspect-oriented programming, for logging, performance monitoring, transaction management, etc. |
| **controller** | Original Java Service REST API controllers, for legacy code documentation only |
| **datasource** | Multi-datasource management, supports runtime datasource switching and connection pool management |
| **event** | Event handling mechanism, supports event subscription and dispatching during Agent execution |
| **mcp** | Model Context Protocol support, implements communication with MCP servers |
| **service** | Core business services related to Agent execution |
| **thread** | Thread pool management, controls concurrent execution |
| **task** | Scheduled task scheduling, manages periodic tasks |
| **sensitive** | Sensitive word filtering, content safety checks |
| **dto/entity** | Data transfer object and entity class definitions |

### 2.2.6 studio-space (DeepResearch)

**Location**: `backend/studio-space/`

**Description**: DeepResearch

**Directory Structure**:

```
studio-space/
├── pom.xml
├── studio-space-api/                # API definitions
├── studio-space-app/                # Application layer
├── studio-space-common/             # Common components
├── studio-space-dao/                # Data access layer
├── studio-space-foundation/         # Foundation capabilities
└── studio-space-service/            # Business services
```

**Sub-module Function Details**:

| Module | Description |
|--------|-------------|
| **studio-space-api** | DeepResearch API definitions, including workspace creation, query, member management, and other interfaces |
| **studio-space-app** | Application layer implementation, handles business orchestration and flow control |
| **studio-space-common** | DeepResearch common components, reused by other sub-modules |
| **studio-space-dao** | Data access layer, responsible for database interaction |
| **studio-space-foundation** | Foundation capability layer, provides core abstractions and implementations for workspace management |
| **studio-space-service** | Business service layer, implements specific business logic for workspaces |

## 2.3 SQL Script Description

| File | Description |
|------|-------------|
| **schema.sql** | Database table structure definitions, including DDL statements for all business tables |
| **init.sql** | Initialization data, including system configurations, dictionary tables, and other base data |
| **data.sql** | Business data, stores initial business test data |

## 2.4 Core Database Table Description

### 2.4.1 User-related Tables

**t_users (User Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | BIGINT | Primary key, auto-increment |
| username | VARCHAR(100) | Username, unique |
| real_name | VARCHAR(100) | Real name |
| email | VARCHAR(100) | Email |
| phone | VARCHAR(20) | Phone |
| department | VARCHAR(100) | Department |
| position | VARCHAR(100) | Position |
| source | VARCHAR(20) | User source (INTERNAL/SAML/OAUTH/LDAP) |
| domain_id | VARCHAR(100) | Tenant ID |
| project_id | VARCHAR(100) | Project ID |
| is_active | BOOLEAN | Whether active |
| created_time | DATETIME | Creation time |
| updated_time | DATETIME | Update time |
| expire_time | DATETIME | Expiration time |

### 2.4.2 Workspace-related Tables

**WorkspaceEntity (Workspace Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key, workspace ID |
| name | VARCHAR | Workspace name |
| flag | VARCHAR | Workspace identifier |
| project_id | VARCHAR | Project ID |
| description | VARCHAR | Description |
| icon | VARCHAR | Icon |
| tenant_id | VARCHAR | Tenant ID |
| type | VARCHAR | Type |
| status | VARCHAR | Status |
| is_preset_agent | INT | Whether a tutorial template has been preset |
| created_on | DATETIME | Creation time |
| creator | VARCHAR | Creator |
| creator_id | VARCHAR | Creator ID |
| updated_on | DATETIME | Update time |
| updater | VARCHAR | Updater |
| updater_id | VARCHAR | Updater ID |
| role | VARCHAR | Space role |

**WorkSpaceMemberEntity (Workspace Member Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key |
| workspace_id | VARCHAR | Workspace ID, foreign key |
| member_id | VARCHAR | Member ID |
| member_name | VARCHAR | Member name |
| member_source | VARCHAR | Member source |
| domain_id | VARCHAR | Tenant ID |
| role | VARCHAR | Role |
| status | INT | Status |
| created_on | DATETIME | Creation time |
| creator_id | VARCHAR | Creator ID |

### 2.4.3 Agent-related Tables

**AgentBaseInfo (Agent Basic Information Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| agent_id | VARCHAR | Primary key, Agent unique identifier |
| domain_id | VARCHAR | Tenant ID |
| project_id | VARCHAR | Project ID |
| workspace_id | VARCHAR | Workspace ID |
| name | VARCHAR | Agent name |
| status | VARCHAR | Status |
| tenant_id | VARCHAR | Tenant ID |
| created_on | DATETIME | Creation time |

**AgentVersion (Agent Version Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| version_id | VARCHAR | Primary key, version unique identifier |
| agent_id | VARCHAR | Agent ID, foreign key |
| project_id | VARCHAR | Project ID |
| name | VARCHAR | Version name |
| description | VARCHAR | Description |
| tags | JSON | Tag list |
| icon | VARCHAR | Icon |
| instructions | TEXT | System instructions |
| prologue | TEXT | Opening message |
| suggest_queries | JSON | Suggested questions |
| trigger_list | JSON | Trigger configuration |
| additional_questions_config | JSON | Follow-up question configuration |
| ir_path | VARCHAR | IR path |
| dsl_path | VARCHAR | DSL path |
| is_online | BOOLEAN | Whether online |
| creator | VARCHAR | Creator |
| created_on | DATETIME | Creation time |
| updated_on | DATETIME | Update time |
| published_on | DATETIME | Publish time |

### 2.4.4 Workflow-related Tables

**WorkflowEntity (Workflow Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key, workflow ID |
| name | VARCHAR | Name |
| code | VARCHAR | Code |
| description | VARCHAR | Description |
| avatar | VARCHAR | Avatar |
| icon_name | VARCHAR | Icon name |
| dsl_path | VARCHAR | DSL file path |
| ir_path | VARCHAR | IR file path |
| status | VARCHAR | Status |
| visibility | VARCHAR | Visibility |
| workflow_type | VARCHAR | Workflow type |
| customize_node | INT | Whether custom node |
| created_at | BIGINT | Creation timestamp |
| updated_at | BIGINT | Update timestamp |
| published_at | BIGINT | Publish timestamp |
| created_by | VARCHAR | Creator |
| creator_id | VARCHAR | Creator ID |
| updated_by | VARCHAR | Updater |
| updater_id | VARCHAR | Updater ID |
| project_id | VARCHAR | Project ID |
| domain_id | VARCHAR | Tenant ID |
| workspace_id | VARCHAR | Workspace ID |
| deploy_wf_version | BIGINT | Deploy version number |
| last_version_id | VARCHAR | Latest version ID |
| test_status | INT | Test status |
| is_share | INT | Whether shared |
| share_info | JSON | Share information |
| trigger_list | JSON | Trigger list |

**WorkflowVersionEntity (Workflow Version Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| version_id | VARCHAR | Primary key, version unique identifier |
| version_name | VARCHAR | Version name |
| (Inherits all fields from WorkflowEntity) | | |

**SessionEntity (Workflow Session Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| session_id | VARCHAR | Primary key, session ID |
| instance_id | VARCHAR | Instance ID |
| workflow_id | VARCHAR | Workflow ID, foreign key |
| project_id | VARCHAR | Project ID |
| created_on | DATETIME | Creation time |
| updated_on | DATETIME | Update time |

### 2.4.5 Knowledge Base-related Tables

**KnowledgeBaseEntity (Knowledge Base Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key, knowledge base ID |
| name | VARCHAR | Name |
| type | VARCHAR | Type |
| status | VARCHAR | Status |
| icon | VARCHAR | Icon |
| knowledge_base_connection_id | VARCHAR | Knowledge base connection ID |
| connector_id | VARCHAR | Connector ID |
| external_id | VARCHAR | External ID |
| description | VARCHAR | Description |
| repo_type | VARCHAR | Repository type |
| create_time | BIGINT | Creation time |
| update_time | BIGINT | Update time |
| project_id | VARCHAR | Project ID |
| domain_id | VARCHAR | Tenant ID |
| domain_name | VARCHAR | Tenant name |
| workspace_id | VARCHAR | Workspace ID |
| created_user_id | VARCHAR | Creator ID |
| created_user_name | VARCHAR | Creator name |
| last_update_user_id | VARCHAR | Updater ID |
| last_update_user_name | VARCHAR | Updater name |
| copy_source_id | VARCHAR | Copy source ID |
| share_scope | VARCHAR | Share scope |

**KnowledgeBaseConnectionEntity (Knowledge Base Connection Configuration Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key |
| name | VARCHAR | Connection name |
| type | VARCHAR | Connection type |
| config | TEXT | Connection configuration |
| project_id | VARCHAR | Project ID |
| domain_id | VARCHAR | Tenant ID |
| created_time | BIGINT | Creation time |

### 2.4.6 MCP Service-related Tables

**McpServerEntity (MCP Server Template Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key, UUID |
| server_code | VARCHAR | MCP identifier |
| name | VARCHAR | Chinese name |
| name_en | VARCHAR | English name |
| icon | VARCHAR | Icon |
| description | VARCHAR | Chinese description |
| description_en | VARCHAR | English description |
| readme | TEXT | Markdown document |
| url | VARCHAR | Official URL |
| server_config | TEXT | Installation configuration |
| tools | JSON | Tool set |
| type | VARCHAR | Built-in/Personal |
| org_type | VARCHAR | Installation type (NPX/UVX/SSE) |
| category | VARCHAR | Category |
| view_times | BIGINT | View count |
| install_times | BIGINT | Install count |

**McpServiceEntity (MCP Service Instance Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key, UUID |
| name | VARCHAR | Service name |
| name_en | VARCHAR | English name |
| description | VARCHAR | Description |
| readme | TEXT | Markdown document |
| org_type | VARCHAR | Package type (NPX/UVX/SSE) |
| deploy_type | VARCHAR | Deploy type (SSE/stdio/streamable_http) |
| server_config | TEXT | Service configuration |
| tools | JSON | Tool list |
| fc_instance_url | VARCHAR | Function instance URL |
| fc_instance_id | VARCHAR | Function instance ID |
| fc_instance_status | VARCHAR | Function instance status |
| function_name | VARCHAR | Function name |
| server_id | VARCHAR | Service template ID, foreign key |
| project_id | VARCHAR | Project ID |
| workspace_id | VARCHAR | Workspace ID |
| domain_id | VARCHAR | Tenant ID |
| icon | VARCHAR | Icon |
| visibility | VARCHAR | Visibility |
| is_share | INT | Whether shared |
| origin | INT | Origin |
| created_date | TIMESTAMP | Creation time |
| last_updated_date | TIMESTAMP | Update time |

### 2.4.7 Application-related Tables

**App (Application Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| app_id | VARCHAR | Primary key, application ID |
| project_id | VARCHAR | Project ID |
| workspace_id | VARCHAR | Workspace ID |
| name | VARCHAR | Application name |
| description | VARCHAR | Description |
| icon | VARCHAR | Icon |
| icon_name | VARCHAR | Icon name |
| tags | JSON | Tag list |
| app_type | VARCHAR | Application type (chat/scene) |
| resource_id | VARCHAR | Resource ID (agent or workflow ID) |
| resource_type | VARCHAR | Resource type (agent/workflow) |
| workflow_type | VARCHAR | Workflow type |
| input_params | TEXT | Input parameters |
| output_params | TEXT | Output parameters |
| prologue | TEXT | Opening message |
| suggest_queries | JSON | Suggested questions |
| creator | VARCHAR | Creator |
| published_on | DATETIME | Publish time |

**Table Relationships**:
- `App.resource_id` -> `AgentBaseInfo.agent_id` (when resource_type='agent')
- `App.resource_id` -> `WorkflowEntity.id` (when resource_type='workflow')

### 2.4.8 Datasource-related Tables

**DatasourceEntity (Datasource Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| id | VARCHAR | Primary key, UUID |
| project_id | VARCHAR | Project ID |
| workspace_id | VARCHAR | Workspace ID |
| domain_id | VARCHAR | Tenant ID |
| name | VARCHAR | Datasource name |
| type | VARCHAR | Type (MYSQL, etc.) |
| desc | VARCHAR | Description |
| internet_access | VARCHAR | Network access type |
| region | VARCHAR | Region |
| instance_id | VARCHAR | RDS instance ID |
| instance_name | VARCHAR | Instance name |
| connection_info | TEXT | Connection information (JSON format) |
| status | VARCHAR | Status (success/failed) |
| last_error_message | TEXT | Last error message |
| created_by | VARCHAR | Creator |
| creator_id | VARCHAR | Creator ID |
| created_on | DATETIME | Creation time |
| updated_by | VARCHAR | Updater |
| updater_id | VARCHAR | Updater ID |
| updated_on | DATETIME | Update time |

### 2.4.9 Skill-related Tables

**SkillEntity (Skill Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| skill_id | VARCHAR | Primary key, skill ID |
| domain_id | VARCHAR | Tenant ID |
| name | VARCHAR | Name |
| icon | VARCHAR | Icon |
| status | VARCHAR | Status |
| source | VARCHAR | Source |
| description | VARCHAR | Description |
| creator_id | VARCHAR | Creator ID |
| creator_name | VARCHAR | Creator name |
| latest_version | VARCHAR | Latest version |
| used_version | VARCHAR | Used version |
| created_at | BIGINT | Creation time |
| updated_at | BIGINT | Update time |
| workspace_id | VARCHAR | Workspace ID |
| project_id | VARCHAR | Project ID |
| published_asset | INT | Whether published |

**SkillVersionEntity (Skill Version Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| version_id | VARCHAR | Primary key, version ID |
| skill_id | VARCHAR | Skill ID, foreign key |
| version | VARCHAR | Version number |
| config | TEXT | Version configuration |
| created_at | BIGINT | Creation time |

### 2.4.10 API Key-related Tables

**ApiKeysEntity (API Key Table)**

| Field Name | Type | Description |
|------------|------|-------------|
| api_key_id | VARCHAR | Primary key, key ID |
| api_key_name | VARCHAR | Key name |
| api_key_value | VARCHAR | Key value |
| description | VARCHAR | Description |
| project_id | VARCHAR | Project ID |
| workspace_id | VARCHAR | Workspace ID |
| domain_id | VARCHAR | Tenant ID |
| user_id | VARCHAR | User ID |
| user_name | VARCHAR | Username |
| created_by_user_name | VARCHAR | Creator |
| last_updated_by_user_name | VARCHAR | Last user |
| created_date | BIGINT | Creation time |

### 2.4.11 Table Relationship Overview

```
t_users (User Table)
    │
    ├── WorkSpaceMemberEntity (Workspace Member) ──── WorkspaceEntity (Workspace)
    │                                            │
    │                                            ├── AgentBaseInfo (Agent Basic Info)
    │                                            │       │
    │                                            │       └── AgentVersion (Agent Version)
    │                                            │
    │                                            ├── WorkflowEntity (Workflow)
    │                                            │       │
    │                                            │       ├── WorkflowVersionEntity (Workflow Version)
    │                                            │       │
    │                                            │       └── SessionEntity (Session)
    │                                            │
    │                                            ├── App (Application)
    │                                            │       │
    │                                            │       └── (Associated with Agent or Workflow)
    │                                            │
    │                                            ├── DatasourceEntity (Datasource)
    │                                            │
    │                                            └── SkillEntity (Skill)
    │                                                    │
    │                                                    └── SkillVersionEntity (Skill Version)
    │
    ├── McpServerEntity (MCP Server Template)
    │       │
    │       └── McpServiceEntity (MCP Service Instance)
    │
    └── ApiKeysEntity (API Key)
```

### 2.4.12 Core Foreign Key Association Description

| Parent Table | Child Table | Association Field | Description |
|--------------|-------------|-------------------|-------------|
| WorkspaceEntity | WorkSpaceMemberEntity | workspace_id | Workspace to members one-to-many |
| WorkspaceEntity | AgentBaseInfo | workspace_id | Workspace to Agent one-to-many |
| WorkspaceEntity | WorkflowEntity | workspace_id | Workspace to Workflow one-to-many |
| WorkspaceEntity | App | workspace_id | Workspace to Application one-to-many |
| AgentBaseInfo | AgentVersion | agent_id | Agent to version one-to-many |
| WorkflowEntity | WorkflowVersionEntity | id->last_version_id | Workflow to version one-to-many |
| WorkflowEntity | SessionEntity | workflow_id | Workflow to session one-to-many |
| McpServerEntity | McpServiceEntity | id->server_id | MCP template to service instance one-to-many |
| SkillEntity | SkillVersionEntity | skill_id | Skill to version one-to-many |
| t_users | WorkSpaceMemberEntity | member_id | User to workspace member association |
| t_users | ApiKeysEntity | user_id | User to API key association |

---

# 3 frontend Module Details

The frontend module is the front-end portion of the project, built on the Angular framework, providing the user interaction interface.

## 3.1 Directory Structure

```
frontend/
├── angular.json                        # Angular project configuration file
├── package.json                        # NPM dependency configuration file
├── tsconfig.json                       # TypeScript configuration
├── tailwind.config.js                  # Tailwind CSS configuration
├── eslint.config.mjs                   # ESLint code linting configuration
├── .nvmrc                              # Node version specification
├── README.md                           # Frontend documentation
├── src/                                # Source code directory
│   ├── index.html                      # HTML entry file
│   ├── main.ts                         # Angular application entry
│   ├── app/                            # Application root component
│   │   ├── app.component.ts
│   │   ├── app.component.html
│   │   ├── app.component.less
│   │   └── index.ts
│   ├── agentcore/                      # Agent core module
│   ├── core/                           # Core module
│   │   ├── i18n/                       # Internationalization
│   │   ├── providers/                  # Dependency injection providers
│   │   └── services/                   # Core services
│   ├── shared/                         # Shared module
│   │   ├── base/                       # Base components
│   │   ├── components/                 # Shared components
│   │   ├── config/                     # Shared configuration
│   │   ├── decorators/                 # Decorators
│   │   ├── directives/                 # Directives
│   │   ├── guard/                      # Route guards
│   │   ├── services/                   # Shared services
│   │   └── validation/                 # Validation
│   ├── routes/                         # Route module
│   │   ├── agent-center/               # Agent Center
│   │   ├── app-center/                 # App Center
│   │   ├── code-editor/                # Code Editor
│   │   ├── datasource-management/      # Datasource Management
│   │   ├── development-configuration/  # Development Configuration
│   │   ├── experience-creation/        # Experience Creation
│   │   ├── health/                     # Health Check
│   │   ├── home/                       # Home
│   │   ├── information-template/       # Information Template
│   │   ├── intent-package/             # Intent Package
│   │   ├── knowledge-center/           # Knowledge Center
│   │   ├── left-menu/                  # Left Menu
│   │   ├── memory-lib/                 # Memory Library
│   │   ├── mobile/                     # Mobile
│   │   ├── model-management/           # Model Management
│   │   ├── model-square/               # Model Square
│   │   ├── overview/                   # Overview
│   │   ├── platform-management/        # Platform Management
│   │   ├── plugin-market/              # Plugin Market
│   │   ├── prompt/                     # Prompt
│   │   ├── service-market/             # Service Market
│   │   ├── subscription/               # Subscription
│   │   ├── tool/                       # Tool
│   │   ├── web-page-experience/        # Web Page Experience
│   │   └── root.routes.ts              # Root route configuration
│   ├── services/                       # Global services
│   ├── constants/                      # Constant definitions
│   ├── enums/                          # Enum definitions
│   ├── models/                         # Data models
│   ├── interfaces/                     # Interface definitions
│   ├── pipes/                          # Pipes
│   ├── utils/                          # Utility functions
│   ├── assets/                         # Static assets
│   ├── styles/                         # Global styles
│   ├── environment/                    # Environment configuration
│   ├── mock/                           # Mock data
│   ├── classes/                        # Type classes
│   ├── types/                          # Type definitions
│   └── single-spa/                     # Micro-frontend configuration
└── .husky/                             # Git hook configuration
```

## 3.2 Frontend Tech Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Core Framework** | Angular | 20.3.25 |
| **UI Component Library** | NG-ZORRO (Ant Design for Angular) | 20.4.4 |
| **State Management** | RxJS | 7.8.0 |
| **Charting Library** | ECharts | 6.1.0 |
| **Graph Editor** | AntV X6 | 3.1.4 |
| **Markdown** | ngx-markdown | 20.1.0 |
| **Code Editor** | Monaco Editor | 0.52.2 |
| **Internationalization** | i18next | 22.5.1 |
| **CSS Framework** | Tailwind CSS | 3.2.7 |
| **Build Tool** | Angular Build / Webpack | 20.3.13 / 5.95.0 |
| **Language** | TypeScript | 5.8.3 |

## 3.3 Core Functional Module Description

| Module Path | Description |
|-------------|-------------|
| **routes/agent-center** | Agent Center, provides a visual interface for Agent creation, configuration, and management |
| **routes/app-center** | App Center, manages the lifecycle of Agent applications |
| **routes/knowledge-center** | Knowledge Center, provides knowledge base creation, upload, and retrieval functions |
| **routes/plugin-market** | Plugin Market, browse, install, and manage plugins |
| **routes/prompt** | Prompt management, provides prompt writing, debugging, and optimization functions |
| **routes/model-management** | Model Management, configure and manage large language models |
| **routes/datasource-management** | Datasource Management, manages various external datasource connections |
| **routes/development-configuration** | Development Configuration, provides development environment and parameter configuration |
| **routes/memory-lib** | Memory Library, manages Agent memory configuration |
| **routes/code-editor** | Code Editor, provides online code writing capability |
| **shared/components** | Common UI component library, reused across modules |
| **core/services** | Core services, including API calls, authentication, global state management, etc. |

---

# 4 docs Module Details

The docs module stores various technical documents for the project, providing developers with detailed usage and development guides.

## 4.1 Directory Structure

```
docs/
├── README.md                            # Documentation navigation entry
├── images/                              # Documentation image assets
│   └── (various screenshots and diagrams)
├── zh/                                  # Chinese documentation (authoritative source)
│   ├── SUMMARY.md                       # Chinese documentation table of contents index
│   ├── tutorial/                        # Tutorials (numbered with digit prefixes)
│   │   ├── 01-quick-start.md
│   │   └── 02-user-guide.md
│   ├── how-to/                          # How-to guides
│   │   ├── deploy-service.md
│   │   ├── upgrade-from-beta4.md
│   │   ├── development-guide.md
│   │   ├── asset-plaza-preset.md
│   │   ├── configure-opentelemetry.md
│   │   └── troubleshooting.md
│   ├── reference/                       # Reference documentation
│   │   └── rest-api.md
│   └── explanation/                     # Explanation documents
│       └── architecture-overview.md
└── en/                                  # English documentation (follows)
```

## 4.2 Documentation Function Description

| File | Description |
|------|-------------|
| **reference/rest-api.md** | API reference documentation, detailing all REST API request/response formats, parameter descriptions, error codes, etc. |
| **how-to/deploy-service.md** | Detailed installation and deployment steps, including environment preparation, Docker deployment configuration, database initialization, etc. |
| **explanation/architecture-overview.md** | Overall project architecture description, including technology selection, module division, system design, etc. |
| **tutorial/02-user-guide.md** | User guide, detailing the usage of various platform features |

---

# 5 docker Module Details

The docker module provides Docker containerization deployment configuration for the project.

## 5.1 Directory Structure

```
docker/
├── compose/                            # Docker Compose configuration
├── k8s/                                # Kubernetes configuration
├── studio-console/                     # Console Docker configuration
├── studio-manager/                     # Manager service Docker configuration
├── studio-runtime/                     # Runtime service Docker configuration
├── studio-builder/                     # Builder service Docker configuration
├── build.sh                            # Docker image build script
├── package.sh                          # Packaging script
├── README.md                           # Docker deployment instructions
└── .gitattributes                      # Git attributes configuration
```

## 5.2 Deployment Script Description

| File/Directory | Description |
|----------------|-------------|
| **build.sh** | Docker image build script, responsible for building Docker images for each service |
| **package.sh** | Packaging script, responsible for packaging applications into deployable format |
| **compose/** | Docker Compose orchestration files, defining multi-container deployment configurations |
| **studio-manager/** | Manager service Docker configuration and environment variables |
| **studio-runtime/** | Runtime service Docker configuration and environment variables |
| **studio-builder/** | Builder service Docker configuration and startup scripts |
| **studio-console/** | Console service Nginx and image build configuration |

---

# 6 Project Tech Stack Summary

## 6.1 Backend Tech Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Core Framework** | Spring Boot | 3.5.15 |
| **Security Framework** | Spring Security | 6.5.10 |
| **Java Version** | JDK | 17 |
| **ORM Framework** | Hibernate | 6.6.8.Final |
| **Database Driver** | MariaDB JDBC (default connection to MySQL-compatible database) | 3.5.6 |
| **Database Driver** | PostgreSQL JDBC | 42.7.11 |
| **Cache** | Redis (Redisson) | 3.39.0 |
| **Database** | H2 | 2.2.224 |
| **Database** | OpenGauss JDBC | 5.0.0 |
| **Object Storage** | OBS SDK | 3.23.9 |
| **Communication Framework** | Netty | 4.1.133.Final |
| **HTTP Client** | OkHttp SSE | 4.12.0 |
| **HTTP Client** | HTTPClient5 | 5.4.4 |
| **Object Mapping** | MapStruct | 1.6.3 |
| **JSON Processing** | FastJSON2 | 2.0.51 |
| **Authentication** | JWT (Nimbus) | 10.3 |
| **Task Scheduling** | Quartz | 2.5.2 |
| **Document Processing** | Apache POI | 5.4.1 |
| **MCP Protocol** | MCP SDK | 0.16.0 |

## 6.2 Frontend Tech Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Core Framework** | Angular | 20.3.25 |
| **UI Component Library** | NG-ZORRO | 20.4.4 |
| **State Management** | RxJS | 7.8.0 |
| **Charting Library** | ECharts | 6.1.0 |
| **Graph Editor** | AntV X6 | 3.1.4 |
| **Markdown** | ngx-markdown | 20.1.0 |
| **Code Editor** | Monaco Editor | 0.52.2 |
| **Internationalization** | i18next | 22.5.1 |
| **CSS Framework** | Tailwind CSS | 3.2.7 |
| **Build Tool** | Angular Build | 20.3.13 |
| **Language** | TypeScript | 5.8.3 |

---

# 7 Project Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Studio Console (Angular + Nginx)                     │
│  Agent Center | Knowledge Center | Plugin Market | Prompt Mgmt |     │
│  Model Management | Workflow Orchestration                          │
└─────────────────────────────────────────────────────────────────────┘
                  │ Management API                │ Execution/Publish API
                  ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ Studio Manager (Java, 31111)    │  │ Studio Runtime (Python, 31014)  │
│ Agent/Knowledge/Tool/MCP/       │  │ Agent/Workflow/LLM/MCP/         │
│ Model Management                │  │ Memory Execution                │
└─────────────────────────────────┘  └─────────────────────────────────┘
                  │ Build, NL2, Prompt invocation          │
                  ▼                                       │
┌─────────────────────────────────┐                        │
│ Studio Builder (Python, 31015)  │                        │
│ NL2 | Prompt Optimization |     │                        │
│ Model Tuning                    │                        │
└─────────────────────────────────┘                        │
                  │                                       │
                  └──────────────────┬────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│            Shared Packages / Infrastructure                         │
│ model_service | storage | MySQL | Redis | MinIO/OBS                 │
└─────────────────────────────────────────────────────────────────────┘
```
