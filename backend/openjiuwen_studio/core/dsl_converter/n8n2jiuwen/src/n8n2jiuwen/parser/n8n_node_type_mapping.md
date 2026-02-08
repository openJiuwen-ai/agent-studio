# n8n Workflow Node Type Mapping Reference

## Complete Guide for Parsing n8n Workflows to Other Agentic Frameworks

---

## 1. Workflow JSON Root Structure

When you export an n8n workflow, the JSON has this structure:

```json
{
  "name": "Workflow Name",
  "nodes": [...],           // Array of node definitions
  "connections": {...},     // Object mapping data flow between nodes
  "pinData": {...},         // Optional: pinned test data
  "settings": {...},        // Workflow-level settings
  "staticData": null,       // Persisted data across executions
  "tags": [],               // Tags for organization
  "triggerCount": 0,        // Number of trigger nodes
  "updatedAt": "ISO-8601",  // Last update timestamp
  "versionId": "uuid"       // Version identifier
}
```

---

## 2. Universal Node Structure

Every node in the `nodes` array follows this schema:

```json
{
  "id": "uuid",                           // Unique identifier
  "name": "Node Display Name",            // User-facing name
  "type": "n8n-nodes-base.nodetype",      // Node type identifier
  "typeVersion": 1,                       // Version of node implementation
  "position": [x, y],                     // Canvas position [x, y]
  "parameters": {...},                    // Node-specific configuration
  "credentials": {...},                   // Credential references (optional)
  "disabled": false,                      // Whether node is disabled
  "notesInFlow": false,                   // Display notes in flow
  "notes": ""                             // Node notes/comments
}
```

---

## 3. Node Categories and Types

### 3.1 TRIGGER NODES (Workflow Entry Points)

**Purpose**: Start workflow execution

| Type Pattern | Description | Example |
|-------------|-------------|---------|
| `n8n-nodes-base.manualWorkflowTrigger` | Manual execution | Click to run |
| `n8n-nodes-base.webhook` | HTTP webhook | External API calls |
| `n8n-nodes-base.scheduleTrigger` | Cron/interval | Scheduled runs |
| `n8n-nodes-base.formTrigger` | Form submission | Web forms |
| `n8n-nodes-langchain.chatTrigger` | Chat interface | AI chat input |
| `n8n-nodes-base.errorTrigger` | Error handler | Catch errors |
| `n8n-nodes-base.executeWorkflowTrigger` | Sub-workflow call | Parent invocation |
| `n8n-nodes-langchain.mcpTrigger` | MCP server trigger | AI agent protocol |

**App-Specific Triggers** (pattern: `n8n-nodes-base.{service}Trigger`):
- `gmailTrigger`, `slackTrigger`, `telegramTrigger`, `githubTrigger`
- `airtableTrigger`, `notionTrigger`, `googleSheetsTrigger`
- `stripeTrigger`, `shopifyTrigger`, `webhookTrigger`

---

### 3.2 CORE NODES (Logic & Data Processing)

**Purpose**: Control flow, data manipulation, generic operations

| Node Type | Purpose | Key Parameters |
|-----------|---------|----------------|
| `n8n-nodes-base.code` | Custom JS/Python | `jsCode`, `pythonCode`, `mode` |
| `n8n-nodes-base.if` | Conditional branching | `conditions` |
| `n8n-nodes-base.switch` | Multi-path routing | `rules`, `fallbackOutput` |
| `n8n-nodes-base.merge` | Combine data streams | `mode`, `joinMode` |
| `n8n-nodes-base.splitInBatches` | Loop/batch processing | `batchSize` |
| `n8n-nodes-base.set` | Set/Edit fields | `assignments`, `options` |
| `n8n-nodes-base.filter` | Filter items | `conditions` |
| `n8n-nodes-base.sort` | Sort items | `sortFieldsUi` |
| `n8n-nodes-base.limit` | Limit output | `maxItems` |
| `n8n-nodes-base.aggregate` | Aggregate data | `aggregate` |
| `n8n-nodes-base.splitOut` | Split arrays | `fieldToSplitOut` |
| `n8n-nodes-base.removeDuplicates` | Deduplicate | `compareBy` |
| `n8n-nodes-base.httpRequest` | HTTP calls | `url`, `method`, `authentication` |
| `n8n-nodes-base.wait` | Pause execution | `amount`, `unit` |
| `n8n-nodes-base.executeWorkflow` | Call sub-workflow | `workflowId` |
| `n8n-nodes-base.respondToWebhook` | Return response | `responseBody` |
| `n8n-nodes-base.stopAndError` | Halt with error | `errorMessage` |
| `n8n-nodes-base.noOp` | No operation | (pass-through) |

