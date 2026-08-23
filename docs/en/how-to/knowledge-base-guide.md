# Knowledge Base Integration Guide

## 1. Introduction

The knowledge base provides enterprise private knowledge retrieval capabilities for agents through Retrieval-Augmented Generation (RAG) technology. It supports vectorized storage and semantic retrieval of text documents, FAQ data, and other content, ensuring agent responses are well-grounded and traceable.

**Core Capabilities:**
- Supports multiple document formats (docx, pdf, pptx, xlsx, csv, txt, md, etc.)
- Supports two data forms: knowledge documents and FAQ Q&A pairs
- Supports vectorized storage and semantic retrieval
- Provides retrieval augmentation capabilities for applications and workflows

---

## 2. Knowledge Base Classification

| Type | Document Management | Data Storage | Use Case |
|------|---------------------|--------------|----------|
| **Platform Knowledge Base** | Full lifecycle management: create, upload documents, parse, vectorize, retrieve | Platform internal | No existing knowledge base; need to upload and manage documents |
| **Third-party Knowledge Base** | Not supported: retrieval only; documents managed by third-party system | Third-party system | Existing enterprise knowledge base; want direct integration |

**Supported Third-party Knowledge Base Types:**

| Type | Description |
|------|-------------|
| General | Generic external knowledge base; requires adaptation according to integration specifications |
| KooSearch | Direct integration with KooSearch knowledge base |
| RAGFlow | Direct integration with RAGFlow knowledge base |

---

## 3. Create Platform Knowledge Base

### Prerequisites

- LakeSearch service is deployed and accessible

### First-time Default Knowledge Base Connection Configuration (Required for New Environments)

Before creating a platform knowledge base for the first time in a new environment, you must complete the default knowledge base connection configuration:

1. In the "Create Knowledge Base" dialog, click **Default Knowledge Base Configuration**
2. Fill in connection information:
   - **Service Address**: LakeSearch access address
   - **Authentication Mode**:
     - `basic`: HTTP Basic authentication; requires Base64-encoded username:password in request header
     - `none`: No authentication; suitable for internal networks without authentication
   - **Authentication Info**: Fill in credentials (username:password) for basic mode
3. Click **Test Connection** to confirm "Connection successful" prompt
4. Click **OK** to save

After configuration is complete, return to the create knowledge base dialog, select "Default" and click "OK" to enter the knowledge base creation page.

> **UI Prompt Description:**
> - **"Connect External Knowledge Base" button**: Displayed when there are no third-party knowledge base connections in the system, guiding users to connect external knowledge bases. Once at least one third-party knowledge base connection is configured, this button automatically hides.
> - **"Default Knowledge Base Configuration" button**: Displayed when the default knowledge base connection has not been configured (i.e., no default connection record in the database). After completing the default configuration, this button automatically hides.

### Steps

1. Go to **Development Center > Component Library**, select **Knowledge Base** tab
2. Click **Create Knowledge Base**, select **Default** in the dialog, click **OK**
3. Fill in basic information:
   - Knowledge base name (required, 1-50 characters)
   - Description (optional, up to 100 characters)
4. Configure models:
   - Vector model: used for document vectorization and semantic retrieval
   - Rerank model: used for fine-grained sorting of retrieval results
5. Configure parsing and splitting strategies (optional)
6. Click **OK** to complete creation

### Upload Documents

After creation, you can upload documents:
- **Knowledge Documents**: Supports docx, pdf, pptx, xlsx, txt, md formats; max 20MB per file
- **FAQ Q&A Pairs**: Manually enter questions and answers
- **FAQ Documents**: Batch import via template; supports xlsx, docx formats

---

## 4. Connect Third-party Knowledge Base

### 4.1 General Knowledge Base

Suitable for self-developed or non-standard interface knowledge base systems.

**Connection Steps:**

1. Go to **Knowledge Base** tab, switch to **External Knowledge Base Connection**
2. Click **Connect External Knowledge Base**, select type **General**
3. Fill in connection information:
   - Knowledge base name
   - Service address (must support retrieval and list interfaces)
   - Authentication info (key in HTTP Header)
4. Click **Test Connection**, save after success
5. Return to **Knowledge Base** tab, click **Create Knowledge Base**, select **Third-party**, check the connected General knowledge base

**Adaptation Requirements:** Third-party knowledge bases must provide retrieval and list interfaces according to integration specifications.

### 4.2 KooSearch Knowledge Base

Suitable for scenarios where KooSearch service is already deployed.

**Connection Steps:**

1. Go to **Knowledge Base** tab, switch to **External Knowledge Base Connection**
2. Click **Connect External Knowledge Base**, select type **KooSearch**
3. Fill in connection information:
   - Knowledge base name
   - Service address
   - Authentication info
4. Click **Test Connection**, save after success
5. Return to **Knowledge Base** tab, click **Create Knowledge Base**, select **Third-party**, check the connected KooSearch knowledge base

### 4.3 RAGFlow Knowledge Base

Suitable for scenarios where RAGFlow is already purchased or deployed.

**Connection Steps:**

1. Go to **Knowledge Base** tab, switch to **External Knowledge Base Connection**
2. Click **Connect External Knowledge Base**, select type **RAGFlow**
3. Fill in connection information:
   - Knowledge base name
   - Service address
   - API Key
4. Click **Test Connection**, save after success
5. Return to **Knowledge Base** tab, click **Create Knowledge Base**, select **Third-party**, check the connected RAGFlow knowledge base

---

## 5. Usage Limits

| Resource | Limit |
|----------|-------|
| Documents per knowledge base | 500 |
| Knowledge bases per agent | 3 |
| Knowledge bases per workflow | 3 |
| Knowledge base icon size | 200KB |
| Knowledge base tag limit | 100 |

---

## 6. FAQ

### 6.1 No Response or Error When Clicking "Default Knowledge Base Configuration"

**Check Steps:**

1. Confirm LakeSearch service is deployed and service address is accessible
2. Check studio-manager service logs, search for keywords:
   - `Fail to list models` — Model query interface call failed
   - `Fail to get KnowledgeBase Connection Info` — Connection configuration read failed

**Troubleshooting SQL:**

```sql
-- Check if default connection configuration exists
SELECT id, params FROM t_knowledge_base_connection
WHERE id = 'default_lakesearch_inside_connection_id';

-- Check if connection route exists
SELECT * FROM t_kb_connection_router
WHERE knowledge_base_connection_id = 'default_lakesearch_inside_connection_id';
```

If query results are empty, database initialization is incomplete. Please check:
- Whether studio-manager service startup logs show database initialization errors
- Whether database connection in environment variables or configuration files is correct

### 6.2 Vector Model/Rerank Model Dropdown is Empty When Creating Knowledge Base

**Cause:** Models are not registered in LakeSearch service.

**Solution:** Confirm LakeSearch service has embedding and rerank models configured.

### 6.3 How to Modify Default Knowledge Base Configuration After Completion

The frontend hides the entry after configuration is complete; there is no direct modification interface. You can update directly via SQL:

```sql
-- View current configuration
SELECT id, params FROM t_knowledge_base_connection
WHERE id = 'default_lakesearch_inside_connection_id';

-- Update configuration (params is JSON format, containing endpoint, auth_mode, authorization fields)
UPDATE t_knowledge_base_connection
SET params = '{"endpoint":"new_address","auth_mode":"basic","authorization":"new_credentials"}'
WHERE id = 'default_lakesearch_inside_connection_id';
```

Refresh the frontend page after modification for changes to take effect.