---

### 3.3 APP/ACTION NODES (Service Integrations)

**Pattern**: `n8n-nodes-base.{serviceName}`

Common services: `slack`, `gmail`, `notion`, `airtable`, `googleSheets`, `postgres`, `mongodb`, `github`, `jira`, `discord`, `telegram`, `openai`, `anthropic`

**Typical Parameters**:
```json
{
  "resource": "message",         // Resource type
  "operation": "send",           // CRUD operation
  // Service-specific fields...
}
```

---

### 3.4 CLUSTER NODES (AI/LangChain)

⚠️ **SPECIAL ATTENTION**: These have hierarchical structure with root nodes and sub-nodes

#### 3.4.1 ROOT NODES (AI Orchestrators)

| Node Type | Purpose |
|-----------|---------|
| `n8n-nodes-langchain.agent` | AI Agent with tools |
| `n8n-nodes-langchain.chainLlm` | Basic LLM chain |
| `n8n-nodes-langchain.chainRetrievalQa` | Q&A with retrieval |
| `n8n-nodes-langchain.chainSummarization` | Document summarization |
| `n8n-nodes-langchain.informationExtractor` | Extract structured data |
| `n8n-nodes-langchain.textClassifier` | Text classification |
| `n8n-nodes-langchain.sentimentAnalysis` | Sentiment detection |
| `n8n-nodes-langchain.code` | LangChain code node |

**Vector Store Root Nodes**:
- `n8n-nodes-langchain.vectorStoreInMemory` (Simple)
- `n8n-nodes-langchain.vectorStorePinecone`
- `n8n-nodes-langchain.vectorStoreSupabase`
- `n8n-nodes-langchain.vectorStoreQdrant`
- `n8n-nodes-langchain.vectorStorePgVector`
- `n8n-nodes-langchain.vectorStoreMilvus`
- `n8n-nodes-langchain.vectorStoreWeaviate`
- `n8n-nodes-langchain.vectorStoreMongoDBAtlas`
- `n8n-nodes-langchain.vectorStoreRedis`
- `n8n-nodes-langchain.vectorStoreZep`
- `n8n-nodes-langchain.vectorStoreAzureAISearch`

---

#### 3.4.2 SUB-NODES (Connected to Root Nodes)

**Chat/LLM Models** (connect to `ai_languageModel` input):

| Node Type | Provider |
|-----------|----------|
| `n8n-nodes-langchain.lmChatOpenAi` | OpenAI GPT |
| `n8n-nodes-langchain.lmChatAnthropic` | Anthropic Claude |
| `n8n-nodes-langchain.lmChatGoogleGemini` | Google Gemini |
| `n8n-nodes-langchain.lmChatAzureOpenAi` | Azure OpenAI |
| `n8n-nodes-langchain.lmChatOllama` | Ollama (local) |
| `n8n-nodes-langchain.lmChatGroq` | Groq |
| `n8n-nodes-langchain.lmChatMistralCloud` | Mistral |
| `n8n-nodes-langchain.lmChatDeepSeek` | DeepSeek |
| `n8n-nodes-langchain.lmChatCohere` | Cohere |
| `n8n-nodes-langchain.lmChatAwsBedrock` | AWS Bedrock |
| `n8n-nodes-langchain.lmChatGoogleVertex` | Google Vertex |
| `n8n-nodes-langchain.lmChatOpenRouter` | OpenRouter |
| `n8n-nodes-langchain.lmChatXaiGrok` | xAI Grok |
| `n8n-nodes-langchain.lmChatVercel` | Vercel AI Gateway |

**Basic LLM Models** (non-chat):
- `n8n-nodes-langchain.lmCohere`
- `n8n-nodes-langchain.lmOllama`
- `n8n-nodes-langchain.lmOpenHuggingFaceInference`

---

**Memory Sub-Nodes** (connect to `ai_memory` input):

| Node Type | Storage |
|-----------|---------|
| `n8n-nodes-langchain.memoryBufferWindow` | Simple (in-memory) |
| `n8n-nodes-langchain.memoryRedisChat` | Redis |
| `n8n-nodes-langchain.memoryPostgresChat` | PostgreSQL |
| `n8n-nodes-langchain.memoryMongoChat` | MongoDB |
| `n8n-nodes-langchain.memoryXata` | Xata |
| `n8n-nodes-langchain.memoryZep` | Zep |
| `n8n-nodes-langchain.memoryMotorhead` | Motorhead |
| `n8n-nodes-langchain.memoryManager` | Chat Memory Manager |

---

**Embedding Sub-Nodes** (connect to `ai_embedding` input):

| Node Type | Provider |
|-----------|----------|
| `n8n-nodes-langchain.embeddingsOpenAi` | OpenAI |
| `n8n-nodes-langchain.embeddingsAzureOpenAi` | Azure OpenAI |
| `n8n-nodes-langchain.embeddingsGoogleGemini` | Google Gemini |
| `n8n-nodes-langchain.embeddingsGoogleVertex` | Google Vertex |
| `n8n-nodes-langchain.embeddingsGooglePalm` | Google PaLM |
| `n8n-nodes-langchain.embeddingsCohere` | Cohere |
| `n8n-nodes-langchain.embeddingsOllama` | Ollama |
| `n8n-nodes-langchain.embeddingsHuggingFaceInference` | HuggingFace |
| `n8n-nodes-langchain.embeddingsAwsBedrock` | AWS Bedrock |
| `n8n-nodes-langchain.embeddingsMistralCloud` | Mistral |

---

**⚠️ TOOL SUB-NODES** (connect to `ai_tool` input) - **CRITICAL FOR AGENTS**

| Node Type | Description | Key Parameters |
|-----------|-------------|----------------|
| `n8n-nodes-langchain.toolCalculator` | Math operations | (none) |
| `n8n-nodes-langchain.toolCode` | Custom code tool | `jsCode`, `name`, `description` |
| `n8n-nodes-langchain.toolHttpRequest` | HTTP requests | `url`, `method`, `description` |
| `n8n-nodes-langchain.toolWorkflow` | Call n8n workflow | `workflowId`, `description` |
| `n8n-nodes-langchain.toolWikipedia` | Wikipedia search | (none) |
| `n8n-nodes-langchain.toolSerpApi` | Google search | `country`, `language` |
| `n8n-nodes-langchain.toolWolframAlpha` | Wolfram Alpha | (none) |
| `n8n-nodes-langchain.toolVectorStore` | Vector search | `name`, `description` |
| `n8n-nodes-langchain.toolMcp` | MCP client | `sseEndpoint`, `tools` |
| `n8n-nodes-langchain.toolSearxng` | SearXNG search | (none) |
| `n8n-nodes-langchain.toolThink` | Reasoning step | (none) |
| `n8n-nodes-langchain.toolAiAgent` | Nested agent | `agentDescription` |

---

**Document Loaders** (connect to `ai_document` input):

| Node Type | Source |
|-----------|--------|
| `n8n-nodes-langchain.documentDefaultDataLoader` | Default/generic |
| `n8n-nodes-langchain.documentGitHubLoader` | GitHub repos |

---

**Text Splitters** (connect to `ai_textSplitter` input):

| Node Type | Method |
|-----------|--------|
| `n8n-nodes-langchain.textSplitterCharacterTextSplitter` | By character |
| `n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter` | Recursive |
| `n8n-nodes-langchain.textSplitterTokenSplitter` | By token |

---

**Retrievers** (connect to `ai_retriever` input):

| Node Type | Purpose |
|-----------|---------|
| `n8n-nodes-langchain.retrieverVectorStore` | Vector search |
| `n8n-nodes-langchain.retrieverMultiQuery` | Multi-query |
| `n8n-nodes-langchain.retrieverContextualCompression` | Compressed context |
| `n8n-nodes-langchain.retrieverWorkflow` | Workflow-based |

---

**Output Parsers** (connect to `ai_outputParser` input):

| Node Type | Format |
|-----------|--------|
| `n8n-nodes-langchain.outputParserStructured` | JSON schema |
| `n8n-nodes-langchain.outputParserItemList` | List items |
| `n8n-nodes-langchain.outputParserAutoFixing` | Auto-correct |

---

**Other Sub-Nodes**:

| Node Type | Purpose |
|-----------|---------|
| `n8n-nodes-langchain.rerankerCohere` | Rerank results |
| `n8n-nodes-langchain.modelSelector` | Dynamic model selection |

---

## 4. Connections Structure

The `connections` object maps how data flows:

```json
{
  "connections": {
    "Source Node Name": {
      "main": [                         // Main output type
        [                               // First output (index 0)
          {
            "node": "Target Node Name",
            "type": "main",             // Input type on target
            "index": 0                  // Input index on target
          }
        ]
      ],
      "ai_tool": [                      // AI tool connections
        [
          {
            "node": "Calculator Tool",
            "type": "ai_tool",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

### Connection Types:

| Type | Used For |
|------|----------|
| `main` | Standard data flow |
| `ai_languageModel` | LLM connections |
| `ai_memory` | Memory connections |
| `ai_tool` | Tool connections |
| `ai_embedding` | Embedding connections |
| `ai_document` | Document loader connections |
| `ai_textSplitter` | Text splitter connections |
| `ai_retriever` | Retriever connections |
| `ai_outputParser` | Output parser connections |
| `ai_vectorStore` | Vector store connections |

---

## 5. Agent Node Deep Dive

### Full Agent Node Structure:

```json
{
  "id": "agent-uuid",
  "name": "AI Agent",
  "type": "n8n-nodes-langchain.agent",
  "typeVersion": 1.7,
  "position": [820, 340],
  "parameters": {
    "options": {
      "systemMessage": "You are a helpful assistant...",
      "maxIterations": 10,
      "returnIntermediateSteps": false
    },
    "promptType": "define",
    "text": "={{ $json.chatInput }}"
  }
}
```

### Agent with Multiple Tools (Connection Example):

```json
{
  "connections": {
    "AI Agent": {
      "ai_languageModel": [[{"node": "OpenAI Chat Model", "type": "ai_languageModel", "index": 0}]],
      "ai_memory": [[{"node": "Simple Memory", "type": "ai_memory", "index": 0}]],
      "ai_tool": [
        [{"node": "Calculator", "type": "ai_tool", "index": 0}],
        [{"node": "HTTP Request Tool", "type": "ai_tool", "index": 0}],
        [{"node": "Custom Code Tool", "type": "ai_tool", "index": 0}],
        [{"node": "Wikipedia", "type": "ai_tool", "index": 0}],
        [{"node": "Call Workflow Tool", "type": "ai_tool", "index": 0}]
      ]
    },
    "Chat Trigger": {
      "main": [[{"node": "AI Agent", "type": "main", "index": 0}]]
    }
  }
}
```

---

## 6. Parsing Strategy for Other Frameworks

### 6.1 Node Type Identification

```python
def categorize_node(node):
    node_type = node['type']
    
    # Trigger nodes
    if 'Trigger' in node_type or node_type.endswith('trigger'):
        return 'trigger'
    
    # AI/LangChain nodes
    if 'langchain' in node_type:
        if node_type in ROOT_AI_NODES:
            return 'ai_root'
        else:
            return 'ai_subnode'
    
    # Core logic nodes
    if node_type in CORE_NODES:
        return 'core'
    
    # App integration nodes
    return 'app_action'
```

### 6.2 Tool Extraction for Agents

```python
def extract_agent_tools(workflow_json, agent_node_name):
    """Extract all tools connected to an agent."""
    tools = []
    connections = workflow_json.get('connections', {})
    
    for source_name, outputs in connections.items():
        if 'ai_tool' in outputs:
            for tool_connections in outputs['ai_tool']:
                for conn in tool_connections:
                    if conn.get('type') == 'ai_tool':
                        # Find the tool node definition
                        tool_node = find_node_by_name(
                            workflow_json['nodes'], 
                            source_name
                        )
                        tools.append({
                            'name': tool_node['name'],
                            'type': tool_node['type'],
                            'parameters': tool_node.get('parameters', {})
                        })
    return tools
```

### 6.3 Framework Mapping Table

| n8n Node Type | LangChain Equivalent | CrewAI | AutoGen |
|---------------|---------------------|--------|---------|
| `agent` | `AgentExecutor` | `Agent` | `AssistantAgent` |
| `toolCode` | `StructuredTool` | `Tool` | `function` |
| `toolHttpRequest` | `RequestsGetTool` | `Tool` | `function` |
| `toolWorkflow` | `Tool` (custom) | `Tool` | `function` |
| `lmChatOpenAi` | `ChatOpenAI` | `ChatOpenAI` | `OpenAI` |
| `lmChatAnthropic` | `ChatAnthropic` | `ChatAnthropic` | `Anthropic` |
| `memoryBufferWindow` | `ConversationBufferWindowMemory` | - | - |
| `vectorStorePinecone` | `Pinecone` | - | - |

---

## 7. Complete Node Type Reference Lists

### All Trigger Types:
```
n8n-nodes-base.manualWorkflowTrigger
n8n-nodes-base.webhook
n8n-nodes-base.scheduleTrigger
n8n-nodes-base.formTrigger
n8n-nodes-base.errorTrigger
n8n-nodes-base.executeWorkflowTrigger
n8n-nodes-base.workflowTrigger
n8n-nodes-base.n8nTrigger
n8n-nodes-base.activationTrigger
n8n-nodes-base.emailImapTrigger
n8n-nodes-base.localFileTrigger
n8n-nodes-base.rssFeedReadTrigger
n8n-nodes-base.sseTrigger
n8n-nodes-langchain.chatTrigger
n8n-nodes-langchain.mcpTrigger
n8n-nodes-base.evaluationTrigger
+ 100+ app-specific triggers ({app}Trigger)
```

### All Core Node Types:
```
n8n-nodes-base.code
n8n-nodes-base.if
n8n-nodes-base.switch
n8n-nodes-base.merge
n8n-nodes-base.splitInBatches
n8n-nodes-base.set
n8n-nodes-base.filter
n8n-nodes-base.sort
n8n-nodes-base.limit
n8n-nodes-base.aggregate
n8n-nodes-base.splitOut
n8n-nodes-base.removeDuplicates
n8n-nodes-base.renameKeys
n8n-nodes-base.httpRequest
n8n-nodes-base.wait
n8n-nodes-base.executeWorkflow
n8n-nodes-base.respondToWebhook
n8n-nodes-base.respondToChat
n8n-nodes-base.stopAndError
n8n-nodes-base.noOp
n8n-nodes-base.html
n8n-nodes-base.xml
n8n-nodes-base.markdown
n8n-nodes-base.crypto
n8n-nodes-base.dateTime
n8n-nodes-base.jwt
n8n-nodes-base.totp
n8n-nodes-base.compression
n8n-nodes-base.convertToFile
n8n-nodes-base.extractFromFile
n8n-nodes-base.readWriteFile
n8n-nodes-base.ftp
n8n-nodes-base.ssh
n8n-nodes-base.git
n8n-nodes-base.ldap
n8n-nodes-base.graphql
n8n-nodes-base.sendEmail
n8n-nodes-base.rssRead
n8n-nodes-base.n8n
n8n-nodes-base.form
n8n-nodes-base.summarize
n8n-nodes-base.compareDatasets
n8n-nodes-base.aiTransform
n8n-nodes-base.dataTable
n8n-nodes-base.debugHelper
n8n-nodes-base.executionData
n8n-nodes-base.evaluation
n8n-nodes-langchain.guardrails
```

### All AI Root Node Types:
```
n8n-nodes-langchain.agent
n8n-nodes-langchain.chainLlm
n8n-nodes-langchain.chainRetrievalQa
n8n-nodes-langchain.chainSummarization
n8n-nodes-langchain.informationExtractor
n8n-nodes-langchain.textClassifier
n8n-nodes-langchain.sentimentAnalysis
n8n-nodes-langchain.code
n8n-nodes-langchain.vectorStoreInMemory
n8n-nodes-langchain.vectorStorePinecone
n8n-nodes-langchain.vectorStoreSupabase
n8n-nodes-langchain.vectorStoreQdrant
n8n-nodes-langchain.vectorStorePgVector
n8n-nodes-langchain.vectorStoreMilvus
n8n-nodes-langchain.vectorStoreWeaviate
n8n-nodes-langchain.vectorStoreMongoDBAtlas
n8n-nodes-langchain.vectorStoreRedis
n8n-nodes-langchain.vectorStoreZep
n8n-nodes-langchain.vectorStoreAzureAISearch
```

### All AI Sub-Node Types:
```
# Chat Models
n8n-nodes-langchain.lmChatOpenAi
n8n-nodes-langchain.lmChatAnthropic
n8n-nodes-langchain.lmChatGoogleGemini
n8n-nodes-langchain.lmChatAzureOpenAi
n8n-nodes-langchain.lmChatOllama
n8n-nodes-langchain.lmChatGroq
n8n-nodes-langchain.lmChatMistralCloud
n8n-nodes-langchain.lmChatDeepSeek
n8n-nodes-langchain.lmChatCohere
n8n-nodes-langchain.lmChatAwsBedrock
n8n-nodes-langchain.lmChatGoogleVertex
n8n-nodes-langchain.lmChatOpenRouter
n8n-nodes-langchain.lmChatXaiGrok
n8n-nodes-langchain.lmChatVercel

# Basic LLMs
n8n-nodes-langchain.lmCohere
n8n-nodes-langchain.lmOllama
n8n-nodes-langchain.lmOpenHuggingFaceInference

# Memory
n8n-nodes-langchain.memoryBufferWindow
n8n-nodes-langchain.memoryRedisChat
n8n-nodes-langchain.memoryPostgresChat
n8n-nodes-langchain.memoryMongoChat
n8n-nodes-langchain.memoryXata
n8n-nodes-langchain.memoryZep
n8n-nodes-langchain.memoryMotorhead
n8n-nodes-langchain.memoryManager

# Embeddings
n8n-nodes-langchain.embeddingsOpenAi
n8n-nodes-langchain.embeddingsAzureOpenAi
n8n-nodes-langchain.embeddingsGoogleGemini
n8n-nodes-langchain.embeddingsGoogleVertex
n8n-nodes-langchain.embeddingsGooglePalm
n8n-nodes-langchain.embeddingsCohere
n8n-nodes-langchain.embeddingsOllama
n8n-nodes-langchain.embeddingsHuggingFaceInference
n8n-nodes-langchain.embeddingsAwsBedrock
n8n-nodes-langchain.embeddingsMistralCloud

# Tools
n8n-nodes-langchain.toolCalculator
n8n-nodes-langchain.toolCode
n8n-nodes-langchain.toolHttpRequest
n8n-nodes-langchain.toolWorkflow
n8n-nodes-langchain.toolWikipedia
n8n-nodes-langchain.toolSerpApi
n8n-nodes-langchain.toolWolframAlpha
n8n-nodes-langchain.toolVectorStore
n8n-nodes-langchain.toolMcp
n8n-nodes-langchain.toolSearxng
n8n-nodes-langchain.toolThink
n8n-nodes-langchain.toolAiAgent

# Document Loaders
n8n-nodes-langchain.documentDefaultDataLoader
n8n-nodes-langchain.documentGitHubLoader

# Text Splitters
n8n-nodes-langchain.textSplitterCharacterTextSplitter
n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter
n8n-nodes-langchain.textSplitterTokenSplitter

# Retrievers
n8n-nodes-langchain.retrieverVectorStore
n8n-nodes-langchain.retrieverMultiQuery
n8n-nodes-langchain.retrieverContextualCompression
n8n-nodes-langchain.retrieverWorkflow

# Output Parsers
n8n-nodes-langchain.outputParserStructured
n8n-nodes-langchain.outputParserItemList
n8n-nodes-langchain.outputParserAutoFixing

# Other
n8n-nodes-langchain.rerankerCohere
n8n-nodes-langchain.modelSelector
```

---

## 8. Credential References

Credentials are referenced by ID, not stored in workflows:

```json
{
  "credentials": {
    "openAiApi": {
      "id": "credential-uuid",
      "name": "OpenAI Account"
    }
  }
}
```

---

## 9. Key Parsing Considerations

1. **Sub-node Connections**: AI sub-nodes connect to root nodes through special connection types (`ai_tool`, `ai_memory`, etc.), not `main`

2. **Tool Arrays**: Multiple tools connect to the same `ai_tool` input as separate array entries

3. **Version Compatibility**: `typeVersion` indicates node implementation version - newer versions may have different parameter schemas

4. **Expression Syntax**: Parameters may contain expressions like `={{ $json.field }}` that reference data from previous nodes

5. **Pin Data**: `pinData` contains test data that should be ignored in production parsing

6. **Disabled Nodes**: Check `disabled: true` to skip nodes that shouldn't execute
