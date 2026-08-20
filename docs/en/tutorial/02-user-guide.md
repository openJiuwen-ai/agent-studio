# Agent Development Platform User Guide

---

## Table of Contents

- [1. Getting Started](#1-getting-started)
    - [1.1 Build Your First Agent](#11-build-your-first-agent)
    - [1.2 Build a Knowledge Base Q&A Workflow](#12-build-a-knowledge-base-qa-workflow)
    - [1.3 Build an Agent Using Templates](#13-build-an-agent-using-templates)
- [2. OpenJiuwen Selection Guide](#2-openjiuwen-selection-guide)
- [3. OpenJiuwen Usage Workflow](#3-openjiuwen-usage-workflow)
- [4. Developing Single Agent Applications](#4-developing-single-agent-applications)
    - [4.1 Single Agent Application Overview](#41-single-agent-application-overview)
    - [4.2 Example: Building a Medical Consultation Assistant Agent Application](#42-example-building-a-medical-consultation-assistant-agent-application)
    - [4.3 Create and Configure a Single Agent Application](#43-create-and-configure-a-single-agent-application)
        - [4.3.1 Create a Single Agent Application](#431-create-a-single-agent-application)
        - [4.3.2 Select and Configure a Model](#432-select-and-configure-a-model)
        - [4.3.3 Configure Prompts](#433-configure-prompts)
    - [4.4 Add Skills to the Application](#44-add-skills-to-the-application)
        - [4.4.1 Add MCP Services](#441-add-mcp-services)
        - [4.4.2 Add Plugins](#442-add-plugins)
        - [4.4.3 Add Workflows](#443-add-workflows)
    - [4.5 Add a Knowledge Base to the Application](#45-add-a-knowledge-base-to-the-application)
    - [4.6 Add Memory to the Application](#46-add-memory-to-the-application)
    - [4.7 Enhance Application Conversation Experience](#47-enhance-application-conversation-experience)
    - [4.8 Debug the Application](#48-debug-the-application)
    - [4.9 Configure Triggers](#49-configure-triggers)
    - [4.10 Publish the Application](#410-publish-the-application)
        - [4.10.1 Publish the Application as an API Service](#4101-publish-the-application-as-an-api-service)
        - [4.10.2 Publish the Application as a Web Application](#4102-publish-the-application-as-a-web-application)
    - [4.11 Call the Single Agent Application via API](#411-call-the-single-agent-application-via-api)
    - [4.12 Manage Applications](#412-manage-applications)
- [5. Developing Workflow Applications](#5-developing-workflow-applications)
    - [5.1 Workflow Overview](#51-workflow-overview)
    - [5.2 Conversational Workflows and Task Workflows](#52-conversational-workflows-and-task-workflows)
    - [5.3 Workflow Usage Limits](#53-workflow-usage-limits)
    - [5.4 Build a Workflow](#54-build-a-workflow)
        - [5.4.1 Workflow Orchestration Logic](#541-workflow-orchestration-logic)
        - [5.4.2 Create a Workflow](#542-create-a-workflow)
        - [5.4.3 Trial Run a Workflow](#543-trial-run-a-workflow)
        - [5.4.4 Configure Triggers](#544-configure-triggers)
        - [5.4.5 Publish a Workflow](#545-publish-a-workflow)
    - [5.5 Using Workflows](#55-using-workflows)
        - [5.5.1 Call a Workflow via API](#551-call-a-workflow-via-api)
        - [5.5.2 Use Workflows in Single Agent Applications](#552-use-workflows-in-single-agent-applications)
        - [5.5.3 Use Workflows in Multi-Agent Applications](#553-use-workflows-in-multi-agent-applications)
    - [5.6 Manage Workflows](#56-manage-workflows)
    - [5.7 Basic Nodes](#57-basic-nodes)
        - [5.7.1 Start Node](#571-start-node)
        - [5.7.2 End Node](#572-end-node)
    - [5.8 Common Nodes](#58-common-nodes)
        - [5.8.1 LLM](#581-llm)
        - [5.8.2 Workflow](#582-workflow)
        - [5.8.3 Agent](#583-agent)
    - [5.9 Logic Nodes](#59-logic-nodes)
        - [5.9.1 Condition](#591-condition)
        - [5.9.2 Code](#592-code)
        - [5.9.3 Loop](#593-loop)
        - [5.9.4 Intent Recognition](#594-intent-recognition)
        - [5.9.5 Advanced Intent Recognition](#595-advanced-intent-recognition)
    - [5.10 Tool Nodes](#510-tool-nodes)
        - [5.10.1 Plugin](#5101-plugin)
        - [5.10.2 MCP Service](#5102-mcp-service)
        - [5.10.3 HTTP Request](#5103-http-request)
    - [5.11 Message Management Nodes](#511-message-management-nodes)
        - [5.11.1 Message](#5111-message)
        - [5.11.2 Input](#5112-input)
        - [5.11.3 Questioner](#5113-questioner)
        - [5.11.4 Q&A](#5114-qa)
        - [5.11.5 Object Extraction](#5115-object-extraction)
        - [5.11.6 Exception](#5116-exception)
    - [5.12 Data & Knowledge Nodes](#512-data-knowledge-nodes)
        - [5.12.1 Variable Assignment](#5121-variable-assignment)
        - [5.12.2 Variable Aggregation](#5122-variable-aggregation)
        - [5.12.3 Knowledge Retrieval](#5123-knowledge-retrieval)
    - [5.13 Node Configuration Management](#513-node-configuration-management)
        - [5.13.1 Manage Intent Packages](#5131-manage-intent-packages)
        - [5.13.2 Message Templates](#5132-message-templates)
        - [5.13.3 Object Management](#5133-object-management)
- [6. Developing Multi-Agent Applications](#6-developing-multi-agent-applications)
    - [6.1 Multi-Agent Application Overview](#61-multi-agent-application-overview)
    - [6.2 Create a Multi-Agent Application](#62-create-a-multi-agent-application)
    - [6.3 Debug a Multi-Agent Application](#63-debug-a-multi-agent-application)
    - [6.4 Publish a Multi-Agent Application as an API](#64-publish-a-multi-agent-application-as-an-api)
    - [6.5 Call a Multi-Agent Application via API](#65-call-a-multi-agent-application-via-api)
    - [6.6 Import and Export Multi-Agent Applications](#66-import-and-export-multi-agent-applications)
- [7. Component Library](#7-component-library)
    - [7.1 Plugins](#71-plugins)
        - [7.1.1 Plugin Overview](#711-plugin-overview)
        - [7.1.2 Example: Create a Web Search Plugin](#712-example-create-a-web-search-plugin)
        - [7.1.3 Create a Plugin](#713-create-a-plugin)
            - [7.1.3.1 Create a Plugin Based on API](#7131-create-a-plugin-based-on-api)
            - [7.1.3.2 Import an API Plugin from a JSON File](#7132-import-an-api-plugin-from-a-json-file)
        - [7.1.4 Debug and Publish Plugins](#714-debug-and-publish-plugins)
        - [7.1.5 Use Plugins](#715-use-plugins)
            - [7.1.5.1 Use Plugins in Single Agents](#7151-use-plugins-in-single-agents)
            - [7.1.5.2 Use Plugins in Workflows](#7152-use-plugins-in-workflows)
        - [7.1.6 Manage Plugins](#716-manage-plugins)
    - [7.2 MCP](#72-mcp)
        - [7.2.1 MCP Overview](#721-mcp-overview)
        - [7.2.2 Example: Create a Search MCP Using a Template](#722-example-create-a-search-mcp-using-a-template)
        - [7.2.3 Example: Quickly Connect to ModelScope MCP Toolkit](#723-example-quickly-connect-to-modelscope-mcp-toolkit)
        - [7.2.4 Create an MCP](#724-create-an-mcp)
            - [7.2.4.1 Custom MCP Connection](#7241-custom-mcp-connection)
            - [7.2.4.2 Create an MCP from a Template](#7242-create-an-mcp-from-a-template)
        - [7.2.5 Debug MCP](#725-debug-mcp)
        - [7.2.6 Use MCP](#726-use-mcp)
            - [7.2.6.1 Use MCP in Single Agents](#7261-use-mcp-in-single-agents)
            - [7.2.6.2 Use MCP in Workflows](#7262-use-mcp-in-workflows)
        - [7.2.7 Manage MCP](#727-manage-mcp)
        - [7.2.8 Troubleshooting](#728-troubleshooting)
    - [7.3 Knowledge Base](#73-knowledge-base)
        - [7.3.1 Knowledge Base Overview](#731-knowledge-base-overview)
        - [7.3.2 Knowledge Base Types](#732-knowledge-base-types)
        - [7.3.3 Knowledge Base Usage Limits](#733-knowledge-base-usage-limits)
        - [7.3.4 Create a Platform Default Knowledge Base](#734-create-a-platform-default-knowledge-base)
            - [7.3.4.1 Create a Knowledge Base](#7341-create-a-knowledge-base)
            - [7.3.4.2 Upload Documents](#7342-upload-documents)
            - [7.3.4.3 Test Knowledge Base Hit Rate](#7343-test-knowledge-base-hit-rate)
            - [7.3.4.4 Knowledge Base Segmentation](#7344-knowledge-base-segmentation)
        - [7.3.5 Connect Third-Party Knowledge Bases](#735-connect-third-party-knowledge-bases)
            - [7.3.5.1 Third-Party Knowledge Base Classification](#7351-third-party-knowledge-base-classification)
            - [7.3.5.2 Connect a General Knowledge Base](#7352-connect-a-general-knowledge-base)
            - [7.3.5.3 Connect a LakeSearch Knowledge Base](#7353-connect-a-lakesearch-knowledge-base)
            - [7.3.5.4 Connect a RAGFlow Knowledge Base](#7354-connect-a-ragflow-knowledge-base)
            - [7.3.5.5 Test Knowledge Base Hit Rate](#7355-test-knowledge-base-hit-rate)
            - [7.3.5.6 Third-Party General Knowledge Base Integration Specification](#7356-third-party-general-knowledge-base-integration-specification)
        - [7.3.6 Use Knowledge Bases](#736-use-knowledge-bases)
            - [7.3.6.1 Use Knowledge Bases in Single Agents](#7361-use-knowledge-bases-in-single-agents)
            - [7.3.6.2 Use Knowledge Bases in Workflows](#7362-use-knowledge-bases-in-workflows)
        - [7.3.7 Manage Knowledge Bases](#737-manage-knowledge-bases)
    - [7.4 Prompts](#74-prompts)
        - [7.4.1 Prompt Overview](#741-prompt-overview)
        - [7.4.2 Prompt Writing Guidelines](#742-prompt-writing-guidelines)
        - [7.4.3 Create Prompts](#743-create-prompts)
        - [7.4.4 Optimize Prompts](#744-optimize-prompts)
        - [7.4.5 Manage Prompts](#745-manage-prompts)
        - [7.4.6 Set Prompts for Agents and Workflows](#746-set-prompts-for-agents-and-workflows)
- [8. Models](#8-models)
    - [8.1 Model Overview](#81-model-overview)
    - [8.2 Connect Custom Models](#82-connect-custom-models)
        - [8.2.1 Custom Model Integration Process](#821-custom-model-integration-process)
        - [8.2.2 Connect Model Providers](#822-connect-model-providers)
        - [8.2.3 Connect Model Services](#823-connect-model-services)
        - [8.2.4 Model API Specification](#824-model-api-specification)
    - [8.3 Test Models](#83-test-models)
    - [8.4 Configure Model Routing Strategies](#84-configure-model-routing-strategies)
    - [8.5 Manage My Credentials](#85-manage-my-credentials)
- [9. Workspaces and Permissions](#9-workspaces-and-permissions)
    - [9.1 Workspace and Permission Overview](#91-workspace-and-permission-overview)
    - [9.2 Create and Manage Team Spaces](#92-create-and-manage-team-spaces)
    - [9.3 Manage Team Space Members](#93-manage-team-space-members)

---

# 1 Getting Started

## 1.1 Build Your First Agent

This chapter will guide you through manually building an "Encyclopedia & News Assistant." Through a full-journey hands-on tutorial, you'll explore how to develop a single agent from scratch on OpenJiuwen and understand its development logic, experiencing OpenJiuwen's agile building capabilities firsthand.

In today's increasingly fragmented information landscape, users often have a compound need to quickly query real-time news and professional encyclopedia knowledge. This "Encyclopedia & News Assistant" integrates multiple skills including Daily News (global updates) and the Compendium of Materia Medica encyclopedia, enabling cross-dimensional information integration from global hot topic tracking to traditional Chinese medicine classics retrieval. Through this practice, you will not only build a practical tool connecting real-time updates with classical wisdom, but also master a methodology for extending a single agent's service boundaries through skill combination.

## Workflow

Building an encyclopedia & news assistant manually requires only four steps to quickly create your own agent application.

| Step | Description |
|------|------|
| Step 1 Create a Single Agent | Follow the overview page guide to create and fill in the single agent's name and description, giving the "Encyclopedia & News Assistant" a clear role identity and functional positioning |
| Step 2 Configure the Single Agent | Expand the single agent's capability boundaries by adjusting prompts, configuring models, adding MCP services and plugins, injecting core capabilities such as logical reasoning, real-time news retrieval, and professional encyclopedia search |
| Step 3 Debug the Single Agent | Conduct real-time conversation validation in the "Preview & Debug" window to ensure the "Encyclopedia & News Assistant" can accurately invoke various skills and generate expected responses |

---

## Step 1 Create a Single Agent

1. Log in to the OpenJiuwen Agent Development Platform
2. On the overview page, click "Create Now" in the "Quick Create Agent" card
3. Fill in the agent's "Name" and "Description" to give the agent a basic identity. After filling, click "OK" to jump to the "Single Agent Configuration" interface

| Parameter | Example Configuration |
|------|----------|
| Name | Encyclopedia & News Assistant |
| Description | A comprehensive assistant integrating real-time updates and encyclopedia search |

---

## Step 2 Configure the Single Agent

Expand the single agent's capabilities by adjusting prompts, configuring models, skills, conversation experience, etc. During configuration, you can continuously adjust the agent's performance in the preview & debug interface.

### Step 1 Configure Basic Information

After entering the "Single Agent Configuration" interface, the system will automatically generate an avatar and prompt for the single agent based on the "Name" and "Description" you have already filled in.

> **Prompt** is the "instruction manual" that drives an agent to execute tasks. By setting personas, task boundaries, and output formats, structured prompts ensure that the agent generates high-quality content that meets expectations and has a specific style.

| Configuration Item | More Operation Details |
|--------|--------------|
| Avatar | To change the avatar, click the avatar to manually upload a local image, or click the button to generate one with AI |
| Prompt | The platform provides the following functional support: smart prompt optimization, reference templates, role instruction templates, save to template |

### Step 2 Configure the Model

The model is the agent's "brain," providing reasoning capabilities for the agent.

Click the dropdown box for the "Model" parameter. In this example, we use the "DeepSeek-V3" model. You can also configure other large models as needed. Click the icon to adjust model parameters as desired.

### Step 3 Configure "News & Encyclopedia" Skills

Skills are the agent's "capability toolbox." This case requires adding the "Daily News" MCP service and the "Compendium of Materia Medica" plugin to introduce real-time news retrieval and professional encyclopedia search capabilities to the agent.

#### Add the "Daily News" MCP Service

1. Click the icon to the right of the "Skills > MCP Services" configuration, and the "Add MCP Service" window will pop up on the right
2. Click "Create MCP > Create from Platform Template" to quickly select an official preset MCP service
3. In the "Select Service" step, search for keywords, find and click the "Daily News" MCP service, then click "Next"
4. Enter the "Service Configuration" step to view the detailed information of this MCP service. Click "Install" and wait for the MCP service to complete installation
- If the FunctionGraph service authorization is not configured, please first click "Click Here" in the prompt box under "Select Installation Method" to complete authorization
5. When the prompt shows "MCP created successfully" and the MCP service card status shows "Deployed," you can check this MCP service and click "OK"
6. Complete the addition of the "Daily News" MCP service

#### Add the "Compendium of Materia Medica" Plugin

1. Click the icon to the right of the "Skills > Plugins" configuration, and the "Add Plugin Tool" window will pop up on the right
2. Switch to the "Plugin Square" tab to quickly select official preset plugin tools
3. Find the "Compendium of Materia Medica" plugin in the list, click the card to expand the plugin details, and click "Add"
4. After confirming everything is correct, click "OK" in the lower right corner to complete the plugin addition

> **Note**: Some MCP services or plugins involve "authentication" configuration. Since they call third-party platform services, you need to first register on the corresponding official platform and obtain a dedicated API Key or Token, and fill it back into the platform configuration to obtain the service usage permission.

### Step 4 Optimize the Prompt

After adding MCP services and plugins, it is recommended to modify the prompt and add the following content in the "Task Description" to ensure the agent clearly understands when to invoke each skill:

> Based on the user's inquiry needs, invoke the "Daily News" MCP service to obtain the latest global updates, or search the "Compendium of Materia Medica" plugin to obtain professional Chinese medicine encyclopedia knowledge, providing users with real-time news and encyclopedia search results.

### Step 5 Enhance Conversation Experience

Configuring "Opening Message" and "Suggested Questions" for the agent can help users quickly understand the agent's functions and purposes, and clarify how to effectively interact with the agent application.

Click the icon to the right of "Opening Message" and "Suggested Questions" to intelligently generate an opening message and suggested questions that match the single agent. You can view the effect in the "Preview & Debug" window on the right.

| Configuration Item | Description |
|--------|------|
| Follow-up Questions | After the agent answers the user's question, it will automatically generate 3 follow-up questions based on the configured follow-up rules and context, effectively guiding users to engage in multi-turn conversations |
| Voice | The voice used by the agent during voice interaction or text-to-speech. You can select a voice that matches the agent's persona from the voice library based on the agent's usage scenario |
| Display Citations and Attribution | When the single agent is configured and uses tools such as web search or knowledge base, enabling this feature will include citation sources in the model's responses, helping verify the accuracy and timeliness of information |

### Step 6 Configure Content Security

The platform has "Content Review Configuration" enabled by default. You can click the icon to customize the filtering, replacement, and fallback replies for sensitive words, protecting users from harmful information during agent usage.

> The "Safety Guardrail" configuration can identify and block Prompt attacks aimed at manipulating or abusing the system, and can also filter inputs and outputs containing sensitive information. However, content review configuration and safety guardrails cannot be enabled simultaneously 鈥?choose one to enable.

---

## Step 3 Debug the Single Agent

In the "Preview & Debug" module, interact with the agent in real-time to intuitively observe its execution process and verify whether the response effect meets expectations. Continuously optimize the configuration based on feedback to ensure the "Encyclopedia & News Assistant" meets usage expectations.

1. In the "Preview & Debug" module on the right side of the "Single Agent Configuration" interface, directly enter questions for Q&A debugging. File upload and voice input are supported

2. Debug function description:

| Function | Description |
|------|------|
| Delete | Delete all conversation content on the current interface, returning to the opening message screen. Context memory will not be cleared |
| Memory | View variable information configured during debugging, with support for variable reset |
| Debug | Select a conversation to view its execution results and invocation details |
| Expand | Expand the preview & debug panel to focus on the agent debugging conversation process |

3. Enter the following question in the input box to check the agent's response:

> Please provide the latest technology news updates, and based on the current solar term, recommend a wellness suggestion from the Compendium of Materia Medica.

4. The agent can now obtain and summarize the day's global technology updates through the "Daily News" MCP service, while successfully invoking the "Compendium of Materia Medica" plugin to retrieve wellness prescriptions matching the current solar term.

---

## Step 4 Share the Single Agent

1. After completing agent debugging, click the "Submit Version" button in the upper right corner of the "Single Agent Configuration" interface
2. The system will default to using the submission time as the version name. Modify the version name and description as needed, then click "OK"
3. A popup will prompt "Version submitted successfully." Click "Share" to enter the "Channel Management" interface

### Invocation Methods

Agent applications with submitted versions support sharing and invocation via API. Click "View API" to open the API details page, which provides detailed API documentation and example code for your reference.

### Sharing Channels

The application can be shared to multiple channels. The sharing scope is limited to "current tenant available." Users not under the same account cannot open this link.

---

## More Configuration Details

| Configuration Item | Description |
|--------|------|
| Workflow | A workflow is the logical orchestration system for agent task execution, defining the sequence of tasks, branch conditions, and automated processing flows, enabling the agent to execute fixed business processes. Before adding, ensure the workflow has been orchestrated and published |
| Knowledge Base | A knowledge base is the agent's "external bookshelf," enabling the agent to retrieve and reference knowledge base content when processing tasks to answer questions |
| Memory Variables | User variables serve as the agent's "notebook." After adding variables, they can be referenced in the "Prompt" using the {{memory.variable_name}} format |
| Input Parameters | Input parameters are used to pass external information to the agent during API calls, typically used for fixed component parameters or injecting deterministic business context |


## 1.2 Build a Knowledge Base Q&A Workflow

### Case Overview

In real-world business, there is often a need to create an AI assistant with a knowledge base to answer domain-specific questions (such as company regulations, industry reports). By introducing knowledge base functionality, you can solve the problem of knowledge gaps and factual errors that large models exhibit when dealing with vertical domains or private data.

In this chapter's case, we will build a "Tourist Attraction Introduction Knowledge Base," then orchestrate a knowledge base Q&A workflow, and use a large model for content summarization.

### Workflow

The process for building a knowledge base Q&A workflow is as follows, requiring only five steps to complete the knowledge base Q&A assistant.

| Step | Description |
|------|------|
| Step 1 Create a Knowledge Base | Create a knowledge base and upload documents, perform hit testing to ensure the system can accurately recall key information from the documents |
| Step 2 Create a Workflow Application | Create a new "Workflow" type application and enter the workflow orchestration canvas to prepare for workflow orchestration |
| Step 3 Orchestrate Workflow Nodes | Build the core logic of the knowledge base Q&A workflow. Connect to the knowledge base through the "Knowledge Retrieval" node, and pass the retrieval results to the "LLM" node for summarization and answering. The workflow contains the following four nodes: Start --> Knowledge Retrieval --> LLM --> End |
| Step 4 Debug the Workflow | Verify whether the knowledge Q&A workflow results meet expectations |

---

### Step 1 Create a Knowledge Base

This chapter will guide you through creating a knowledge base and uploading a demo document (Selected National Tourist Cities.docx), verifying document recall capability through hit testing, providing support for the subsequent workflow.

1. Log in to the OpenJiuwen Agent Development Platform
2. In the left navigation bar, select "Development Center > Component Library." In the "Knowledge Base" tab, click "Create Knowledge Base" in the upper right corner, select "Default" knowledge base, and click "OK"
3. In the "New Knowledge Base" popup, configure the knowledge base parameters according to Table 1-5. After filling, click "OK" to create the knowledge base

#### Parameter Description

| Parameter | Example Configuration | Description |
|------|----------|------|
| Knowledge Base Name | Attraction Introduction Knowledge Base | Used to identify the knowledge base |
| Description | Attraction Introduction Knowledge Base, providing attraction introductions nationwide | A brief description of the knowledge base content and purpose |
| Vector Model | agentBuilder_embedding | A vector model converts unstructured data such as text and images into numerical vectors. For example, during text processing, it slices text documents and converts them into vector representations; during knowledge retrieval, it recalls slices based on user input |
| Rerank Model | agentBuilder_rerank | A rerank model performs fine-grained sorting on retrieval results. Based on user input, it sorts the slices recalled by the vector model by relevance from high to low, presenting the most relevant information to the user |
| Parsing Configuration | Not configured | Used to set whether to call OCR service during document parsing, whether to include headers/footers/table of contents, and how to handle images |
| Splitting Settings | Auto Segmentation | Splits documents into desired segments through auto segmentation, length segmentation, or hierarchical segmentation |

4. The created knowledge base will be automatically displayed in the knowledge base list. Click the knowledge base name to enter the knowledge base details page
5. Download the demo document (Selected National Tourist Cities.docx) and upload it to the knowledge base
6. Wait for the document status to show "Success," then click "Hit Test" in the upper right corner
7. Enter questions related to the demo document content, such as "What attractions are there in Shanghai." Check the knowledge base recall results and record the similarity scores

> **Note**: This score will be used as a reference value for the "Search Recall" node parameter in Step 3 Orchestrate Workflow Nodes (in the example using "What attractions are there in Shanghai" as the test question, the similarity score was 0.30)

---

### Step 2 Create a Workflow Application

An application is the entity that carries the business. Before orchestrating workflow nodes, you need to first create a workflow application and enter the workflow editing interface.

1. Return to the "Development Center > Agent Management" page, enter the "Workflow" tab, and click "Create Workflow" in the upper right corner
2. Select "Conversational Workflow" and set the display name, name, and description
- Display Name: Knowledge Base Q&A Assistant
- Name: KnowledgeBaseAssistant
- Description: Knowledge Base Q&A Assistant
3. Click "Create Now" in the lower right corner

After creation, you will enter the workflow editing page. Please refer to Step 3 Orchestrate Workflow Nodes for subsequent operations.

---

### Step 3 Orchestrate Workflow Nodes

This is the core part of building a knowledge base Q&A workflow. Through visual drag-and-drop, connect "Start -> Knowledge Retrieval -> LLM -> End" four key nodes in sequence, and configure parameters to link the static knowledge base with the large model's reasoning capabilities, implementing the "retrieve first, then generate" business logic.

1. The workflow shows "Start -> LLM -> End" nodes by default. Hover between the Start node and the LLM node, click to add a "Knowledge Retrieval" node
2. Click the node to expand the node's parameter configuration page. Refer to Table 1-6 to set each node's parameters in sequence

> **Note**: After configuring each node, you need to click "OK" in the lower right corner for the node configuration to take effect

#### Workflow Node Parameter Table

| Node Type | Parameter Modification Description |
|----------|--------------|
| Start Node | Use the default "query" parameter to extract the user's question. No changes |
| Knowledge Retrieval Node | Set the following parameters for the knowledge retrieval node:<br>- **Input Parameters**: Reference the "query" parameter from the Start node, meaning the user's question is passed to the knowledge base for search<br>- **Knowledge Base**: Add a knowledge base, select the previously created "Attraction Introduction Knowledge Base"<br>- **Knowledge Base Settings**: Click the button to the right of the knowledge base to configure knowledge base parameters. Set the retrieval strategy to "Hybrid Retrieval"; set the relevance threshold to 0.2 to prevent empty recalls when the question has low similarity with the knowledge base content |
| LLM Node | Set the following parameters for the LLM node:<br>- **Model Configuration**: Select a model, such as "DeepSeek-V3"<br>- **Input Parameters**: The LLM needs to read the search recall content for summarization. Therefore, reference the output parameter of the "Knowledge Retrieval" node. For convenience in distinguishing parameter flow, change the LLM's default input parameter name to match the knowledge retrieval output parameter name output_list<br>- **Add Input Parameter**: Click to the right of the input parameter to add a query parameter, referencing the query parameter value from the Start node. When the model summarizes later, it needs to pass both the user's original question and the knowledge retrieval recall to the LLM for summarization<br>- **System Prompt**: Enter content<br>- **User Prompt**: Enter content |
| End Node | The input parameter references the LLM node's output content, other parameters use default configuration |

#### LLM Node System Prompt Example

```
# Role Definition
You are a professional content analysis and summarization specialist, skilled at extracting key information from various document fragments, and can also provide professional answers based on the question itself.

# Core Task
Understand the user's question, prioritize using relevant document fragments returned from knowledge base retrieval to extract information and generate answers; if retrieval has no results or information is incomplete, directly answer based on the question itself.

# Processing Principles
1. Prioritize knowledge base retrieval content, filter core relevant information, discard irrelevant content, and do not fabricate information not mentioned in the original text;
2. Integrate multi-fragment information, merge duplicate content, supplement related information, and ensure factual accuracy;
3. When retrieval content is insufficient or there are no retrieval results, directly provide professional answers around the core of the question.

# Output Guidelines
- Language should be concise and professional, avoid colloquialisms
- Do not reveal knowledge base related technical details
```

#### LLM Node User Prompt Example

```
## User's Original Question
{{query}}

## Document Fragments Returned by Knowledge Base Retrieval
{{output_list}}

Please answer the user's question based on the above document fragments.
```

---

### Step 4 Debug the Workflow

After workflow orchestration is complete, you must verify the logic's correctness through actual execution. This chapter will guide you to input specific test questions, check whether the workflow can accurately retrieve document fragments, and verify whether the large model can generate expected answers based on the retrieval results.

1. Click "Trial Run" in the upper right corner of the workflow page. The system will automatically detect whether the workflow parameters are set correctly. If a node reports an error, please refer to Step 3 Orchestrate Workflow Nodes to check node parameters
2. Enter test content, such as "What attractions are there in China," and check whether the workflow produces an answer

> **Note**: During testing, if you find that the answer is truncated, please check whether the "Max Reply Length" of the "LLM" node is set too small, causing incomplete model responses. After updating node configuration, you need to click "OK" in the lower right corner to make the configuration take effect

After completing workflow debugging, click the "Submit Version" button in the upper right corner.

---

### Share the Workflow

After completing workflow debugging, click "Submit Version" in the upper right corner of the "Workflow Configuration" interface to share the workflow with others via API and other methods.


## 1.3 Build an Agent Using Templates

### Case Overview

The OpenJiuwen Asset Square provides rich application templates, covering mature assets in various forms including single agents and workflows, designed to help users quickly reuse popular application solutions.

This chapter will guide you to use the "City Tourism Recommendation" single agent application template from the OpenJiuwen Asset Square, taking you through the full process from one-click copy to key configuration in a zero-code environment. Addressing the challenges of scattered travel planning information and cumbersome plan preparation, this agent can quickly generate professional guides based on user preferences, including route suggestions, opening hours, and budget details, and export them directly as .docx files.

Through this single agent building practice, you will intuitively experience the convenience of the OpenJiuwen Asset Square and master how to efficiently transform preset assets into personalized services that meet your own needs.

### Workflow

Using the OpenJiuwen Asset Square application template, you can quickly build your own agent application in just three steps.

| Step | Description |
|------|------|
| Step 1 Obtain Asset Square Template | Visit the Asset Square, select an application template, and copy its complete preset configuration to your workspace with one click |
| Step 2 Configure Single Agent Using Application Template | Customize and fine-tune based on the template's preset configuration, and complete effect verification in the debug preview window |

---

### Step 1 Obtain Asset Square Template

1. Log in to the OpenJiuwen Agent Development Platform
2. Click "Asset Square" in the left navigation bar to enter the Asset Square interface

> The Asset Square provides a series of rich templates and resource tools. Here you can use various application templates and resource tools preset by the platform, as well as assets shared by your team space

3. In the "Application Templates" interface, find the "City Tourism Recommendation" application template

| Action | Description |
|------|------|
| Try Now | Enter the conversation interface with the City Tourism Recommendation single agent application to experience interacting with the agent |
| Copy to Create | Copy the application directly to the current space and enter the "Single Agent Configuration" interface |

4. Click "Try Now" to enter the conversation interface with the "City Tourism Recommendation" agent. In the conversation interface, you can enter questions to experience the agent's functionality

---

### Step 2 Configure Single Agent Using Application Template

Click the "Copy to Current Space" button in the upper right corner. In the successful copy popup, click "OK" to jump directly to the "Single Agent Configuration" interface and start your custom configuration.

The application template has preset the core capabilities of this single agent, supporting out-of-the-box use or on-demand adjustment.

#### Single Agent Configuration Interface Section Introduction

| Interface Section | Introduction |
|----------|------|
| Configure the single agent's basic information and prompt, defining "who" the agent is | Set the application name and description, define the single agent's role setting, task objectives, and behavioral norms |
| Expand various capabilities and functional modules for the single agent, making it go from "can talk" to "truly helpful" | Model configuration, skills, knowledge base, memory, conversation experience, security |
| Test the single agent's effectiveness in real-time, verifying "whether it works well" | In the "Preview & Debug" area, you can have conversational interactions and instantly verify the effects after configuration changes |

#### Identity and Instructions

This template has preset the agent's "Single Agent Information" and "Prompt," giving the "City Tourism Recommendation" agent a clear identity positioning and work instructions.

| Configuration Item | Description |
|--------|------|
| Single Agent Information | The single agent's avatar, name, and description, giving the agent a basic identity for external display |
| Prompt | The prompt is the agent's "instruction manual." Modifying the prompt directly affects the agent's response results. The template has preset a set of instructions defining the agent's persona, tasks, execution steps, and other key instructions, letting the agent know how to work. The prompt complements the "Capability Components" below |

#### Capability Components

This template has preset a suitable model and document generation plugin, giving the "City Tourism Recommendation" agent the ability to perform Q&A reasoning and generate city tourism documents.

| Configuration Item | Configuration Description |
|--------|----------|
| Model Configuration | The model is the agent's "brain," determining the agent's understanding capability, reasoning speed, and response quality. You can quickly judge whether a model meets your needs based on the capability tags below each model. This template has already selected a suitable large model for you |
| Skills | Skills are the agent's "capability toolbox," enabling the agent to call external services and execute specific tasks.<br>- **Plugins**: The template has added a document generation plugin by default, enabling it to directly write and generate .docx format files<br>- **MCP Services**: MCP services are universal connectors based on the Model Context Protocol standard<br>- **Workflows**: Workflows are the logical orchestration system for agent task execution |
| Knowledge Base | The knowledge base is the agent's "external bookshelf," enabling the agent to precisely retrieve and reference knowledge base content when processing tasks |
| Memory | Variables in memory serve as the agent's "notebook," enabling the agent to flexibly adjust response logic based on external parameters or user preferences.<br>- **User Variables**: Used to store data that needs persistent storage and retrieval during user interaction with the agent<br>- **Input Parameters**: Used to pass external information to the agent during API calls |

#### Conversation Experience

The application template has preset conversation opening message, suggested questions, follow-up question generation rules, and voice configuration to enhance the interaction experience with the "City Tourism Recommendation" agent.

| Configuration Item | Configuration Description |
|--------|----------|
| Opening Message | The opening message will be displayed as the opening in the conversation interface. Click the icon to generate an opening message with AI |
| Suggested Questions | Suggested questions are displayed as quick bubbles above the dialog box, allowing users to ask questions without typing, guiding user inquiries |
| Follow-up Questions | After the agent answers the user's question, it will automatically generate 3 follow-up questions based on the configured follow-up rules and context |
| Voice | The voice used by the agent during voice interaction or text-to-speech |
| Display Citations and Attribution | When the single agent is configured and uses tools such as web search or knowledge base, enable the "Display Citations and Attribution" feature |

#### Security Configuration

The application template has content review configuration enabled by default, used to filter and review sensitive content during agent usage, ensuring the agent's safe use. Content review configuration and safety guardrails cannot be enabled simultaneously.

| Configuration Item | Configuration Description |
|--------|----------|
| Content Review Configuration | Filters input and output content by configuring sensitive word filtering, replacement, and fallback replies, protecting users from harmful information |
| Safety Guardrail | Enabling safety guardrails can identify and block Prompt attacks aimed at manipulating or abusing the system, and can also filter inputs and outputs containing sensitive information |

---

### Share the Single Agent

1. After completing agent debugging, click the "Submit Version" button in the upper right corner of the "Single Agent Configuration" interface
2. The system will default to using the submission time as the version name. Modify the version name and description as needed, then click "OK"
3. A popup will prompt "Version submitted successfully." Click "Share" to enter the "Channel Management" interface

#### Invocation Methods

Agent applications with submitted versions support sharing and invocation via API. Click "View API" to open the API details page, which provides detailed API documentation and example code for your reference.

#### Sharing Channels

The application can be shared to multiple channels. The sharing scope is limited to "current tenant available." Users not under the same account cannot open this link.


# 2 OpenJiuwen Selection Guide

To meet the diverse needs ranging from simple conversations to complex business automation, OpenJiuwen provides three core application building modes: single agent, workflow, and multi-agent.

Before building an AI application, you need to answer a core question: "Should my task be handled by one person, an assembly line, or a team?"

The platform provides three core development modes, whose relationships are shown in Table 2-1.

## Application Mode Overview

| Type | Analogy | Execution Method | Complexity |
|------|------|----------|--------|
| Single Agent | One versatile employee | One person completes all conversations | 鈽?|
| Workflow | One assembly line | Executes automatically according to predefined steps | 鈽呪槄鈽?|
| Multi-Agent | One collaborative team | Multiple experts each handle their responsibilities to collaboratively complete complex tasks | 鈽呪槄鈽呪槄鈽?|

### Single Agent

A single agent is the most basic AI application form. A single agent can independently complete all work. The single agent is prompt-driven, leveraging large models to autonomously understand intent and dynamically plan task steps, calling knowledge bases, plugins, MCP services, and other tools to complete tasks.

- **Applicable Scenarios**: Open-ended conversation applications, such as intelligent customer service, knowledge Q&A, task assistants, travel planning, and other scenarios requiring flexible decision-making
- **Typical Characteristics**: AI autonomous decision-making, with the large model dynamically decomposing tasks based on prompts, adapting to changing user needs

### Workflow

A workflow is a deterministic automation pipeline that decomposes tasks into multiple predefined step nodes. Through visual node orchestration, multi-step tasks are connected into stable, reproducible execution chains.

- **Applicable Scenarios**: Fixed-process automation, such as automated report generation, order processing, multi-step approval flows, data annotation, and other scenarios requiring precise control
- **Typical Characteristics**: Predefined processes precisely control each step, with deterministic logic, ensuring stability and predictability of task execution

### Multi-Agent

Multi-agent consists of multiple independent Agents collaborating through role division and task allocation to solve complex problems.

- **Applicable Scenarios**: Complex task collaboration, such as cross-department business process automation, multi-role decision support systems, comprehensive project management, etc.
- **Typical Characteristics**: Multi-agent collaboration, improving the efficiency and accuracy of complex task processing through role division and task allocation

## Application Mode Comparison

| Dimension | Single Agent | Workflow | Multi-Agent |
|----------|----------|--------|----------|
| Development Method | Graphical operation, page selection and text input configuration, zero code | Canvas component drag-and-drop + low-code development, orchestrate, configure multi-agent central control instructions, and reference sub-agents, define division of labor |
| Target User | Business personnel who cannot write code and use office tools relatively simply | Technical personnel who can develop workflows with low code, debug various specialized components and APIs without writing code | Senior business personnel integrating multiple business scenarios |
| Applicable Scenarios | Self-planning task scenarios, scenarios with fixed task execution processes, high accuracy requirements | Complex user intent recognition and division scenarios requiring multiple agents to collaborate |
| Development Characteristics | Quick and simple, low barrier, unstable accuracy | Planning and configuration have barriers, high execution success rate, long configuration time | Relatively simple, depends on pre-developed expert agents |
| Capability Constraints | Completely depends on the model's own capabilities, with many restrictions on plugin quantity, interface parameter quantity, execution step quantity, etc. | The orchestrated process is relatively rigid during execution, with low intelligence | Highly dependent on the intelligence level of the central control model, with many sub-agent associations involved. Additionally, there is currently no visual debugging capability, making effect optimization debugging difficult |

## Selection Decision Guide

### Quick Decision Tree

- **What are your task requirements?**
    - Task is relatively simple, single responsibility? 鈫?Choose [Single Agent]
    - Task has clear fixed steps/processes?
- Does the process require conditional judgment and branch routing?
- Need strict control over output format and intermediate steps?
- High requirements for result determinism and consistency? 鈫?Choose [Workflow]
    - Task involves multiple professional domains?
- Different questions need different knowledge bases/tools?
- A single prompt is already very long and complex, with declining effectiveness? 鈫?Choose [Multi-Agent]
    - Still not sure? 鈫?Start with [Single Agent], upgrade when encountering bottlenecks

### Detailed Selection Criteria

#### Choose Single Agent

| Scenario Characteristic | Example |
|----------|------|
| Single task objective, clear responsibility | Translation assistant, copy editing, code explanation |
| Conversational interaction, mainly free Q&A | Chatbot, general Q&A assistant |
| Need to flexibly handle various uncertain user inputs | Creative writing assistant, brainstorming assistant |
| Few tools/knowledge bases to call (鈮?) | Personal assistant with weather + calendar |
| Quick idea validation, minimum viable product stage | Initial prototype for any scenario |
| No strict requirements on output format | Unstructured natural language responses |

#### Choose Workflow

| Scenario Characteristic | Example |
|----------|------|
| Task has clear sequential steps | Extract information 鈫?classify 鈫?generate reply |
| Intermediate process requires strict control | Must review sensitive words first, only output after passing |
| Need conditional branches for different logic | VIP users go to manual, regular users go to auto-reply |
| Strict requirements on output format and structure | Must output structured data in fixed JSON format |
| Need to connect multiple systems/interfaces | Check inventory 鈫?calculate price 鈫?generate order 鈫?send notification |
| Need to insert code logic in non-LLM steps | Data cleaning, format conversion, mathematical calculation |
| Need to minimize Token usage | Only call large model at necessary nodes, use rules for the rest |

#### Choose Multi-Agent

| Scenario Characteristic | Example |
|----------|------|
| Involves multiple distinctly different professional domains | One entry point handles HR, finance, and IT issues simultaneously |
| Different domains need different knowledge bases/tools | HR uses HR knowledge base, finance uses finance system |
| Single Agent's prompt is too long, causing effectiveness decline | Split a 3000-word prompt into 3 Agents with 1000 words each |
| Need "expert consultation" mode | Multi-role collaboration: researcher + writer + reviewer |
| Multiple business lines but want unified entry | Enterprise all-in-one assistant (covering HR/IT/Admin/Legal, etc.) |
| Sub-tasks are relatively independent | Domain Agents can be developed and maintained independently |

### Scenario-Based Quick Reference

| Business Scenario | Recommended Mode | Recommendation Reason |
|----------|----------|----------|
| Enterprise Knowledge Q&A | Single Agent | Single knowledge domain, conversational interaction, no complex process needed |
| Role-playing/AI Training | Single Agent | Depends on persona prompt and multi-turn conversation capability |
| Daily News Morning Brief | Workflow | Fixed steps (search 鈫?filter 鈫?summarize 鈫?format 鈫?push) |
| Batch Data/File Processing | Workflow | Need loop node to iterate through list item by item |
| Form Collection and Approval | Workflow | Fixed routing steps + manual approval node |
| PPT/Report Auto Generation | Workflow | Multi-step generation, strict format requirements |
| E-commerce Comprehensive Customer Service | Multi-Agent | Need pre-sales/after-sales/complaint multi-role division |
| Enterprise Comprehensive Assistant | Multi-Agent | Involves HR, IT, finance and other domains, need routing dispatch |
| Software Development Collaboration Simulation | Multi-Agent | PM 鈫?Development 鈫?Testing multi-role sequential execution |
| Investment Decision Support | Multi-Agent | Multi-perspective analysis (optimistic/pessimistic/neutral Agent debate) |

## Common Selection Misconceptions

| Misconception | Correct Understanding |
|------|----------|
| Multi-agent is definitely better than single agent | Wrong. Multi-agent introduces coordination costs and latency. For simple tasks, a single agent is more effective and faster |
| Workflows are not intelligent enough | Wrong. Each LLM node in a workflow can perform complex reasoning. The "determinism" of workflows is an advantage in production environments |
| One Agent with enough tools can solve everything | Dangerous. When tools exceed 10-15, the probability of the model selecting the wrong tool increases dramatically. At this point, split into multi-agent |
| Build multi-agent first, simplify later | Wrong. Start with single agent, upgrade when encountering bottlenecks |

# 3 OpenJiuwen Usage Workflow

OpenJiuwen is an enterprise-level one-stop agent building and operations platform. It breaks traditional development barriers, supporting R&D and business personnel to quickly build various AI applications from simple assistants to complex business flows through visual, low-code methods.

## Single Agent Application Development Workflow

| Process | Sub-process | Description | Operation Guide |
|------|--------|------|----------|
| Develop Single Agent Application | Create and configure single agent application | First create a single agent application, mainly setting the application's name, description, and icon. Then configure the single agent's model and prompt | Create and configure single agent application |
| | (Optional) Add skills to application | Skills include plugins, workflows, chat memory, etc. Developers can continuously expand the model's functional scope through integrating plugins, designing workflows, etc. | Add skills to application |
| | (Optional) Add knowledge base to application | Knowledge base is the core component for agents to store, manage, and retrieve domain knowledge. Developers can add knowledge bases to provide precise information support for agents | Add knowledge base to application |
| | (Optional) Add memory to application | Variables store user behaviors or preferences. During conversations, the system automatically identifies content matching variables and stores it in the variables | Add memory to application |
| | (Optional) Add MCP services to application | Developers can quickly expand agent capabilities through integrating MCP services | Add MCP services |
| | (Optional) Enhance application conversation experience | Developers can enhance the application's conversation experience by configuring the agent's opening message, suggested questions, follow-up questions, voice, citation display, content review capabilities | Enhance application conversation experience |
| Debug and publish single agent application | Debug single agent application | After single agent application development is complete, developers can debug the application to precisely identify issues and quickly adjust configurations | Debug application |
| | Publish single agent application | After single agent application debugging is complete, the application needs to be published before users can use it | Publish application |
| Use single agent application | - | After the single agent application is published, it can be called through API interfaces | Call application via API |

## Workflow Application Development Workflow

| Process | Sub-process | Description | Operation Guide |
|------|--------|------|----------|
| Create workflow application | - | Create a workflow, including global configuration, orchestration, node selection, parameter configuration, node debugging, and completing functional connectivity | Create workflow |
| Debug and publish workflow application | Trial run workflow application | Developers can directly interact with the workflow after creation, observing its execution process and response effects in real-time, and optimizing and adjusting configurations as needed. The platform's full-link debugging feature allows developers to view the complete flow of each user request from input to response, including intent recognition, knowledge retrieval, and other detailed information | Trial run workflow |
| | Publish workflow application | After workflow application debugging is complete, the application needs to be published before users can use it | Publish workflow |
| Use workflow application | - | After the workflow application is published, it can be used in single agent applications, in multi-agent applications, or called through API interfaces | Use workflows in single agent applications, use workflows in multi-agent applications, call via API |

## Multi-Agent Application Development Workflow

| Process | Sub-process | Description | Operation Guide |
|------|--------|------|----------|
| Create multi-agent application | - | Multi-agent applications can flexibly use various workflows to complete user tasks, supporting jumping between different workflows based on user intent | Create multi-agent application |
| Debug and publish multi-agent application | Debug multi-agent application | Developers can directly converse with the multi-agent after creation, observing its execution process and response effects in real-time, and optimizing and adjusting configurations as needed | Debug multi-agent application |
| | Publish multi-agent application | After multi-agent application debugging is complete, the application needs to be published before users can use it | Publish multi-agent application as API |
| Use multi-agent application | - | After the multi-agent application is published, it can be called through API interfaces | Call application via API |

# 4 Developing Single Agent Applications

## 4.1 Single Agent Application Overview

A Single Agent is an independently operating AI entity that can autonomously perceive its environment, plan decisions, and execute tasks without requiring collaboration from other agents. Its core characteristic is centralized processing, suitable for scenarios with clear objectives and low complexity (such as customer service bots, game NPCs).

Single agent applications are suitable for handling simple independent tasks. If there are fixed task execution processes with high accuracy requirements, you can choose workflow applications; if you need to handle complex collaborative tasks, you can choose the multi-agent mode.

### Single Agent Application Orchestration Capabilities

| Feature | Description |
|------|------|
| Orchestration Mode | Supports manual creation or AI-assisted creation of single agents, completing a native AI application creation instantly with zero-code operations |
| Model Selection | OpenJiuwen supports selecting connected models or created routing strategies |

### Prompts

A prompt is a text instruction input by the user to the large model, used to guide the model in generating specific output. Prompt design directly affects the model's response quality and is a key tool for optimizing model performance.

| Feature | Description |
|------|------|
| Prompt Writing | Write prompts and set better-performing prompts as candidates. For more information, refer to prompt writing guidelines. Supports importing prompt examples, model settings, variable definition in prompts, effect preview, and history |
| Prompt Comparison | Supports selecting candidate prompts for comparison, including difference comparison and effect comparison |
| Prompt Optimization | The prompt editing interface provides automatic prompt optimization, using heuristic algorithm-based prompt self-optimization technology and prompt selection gradient optimization technology, which can automatically optimize existing prompts based on evaluation cases |
| Prompt Auto Generation | Using intelligent template matching and layout optimization technology, automatically generates high-quality prompt templates based on user input combined with prompt templates and model capabilities |
| Prompt Usage | Instruction configuration and LLM, intent recognition, Agent, advanced intent recognition, and questioner nodes in workflows support saving and referencing Prompt templates |

### Role Instructions

Agents can be given anthropomorphic characteristics through role instructions, enhancing interaction realism. The platform presets role instruction templates at the prompt editing area. You can also use smart addition to have the large model output a more suitable role prompt.

### Skills

The agent's core capabilities come from its skill system. Developers can continuously expand the model's functional scope through integrating MCP services, plugins, designing workflows, etc.

| Feature | Description |
|------|------|
| MCP Services | The platform's tool invocation supports the MCP protocol. Developers can quickly expand agent capabilities through integrating MCP services |
| Plugins | You can seamlessly connect various platforms and services through APIs, quickly expanding agent capabilities. The platform provides rich built-in plugins, ready to use out of the box; it also supports custom plugin development, wrapping any API as a tool for flexible invocation |
| Workflows | Single agents support adding published workflow version applications. Workflows are visual tools for building complex functional logic, capable of designing multi-step automated processes through flexible combination of multiple task nodes |

### Knowledge Base

Provides out-of-the-box enterprise-level RAG (Retrieval-Augmented Generation) services, covering all functions including management, testing, and retrieval strategy configuration.

| Feature | Description |
|------|------|
| Knowledge Base Hit Testing | Supports hit testing on created knowledge bases to evaluate the knowledge base's effectiveness and accuracy |
| Knowledge Base Recall Strategy | Retrieval strategies include semantic retrieval, keyword retrieval, and hybrid retrieval; relevance threshold setting; topk recall quantity; FAQ direct output threshold; view sources; view images |

### Memory

The system provides variable settings, automatically identifying and storing user behaviors or preferences, which can be called in subsequent conversations to provide responses more tailored to user needs.

| Feature | Description |
|------|------|
| Variables | Used to store user behaviors or preferences. During conversations, the system automatically identifies content matching variables and stores it in the variables |

### Conversation Experience

Agent development conversation experience supports full visualization, with quick issue identification and configuration optimization through debugging features.

| Feature | Description |
|------|------|
| Single Agent Icon | The Agent's brand identity, used for visual recognition, typically reflecting its function or personality |
| Opening Message | The Agent's initial welcome message when interacting with users, setting the conversational tone and guiding users. Supports user-defined configuration |
| Suggested Questions | Typical question examples preset at the start of each conversation, helping users quickly understand the agent's capability scope |
| Follow-up Questions | Proactive follow-up questions raised when conversing with the Agent, used to clarify needs or deepen interaction |
| Display Citations and Attribution | Model-generated responses will include citation sources, helping verify the accuracy and timeliness of information |
| Content Review Configuration | Ensures large model content safety by setting keyword matching to process input and output content |
| Preview & Debug | A tool for real-time testing and optimizing Agent functionality, displaying execution results and invocation details |

### Triggers

During Agent development, triggers can be added so that the Agent executes according to the trigger settings.

| Parameter | Description |
|------|------|
| Trigger Name | The trigger's name, consisting of 2-20 characters, must start with Chinese or English characters, supports Chinese, English, numbers, and underscores |

---

## 4.2 Example: Building a Medical Consultation Assistant Agent Application

With the continuous advancement of AI technology, large model applications in the medical field are becoming increasingly mature. By combining medical knowledge bases, natural language processing, and intelligent interaction technologies, medical consultation assistant agents can provide patients with preliminary health consultations, symptom analysis, and diagnostic suggestions, while reducing doctors' workloads and improving healthcare service efficiency.

### Prerequisites

An available model exists.

### Create a Single Agent Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. In the single agent application management interface, click "Create Single Agent" in the upper right corner
4. On the creation page, enter the application name, functional description, and other information in the basic information configuration, and select a "Single Agent Icon"

| Parameter | Example | Description |
|------|------|------|
| Name | Medical Consultation Assistant | In the single agent application workspace, names cannot be duplicated. Supports Chinese, English, numbers, underscores, hyphens, and spaces, 2-64 characters |
| Description | In the medical consultation assistant agent application, clarify the agent's objectives, functional scope, and interaction | Can simulate a doctor's consultation process, guiding users to describe their symptoms step by step through dialogue, then providing corresponding health advice |

5. Click "Create Now" to enter the application orchestration interface

### Select a Model

On the medical consultation assistant application configuration page, click "Application Configuration" in the middle of the interface, and select a model in the "Model" area.

In this example, set the default model to "DeepSeek-V3," select "Custom" mode, and use the system recommended values.

### Write the Prompt

When writing the prompt, define the agent's core pattern through role setting and interaction logic, clarifying key elements such as its role, task description, constraints, execution steps, and output format.

Example prompt:

```
You are a personal digital health manager. You can conduct consultations like a doctor, asking about the patient's condition and providing suggestions and treatment plans.

Requirements:
1. Focus on questions related to diseases, symptoms, examinations, and medications.
2. When users describe symptoms, you need to follow up, asking at most 2 questions each time, guiding the patient to describe symptoms and background in detail (such as past medical history, surgical history, medication history, family medical history, etc.) to assist diagnosis.
3. When patient information is sufficient or you have comprehensively understood the patient's main problems and symptom development, directly summarize the condition, recommend necessary examinations, treatment plans, and the appropriate department to visit.
4. Ensure answers are accurate, concise, and directly related to the patient's current health status or problem, avoiding digression.
5. Do not repeat questions from historical conversations. If the patient did not answer a question, do not ask again.
6. Do not repeat symptoms described by the patient. Ensure conversation content is novel and relevant.
7. Your response should not exceed 100 characters, with each sentence on a new line.
8. Strictly prohibit answering questions outside medical knowledge, such as small talk, entertainment, etc.

Please strictly follow the above rules and only provide necessary, concise answers.
```

### Expand the Agent's Capability Boundaries

When creating the medical consultation assistant, if the model's capabilities can basically cover the agent's required functions, you only need to write the prompt. If the agent needs to implement functions beyond the model's basic capabilities, you need to expand its capability boundaries by adding plugins, workflows, or MCP services.

1. In the "Skills" area of the orchestration page, click the icon after MCP services and select the corresponding icon for the MCP service
2. On the "Add MCP" page, select "Zhipu Web Search" and click "OK"
3. Modify the persona and response logic in the "Prompt" to instruct the agent to call the "Zhipu Web Search" plugin to answer questions beyond the model's knowledge

### Set Application Conversation Experience

Application conversation experience supports setting opening message, suggested questions, follow-up questions, display citations and attribution, content review configuration, etc.

1. Set opening message: Add an opening message for the agent, which will be displayed as the application's opening in the bubble to users
2. Set suggested questions: Enter in the input box or auto-generate in "Smart Add" (only supports adding 3 suggested questions)
3. Set follow-up questions: When follow-up question feature is enabled, the system provides question suggestions based on conversation content after each response
4. Set display citations and attribution: When configured and using web search or knowledge base tools, this feature can be enabled

### Debug the Medical Consultation Assistant Single Agent Application

After configuring the agent, you can test whether the agent's Q&A results meet expectations in the preview & debug area.

- Preview & debug interface supports text input and file input
- Debug results support one-click copy
- Supports editing or resetting variables
- Supports manual annotation, like, and dislike of debug result data
- Supports one-click clearing of trial run interface content

### Publish and Use the Medical Consultation Assistant Single Agent Application

1. In the single agent development debugging interface, click the "Submit Version" button in the upper right corner
2. In the "Submit Version" popup, fill in the version name and description, and click "OK." After success, click "Share" to jump to the "Channel Management" interface
3. After publishing, jump to the API invocation page where you can see the published API invocation interface information

---

## 4.3 Create and Configure a Single Agent Application

### 4.3.1 Create a Single Agent Application

OpenJiuwen supports the following ways to create single agent applications:

| Creation Method | Function | Operation Guide |
|----------|------|----------|
| Regular Creation | Orchestrate connected model services, tools, workflows, knowledge bases, etc. into an Agent | Regular create single agent application |
| AI-Assisted Creation | Describe the required Agent's application scenario and core functions through natural language. The platform will automatically generate and support quick modification of customized Agent persona, skills, rules, and knowledge base information | AI-assisted create single agent application |
| Use Preset Application | The Asset Center has built-in agent applications. Users can copy templates with exactly the same configuration as needed | Create |

#### Prerequisites

- Models have been connected to the OpenJiuwen platform
- The logged-in user is a space owner, space administrator, or development engineer

#### Regular Create Single Agent Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. In the single agent application management interface, click "Create Single Agent" in the upper right corner
4. On the creation page, set the application's basic information in the "Basic Information Configuration" tab

| Parameter | Description | Example |
|------|------|------|
| Name | In the single agent application interface, names cannot be duplicated. Supports Chinese, English, numbers, underscores, hyphens, and spaces, 2-64 characters, and the name cannot start or end with spaces | Smart Customer Service Single Agent |
| Description | Clarify the agent's objectives, functional scope, and interaction, displayed intuitively to users | Smart Customer Service agent application is the interface for users to interact with the smart customer service system |
| Single Agent Icon | The system provides a default single agent icon. After entering the name and description, click to auto-generate an avatar. Users can also customize the icon | - |

5. After setting, click "Create Now" to enter the application orchestration interface

#### AI-Assisted Create Single Agent Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. The following two creation methods are supported:
- Creation Method 1: Click "AI-Assisted Creation" in the "Quick Create Agent" card on the "Overview" page
- Creation Method 2: Select "Development Center > Agent Management" in the left navigation bar, enter the "Single Agent" tab, click "Create Single Agent," and click "AI-Assisted Creation" on the "Create Single Agent" page
3. Enter the task for AI-assisted creation in the input box, select "Model" and "Single Agent Application" in the lower left corner of the input box, and click send
4. In the thinking results, select the Agent task information you need, and click "Submit Requirements"
5. The platform will automatically generate the single agent's configuration items and prompt based on your selections. After thinking is complete, click "Confirm Generate" to complete creation

### 4.3.2 Select and Configure a Model

In OpenJiuwen, configuring a model after creating an agent is a key operation for building and optimizing intelligent applications. Users can select and integrate multiple large language models through the visual configuration page.

#### Prerequisites

OpenJiuwen has connected models.

#### Select a Model

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. In the single agent application management interface, select the created single agent
4. Enter the "Single Agent Configuration" page, click the "Model" parameter dropdown box, and select a model

Model tag display:
- Web: Indicates the large model has web search capability
- Thinking: Indicates the large model has thinking and reasoning capability
- Tools: Indicates the large model supports application calling external tools
- default-import: Indicates the large model is a system default model
- Free: Indicates the platform preset large model can be used for free
- Experience: Indicates the platform preset large model can be experienced

Model types include:
- Text: Indicates the large model is a text conversation type
- Vision: Indicates the large model is an image understanding type
- Embedding: Indicates the large model is a text vectorization type
- Rerank: Indicates the large model is a text ranking type

#### Adjust Model Generation Tendency

Click the icon after "Model" to configure the model generation tendency, adjusting the randomness and diversity of different models when generating content from multiple dimensions.

| Configuration Item | Description |
|------|------|
| Temperature | i.e., temperature, used to control the randomness of results. Increasing temperature makes the model's output more diverse and innovative; conversely, decreasing temperature makes the output more instruction-following but less diverse |
| Top P | The model selects from the highest probability words when outputting, until the cumulative probability of these words reaches the top_p value, limiting the model to selecting these high-probability words |
| History Dialogue Rounds | Set the number of conversation history rounds brought into the model context. More rounds mean higher relevance. Parameter range 1-100 |
| Max Reply Length | Used to control the length and quality of chat replies |
| Repetition Penalty | Used to prevent the model from frequently using the same words and phrases. Range -2 to 2 |

### 4.3.3 Configure Prompts

In the process of building an Agent application, setting prompts is a crucial step. A prompt is a natural language instruction used to guide the large language model on how to complete a specific task.

#### Prerequisites

The logged-in user is a space owner, space administrator, or development engineer.

#### Configure Prompts

Write prompts according to business needs. The clearer and more explicit the prompt, the more the agent's responses will meet expectations.

- Directly write prompts
- Role instruction templates: The platform provides prompt templates for reference when writing prompts
- AI-generated prompts: You can tell AI through natural language what prompt you want to write or optimize
- Reference templates: OpenJiuwen has preset multiple prompt templates for different scenarios, which can be used directly
- Reference variables: When users add memory and create variables for the application, they can select created variables in the prompt

---

## 4.4 Add Skills to the Application

### 4.4.1 Add MCP Services

Agent tool invocation supports the MCP protocol and provides a rich MCP service ecosystem to enhance agent capabilities. MCP is an open protocol that standardizes how applications provide context to large language models.

#### Constraints and Limitations

| Category | Description |
|------|------|
| Maximum MCP Services | The number of MCP services added to an application must be less than or equal to 5 |
| MCP Service Address | Installing preset MCP currently supports SSE and streamableHttp installation methods. Only HTTP and HTTPS are supported, must be in standard URL format |

#### Add MCP Services

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent management interface
3. Click the target single agent. In the "Skills" area, click the icon after MCP services and select the corresponding icon for the MCP service
4. On the "Add MCP Service" interface, click "Add All" after the deployed MCP service or click "Add" after the specific MCP service tool, and click "OK"
5. After adding MCP services, you can view the currently added MCP services in "MCP Services"
6. After successfully adding MCP, modify the persona and response logic in the prompt module to instruct the agent to call "MCP Services" to handle problems

### 4.4.2 Add Plugins

OpenJiuwen provides a rich plugin ecosystem to enhance agent capabilities. A plugin is a toolset, where one plugin is one API tool.

#### Prerequisites

- The logged-in user is a space owner, space administrator, or development engineer
- If you need to add personal plugins, ensure that personal plugin creation and debugging/publishing have been completed
- If you need to add preset plugins, ensure that plugin authentication has been configured
- If you need to add shared plugins, ensure that plugins shared by others are available

#### Constraints and Limitations

| Category | Description |
|------|------|
| Maximum Tool Quantity | Supports adding up to 20 tools |
| Plugin URL | URL protocol only supports HTTP and HTTPS |
| Request Method | The request method for the plugin service, POST or GET |

#### Add Plugins

- Add preset plugins
- Add personal plugins
- Add team shared plugins

### 4.4.3 Add Workflows

Workflows are a core tool in OpenJiuwen for designing and implementing complex task automation. Through task orchestration, conditional judgment, and the collaborative function of multiple components, workflows help developers efficiently handle complex tasks.

#### Prerequisites

- The logged-in user is a space owner, space administrator, or development engineer
- Before adding a workflow, ensure the workflow orchestration has been completed
- If you need to add shared workflows, ensure that workflows shared by others are available

#### Constraints and Limitations

One agent application supports adding up to 5 workflows.

---

## 4.5 Add a Knowledge Base to the Application

A knowledge base is the core component in an Agent for storing, managing, and retrieving domain knowledge. Through structured storage, intelligent retrieval, and dynamic update mechanisms, it provides high-match information support for the Agent.

#### Prerequisites

- The logged-in user is a space owner, space administrator, or development engineer
- If you need to use a local knowledge base in a single agent, ensure that a platform default knowledge base has been created and is in enabled status
- If you need to use a third-party knowledge base in a single agent, ensure that a third-party knowledge base has been connected and is in enabled status

#### Constraints and Limitations

| Category | Description |
|------|------|
| Maximum Knowledge Base Quantity | Supports associating 3 knowledge bases by default, expandable to 10 |
| Knowledge Base Size | Single document upload limit of 60MB maximum |

#### Add a Knowledge Base

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Click the target single agent application. In the "Knowledge Base" module, click the icon
4. In the "Add Knowledge Base" window, select the knowledge base type, click the target knowledge base or add after the target knowledge base, and click "OK"

#### Knowledge Base Recall Strategy

Click to perform advanced configuration on the knowledge base, including retrieval strategy and various recall thresholds.

| Category | Configuration Item | Description |
|------|--------|------|
| Retrieval Strategy | Semantic Retrieval | Uses vector retrieval technology to recall slice content with high relevance to user intent |
| | Keyword Retrieval | Uses inverted index retrieval technology to recall slice content with high keyword match to the Query |
| | Hybrid Retrieval | Uses both vector retrieval and keyword retrieval strategies to search the knowledge base |
| Recall Threshold | Relevance Threshold | Search results exceeding the relevance threshold will be submitted to the large model for summarization |
| | topk Recall Quantity | The number of top relevance threshold slices recalled |
| | FAQ Direct Output Threshold | FAQ retrieval results exceeding the threshold will be directly submitted to the large model for summarization |
| View Sources | View Sources | After adding a knowledge base and enabling this feature, you can view detailed source information of search results in the preview & debug interface |
| | View Images | After enabling this feature, when the knowledge base supports image retrieval, you can view image information in the retrieval results |

---

## 4.6 Add Memory to the Application

In multi-turn conversation scenarios, users often expect the agent to remember their preferences, identity, and interaction habits, thereby obtaining a coherent and personalized service experience.

OpenJiuwen provides the following memory types:

- User Variables: Store user attributes and preferences (such as name, language habits, areas of interest), supporting automatic identification and extraction, cross-session persistence, and dynamic updates
- Input Parameters: Dynamically inject external information into the agent through API calls (such as user ID, business document number), supporting String, Boolean, Integer, Number types

#### Constraints and Limitations

| Category | Description |
|------|------|
| Variables | Each application supports creating up to 30 variables |
| Variable Name | Cannot be empty, supports up to 100 characters, cannot contain the ^ symbol |
| Description and Default Value | Supports up to 500 characters |

#### Example: Configure and Use User Variables

Taking building a "Smart Customer Service Assistant" as an example:

1. Refer to creating a "Smart Customer Service Assistant" single agent
2. Add user variables: User variables allow the agent to identify and record specific user attributes during conversations

| Name | Description | Default Value |
|------|------|--------|
| name | User salutation | - |
| language | Communication language | - |

3. Reference variables in the prompt: Through the "{{memory.variable_name}}" syntax, defined variables can be incorporated into the prompt
4. Preview & debug and dynamic variable perception: User variables are automatically extracted and updated in real-time based on conversation content

---

## 4.7 Enhance Application Conversation Experience

### Configure Opening Message

The opening message is the guiding information users see first when entering the agent application, helping users quickly understand the agent application's functions and purposes.

### Configure Suggested Questions

Suggested questions are questions or topic suggestions that the application proactively displays when users first interact with the application. Up to 3 suggested questions can be configured.

### Configure Follow-up Questions

The follow-up question feature refers to the agent proactively asking further questions during interaction with users, based on the user's responses or context, to obtain more information or clarify user needs.

### Configure Voice

Configure voice, supporting assigning preset voices to the agent, used to configure the reading voice for the smart application's debug conversation model response results.

### Configure Display Citations and Attribution

When the single agent is configured and uses web search or knowledge base tools, the "Display Citations and Attribution" feature can be enabled.

| Output Type | Description |
|----------|------|
| Text Output | Citation sources are appended to the model response in text form |
| JSON Output | Citation sources are returned in structured JSON format |

### Configure Security Information

Content Review Configuration: Filters inappropriate, sensitive, or illegal information by setting keyword matching to process input and output content.

- Filter: The large model's output content fields are masked before returning to the user
- Replace: The large model's output keywords are replaced with the configured fields
- Fallback Reply: When keywords are triggered, the configured fallback reply content will be directly returned

---

## 4.8 Debug the Application

Developers can directly interact with the agent application after it is built, observing its execution process and response effects in real-time, and optimizing and adjusting configurations as needed.

### Debug the Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Click the target single agent application. In the "Preview & Debug" interface text box, enter a conversation, and the Agent application will generate corresponding responses based on the conversation
4. During debugging, click "Debug" in the upper right corner to view the execution results and invocation details of the current session or historical sessions

### Debug Information Description

- Execution Results: You can see the application's execution start time, end time, runtime, and other information, as well as input and output information
- Invocation Details: When triggering the application, the invocation chain shows detailed information about specific events, including triggered components, event duration, event input and output information, etc.

### Common Debug Scenarios

| Scenario | Debug Method |
|------|----------|
| Workflow | You can view the input and output of each workflow node for each request-response through the debug interface |
| MCP Services | You can view the operation status of MCP services called in each request-response through the debug interface |
| Plugins | You can view the operation status of plugins called in each request-response through the debug interface |
| Knowledge Base | You can view the operation status of the knowledge base node in the debug interface |

---

## 4.9 Configure Triggers

Triggers are a key function for task automation in Agents. They can automatically start task execution under specific conditions without manual intervention.

### Trigger Method

Call the application through scheduled tasks to execute tasks according to trigger instructions.

### Add a Trigger

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Click the target single agent application. Click the trigger configuration button in the upper right corner of the agent application
4. On the right side of the trigger configuration page, click the add button
5. Configure trigger information

| Parameter | Description |
|------|------|
| Trigger Name | The trigger's name, consisting of 2-20 characters, supports Chinese, English, numbers, underscores, must start with Chinese or English |
| Trigger Type | Supports periodic trigger and interval trigger |
| Trigger Time | Triggers the agent application execution at the set time |
| Bot Prompt | Enter natural language instructions; when triggered, the Agent follows these instructions to execute on schedule |

6. Click "OK" to complete trigger creation

---

## 4.10 Publish the Application

### 4.10.1 Publish the Application as an API Service

After publishing the Agent application as an API service, you can use the Agent program by calling the OpenAPI.

#### Prerequisites

- A single agent application has been created
- The logged-in user is a space owner, space administrator, or development engineer

#### Publish Agent Application as API Service

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Click "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. On the application development main page, select the created Agent application or click the "Create Single Agent" button in the upper left corner
4. On the application editing page, complete the function editing and debugging, then click the "Submit Version" button in the upper right corner
5. After publishing, click the "Share" button to jump to the "Channel Management" page, where you can view the API invocation interface information

### 4.10.2 Publish the Application as a Web Application

OpenJiuwen supports publishing Agent applications as web applications, suitable for various scenarios.

#### Prerequisites

- A single agent application has been created
- The logged-in user is a space owner, space administrator, or development engineer

#### Publish Application as Web Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. On the application development main page, select the created Agent application
4. On the application editing page, complete the function editing and debugging, then click the "Submit Version" button in the upper right corner
5. After publishing, you can click the "Share" button to jump to the "Channel Management" page
6. On the channel management page, click "Publish" in the operation column of the web sharing channel to access it

---

## 4.11 Call the Single Agent Application via API

OpenJiuwen provides Open API request methods. You can send requests through the invocation path, and the program will call the application and return expected results.

#### Prerequisites

Before calling the application, ensure the application has been published.

#### Get Application ID

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Hover the mouse over the target application, click "Copy ID" to get the current application ID

---

## 4.12 Manage Applications

After creating applications in OpenJiuwen, you can manage applications in the single agent application interface, performing deletion, copy creation, copy application ID, import, export, etc.

### Copy Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Hover the mouse over the target application, click "Copy" below the application
4. In the "Copy To" dropdown box, select the created target space

### Delete Application

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Hover the mouse over the target application, click "More > Delete" below the application
4. In the popup dialog box, click "OK"

### Copy ID

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Hover the mouse over the target application, click "More > Copy ID" below the application

### Import Application

The platform supports importing single agent applications. When importing a single agent application, the associated plugin and other configurations will be imported simultaneously.

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Import single agent application
- Click "Import" in the upper right corner of the page
- On the "Import" page, click "Select File" to select the jsonl format file to import, and click "Import"

### Export Application

The platform supports exporting single agent applications. When exporting a single agent application, the associated plugin and other configurations will be exported simultaneously.

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Export single agent application
- Click "Export" in the upper right corner of the page, or hover the mouse over the target single agent and click "More > Export"
- On the "Export" page, select the single agent application and click "Export"

### Channel Management

1. Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space
2. Select "Development Center > Agent Management" in the left navigation bar. Click the "Single Agent" tab in the upper left corner to enter the single agent application management interface
3. Hover the mouse over the target application, click "Channel Management" below the application
4. Jump to the "Publish Management" page


# 5 Developing Workflow Applications

## 5.1 Workflow Overview

A workflow is a series of interconnected steps used to implement business logic or complete specific tasks. It provides a structured framework for data flow and task processing for applications/agents.

The core of a workflow is an intelligently designed and orchestrated system, where multiple AI Agents collaborate to complete tasks using natural language processing (NLP) and large language models (LLMs). These agents work within a preset logical framework, able to autonomously perceive, reason, and act according to established rules to pursue specific goals, forming powerful collective intelligence that can break down information silos, integrate different data sources, and provide seamless end-to-end automation.

The OpenJiuwen platform provides a visual canvas where you can quickly build workflows by dragging nodes. It also supports real-time workflow debugging on the canvas. In the workflow canvas, you can clearly see the data flow process and task execution sequence.

### Workflow Node Overview

OpenJiuwen workflows consist of multiple nodes. Nodes are the basic units that make up a workflow. The platform supports various nodes, categorized by function into basic nodes, common nodes, logic nodes, tool nodes, message management nodes, and data & knowledge nodes. See Table 5-1 for specific node functions.

**Table 5-1 Configuration Nodes**

| Category | Node Name | Node Description |
|------|----------|----------|
| Basic Node | Start Node | The start node is the beginning node of the workflow. User input information is passed in through the start node. |
| Basic Node | End Node | The end node is the final node of the workflow, used to define the workflow's output information. |
| Common Node | LLM Node | Used to introduce large model capabilities in the workflow. |
| Common Node | Workflow Node | Implements workflow nesting within workflows. |
| Common Node | Agent Node | Used for dynamic planning of user tasks, completing automatic resolution of complex tasks through decomposing user original input, calling plugins, etc. |
| Logic Node | Condition Node | Serves as a branch switching node when orchestrating applications, directing to corresponding workflow branches based on input conditions. |
| Logic Node | Intent Recognition Node | Used for intent classification based on user input and directing to different subsequent processing flows. |
| Logic Node | Code Node | Used to introduce a code executor that executes Python or Node.js code based on node input, with the code execution result as the node output. |
| Logic Node | Advanced Intent Recognition Node | Used for intent classification based on large amounts of classifiable user input. Suitable for orchestrating branch logic with more than 20 intents. |
| Logic Node | Loop Node | The loop node is used to repeatedly execute a series of tasks. |
| Tool Node | Plugin Node | Used to introduce API plugins, executing user-defined plugins based on node input, with plugin execution results as node output. |
| Tool Node | MCP Service Node | Supports selecting configured or preset MCP services and choosing the required tools for invocation. |
| Tool Node | HTTP Request Node | Allows users to send requests to external services via HTTP protocol, enabling data retrieval, submission, and interaction. Supports multiple HTTP request methods and allows users to configure request parameters, headers, authentication information, request body, etc. |
| Message Management Node | Message Node | Defines text content to send to users during workflow execution. |
| Message Management Node | Questioner Node | Provides the ability to collect more information from users during conversations. |
| Message Management Node | Input Node | The input node is used to collect user input during workflow runtime. |
| Message Management Node | Q&A Node | The Q&A node provides the ability to ask users questions during intermediate processes. |
| Message Management Node | Object Extraction Node | Used to extract parameters from specified objects, supporting configuring sub-workflows for parameter validation and calibration, and initiating user interaction. |
| Message Management Node | Exception Node | The exception node allows users to flexibly set and throw detailed exception information based on business needs. |
| Variable & Knowledge Node | Variable Assignment Node | Used to dynamically set intermediate variables during loop execution. |
| Variable & Knowledge Node | Variable Aggregation Node | Can integrate output variables from multiple branches into one, facilitating unified configuration for downstream nodes. |
| Variable & Knowledge Node | Knowledge Retrieval Node | Can recall matching information from specified knowledge bases based on input parameters. |

### Configuration Method

When creating a workflow, each node needs to be configured with different parameters, such as input and output parameters. Developers can visually orchestrate more nodes through drag-and-drop to implement complex business process orchestration, quickly building applications.

The workflow approach is mainly aimed at complex business scenarios where the target task contains multiple complex steps and has strict requirements for output result success rate and accuracy.

When orchestrating workflows, use nodes for design based on functional needs.

## 5.2 Conversational Workflows and Task Workflows

The platform provides two types of workflows: conversational workflows and task workflows. Users can choose the appropriate workflow for different tasks or scenarios.

- Conversational Workflow: Oriented towards multi-turn interactive open-ended Q&A scenarios, extracting key information based on user conversation content and outputting final results. Suitable for customer service assistants, work order assistants, entertainment interaction, and other scenarios.
- Task Workflow: Oriented towards automated processing scenarios, directly outputting results based on input content without intermediate conversation interaction. Suitable for content generation, batch translation, data analysis, and other scenarios.

### Application Limitations

Task workflows do not support configuring input nodes, message nodes, questioner nodes, Q&A nodes, object extraction nodes, and Agent nodes.

### Differences Between Conversational and Task Workflows

**Table 5-2 Conversational vs Task Workflow Comparison**

| Difference | Conversational Workflow | Task Workflow |
|--------|--------------|--------------|
| Applicable Scenarios | AI customer service assistants, virtual assistants, work order assistants, entertainment interaction, and other multi-turn interaction scenarios. | Data processing, batch generation, automated reports, batch translation, data analysis, and other scenarios. |
| Nodes | Supports input nodes, message nodes, questioner nodes, and Agent nodes. | Does not support input nodes, message nodes, questioner nodes, and Agent nodes. |
| Trial Run Method | If the "Start" node has multiple parameters, first configure parameters other than query, then trial run in dialog box format. | If the "Start" node has multiple parameters, configure all input parameters simultaneously during trial run. |

## 5.3 Workflow Usage Limits

A workflow is a series of interconnected steps used to implement business logic or complete specific tasks. Note the following limitations during use.

### Workflow Usage Limits

**Table 5-3 Workflow Usage Limits**

| Limit | Description |
|------|------|
| Timeout | Workflow timeout 15 minutes, plugin timeout 50s, model timeout 15 minutes, other single nodes have no limit. |
| Run Count | Loop node's own maximum loop count is 1000. |
| Total Nodes | Maximum 150 non-free nodes in a workflow. |
| Request Size | Request query size limit of 100,000 characters. |

## 5.4 Build a Workflow

### 5.4.1 Workflow Orchestration Logic

Business logic refers to the part of an application that handles specific business rules and operations. It defines how the application processes data, executes operations, and makes decisions based on business needs. In OpenJiuwen, business logic is primarily implemented through workflows.

In OpenJiuwen, the Asset Square, component library plugins, MCP, knowledge bases, prompts, and development configuration models on the left side are all called "resources." In workflows, resources can be added or created based on business processing logic and business data to accomplish corresponding business objectives.

Resources in OpenJiuwen can be connected through process building and business connections for mutual invocation. During workflow orchestration, resources can be added to the work panel through drag-and-drop.

#### Understanding Business Orchestration

A workflow is a visual representation of business logic that determines the application's input and output data structures, data reception and processing rules, and decision flows.

For example: A text parsing workflow adds input resources for simple text input processing.

#### Orchestration Modes

OpenJiuwen supports both serial and parallel orchestration modes. Users can choose the appropriate orchestration logic as needed. For complex tasks, a reasonable combination of parallel and serial can significantly improve system efficiency.

**Table 5-4 Orchestration Mode Comparison**

| Orchestration Mode | Function | Use Case | Advantage |
|----------|------|----------|------|
| Serial Orchestration | Tasks execute one after another in sequence, with the next task starting only after the previous one completes. | Linear processing flow: each step must be completed in order, with the previous step's output as the next step's input. | Ensures tasks execute in logical order, with each node working based on the previous node's output results. |
| Parallel Orchestration | LLM or knowledge retrieval or other nodes process the same task simultaneously, integrating output results in variable aggregation, improving task processing accuracy and comprehensiveness. | Multi-task processing: multiple datasets can be processed simultaneously, improving processing efficiency. | After decomposing complex tasks into sub-tasks, multiple nodes can work simultaneously, improving processing efficiency and response speed through parallel processing. |

Note

Parallel orchestration supports multiple structures:
- Regular parallel: Only three levels, including start node, parallel structure, and end node. After the start node outputs results, multiple parallel nodes execute multiple tasks simultaneously.
- Nested parallel: Contains multiple layers of nesting, including start node, multiple parallel structures, and end node. After the start node outputs results, tasks connected to the start node begin executing, and their output is transferred to nested nodes.

### 5.4.2 Create a Workflow

A workflow is a series of interconnected steps used to implement business logic or complete specific tasks. Workflows can be used in agent and application building to implement specific tasks or instructions. Whether using workflows in agents or applications, you need to first create a runnable workflow.

OpenJiuwen supports the following ways to create workflow applications as shown in Table 5-5.

**Table 5-5 Creation Method Description**

| Creation Method | Function | Advantages | Disadvantages |
|----------|------|------|------|
| Create from Blank | Build workflows quickly through dragging nodes and configuring parameters on the platform's visual canvas. | Strong controllability, low development cost, high transparency. | Higher development cost. |
| AI-Assisted Creation | Describe the specific application scenario and core functions of the desired workflow. The platform will automatically generate a customized workflow based on user needs. | Strong adaptability, good user experience. | Poor controllability, strong data dependency. |
| Use Preset Application | The Asset Square has built-in workflow applications. Users can copy workflows with exactly the same configuration as needed. | Efficient development speed, low barrier. | Highly customized, cannot meet all personalized needs. |

#### Prerequisites

- Models have been connected to the OpenJiuwen platform. For connection guidance, refer to Models.
- The logged-in user is a space owner, space administrator, or development engineer.

#### Regular Create Workflow

Step 1 Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space.

Step 2 Click "Development Center > Agent Management" in the left navigation bar. Click the "Workflow" tab in the upper left corner to enter the workflow application management interface.

Step 3 Click "Create Workflow" in the upper right corner to enter the "Create Conversational Workflow" or "Create Task Workflow" page. See Table 5-2 for differences.

Step 4 After selecting, configure the application's basic information. See Table 5-6 for parameter descriptions.

**Table 5-6 Basic Information Configuration**

| Parameter | Description | Example |
|------|------|------|
| Name | In the workflow application interface, workflow names cannot be duplicated. Input can only contain English letters, numbers, underscores, and spaces, starting with a letter, 2-64 characters, and cannot start or end with spaces. | SmartCustomerService |
| Description | Describes the workflow's function, displayed to users, length 0-256. | Smart customer service agent application is the interface for users to interact with the smart customer service system. |
| Workflow Icon | System default workflow icon. Users can also customize the icon or auto-generate with AI. | 1. Hover over the system default icon, left-click. 2. Upload a prepared application icon. Supports jpg, jpeg, png, gif formats, no larger than 200KB. |

Step 5 After configuration, click "Create Now" to enter the workflow orchestration page.

In the initial state, the workflow contains Start, LLM, and End nodes:
- Start Node: Used to start the workflow.
- LLM Node: (Optional) Provides large model capabilities. You can configure deployed models in the node. Users can have the model process tasks by writing prompts and setting parameters. If not needed, click the delete button in the upper right corner to remove the node.
- End Node: Used to return the workflow's execution results.

#### AI-Assisted Create Workflow

Note:
- AI-assisted creation only supports creating conversational workflows.
- OpenJiuwen supports creating workflows through AI, both through "Development Center > Agent Management > Workflow" and through "Overview Page > Quick Create > AI-Assisted Creation."

Step 1 Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space.

Step 2 Click "Development Center > Agent Management" in the left navigation bar. Click the "Workflow" tab in the upper left corner to enter the workflow application management interface.

Step 3 Click "Create Workflow" in the upper right corner of the workflow application management interface.

Step 4 Click "AI-Assisted Creation" on the "Create Conversational Workflow" page.

Step 5 Select a task above the input box, or enter a task in the input box, select "Model" and "Workflow Application" in the lower left corner, and click. Using "Create a leave approval workflow" as an example.

Step 6 Submit requirements in the input box on the thinking interface, and click "Confirm Generate" after the thinking results appear.

Note:
- If the thinking results do not meet requirements, you can re-enter instructions in the input box.
- On the workflow orchestration page, you can expand the workflow application's capabilities as needed.

Step 7 OpenJiuwen will generate the workflow application based on the workflow design diagram, viewable in the preview interface. You can click "Go to Edit" in the upper right corner to jump to the workflow orchestration page or click "Submit Version."

Note:
- The workflow name is auto-generated when the workflow application is created, and can be modified by clicking the button.

#### Global Configuration

On the workflow orchestration interface, there is a global configuration entry in the upper right corner of the canvas, used to configure conversational workflow conversation experience, default model, global feature switches, and defined configuration capabilities.

Note:
- Published workflow versions as independent resources do not support modifying global configuration.

**Table 5-8 Global Configuration Parameters**

| Parameter | Function |
|------|------|
| Default Model | Serves as the intelligent generation model source for opening message and suggested questions. New nodes default to using this model configuration. Checking the checkbox under model configuration can batch-modify the global model, improving model configuration efficiency. |
| Conversation Experience | The description will be displayed as the application's opening message in the bubble. Supports up to 226 characters. Supports configuring opening message and suggested questions for conversational workflows. Supports intelligent generation. Follow-up questions: Takes effect when a model is set in global configuration, proactively asking follow-up questions during workflow conversations. |
| Memory Variables | Memory variable node assignment supports workflow node references, and also supports referencing object templates and JSON import. When global variables are configured with node assignment and the start node has other input parameters, these parameters can be debugged in the trial run interface. Memory variables support session-level; when the session ends, recorded parameter values will automatically restore to default values. |
| Content Review Configuration | Supports enabling or disabling content review configuration through the toggle button on the right. When enabled, click "Configure" to set keyword matching for input/output content, ensuring large model content safety. |

#### Orchestrate Workflow

After creating a workflow, the initial state contains Start, LLM, and End nodes. Add nodes in the canvas, connect them according to task execution order, and configure input and output parameters according to workflow business flow.

The workflow has multiple built-in basic nodes. You can also add "Plugin" nodes to execute specific tasks. For plugin node usage, see Using Plugins in Workflows.

For canvas interface operations, see Canvas Operation Instructions.

Step 1 In the workflow panel, click "Add Node" and select the target node.

Step 2 Connect each node, paying attention to business flow direction when connecting.

Step 3 Configure node input and output parameters.

### 5.4.3 Trial Run a Workflow

Developers can directly interact with the workflow after creation, observing its execution process and response effects in real-time, and optimizing and adjusting configurations as needed. The platform's full-link debugging feature allows developers to view the complete flow of each user request from input to response, including intent recognition, knowledge retrieval, and other detailed information, enabling efficient issue identification and quick configuration adjustments.

OpenJiuwen supports debugging the entire workflow as well as debugging individual workflow nodes.

#### Prerequisites

- A workflow has been created.
- The logged-in user is a space owner, space administrator, or development engineer.

#### Constraints and Limitations

When trial running a workflow, the end-to-end runtime can execute for up to 10 minutes.

#### Trial Run Workflow (Required)

Step 1 Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space.

Step 2 Click "Development Center > Agent Management" in the left navigation bar. Click the "Workflow" tab in the upper left corner to enter the workflow application management interface.

Step 3 Find the target workflow in the workflow interface and click to enter the workflow orchestration page.

Step 4 Trial run the workflow.

In the workflow's start node, there is a default input parameter query, representing the user's original input content in the current conversation round. You can also add other parameters as needed for downstream nodes. Therefore, trial running the workflow has two scenarios: one using only the start node's default input parameter query, and another where the start node has user-added parameters.

- When the start node has the default input parameter query, after workflow orchestration, click "Trial Run" in the upper right corner, enter a question in the dialog box, and wait for the trial run results.

- When the start node has user-added parameters, after workflow orchestration, click "Trial Run" in the upper right corner, enter questions in the dialog box, click "Start Run," and wait for trial run results.

Step 5 After the trial run, you can click the runtime in the upper right corner to view debug results, including execution results and invocation details.

If the trial run fails, see Application Development FAQ for common errors and solutions.

#### Debug Single Node

Using debugging the "Intent Recognition" node as an example:

Step 1 On the workflow orchestration page, click the intent recognition node's icon to enter the single node debug page.

Step 2 Enter parameter content and click "Start Run."

Step 3 On the "Execution Results" page, view the current node's execution results.

If execution succeeds, the node will display "Execution Succeeded."

If execution fails, adjust node parameters based on the prompt.

### 5.4.4 Configure Triggers

Triggers are a key function for task automation in workflows. They can automatically start task execution under specific conditions without manual intervention. Triggers can be flexibly set to ensure tasks are completed on time and as needed, improving the automation level and response speed of workflow applications.

#### Trigger Method

Call the application through scheduled tasks to execute tasks according to trigger instructions.

#### Add a Trigger

Step 1 Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space.

Step 2 Click "Development Center > Agent Management" in the left navigation bar. Click the "Workflow" tab in the upper left corner to enter the workflow application management interface.

Step 3 Click the target workflow. Click the trigger configuration button in the upper right corner of the workflow application.

Step 4 On the right side of the trigger configuration page, click add.

Step 5 Configure trigger information. See Table 5-10 for parameter configuration.

**Table 5-10 Create Trigger Parameters**

| Parameter | Description |
|------|------|
| Trigger Name | The trigger's name. 2-20 characters, supports Chinese, English, numbers, underscores, must start with Chinese or English. |
| Trigger Time | Triggers the agent application execution at the set time. Periodic trigger - daily/weekly/monthly. Interval trigger - supports intervals of "days," "hours," "minutes," "seconds." |
| Bot Prompt | Enter natural language instructions; when triggered, the Agent follows these instructions to execute on schedule. |
| Invocation Method | Synchronous: After triggering, waits for the called operation to fully execute and return results before continuing. Asynchronous: After triggering, only initiates the call request without waiting for completion, directly continuing subsequent flows. |

Step 6 Click "OK" to complete trigger creation. You can view, modify, and delete triggers in the trigger list.

### 5.4.5 Publish a Workflow

After the workflow trial run succeeds, it can be published for subsequent use, such as adding the workflow in single agent applications.

#### Prerequisites

The workflow has been debugged. See Trial Run Workflow for details.

#### Publish Workflow

Step 1 On the workflow orchestration page, click "Submit Version" in the upper right corner, enter the version name and description, and click "OK."

Step 2 After publishing, click "Share," or navigate to "Development Center > Agent Management" in the left navigation bar, click the target application, enter the application configuration page, and select the "Channel Management" tab to enter the channel management page.

Step 3 On the channel management page, click "View API" in the invocation method tab to view API invocation interface information.

Step 4 In the channel management's sharing channels tab, you can see multi-platform publishing status.

#### View Publish History

Click in the upper right corner to view the current workflow's publish history.

## 5.5 Using Workflows

### 5.5.1 Call a Workflow via API

After the workflow is published successfully, you can call the workflow using API.

#### Prerequisites

- Ensure the workflow has been published.
- The logged-in user is a space owner, space administrator, or development engineer.

#### Get Workflow ID

Step 1 Log in to the OpenJiuwen Agent Development Platform. In the "Personal Space" area of the left navigation bar, select the target space.

Step 2 Click "Development Center > Agent Management" in the left navigation bar. Click the "Workflow" tab in the upper left corner to enter the workflow application management interface.

Step 3 Hover the mouse over the target workflow, click "More > Copy ID" to get the current workflow ID. Save it for filling in the agent_id field when calling the Agent application interface.

#### Use API to Call Workflow Application

After the workflow is published as an API service, you can call the workflow application via API. Refer to the "Calling Workflow Applications" chapter in the Agent Development Platform 26.2.1 API Reference.

### 5.5.2 Use Workflows in Single Agent Applications

The workflow feature is a core part of implementing single agent application business logic. It defines the application's input and output data structures, data reception and processing rules, and decision flows. Through workflows, single agent applications can support adding workflow skills, allowing users to combine plugins, large models, and other different nodes through canvas orchestration, implementing complex and stable business process orchestration.

#### Prerequisites

- Ensure the workflow has been published.
- The logged-in user is a space owner, space administrator, or development engineer.

#### Configure Workflow in Single Agent Application

Step 1 In the "Skills > Workflow" module, click add.

Step 2 In the "Add Workflow" window, click to add, then click "OK."

Step 3 After adding the workflow, you can view the currently added workflows in "Skills > Workflow."

### 5.5.3 Use Workflows in Multi-Agent Applications

The workflow feature can be used to implement the business logic part of multi-agent applications. Workflows determine the application's input and output data structures, data reception and processing rules, and decision flows, and are the core part of agent applications.

Multi-agent applications add workflow skills to analyze user session intent and route to different sub-workflows to execute orchestrated tasks.

#### Prerequisites

- Ensure the workflow has been published.
- The logged-in user is a space owner, space administrator, or development engineer.

#### Configure Workflow in Multi-Agent Application

Step 1 On the "Multi-Agent Controller" configuration page, you can add intent recognition, sub-agents, global intents, start workflow, default workflow, and end workflow.

Step 2 After adding workflows, click the dropdown box to select published workflow version applications.

Step 3 After adding and saving workflows, you can view currently added workflows in the canvas.

Step 4 Add start, default, and end workflows by clicking the dropdown box to select and "Save."

## 5.6 Manage Workflows

### Import Workflow

Supports importing OpenJiuwen DSL files and Dify DSL files. Only jsonl format files are supported for OpenJiuwen DSL, max 128MB. For Dify DSL, only yml format files are supported, max 128MB.

If associated resources (such as plugins, MCP, knowledge bases) fail to import, the application will still import normally, but these resources will not be imported.

### Export Workflow

The platform supports exporting workflows. When exporting a workflow, associated plugin and other configurations will be exported simultaneously.

### Workflow-Related Operations

**Table 5-11 Workflow-Related Operations**

| Type | Operation |
|------|------|
| Copy | Hover over the target workflow, click "Copy," select the target space in the "Copy To" dropdown. Configuration parameters, large models, nodes, etc. will be copied. The copied application needs to be published separately. |
| Get Workflow ID | Hover over the target workflow, click "More > Copy ID" to get the current workflow ID. |
| Invocation Path | Hover over the target workflow, click "Invocation Path" to get the workflow's API interface. |
| Delete | Note: If the workflow version has been referenced, deletion will automatically cancel the reference. Hover over the target workflow, click "More > Delete." |
| Channel Management | Hover over the target application, click "Channel Management" below the application. |

## 5.7 Basic Nodes

### 5.7.1 Start Node

The start node is used to trigger a workflow, and the end node returns the workflow's final results.

#### Start Node

The start node is the workflow's "perception boundary" and "data entry point." It defines what external information the workflow needs to receive when starting (whether it's a piece of text, a file, or a specific parameter).

- Node Positioning: It determines how the workflow understands user intent. If the start node is not clearly defined, subsequent LLM nodes or other nodes will not be able to pass parameters properly.
- Default Parameter: The system presets a query parameter, representing the user's original input content in the current conversation round. You can also add other parameters as needed for downstream node input.

Note:
- The start node supports a maximum input string length of 100,000. Exceeding this limit will cause an error. If building long text processing, HTML cleaning, data cleaning workflows, please note the input length limit to prevent error OpenJiuwen.02001003.

##### Data Types

The start node supports configuring String, Number, Boolean, Object, File, Array input parameters. For complex business parameters (such as user information), using Object (supports 5 levels of nesting) is recommended to maintain data structure cleanliness.

##### Parameter Description

Parameter description information. Extremely important! When the workflow is bound to an agent, the large model uses this description to decide how to automatically extract information from user conversations.

##### Required

Whether the parameter is required. If set to required, the workflow cannot run without this parameter.

##### Parameter Default Value

You can set default values for input parameters. The default values will be displayed in the trial run interface's input box. For Object type parameters, the default value needs to be entered as JSON data.

### 5.7.2 End Node

The end node is the workflow's "interaction exit." It determines how the workflow feeds results back to users or downstream systems after executing a series of complex logic.

- Conversational feedback: Directly replies with natural text. For example: The result found for you is {{result}}.
- Task feedback: Returns structured data (JSON), upgrading the workflow's return from "natural language conversation" to "programmatically callable standardized data format."

#### Input Parameters

Used to receive data passed from upstream nodes. Supports referencing upstream node outputs or entering a constant value. This parameter cannot be returned directly; it must be inserted in the "Specified Reply" using {{variable_name}} format to appear in the final result.

System parameters:
- "conversation_history": Stores the current conversation's historical message records.
- "current_time": Gets the current system timestamp or time string.
- "user_id": Identifies the current user's unique identifier.
- "conversation_id": The current workflow's unique conversation identifier.
- "dialogue_count": The current conversation's round count.

#### Output Parameters

The end node's output parameters are specifically for returning data externally in variable form. All output parameters are aggregated and returned in JSON format after workflow execution.

#### Specified Reply

The specified reply is the visual display content editing area for the workflow's final result. Users can customize reply text content and insert configured input parameters using {{variable_name}} format.

The specified reply does not support inserting output parameters.

#### Common Issues

**Q: Error "response_template type error, empty or reference exception", how to fix?**

**A:** Check if variable references are valid (most common cause). The parameter referenced in "Specified Reply" is not defined in "Input Parameters." Change the input parameter name to result, or change the specified reply's reference parameter to {{accountName}}.

## 5.8 Common Nodes

### 5.8.1 LLM

The LLM node is the workflow's "brain." It can not only generate conversations but also perform logical reasoning, task decomposition, and unstructured data extraction based on context. By configuring prompts and model parameters, you can control its output style and format, providing decision basis or structured data for downstream nodes.

#### Core Capabilities

- Content Generation: Writing copy, code, translations, creative writing.
- Logical Decision: Analyzing user intent, determining which plugin to call next.
- Information Extraction: Extracting key fields (such as time, location, amount) from natural language in JSON format.

#### Constraints and Limitations

- If using multiple LLMs in parallel after an LLM node, the first LLM node should be configured as non-streaming output.
- LLM does not support retry on failure.

#### Configure LLM Node

##### Model Configuration

Select the model to use. The output quality of this node is largely affected by the model's capabilities.

##### Input Parameters

Input parameters define variables passed from preceding nodes, referenced in prompts via {{parameter_name}}. Default parameter name is query.

##### Output Parameters

- Output Format: Specifies the content format of this node's output.
    - Text: Plain text format. Contains one text type output variable, default name raw_output.
    - Markdown: Markdown format. Contains one text type output variable, default name raw_output.
    - JSON: Standard JSON format. Supports defining multiple structured output variables. The node will attempt to parse the model's response and fill extracted information into corresponding output parameters.
- Streaming Output: Controls whether the model returns results character by character or all at once. Only Text and Markdown formats support streaming output.

##### Prompt Configuration

- Short-term Memory: Controls whether the LLM reads multi-turn conversation history. Disabled by default.
- System Prompt: Configure the prompt input to the LLM, system-level prompt used to guide the model in replying as required.
- User Prompt: The specific question, instruction, or request that the user directly inputs to the LLM. Supports referencing variables using {{variable}} format.

##### Exception Handling

Supports handling node exceptions (such as timeout, call failure), including timeout duration, retry count, and exception handling method.

- Timeout: 0.1-900, default 900s.
- Retry Count: No retry, retry 1/2/3 times. Default no retry.
- Exception Handling: Interrupt flow / Return specified content / Execute exception flow.

##### Security

Mainly used to detect and intercept potentially harmful, sensitive, or offensive content. Enabling safety guardrails may cause some performance degradation. Disabled by default.

### 5.8.2 Workflow

Design workflow nodes to implement workflow nesting functionality.

#### Node Description

In one workflow, you can use another workflow as one of its steps or nodes, implementing encapsulation of complex tasks. Through workflow nesting, modular splitting and processing of complex tasks can be achieved.

**Table 5-13 Workflow Node Configuration**

| Configuration Type | Parameter Name | Description | Example |
|----------|----------|----------|----------|
| Parameter Config | Input Parameters | The input structure depends on the sub-workflow's defined input structure. | query |
| Parameter Config | Output Parameters | The output structure depends on the sub-workflow's defined output structure. response_content is a fixed output parameter. | response_content |
| Exception Handling | - | Supports handling node exceptions. | Timeout: 900. Exception handling: Interrupt flow. |

### 5.8.3 Agent

The Agent node provides large model capabilities and large model tool calling capabilities.

#### Agent Node Description

You can configure deployed models in the node. Users can have the model process tasks by writing prompts and binding plugins.

**Table 5-14 Agent Node Configuration**

| Configuration Type | Parameter Name | Description | Example |
|----------|----------|----------|----------|
| Model Config | Model | Select the model for this node. | DeepSeek-V3-64k |
| Model Config | Temperature | Controls randomness of generation results. | 0.5 |
| Model Config | Top P | Controls diversity of output content. | 0.5 |
| Model Config | Max Reply Length | Controls the maximum Tokens length of model output. | 131072 |
| Parameter Config | Input Parameters | Add input parameters. | - |
| Parameter Config | Plugins | Bind manually created or preset plugins. | - |
| Parameter Config | Tool Usage Constraints | Configure usage constraints for the large model. | - |
| Termination Condition | Max Iteration Rounds | Maximum interaction count with the model. | 9 |
| Termination Condition | Plugin Execution Success | Break out of Agent node after plugin succeeds. | Disabled |
| Termination Condition | Detect User Exit Intent | Break out when user shows exit intent. | Enabled |
| Parameter Config | Output Parameters | The output is the Agent node's last round output. | - |

## 5.9 Logic Nodes

### 5.9.1 Condition

The condition node is the workflow's logical router. It directs the workflow to different execution branches through preset condition expressions (IF/ELSE) based on preceding node output variables.

#### Configure Condition Node

When input parameters are provided to this node, it evaluates whether they meet the IF condition. If met, the IF workflow branch executes; otherwise, the ELSE branch executes.

Each branch condition supports adding multiple conditions (AND/OR). Multiple branches can be added.

#### Common Issues

- **What's the difference between condition nodes and intent recognition nodes?**
    - Intent Recognition Node: Specifically for "understanding human language." Uses large model to analyze natural language input and identify underlying intent. Suitable for handling ambiguous, diverse language expressions.
    - Condition Node: Specifically for "processing data." Makes precise judgments on structured data based on preset logical conditions (such as >, ==, contains). Suitable for programmatic logic routing.

### 5.9.2 Code

The code node is used to execute custom code logic in workflows. When the workflow requires data processing, format conversion, mathematical calculation, logic judgment, etc., and these operations are difficult with other nodes or inaccurate with large models, code can be written through the code node. Code execution results are deterministic.

**Table 5-16 Code Node Use Cases**

| Scenario | Example |
|------|------|
| Data Format Conversion | Extract and reorganize JSON data from upstream nodes into formats needed by downstream nodes. |
| Mathematical Calculation | Price calculation, discount calculation, data summary statistics. |
| Text Processing | Regex matching, string concatenation, content extraction, encoding conversion. |
| Logic Judgment | Complex conditional judgment, data validation, rule matching. |
| Data Cleaning | Deduplication, filtering, sorting, field mapping. |
| Calling External Interfaces | HTTP calls requiring custom request logic. |

Code example:
```python
def main(args: dict) -> dict:
    """Running the code node calls this function"""
    ret = {
        "key0": args.get('input', 'default'),
        "key1": "hi"
    }
    return ret
```

### 5.9.3 Loop

The loop node provides the ability to execute nodes in a loop. You can configure nodes to be looped within the loop body.

#### Constraints and Limitations

The loop node does not support configuring Q&A nodes, questioner nodes, Agent nodes, input nodes, or sub-workflows containing these nodes.

**Table 5-18 Loop Node Configuration**

| Configuration Type | Parameter Name | Description |
|----------|----------|----------|
| Loop Type Config | Use Array Loop | Similar to for syntax. Traverses a known sequence. Built-in variables: item (array element), index (array index). |
| Loop Type Config | Specify Loop Count | Used for batch, sequential data processing. Default 5 times, supports 1-1000 times. |
| Variable Config | Type/Value | Only configurable when using array loop. Name fixed as arr_loop_var, only supports referencing upstream node output. |
| Intermediate Variables | - | Loop nodes support setting intermediate variables, effective for each loop iteration. |
| Output Parameters | - | Can be set as the execution result collection of the loop body, or as intermediate variable values. |
| Termination Condition | Expression | Branch composed of [comparison parameter, comparison condition, comparison parameter]. |

### 5.9.4 Intent Recognition

The intent recognition node primarily lets the application understand the user's intent or purpose expressed in natural language. It can be used for scenarios requiring classification of user questions or providing comprehensive functionality with different branch processing.

### 5.9.5 Advanced Intent Recognition

The advanced intent recognition node is used for intent classification based on large amounts of classifiable user input, suitable for orchestrating branch logic with more than 20 intents. It supports importing intent packages for managing large numbers of intents.

## 5.10 Tool Nodes

### 5.10.1 Plugin

The plugin node is used to introduce API plugins, executing user-defined plugins based on node input, with plugin execution results as node output.

### 5.10.2 MCP Service

Supports selecting configured or preset MCP services and choosing required tools for invocation.

### 5.10.3 HTTP Request

The HTTP request node allows users to send requests to external services via HTTP protocol, enabling data retrieval, submission, and interaction.

**Table 5-25 HTTP Request Node Configuration**

| Configuration Type | Parameter Name | Description |
|----------|----------|----------|
| API Config | Request Method | GET: Request data from external services. POST: Submit data to the server. |
| API Config | Domain | Server domain of the request address. |
| API Config | Path | The actual path of the request address, supports dynamic parameter specification. |
| Parameter Config | Input Parameters | Supports dynamic parameter specification in path or request body. |
| Parameter Config | Request Parameters | Key-value pairs appended to the URL. |
| Parameter Config | Request Headers | Contains client information, such as User-Agent, Accept. |
| Parameter Config | Request Body | Data contained in the HTTP request body. Supports none and json modes. |
| Output Parameters | - | Defines the data structure returned after a successful HTTP request. |
| Authentication | No Authentication | No additional authentication needed. |
| Authentication | API Key | Custom authentication with key and value. |
| Exception Ignore | - | When enabled, if this node fails, the workflow continues without interruption. |

## 5.11 Message Management Nodes

### 5.11.1 Message

The message node is the workflow's real-time feedback mechanism. Unlike the "End Node," the message node allows the workflow to proactively push intermediate results to the user interface during execution without waiting for the entire process to complete.

#### Core Value

- Reduce waiting anxiety: Send "Searching..." prompt before executing time-consuming tasks.
- Step-by-step output: Split complex reasoning into multiple message bubbles.
- Debugging and monitoring: Output variable intermediate states during development.

**Table 5-28 Message Node vs End Node**

| Dimension | Message Node | End Node |
|------|----------|----------|
| Trigger Timing | Sent immediately when workflow reaches this node | Output after all workflow execution completes |
| Occurrence Count | Can have multiple in one workflow | Usually only one end node |
| Blocks Flow | Does not block; workflow continues after sending | Blocks; workflow ends after output |
| Streaming Output | Supports referencing streaming parameters | Does not support streaming output parameters |
| Typical Use | Intermediate messages, progress prompts | Final results, complete replies |

### 5.11.2 Input

The input node pauses the workflow during execution to collect additional information from users. When downstream nodes need certain parameters not yet obtained, you can insert an input node to proactively ask the user.

**Table 5-33 Input Node vs Start Node**

| Dimension | Start Node | Input Node |
|------|----------|----------|
| Position | At the very beginning, only one | Any intermediate position, can have multiple |
| Trigger Timing | Auto-triggered when user initiates conversation | Proactively pauses when workflow reaches this position |
| Information Type | User's initial input | Additional information needed mid-workflow |
| Blocks | Does not block (workflow starts here) | Blocks workflow execution until user input completes |

### 5.11.3 Questioner

The questioner node proactively asks users questions during workflow execution, extracting structured parameters needed to complete tasks from natural language conversations. It loops follow-up questions until all required information is collected or the maximum interaction count is reached.

#### Constraints and Limitations

The questioner node is only applicable to conversational workflows.

**Table 5-36 Default Output Parameters**

| Parameter Name | Type | Description |
|--------|------|------|
| USER_RESPONSE | string | User's original reply text (unprocessed) |
| STATUS | integer | Extraction status code: 0=normal successful extraction; 10=normal successful extraction, user confirmed; 100=partial parameters, user interrupted; 101=partial parameters, loop exceeded; 201=LLM call exception; 202=reflection module error. |

### 5.11.4 Q&A

The Q&A node is used to ask users preset questions during workflow execution. Depending on the configuration mode, it can either pause the workflow waiting for user answers (requires answer mode) or simply send the question and continue (no answer needed mode).

### 5.11.5 Object Extraction

The object extraction node is used to extract parameters from specified objects, supporting configuring sub-workflows for parameter validation and calibration, and triggering user interaction flows.

**Table 5-43 Object Extraction Node Configuration**

| Configuration Type | Parameter Name | Description |
|----------|----------|----------|
| Input Parameters | Input Parameters | Supports configuring one or more input parameters. |
| Context Variables | Context Variables | Can be referenced by sub-workflows, effective throughout the session. |
| Domain Object | Domain Object | Can be referenced by sub-workflows, effective throughout the session. |
| Object Processing Flow (Optional) | - | After model completes object extraction, executes multiple object processing flows in defined order. |
| Model Parameter Config | Select Model | Select a configured large language model. |
| Prompt Config | - | Configure prompts for the LLM. |
| Extended Workflow (Optional) | - | Supports adding multiple workflows with execution timing configuration. |
| Node Exit Condition | - | Condition for exiting this node. |
| Node Exception Condition | - | Condition for entering the exception branch. |

### 5.11.6 Exception

The exception node function terminates the flow when the workflow encounters a business exception, returning preset error information and exception codes to the user or upstream system.

Exception information must be in JSON format:
```json
{
  "code": "ERROR_CODE",
  "message": "Human readable error"
}
```

## 5.12 Data & Knowledge Nodes

### 5.12.1 Variable Assignment

The variable assignment node assigns specific values to variables, enabling dynamic data update and transfer.

**Table 5-46 Variable Assignment Node Configuration**

| Configuration Type | Parameter Name | Description |
|----------|----------|----------|
| Outside Loop | Variable Assignment Config | Variable names only support memory variable references from global configuration. Values support reference or input. |
| Outside Loop | Type, Value | Supports "Reference" and "Input" types. |
| Outside Loop | Operation Assignment | Supports simple arithmetic for numeric types, including increment and decrement. Supports 8 data types for null assignment. |
| Inside Loop | - | Only supports modifying intermediate variables. |
| Inside Loop | Operation Assignment | Supports simple arithmetic for numeric types, including increment and decrement. |

### 5.12.2 Variable Aggregation

The variable aggregation node can aggregate outputs from multiple branches, facilitating unified configuration for downstream nodes.

The variable aggregation node reads the first non-null value from multiple branches for use by downstream nodes.

**Table 5-47 Variable Aggregation Node Configuration**

| Configuration Type | Parameter Name | Description |
|----------|----------|----------|
| Parameter Config | Output Parameters | Name fixed as Group1, increments as Group2, Group3, etc. |
| Aggregation Strategy | - | Currently only supports "Return first non-null value in each group." |
| Aggregation Group | - | Default one group Group1. All variable types in a group must be the same. |

### 5.12.3 Knowledge Retrieval

The knowledge retrieval node is the workflow's "external knowledge storage." It uses RAG (Retrieval-Augmented Generation) technology to match relevant fragments from pre-uploaded knowledge bases based on user intent.

#### Core Function

Solves the problem of large models not being able to master private domain data, real-time information, and being prone to hallucinations. Data flow: Input user question > Retrieve matching documents > Output retrieval information.

#### Configure Knowledge Retrieval Node

##### Input Parameters

Fixed one input parameter named query, type string. Supports "Reference" and "Input" types.

##### Knowledge Base

You can select one or more knowledge bases. Supports configuring label-based retrieval, retrieval strategy, relevance threshold, topk recall quantity, etc.

Default supports associating 3 knowledge bases, expandable to 10.

##### Retrieval Strategy

- Semantic Retrieval: Uses vector retrieval technology.
- Keyword Retrieval: Uses inverted index retrieval technology.
- Hybrid Retrieval: Uses both vector and keyword retrieval strategies.

##### FAQ Direct Output Threshold

When FAQ type documents are uploaded, FAQ retrieval results exceeding the threshold will be returned directly without document retrieval. Range 0-1.

##### Relevance Threshold

Search results with scores below the relevance threshold will be filtered. Range 0-1.

##### topk Recall Quantity

Maximum number of slices recalled from the knowledge base. Range 1-50.

##### Output Parameters

The output is an object array named output_list, representing all knowledge slices meeting retrieval requirements. Each object has four properties:
- document_name: Knowledge document name where the slice is located.
- subtitle: Knowledge slice subtitle.
- content: Knowledge slice content.
- score: Knowledge slice match score, sorted from high to low.

## 5.13 Node Configuration Management

### 5.13.1 Manage Intent Packages

Intent packages are collections of intents used by the advanced intent recognition node. They support importing via Excel files.

#### Create Intent Package

Intent packages can be created through the "Development Center > Development Configuration > Node Configuration Management" interface.

Supports single and multiple intent packages. For multiple intent packages, each Sheet corresponds to one intent package.

### 5.13.2 Message Templates

Message templates are predefined standardized JSON message structures. You can create commonly used message content as templates.

Message templates are currently mainly used with exception nodes in workflows, enabling quick reference to these templates in exception nodes.

**Table 5-50 Create Message Parameters**

| Parameter Name | Description |
|----------|----------|
| Message Name | Unique identifier name for the template. |
| Message Category | Template usage category. Exception: Standardized error message output for workflow exception nodes. Custom: Reserved, not yet available. |
| Visibility Scope | Tenant-wide, Current space, Personal only. |
| Message Body | Must be valid JSON format. |

### 5.13.3 Object Management

Object management introduces how to create, edit, and delete objects. You can create object templates and reference them in related nodes.

**Table 5-52 New Object Parameters**

| Parameter | Description |
|------|------|
| Object Name | Custom name, 2-64 characters. |
| Object Variables | Include variable name, variable type, and description (optional). Supports String, File, Integer, Number, Boolean, Object, Array types. Object supports up to 5 levels of nesting. |


# 6 Developing Multi-Agent Applications

## 6.1 Multi-Agent Application Introduction

Single-agent applications created in OpenJiuwen can handle basic tasks, but when processing complex tasks, they require detailed and lengthy prompts, and the addition of various plugins, knowledge bases, MCP services, etc., which increases debugging complexity. In single-agent applications, any change may affect the overall functionality, causing the processing results to deviate significantly from expected outcomes when users handle actual tasks.

To address this issue, OpenJiuwen provides multi-agent applications. Multi-agent applications have the following advantages:
- Multi-agent applications can flexibly use various workflows to complete user tasks, supporting jumps between different workflows based on user intent.
- Multi-agent applications support model automatic control mode, further improving the efficiency and accuracy of task processing.

#### Applicable Scenarios

Suitable for scenarios that require multi-task processing. For example, in the financial domain, an application implements an intelligent investment advisory system with multiple complex capabilities such as risk assessment, portfolio optimization, and research report analysis.

#### Advantages

Supports complex user intent recognition and understanding, with master-slave models flexibly and efficiently achieving sub-capability coordination. It supports 3 levels of organizational nesting, i.e., multi-agent -> multi-agent -> workflow.

#### Differences Between Single-Agent and Multi-Agent in Functionality and Application Scenarios

Single-agent: Relies on models and can use plugins, workflows, knowledge bases, MCP services, and other tools to let the model autonomously plan and use different tools to complete specified tasks.

Multi-agent: Can configure multiple workflows, focusing on selecting and jumping between different workflows based on customer intent.

## 6.2 Creating a Multi-Agent Application

Multi-agent applications allow users to combine multiple agent applications or workflow applications and orchestrate them according to preset modes.

#### Prerequisites

- Published workflows.
- The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

#### Creating a Multi-Agent Application

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Agent Management".

Step 3 Select the "Multi-Agent" tab and click "Create Multi-Agent".

Step 4 On the "Create Multi-Agent" page, configure the basic information. For specific parameter descriptions, please refer to Table 6-1.

**Table 6-1 Basic Information Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Name | The name of the multi-agent application. Composed of 2~64 characters, including Chinese, English, numbers, underscores, hyphens, and spaces. Cannot start or end with a space. | Intelligent Outbound Call |
| Description | Description information of the multi-agent. Composed of 1~256 characters. | Intelligent Outbound Call |
| Multi-Agent Icon | The system default multi-agent application icon. You can click to auto-generate an icon, or customize the icon. | 1. Move the mouse over the system default icon and left-click. 2. Upload a prepared application icon. Supports jpg, jpeg, png, gif format images, no larger than 200KB. |

Step 5 Click "Create Now".

After creation, you will enter the "Multi-Agent Configuration" page, which initially has only one "Multi-Agent Controller" node. The created multi-agent application is displayed in the multi-agent application card list.

Step 6 Set global configuration.

On the upper right of the "Multi-Agent Configuration" page, click "Global Configuration".

Global configuration can configure input parameters and global variables, which can be used as input parameters for workflows.

**Table 6-2 Global Configuration Parameter Description**

| Parameter | Description |
|------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Input Parameters | Input parameters passed to the workflow, and their values cannot be modified. Click to add input parameters. Parameter name: Composed of 1~64 characters, including letters, numbers, and underscores, cannot start with a number. Type: Supports String, Integer, Number, Boolean. Default is String. Description: Composed of 0~256 characters. Required: Uncheck as needed. Checked by default. |
| Global Variables | Input parameters passed to the workflow. If the workflow has output parameters with the same name and type, the value will be overwritten. Click to add global variables. Parameter name: Composed of 1~64 characters, including letters, numbers, and underscores, cannot start with a number. Type: Supports String, Integer, Number, Boolean. Default is String. Description: Composed of 1~256 characters. |

Step 7 Configure the Multi-Agent Controller.

Click the "Multi-Agent Controller" card, and configure parameter information in the popup page. For Multi-Agent Controller parameter descriptions, please refer to Table 6-3.

**Table 6-3 Multi-Agent Controller Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Model Configuration (Optional) | At least one of "Model Configuration" and "Intent Recognition" must be filled in. If the intent recognition workflow does not return a valid intent, the selected model is used for intent recognition. Select the model service used by this multi-agent application in the dropdown. | DeepSeek-V3 |
| Sub-workflow Execution Logic Prompt | The prompt for executing sub-workflows. This prompt is fed back to the LLM, which recognizes it and executes the corresponding sub-workflow. It is equivalent to a role setting, assisting the agent in selecting the appropriate sub-workflow to execute tasks. | Keep default |
| Intent Recognition (Optional) | At least one of "Model Configuration" and "Intent Recognition" must be filled in. The intent recognition workflow is called first. The intent recognition capability of this multi-agent application. If not configured, the model decides which workflow to execute. If configured, the configured workflow application is used for decision-making to execute the corresponding workflow. | - |
| Sub-Agent | Select the corresponding workflow. On the right side of the sub-agent, click to add workflows and multi-agents. Workflow: Supports up to 30 sub-workflows. After adding a workflow, set the execution action of the sub-workflow. Supported execution actions are as follows: Continue: Continue executing other sub-workflows based on the execution result of this workflow. Terminate: End the task by calling the end workflow based on the execution result of this workflow. Wait for Input: Execute the task after the user inputs a question. Multi-Agent: In a multi-agent application, one multi-agent application can be used within another multi-agent application, achieving multi-level control. Currently supports 2-level control. Supports up to 30 agents. | - |
| Global Intent | During interaction with the agent, users may have some common intents unrelated to business, such as "not interested", "not the person", etc. These intents can be configured as global intents, and corresponding actions can be configured. Supported processing methods: Direct Answer: Configure a text to output to the user. Flow Jump: Associate a workflow to complete the action needed for the corresponding intent. Supported execution actions: Continue, Terminate, Wait for Input. | - |
| Start Workflow (Optional) | After the start workflow is configured, regardless of how the global intent changes the execution order, the multi-agent application will start with this workflow. | - |
| Default Workflow (Optional) | When the user's question does not match any sub-workflow business intent, the current default workflow is executed. | - |
| End Workflow (Optional) | After the end workflow is configured, regardless of how the global intent changes the execution order, the multi-agent application will end with this workflow. | - |
| Max Conversation History Rounds | Set the number of historical conversations. Select N to record the most recent N conversation entries. For example, select 10 to record the most recent 10 conversation entries. Value range 0~100, default value 10. | 10 |
| Max Jump Count | During multi-agent operation, based on user intent, it jumps between multiple workflows. To prevent infinite looping between workflows, this parameter limits the maximum number of jumps. Only jumps between business workflows are counted; start and end workflows are not counted. Value range 0~30, default value 9. | 9 |

Step 8 Click "OK".

After setting, enter the "Multi-Agent Configuration" page. On the "Multi-Agent Configuration" page, the Multi-Agent Controller and added workflows, agents, and corresponding workflows are displayed. Click a workflow card to customize the intent name and intent description.

#### Related Operations

**Table 6-4 Canvas Operations**

| Icon | Description |
|------|------|
| Show/Hide Thumbnail | - |
| View Canvas Nodes | - |
| Zoom Out/In Canvas Content | - |
| / | Global Collapse/Expand Nodes |
| Center Canvas Content | - |
| Optimize Canvas Content Layout | - |

**Table 6-5 Related Operations**

| Operation | Description |
|------|------|
| Edit Multi-Agent Application Information | Click the multi-agent application card to be edited, enter the "Multi-Agent Configuration" page, and click to the right of the name to edit the name, description, and icon of the multi-agent application. |
| Channel Management | Move the mouse over the published multi-agent application card, click "Channel Management" to enter the channel management page. |
| Copy Multi-Agent Application to Other Spaces | Move the mouse over the multi-agent application card to be copied, click "Copy", on the "Copy To" page, select the space to copy to, and click "OK". |
| Get Multi-Agent Application Call Path | Move the mouse over the multi-agent application card for which you want to get the call path, click "Call Path", and on the "Call Path" page, click "Copy Path". |
| Copy Multi-Agent Application ID | Move the mouse over the multi-agent application card whose ID you want to copy, and click "Copy ID". |
| Delete Multi-Agent Application | Note: If the application has been listed, the user cannot delete it directly. The application must be manually delisted before it can be deleted on the application management page. Move the mouse over the multi-agent application card to be deleted, and click "More > Delete". |

## 6.3 Debugging Multi-Agent Applications

Developers can directly converse with the multi-agent after creation, observe its execution process and response effects in real time, and optimize and adjust the configuration as needed.

#### Prerequisites

- A multi-agent application has been created.
- The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

#### Debugging Multi-Agent Applications

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Agent Management".

Step 3 Select the "Multi-Agent" tab and click the multi-agent application card to be debugged.

Step 4 On the "Multi-Agent Configuration" page, click "Trial Run".

Step 5 On the "Trial Run Configuration" page, enter the trial run configuration and click "Start Run".

The "Run Configuration" page is displayed only when the multi-agent application has input parameters set in the global configuration or when the start node of the workflow application used has input parameters set. Supports manual input of initial parameters, and also supports importing initial parameters.

Step 6 On the "Trial Run" page, enter conversation content to converse with the agent, and optimize the "Multi-Agent Controller" parameter configuration based on the execution process and response results.

Text input: Enter the conversation in the input box and press Enter or click to view the application response results.

Click to clear the current session content and start a new session.

After the trial run conversation ends, manual annotation, like, and dislike of generated content are supported.

Step 7 During the trial run, you can click the upper right corner to view debugging results, including run results and call details.

- Run results: The run results show the application's execution start time, end time, run time, and other information, as well as input and output information.
- Call details: During multi-agent application conversations, the call chain displays detailed information of the controller or workflow, including the running controller or workflow, controller or workflow duration, controller or workflow input and output information, etc. Click "View Sub-workflow Call Chain" to view detailed information of each node in the workflow.

## 6.4 Publishing Multi-Agent Applications as APIs

After a successful trial run of a multi-agent application, it can be published for subsequent use.

#### Prerequisites

- A multi-agent application has been created.
- The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

#### Publishing Multi-Agent Applications as APIs

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Agent Management".

Step 3 Select the "Multi-Agent" tab and click the multi-agent application card to be published.

Step 4 On the "Multi-Agent Configuration" page, click "Submit Version".

For already published multi-agent applications, after modification and re-publishing, it shows "Update Version".

Step 5 On the "Submit Version" page, configure the publishing information. For specific parameter descriptions, please refer to Table 6-6.

**Table 6-6 Publishing Multi-Agent Parameter Description**

| Parameter | Description |
|------|------|
| Version Name | The system auto-generates a version name with a date, starting with v. You can also customize the version name, composed of 1~32 characters. |
| Version Description (Optional) | Description information of the multi-agent. Composed of 0~256 characters. |

Step 6 Click "OK".

After publishing, "Submitted" is displayed on the card in the "Multi-Agent" page.

Step 7 (Optional) On the "Version Submission" page, click "Share" to enter the "Channel Management" page. In "Channel Management", click "View API" to view the API call interface information.

#### Related Operations

**Table 6-7 Multi-Agent Application Related Operations**

| Operation | Description |
|------|------|
| View Version History | Click to view version history. In the version history, the following operations can be performed. To the right of "Version ID", click to copy the published version ID. The version ID is used as the value of the "version" parameter when the multi-agent application is called via API. Click "Restore Version" to restore to this version. Note: After restoration, the current workflow configuration will no longer be retained, please operate with caution. Click "Delete" to delete this published version. |

## 6.5 Calling Multi-Agent Applications via API

OpenJiuwen's API calls are a powerful tool in application development, helping users quickly integrate functions and services, while supporting interaction with other systems or services to enhance application performance and user experience.

Advantages of calling multi-agents via API:
- Improve development efficiency: API interfaces enable different applications to interact efficiently, significantly saving human and material costs for data transmission and processing.
- Expand application scope: Through the use of API interfaces, interaction between different systems, platforms, and services can be achieved.

#### Prerequisites

- Before calling the application, ensure the application has been published. For details, please refer to Publishing Multi-Agent Applications as APIs.
- The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

#### Obtaining Application ID and Call Path

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Agent Management".

Step 3 Select the "Multi-Agent" tab and move the mouse over the multi-agent application card.

Step 4 Click "Copy ID" to get the current application ID. Please save it for filling in the agent_id field when calling the Agent application interface.

Step 5 Click "Call Path", and in the popup "Call Path" page, click "Copy Path" to get the call path.

Where "bbd49397-fe4f-4ce6-b174-f900e5efbd5d" is a randomly generated string that can be replaced with another string when in use. The string length is 1~64 characters, supporting English letters, numbers, hyphens, and underscores. When the multi-agent application is called via API, it is the value of "conversation_id".

#### Using API to Call Multi-Agent Applications

For operations on using API to call multi-agent applications, please refer to "Agent Development Platform 26.2.1 API Reference" in the "Calling Agent Applications" chapter.

## 6.6 Importing and Exporting Multi-Agent Applications

OpenJiuwen supports exporting multi-agent applications from one environment and importing them into another, eliminating the need for users to rebuild them and quickly completing cross-environment construction or reuse of multi-agent applications.

Business scenarios for use:
- Export multi-agents from the test environment and deploy them in the production environment.
- Migrate multi-agent applications between different development environments.
- Download multi-agent applications to local for code archiving.
- Provide as templates for reuse by other customers.

#### Prerequisites

The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

#### Importing Multi-Agent Applications

A JSONL format file of a multi-agent application exported from another OpenJiuwen environment is available.

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Agent Management".

Step 3 Select the "Multi-Agent" tab and click "Import".

Step 4 On the "Import" page, click "Select File", select the locally prepared file, check the content to import, and click "Import".

Supports JSONL format files, up to 128MB.

Note:
- If resources associated with the application (such as plugins, MCP, knowledge bases, workflows, agents) fail to import, the application will still be imported normally, but these resources will not be imported.
- If the import fails, you can view the reason in the operation column.
- If there are resources in the imported agent that have not been configured with authentication, the system will mark "Not Configured Authentication". After clicking "Configure Authentication" in the operation column, you can operate in the configuration authentication window.

After import, the imported multi-agent application is displayed in the multi-agent application card list. If the name is the same, the original multi-agent application will be overwritten.

#### Exporting Multi-Agent Applications

A multi-agent application has been created or imported.

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Agent Management".

Step 3 Select the "Multi-Agent" tab, click "Export", check the checkbox to the left of the multi-agent application to be exported, and click "Export"; or move the mouse over the target agent and click "More > Export".

Step 4 Click "Download", and the agent is downloaded as a JSONL format file to the local machine.

Note:
- If resources associated with the application (such as plugins, MCP, knowledge bases, workflows, agents) fail to export, the exported file will not contain the corresponding resources.
- If the export fails, you can view the reason in the operation column.


# 7 Component Library

## 7.1 Plugins

### 7.1.1 Plugin Introduction

#### What are Plugins

In an Agent, plugins are a series of tools for the Large Language Model (LLM) to interact with the external world.

Although LLMs have powerful natural language processing and reasoning capabilities, they are essentially static systems based on training data and have two major limitations:

- Information lag: Unable to obtain real-time information after the training cutoff date.
- Lack of action capability: Unable to directly interact with software or hardware systems in the real world (such as reading/writing databases, sending requests).

The introduction of plugins gives Agents the ability to retrieve real-time information and execute external tasks, making them a key module in the evolution of Agents from "conversation systems" to "task-solving systems".

The OpenJiuwen Agent Development Platform provides a rich set of preset plugins, including weather query, hot search query, document generation, travel and tourism, etc. For example, adding a weather query plugin to your Agent can give it the ability to query real-time weather.

When official plugins cannot meet specific business needs, you can create custom plugins.

#### Plugin Classification and Forms

The OpenJiuwen Agent Development Platform provides rich plugin resources. In addition to preset official plugins, the service supports user-defined plugins, which can introduce API and function code capabilities into Agents through the plugin form.

**Table 7-1** Plugin Classification and Forms

| Plugin Classification | Description |
|---------|------|
| Official Preset Plugins | Official plugins listed by the OpenJiuwen Agent Development Platform in the "Asset Marketplace", provided with technical support and maintenance by OpenJiuwen. Official preset plugins are divided into two categories: no authentication required and authentication required:<br>- No authentication required: Can be used directly by adding the plugin to the Agent.<br>- Authentication required: Can be used directly after filling in API Key authentication information. |
| Custom-API Type Plugins | API type plugins encapsulate existing RESTful APIs (HTTP/HTTPS interfaces) as tools callable by Agents. They allow the Agent to translate understood instructions into actual API requests, directly calling external systems to complete tasks.<br>- **Running location**: The actual business logic runs on an external API server (such as an enterprise's backend server, third-party functional platform). The Agent acts as a client to send requests and receive API responses.<br>- **Applicable scenarios**<br>  - Data retrieval: Obtain real-time data from external databases or services (such as weather query, web search, news query).<br>  - State change: Execute submission and change operations in external systems.<br>  - Complex business logic processing: Utilize existing mature backend services to handle large business processes. |

#### Plugins and Tools

In the OpenJiuwen Agent Development Platform, understanding the subordinate relationship between plugins and tools is a prerequisite for successfully creating plugins. The "Text Recognition" plugin below can help with intuitive understanding.

**Table 7-2** Text Recognition Plugin Example

| Plugin Name | Tool Name | API Interface Address |
|---------|---------|------------|
| Text Recognition Plugin | General Text Recognition | https://{endpoint}/v2/{project_id}/ocr/general-text |
| | General Table Recognition | https://{endpoint}/v2/{project_id}/ocr/general-table |
| | Handwriting Recognition | https://{endpoint}/v2/{project_id}/ocr/handwriting |

- **Plugin**: A functional collection that integrates one or more tools. It defines the basic attributes shared by these tools (such as service domain, authentication method).
- **Tool**: The specific execution unit within a plugin. Each tool corresponds to an independent function and is responsible for completing a specific single task.

The OpenJiuwen Agent Development Platform supports the development and creation of custom plugins. In the configuration rules, tools within the same plugin must have similar functionality.

Taking Table 7-2 as an example, https://{endpoint}/v2/{project_id}/ocr is the root of all interfaces, defining the plugin's connection target (composed of service domain + base URL); suffixes like /general-text are each tool's unique "path", distinguishing different capabilities within the plugin.

#### Figure 7-1 API and Plugin Relationship Example

At the execution level, the Agent does not directly "run a plugin" but calls a specific tool within the plugin. When the Agent needs to do a "extract text from table image" task, it locates the "Text Recognition Plugin" and precisely calls the "General Table Recognition Tool" within it, which essentially sends a request to the .../ocr/general-table interface.

#### Figure 7-2 Plugin and Tool Relationship Example

### 7.1.2 Example: Creating a Web Search Plugin

This example introduces how to create a web search plugin through the OpenJiuwen Agent Development Platform, debug and publish the plugin, and finally apply it to an Agent.

#### Constraints and Limitations

Before using this example, ensure the network is connected to the public internet to properly call the Huawei Cloud General Text Recognition API.

#### Preparing the Web Search API

This example uses the web search API to implement web search functionality. The API interface call example is as follows. Please create an API Key in advance and replace <AppBuilder API Key> in the code below with the obtained API Key.

```bash
# Note: Please replace <AppBuilder API Key> with the actual API Key obtained when preparing the web search API
curl --location --request POST 'https://qianfan.baidubce.com/v2/ai_search/web_search' \
--header 'Authorization: Bearer <AppBuilder API Key>' \
--header 'Content-Type: application/json' \
--data-raw '{
    "messages": [
        {
            "role": "user",
            "content": "浠€涔堟槸Agent"
        }
    ]
}'
```

#### Step 1: Create Plugin

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. In the left navigation bar, select "Development Center > Component Library", and in the "Plugins" tab, click "Create Plugin" in the upper right corner of the page.

3. Select the "API Type" plugin, and then configure the plugin information according to the following steps.

**Table 7-3** Basic Information

| Parameter | Filling Instructions |
|-----|---------|
| Import and Parse | Not used |
| Plugin Icon | Use default. |
| Name | Fill in "Web Search". |
| Description | Fill in "Obtain real-time internet information through search engines, including news, encyclopedia, web page content, etc.". |
| Visible Only to Me | Off |

4. Click "Next", and in the "Configuration Information" step, configure the plugin information. Please refer to Table 7-4 for configuration.

**Table 7-4** Configuration Information

| Parameter | Filling Instructions |
|-----|---------|
| Protocol | Select "https". |
| Service Domain | Fill in "qianfan.baidubce.com". |
| Base URL | Fill in "/v2/ai_search", note there is only one /. |

| Parameter | Filling Instructions |
|-----|---------|
| Authentication | Select "API Key". |
| Key Location | Select "Header". |
| Parameter List | Add a parameter, parameter name fill in "Authorization", parameter value in Bearer <AppBuilder API Key> format, replace <AppBuilder API Key> with the API Key obtained when preparing the web search API. |

5. After configuration, click "OK". The platform will automatically jump to the tool information page. Please refer to Step 2 Create Tool to add tools for the plugin.

------

#### Step 2: Create Tool

1. On the "Tool Information" page, click "Create Tool". Please refer to Table 7-5 for tool configuration.

**Table 7-5** Tool Configuration

| Parameter | Parameter Description |
|-----|---------|
| Display Name | Fill in "Web Search". |
| Name | Fill in "web_search". |
| Description | Fill in "Obtain real-time internet information through search engines, including news, encyclopedia, web page content, etc.". |

| Parameter | Parameter Description |
|-----|---------|
| Tool URL | Use the platform's auto-parse feature, no need to manually fill in parameters. |
| Request Parameters | Click "Import and Parse", enter the interface example from preparing the web search API, and click "OK". Note that <AppBuilder API Key> in the example should be replaced in advance. |
| Request Header | In the Request Header, set the identified parameters to "Required". |
| Request Body | The Request Body needs to be set referring to Figure 7-8 (if the auto-parse result does not match the figure, please set according to the figure). |

| Parameter | Parameter Description |
|-----|---------|
| Response Parameters | In the parameter list below, add a row of parameters. Parameter name is "references", description fill in "output information", parameter type select "Array<String>". |

2. After configuration, click "OK". For subsequent debugging steps, please refer to Step 3 Debug and Publish Plugin.

------

#### Step 3: Debug and Publish Plugin

After the tool is created, a tool with "Pending Debug" status will be added to the tool list. The tool must be debugged before the corresponding plugin can be published for use.

1. In the tool list, click the "Debug" button, enter a question, and click "Start Debug".

2. After successful debugging, the tool status changes to "Success". You can then click "Publish" in the upper right corner to publish the plugin.

------

#### Step 4: Using the Plugin in a Single Agent

After the plugin is created, it is merely a static asset. To make it truly valuable, it needs to be mounted on an agent with thinking capabilities.

In this section, you will create the most basic single-agent application. You don't need complex logic orchestration鈥攋ust simple configuration can give the agent web search capabilities, experiencing how it breaks through the timeliness limitations of model training data and autonomously obtains the latest information from the internet.

1. Return to the OpenJiuwen Agent Development Platform overview page and click "Create Agent".

2. On the create application page, select "Single Agent". Fill in the name and description as "Web Search Agent", and click "Create Now".

3. On the "Single Agent Configuration" page, configure according to the following information.

**Table 7-6** Single Agent Configuration Information

| Parameter | Filling Instructions |
|-----|---------|
| Prompt | After entering "web search", use the AI feature to intelligently optimize the prompt and fill in the optimized prompt. |

| Parameter | Filling Instructions |
|-----|---------|
| Model | In the model configuration area, select an available LLM. |

| Parameter | Filling Instructions |
|-----|---------|
| Plugin | In the middle of the configuration page, add a web search plugin. |

| Parameter | Filling Instructions |
|-----|---------|
| Other Parameters | Use defaults, no settings. |

4. On the right side of the configuration page, you can debug the agent.

------

### 7.1.3 Creating Plugins

#### 7.1.3.1 Creating Plugins Based on API

In the OpenJiuwen Agent Development Platform, when the official plugin marketplace cannot meet specific business needs, developers need to create plugins independently.

##### API Form Plugin

API type plugins encapsulate existing RESTful APIs (HTTP/HTTPS interfaces) as tools callable by Agents. They do not carry business logic but "translate" the LLM's natural language instructions into standard API requests and send them to external systems.

**Typical Applicable Scenarios:**

- Data retrieval: such as weather query, web search, news query.
- State change: such as sending messages, triggering task creation.
- Complex business logic processing: After-sales return/exchange processing (API backend verifies whether the product meets return conditions, whether exchange inventory is sufficient, generates cancellation link, sends notification messages...).

**Inapplicable Scenarios:** Pure logical computation (simple numerical calculation), simple string processing (high latency and waste of network resources).

##### Plugin Call Chain

1. User input: Help me check the status of order 12345.
2. Agent analysis: Hits plugin get_order_status.
3. Parameter generation: The model in the Agent generates structured parameters { "order_id": "12345" }.
4. Request construction: The Agent assembles the API plugin request.
5. Network interaction: The Agent sends a GET /api/orders/12345 request to the API server.
6. Response parsing: The server returns JSON data, the Agent cleans it and injects it into the model context.
7. Final reply: The model generates natural language based on the data: "Order 12345 current status is shipped...".

##### Constraints and Limitations

- A single plugin supports up to 30 tools.
- Before using this example, ensure the network is connected to the public internet to properly call the Huawei Cloud General Text Recognition API.
- The base URL in the example contains the `{project_id}` variable, which requires public internet connectivity to obtain. Please log in to the "My Credentials" page to query the project ID corresponding to the "North China-Beijing 4" region.

##### Step 1: Create Plugin

During the plugin creation process, the example of "Creating a plugin using the Text Recognition API" will be used for explanation. For Text Recognition API, plugin, and tool descriptions, please refer to Plugin Introduction.

> **Note**
>
> The example uses "Text Recognition Service > General Text Recognition API". Please enable this API in the Text Recognition Service console in advance.

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. In the left navigation bar, select "Development Center > Component Library", and in the "Plugins" tab, click "Create Plugin" in the upper right corner of the page.

3. On the "Create Plugin" page, select "API Type" in the "Plugin Type", and then configure the plugin information according to the following steps.

**Table 7-7** Basic Information

| Parameter | Description | Example |
|-----|-----|-----|
| Import and Parse | To simplify the plugin configuration process, you can use this feature to import a JSON file conforming to the OpenAPI 3.0 specification. The platform will automatically parse the file content and fill in the corresponding configuration parameters, avoiding tedious manual entry and improving configuration efficiency.<br><br>**Note**<br>- Authentication information: The platform currently cannot automatically parse authentication configurations. After import, you need to manually add authentication information, otherwise tool calls will fail due to missing authentication.<br>- Specification check: After the configuration file is imported and parsed into tools, it is recommended to check each tool's request parameters and response parameters one by one to ensure they are correctly parsed.<br>- Only GET and POST request methods are supported for import. | This example uses manual creation, not the auto-parse feature. |
| Plugin Icon | Click the default icon button to upload a local image as the plugin's system default icon.<br><br>Supports jpg, jpeg, png formats, no larger than 200KB. | System default icon |
| Name | Used to identify the current plugin, displayed on the "Component Library > Plugins" page.<br><br>**Naming rules**: Name according to the actual functionality of the plugin, which helps the Agent accurately identify and schedule the plugin.<br><br>**Naming requirements**: Can include Chinese, English, numbers, underscores;<br>**Length limit**: 2~64 characters. | Text Recognition |
| Description | Describe the type, functionality, and applicable scenarios of the current plugin. Provides general text recognition capability, which can accurately extract and parse text in images, output structured text results, and adapt to various scenario text recognition needs.<br><br>Needs to be filled in according to the actual functionality of the plugin, which helps the Agent accurately identify and schedule the plugin. | Provides general text recognition capability, which can accurately extract and parse text in images, output structured text results, and adapt to various scenario text recognition needs. |
| Visible Only to Me | When enabled, this plugin becomes private and is only visible to the current logged-in user. Other users cannot view it. This switch cannot be modified after creation. | Not enabled |

4. Click "Next", and in the "Configuration Information" step, configure the plugin information. Please refer to Table 7-8 for configuration.

**Table 7-8** Configuration Information

| Parameter | Description | Example |
|-----|-----|-----|
| Protocol | API service interface communication protocol. | https<br>- https<br>- http |
| Service Domain | The service domain that provides the API service. | Click the "Add Variable" button on the right to add a variable in the service domain. After adding the variable, you can set the parameter description in the variable parameter section.<br><br>Taking the Huawei Cloud General Text Recognition API as an example, https://{endpoint}/v2/{project_id}/ocr/general-text, the {endpoint} in this API represents the service domain. |
| Base URL | The Base URL is the URL root path of the domain (can be understood as the API's common path), default is /. Please adapt according to the actual API interface.<br><br>**Note** You need to click "Add Variable" on the right to add the {project_id} variable. This variable represents the project ID, used to identify resource ownership under a user's specific region. | /v2/{project_id}/ocr<br><br>For example, in the Huawei Cloud Text Recognition Service, different API interfaces all have the same base URL: /v2/{project_id}/ocr<br><br> |
| Authentication | Select whether authentication is needed when calling the API. | - **No authentication**: The API can be publicly accessed without any form of identity verification or authorization.<br>- **API Key**: Provides a unique API Key for authentication when calling the API. The following information needs to be configured for verification: IAM username/password<br>  - **Key Location**: Whether the key is read from the Header (request header) or from the Query (URL parameter).<br>  - **Parameter Name**: The authentication parameter name of the API Key.<br>  - **Parameter Value**: The specific value of the API Key.<br>  - **Access Key ID/Secret**<br>      - Access Key ID: Access key ID.<br>      - Secret Access Key: The key used in combination with the access key ID. |

5. After configuration, click "OK". The platform will automatically jump to the tool information page. Please refer to Step 2 Create Tool to add tools for the plugin.

------

##### Step 2: Create Tool

To understand the relationship between plugins and tools, please refer to Plugin Introduction.

1. On the "Tool Information" page, click "Create Tool". Please refer to Table 7-9 for configuration.

**Table 7-9** Tool Basic Information Configuration

| Parameter | Description | Example |
|-----|-----|-----|
| Display Name | Used to identify the current tool. Naming rules: Name according to the actual functionality of the tool, which helps the Agent accurately identify and schedule the plugin. | General Text Recognition |
| Name | The English name of the tool.<br><br>- **Naming rules**: Name according to the actual functionality of the tool, which helps the Agent accurately identify and schedule the plugin.<br>- **Naming requirements**: Can include uppercase and lowercase letters, numbers, underscores.<br>- **Length limit**: 1~64 characters. | RecognizeGeneralText |
| Description | Describe the type, functionality, and applicable scenarios of the current tool. Recognizes text information on images and returns recognized text and coordinates in JSON format.<br><br>Needs to be filled in according to the actual functionality of the tool, which helps the Agent accurately identify and schedule the plugin. | Recognizes text information on images and returns recognized text and coordinates in JSON format. |

2. Refer to the table below to continue configuring tool URL, request parameters, response parameters, and other information.

**Table 7-10** Tool Configuration

| Parameter | Description | Example |
|-----|-----|-----|
| Import and Parse | AI auto-parses API request parameters. Enter the API's cURL or openAPI raw content. | This example uses manual creation, not the auto-parse feature. |
| Tool URL | The request method for requesting the API, supports POST or GET. | POST |
| Tool path | The tool path is the suffix fragment in the complete API call address used to locate specific functionality. | /general-text |
| Request Parameter Wrapping | Parameters meet the requirement of some interfaces that force input parameters to be arrays, changing object type (Object) parameters to arrays (Array), i.e., putting input parameters in a pair of square brackets [].<br><br>- Original parameter list: {"a":"string", "b":1}.<br>- After enabling: [{"a":"string", "b":1}]. | Not enabled |
| Request Header | One of the components of an HTTP request message. The request header is responsible for notifying the server about client request information.<br><br>Click the "Add" button to add new parameters. For parameter configuration instructions, please refer to Table 7-11. | Add two request header parameters and set them as required:<br>- X-Auth-Token: For obtaining the code, please refer to the appendix.<br>- Content-Type: Value is application/json |

| Parameter | Description | Example |
|-----|-----|-----|
| Request Body | One of the components of an HTTP request message. The request body presents the data sent to the server. Base64 encoding.<br><br>Parameters can be added in two ways: Using base64 encoding requires filling in "image".<br><br>- Click the "Add" button to add new parameters. For parameter configuration instructions, please refer to Table 7-11.<br>- Click the "Import" button, enter parameter content in JSON or JSONSchema format. Click "OK", and the platform will automatically parse and complete the import.<br><br>**Note**<br>- The platform does not support importing parameters with "Chinese names". If you need to set "Chinese name" parameters, please manually configure them after import.<br>- This operation will overwrite the original parameter configuration, please operate with caution. | Here use "url" and set as required, parameter name is "image".<br><br> |
| Query Parameters | One of the components of an HTTP request message, used to pass additional parameter information to the server. These parameters usually appear as key-value pairs and are appended after the URL path, separated by ?.<br><br>For example, in /items?id=123, the query parameter is ID, and the value is 123.<br><br>Click the "Add" button to add new parameters. For parameter configuration instructions, please refer to Table 7-11. | Not applicable for the Text Recognition plugin |
| Path Parameters | Automatically parses path parameters contained in the tool path. The tool path supports variable parameter configuration.<br><br>For example: /weather/weatherInfo/{path_1}/{path_2}. | Not applicable for the Text Recognition plugin |
| Response Parameters | Streaming: When the plugin calls a model with thinking effects (like DeepSeek) or a time-consuming interface, enabling this feature allows the API to stream responses as they are received, rather than waiting for the API to completely obtain results before displaying them all at once. | Not enabled |
| Parameter Wrapping | Meets the requirement of subsequent plugin usage (such as batch reading data in workflow loop nodes) that inputs must be arrays, changing object type (Object) responses to arrays (Array), i.e., putting output parameters in a pair of square brackets [].<br><br>- Original parameter list: {"a":"string", "b":1}.<br>- After enabling: [{"a":"string", "b":1}]. | Not enabled |
| Parameter List | Response parameter list, fill in according to the actual response parameter structure of the API.<br><br>Click the "Import" button, enter parameter content in JSON or JSONSchema format. Click "OK", and the platform will automatically parse and complete the import. This operation will overwrite the original parameter configuration, please operate with caution. | Add a response parameter, name is "result", and set as required.<br><br> |

**Table 7-11** Parameter Configuration Instructions

| Parameter | Description |
|-----|-----|
| Parameter Name | Set the name of the request parameter. The parameter name serves as the basis for the LLM to parse the parameter meaning.<br><br>**Naming rules**: Only supports letters, numbers, underscores, or hyphens. |
| Chinese Name | Set the Chinese name of the parameter for users to understand the parameter meaning. |
| Parameter Type | Set the data type of the request parameter.<br><br>**Note** In the request header (Header), all parameter values must be string type and cannot be set to other types. |
| Default Value | Set the default value of the parameter, used when the parameter is not provided. |
| Description | Set detailed description information of the request parameter, accurately explaining the meaning, purpose, and format requirements of the parameter to improve the accuracy of the LLM's parameter identification and extraction. |
| Parameter Validation | Set whether the current parameter needs validation.<br><br>**Validation rules**:<br>- Parameter name: The parameter name to be validated.<br>- Validation type:<br>  - Maximum character length<br>  - Enum values<br>  - Date/time<br>- Validation rules: Can set specified format and custom format.<br>  - Specified format: Select system preset standard validation rules. When the validation type is date/time, specified format is supported.<br>  - Custom format: Customize validation rules according to actual needs. |
| Required | Set whether this parameter is required. |

3. Click the "Tool Test" button, enter parameter values, and click "Start Test" to check the test results.

4. Ensure the output meets expectations, then click the "Auto Parse" button in the lower right corner of the tool test page. The system will automatically generate response parameters.
5. After tool debugging is complete, click "OK".

After the tool is created, you can view the completed tool in the tool list.

------

##### Related Operations

After the tool is created, you can view each tool's debug status, agent reference count, and workflow reference count in the tool list. You can perform the operations shown in Table 7-12.


**Table 7-12** Related Operations

| Operation | Description |
|-----|-----|
| Edit | In the tool information list, find the tool to be edited, and click "Edit" in the operation column of that tool to edit the tool information. |
| Debug | In the tool information list, find the tool to be debugged, and click "Debug" in the operation column of that tool. In the expanded dialog, enter parameter information to debug the tool. |
| Delete | In the tool information list, find the tool to be deleted, and click "Delete" in the operation column of that tool to delete the tool. |
| View Details | In the tool information list, find the tool for which you want to view details, and click the tool name to view the tool's detailed information. |


##### OpenAPI 3.0 Configuration File Example Explanation

###### OpenAPI 3.0 Introduction

OpenAPI 3.0 (formerly Swagger) is a standard specification format for describing RESTful APIs. It defines API request paths, parameters, request bodies, response structures, and other information in a structured way, enabling both machines and humans to quickly understand the API's capabilities and usage.

A standard OpenAPI 3.0 document typically contains the following core modules:

**Table 7-13** OpenAPI 3.0 Core Modules

| Core Module | Description |
|---------|-----|
| openapi | Declares the OpenAPI specification version used, such as 3.0.1. |
| info | Basic metadata of the API, including title, description, and version number. |
| servers | API server address list, defining the base URL for requests. |
| paths | The core part, defining all available API paths and their supported HTTP methods (GET, POST, etc.). Each method corresponds to a specific interface (tool). |
| components (not used in this example) | Reusable data models, parameters, response bodies, etc., to reduce repetitive descriptions. |
| security (not used in this example) | Global or interface-level authentication method declaration, such as API Key. |

When creating an Agent plugin, the platform parses the imported OpenAPI 3.0 configuration file:
- info.title: Will be used as the plugin name.
- info.description: Will be used as the plugin description.
- paths: Each interface under paths will be parsed as a tool in the plugin.

###### Example

This example provides a "User Management API" configuration file conforming to the OpenAPI 3.0 specification, aiming to demonstrate how to define Agent plugins by writing standardized OpenAPI 3.0 specification files.

Through detailed analysis of the file structure (including basic information, server addresses, interface paths) and specific interface operations (such as querying user lists, creating new users), this example helps users understand the mapping relationship between OpenAPI fields and platform plugin configuration items (such as plugin names, tool definitions, parameter constraints). You can refer to this example to learn how to correctly write configuration files to quickly import existing RESTful APIs into the platform and parse them into available tools.

```yaml
openapi: 3.0.1
info:
  title: 鐢ㄦ埛绠＄悊 API
  description: 杩欐槸涓€涓畝鍗曠殑鐢ㄦ埛绠＄悊 API 绀轰緥
  version: 1.0.0
servers:
  - url: https://api.example.com/v1
    description: 鐢熶骇鏈嶅姟鍣?paths:
  /users:
    get:
      summary: 鑾峰彇鐢ㄦ埛鍒楄〃
      description: 杩斿洖绯荤粺涓殑鐢ㄦ埛鍒楄〃锛屾敮鎸佸垎椤靛拰杩囨护
      operationId: getUsers
      parameters:
        - name: page
          in: query
          description: 椤电爜
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          description: 姣忛〉鏁伴噺
          schema:
            type: integer
            default: 20
        - name: role
          in: query
          description: 鎸夎鑹茶繃婊?          schema:
            type: string
            enum: [admin, user, guest]
      responses:
        '200':
          description: 鎴愬姛杩斿洖鐢ㄦ埛鍒楄〃
          content:
            application/json:
              schema:
                type: object
                properties:
                  total:
                    type: integer
                    description: 鐢ㄦ埛鎬绘暟
                  page:
                    type: integer
                    description: 褰撳墠椤电爜
                  limit:
                    type: integer
                    description: 姣忛〉鏁伴噺
                  data:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                          description: 鐢ㄦ埛ID
                        username:
                          type: string
                          description: 鐢ㄦ埛鍚?                        email:
                          type: string
                          format: email
                          description: 鐢靛瓙閭
                        role:
                          type: string
                          enum: [admin, user, guest]
                          description: 鐢ㄦ埛瑙掕壊
                        createdAt:
                          type: string
                          format: date-time
                          description: 鍒涘缓鏃堕棿
        '400':
          description: 璇锋眰鍙傛暟閿欒
          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                    description: 閿欒鐮?                  message:
                    type: string
                    description: 閿欒淇℃伅
        default:
          description: 鏈嶅姟鍣ㄩ敊璇?          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                    description: 閿欒鐮?                  message:
                    type: string
                    description: 閿欒淇℃伅
    post:
      summary: 鍒涘缓鏂扮敤鎴?      description: 鍒涘缓涓€涓柊鐨勭敤鎴疯处鎴?      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - username
                - email
                - password
              properties:
                username:
                  type: string
                  minLength: 3
                  maxLength: 20
                  description: 鐢ㄦ埛鍚?                email:
                  type: string
                  format: email
                  description: 鐢靛瓙閭
                password:
                  type: string
                  minLength: 6
                  format: password
                  description: 瀵嗙爜
                role:
                  type: string
                  enum: [user, guest]
                  default: user
                  description: 鐢ㄦ埛瑙掕壊
      responses:
        '201':
          description: 鐢ㄦ埛鍒涘缓鎴愬姛
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                    description: 鐢ㄦ埛ID
                  username:
                    type: string
                    description: 鐢ㄦ埛鍚?                  email:
                    type: string
                    format: email
                    description: 鐢靛瓙閭
                  role:
                    type: string
                    enum: [admin, user, guest]
                    description: 鐢ㄦ埛瑙掕壊
                  createdAt:
                    type: string
                    format: date-time
                    description: 鍒涘缓鏃堕棿
        '400':
          description: 璇锋眰鏁版嵁楠岃瘉澶辫触
          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                    description: 閿欒鐮?                  message:
                    type: string
                    description: 閿欒淇℃伅
                  errors:
                    type: array
                    description: 璇︾粏閿欒鍒楄〃
                    items:
                      type: object
                      properties:
                        field:
                          type: string
                          description: 閿欒瀛楁
                        message:
                          type: string
                          description: 閿欒淇℃伅
        '409':
          description: 鐢ㄦ埛宸插瓨鍦?          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                    description: 閿欒鐮?                  message:
                    type: string
                    description: 閿欒淇℃伅
        default:
          description: 鏈嶅姟鍣ㄩ敊璇?          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                    description: 閿欒鐮?                  message:
                    type: string
                    description: 閿欒淇℃伅
```

#### 7.1.3.2 Importing API Plugins via JSON File

OpenJiuwen supports importing API plugins via JSON files. You can directly edit the interfaces, input parameters, output parameters, authentication, and other information defined in the API plugin as a JSON file, and then import it into the platform to create an API form plugin.

This file defines the plugin's basic attributes, backend service connection address, input/output parameter structure, and authentication method. Developers can quickly integrate existing RESTful APIs into the platform as plugins by modifying this file.

> **Recommended to combine with examples**: View Creating a Web Search Plugin and Creating Plugins Based on API for better understanding of the parameters in the JSON file.

##### Prerequisites

The plugin and tool creation operations have been completed. For operation instructions, please refer to Creating Plugins Based on API.

##### Obtaining JSON Example File

The platform requires first creating and publishing an API plugin, then exporting the plugin's JSON configuration file. You can refer to the example: Creating a Web Search Plugin to create a plugin and export the plugin's JSON file.

###### Plugin Basic Information

Defines the display information and unique identifier of the plugin on the platform page.

**Table 7-14** Plugin Basic Information Parameters

| Parameter | Name | Example |
|-----|-----|-----|
| plugin_display_name | Plugin English identifier name | "web_search" |
| plugin_chinese_name | Plugin Chinese name (name displayed in marketplace or orchestration page) | "Web Search Plugin" |
| plugin_desc | Plugin description | "Web Search Plugin" (used for model to understand plugin purpose) |
| icon | Plugin icon | Base64-encoded icon |
| type | Plugin type | "custom" (indicates user-defined plugin) |
| call_mode | Call mode | "api" (core field, identifies this as an HTTP interface call, not a code function) |

###### Service Connection Configuration

Field: request_info. Note that the value of this field is an escaped JSON string. It defines the physical address of the API and the tool list.

###### Interface Contract Definition

This is the most complex part of the configuration file, defining how the plugin assembles parameters and how it handles return values.

- **Input parameter definition (input_schema)** Format: JSON string array.
  This field defines the Header, Body, and Query parameters required for API requests. When editing this field, you must strictly follow JSON escape rules (e.g., " must be written as \"), otherwise the import will fail.
- **Output parameter definition (output_schema)** Format: JSON string array.
  Defines the structure of the API response, helping the Agent extract key information.

###### Authentication Configuration

Field: auth_info

Defines the authentication method when the Agent calls external APIs.


###### Lifecycle and State Control

**Table 7-15** Parameter Description

| Parameter | Description |
|-----|-----|
| visibility | Visibility, such as "project" (visible within project). |
| auth_required | Whether the user needs to authenticate themselves. false means using the platform's preset unified authentication. |
| intf_type | Interface type. Contains JSON string, blocking represents synchronous blocking call (waiting for API to return). |

> If you need to create a new API plugin based on this template (e.g., integrating a weather query API), follow these steps to modify the JSON:
>
> - Modify basic information: Update plugin_chinese_name and plugin_desc.
> - Update request address: Modify the host in request_info to your API domain (e.g., api.weather.com). Update path and method in tool_info.
> - Rewrite Schema: This is the most error-prone step. It is recommended to first write a standard JSON Schema object, then use a tool to convert it to an escaped string, and fill it into input_schema and output_schema.
> - Configure authentication: If the API requires a Key, fill in the corresponding Header Key name and Value in auth_info.

### 7.1.4 Debugging and Publishing Plugins

After plugin creation, the tools within need to be tested. Only after successful testing can they be published. Only published plugins can be used normally by agents and workflows.

#### Prerequisites

A plugin has been created.

#### Debugging Tools and Publishing Plugins

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. In the left navigation bar, select "Development Center > Component Library", and in the "Plugins" tab, select the created plugin, click the plugin name, and enter the "Tool Information" page.
3. Click "Debug" in the operation column of the tool list. Fill in the test case according to the request parameter structure defined when creating the tool. Click "Start Test" to execute the test.

4. After successful testing, check whether the output content meets expectations. If there are no issues, close the test window and click "Publish" in the upper right corner of the page to publish the plugin.

------

#### Common Issues

##### Authentication Configuration Unavailable

Plugin authentication is unavailable, and the page shows OpenJiuwen.02401121 error. Please check whether the API authentication parameters are filled in incorrectly or have expired.

##### Debugging Succeeds but Output is Empty

Incorrect test parameter filling or inconsistency with the plugin definition will result in successful debugging but empty output (false success). Please check whether the test parameters match the API requirements.

### 7.1.5 Using Plugins

#### 7.1.5.1 Using Plugins in Single Agent

If the LLM is compared to the "brain" of the agent, then plugins are its "eyes" and "hands".

By integrating plugins, a single agent can break through the limitations of text-only generation and gain the following capabilities:

- Connect to the external world: Query weather in real time, search the web, read databases.
- Execute specific operations: Send emails, schedule meetings, generate charts.
- Private data interaction: Call enterprise internal APIs to obtain business data.

In a single agent, the LLM can understand user intent and proactively call plugins to obtain precise information and complete specific tasks. When you configure a plugin, the system automatically injects the plugin's name, description, and parameter definitions into the model's System Prompt. The model automatically determines whether to call the plugin based on the user's question, and what parameters need to be extracted.

##### Prerequisites

- If you need to add a personal plugin, ensure that the personal plugin has been created and debugged/published.
- If you need to add a platform-selected plugin, ensure that the plugin has been authenticated.
- If you need to add a team-shared plugin, ensure that there are plugins shared by others.

##### Single Agent Plugin Usage Process Overview

1. **Select/Create Plugin**: Learn about the platform's preset official plugins in the Asset Marketplace or create custom plugins.
2. **Bind and Configure**: During single-agent creation, mount the plugin to the agent. If the plugin requires authentication, configure the authentication information.
3. **Orchestrate Prompt** (Key): Clearly define the plugin's usage boundaries in the prompt to ensure the model calls accurately.

##### Operation Steps

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. Select "Development Center > Agent Management" in the left navigation bar, click "Create Single Agent" in the upper left corner, and select the "Single Agent" type.

3. Fill in the single-agent name and description, such as "Agent Assistant". Click "Create Now" in the lower right corner to enter the single-agent configuration page.
4. In the middle area of the configuration page, select an available model. In the "Plugins" area, click to select a plugin.

> If the plugin requires authentication before use, please configure the plugin authentication according to the page prompts.

5. Configure the agent's prompt.

   To improve the accuracy of the model calling the plugin, it is recommended to add plugin usage instructions in the "Prompt". You can refer to the following example:

   ```
   You are an all-around assistant. When users ask about real-time information (such as weather, stock prices, news), you must prioritize calling the configured tools/plugins to obtain data, and do not fabricate answers based on your training knowledge. When calling tools, please ensure the extracted parameters are accurate.
   ```

6. After configuration, you can debug the agent in the right area of the page.

------

##### Related Documentation

For detailed information on using plugins in single-agent applications, please refer to Adding Plugins.

#### 7.1.5.2 Using Plugins in Workflows

Compared to the "probabilistic calling" of plugins in single agents (where the LLM decides whether to use them), using plugins in workflows is "deterministic calling" (the flow must execute when it reaches this step). Therefore, the focus must shift from "prompt setting" to "parameter mapping" and "data flow".

##### Applicable Scenarios

- Fixed business logic: Must first query order status, then reply to the user based on the status.
- Precise data processing: Need to call calculators, exchange rate conversion, database queries, and other operations that cannot tolerate errors.
- Connect to external systems: Connect to enterprise ERP, CRM systems to obtain real-time information.

##### Prerequisites

- If you need to add a personal plugin, ensure that the personal plugin has been created and debugged/published.
- If you need to add a platform-selected plugin, ensure that the plugin has been authenticated.
- If you need to add a team-shared plugin, ensure that there are plugins shared by others.

##### Data Flow and Constraints

Before configuring a plugin node, you must understand how data flows between nodes.

###### Configuring Plugin Input Data

You need to select upstream nodes by setting "Reference" on the page. The referenced upstream node must be consistent with the plugin's input parameters in parameter type and parameter body structure.

###### Downstream Nodes Using Plugin Data

After the plugin node executes, it typically outputs a JSON object.

- **Scenario 1: LLM Node References Plugin Data**
  "Feed" the objective information queried by the plugin (such as weather temperature, order status) to the LLM, letting the model organize language to reply to the user based on this information.
  For example, in the LLM node's prompt, use variable syntax (such as {{output}}) to insert the plugin's output result.

- **Scenario 2: Logic Node Makes Decisions Based on Data**
  Based on the status returned by the plugin (success/failure, in stock/out of stock, contains specific value...), determine which path the workflow takes.
  For example, in the logic node's condition settings, select a specific field of the plugin output (such as status), and set judgment rules (e.g., when status equals Success, take branch A).

##### Operation Steps

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. Select "Development Center > Agent Management" in the left navigation bar, click "Create Single Agent" in the upper right corner, and select "Single Agent" or "Task-oriented Workflow". Both types of workflows have plugin nodes.

3. Fill in the workflow name and description. Click "Create Now" in the lower right corner to enter the workflow configuration page.
4. On the configuration page, you can add plugins to the workflow and configure the plugin's input data.

After the plugin is selected, the panel displays the plugin's corresponding input parameters and output parameters. You can "reference" upstream nodes as the plugin's input data source. Note that the plugin's parameter types need to be consistent with the upstream node's parameter types.

If the plugin has fixed-value parameters that do not need to change, directly enter fixed text content in the input box.

If the plugin requires authentication before use, please configure the plugin authentication according to the page prompts.

5. Connect the plugin's downstream nodes.

After the plugin executes and obtains data, it can be connected to an LLM node to process this data and generate a reply. Note to add the plugin's returned query content to the LLM node's system prompt.

**Example:**

```
You are a weather assistant.
The user's question is: {{query}}
The data returned by calling the weather plugin is: {{output}}
Please answer the user in natural language based on the above data.
```

------

### 7.1.6 Managing Plugins

OpenJiuwen service supports version management, viewing version history, reference queries, deletion, export/import of plugin JSON files, and other operations for plugins, ensuring the standardization of full lifecycle plugin management. Core functions include:

- **Version Management**: Publish new plugin versions and record version information, view all plugin version release details in chronological order.
- **Reference Query**: Locate agents and workflows that use this plugin, support manual version updates.
- **Plugin Deletion**: Remove plugins that are no longer in use (high-risk operation, proceed with caution).
- **Export/Import Plugin JSON Files**: Enable local backup, sharing, or cross-space migration of plugins.

#### Prerequisites

A plugin has been created.

#### Managing Plugin Versions

New versions of plugins can be generated through the publish operation. The system records the version name and update description for subsequent traceability.

- **View Plugin Version**
  After logging in to the platform, select "Development Center > Component Library" in the left navigation bar. On the "Plugins" page, click the target plugin to enter the plugin details page. You can perform version publishing and view historical versions for the plugin.

- **Delete Plugin Version**

  In the upper right corner of the plugin details page, click the publish history icon. Move the mouse over the historical record card to be deleted, and click "Delete" to delete that publish history.

> **Note**
>
> If the version has been shared, it cannot be deleted directly. You must first "Cancel Sharing" before deleting the version.

#### Deleting Plugins

After logging in to the platform, select "Development Center > Component Library" in the left navigation bar. On the "Plugins" page, move the mouse over the target plugin to perform the plugin deletion operation.

> **Note**
>
> - If the plugin has been referenced, the reference will be automatically canceled after deletion, which may cause workflows or Agents to fail to run. This operation is irreversible, please proceed with caution.
> - If the plugin has been shared, it cannot be deleted directly. You must first "Cancel Sharing" before deleting the plugin in the "Component Library - Plugins" interface. Please go to "Asset Marketplace > Plugins" to operate.

#### Viewing Plugin Reference List

Query the agents and workflows that use this plugin, and support manual plugin version updates (plugins do not auto-update and require manual operation to ensure application stability).

- Whether plugins referenced in single agents are platform preset plugins or personally created plugins, they will not automatically update to the latest version. Manual update is required.

a. On the plugin details page, click the reference plugin list icon to view which agents reference this plugin.

b. In the reference plugin list, click the agent name to jump directly to the agent's orchestration page, where you can update the plugin.

- When using plugins in workflows, whether platform preset plugins or personally created plugins, they will not automatically update to the latest version. This means even if a new version of the plugin is published, the workflow will continue to use the currently specified version, ensuring stable application operation. If you need to use the latest plugin version in the workflow, you can manually upgrade the plugin version on the workflow page according to the prompts, as shown in Figure 7-42.

#### Exporting/Importing Plugin JSON Files

Through the export/import plugin JSON file function, you can achieve local backup, sharing, or cross-space migration of plugins. Only whole plugin operations are supported; individual tools within a plugin cannot be exported/imported separately.

After logging in to the platform, select "Development Center > Component Library" in the left navigation bar. On the "Plugins" page, click the "Export" button in the upper right corner to export the desired plugins. Click the "Import" button to import the plugin JSON file. For JSON file introduction, please refer to Importing API Plugins via JSON File.

---


## 7.2 MCP

### 7.2.1 MCP Introduction

MCP (Model Context Protocol) is an open protocol designed to break down the interaction barriers between LLM applications and external data sources and tools. In traditional development scenarios, since each data source, tool, or service has independent format specifications, integration protocols, and authentication systems, developers often need to write code separately for each API, process documentation, configure authentication methods and error handling, which is not only inefficient but also greatly increases development and maintenance costs.

The emergence of MCP is like building a standardized bridge between AI models and the external world. MCP provides tools and data through "MCP services" in a universal "standard language" (develop once, connect infinitely), enabling more efficient and convenient interoperability between Agent applications and thousands of external tools and data, greatly improving development efficiency and flexibility. For more detailed information about MCP, please refer to the MCP official documentation.

#### MCP Classification

OpenJiuwen service provides three types of MCP creation methods, all supporting convenient configuration and calling within the platform:

- **Custom Access MCP (Blank Creation)**: Suitable for accessing open-source community MCPs or self-developed MCP services. When platform-selected and third-party MCP services cannot meet business needs, custom MCP services can be accessed. For access methods, please refer to Custom Access MCP.
- **Platform Selected MCP**: Standardized MCP services officially listed by the platform in the Asset Marketplace. Users can directly add and use them (some MCPs require authentication parameters to be configured before use), without additional configuration or development, enabling quick access and calling. For access methods, please refer to Creating MCP Based on Template.

#### Difference Between MCP and Plugins

OpenJiuwen service supports both plugins and MCP to extend tool capabilities for agents. The core differences between the two are as follows:

**Table 7-16** Differences Between MCP and Plugins

| Comparison Dimension | Plugins | MCP |
|---------|------|-----|
| Access Protocol | Based on OpenAPI/custom HTTP interfaces | Based on MCP standard protocol |
| Configuration Method | Need to configure each interface's address and parameters individually | Only need to configure the MCP service address, tools are auto-discovered |
| Tool Usage | Manually define each tool | MCP service automatically exposes available tool list |
| Use Cases | Integrating existing REST API interfaces | Integrating standardized services conforming to MCP protocol |

#### Preparation Before Creating MCP

Before starting creation, it is recommended to confirm the following information:

- **Clarify requirements**: What external capabilities does the agent need? (Such as web scraping, web search, data processing, etc.)
- **Choose creation method**:
    - Have an existing MCP service address (open-source or self-developed): Custom Access MCP
    - Platform-selected has MCP that meets requirements: Creating MCP Based on Template
- **Prepare authentication information (if needed)**: Some MCP services require API Key, OAuth2.0, and other authentication information to function properly.

### 7.2.2 Example: Creating a Search MCP Using Template

This example introduces how to use the preset MCP in the Asset Marketplace, using the Bing Search MCP as an example to introduce the installation and usage of preset MCP.

#### Constraints and Limitations

Before using this example, ensure the network is connected to the public internet to properly use the Bing Search MCP service (Bing).

#### Step 1: Install Preset MCP

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. Click "Asset Marketplace" and enter the "MCP" tab, search and find a Bing Search MCP service (Bing).

3. Move the mouse over the MCP and click "Install". In the popup MCP information, check whether service authentication is needed:

> Generally, the MCP configuration displayed on the platform, whether form editing or JSON editing, does not need to be modified. You only need to focus on whether to fill in authentication information. Whether MCP requires authentication depends on the requirements of the backend service it connects to.

- **No authentication needed**: Some MCP services are publicly open, and anyone can call them directly without authentication. They can be installed and used directly.
- **Authentication needed**: Some MCP services involve private data and permission control. The server requires the caller to prove their identity before access. MCP needs to configure the corresponding authentication information, and cannot function properly without configuration. MCP services requiring authentication need to obtain authentication information according to the prompts and fill in authentication parameters and values.

4. The Bing Search MCP selected in this example does not require authentication and can be installed directly.

5. Return to the "Component Library > MCP" page to view the deployed MCP.

6. Click the deployed MCP to enter the "Tools" tab and view the tool functions under the MCP. Move the mouse over the parameter input box to see parameter input requirements. Enter parameter values according to the prompts and click "Test" for functional verification.

------

#### Step 2: Debug MCP

Click the deployed MCP to enter the "Tools" tab and view the tool functions under the MCP. Move the mouse over the parameter input box to see parameter input requirements. Enter parameter values according to the prompts and click "Test" for functional verification.

#### Step 3: Using MCP in Single Agent

1. On the "Agent Management > Single Agent" page, click "Create Single Agent". Fill in the single-agent name and description as "Q&A Assistant".

2. Set the prompt to "Please use Bing MCP to search the user's question before answering"; select an available model; select the installed Bing MCP.

3. Enter a test question "What's the latest hot news" in the right side of the page and wait for the agent to output results.

Based on the response content, you can determine whether MCP was called, or click the "Debug" button, select a recent session, and in the "Call Details" you can also see that MCP was called.

------

### 7.2.3 Example: Quick Access to ModelScope MCP Toolset

This example introduces how to access the open-source MCP toolset from the ModelScope community in the OpenJiuwen Agent Development Platform.

#### Constraints and Limitations

Before using this example, ensure the network is connected to the public internet to properly use the Bing Search MCP service (Bing).

#### MCP Installation Methods

The OpenJiuwen Agent Development Platform supports two connection modes: Stdio (local process, including NPX, UVX) and Streamable HTTP/SSE (remote network).

##### Stdio (Local Process, Including NPX, UVX)

"Local" here refers to the runtime environment provided by the OpenJiuwen service. When installing MCP using NPX or UVX, the platform will download and start this MCP internally.

- **NPX**: MCP services based on the Node.js ecosystem.
- **UVX**: MCP services based on the Python ecosystem.

##### Streamable HTTP/SSE (Remote Network)

"Remote" refers to MCP services on user-built servers or third-party-provided MCP services. The MCP service code does not run within the OpenJiuwen service but runs elsewhere (such as addresses exposed through local computer intranet penetration, MCP API interfaces provided by third-party MCP vendors). The platform only acts as a client to initiate connections via network protocols.

- **Streamable HTTP type**: MCP connection method based on standard HTTP protocol, supports streaming transmission, is the remote connection method recommended by the MCP protocol. Only needs to provide the MCP service's HTTP interface address to connect.
- **SSE type**: MCP connection method based on Server-Sent Events protocol, is an earlier remote connection method that achieves real-time communication through the server actively pushing data to the client. Only needs to provide the MCP service's SSE interface address to connect.

When accessing MCP services, the MCP provider basically鏍囨敞es the MCP installation method. If not explicitly written, you can also determine the installation method from the MCP configuration script. Please choose the appropriate MCP installation method.

#### Step 1: Access ModelScope MCP Toolset

1. Register and log in to the ModelScope community, enter the "MCP Marketplace". Select "Browser Automation" > "Fetch Web Content Scraping" MCP.

2. Click the MCP name to view the MCP configuration information on the details page. The page shows that the "Fetch Web Content Scraping" MCP can be used without authentication; for MCPs requiring authentication, please obtain the corresponding API KEY according to the prompts.

If using Streamable HTTP to access MCP, click the "Connect" button to obtain the configuration script; the same applies to Stdio, configuration scripts can also be obtained.

3. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
4. In the "Component Library > MCP" tab, click "Create MCP > Blank Creation".

5. Fill in the service name and service description (Web content scraping, Web page content scraping).

6. Select the installation method based on the copied MCP configuration script. This example selects "Streamable HTTP". Select "JSON Editing" for the input method, and delete the example in the page.
7. Copy the configuration information obtained from the ModelScope community and fill it into the OpenJiuwen platform. Click "Install" and wait for MCP installation to succeed.

> **Note**
>
> If MCP installation fails, most causes are MCP itself issues, such as untimely maintenance of open-source community MCP or backend service failure. If installation fails, please try changing the MCP source.

------

#### Step 2: Debug MCP

1. Click the deployed MCP to enter the "Tools" tab and view the tool functions under the MCP. After the MCP service is successfully installed, the corresponding tool capabilities of the MCP will be automatically parsed. Please refer to the MCP function introduction in the ModelScope community, enter parameter values for debugging.

> **Note**
>
> - MCP tool parsing failure is mostly caused by MCP itself issues, such as untimely maintenance of open-source community MCP or backend service failure. If tool parsing fails, please try changing the MCP source.
> - When debugging MCP, please strictly follow the parameter format requirements to avoid errors.
> - When using "web scraping" type MCP to obtain web content, if the target website has anti-scraping protection (such as robots restrictions, IP bans, CAPTCHAs, etc.), scraping may fail. This is a common and normal technical limitation.

------

#### Step 3: Using MCP in Single Agent

1. On the "Agent Management > Single Agent" page, click "Create Single Agent". Fill in the single-agent name and description as "Web Content Summary Assistant".

2. Set the prompt to pass the user-input URL link to the "Web Content Scraping" MCP to obtain the body content and summarize it. When the MCP cannot obtain web content, reply "Unable to obtain web content"; select an available model; select the installed Web Content Scraping MCP.

3. Enter a test link in the right side of the page and wait for the agent to output results.

Based on the response content, you can determine whether MCP was called, or click the "Debug" button, select a recent session, and in the "Call Details" you can also see that MCP was called.

------

### 7.2.4 Creating MCP

#### 7.2.4.1 Custom Access MCP

Custom access is the most flexible MCP creation method. You can connect any MCP service to the platform for agent use by filling in the MCP service's connection address.

This method supports accessing MCPs from open-source communities (such as open-source MCPs on GitHub, ModelScope), as well as user self-developed MCP services. It is suitable for scenarios with specific business system integration needs or requiring the use of community open-source MCP capabilities. For operation examples, please see Example: Quick Access to ModelScope MCP Toolset.

##### Prerequisites

- If you need to access self-developed or privately deployed MCP services, ensure the service has been deployed and can be accessed via a public network address. Since OpenJiuwen is a public cloud service, the platform needs to establish connections with MCP services through the public network and cannot directly access services in intranet or local environments.
- If the MCP service requires authentication, please prepare the required authentication information in advance (such as API Key, OAuth 2.0 client ID and secret, etc.)

##### Operation Steps

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. In the left navigation bar, select "Development Center > Component Library", click the "MCP" tab in the upper left corner to enter the MCP management interface.
3. In the MCP management interface, click "Create MCP > Blank Creation" in the upper right corner to create an MCP service.

4. In the "Blank Creation" dialog, enter the MCP service configuration information. For parameter descriptions, please refer to Table 7-17.

**Table 7-17** MCP Service Parameter Description

| Parameter | Description | Example |
|-----|-----|-----|
| Service Icon | MCP service icon. Supports SVG, PNG, JPG, JPEG formats by default, no larger than 1MB. | Default icon |
| Service Name | MCP service name, used to distinguish different MCP service instances. Does not affect the model's judgment and calling.<br><br>**Naming rules**:<br>- Naming requirements: Only supports starting with Chinese or English.<br>- Supported characters: Chinese, English, numbers, hyphens (-), underscores (_).<br>- Length limit: 2~64 characters. | Web Content Scraping |
| Service Description | MCP service description information, helping users understand the service functionality. For example, a powerful MCP server that can easily scrape web content and convert it to various formats (HTML, JSON, Markdown, plain text). | This server enables LLMs to retrieve and process web content, converting HTML to various formats for easier use. |
| Service Introduction (Optional) | More detailed introduction of some features of this MCP service. For example, usage methods, key capabilities, use cases, notes, etc. | A powerful MCP server that can easily scrape web content and convert it to various formats (HTML, JSON, Markdown, plain text). |
| Installation Method | The platform supports the following two categories and four MCP connection modes:<br><br>- **Stdio (including NPX, UVX)**<br>  When this method is selected, the platform automatically downloads and starts the MCP service internally, without user deployment. NPX is suitable for Node.js ecosystem MCP services, UVX is suitable for Python ecosystem MCP services.<br><br>- **Streamable HTTP/SSE**<br>  When this method is selected, the MCP service runs in an external environment (such as user-built servers, third-party MCP vendor-provided interfaces, etc.), and the platform acts as a client to initiate connections via network address. Streamable HTTP is the remote connection method recommended by the MCP protocol, SSE is an earlier remote connection method. Both only require providing the MCP service's interface address to connect.<br><br>The platform provides two ways to enter MCP configuration information, choose one to fill in:<br>- **Form Editing**: Directly fill in the MCP service's connection address in the form, suitable for scenarios with simple configuration information. In form editing mode, in addition to filling in the connection address, you can also configure the following two items as needed.<br>  - Environment variables: Used to set variable parameters needed for MCP service runtime, typically used to store sensitive information such as API Keys, Tokens.<br>  - Request headers: Used to attach custom HTTP header information when the platform sends requests to the MCP service. Some MCP services require authentication credentials or other identification parameters to be passed in request headers.<br>- **JSON Editing (Recommended)**: Fill in the complete MCP configuration in standard JSON format. Most MCP vendors provide complete JSON configurations that can be directly copied and used without additional conversion to forms.<br><br>When accessing MCP services, the MCP provider basically鏍囨敞es the MCP installation method. If not explicitly written, you can also determine the installation method from the MCP configuration script. Please choose the appropriate MCP installation method. | Using UVX, JSON editing<br>```json<br>{<br>  "mcpServers": {<br>    "fetch": {<br>      "args": [<br>        "mcp-server-fetch"<br>      ],<br>      "command": "uvx"<br>    }<br>  }<br>}<br>``` |
| Authentication Configuration | Select whether authentication is needed when calling MCP.<br><br>- **No authentication**: The API can be publicly accessed without any form of identity verification or authorization.<br>- **API Key**: Provides a unique API Key for authentication when calling the API. The following information needs to be configured: key location, key parameter name, and value. When the Agent initiates a request, it automatically puts this API Key in the request's Header or Query.<br>  - **Key Location**: Whether the key is read from the Header or from the Query.<br>  - **Parameter Name**: The authentication parameter name of the API Key.<br>  - **Parameter Value**: The specific value of the API Key.<br>- **OAuth2.0**: OAuth 2.0 is an open authorization protocol that allows third-party applications to securely obtain access to your resources in other services without obtaining your account password.<br>  - **Authorization Server URL**: The endpoint URL of the authorization server, used to send authorization requests and receive responses. The platform sends requests to this address to obtain Access Tokens. This address is provided by the API service provider you are connecting to.<br>  - **Client ID**: The application's unique identifier assigned by the API service provider, used to distinguish and identify different applications. Typically obtained after creating an application in the service provider's developer backend.<br>  - **Client Secret**: The key paired with the Client ID, used to verify the legitimacy of the application identity, ensuring only authorized applications can use it.<br>  - **Requested Permission Scope**: Declares the resource scope that needs to be accessed for this authorization, used to limit the application's access permissions. | No authentication |

5. After configuration, click "Install".

------

#### 7.2.4.2 Creating MCP Based on Template

If you don't want to manually configure the MCP service's connection address and parameters, you can directly use the platform's selected MCP templates. Platform selected MCPs are standardized MCP services officially screened and listed in the Asset Marketplace, which have been adapted and verified. You only need to install them to use (some MCPs require authentication information to be filled in before normal calling), without additional configuration or development. When your needs happen to be within the platform's selected coverage, this is the fastest access method. For operation examples, please see Example: Creating a Search MCP Using Template.

##### Constraints and Limitations

Please ensure the network is connected to the public internet to properly install the preset MCP.

##### Operation Steps

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. In the left navigation bar, select "Development Center > Component Library", click the "MCP" tab in the upper left corner to enter the MCP management interface.
3. In the MCP management interface, click "Create MCP > Platform Template Creation" in the upper right corner to create an MCP service.

4. The platform provides various preset MCP services. Select one and click "Next" to configure MCP information.

5. On the MCP service configuration tab, you can view the preset MCP's introduction and modify it. Focus on whether the MCP requires authentication.

> Generally, the MCP configuration displayed on the platform, whether form editing or JSON editing, does not need to be modified. You only need to focus on whether to fill in authentication information. Whether MCP requires authentication depends on the requirements of the backend service it connects to.

- **No authentication needed**: Some MCP services are publicly open, and anyone can call them directly without authentication. They can be installed and used directly.
- **Authentication needed**: Some MCP services involve private data and permission control. The server requires the caller to prove their identity before access. MCP needs to configure the corresponding authentication information, and cannot function properly without configuration. MCP services requiring authentication need to obtain authentication information according to the prompts and fill in authentication parameters and values.
6. After confirming the configuration information is correct, click "Install".

------

### 7.2.5 Debugging MCP

After MCP creation, it is recommended to first perform debugging verification, confirming that the MCP service connection is normal, tools are correctly identified, and call results meet expectations before associating it with agents for use. The debugging phase is the best time to discover and troubleshoot issues. Skipping debugging and bringing problems into the agent runtime will significantly increase troubleshooting difficulty.

#### Pre-Debug Confirmation

Before starting debugging, please check the following items:

- **Whether tools have been identified**: Enter the MCP details page and confirm that the tool list has been correctly loaded. If the tool list is empty, it is usually due to incorrect MCP configuration or MCP service itself issues. Such as untimely maintenance of open-source community MCP or backend service failure. If failure occurs, please try changing the MCP source.

- **Whether authentication information has been configured**: If the MCP service requires authentication, please confirm that authentication parameters have been correctly filled in during creation, otherwise debugging will return authentication failure errors.
- **Whether the service is accessible**: For Streamable HTTP / SSE type MCPs, confirm that the service address can be accessed normally via the public network.

#### Debugging MCP

1. After MCP deployment succeeds, click the MCP name and enter the "Tools" tab to view the MCP's tools and perform testing.

Before debugging, first check whether each tool's name, description, and parameter definition are complete and accurate. This information directly affects whether the agent can correctly understand and call the tool subsequently. If tool descriptions are found to be missing or parameter definitions are incomplete, corrections need to be made on the MCP service side (or try redeploying the MCP).

Incorrect parameter format is the most common error cause during debugging. When debugging, please carefully check each parameter's type and format instructions, and fill in according to the requirements. For detailed format issues, please refer to MCP Debugging Failures. Common format issue examples:

```
鉁?url: example.com 鈫?鉁?url: https://www.example.com
鉁?date: 2025骞?鏈?5鏃?鈫?鉁?date: 2025-01-15
鉁?tags: 绉戞妧,閲戣瀺 鈫?鉁?tags: ["绉戞妧", "閲戣瀺"]
鉁?age: "25" 鈫?鉁?age: 25
鉁?enabled: "true" 鈫?鉁?enabled: true
鉁?filter: {name: "寮犱笁"} 鈫?鉁?filter: {"name": "寮犱笁"}
鉁?language: ZH锛堝彲閫夊€间负 zh/en/ja锛?鈫?鉁?language: zh
```

------


### 7.2.6 Using MCP

#### 7.2.6.1 Using MCP in Single Agent

After MCP creation and debugging pass, it can be added to agents for use. The platform supports using MCP in both single-agent and workflow modes. For using MCP in workflows, please see Using MCP in Workflows. The core difference between the two lies in the tool calling method:

**Table 7-18** Differences Between Using MCP in Single Agent and Workflow

| Comparison Dimension | Using in Single Agent | Using in Workflow |
|---------|-----------------|---------------|
| Calling Decision | The LLM autonomously determines whether to call and which tool to call | Fixed call at specified process node |
| Parameter Source | The LLM automatically extracts parameters from conversation context | Pre-configured in the node, or references upstream node variables |
| Execution Order | Not fixed, dynamically determined by the LLM based on conversation | Fixed, executed in the orchestrated process order |
| Use Cases | Conversational scenarios with diverse user intents requiring flexible responses | Scenarios with clear processes, fixed steps, and precise control requirements |

Simply understood: In single-agent mode, MCP tools are the LLM's "optional moves"; in workflow mode, MCP tools are "prescribed moves" in the process.

##### Notes

In single-agent mode, MCP calling is entirely decided by the LLM. The LLM determines whether to call a tool, which tool to call, and what parameters to extract from the conversation context based on the user's input content, combined with the tool's name and description. The entire process requires no human intervention, but it also means that whether the tool can be accurately called depends heavily on configuration details. The following are key notes:

- **Clearly specify tool usage scenarios and rules in the prompt**

  This is the most effective way to improve MCP tool calling accuracy. Do not assume the LLM can automatically understand when to use which tool. Instead, explicitly write each tool's usage timing, calling conditions, and usage rules in the prompt:

  **Example:**

  ```
  # MCP Usage Rules

  1. [Weather Query MCP]
     - Usage timing: When users ask about weather, temperature, rain, etc. for a city
     - Notes: Need to extract the city name from the user's conversation as a parameter. If the user does not mention a specific city, ask first

  2. [Web Scraping MCP]
     - Usage timing: When users provide a web link and ask you to obtain, analyze, or summarize the web page content
     - Notes: The user must provide a complete URL (including https://). If the user only gives a domain, guide them to complete it first
  ```

  **Important:**

  - If the user's question can be answered directly, do not call MCP
  - When unsure which MCP to use, prioritize clarifying user needs through conversation
  - Call only one MCP at a time, and decide the next step after receiving results

- **Ensure MCP description is clear and accurate**

  In addition to referring to the prompt, the LLM also relies on the MCP's own name and description to determine its purpose. If the MCP service provides descriptions that are too brief or vague, it may cause the LLM to misunderstand.

- **Guide the LLM to confirm information before calling**

  MCP calling parameters are automatically extracted by the LLM from the conversation. If the user's expression is vague or information is incomplete, parameter extraction errors may occur. It is recommended to require the LLM in the prompt to confirm key information before calling MCP:

  ```
  # Confirmation Rules Before Calling MCP

  - Before calling MCP, confirm that all required parameters have been obtained from the user's conversation
  - If the user's information is incomplete or ambiguous, ask for confirmation through conversation first, do not guess
  ```

- **Control MCP quantity**

  Too many mounted MCPs increase the LLM's difficulty in choosing, easily leading to selecting the wrong MCP or indecision. It is recommended that the total number of MCPs associated with a single agent does not exceed 5. If the business indeed requires more MCPs, consider splitting into a multi-agent architecture, letting different sub-agents each be responsible for tools in specific domains.

- **Debug and verify MCP calling effects**

  After single-agent configuration is complete, it is recommended to verify tool calling with different types of test questions:

  **Test Points:**

  1. Questions that should trigger MCP calls 鈫?Did it correctly call the corresponding MCP?
  2. Questions that should not trigger MCP calls 鈫?Was there no misfire?
  3. Questions with incomplete information 鈫?Did it ask first rather than calling directly?
  4. Questions where multiple MCPs may match 鈫?Did it select the correct one?

##### Using MCP in Single Agent

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. "Development Center > Agent Management", click the "Single Agent" tab in the upper left corner to enter the single-agent application management interface.
3. Click the target single-agent application, and in the "Single Agent Configuration" tab, click the "Add" button to the right of the MCP service to add MCP services.
4. In the prompt area, set MCP calling rules. In the right debugging area, enter questions to verify whether MCP has been triggered successfully.

------

#### 7.2.6.2 Using MCP in Workflows

After MCP creation and debugging pass, it can be added to workflows for use. The platform supports using MCP in both single-agent and workflow modes. For using MCP in single agents, please see Using MCP in Single Agent. The core difference between the two lies in the tool calling method:

**Table 7-19** Differences Between Using MCP in Single Agent and Workflow

| Comparison Dimension | Using in Single Agent | Using in Workflow |
|---------|-----------------|---------------|
| Calling Decision | The LLM autonomously determines whether to call and which tool to call | Fixed call at specified process node |
| Parameter Source | The LLM automatically extracts parameters from conversation context | Pre-configured in the node, or references upstream node variables |
| Execution Order | Not fixed, dynamically determined by the LLM based on conversation | Fixed, executed in the orchestrated process order |
| Use Cases | Conversational scenarios with diverse user intents requiring flexible responses | Scenarios with clear processes, fixed steps, and precise control requirements |

Simply understood: In single-agent mode, MCP tools are the LLM's "optional moves"; in workflow mode, MCP tools are "prescribed moves" in the process.

##### Notes

In workflow mode, MCP is called as a fixed node in the process. When to call and what parameters to pass are pre-configured during orchestration, without relying on the LLM's autonomous judgment. Compared to single-agent mode, workflow tool calling is more deterministic and controllable, but the following points need attention during construction:

- **Correct parameter configuration:**

  MCP input parameters need to be manually configured in the node. You can fill in fixed values or reference upstream node variables. Ensure parameter types and formats are consistent with MCP requirements (e.g., if MCP requires String type input, the referenced node parameter must also be String type, and the format must be consistent).

- **Pay attention to data transfer between nodes:**

  If the MCP node's output results need to be used in subsequent nodes, confirm that the variable reference relationship is correct and the data format can be properly parsed by downstream nodes.

- **Handle exception branches properly:**

  MCP calls may fail due to network timeout, parameter errors, service exceptions, etc. It is recommended to configure exception handling branches in the workflow to avoid the entire process being interrupted due to a single node error.

##### Using MCP in Workflows

1. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
2. "Development Center > Agent Management", click the "Workflow" tab to enter the workflow application management interface.
3. Click the target workflow application to enter the workflow orchestration interface.
4. In the workflow orchestration interface, click "Add Node" and select the "MCP Service" node. Connect the MCP node into the workflow.

5. Set the MCP node's input parameters, referencing upstream nodes; set the MCP downstream node's input, passing the MCP results to subsequent nodes.

6. Click "Trial Run" in the upper right corner of the page to verify whether the workflow can run normally.

------

### 7.2.7 Managing MCP

After MCP creation, in the "Component Library > MCP" tab, you can view successfully installed MCP services. You can find MCP services through property type (service name) or keyword search. You can also perform operations as shown in Table 7-20 as needed.

**Table 7-20** More Operations

| Operation | Steps |
|-----|-----|
| View Reason | If MCP deployment fails, move the mouse over the MCP service card and click "View Reason" to view the specific deployment failure reason. |
| Edit MCP Configuration | 1. In the "MCP" tab, click the target MCP service card to enter the details page.<br>2. Click the "Edit" button in the upper right corner of the page to modify the MCP service's configuration information. |
| Redeploy | Move the mouse over the MCP service card and click "Redeploy" to redeploy the MCP service. |
| Uninstall MCP Service | After uninstallation, the MCP service will go offline. Please operate with caution.<br>1. In the "MCP" tab, move the mouse over the MCP service card to be uninstalled.<br>2. Click the "Uninstall" button in the lower left corner of the card to complete uninstallation.<br><br>**Note**<br>If the MCP service has been referenced, uninstallation will automatically cancel the reference relationship, which may cause workflows or agents to fail to run. This operation is irreversible, please proceed with caution. |
| View MCP Service Overview | 1. In the "MCP" tab, click the target MCP service card to enter the details page.<br>2. Under the "Overview" tab on the details page, view detailed information such as the MCP service's service description and service introduction. |
| View and Test Tools | 1. In the "MCP" tab, click the target MCP service card to enter the details page.<br>2. Under the "Tools" tab on the details page, you can view the MCP's supported tool details and perform testing to verify tool execution effects. |

### 7.2.8 Troubleshooting

When MCP installation fails, the platform returns specific error codes and error message prompts. For network connectivity, environment configuration conflicts, and protocol errors that may occur during service creation, this chapter provides diagnostic flows and solutions for typical error codes.

#### Pre-Check: Confirm MCP Installation Method

Most MCP service installation failures stem from incorrect MCP installation method selection. Before deeply investigating network issues and configuration issues, please first confirm whether the MCP installation method is correctly selected.

The platform supports two connection modes: Stdio (local process, including NPX, UVX) and Streamable HTTP/SSE (remote network).

##### Stdio (Local Process, Including NPX, UVX)

"Local" here refers to the runtime environment provided by the OpenJiuwen service. When installing MCP using NPX or UVX, the platform downloads and starts this MCP internally.

- **NPX**: MCP services based on the Node.js ecosystem.
- **UVX**: MCP services based on the Python ecosystem.

##### Streamable HTTP/SSE (Remote Network)

"Remote" refers to user-built MCP services or third-party-provided MCP services. The MCP service code does not run within the OpenJiuwen service but runs elsewhere (such as addresses exposed through local computer intranet penetration, MCP API interfaces provided by third-party MCP vendors). The platform only acts as a client to initiate connections via network protocols.

- **Streamable HTTP type**: MCP connection method based on standard HTTP protocol, supports streaming transmission, is the remote connection method recommended by the MCP protocol. Only needs to provide the MCP service's HTTP interface address to connect.
- **SSE type**: MCP connection method based on Server-Sent Events protocol, is an earlier remote connection method that achieves real-time communication through the server actively pushing data to the client. Only needs to provide the MCP service's SSE interface address to connect.

When accessing MCP services, the MCP provider basically鏍囨敞es the MCP installation method. If not explicitly written, you can also determine the installation method from the MCP configuration script. Please choose the appropriate MCP installation method.

#### MCP Debugging Failures

When debugging MCP tools, please strictly fill in input values according to parameter format requirements. Incorrect parameter format is the most common error cause during debugging. It is recommended to check each parameter's type, format instructions, and examples before debugging to ensure input values meet requirements.

The following are several common parameter format errors and correct writing:

##### Example 1: Date/Time Parameters

Some MCP tools require date or time parameters, typically following specific formats:

```
鉂?Incorrect:
date: 2025骞?鏈?5鏃?date: 01-15-2025
date: 2025/01/15

鉁?Correct (need to fill in according to MCP's actual requirements):
date: 2025-01-15 (Date format: YYYY-MM-DD)
datetime: 2025-01-15T10:30:00Z (DateTime format: ISO 8601)
```

##### Example 2: Array/List Parameters

Some tool parameters require multiple values (array format):

```
鉂?Incorrect:
tags: 绉戞妧,閲戣瀺,鍖荤枟
tags: 绉戞妧銆侀噾铻嶃€佸尰鐤?tags: "绉戞妧" "閲戣瀺" "鍖荤枟"

鉁?Correct:
tags: ["绉戞妧", "閲戣瀺", "鍖荤枟"]
```

**Common error**: Expected array, got string, or parameter type mismatch.

**Cause**: Array parameters need to use JSON array format ["value1", "value2"], not comma-separated plain text.

##### Example 3: JSON Object Parameters

Some tools require structured JSON objects:

```
鉂?Incorrect:
filter: name=寮犱笁, age=25
filter: {name: 寮犱笁, age: 25}

鉁?Correct:
filter: {"name": "寮犱笁", "age": 25}
```

**Common error**: JSON parse error or Invalid JSON format.

**Cause**: JSON format requires key names to be wrapped in English double quotes, and string values also need double quotes. Single quotes or omitted quotes are not allowed.

##### Example 4: Enum/Fixed Optional Values

Some parameters only accept a few predefined fixed values:

```
Parameter description: language, optional values: zh / en / ja

鉂?Incorrect:
language: 涓枃
language: chinese
language: ZH

鉁?Correct:
language: zh
```

**Common error**: Invalid enum value or parameter value not within allowed range.

**Cause**: Enum parameters must strictly use the specified optional values. Note that case usually also needs to match exactly.

##### Quick Troubleshooting Checklist

- Is the parameter value type correct (string/number/boolean/array/object)?
- Do string values need quotes?
- Does the date format conform to ISO 8601 standard (YYYY-MM-DD)?
- Are array parameters using JSON array format ["value1", "value2"]?
- Are JSON object key names using English double quotes?
- Are enum parameter values exactly matching the options (including case)?
- Are all required parameters filled in?
- Do parameter values contain extra spaces or special characters?

#### MCP Usage Failures in Agents

**Table 7-21** Troubleshooting Instructions

| Symptom | Possible Cause | Troubleshooting Method |
|---------|---------|---------|
| Agent does not call MCP after user explicitly states need | MCP description not clear enough, LLM cannot associate. | Optimize MCP name and description to be more explicit. |
| | Prompt lacks MCP usage guidance. | Clearly specify MCP usage scenarios and timing in the prompt. |
| | MCP not correctly associated with agent. | Check whether the corresponding MCP has been added in agent configuration. |
| | Agent selects wrong MCP | Multiple MCPs have similar descriptions, LLM is confused. | Differentiate each MCP's description, highlight their respective usage scenarios. |
| | Too many MCPs mounted. | Reduce MCP count, recommended not to exceed 5. |
| | Prompt does not distinguish different MCPs' usage conditions. | Write specific usage scenarios for each MCP in the prompt. |
| Agent misinterprets MCP return results | Returned data field meanings unclear | Explain how to interpret MCP returned data in the prompt. |

#### MCP Installation Failures

When MCP installation fails, the platform returns specific error codes and error messages. Please follow this approach for preliminary diagnosis:

OpenJiuwen has a built-in intelligent detection mechanism. Understanding this mechanism helps you quickly determine whether the problem is at the physical network layer or application configuration layer when facing complex errors (such as "timeout" or "conflict").

When the system connects to your MCP service, it performs two-step detection in sequence:

- **Step 1 (Scout Reconnaissance)**: Uses TCP protocol to attempt to establish a connection with the MCP service.
- **Step 2 (SDK Handshake)**: After the connection is established, uses HTTP protocol to send data.

Based on this mechanism, you can precisely delineate based on error details:

**Table 7-22** Error Code Description

| Error Code | Error Scenario | Typical Error Message | Troubleshooting and Solution |
|-------|---------|-------------|--------------|
| OpenJiuwen.02401173 | Domain name error, unable to resolve target host address | AgentStudioException: Unknown Host: mcp-unknown-host.local<br><br>- **Symptom**: Error message shows Unknown Host.<br>- **Cause**: The system failed at the MCP domain name IP resolution stage, no network packets were sent.<br>- **Solution**:<br>  - When creating MCP service: Check whether the MCP address filled in OpenJiuwen is correct, whether there are spelling errors in the URL.<br>  - When connecting to third-party MCP: The other party may have blocked cloud vendor IP ranges (geo-fencing). It is recommended to replace with an MCP with the same functionality.<br>  - When connecting to local self-built MCP: Self-built MCP services must bind a public IP (EIP) or use an intranet penetration domain. The local MCP server's security group/system firewall has not opened the port, or you have not configured a public IP, or whether .local or k8s-svc and other internal domain names are used? OpenJiuwen uses public DNS and cannot resolve private domain names, causing OpenJiuwen to be unable to connect to MCP. |
| OpenJiuwen.02401161 | Connection timeout, network physical isolation or firewall packet loss | Connect timed out (2s limit)<br>TimeoutException... within 120000ms<br><br>- **Symptom**: Error message shows Connect timed out (2s limit) or TimeoutException... within 120000ms.<br>- **Cause**: The system cannot even complete TCP handshake, reporting connection timeout.<br>- **Solution**:<br>  - When connecting to third-party MCP: The other party may have blocked cloud vendor IP ranges (geo-fencing). It is recommended to replace with an MCP with the same functionality.<br>  - When connecting to local self-built MCP: Whether the MCP server has not opened the port due to security group/system firewall reasons, or has not configured a public IP. |
| OpenJiuwen.02401162 | Connection refused, IP reachable but port not open | Connection refused: no further information<br><br>- **Symptom**: Error message shows Connection refused: no further information.<br>- **Cause**: The system successfully reached the MCP service, but the MCP explicitly returned a rejection.<br>- **Solution**:<br>  - When connecting to local self-built MCP: Check whether the code has a fixed listening address, causing it to only accept internal server requests and reject external OpenJiuwen requests. Change the address to a public IP or intranet penetration domain.<br>  - When creating MCP service: Check whether the protocol port matches. HTTP default port is 80, HTTPS default port is 443. Do not force HTTPS protocol to a non-encrypted port. |
| OpenJiuwen.02401163 | Path error (404) | HTTP 404 Not Found: http://.../wrong-path<br><br>- **Symptom**: Error message shows HTTP 404 Not Found.<br>- **Cause**: The system successfully reached the MCP service, but the MCP explicitly returned a rejection.<br>- **Solution**:<br>  - Check whether the MCP address filled in OpenJiuwen is correct, whether there are spelling errors in the URL. Check the end of the URL. For example, if the MCP specification requires /sse, was it written as /chat? Try accessing the URL directly in a browser to confirm whether you can see a returned result.<br>  - Check whether parameters were omitted when creating the MCP, or whether there are spelling errors. |
| OpenJiuwen.02401164 | Proxy/authentication conflict, platform intelligently infers configuration error code 1164 | TimeoutException... (but error code determined as 1164) or Conflict detected<br><br>- **Symptom**: Error message shows TimeoutException with a long time (such as 60s/120s), but error code determined as 1164.<br>- **Cause**: The system found that TCP connection succeeded (indicating IP, port, firewall are all connected), but was blocked or timed out when sending HTTP requests.<br>- **Solution**:<br>  - When connecting to third-party MCP: Very likely the other party's WAF (Web firewall) or CDN treats OpenJiuwen's requests as crawler/attack traffic and intercepts them (TCP handshake allowed, HTTP content intercepted). It is recommended to replace with an MCP with the same functionality.<br>  - When connecting to company intranet-built MCP: The company's edge gateway Proxy policy intercepted the request but did not return a standard rejection status code. Check proxy configuration, ensure the target address is added to the NO_PROXY list, or allow HTTP persistent connections from OpenJiuwen. |
| OpenJiuwen.02401150 | SSL/certificate error or other general network security protocol and certificate failures | Probe Error: PKIX path building failed or Handshake error.<br><br>- **Symptom**: Error message shows PKIX path building failed or Handshake error.<br>- **Cause**: The network between OpenJiuwen and MCP is connected, but both parties failed when establishing an encrypted connection (SSL/TLS).<br>- **Solution**: Focus on troubleshooting HTTPS certificate validity. Since OpenJiuwen does not trust self-signed certificates that have not been certified by CA institutions by default, it cannot trust certificates issued by non-authoritative institutions. Please take the following measures based on your scenario:<br>  - It is recommended to temporarily change the protocol from https:// to http:// during the testing phase. This operation can bypass all certificate validation logic, but please ensure your server has opened non-encrypted port (usually port 80 or custom port) listening.<br>  - If unsure about the certificate status, directly access the MCP's URL in a local browser. If the address bar pops up "Your connection is not private" or "Not secure" warning, this confirms a certificate issue. It is recommended to update the self-built MCP service's certificate, such as updating to Let's Encrypt or other formal trusted certificates. |


## 7.3 Knowledge Base

### 7.3.1 Knowledge Base Introduction

#### Function Overview

A knowledge base is a system for organizing, storing, and managing knowledge, covering the classification and organization of documents, images, videos, and other information, helping users efficiently manage large amounts of information. Adding a knowledge base to an Agent, enabling it to interact with professional knowledge bases provided by users, can significantly improve the Agent's accuracy and professionalism.

OpenJiuwen's knowledge base function performs vectorization storage and knowledge retrieval on text documents, FAQ (Frequently Asked Questions), and other data, supporting retrieval-enhanced capabilities for applications and workflows. Whether text documents, presentations, or spreadsheet files, users can easily import data into the knowledge base without additional conversion or format processing.

#### Supported Document Formats

The knowledge base supports importing local documents as shown in Table 7-23:

**Table 7-23 Supported Document Formats**

| Document Type | Document Format | Size Requirements |
|---------|---------|---------|
| Knowledge Documents | Supports uploading common text formats, including: psd, tiff, bmp, gif, csv, tif, ico, md, jpeg, jpg, xlsx, pcx, dps, png, webp, ofd, docx, et, pptx, txt, pdf, ppt, doc, wps, xls formats | Single document upload limited to 60MB max |
| FAQ | Supports uploading text according to template, template file types are Word and Excel | Only supports xlsx, xls, docx, doc format files, single file max 60MB; Excel single file max 100,000 records, empty rows in the file are not allowed, data after empty rows will be ignored |

**Note**

- If the connected LakeSearch version is lower than 3.6.0, parsing md format files is not supported. For details, please refer to "Agent Development Platform 26.2.1 Installation Guide"
- If the connected LakeSearch has not deployed an OCR model, parsing png, jpg, jpeg, bmp, gif format files is not supported. For details, please refer to "Agent Development Platform 26.2.1 Installation Guide"

#### Application Scenarios

- **Cultural Tourism Service Scenario**: Travel platforms can upload scenic spot introductions, travel routes, nearby dining and accommodation information, transportation schedules, ticket prices and discount policies, and local special experience projects to the knowledge base. When tourists query "weekend family trip scenic spot recommendations", the intelligent assistant generates customized plans based on information such as suitable age groups and travel duration; when querying "how to book scenic spot tickets", it directly retrieves booking requirements and processes.
- **Scientific Research Assistance Scenario**: Researchers can upload Chinese and English literature abstracts, experimental data records, reference bibliography, and industry standards and research methods to the knowledge base. When writing papers, the agent retrieves relevant literature abstracts through vector recall, extracting core conclusions and data support; when designing experimental plans, it quickly retrieves parameter settings and research methods of similar experiments, comparing pros and cons and optimizing experimental design to improve research efficiency.
- **Intelligent Q&A Assistant Scenario**: Enterprises can upload product documents, product user manuals, collections of frequently asked user questions, product parameter specification tables, common troubleshooting guides, and other information to the knowledge base. The agent can accurately answer users' questions through precise matching of relevant information in the knowledge base.

#### Knowledge vs. Memory Comparison

Knowledge: Refers to information and understanding obtained by the Agent through data input. This information can be unstructured (such as documents, articles).

Memory: Refers to specific information stored and retrieved by the Agent during interactions with users. This information is typically related to specific users or sessions, used to provide personalized services and context-related responses.

**Table 7-24 Knowledge vs. Memory Comparison**

| Type | Knowledge | Memory |
|-----|------|------|
| **Similarities** | | |
| Information Storage | Both knowledge and memory involve information storage. Whether data in the knowledge base or temporary information in a session, both are for quick access and use when needed | |
| Decision Support | Both knowledge and memory support the Agent in making more accurate and effective decisions during interactions with users. Knowledge provides a broad information base, while memory provides specific context information | |
| Dynamics | Both knowledge and memory are dynamic, requiring regular updates and maintenance. The knowledge base needs regular updates to maintain information accuracy and timeliness, while memory needs continuous updates during sessions to reflect the user's latest interactions | |
| Improve User Experience | The knowledge base provides comprehensive information support, helping users quickly find answers; memory provides personalized services, making interactions more natural and coherent | |
| **Differences** | | |
| Storage Method | Usually stored in external media, such as databases, knowledge graphs, documents, etc. This information is structured or unstructured and can be stored long-term and shared | Usually stored in the Agent's internal state, such as session state, user state, etc. This information is typically temporary and is cleared when the session ends or the user logs out |
| Information Type | Covers a wide range of information, including facts, principles, skills, methods, etc. This information is generic and can be applied to multiple users and scenarios | Involves information specific to a user or session, such as user query history, preferences, context information, etc. This information is personalized, specific to a particular user or session |
| Update Frequency | Needs regular updates and maintenance to maintain information accuracy and timeliness. Update frequency may be lower, but each update involves large amounts of information | Continuously updated during each interaction to reflect the user's latest behavior and needs. Update frequency is higher, but each update involves smaller amounts of information |
| Transferability | Knowledge bases can be shared across multiple Agents, improving overall service quality | Usually specific to a particular user or session, not directly transferred to other users or sessions. Memory information transfer usually requires user identification and session identification |
| Application Scenarios | Widely used in FAQ, product information, policies and regulations, best practices, etc. This information is generic, applicable to multiple users and scenarios | Mainly used in multi-turn conversations, personalized recommendations, user identification, context understanding, etc. This information is personalized, specific to a particular user or session |
| Individual Differences | Different Agents may have different knowledge levels and acquisition channels, but knowledge itself is objective, applicable to all users | Different users' memory content and methods differ significantly, influenced by the user's specific needs and historical behavior |

### 7.3.2 Knowledge Base Types

Knowledge Base Types

OpenJiuwen supports the management of the following two types of knowledge bases:

- **Default**: Knowledge bases created and managed directly within OpenJiuwen. Supports uploading text documents, FAQ documents, and other files, setting document tags, and performing vectorization storage and knowledge retrieval on them.
- **Third-party**: Connects knowledge bases from third-party systems to OpenJiuwen. Currently supports connecting to open-source third-party knowledge bases General, LakeSearch, and RAGFlow.

### 7.3.3 Knowledge Base Usage Limits

When using knowledge bases, note the following limits.

**Table 7-25 Knowledge Base Usage Limits**

| Resource | Description |
|-----|------|
| **Knowledge Base Quantity** | - Single tenant can create up to 5 knowledge bases<br>- Single agent can add 3 (expandable to 10) knowledge bases by default<br>- Single workflow can add 3 (expandable to 10) knowledge bases by default<br>- Single tenant can connect up to 5 third-party knowledge base platforms<br>- Single tenant can create up to 50 third-party knowledge bases |
| **Knowledge Base Files** | **Knowledge Documents**<br>- Total number of knowledge documents or FAQ documents uploaded to a single knowledge base shall not exceed 500<br>- Each file size shall not exceed 60MB<br>- Total file size shall not exceed 1GB<br>- When using OBS to upload knowledge documents, single file shall not exceed 128MB<br>**FAQ Documents**<br>- Total number of knowledge documents or FAQ documents uploaded to a single knowledge base shall not exceed 500<br>- Each file size shall not exceed 60MB<br>- Total file size shall not exceed 1GB<br>- When uploading Excel files, single file max 100,000 records, empty rows in the file are not allowed, data after empty rows will be ignored |
| **Knowledge Base Capacity** | The total capacity of all knowledge bases under a single tenant is max 1GB |
| **Recall Quantity** | Supports a maximum of 50 recalled text chunks |

### 7.3.4 Creating Platform Default Knowledge Base

#### 7.3.4.1 Creating a Knowledge Base

OpenJiuwen's knowledge base function performs vectorization storage and knowledge retrieval on text documents, FAQ, and other data, supporting retrieval-enhanced capabilities for applications and workflows.

This article details how to create a knowledge base, including model configuration, parsing configuration, and splitting configuration.

**Table 7-26 Creating Local Knowledge Base Process**

| No. | Process Step | Description |
|-----|---------|------|
| 1 | Create Knowledge Base | OpenJiuwen's knowledge base function performs vectorization storage and knowledge retrieval on text documents, FAQ, and other data, supporting retrieval-enhanced capabilities for applications and workflows |
| 2 | Update Knowledge Information to Knowledge Base | When creating a knowledge base, you can choose to upload local knowledge documents to the knowledge base. Upload FAQ Q&A pairs for quickly resolving questions users may encounter. The knowledge base supports batch importing FAQ Q&A pairs through uploading FAQ documents |
| 3 | Test Knowledge Base Hit Rate | OpenJiuwen evaluates the effectiveness and accuracy of the knowledge base through hit rate testing |

**Prerequisites**

The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

**Configure LakeSearch Connection Information**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, and on the "Knowledge Base" page, click "Create Knowledge Base".

**Step 4** In the "Select Creation Type" dialog, click "Default Knowledge Base Configuration" and click "OK".

**Step 5** Refer to Table 7-27 to fill in LakeSearch's relevant configuration information, and click "Test Connection".

**Table 7-27 Default Knowledge Base Configuration**

| Configuration Item | Parameter | Description | Example |
|-------|------|------|------|
| Authentication Mode | Mode Selection | Required parameter. LakeSearch connection authentication mode. Value range: Basic (basic mode, requires authentication Token), None (no authentication Token needed) | Basic |
| Connection Information | Service Address | Required parameter. External LakeSearch knowledge base connection address. LakeSearch's default port is 24462, please fill in according to the actual port | https://xxx.com |
| | Authentication Token | When "Mode Selection" is "Basic", this parameter is required. Basic Token data | Basic YWRtaW46MTIz |
| Enable OCR | OCR Document Recognition | Not enabled, cannot call OCR service for intelligent document recognition. After enabling, OCR service can be called for intelligent document recognition, such as table parsing or scanned files | Not enabled |

**Step 6** After the page shows connection success, click "OK" to complete LakeSearch knowledge base configuration.

**Create New Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, and on the "Knowledge Base" page, click "Create Knowledge Base".

**Step 4** In the "Select Creation Type" dialog, select "Default" and click "OK".

**Step 5** On the "Create New Knowledge Base" page, configure knowledge base information referring to Table 7-28.

**Table 7-28 Parameter Description**

| Parameter | Description | Example |
|-----|------|------|
| **Basic Information** | | |
| Knowledge Base Icon | Optional parameter. Default knowledge base LOGO. Click the currently displayed knowledge base icon to select a new icon file to upload in the popup dialog. Supports jpg, jpeg, png, and gif formats, size no larger than 200KB | |
| Knowledge Base Name | Required parameter. Used to identify the knowledge base. Naming rules: Can include letters, numbers, Chinese, underscores _, hyphens -, and must start with a letter, number, or Chinese. Length 1~50 characters | OpenJiuwen_Knowledge_Base_001 |
| Description | Required parameter. Brief description of knowledge base content and purpose. Naming rules: Length no larger than 100 characters | Knowledge Base |
| **Model Configuration** | | |
| Vector Model | Required parameter. A vector model is a model that converts unstructured data such as text and images into numerical vectors. For example, in the text processing stage, it slices documents and converts them to vectorized representations; in the knowledge retrieval stage, it recalls chunks based on user input information. The vector model is used to quickly identify words or sentences semantically similar to the user's input information in the massive knowledge base, performing initial information filtering, solving the "needle in a haystack" efficiency problem | embedding-zh |
| Rerank Model | Required parameter. A rerank model is a model for fine-grained sorting of retrieval results. For user input information, it sorts the chunks recalled by the vector model by relevance from high to low, presenting the top few most relevant information (e.g., Top 10) to the user. The rerank model is used to further improve the relevance accuracy of system search | rerank-zh |
| **Parsing Configuration (Optional)** | | |
| OCR Enhancement | - Not enabled, cannot call OCR service for intelligent document recognition<br>- After enabling, can call OCR service for intelligent document recognition, such as table parsing or scanned files | |
| Header/Footer Parsing | - Not enabled, parsing results do not include headers/footers<br>- After enabling, parsing results include headers/footers | |
| Table of Contents Page Parsing | - Not enabled, parsing results do not include table of contents pages<br>- After enabling, parsing results include table of contents pages | |
| Image Parsing | - Not enabled, images in documents are skipped by default, images are not processed<br>- After enabling, choose "Extract Image Text" or "Keep Original Image" as needed<br>&nbsp;&nbsp;&nbsp;&nbsp;- Extract Image Text: Recognizes text within images<br>&nbsp;&nbsp;&nbsp;&nbsp;- Keep Original Image: Only extracts and saves images, does not recognize image content, for Q&A image-text display | |
| **Splitting Configuration (Optional)** | | |
| Splitting Setting | System default is automatic splitting. Supports the following splitting strategies:<br>- Automatic Splitting: Splits according to system default preset rules and separators<br>- Length Splitting: Determines how to split based on content length<br>- Hierarchical Splitting: Splits based on the structural hierarchy of content | Automatic Splitting |

**Step 6** After configuration, click "OK" to complete knowledge base creation.

The created knowledge base is enabled by default. You can share your created knowledge base to "Asset Marketplace > Knowledge" so team members can reference these shared knowledge bases in agent development and workflow configuration scenarios, thereby improving work efficiency.

#### 7.3.4.2 Uploading Documents

After creating a knowledge base, you need to upload documents to it. The platform supports three forms of documents: knowledge documents, FAQ Q&A pairs, and FAQ documents.

- **Upload Knowledge Documents**: After knowledge documents are uploaded and parsed, users can add/edit chunks as needed to improve the knowledge base's retrieval efficiency; if users are unsatisfied with the parsing and chunking of documents in the knowledge base, they can modify the knowledge base's model configuration, parsing configuration, and splitting configuration, and re-parse and split documents in the knowledge base.
- **Upload FAQ Q&A Pairs**: FAQ (Frequently Asked Questions) Q&A pairs are common questions and their corresponding answers, used to quickly resolve questions users may encounter.
- **Upload FAQ Documents**: The knowledge base supports batch importing FAQ Q&A pairs through uploading FAQ documents. After FAQ documents are uploaded and parsed, users can add/edit chunks as needed to improve the knowledge base's retrieval efficiency.

**Prerequisites**

- A knowledge base has been created.
- The logged-in user is a space owner, space administrator, or development engineer. For details, please refer to Managing Team Space Members.

**Upload Knowledge Documents**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, and on the "Knowledge Base" page, click the desired knowledge base name in the knowledge base list to enter the knowledge base details page.

**Step 4** [Optional] On the "Tag Management" tab, you can add document tags (such as science, education, technology, etc.) for document classification. After configuring tags, you can configure tag-based document retrieval in the workflow "Knowledge Retrieval" node.

**Step 5** On the knowledge base details page, select the "Knowledge Documents" tab and click "Upload" to enter the document upload page.

**Step 6** Click "Click to Upload", and in the popup dialog, select the documents to upload. You can also configure document tags.

**Note**

- Supports multiple documents in formats: psd, tiff, bmp, gif, csv, tif, ico, md, jpeg, jpg, xlsx, pcx, dps, png, webp, ofd, docx, et, pptx, txt, pdf, ppt, doc, wps, xls
- Single document cannot be larger than 60MB
- Total number of knowledge documents and FAQ documents uploadable to a single knowledge base shall not exceed 500
- If the connected LakeSearch version is lower than 3.6.0, parsing md format files is not supported
- If the connected LakeSearch has not deployed an OCR model, parsing png, jpg, jpeg, bmp, gif format files is not supported

**Step 7** Click "OK". When the file appears in the file list, the file upload is complete.

When the file status is "Success", file parsing is complete.

**(Optional) Add Document Chunks**

**Step 1** On the knowledge base details page, select the "Knowledge Documents" tab, and click the file name whose "Status" is "Success" to enter the document details page.

The left side shows document basic information and splitting configuration information, and the right side shows document chunk information.

**Step 2** Click "Add Chunk", and set chunk information referring to Table 7-29.

**Table 7-29 Chunk Information**

| Parameter | Description | Example |
|-----|------|------|
| Chunk Title | Required parameter. Used to quickly understand each chunk's content, facilitating search and management among large numbers of chunks | 1 What is OpenJiuwen |
| Chunk Content | Required parameter. Through chunk content, users can read and understand each knowledge point or information in detail. Naming rules: Length no larger than 6000 characters | Contains "1 What is OpenJiuwen" and its sub-section "OpenJiuwen Usage Limits" content |

**Step 3** Click "OK". The newly added chunk can be viewed in the chunk information.

**(Optional) Re-parse and Split Documents**

**Step 1** On the knowledge base details page, click "Advanced Settings" in the upper right corner.

**Note**

The "Advanced Settings" option is only available when the current knowledge base's status is disabled.

**Step 2** In the popup dialog, you can modify model configuration, parsing configuration, and splitting configuration information.

**Step 3** After modification, click "OK".

**Step 4** Select the documents that need to use the new configuration for parsing chunks, and click "Retry".

**Step 5** In the popup dialog, click "Retry" to start document re-parsing and chunking.

**Step 6** Select the "Task Management" tab to view retry tasks.

**Upload FAQ Q&A Pairs**

**Step 1** On the knowledge base details page, select the "FAQ Q&A Pairs" tab and click "Create".

**Step 2** In the popup Create FAQ dialog, fill in FAQ Q&A pair information referring to Table 7-30.

**Table 7-30 Parameter Description**

| Parameter | Description | Example |
|-----|------|------|
| Standard Question | Required parameter. The most direct and clear form of the question the user might ask. Naming rules: Length no larger than 1000 characters | How to treat childhood obesity |
| Answer | Required parameter. Detailed answer provided for the standard question. Naming rules: Length no larger than 10000 characters | Once a child develops obesity, parents should first change the child's condition through exercise and diet. Let the child do exercises appropriate for their age, such as swimming, jogging, etc. Give the child more foods like apples, kiwis, carrots, etc. Prohibit the child from eating high-calorie, high-fat foods like cakes, dried fruits, cookies, etc. Strictly control the child's diet, do not let them overeat, and more exercise is beneficial for changing childhood obesity. If the situation is severe during the treatment of childhood obesity, it is recommended that parents first take the child to the hospital to check the cause of childhood obesity and then provide targeted treatment |
| Similar Question | Optional parameter. A series of questions with similar or related meanings to the standard question. Naming rules: Length no larger than 1000 characters | Treatment of childhood obesity needs to comprehensively consider diet, exercise, and behavioral changes. It is recommended to consult a professional pediatrician or nutritionist to develop a personalized treatment plan based on the child's specific situation |

**Step 3** Click "OK" to complete FAQ Q&A pair creation.

**Upload FAQ Documents**

**Step 1** On the knowledge base details page, select the "FAQ Documents" tab and click "Upload" to enter the document upload page.

**Step 2** Click "Click to Upload", and in the popup dialog, select FAQ documents that meet the "Excel Template" or "Word Template" requirements to upload.

**Note**

- Supports xlsx, xls, docx, doc file type formats
- Single file cannot be larger than 60MB
- Excel single file max 100,000 records, empty rows in the file are not allowed, data after empty rows will be ignored

**Step 3** Click "OK". When the file appears in the file list, the file upload is complete.

**Step 4** When the file status is "Success", FAQ document parsing is complete.

**Step 5** Select the "FAQ Q&A Pairs" tab to view the corresponding Q&A pair records.

**(Optional) Add FAQ Document Chunks**

**Step 1** On the knowledge base details page, select the "FAQ Documents" tab, and click the FAQ file name whose "Status" is "Success" to enter the FAQ document details page.

The left side shows FAQ document basic information and splitting configuration information, and the right side shows the Q&A pair list parsed from the FAQ document.

**Step 2** Click "Add Chunk", and set chunk information referring to Table 7-31.

**Table 7-31 Chunk Information**

| Parameter | Description | Example |
|-----|------|------|
| Chunk Title | Required parameter. Used to quickly understand each chunk's content, facilitating search and management among large numbers of chunks. Length no larger than 1000 characters | 1 What is OpenJiuwen |
| Chunk Content | Required parameter. Through chunk content, users can read and understand each knowledge point or information in detail. Length no larger than 6000 characters | Contains "1 What is OpenJiuwen" and its sub-section "OpenJiuwen Usage Limits" content |

**Step 3** Click "OK".

**More Operations**

On the knowledge base details page, other supported operations are shown in Table 7-32.

**Table 7-32 Related Operations**

| Operation | Description |
|-----|------|
| View Knowledge Documents | On the "Knowledge Documents" tab, click the specified file name to view document details. On the document details page, the following operations are supported:<br>- Edit document chunks: In the chunk information area, click "Edit" on the right to modify document chunks<br>- Delete document chunks: In the chunk information area, click "Delete" on the right to delete document chunks |
| Download Knowledge Documents | On the "Knowledge Documents" tab, click "Download" in the operation column of the knowledge file list to download knowledge documents |
| Delete Knowledge Documents | On the "Knowledge Documents" tab, click "Delete" in the operation column of the knowledge file list to delete knowledge documents |
| Edit Tags | On the "Knowledge Documents" tab, click the button in the tag column, or click "More > Edit Tags" in the operation column of the knowledge file list to modify tags |
| Edit FAQ Q&A Pairs | On the "FAQ Q&A Pairs" tab, click "Edit" in the operation column of the FAQ Q&A pair list to edit FAQ Q&A pairs |
| Delete FAQ Q&A Pairs | On the "FAQ Q&A Pairs" tab, click "Delete" in the operation column of the FAQ Q&A pair list to delete FAQ Q&A pairs |
| Download FAQ Documents | On the "FAQ Documents" tab, click "Download" in the operation column of the FAQ file list to download FAQ documents |
| Delete FAQ Documents | On the "FAQ Documents" tab, click "Delete" in the operation column of the FAQ file list to delete FAQ documents |
| Edit Document Chunks | On the "FAQ Documents" tab, click the specified file name to enter the document details page, and click "Edit" to edit document chunks |
| Delete Document Chunks | On the "FAQ Documents" tab, click the specified file name to enter the document details page, and click "Delete" to delete document chunks |


#### 7.3.4.3 Testing Knowledge Base Hit Rate

OpenJiuwen supports hit rate testing of created knowledge bases to evaluate their effectiveness and accuracy.

**Prerequisites**

Document upload has been completed.

**Hit Rate Test**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library", and select the "Knowledge Base" tab.

**Step 3** On the "Knowledge Base" page, click "Hit Rate Test" in the operation column of the knowledge base to be tested.

When the knowledge base is displayed in card form, move the mouse over the knowledge base card to be hit-tested and click "Hit Rate Test".

**Step 4** On the hit rate test page, enter a question in the text box on the left and click "Hit Rate Test".

On the right side of the page, multiple matched contents will be displayed based on different retrieval methods (semantic retrieval, keyword retrieval, hybrid retrieval, FAQ retrieval), sorted by match score in descending order.

**Step 5** Users can evaluate whether the current knowledge base meets requirements based on the score and the number of matched information.

**Step 6** Click "View History" in the upper right corner to view the user's historical questions.

**Note**

- In the history records, click the delete button on the right to delete that record
- In the history records, click the copy button on the right to copy that record's content

#### 7.3.4.4 Knowledge Base Splitting

**Knowledge Base Splitting Introduction**

Knowledge base splitting settings are mainly to improve the organization, readability, and retrieval efficiency of information. Specifically, the advantages of splitting settings include:

- **Improve Readability**: Dividing long content into multiple paragraphs, each focusing on a topic or aspect, makes it easier for readers to understand and digest information. Long texts often make readers feel fatigued, while splitting provides natural pauses, helping readers better absorb information.
- **Enhance Organization**: Through splitting, related information can be grouped together, making the knowledge base's content structure clearer. This structured organization not only helps authors maintain logical clarity when writing but also helps readers quickly find content they are interested in.
- **Improve Retrieval Efficiency**: For large knowledge bases, splitting settings can be combined with indexing, tagging, and other mechanisms to help users locate specific information faster. For example, search engines can more easily identify key content in each paragraph, thereby improving the relevance and accuracy of search results.
- **Facilitate Maintenance and Updates**: Split knowledge base content is easier to maintain and update. When information needs to be modified or added, operations can be performed on specific paragraphs without affecting other parts, helping maintain the knowledge base's accuracy and timeliness.
- **Adapt to Different Reading Habits**: Different people have different reading habits and preferences. Splitting settings can meet different users' needs, for example, some users may prefer quickly browsing titles and first sentences of paragraphs for an overview, while others may prefer to deeply read the detailed content of each paragraph.

**Splitting Strategies**

**Table 7-33 Splitting Strategies**

| Splitting Type | Automatic Splitting | Length Splitting | Hierarchical Splitting |
|---------|---------|---------|---------|
| **Splitting Principle** | OpenJiuwen can automatically split uploaded content, supporting complex layout file processing, for example:<br>- Can recognize paragraphs<br>- Can recognize headers/footers/footnotes and other non-key content<br>- Supports cross-page paragraph merging<br>- Supports parsing image information in tables<br>- Supports parsing table content in documents (currently, only table content with borders is supported) | Flexibly configures splitting identifiers, max segment length, splitting overlap, and other parameters according to user needs. Also supports setting text preprocessing rules to perform specific processing on text before splitting | Splits content into text units of different levels based on the document's table of contents structure, chapter division, and other hierarchical information |
| **Splitting Advantages** | System preset, no additional configuration needed, improving usage efficiency | Strictly controls splitting length, saving Tokens during LLM conversations | Clear structure, easy for users to understand, improving retrieval efficiency |
| **Splitting Disadvantages** | Automatic splitting effectiveness depends on document quality | Complex configuration, not suitable for users unfamiliar with document structure and parameter rules | Requires documents to have clear hierarchical structure, difficult to apply to documents with irregular structures |
| **Applicable Scenarios** | Applicable to most splitting scenarios, usually with relatively standard document structure, is the most used splitting type | Applicable to scenarios with strict splitting length requirements | Applicable to knowledge systems with clear structural hierarchy, such as technical manuals, legal provisions, standard specifications, etc. These documents typically have clear structural hierarchy, needing to be organized and retrieved by chapters, sections, etc. |

**Splitting Strategy Configuration**

- **Automatic Splitting**: System default is automatic splitting. When this strategy is selected, it automatically uses periods, semicolons, question marks, exclamation marks, and other punctuation as splitting basis, dividing the document into independent sentences or paragraphs. No other configuration items.
- **Length Splitting**: Select this splitting strategy and complete the following configuration.
    - **Splitting Identifier**: The splitting method truncates when encountering the selected symbol. Symbols have no priority between them. After final splitting, they are merged to the estimated maximum length. If the splitting identifier is not hit in custom splitting, splitting will fail. Supports Chinese period, English period, Chinese exclamation mark, English exclamation mark, Chinese question mark, English question mark, space, Chinese comma, English comma.
    - **Estimated Splitting Length**: The maximum length of splitting. If the document's body text is larger than the set maximum length, a fragment of the maximum length is taken as a new document, then backtracking the splitting overlap characters, continuing to check backward until the document ends. Value range 1~6000, default value 500.
- **Hierarchical Splitting**: Select this splitting strategy and complete the following configuration.
    - **Hierarchical Parsing Model**:
        - **Automatic Parsing**: Automatically identifies and parses data or information with hierarchical structure
        - **Rule Parsing**: Supports adding custom hierarchical rules
    - **Title Hierarchy Depth**: Refers to the set splitting title level. For example, if the text contains up to 5 levels of titles and the selected title hierarchy depth is 3, all content under level 3 titles will be merged into text blocks, and the text blocks will be split as a whole in subsequent operations. Input value must be between 1 and 10.
    - **Title Storage Method**: Refers to how title information is stored in chunks, affecting the display logic of retrieval results and index construction methods.
        - **Store Multi-title Combination**: Multi-level titles combined with specific symbols: Level1 Title-Level2 Title-Level3 Title-鈥?Text
        - **Store Last Level Title**: Only combine the last level title: Last Level Title-Text
    - **Cross-title Merging**: Enable or disable as needed.
        - Enable "Cross-title Merging": When paragraphs under different titles have little text, the platform will automatically merge them to the specified splitting length, helping to generate more comprehensive content
        - Disable "Cross-title Merging": Content under different titles will not be automatically merged
    - **Splitting Identifier**: The splitting method truncates when encountering the selected symbol. Symbols have no priority between them. After final splitting, they are merged to the estimated maximum length. If the splitting identifier is not hit in custom splitting, splitting will fail. Supports Chinese period, English period, Chinese exclamation mark, English exclamation mark, Chinese question mark, English question mark, space, Chinese comma, English comma.
    - **Estimated Splitting Length**: The maximum length of splitting. If the document's body text is larger than the set maximum length, a fragment of the maximum length is taken as a new document, then backtracking the splitting overlap characters, continuing to check backward until the document ends. Value range 1~6000, default value 500.

### 7.3.5 Connecting Third-Party Knowledge Bases

#### 7.3.5.1 Third-Party Knowledge Base Classification

Supports connecting knowledge bases from third-party systems to OpenJiuwen. Currently supported knowledge base types are shown in Table 7-34.

**Table 7-34 Third-Party Knowledge Base Classification Description**

| Knowledge Base Type | Description |
|-----------|------|
| General | General external knowledge base. Users need to first adapt the knowledge base according to the third-party general knowledge base access specification, then connect |
| LakeSearch | Can directly connect to LakeSearch knowledge base |
| RAGFlow | Can directly connect to RAGFlow knowledge base |

#### 7.3.5.2 Connecting General Knowledge Base

Currently, there are many types of knowledge bases in the industry, but there is no unified specification. For user-developed knowledge base platforms, OpenJiuwen provides a third-party general knowledge base access specification. Knowledge base developers can refer to this specification for adaptation, and then connect as a third-party knowledge base to the OpenJiuwen platform.

**Step 1 Preparation**

- The user has a self-developed knowledge base system (hereafter referred to as the third-party knowledge base), and has completed adaptation according to the third-party general knowledge base access specification. The knowledge base's service interface is published to a public IP and is accessible.
- The logged-in user is a space owner, space administrator, or development engineer
- Obtain the connection information of the established third-party knowledge base:
  a. Obtain the server interface address, i.e., the published address IP of the third-party knowledge base interface, for example, http://123.456.789.12:8080
  b. Obtain the authentication information key, which is the authentication information of the third-party knowledge base platform user, provided by the third-party knowledge base. For example, 123456789

**Note**

Users do not need to prepend Bearer to the key when entering it. The OpenJiuwen platform is responsible for the concatenation.

c. Obtain the knowledge base details page link. After logging into the third-party knowledge base platform, enter the knowledge base details page, copy the URL from the address bar, and replace the knowledge base ID with {{id}}. Taking RAGFLOW as an example below, its knowledge base details page link is: http://123.456.789.12/dataset?id={{id}}

**Note**

This connection information is used so that after connecting the third-party knowledge base, OpenJiuwen users can jump to the third-party knowledge base platform page through this link. If the third-party knowledge base only has a backend server without a web or frontend page, fill in http://xxx.com as a placeholder.

**Step 2 Connect General External Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, switch to the "External Knowledge Base Connection" page, and click "Connect External Knowledge Base".

**Step 4** In the popup dialog, set the General external knowledge base basic information referring to Table 7-35.

**Table 7-35 Parameter Description**

| Parameter | Description | Example |
|-----|------|------|
| **Basic Information** | | |
| Select Knowledge Base Type | - General<br>- RAGFlow<br>- LakeSearch | General |
| Knowledge Base Name | Used to identify the knowledge base. It is a required field when creating a knowledge base. Naming rules:<br>- Naming requirements: Only supports starting with letters, numbers, or Chinese<br>- Supported characters: Chinese, English, numbers, hyphens (-), underscores (_)<br>- Length limit: 1~50 characters | General |
| Description (Optional) | Used to briefly describe the knowledge base content and purpose | |
| Knowledge Base Icon | Knowledge base icon. Click the currently displayed knowledge base icon to select a new icon file to upload in the popup dialog. Supports jpg, jpeg, png, and gif formats, size no larger than 200KB | |
| **Connection Information** | | |
| Service Address | The address that can access the retrieval interface and query list interface, starting with https:// or http:// | |
| Authentication Information Key | The user authentication key information added to the http/https request header | |
| Knowledge Base Details Page Link | The link to the third-party General knowledge base details page, through which you can directly access the General knowledge base details page. Note that you need to use the placeholder {{id}} to represent the knowledge base ID, otherwise you cannot jump to the corresponding knowledge base page | |

**Step 5** Click "Test Connection", and a "Test Successful" prompt appears.

If "Third-party knowledge base connection failed, please check the connection address and authentication information" is displayed, please check whether the General service supports API access on the public network.

**Step 6** Click "OK" to complete the General knowledge base connection. After successful connection, you can view it in the "External Knowledge Base Connection" tab.

**Step 3 Create General Third-Party Knowledge Base**

Step 2 Connect General External Knowledge Base has been completed.

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, and on the "Knowledge Base" page, click "Create Knowledge Base".

**Step 4** In the "Select Creation Type" dialog, select "Third-party" and click "OK".

**Step 5** On the "Connect Third-Party Knowledge Base" page, click the "Select Connected Knowledge Base Type" dropdown and select the third-party knowledge base to connect.

**Step 6** In the "Knowledge Base List", check the desired knowledge bases to add, and click to add them to the "Selected Items" on the right.

**Step 7** Click "OK" to complete connecting the third-party knowledge base. After creation, you can view the connected external knowledge bases in the "Connect Third-Party Knowledge Base" page.

The created knowledge base is enabled by default.

#### 7.3.5.3 Connecting LakeSearch Knowledge Base

OpenJiuwen supports connecting external knowledge bases so users can access and utilize external knowledge resources.

**Step 1 Preparation**

- The logged-in user is a space owner, space administrator, or development engineer
- Please confirm with operations personnel that the connection between OpenJiuwen and LakeSearch has been successfully established. You need to obtain the access address, service address, account, and password from operations personnel. Ensure all information is accurate for smooth subsequent operations.

**Step 2 Connect External Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, switch to the "External Knowledge Base Connection" page, and click "Connect External Knowledge Base".

**Step 4** In the popup dialog, set LakeSearch external knowledge base basic information referring to Table 7-36.

**Table 7-36 Parameter Description**

| Parameter | Description | Example |
|-----|------|------|
| **Basic Information** | | |
| Select Knowledge Base Type | - General<br>- RAGFlow<br>- LakeSearch | LakeSearch |
| Knowledge Base Name | Used to identify the knowledge base. Naming rules:<br>- Naming requirements: Only supports starting with letters, numbers, or Chinese<br>- Supported characters: Chinese, English, numbers, hyphens (-), underscores (_)<br>- Length limit: 1~50 characters | B030_lakesearch_kv04 |
| Description (Optional) | Used to briefly describe the knowledge base content and purpose | |
| Knowledge Base Icon | Knowledge base icon. Supports jpg, jpeg, png, and gif formats, size no larger than 200KB | |
| **Connection Information** | | |
| Service Address | The address that can access the retrieval interface and query list interface | https://xxx.com |
| Username | MRS account with LakeSearch access permissions | lakesearch1 |
| User Password | Password for logging into the MRS account with LakeSearch access permissions | lakesearch1@ |
| Knowledge Base Details Page Link | The link to the third-party LakeSearch knowledge base details page, through which you can directly access LakeSearch | http://xxxxx.com/knowledge/dataset |

**Step 5** Click "Test Connection", and a "Test Successful" prompt appears.

**Step 6** Click "OK" to complete the LakeSearch knowledge base connection. After successful connection, you can view it in the "External Knowledge Base Connection" tab.

**Step 3 Create Third-Party Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, and on the "Knowledge Base" page, click "Create Knowledge Base".

**Step 4** In the "Select Creation Type" dialog, select "Third-party" and click "OK".

**Step 5** On the "Connect Third-Party Knowledge Base" page, click the "Select Connected Knowledge Base Type" dropdown and select the third-party knowledge base to connect.

**Step 6** In the "Knowledge Base List", check the desired knowledge bases to add, and click to add them to the "Selected Items" on the right.

**Step 7** Click "OK" to complete connecting the third-party knowledge base. After creation, you can view the connected external knowledge bases in the "Connect Third-Party Knowledge Base" page.

The created knowledge base is enabled by default.

#### 7.3.5.4 Connecting RAGFlow Knowledge Base

OpenJiuwen supports connecting external knowledge bases. By connecting external knowledge bases, the knowledge scope of internal knowledge bases can be significantly expanded, introducing more domains and broader information resources, thereby improving the comprehensiveness and depth of the knowledge base.

**Step 1 Preparation**

- The logged-in user is a space owner, space administrator, or development engineer
- RAGFlow server version must be 0.26.0 or above; versions below this are not supported (API and response structure have incompatible changes)
- Obtain the connection information of the third-party RAGFlow knowledge base:
  a. Create a knowledge base in RAGFlow and upload related documents
  b. Obtain RAGFlow's connection information in RAGFlow's "Personal Center > API"
  c. Select the third-party knowledge base in the knowledge base list, click to copy the knowledge base address, paste the link in a new browser window's address bar and access it to jump directly to the third-party knowledge base's details page

**Step 2 Connect RAGFlow External Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, switch to the "External Knowledge Base Connection" page, and click "Connect External Knowledge Base".

**Step 4** In the popup dialog, set external knowledge base basic information referring to Table 7-37.

**Table 7-37 Parameter Description**

| Parameter | Description | Example |
|-----|------|------|
| **Basic Information** | | |
| Select Knowledge Base Type | - General<br>- RAGFlow<br>- LakeSearch | RAGFlow |
| Knowledge Base Name | Used to identify the knowledge base. Naming rules:<br>- Naming requirements: Only supports starting with letters, numbers, or Chinese<br>- Supported characters: Chinese, English, numbers, hyphens (-), underscores (_)<br>- Length limit: 1~50 characters | B030_ragflow_kv04 |
| Description (Optional) | Used to briefly describe the knowledge base content and purpose | |
| Knowledge Base Icon | Knowledge base icon. Supports jpg, jpeg, png, and gif formats, size no larger than 200KB | |
| **Connection Information** | | |
| Service Address | The address that can access the retrieval interface and query list interface | https://xxx.com |
| APIKey | Authentication key for accessing the third-party RAGFlow knowledge base | sk-xxxxxxxx |
| Knowledge Base Details Page Link | The link to the third-party RAGFlow knowledge base details page, through which you can directly access the RAGFlow knowledge base details page. Note that you need to use the placeholder {{id}} to represent the knowledge base ID, otherwise you cannot jump to the corresponding knowledge base page | http://xxxxx.com/knowledge/dataset?id={{id}} |

**Step 5** Click "Test Connection", and a "Test Successful" prompt appears.

If "Third-party knowledge base connection failed, please check the connection address and authentication information" is displayed, please check whether the RAGFlow service supports API access on the public network.

**Step 6** Click "OK" to complete the RAGFlow knowledge base connection. After successful connection, you can view it in the "External Knowledge Base Connection" tab.

**Step 3 Create RAGFlow Third-Party Knowledge Base**

Step 2 Connect RAGFlow External Knowledge Base has been completed.

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library".

**Step 3** Select the "Knowledge Base" tab, and on the "Knowledge Base" page, click "Create Knowledge Base".

**Step 4** In the "Select Creation Type" dialog, select "Third-party" and click "OK".

**Step 5** On the "Connect Third-Party Knowledge Base" page, click the "Select Connected Knowledge Base Type" dropdown and select the third-party knowledge base to connect.

**Step 6** In the "Knowledge Base List", check the desired knowledge bases to add, and click to add them to the "Selected Items" on the right.

**Step 7** Click "OK" to complete connecting the third-party knowledge base. After creation, you can view the connected external knowledge bases in the "Knowledge Base" page.

The created knowledge base is enabled by default.

#### 7.3.5.5 Testing Third-Party Knowledge Base Hit Rate

OpenJiuwen performs hit rate testing on created knowledge bases to evaluate their effectiveness and accuracy.

**Prerequisites**

Connecting General knowledge base, connecting LakeSearch knowledge base, and connecting RAGFlow knowledge base have been completed.

**Hit Rate Test**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** In the left navigation bar, select "Development Center > Component Library", and select the "Knowledge Base" tab.

**Step 3** On the "Knowledge Base" page, click "Hit Rate Test" in the operation column of the knowledge base to be tested.

When the knowledge base is displayed in card form, move the mouse over the knowledge base card to be hit-tested and click "Hit Rate Test".

**Step 4** On the hit rate test page, enter a question in the text box on the left and click "Hit Rate Test".

On the right side of the hit rate test page, multiple matched contents will be displayed based on different retrieval methods, sorted by match score in descending order.

Users can evaluate whether the current knowledge base meets requirements based on the score and the number of matched information.

**Note**

RAGFlow knowledge base only supports semantic retrieval.

**Step 5** Click "View History" in the upper right corner to view the user's historical questions.


#### 7.3.5.6 Third-Party General Knowledge Base Access Specification

**Foreword**

This specification is intended for third-party knowledge base developers (hereafter referred to as developers). Its purpose is to provide guidance for developers to adapt to the OpenJiuwen platform, ultimately enabling third-party knowledge base content to be connected to the OpenJiuwen platform for use.

**API Interface Specification**

For API interface adaptation, developers need to add two interfaces: one for obtaining the knowledge base list, and one for retrieving the knowledge base. Developers provide external interfaces according to the interface specification, and implement key authentication, data query, knowledge retrieval, and other business logic within the interfaces, and finally return corresponding data according to the specification.

**Interface: Get Knowledge Base List**

- URI: GET /knowledge-bases
- Query Parameters

**Table 7-38 Query Parameters**

| Parameter | Required | Parameter Type | Description |
|-----|---------|---------|------|
| name | No | String | Parameter explanation: Knowledge base name, used to filter knowledge base names when listing knowledge bases. Value range: Length no more than 64 characters. Default value: N/A |
| offset | No | Integer | Parameter explanation: The pagination offset of the current request, indicating from which record to start retrieving data. Default value is 0, meaning starting from record 0. Value range: 0~65535. Default value: 0 |
| limit | No | Integer | Parameter explanation: The maximum number of data items returned per page for the current request, indicating the number of data items returned per request. Default value is 10, meaning at most 10 items per page. Value range: 1-100. Default value: 10 |

- Request Header Parameters

**Table 7-39 Request Header Parameters**

| Parameter | Required | Parameter Type | Description |
|-----|---------|---------|------|
| Authorization | Yes | String | Parameter explanation: The api-key key used for authentication, the string after concatenating "Bearer ". Example: Bearer d59******9C3, used for third-party knowledge base authentication. Value range: N/A. Default value: N/A |

- Response Parameters

**Table 7-40 Response Parameters 200**

| Parameter | Parameter Type | Description |
|-----|---------|------|
| total | Integer | Parameter explanation: Total number of knowledge bases. Value range: N/A |
| knowledge_base_list | Array of Table 7-41 | Parameter explanation: Knowledge base data information list. Note: Third-party knowledge bases should only return available knowledge bases, i.e., knowledge base data that can be externally referenced and supports retrieval at the current time. Value range: N/A |

**Table 7-41 KnowledgeBaseInfo**

| Parameter | Parameter Type | Description |
|-----|---------|------|
| knowledge_base_id | String | Parameter explanation: Knowledge base ID. Value range: N/A |
| name | String | Parameter explanation: Knowledge base name. Value range: N/A |
| description | String | Parameter explanation: Knowledge base description. Value range: N/A |

**Table 7-42 Response Parameters 400, 500, etc.**

| Parameter | Parameter Type | Description |
|-----|---------|------|
| error_code | String | Parameter explanation: Error code. Value range: N/A |
| error_msg | String | Parameter explanation: Error description. Value range: N/A |

**Interface: Retrieve Knowledge Base**

- URI: POST /knowledge-bases/retrieve
- Request Header Parameters

**Table 7-43 Request Header Parameters**

| Parameter | Required | Parameter Type | Description |
|-----|---------|---------|------|
| Authorization | Yes | String | Parameter explanation: The api-key key used for authentication, the string after concatenating "Bearer ". Example: Bearer d59******9C3, used for third-party knowledge base authentication. Value range: N/A. Default value: N/A |

- Body Parameters

**Table 7-44 Body Parameters**

| Parameter | Required | Parameter Type | Description |
|-----|---------|---------|------|
| knowledge_base_ids | Yes | Array of String | Parameter explanation: List of knowledge base IDs, used to specify the knowledge bases to be searched. Value range: List length >= 1, i.e., at least one knowledge base must be specified for retrieval. Default value: N/A |
| query | Yes | String | Parameter explanation: Search content. Value range: Length no more than 4096 characters. Default value: N/A |
| method | Yes | String | Parameter explanation: Search method. Semantic retrieval: "doc". Value range: N/A. Default value: N/A |
| offset | No | Integer | Parameter explanation: The pagination offset of the current request, indicating from which record to start retrieving data. Default value is 0, meaning starting from record 0. Value range: 0~65535. Default value: 0 |
| limit | No | Integer | Parameter explanation: The maximum number of data items returned per page for the current request. Default value is 10, meaning at most 10 items per page. Value range: 1-100. Default value: 10 |
| top_k | No | Integer | Parameter explanation: The maximum number of recall results returned by retrieval. Value range: 1-1024. Default value: 50 |
| search_threshold | No | Number | Parameter explanation: The relevance score threshold during retrieval. Default value 0.0 means no relevance score threshold is set. Value range: 0.0 - 1.0. Default value: 0.0 |
| extra_params | No | Array of Table 7-45 | Parameter explanation: Additional parameters, used to pass other parameters required by the third-party knowledge base. Value range: N/A. Default value: N/A |

**Table 7-45 KnowledgeBaseExtraParam**

| Parameter | Required | Parameter Type | Description |
|-----|---------|---------|------|
| key | Yes | String | Parameter explanation: Additional parameter key name. Value range: N/A |
| value | Yes | String | Parameter explanation: Additional parameter value. Value range: N/A |

- Response Parameters

**Table 7-46 Response Parameters 200**

| Parameter | Parameter Type | Description |
|-----|---------|------|
| total | Integer | Parameter explanation: Total number of retrieval results. Value range: N/A |
| search_result_list | Array of Table 7-47 | Parameter explanation: List of retrieval result information. Value range: N/A |

**Table 7-47 SearchChunkInfo**

| Parameter | Parameter Type | Description |
|-----|---------|------|
| knowledge_base_id | String | Parameter explanation: Knowledge base ID. Value range: N/A |
| file_id | String | Parameter explanation: File ID. Value range: N/A |
| chunk_id | String | Parameter explanation: Chunk ID. Value range: N/A |
| content | String | Parameter explanation: Text content returned by retrieval. Value range: N/A |
| score | Number | Parameter explanation: Retrieval result score. Value range: 0.0 - 1.0 |
| title | String | Parameter explanation: Text title, recommended to return the file name. Value range: N/A |

**Table 7-48 Response Parameters 400, 500, etc.**

| Parameter | Parameter Type | Description |
|-----|---------|------|
| error_code | String | Parameter explanation: Error code. Value range: N/A |
| error_msg | String | Parameter explanation: Error description. Value range: N/A |

### 7.3.6 Using Knowledge Base

#### 7.3.6.1 Using Knowledge Base in Single Agent

Supports adding reference knowledge bases in OpenJiuwen to retrieve and recall corresponding knowledge chunks based on user intent.

**Prerequisites**

- The logged-in user is a space owner, space administrator, or development engineer
- If you need to use a local knowledge base in a single agent, ensure a platform default knowledge base has been created and is enabled
- If you need to use a third-party knowledge base in a single agent, ensure a third-party knowledge base has been connected and is enabled

**Configure Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** Click "Development Center > Agent Management" in the left navigation bar, click the "Single Agent" tab in the upper left corner to enter the single-agent application management interface.

**Step 3** Click the target single-agent application, and in the "Single Agent Configuration" tab, click the add button in the "Knowledge Base" module.

**Step 4** In the "Add Knowledge Base" window, select the knowledge base type, check the target knowledge base to add, and click "OK".

**Step 5** Click the desired knowledge base and click "OK" to complete adding the knowledge base.

**Step 6** Click the configuration button in the "Knowledge Base" module to open the configuration popup.

**Step 7** Set parameters referring to Table 7-49.

**Table 7-49 Parameter Description**

| Parameter | Description | Example |
|-----|------|------|
| Knowledge Base Retrieval Strategy | Retrieval strategy, the document retrieval method, has three types:<br>- **Semantic Retrieval**: Uses vector retrieval technology to retrieve knowledge from documents and structured data, recalling chunks with high relevance to user intent. Recommended for scenarios requiring context relevance and user intent understanding<br>- **Keyword Retrieval**: Uses inverted index retrieval technology to retrieve knowledge from documents and structured data, recalling chunks with high keyword match to the Query. Recommended for scenarios requiring high user question keyword match<br>- **Hybrid Retrieval**: Uses both vector retrieval and keyword retrieval strategies to retrieve the knowledge base. Recommended for scenarios requiring both user intent understanding and keyword match | Semantic Retrieval |
| Relevance Threshold | Search results exceeding the relevance threshold will be submitted to the LLM for summarization, otherwise filtered. You can refer to the relevance scores in the knowledge base hit test to adjust this threshold. Value range: 0~1. Default value: 0.500 | 0.500 |
| Top-k Recall Quantity | The number of top-k chunks recalled by relevance threshold. For example, if top-k recall quantity is 5, the top 5 chunks by relevance will be recalled and submitted to the LLM for summarization. Value range: 1~50. Default value: 3 | 3 |
| FAQ Direct Output Threshold | FAQ retrieval results exceeding the threshold will be directly submitted to the LLM for summarization, without further document retrieval. If no results exceed the threshold, document retrieval will be performed. Value range: 0~1. After enabling FAQ functionality, the system will prioritize searching FAQ data. If no results are hit, it will continue to query chunk content, which may bring some performance overhead. When FAQ retrieval results exceed the preset threshold, they will be directly submitted to the LLM for summarization, without further document retrieval. If not exceeding the threshold, document retrieval will continue | 0.900 |
| View Source | After adding a knowledge base and enabling this feature, you can view detailed source information of search results in the preview debugging interface, including context content and file names. Helps to more quickly and accurately locate and understand search results | Enabled |
| View Images | After enabling this feature, when the knowledge base supports image retrieval, you can enable viewing image information in retrieval results | |

**Step 8** Click elsewhere to close the popup and complete configuration.

#### 7.3.6.2 Using Knowledge Base in Workflows

Supports adding reference knowledge bases in OpenJiuwen to retrieve and recall corresponding knowledge chunks based on user intent.

**Prerequisites**

- The logged-in user is a space owner, space administrator, or development engineer
- If you need to use a local knowledge base in a workflow, ensure a platform default knowledge base has been created and is enabled
- If you need to use a third-party knowledge base in a workflow, ensure a third-party knowledge base has been connected and is enabled

**Configure Knowledge Base**

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** Click "Development Center > Agent Management" in the left navigation bar, click the "Workflow" tab in the upper left corner to enter the workflow application management interface, and click your created workflow.

**Step 3** Click "Add Node" and select the "Knowledge Retrieval" node.

**Step 4** Click the node to open the node configuration page.

**Step 5** Configure input parameters. Set parameters referring to Table 7-50.

**Table 7-50 Parameter Description**

| Parameter Name | Description | Example |
|---------|------|------|
| **Input Parameters** | - Parameter name: Input parameter is fixed at only 1, type value: 1<br>- Parameter name is query and cannot be modified, type is string, representing the question for knowledge retrieval<br>- Type, value: Supports "Reference" and "Input" two types<br>&nbsp;&nbsp;&nbsp;&nbsp;- Reference: Supports users selecting output variable values of upstream nodes already included in the workflow and memory variables in global configuration. Limited to String type. Applicable to scenarios where knowledge retrieval questions need to be obtained from upstream node outputs<br>&nbsp;&nbsp;&nbsp;&nbsp;- Input: Supports users to customize input questions. Applicable to scenarios where knowledge retrieval questions are fixed | |
| **Output Parameters** | The output of the knowledge retrieval node is an object array:<br>- Parameter name is output_list, representing all knowledge chunks that meet retrieval requirements. Objects in the array have four properties:<br>&nbsp;&nbsp;&nbsp;&nbsp;- document_name, the name of the knowledge document where the chunk is located<br>&nbsp;&nbsp;&nbsp;&nbsp;- subtitle, the chunk subtitle<br>&nbsp;&nbsp;&nbsp;&nbsp;- content, the chunk content<br>&nbsp;&nbsp;&nbsp;&nbsp;- score, the chunk's match score, elements in output_list are sorted by score from high to low<br>- Subsequent nodes referencing this output parameter can reference output_list, which will obtain all retrieval results including document name, chunk subtitle, chunk content, and score. Can also directly reference chunk properties, such as content, which will obtain the first record's chunk content in output_list | |

**Step 6** Click the add button in the knowledge base area to enter the knowledge base addition page.

**Step 7** In the "Add Knowledge Base" window, select the knowledge base type, check the target knowledge base to add, and click "OK".

**Step 8** Click the configuration button in the knowledge base area to open the retrieval parameter configuration page.

**Step 9** Configure retrieval parameters. After completion, click elsewhere to close the popup.

**Table 7-51 Parameter Description**

| Parameter Name | Description | Example |
|---------|------|------|
| Retrieval Strategy | Document retrieval method, has three types:<br>- **Semantic Retrieval**: Uses vector retrieval technology to retrieve knowledge from documents and structured data, recalling chunks with high relevance to user intent. Recommended for scenarios requiring context relevance and user intent understanding<br>- **Keyword Retrieval**: Uses inverted index retrieval technology to retrieve knowledge from documents and structured data, recalling chunks with high keyword match to the Query. Recommended for scenarios requiring high user question keyword match<br>- **Hybrid Retrieval**: Uses both vector retrieval and keyword retrieval strategies to retrieve the knowledge base. Recommended for scenarios requiring both user intent understanding and keyword match | Semantic Retrieval |
| Relevance Threshold | Search results exceeding the relevance threshold will be submitted to the LLM for summarization, otherwise filtered. You can refer to the relevance scores in the knowledge base hit test to adjust this threshold. Value range: 0~1. Default value: 0.5 | 0.500 |
| Top-k Recall Quantity | The number of top-k chunks recalled by relevance threshold. For example, if top-k recall quantity is 5, the top 5 chunks by relevance will be recalled and submitted to the LLM for summarization. Value range: 1~50. Default value: 3 | 3 |
| FAQ Direct Output Threshold | FAQ retrieval results exceeding the threshold will be directly submitted to the LLM for summarization, without further document retrieval. If no results exceed the threshold, document retrieval will be performed. Value range: 0~1. After enabling FAQ functionality, the system will prioritize searching FAQ data. If no results are hit, it will continue to query chunk content, which may bring some performance overhead. When FAQ retrieval results exceed the preset threshold, they will be directly submitted to the LLM for summarization, without further document retrieval. If not exceeding the threshold, document retrieval will continue | 0.900 |
| View Images | After enabling this feature, when the knowledge base supports image retrieval, you can view image information in retrieval results | |

**Step 10** On the knowledge retrieval configuration page, click "OK" to complete the knowledge retrieval node configuration.

### 7.3.7 Managing Knowledge Base

After knowledge base creation, on the "Knowledge Base" page, you can find knowledge bases through category filtering (all types, default, and third-party) or search (by name and source) functions.

Knowledge bases support list and card display. Click the list button to the right of the search box to display knowledge bases in list form. Click the card button to the right of the search box to display knowledge bases in card form.

**Table 7-52 Related Operations**

| Operation | Description |
|-----|------|
| Enable Knowledge Base | - When knowledge bases are displayed in list form, find the knowledge base whose "Status" is "Disabled", click "Enable" in the operation column to enable the knowledge base<br>- When knowledge bases are displayed in card form, find the knowledge base whose "Status" is "Disabled", move the mouse over the knowledge base card to be enabled and click "Enable" to enable the knowledge base<br>**Note**: Only knowledge bases with "Status" as "Enabled" can be referenced in applications and workflows |
| Disable Knowledge Base | **Note**: Disabling a knowledge base that has been referenced by applications and workflows will cause retrieval results to return empty values, please operate with caution<br>- When knowledge bases are displayed in list form, find the knowledge base whose "Status" is "Enabled", click "Disable" in the operation column to disable the knowledge base<br>- When knowledge bases are displayed in card form, find the knowledge base whose "Status" is "Enabled", move the mouse over the knowledge base card to be disabled and click "Disable" to disable the knowledge base |
| Hit Rate Test | - When knowledge bases are displayed in list form, click "Hit Rate Test" in the operation column to test the knowledge base hit rate<br>- When knowledge bases are displayed in card form, move the mouse over the knowledge base card to be hit-tested and click "Hit Rate Test" to test the knowledge base hit rate<br>**Note**: Only knowledge bases with "Status" as "Enabled" can be hit-tested |
| Edit Knowledge Base | Editing knowledge base can modify "Knowledge Base Icon", "Knowledge Base Name", "Knowledge Base Description"<br>- When knowledge bases are displayed in list form, click "More > Edit" in the operation column to edit the knowledge base<br>- When knowledge bases are displayed in card form, move the mouse over the knowledge base card to be edited and click "Edit" to test the knowledge base hit rate<br>**Note**: Only platform default knowledge bases with "Status" as "Disabled" can be edited |
| Cancel Connection | - When knowledge bases are displayed in list form, click "More > Cancel Connection" in the operation column to cancel the external knowledge base connection<br>- When knowledge bases are displayed in card form, move the mouse over the knowledge base card to be disconnected and click "Cancel Connection" to cancel the external knowledge base connection<br>**Note**: Only external knowledge bases with "Status" as "Disabled" can be disconnected |
| Advanced Settings | Advanced settings can modify "Model Configuration", "Parsing Configuration", "Splitting Configuration (Optional)"<br>- When knowledge bases are displayed in list form, click "More > Advanced" in the operation column to edit the knowledge base<br>- When knowledge bases are displayed in card form, move the mouse over the knowledge base card to be configured and click "Advanced" to edit the knowledge base<br>**Note**: Only platform default knowledge bases with "Status" as "Disabled" can modify advanced settings |
| View References | You can view which agents and workflows reference the current knowledge base. There are three viewing methods:<br>- When knowledge bases are displayed in list form, click "More > View References" in the operation column to view which agents and workflows reference the knowledge base<br>- When knowledge bases are displayed in card form, move the mouse over the knowledge base card to be viewed and click "View References" to view which agents and workflows reference the knowledge base<br>- On the knowledge base details page, click "Reference List" in the upper right corner to view which agents and workflows reference the knowledge base<br>**Note**: Clicking the agent or workflow name in the reference list will jump to the specific application details |
| Delete Knowledge Base | **Note**: Deleting an application is a high-risk operation. Before deletion, ensure this knowledge base is no longer in use<br>- When knowledge bases are displayed in list form, click "More > Delete" in the operation column to delete the knowledge base<br>- When knowledge bases are displayed in card form, move the mouse over the knowledge base card to be deleted and click "Delete" to delete the knowledge base<br>**Note**: Only default knowledge bases with "Status" as "Disabled" can be deleted |
| Edit External Knowledge Base Connection Information | - When knowledge bases are displayed in list form, in the "External Knowledge Base Connection" tab, click "Edit" in the operation column of the knowledge base list to edit external knowledge base connection information<br>- When knowledge bases are displayed in card form, in the "External Knowledge Base Connection" tab, move the mouse over the knowledge base card to be edited and click "Edit" to edit external knowledge base connection information |
| Delete External Knowledge Base Connection Information | - When knowledge bases are displayed in list form, in the "External Knowledge Base Connection" tab, click "Delete" in the operation column of the knowledge base list to delete external knowledge base connection information<br>- When knowledge bases are displayed in card form, in the "External Knowledge Base Connection" tab, move the mouse over the knowledge base card to be deleted and click "Delete" to delete external knowledge base connection information |


## 7.4 Prompts

### 7.4.1 Prompt Introduction

#### Prompt Introduction

A prompt is a text instruction input by the user to the LLM to guide the model in generating specific output. Prompt design directly affects the quality of the model's responses and is a key tool for optimizing model performance. Through different prompt words, you can test the model's performance in scenarios such as semantic understanding and logical reasoning, helping users discover and solve common sense errors, logical gaps, and other issues.

The platform's asset center provides rich prompt templates, covering various application scenarios such as conversational Q&A, copywriting generation, etc., supporting quick reference by users. Users can also customize and create prompts based on specific needs.

#### Basic Elements of Prompts

You can get many results through simple prompts, but the quality of the results depends on the amount and completeness of the information you provide. A prompt can contain instructions or questions that you pass to the model, as well as other types of information such as context, input, or examples. You can use these elements to better guide the model and therefore get better results. Prompts mainly include the following elements:

- **Instruction**: Clearly tell the model what task to execute, such as summarize, extract, or generate content.
- **Context**: Provide additional information or background to help the model better understand the task.
- **Input Data**: Specific content or questions provided by the user.
- **Output Indication**: Specify the type or format of the output to ensure the result meets expectations.

The format required for a prompt depends on the type of task you want the language model to complete. Not all of the above elements are required.

#### Prompt Types

When building and using agents, prompts are divided into two categories: prompts in the Asset Marketplace and Component Library prompts. Understanding the difference and role of both helps users better design and utilize agents.

**Prompts in the Asset Marketplace**: Prompts in the Asset Marketplace are the initial parameters and behavioral guidelines set by developers for the LLM when building agents. It defines the agent's persona and response logic, having a continuous impact on the model's response pattern throughout the conversation. Through carefully written system prompts, you can set specific role positioning and response logic for the LLM, making it exhibit expected behavior when interacting with users.

**Component Library Prompts**: Refers to specific instructions or questions directly given by the user when conversing with the agent, used to guide the LLM to complete specific tasks or provide needed information. To help the model more accurately understand and respond to needs, prompts should be kept concise and clear, avoiding ambiguity, making communication more efficient.

Assuming you need to build a travel assistant, the following are examples of Asset Marketplace prompts and Component Library prompts:

- **Asset Marketplace Prompt**: "You are a friendly and professional travel planning assistant, focused on providing users with detailed travel advice and information. When answering users' questions, your answers should be both comprehensive and practical, while maintaining a friendly and encouraging tone. Please ensure all recommended attractions and activities are safe and suitable for users' travel preferences."
- **Component Library Prompt**: "I plan to travel to Beijing next month, what are the must-visit attractions and food recommendations?"

### 7.4.2 Prompt Writing Guidelines

#### Recommendations for Writing Prompts

Clear and explicit prompts can significantly improve the output quality of LLMs, reduce error rates, and meet specific needs. It is recommended to master relevant techniques before writing.

- **Clarify Goals and Tasks**: Before writing prompts, clarify the goals and tasks of the agent or LLM, ensuring the prompt directly points to expected behavior.
- **Clarity**: Prompts should clearly express the goal, avoiding ambiguity. For example: Don't write "Tell me about health", instead write "Please describe how to maintain a healthy lifestyle".
- **Accuracy**: Prompts should be fact-based, avoiding incorrect or misleading content. For example: In medical scenarios, avoid using inaccurate medical terminology or incorrect health advice.
- **User Friendliness**: Prompts should use simple, easy-to-understand language, avoiding professional terminology or complex expressions. For example: Don't write "Please provide your medical history and allergy history", instead write "Have you had any diseases or drug allergies?".
- **Diversity**: Prompts should be able to handle various user expression methods, such as different wordings, tones, or language styles.
- **Use Context**: When writing prompts, relevant context information can be included to help the agent or LLM understand the task background.
- **Feedback and Iteration**: Continuously adjust and optimize prompts based on user feedback to ensure they meet user needs.
- **Testing and Validation**: Before publishing, comprehensively test prompts to ensure they work properly in various situations.
- **Comply with Ethical and Legal Standards**: When writing prompts, ensure they comply with ethical and legal standards, including but not limited to protecting user privacy, avoiding discriminatory language or behavior, and ensuring fairness and inclusivity.

### 7.4.3 Creating Prompts

In the process of building Agent applications, setting prompts is a crucial step. Prompts aim to provide the model with clear task goals, standardize output format, optimize generated content, and meet personalized needs. Through careful design and optimization of prompts, you can ensure the Agent's generated content meets specific styles and requirements.

When writing prompts, you can set prompt variables. That is, by adding placeholders {{ }} in the prompt to represent dynamic information, letting the model generate different text based on different situations, increasing the model's flexibility and adaptability. When viewing prompt effects, you can replace the value of {{location}} to get model answers, improving evaluation efficiency.

Prompts are important guidance information for LLMs and play a key role in agent development and workflow configuration scenarios.

The platform not only supports creating individual prompts but also supports batch importing prompts, helping you more efficiently manage and use prompts, improving work efficiency.

#### Constraints and Limitations

**Table 7-53** Usage Limits

| Limit | Description |
|-----|------|
| Prompt Content Length | A single prompt's input prompt content can contain up to 20,000 characters. |
| Prompt Template Import Quantity | Up to 100 prompt templates can be imported at a time. |
| Prompt Template Export Quantity | Up to 100 prompt templates can be exported at a time. |
| Prompt Template Quantity | Created prompt templates cannot exceed 500. |
| Prompt Variable Name Length | A single variable name cannot exceed 20 characters. |
| Prompt Variable Quantity | A single prompt can contain up to 50 variables. |
| Prompt Variable Content | A single variable's content cannot exceed 2,000 characters. |

#### Creating a Single Prompt

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 3** Click "Create Prompt" in the upper right corner of the prompt management interface.

**Step 4** On the "Create Prompt" page, set the prompt according to the prompts and click "OK".

**Table 7-54** Create Prompt

| Parameter | Description | Example |
|-----|-----|-----|
| Name | Required parameter. Travel<br><br>Used to identify the prompt's content. | |
| Industry | Required parameter. General<br><br>Used to identify the prompt's application field or background.<br><br>**Value range**:<br>- Finance<br>- Internet<br>- Education<br>- General<br>- Medical<br>- Government<br>- Manufacturing<br>- Life Services<br>- Academic Research<br>- Copywriting Creation | |
| Type | Used to describe the variable types included in the prompt.<br><br>**Value range**:<br>- Text: Indicates the prompt can contain text variables. Text variables can be any text content, such as sentences, paragraphs, keywords, etc.<br>- Multimodal: Indicates the prompt can contain text variables and image variables. Text variables and image variables can be used in combination to provide richer information. | Text |
| Tags (Optional) | Used to classify or mark prompts for subsequent management and search.<br><br>**Value range**:<br>- Q&A<br>- Classification<br>- Generation<br>- Summary<br>- Translation | Q&A, Classification |
| Description (Optional) | Supplementary explanation of the prompt. | Travel-type prompt |
| Prompt | The prompt is content used to guide the model in generation. Written prompts should include key information about the task or domain, such as topic, style, format, etc.<br><br>When writing prompts, you can set prompt variables. Enter {{ }} in the prompt to reference variables or click the reference button in the upper right corner of the prompt editor to insert text variables or image variables. | You are a travel assistant and need to introduce the local customs of the travel destination to users. Please introduce the local customs of {{location}}. |

**Step 5** After creation, you can view the created prompt in the "Prompts" tab of the "Development Center > Component Library > Prompts" page.

------

#### Batch Importing Prompts

**Step 1** On the "Prompts" page, select the "Prompts" tab and click "Import" in the upper right corner of the page.

**Step 2** In "Import Prompt Templates", click "Add File" to select the file to import.

> **Note**
>
> - The number of data entries in the imported file should not exceed 100; exceeding this quantity will not be allowed for import.
> - The imported file template names must not duplicate existing file template names.
> - The imported file is limited to xls and xlsx formats, file size must not exceed 20MB.
> - Select prompt template file for import, supports downloading templates.

**Step 3** Click "Import". Successfully imported prompts will be displayed on the "Prompts" page.

------

#### More Operations

After creating prompts, on the "Prompts" page, you can find prompts through category filtering (by industry and tags) or search (by name, content, and ID) functions. Additionally, you can delete, modify, and perform other operations on prompts. For details, please see Managing Prompts.

### 7.4.4 Optimizing Prompts

The optimize prompt function not only improves the accuracy and response quality of model answers but also significantly enhances user experience and work efficiency, adapting to various application scenarios and needs, and supports continuous improvement and iteration. Through the optimize prompt function, you can add variables to prompts, enabling quick reuse in different scenarios. Additionally, by adding data evaluation sets and supplementing prompt background knowledge, you can help the model better understand prompts. Multi-scenario evaluation data makes prompt instructions more specific and output more in line with expectations.

After successfully executing a prompt optimization task, you can easily discover quality prompts through the view operation and save them to Component Library prompts for reference in agent development and workflow configuration scenarios.

#### Constraints and Limitations

When creating a prompt optimization task, the number of variable data evaluation sets cannot exceed 500.

#### Optimizing Prompts

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 3** On the "Prompts" page, select the "Optimization Tasks" tab and click "New Optimization Task".

**Step 4** Fill in information and test case sets, as shown in Figure 7-115.

1. In the form on the left, enter the task name and description.
2. Select the model to use. For connected model services, see Models.
3. Select the optimization task type:
- Text: Indicates the prompt can contain text variables. Text variables can be any text content, such as sentences, paragraphs, keywords, etc.
- Multimodal: Indicates the prompt can contain text variables and image variables. Text variables and image variables can be used in combination to provide richer information.
4. In the prompt input box, enter your prompt. The prompt can contain variables. Enter {{ }} in the prompt or click the reference button in the upper right corner of the prompt editor to insert text variables or image variables.
5. Set variable data evaluation sets.

   Expected output is mainly used in the evaluation set to help the model learn more effectively and guide the optimization direction of the prompt, making the model's answers more in line with expectations. It is recommended to provide expected outputs for various scenarios to promote the model's learning.

- **Manually Add Cases**: When the prompt contains variables, in the "Variable Data Evaluation Set" area on the right, click the "Add Case" button to manually enter the specific content of variables and expected output results. After adding each case, click "Save" to save the added case.
- **Batch Import Cases**: If you have previously created case sets, you can select the "Import" button to batch upload cases. The system will automatically combine the variables in the selected dataset with your prompt.

> **Note**
>
> - Imported data should not exceed 500 entries; exceeding this quantity will not be allowed for import.
> - If the imported data contains records that are exactly the same as existing data in the system, these records will not be imported again.
> - Imported files only support zip format.

6. After completing the above settings, click "Next" to continue with subsequent operations.

**Step 5** Configure optimization strategy.

1. In basic configuration, set the prompt optimization model, task start time, and maximum optimization rounds.

**Table 7-55** Basic Configuration

| Parameter | Parameter Description | Example |
|-----|---------|-----|
| Prompt Optimization Model | Select the model service used for this prompt in the dropdown. For connected model services, see Models. | |
| Task Start Time | Used to set the optimization task start time.<br><br>- Start Immediately: The optimization task will start after configuration is completed.<br>- Start Later: The optimization task will start executing at the user-specified time. | Start Immediately |
| Maximum Optimization Rounds | Indicates the maximum number of times the system will attempt to optimize the prompt. More optimization rounds can improve optimization effectiveness but increase optimization time.<br><br>**Value range**: 0~20 | 1 |

2. Task Configuration:

**Table 7-56** Task Configuration

| Parameter | Parameter Description | Example |
|-----|---------|-----|
| Number of Prompt Examples | Adding specific reply examples to the prompt will improve the LLM's understanding and answer accuracy. The more examples, the more precise the answers, but the more tokens consumed.<br><br>**Value range**: 0~5 | 3 |
| Task Type | Classification method for optimization tasks.<br><br>- Subjective Task: Suitable for creative scenarios without standard answers, optimizing with explicit subjective preferences.<br>- Objective Task: Suitable for classification or intent recognition scenarios with standard answers, optimizing with explicit objective criteria. | Subjective Task |

3. Advanced Configuration:

**Table 7-57** Advanced Configuration

| Parameter | Parameter Description | Example |
|-----|---------|-----|
| Scoring Criteria | Used to supplement the output scoring criteria, for example, whether order matters, what key points the answer should include, etc. Can be combined with optimization task details - scoring reasons to set scoring rules based on specific task requirements.<br><br>**Value range**: No more than 1000 characters. | 0 points: Text piling, unsupported exaggerated expressions<br>3 points: Contains food ingredients<br>5 points: Contains food ingredients and finished product characteristics |
| Background Knowledge | Used to supplement some domain-specific knowledge for the prompt optimization model. The model can choose whether to add this knowledge to the prompt to improve the task execution effect.<br><br>**Value range**: No more than 1000 characters. | Egg pancake recipe:<br>Crack eggs into a bowl, add a little salt, stir well; add flour, then add appropriate amount of water, stir into a batter without lumps, then add chopped green onion (can be replaced with zucchini, carrot, ham, etc.), stir well; add a little oil to a hot pan, pour the batter into the center of the pan, slowly shake the pan to spread the batter evenly into a circle (or use a spatula to slowly spread); cook over low heat, flip to the other side after one side is set, fry until both sides are golden brown and serve. |

**Step 6** Click "Create Now".

After creation, you can view the created prompt optimization task in the "Optimization Tasks" tab of the "Development Center > Component Library > Prompts" page.

------

#### More Operations

After creating a prompt optimization task, on the "Optimization Tasks" page, you can find prompt optimization tasks through task status and task type filtering functions, or use keyword search functions. Additionally, you can delete, edit, and perform other operations on prompt optimization tasks. For details, please see Managing Prompts.

### 7.4.5 Managing Prompts

Prompts can be saved as a reusable resource in the resource library. Through team sharing of this resource library, the efficiency and effectiveness of calling the Large Language Model (LLM) can be unified and improved. This document details how to delete, edit, and perform other operations on prompts/prompt optimization tasks in the resource library to ensure continuous updating and optimization of the resource library.

#### Prerequisites

- Prompts have been created.
- Prompt optimization tasks have been created.

#### Viewing Prompts

**Step 1** Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

**Step 2** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 3** On the "Prompts" page, select the prompt to view.

**Step 4** Click the prompt card, and in the popup "View Prompt" dialog, you can view the prompt template's creation time, tags, content, etc., as shown in Figure 7-117.

Click "Copy" to copy the template content.

------

#### Deleting Prompts

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Prompts" tab, find the prompt to delete, move the mouse over the prompt card, and click the "Delete" button below the card.

**Step 3** In the popup dialog, click "OK" to complete the prompt deletion.

------

#### Editing Prompts

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Prompts" tab, find the prompt to edit, move the mouse over the prompt card, and click the "Edit" button below the card.

**Step 3** Make corresponding modifications referring to Table 7-54.

**Step 4** After modification, click "OK" to complete the prompt editing.

------

#### Optimizing Prompts

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Prompts" tab, find the prompt to optimize, move the mouse over the prompt card, and click the "Optimize" button below the card.

**Step 3** Please refer to Optimizing Prompts for corresponding optimization.

------

#### Exporting Prompts

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Prompts" tab and click "Export".

**Step 3** (Optional) On the "Export" page, you can view the prompt list. Click the settings button above the prompt list to make basic settings for the prompt list, then click "OK".

- **Table Content Wrapping**:
    - When enabled, prompt list cell content will automatically wrap. When the text length in a cell exceeds the cell width, the text will wrap within the cell.
    - When disabled, prompt list cell content will not automatically wrap. When the text length in a cell exceeds the cell width, the text will be truncated within the cell instead of wrapping.
- **Table Data Column Fixing**:
    - Not Fixed: All columns can scroll horizontally. When scrolling the table horizontally, all columns move synchronously.
    - Fix First Column: The first column is fixed on the left side of the table, other columns can scroll horizontally, while the first column always stays in place.
    - Fix First Two Columns: The first two columns are fixed on the left side of the table, other columns can scroll horizontally, while the first two columns always stay in place.
- **Custom Display Columns**: Supports displaying "Prompt" and "Description" columns. Users can customize display columns by clicking the checkboxes before prompt and description.

**Step 4** On the "Export" page, check the checkboxes before prompts and click "Export". Prompts will be downloaded as an xlsx format file to your local machine.
> **Note**
>
> When exporting multiple prompts, different prompts will be presented in the same xlsx file.

------

#### Deleting Prompt Optimization Tasks

When the optimization task status is Draft, Pending Optimization, Optimization Successful, Optimization Failed, or Paused, deleting prompt optimization tasks is supported.

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Optimization Tasks" tab, find the prompt optimization task to delete, and click "Delete" in the operation column of that task.

**Step 3** In the popup dialog, click "OK" to complete the prompt optimization task deletion.

------

#### Editing Prompt Optimization Tasks

When the optimization task status is Draft, editing prompt optimization tasks is supported.

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Optimization Tasks" tab, find the prompt optimization task to edit, and click "Edit" in the operation column of that task.

**Step 3** Refer to Optimizing Prompts for corresponding modifications.

**Step 4** After modification, click "OK" to complete the optimization task editing.

------

#### Viewing Prompt Optimization Tasks

When the optimization task status is Optimization Successful, viewing prompt optimization task details is supported. On the "Optimization Tasks" details page, users can compare the effects of original and optimized prompts, easily find high-quality prompts, and publish them to "Prompts" for quick calling and reuse in subsequent work.

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Optimization Tasks" tab, find the prompt optimization task whose details you want to view, and click "View" in the operation column of that task.

**Step 3** On the task details page, you can view the task's basic information, optimization configuration information, and comparison effects before and after optimization.

- Click "Re-optimize" in the upper right corner to re-optimize prompts with unsatisfactory target accuracy. For re-optimization steps, please refer to Optimizing Prompts.
- Click the "Complete" button in the upper right corner, and in the popup dialog:
    - Check the "Don't remind again" checkbox, then click "Save". After the prompt is saved successfully, you will return to the prompt optimization task list page.
    - Click "Save", and for subsequent operations, please refer to steps 2 and 3.
- **Highlight Differences**: When enabled, you can quickly identify the differences between the pre-optimization and post-optimization versions, helping users more intuitively understand the differences in semantic expression, tone style, guidance direction, or generation effect of each prompt.
- When the "Maximum Optimization Rounds" parameter is set to greater than 1, click the dropdown to view each iteration's details.

- Click the evaluation button of the original prompt or optimal prompt to view the evaluation set assessment details, such as system answer, expected answer, model score, scoring reason, etc.

- Click the copy button to copy the optimized prompt.
- Click "Save Prompt" to save the optimized prompt to Prompts for reference in agent development and workflow configuration scenarios. The steps for saving a prompt are as follows:
  a. Click "Save Prompt".
  b. Fill in the prompt information referring to Table 7-54.

  c. After filling in, click "OK". The platform will create a new prompt.

------

#### Retrying Prompt Optimization Tasks

When the optimization task status is Optimization Failed, restarting prompt optimization tasks is supported.

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Optimization Tasks" tab, find the prompt optimization task to retry, and click "Retry" in the operation column of that task to complete the optimization task retry.

------

#### Pausing Prompt Optimization Tasks

When the optimization task status is Optimizing, pausing prompt optimization tasks is supported.

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Optimization Tasks" tab, find the prompt optimization task to pause, and click "Pause" in the operation column of that task to complete the optimization task pause.

------

#### Creating Prompt Optimization Task Copies

When the optimization task status is Optimizing, Pending Optimization, Optimization Successful, or Optimization Failed, creating prompt optimization task copies is supported. Creating optimization task copies can serve as backups. If the original task encounters problems, you can quickly restore to the pre-optimization state.

**Step 1** Click "Development Center > Component Library" in the left navigation bar, click the "Prompts" tab in the upper left corner to enter the prompt management interface.

**Step 2** On the "Prompts" page, select the "Optimization Tasks" tab, find the prompt optimization task for which you want to create a copy, and click "Create Copy" in the operation column of that task. A new task with "Copy" appended to the original task name is generated, completing the copy creation.

------

### 7.4.6 Setting Prompts for Agents and Workflows

In actual business scenarios, the application of LLMs requires clear task instructions to achieve efficient configuration. However, when directly using LLMs for complex tasks, you may face inaccurate output and results that do not match business needs. How to effectively guide LLMs to complete specific tasks? As a natural language instruction, prompts provide a solution to this problem.

Prompts are key guidance information for LLMs, playing an important role especially in agent development and workflow configuration scenarios.

#### Prerequisites

- A single-agent application has been created.
- A workflow has been created.
- A prompt has been created.

#### Setting Prompts for Single-Agent Applications

Write prompts according to business needs. The clearer and more explicit the prompt, the more the agent's replies will meet expectations.

- **Directly Write Prompts**
  a. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
  b. Click "Development Center > Agent Management" in the left navigation bar, click the "Single Agent" tab in the upper left corner to enter the single-agent application management interface.
  c. Click the desired single-agent application card or create a new single-agent application to enter the orchestration page.
  d. Write the prompt in the prompt panel.

- **Role Instruction Template**

  The platform provides prompt templates that can be referenced for writing prompts.

  a. In the prompt panel, click the "Role Instruction Template" icon.

  b. Fill in the prompt according to the template in the prompt editor.

  c. After using the prompt, the system will automatically fill the selected prompt into the prompt editor. You can modify the prompt based on the business scenario. When modifying the prompt, you need to focus on the underlined parts. You need to add text content according to the blank guidance of the editing block.

- **Reference Template**

  OpenJiuwen has preset multiple prompt templates for different scenarios. You can use templates directly or reference them for writing prompts.

  > **Note**
  >
  > - Before referencing "Prompts", ensure prompts have been created in the resource library. For specific steps, please refer to Creating Prompts.
  > - Preset prompt data source is the asset center. Before referencing, you can view preset prompts in the asset center.

  a. In the prompt panel, click the "Reference Template" icon.

  b. In the prompt template popup, you can select "Prompt Marketplace" or "Component Library Prompts".

  c. After selecting a prompt template, click "OK". The system will automatically fill the selected prompt template into the prompt editor. Users can modify the prompt based on the business scenario.

- **AI-Generated Prompts**

  You can tell the AI in natural language what prompt you want to write or optimize. The LLM will automatically generate a prompt based on the input description.

  a. In the "Prompt" panel's editor, enter the prompt you want to write, such as "You are an intelligent customer service assistant".
  b. In the upper right corner of the "Prompt" panel, click "Smart Optimize Prompt". The AI will then generate an optimized prompt.

  c. Click "Confirm Replace" to input the prompt content into the prompt editor.

- **Reference Variables**

  In mode-priority mode, when the user adds memory and creates variables for the application, the created variables can be selected in the prompt for quickly defining a user's behavior or preference. Users can also input variables in the prompt input box.

For specific operations on referencing prompts in single agents, please refer to Configuring Prompts.

#### Setting Prompts for Workflow Applications

When using LLM nodes in workflows, you need to set prompts for these nodes, letting the LLM execute tasks as needed.

> **Note**
>
> Intent recognition, advanced intent recognition, questioner, and Agent nodes in workflows also need to have prompts set.

- **Directly Write Prompts**
  a. Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.
  b. Click "Development Center > Agent Management" in the left navigation bar, click the "Workflow" tab in the upper left corner to enter the workflow application management interface.
  c. Click the desired workflow application card or create a new workflow application to enter the orchestration page.
  d. In the workflow canvas, click the LLM node, and write "System Prompt" or "User Prompt" in the "Prompt Configuration" of the LLM node popup.

- **Reference Template**

  OpenJiuwen has preset multiple prompt templates for different scenarios. You can use templates directly or reference them for writing prompts.

  > **Note**
  >
  > - Before referencing "Prompts", ensure prompts have been created in the resource library. For specific steps, please refer to Creating Prompts.
  > - Preset prompt data source is the asset center. Before referencing, you can view preset prompts in the asset center.

  a. In the prompt configuration, click the "Reference Template" icon for system prompt or user prompt.

  b. In the prompt template popup, you can select "Prompt Marketplace" or "Component Library Prompts".

  c. After selecting a prompt template, click "OK". The system will automatically fill the selected prompt template into the prompt editor. Users can modify the prompt based on the business scenario.

- **AI-Generated Prompts**

  You can tell the AI in natural language what prompt you want to write or optimize. The LLM will automatically generate a prompt based on the input description.

  a. In the "System Prompt" or "User Prompt" editor, enter the prompt you want to write, such as "You are an intelligent customer service assistant".
  b. In the upper right corner of "System Prompt" or "User Prompt", click "Smart Optimize Prompt". The AI will then generate an optimized prompt.

  c. Click "Confirm Replace" to input the prompt content into the prompt editor.

For specific operations on referencing prompts in workflows, please refer to LLM, Agent, Intent Recognition, Advanced Intent Recognition, and Questioner.


# 8 Models

## 8.1 Model Introduction

Model Serving provides core reasoning capabilities for agents and is the foundation for agents to achieve autonomous decision-making and task execution. In OpenJiuwen, you can connect LLMs to agents through model services, enabling them with text conversation, image understanding, vectorization, and other capabilities.

### Model Service Classification

To meet the technical capabilities, business scenarios, and needs of different users, OpenJiuwen provides diverse model service modes. The following introduces various model services from the perspective of model sources, as shown in Table 8-1.

**Table 8-1 Model Service Classification Introduction**

| Classification | Description | Applicable Scenarios |
|------|------|----------|
| Custom Access Model | Connects model service APIs deployed by users or provided by third parties. Requires using specific models or having self-built/third-party model services. For specific operations, please refer to Connecting Custom Models. | Connecting Custom Models |

## 8.2 Connecting Custom Models

### 8.2.1 Custom Model Connection Process

#### Overview

OpenJiuwen supports connecting model service APIs deployed by users or third parties in external environments. Compared to using platform preset models, connecting custom model services has the following advantages:

- Optimize personalized experience: Connect customized models based on business characteristics, reducing users' search and selection time, providing a more smooth and efficient user experience. For example, search engines can provide more precise search results based on users' search history and preferences.
- Enhance domain-specific accuracy: Connecting professional domain model services can significantly improve output accuracy in specific scenarios. For example, connecting a professional medical model in the medical domain can provide more accurate diagnostic recommendations.
- Improve development efficiency: Developers do not need to build complex models from scratch and can directly connect existing high-quality model service APIs to quickly integrate LLM capabilities.

#### Connection Process

OpenJiuwen supports connecting model service APIs deployed by users or third parties in external environments. Before connecting, you must first add the model provider, then connect the model services it provides. The complete process for connecting custom model services is shown in Figure 8-1.

**Table 8-2 User Custom Model Provider Service Usage Process Details**

| No. | Process Step | Description |
|------|----------|------|
| 1 | Connect Model Provider | Before connecting model services, the model provider must first be registered to the OpenJiuwen platform. For specific operations, please refer to Connecting Model Providers. |
| 2 | Connect Model Service | After the model provider is connected, connect its provided model service API to the OpenJiuwen platform. For specific operations, please refer to Connecting Model Services. |
| 3 | Test Model | Perform actual calls, parameter adjustments, and effect observations on the model, verifying its functional performance and performance indicators in specific scenarios, ensuring stable operation in real business scenarios. For specific operations, please refer to Testing Models. |
| 4 | Configure Model Routing Strategy (Optional) | When multiple model services of the same type are connected, it is recommended to configure routing strategies for automatic failover. After the routing strategy is created, it is recommended to test the routing entry to verify whether failover takes effect. For specific operations, please refer to Configuring Model Routing Strategies. |
| 5 | Use Model Service | After the model service is connected, it can be used in agents and workflows. Please refer to Developing Single-Agent Applications, Developing Workflow Applications, and Developing Multi-Agent Applications. |

### 8.2.2 Connecting Model Providers

Model providers' model services enable enterprises and individuals to quickly obtain and use high-quality models.

Before connecting external model service APIs in OpenJiuwen, you must first connect the model provider for unified management and identification of model sources. After completing the provider connection, you can continue to connect specific model services under that provider.

#### Prerequisites

The logged-in user is a space owner, space administrator, development engineer, or operations engineer. For details, please refer to Managing Team Space Members.

#### Creating a Model Provider

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Development Configuration".

Step 3 Select the "Custom Models" tab and click "New Model Provider".

Step 4 On the "New Model Provider" page, configure parameter information, as shown in Figure 8-3. For specific parameter descriptions, please refer to Table 8-3.

**Table 8-3 New Model Provider Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Provider Icon | System default provider icon, users can also customize the icon. System default icon: 1. Move the mouse over the system default icon and left-click. 2. In the dashed box, left-click to upload a prepared provider icon. Supports jpg, png format images, no larger than 100KB. | |
| Provider Name | The provider's name. Composed of 2~64 characters, including Chinese, English, numbers, underscores, hyphens, spaces, vertical bars. | DeepSeek |
| Provider English Name | The provider's English name. Composed of 2~64 characters, including English, numbers, underscores, hyphens, spaces, vertical bars. | DeepSeek |
| Description | Optional. The provider's description information. Composed of 0~1000 characters. | DeepSeek is a new organization of quantitative giant Huafang exploring AGI (General Artificial Intelligence), established in 2023, focused on researching world-leading general artificial intelligence underlying models and technologies, challenging cutting-edge artificial intelligence problems. |
| Select Authentication Method | Select the authentication method for calling the model service in agents, workflows, or via API. Supports the following authentication methods, for details please refer to Table 8-4: No Authentication, Api-key, AK/SK, App-code, Custom ApiKey, IAM Authentication | Api-key |

**Table 8-4 Authentication Method Description**

| Authentication Method | Parameter Description |
|----------|----------|
| Api-key | Authenticates via the Authentication field in the request Header carrying Bearer <Api-key>. Api-key: Enter the API Key of the provider's model service to be connected. After entering, key information will be encrypted and saved, taking effect about 2 minutes after setting. |
| AK/SK | Suitable for Pangu large models, calls requests via AK/SK encryption. AK (Access Key ID): Enter the AK of the provider's model service to be connected. After entering, key information will be encrypted and saved. SK (Secret Access Key): Enter the SK of the provider's model service to be connected. After entering, key information will be encrypted and saved. |
| App-code | Authenticates via the "X-Apig-Appcode" field in the request Header carrying App-code. App-code: Enter the App code of the provider's model service to be connected. After entering, key information will be encrypted and saved, taking effect about 2 minutes after setting. |
| Custom ApiKey | Authenticates via custom request header parameters. 1. To the right of "Header Configuration", click "+" to add Header parameters. 2. Fill in Header parameter information: parameter name, parameter value. |

Step 5 Click "OK" to complete the model provider connection.

The newly created model provider will be displayed in the "Custom" model provider card list, with a default status of "Authentication Configured". Model services under model providers with "Authentication Configured" status support testing and use.

Step 6 After completing the model provider connection, please refer to Connecting Model Services to connect specific model APIs, and perform testing and publishing.

----End

#### Related Operations

In the model provider card list, other supported operations are shown in Table 8-5.

**Table 8-5 Model Provider Information Related Operations**

| Operation | Description |
|------|------|
| Remove Authentication Configuration | Warning: After removing authentication configuration, models do not support testing or use. When adding a new model provider, "Authentication Method" selects "Api-key", "AK/SK", "App-code", "Custom ApiKey", or "IAM Authentication" to support removing authentication configuration. Move the mouse over the model provider card whose authentication configuration needs to be removed, click "Authentication Configuration", and click "Remove". After removing authentication configuration, the model service is "Not Configured Authentication". Models without authentication configuration do not support testing or use. |
| Modify Model Provider Information | Move the mouse over the model provider card to be modified and click "Edit". |
| Delete Model Provider | Note: If there are published model services in the model provider, the model services must be deleted first. Move the mouse over the model provider card to be deleted and click "Delete". |

### 8.2.3 Connecting Model Services

This section introduces how to connect model service APIs under an already connected model provider.

To meet users' personalized and professional needs for models, OpenJiuwen supports connecting model service APIs deployed by users or third parties in external environments. After model services are connected, you can test and publish them in OpenJiuwen, and select them for use in agents.

#### Supported Model Types

Currently supported model types for connection are as follows:

- Text Conversation (Chat)
- Text Vectorization (Embeddings)
- Text Ranking (Rerank)
- Image Understanding

#### Interface Protocol Requirements

To ensure the quality of connected model services, please verify that the model API conforms to the corresponding interface protocol specification before connection. Different model types support the following interface protocols:
- Text Conversation, Text Vectorization, Image Understanding: Standard OpenAI Protocol, Alibaba Qwen Interface Protocol, MaaS Standard API V1, MaaS Standard API V2
- Text Ranking: AI Engine Standard Protocol

#### Prerequisites

- A model provider has been connected.
- The logged-in user is a space owner, space administrator, development engineer, or operations engineer. For details, please refer to Managing Team Space Members.
- Necessary information for the model service to be connected has been obtained, such as API address, authentication information (API Key, etc.), model name (model ID/model code), and protocol type.

#### Creating a Model Service

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Development Configuration".

Step 3 Select the "Custom Models" tab, click the corresponding model provider card, and on the "Provider Details" page, click "New Model Service".

Step 4 On the "New Model Service" page, configure parameter information. For specific parameter descriptions, please refer to Table 8-6.

**Table 8-6 New Model Service Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Model Service Icon | System default model service icon, users can also customize the icon. System default icon: 1. Move the mouse over the system default icon and left-click. 2. In the dashed box, left-click to upload a prepared model service icon. Supports jpg, png format images, no larger than 100KB. | |
| Model Service Name | Custom model service name. Composed of 2~64 characters, including Chinese, English, numbers and :._/|\-, starting and ending with Chinese, English, or numbers. | Text Conversation |
| Model Name | The filled-in model name must be the model's model ID/model code, otherwise the model will be unavailable. Need to log in to the third-party model vendor's official website to view, for example, Baichuan4, deepseek-chat, glm-4-air. If connecting a self-built model service, this model name will be used for the model field in the interface call request body. Composed of 2~64 characters, including Chinese, English, numbers and :._/|\-, starting and ending with Chinese, English, or numbers. | deepseek-chat |
| Model Type | Select the model type. Text Conversation: Text conversation models, commonly known as conversational AI or chatbots, are AI systems trained to understand and generate human language and communicate in multi-turn, contextually coherent ways. Text Vectorization: The core task of text vectorization models is to convert text (words, sentences, paragraphs, or documents) into numerical forms that computers can understand and process鈥攊.e., high-dimensional vectors (also called "embeddings"). Text Ranking: Text ranking models are used to sort a set of text objects by relevance. Image Understanding: Image understanding models are AI models that can analyze, interpret, and understand image content. | Text Conversation |
| Model Service API Address | Fill in the API address information of the model to be connected. Character length no larger than 255 characters. | https://api.deepseek.com/chat/completions |
| API Interface Protocol | When "Model Type" is "Text Conversation", "Text Vectorization", or "Image Understanding", select "Standard OpenAI Protocol", "Alibaba Qwen Interface Protocol", "MaaS Standard API V1", or "MaaS Standard API V2". When "Model Type" is "Text Ranking", select "AI Engine Standard Protocol". | Standard OpenAI Protocol |
| Flow Control Configuration | Exceeding the flow control value triggers rate limiting, and user requests will fail due to flow control. Unlimited, 10 times/second, 50 times/second, 100 times/second, 200 times/second | |
| Select Tags | Optional. When "Model Type" is "Text Conversation" or "Image Understanding", this parameter is available. After selecting tags, when selecting LLMs in applications, they are displayed on the right side of the LLM. Tool: The LLM supports the application calling external tools. Thinking: The LLM has thinking reasoning capability. Web Search: The LLM has web search capability. | Tool |
| Whether to Support Disabling Chain of Thought Output | When "Select Tags" includes "Thinking", this parameter is available. Enable: The model shows the "Deep Thinking" parameter during testing and use. Disable: The model does not show the "Deep Thinking" parameter during testing and use. Disabled by default. | |
| Custom Tags | Optional. Supports up to 5 tags. | |
| Model Service Description | Optional. Model service description information. Composed of 0~1000 characters. | |

Step 5 Click "OK".

The newly created model service is displayed in the model service card list under the model provider, with a default status of "Not Published".

Step 6 On the model service card to be tested, click " > Test". For specific testing operations, please refer to Testing Models.

Step 7 On the model service card to be published, click " > Publish".

The model service card displays as "Published" and supports use in agents.

Step 8 (Optional) When multiple model services of the same type have been connected and published, model routing strategies can be configured for automatic model failover, improving availability. For specific operations, please refer to Configuring Model Routing Strategies.

----End

#### Related Operations

In the connected model service card list, other supported operations are shown in Table 8-7.

**Table 8-7 Connected Model Service Related Operations**

| Operation | Description |
|------|------|
| View Model Service Information | Click the model service card to enter the model service details page, where you can view model service information. |
| Modify Model Service Information | Note: Only unpublished model services can be modified. On the model service card to be modified, click " > Edit". |
| Cancel Publish | Note: Only published model services can be canceled from publishing. Unpublished model services do not support use. On the model service card to be unpublished, click " > Cancel Publish". |
| Delete Model Service | Note: Published model services must be unpublished before they can be deleted. On the model service card to be deleted, click " > Delete". |

#### Related Documentation

- After model services are connected, model services can be tested. For specific operations, please refer to Testing Models.
- When multiple model services of the same type have been connected and published, model routing strategies can be configured for automatic model failover, improving availability. For specific operations, please refer to Configuring Model Routing Strategies.
- After model services are connected, they can be used in agents and workflows. Please refer to Developing Single-Agent Applications, Developing Workflow Applications, and Developing Multi-Agent Applications.

### 8.2.4 Model API Interface Specification

This section introduces the interface specifications for the Standard OpenAI Protocol and AI Engine Standard Protocol. Before connecting custom model services, please ensure the model API conforms to the corresponding interface protocol specification.

The current model gateway supports connecting the following four types of model APIs:

- Text Conversation (Chat)
- Text Vectorization (Embeddings)
- Text Ranking (Rerank)
- Image Understanding

The interface protocols supported by each model type are shown in the table below.

**Table 8-8 Model Type and Interface Protocol Mapping**

| Model Type | Supported Interface Protocols |
|----------|----------------|
| Text Conversation | Standard OpenAI Protocol, Alibaba Qwen Interface Protocol, MaaS Standard API V1, MaaS Standard API V2 |
| Text Vectorization | Standard OpenAI Protocol, Alibaba Qwen Interface Protocol, MaaS Standard API V1, MaaS Standard API V2 |
| Text Ranking | AI Engine Standard Protocol |
| Image Understanding | AI Engine Standard Protocol |

#### Applicable Scenarios

This section applies to the following scenarios:

- Need to connect third-party model services (such as DeepSeek, Moonshot, etc.) to OpenJiuwen, to confirm whether the model API meets the platform's interface protocol specification.
- Self-deployed model inference services need to implement/adapt API interfaces according to platform-supported protocols before connecting to OpenJiuwen.
- Anomalies occur during model connection or calling (e.g., request failure, missing response fields, format incompatibility, etc.), needing to check request and response format issues against the interface specification.

#### Text Conversation (Chat) API Specification

**Interface Format**

Type: POST

Protocol: HTTP/HTTPS

**Request Body Parameters**

**Table 8-9 Request Body Parameters**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| messages | Yes | Array of objects | Table 8-10 text conversation message body class |
| model | Yes | String | Model name used for text conversation |
| frequency_penalty | No | Number | Frequency penalty, value range -2.0~2.0 |
| logit_bias | No | Map<String,Integer> | Token mapping to association bias values from -100 to 100 |
| max_tokens | No | Integer | Maximum number of tokens allowed in the response body |
| n | No | Integer | Number of choices included in the response body, value range 1-128, default 1 |
| presence_penalty | No | Number | Presence penalty, value range -2.0~2.0 |
| stream | No | Boolean | When set to true, returns streaming; when set to false, returns non-streaming. Default: false |
| temperature | No | Number | Controls randomness, value range 0-2, default 1 |
| top_p | No | Number | Affects output diversity, value range 0.0-1.0, default 1 |
| tools | No | Array of objects | Table 8-11 tools available for the model to call |
| tool_choice | No | String | Controls how the model selects to call functions, default is auto |

**Table 8-10 ChatCompletionRequestMessage**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| role | Yes | String | The role corresponding to the message body. system/user |
| content | Yes | String | Specific content of the message |
| name | No | String | Optional name of the conversation participant |

**Table 8-11 FunctionCallTool**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| type | No | String | Tool call type, currently only supports function |
| function | No | object | Only supplemented when the tool type is function |

**Table 8-12 function**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| name | No | String | Function name, max length 64 characters |
| description | No | String | Used to describe the function's functionality |
| parameters | No | Object | Json Schema object, used to define the parameters accepted by the function |

**Response Body Parameters**

**Table 8-13 Response Body Parameters**

| Parameter | Parameter Type | Description |
|------|----------|------|
| id | String | Text conversation unique identifier |
| choices | Array of objects | Table 8-14 response body list |
| created | Integer | Time when the Q&A occurred, format is timestamp |
| model | String | Model name used for text conversation |
| object | String | Fixed value "chat.completion" |
| usage | object | Table 8-18 text conversation usage statistics |

**Table 8-14 choices**

| Parameter | Parameter Type | Description |
|------|----------|------|
| index | Integer | When multiple choices are returned, the order corresponding to each choice |
| message | object | Specific message body content returned by the model service |
| finish_reason | String | Reason for returning end: stop/length/content_filter/tool_calls |

**Table 8-15 ChatCompletionResponseMessage**

| Parameter | Parameter Type | Description |
|------|----------|------|
| content | String | Content of the returned message body, either this or tool_calls |
| role | String | Role of the returned message body: user/assistant |
| tool_calls | Array of objects | Table 8-16 tool call messages, either this or content |

**Table 8-16 ToolCall**

| Parameter | Parameter Type | Description |
|------|----------|------|
| id | String | Tool call unique identifier |
| type | String | Tool type, currently only supports function |
| function | Object | Detailed information of the called function |

**Table 8-17 CallFunction**

| Parameter | Parameter Type | Description |
|------|----------|------|
| name | String | Function name |
| arguments | String | Parameters for calling the function, JSON format |

**Table 8-18 CompletionUsage**

| Parameter | Parameter Type | Description |
|------|----------|------|
| completion_tokens | Integer | Number of tokens in the answer |
| prompt_tokens | Integer | Number of tokens in the question |
| total_tokens | Integer | Total tokens (question + answer) |

#### Text Vectorization (Embeddings) API Specification

**Interface Format**

Type: POST

Protocol: HTTP/HTTPS

**Request Body Parameters**

**Table 8-19 Request Body Parameters**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| input | Yes | Array of strings | Plain text (string) or text list (array), array length: 1-2048 |
| model | Yes | String | Vectorization model name |

**Response Body Parameters**

**Table 8-20 Response Body Parameters**

| Parameter | Parameter Type | Description |
|------|----------|------|
| data | Array of objects | Table 8-21 vectorization results |
| model | String | Vectorization model name |
| object | String | Fixed value "list" |
| usage | object | Usage statistics per request |

**Table 8-21 Embedding**

| Parameter | Parameter Type | Description |
|------|----------|------|
| index | Integer | The order of the vector in the vector list |
| embedding | Array of numbers | Vector array, Float type |
| object | String | Fixed value "embedding" |

**Table 8-22 usage**

| Parameter | Parameter Type | Description |
|------|----------|------|
| prompt_tokens | Integer | Number of tokens in the question |
| total_tokens | Integer | Number of tokens in the question |

#### Text Ranking (Rerank) API Specification

**Interface Format**

Type: POST

Protocol: HTTP/HTTPS

**Request Body Parameters**

**Table 8-23 Request Body Parameters**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| query | Yes | String | Original request question, based on which candidate texts are ranked |
| top_n | Yes | Integer | Returns the top n ranked results |
| docs | Yes | Array of strings | Candidate texts, file size limit within 512MB |
| model | Yes | String | Ranking model name |

**Response Body Parameters**

**Table 8-24 Response Body Parameters**

| Parameter | Parameter Type | Description |
|------|----------|------|
| model | String | Ranking model name |
| usage | object | Usage statistics per request |
| results | Array of objects | Table 8-26 ranking results |

**Table 8-25 usage**

| Parameter | Parameter Type | Description |
|------|----------|------|
| prompt_tokens | Integer | Number of tokens in the question |
| total_tokens | Integer | Number of tokens in the question |

**Table 8-26 RankDocument**

| Parameter | Parameter Type | Description |
|------|----------|------|
| index | Integer | The corresponding sequence number after text ranking |
| document | object | Text |
| relevance_score | Number | The ranking score of the text |

**Table 8-27 Document**

| Parameter | Parameter Type | Description |
|------|----------|------|
| text | String | Text content |

#### Image Understanding API Specification

**Interface Format**

Type: POST

Protocol: HTTP/HTTPS

**Request Body Parameters**

**Table 8-28 Request Body Parameters**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| messages | Yes | Array of objects | Table 8-29 image understanding conversation message body class |
| model | Yes | String | Model name used for image understanding conversation |
| frequency_penalty | No | Number | Frequency penalty, value range -2.0~2.0 |
| logprobs | No | boolean | Whether to return the log probabilities of output Tokens |
| top_logprobs | No | Integer | Specifies the maximum number of candidate Tokens with highest probability to return, value range: [0,5] |
| max_tokens | No | Integer | Maximum number of tokens allowed in the response body |
| presence_penalty | No | Number | Presence penalty, value range -2.0~2.0 |
| n | No | Integer | Number of generated responses, value range 1-4, default value 1 |
| stream | No | Boolean | When set to true, returns streaming; when set to false, returns non-streaming. Default: false |
| seed | No | Integer | Setting the seed parameter makes the text generation process more deterministic |
| temperature | No | Number | Controls randomness, value range 0-2, default 1 |
| top_p | No | Number | Affects output diversity, value range 0.0-1.0, default 1 |

**Table 8-29 ChatCompletionRequestMessage**

| Parameter | Required | Parameter Type | Description |
|------|----------|----------|------|
| role | Yes | String | The role corresponding to the message body: system/user |
| content | Yes | String | Specific content of the message |
| name | No | String | Optional name of the conversation participant |

**Response Body Parameters**

**Table 8-30 Response Body Parameters**

| Parameter | Parameter Type | Description |
|------|----------|------|
| id | String | Image understanding text conversation unique identifier |
| choices | Array of objects | Table 8-31 response body list |
| created | long | Time when the Q&A occurred, format is timestamp |
| model | String | Model name used for image understanding text conversation |
| object | String | Fixed value "chat.completion" |
| usage | object | Table 8-35 image understanding text conversation usage statistics |

**Table 8-31 ChatNonStreamingChoice**

| Parameter | Parameter Type | Description |
|------|----------|------|
| index | Integer | When multiple choices are returned, the order corresponding to each choice |
| message | object | Specific message body content returned by the model service |
| finish_reason | String | Reason for returning end: stop/length/content_filter/tool_calls |

**Table 8-32 ChatMessageResponse**

| Parameter | Parameter Type | Description |
|------|----------|------|
| content | String | Content of the returned message body, either this or tool_calls |
| role | String | Role of the returned message body: user/assistant |
| tool_calls | Array of objects | Table 8-33 tool call messages, either this or content |
| audio | ChatMessageAudio | Audio part in the chat message |
| reasoning_content | String | Used to display the model's reasoning process |

**Table 8-33 ToolCall**

| Parameter | Parameter Type | Description |
|------|----------|------|
| id | String | Tool call unique identifier |
| type | String | Tool type, currently only supports function |
| function | Object | Detailed information of the called function |

**Table 8-34 CallFunction**

| Parameter | Parameter Type | Description |
|------|----------|------|
| name | String | Function name |
| arguments | String | Parameters for calling the function, JSON format |

**Table 8-35 CompletionUsage**

| Parameter | Parameter Type | Description |
|------|----------|------|
| completion_tokens | Integer | Number of tokens in the answer |
| prompt_tokens | Integer | Number of tokens in the question |
| total_tokens | Integer | Total tokens (question + answer) |


## 8.3 Testing Models

Model testing refers to the process of making real calls to model services on the platform side, combined with parameter adjustments and effect observation, to verify the model's usability, stability, and performance in specific scenarios. Through testing, you can discover and locate common issues (such as authentication failures, interface protocol mismatches, response timeouts, output not meeting expectations, etc.) before the model is officially published or integrated into business processes, ensuring stable and efficient operation in real business scenarios.

This chapter introduces the testing process for connected model services on the platform. Currently supported model types for testing include: Text Conversation, Image Understanding, Text Vectorization (vector model), and Text Ranking.

Model testing is typically used for the following scenarios:

- Post-connection verification: Newly connected model services need to be tested to confirm they can be called before publishing and use.
- Post-change regression verification: When you update API Keys, change API addresses, adjust model names (model ID/code), or switch interface protocols, re-testing is recommended.
- Effect and parameter optimization: For the same type of question, compare output effects by adjusting parameters to choose more suitable configurations.
- Problem troubleshooting: When agents/workflows encounter anomalies when calling models, you can reproduce issues through testing and view call results and error messages to quickly narrow down the troubleshooting scope.

#### Prerequisites

- A model service or routing strategy is available for testing:
    - Testing custom model services: Custom model service connection has been completed (including model provider connection and successful model service connection).
    - Testing model routing strategies: An available routing strategy is available. For details, please see Configuring Model Routing Strategies.
- The logged-in user is a space owner, space administrator, development engineer, or operations engineer. For details, please refer to Managing Team Space Members.

#### Testing Model Services

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Development Configuration", and enter the "Model Testing" tab.

To directly test a single model, you can operate through the following entries:
- Test preset models (Asset Marketplace entry): In the left navigation, select "Asset Marketplace", enter the "Models" page, move the mouse over the model card to be tested, and click "Model Testing".
- Test custom-connected models (Custom Models entry): In the left navigation, select "Development Center > Development Configuration". Enter the "Custom Models" tab, enter the "Provider Details" page for the model to be tested, and on the model service card to be tested, click " > Test".

Step 3 Optional: On the "Model Testing" page, you can test the following types of model services.

##### Text Conversation

1. In the "Model Type" area, select "Text Conversation". For parameter configuration, please refer to Table 8-36.

**Table 8-36 Text Conversation Type Model Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Model Service | "Model Service A" defaults to the selected provider's model service. "Model Service B" is optional. You can select or switch the following types of model services through the dropdown: user self-connected model services, platform recommended, routing strategies | DeepSeek-V3 |
| Deep Thinking | This parameter is only displayed in the following scenarios: when the platform recommended selected model is a thinking model and supports disabling deep thinking; when the user self-connected model service selected model is a thinking model and "Whether to Support Disabling Chain of Thought Output" was enabled when creating the new model service. Enable: The LLM will first perform deep thinking and reasoning. Disable: The LLM will skip the chain of thought reasoning process and directly generate the final answer. | |
| Output Method | Streaming (default): Fast return mode word by word, without waiting for the LLM to complete generation. Non-streaming: The LLM returns all at once after fully generating the answer. | Streaming |
| Max Output Tokens | The maximum number of tokens the model can output during a single inference or content generation. Value range 100~32768, default value 2048. | 2048 |
| Temperature | Higher values make the output more random, while lower values make it more focused and deterministic. Value range 0.01~2, default value 0.5. It is recommended to set only 1 of this parameter and "Diversity". | 0.5 |
| Diversity | Affects the diversity of output text; the larger the value, the stronger the diversity of generated text. Value range 0~1, default value 0.5. It is recommended to set only 1 of this parameter and "Temperature". | 0.5 |
| Presence Penalty | Positive values tend to avoid using already-appeared words, more inclined to generate new words. Value range -2.0~2.0, default value 0. | 0 |
| Frequency Penalty | Positive values tend to avoid using common words and phrases, more inclined to generate less common words. Value range -2.0~2.0, default value 0. | 0 |

2. In the "Effect Preview" area on the right, enter a test statement in the conversation input box and press Enter or click to view the model response results.

Click to clear the current session content and start a new session.

##### Image Understanding

1. In the "Model Type" area, select "Image Understanding". For parameter configuration, please refer to Table 8-37.

**Table 8-37 Image Understanding Type Model Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Model Service | Defaults to the selected provider's model service. You can also switch to the following model services in the dropdown: user self-connected model services, platform recommended | Qwen2.5-VL-72B |
| Output Method | Streaming (default): Fast return mode word by word, without waiting for the LLM to complete generation. Non-streaming: The LLM returns all at once after fully generating the answer. | Non-streaming |
| Upload Image | Click to upload local images. Supports uploading JPG, PNG format images, no larger than 4MB. | |
| Prompt Content | Enter a prompt to ask questions about the image. | What's in the image? |

2. Click "Generate Image Understanding", and view the model response effect in the "Effect Preview" area on the right.

##### Text Vectorization

1. In the "Model Type" area, select "Text Vectorization". For parameter configuration, please refer to Table 8-38.

**Table 8-38 Text Vectorization Type Model Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Model Service | Defaults to the selected provider's model service. You can also switch to the following model services in the dropdown: user self-connected model services, platform recommended | BGE-M3 |
| Enter Text | Enter the text to be vectorized. Refer to the following examples: Example 1: That was a happy person. Example 2: ["That was a happy person", "That was a glad person", "That was a melancholy person"] | That was a happy person |

2. Click "Generate Vectorization", and view the model response effect in the "Effect Preview" area on the right.

##### Text Ranking

1. In the "Model Type" area, select "Text Ranking". For parameter configuration, please refer to Table 8-39.

**Table 8-39 Text Ranking Type Model Parameter Description**

| Parameter Name | Parameter Description | Example |
|----------|----------|------|
| Model Service | Defaults to the selected model service. You can also switch to the following model services in the dropdown: user self-connected model services, platform recommended | BGE-Reranker-V2-M3 |
| Texts to be Ranked | Enter texts to be ranked. Click Add Text, up to 10 texts can be added. | The child is happy at school |
| Number of Displayed Texts | The number of texts displayed after ranking is complete. Value range 3~10, default value 1. | 1 |
| My Question | Describe the problem to be solved. | How is the child doing at school? |

2. Click "Start Ranking", and view the model response effect in the "Effect Preview" area on the right.

Step 4 After successful testing, model services can be used in agents and workflows. Please refer to Developing Single-Agent Applications, Developing Workflow Applications, and Developing Multi-Agent Applications.

----End

## 8.4 Configuring Model Routing Strategies

By configuring model routing strategies, you can orchestrate multiple connected model services according to rules, enabling automatic model failover capability. When the primary model cannot respond normally due to failure, timeout, or unavailability, the system will automatically switch to other available models based on the routing strategy to continue providing services, thereby improving business stability and availability.

After the routing strategy is created, you can test the routing entry for verification and select it for use in agents.

#### Applicable Scenarios

- Multiple model services of the same type have been connected (e.g., multiple text conversation models), and you want to automatically switch when the primary model is unavailable, improving service continuity.
- The business has high stability requirements and wants to reduce the impact of single model service anomalies.
- You want to achieve model switching or scaling by adjusting routing strategies without modifying agent configurations.

#### Prerequisites

- Model services have been connected.
- The logged-in user is a space owner, space administrator, development engineer, or operations engineer. For details, please refer to Managing Team Space Members.
- Model services referenced in the routing should have been tested to ensure the model services themselves can be called normally. The routing strategy solves the "high availability of the calling entry" problem, and model testing is used to verify "whether the model service/routing entry is available". It is recommended to first test the availability of each model service, then configure the routing strategy and test the routing entry, so as to quickly locate issues.

#### Creating a Routing Strategy

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Development Configuration".

Step 3 Select the "Routing Strategies" tab and click "Create Routing Strategy".

Step 4 On the "Create Routing Strategy" page, configure parameter information. For specific parameter descriptions, please refer to Table 8-40. After configuration, click "Save".

The newly created routing strategy is displayed in the routing strategy list.

**Table 8-40 Routing Strategy Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Strategy Name | Custom routing strategy name. Composed of 2~36 characters, including Chinese, English, numbers, hyphens (-), underscores (_), dots (.), only supports starting with Chinese or English. | Text Conversation Routing Strategy |
| AI Model | Select the model service in the "Model A" dropdown. Only text conversation type model services are supported. Click "+ AI Model" to add model services. A total of 3 model services can be added. When the routing strategy provides model services, the model calling order is: Model A > Model B > Model C. When Model A cannot work normally, it can automatically switch to Model B and Model C in sequence. | Model A: DeepSeek-R1; Model B: DeepSeek-V3; Model C: Qwen3-32B |
| Strategy Total Timeout | The overall timeout for the model routing strategy. Value range 1000~1,000,000ms, default value 10,000ms. | 10000ms |
| Model Retry Count | The retry count for a single model service in the routing strategy. Value range 0-100, default value 0. | 0 |
| Strategy Description | Routing strategy description information. Composed of 1~100 characters. | This strategy is a text conversation type routing strategy. |

Step 5 In the "Model Testing" area, test the model. For specific parameter descriptions, please refer to Table 8-41.

**Table 8-41 Model Testing Parameter Description**

| Parameter Name | Parameter Description | Example |
|----------|----------|------|
| Output Method | Optional non-streaming, streaming. Streaming: Fast return mode word by word, without waiting for the LLM to complete generation. Non-streaming: The LLM returns all at once after fully generating the answer. Default streaming. | Streaming |
| Max Output Tokens | The maximum number of tokens the model can output during a single inference or content generation. Value range 100~32768, default value 2048. | 2048 |
| Temperature | Higher values make the output more random, while lower values make it more focused and deterministic. Value range 0.01~2, default value 0.5. It is recommended to set only 1 of this parameter and "Diversity". | 0.5 |
| Diversity | Affects the diversity of output text; the larger the value, the stronger the diversity of generated text. Value range 0~1, default value 0.5. It is recommended to set only 1 of this parameter and "Temperature". | 0.5 |
| Presence Penalty | Positive values tend to avoid using already-appeared words, more inclined to generate new words. Value range -2.0~2.0, default value 0. | 0 |
| Frequency Penalty | Positive values tend to avoid using common words and phrases, more inclined to generate less common words. Value range -2.0~2.0, default value 0. | 0 |

Step 6 In the "Preview Debug" area on the right, enter a test statement in the conversation input box and press Enter or click to view the model response results.

Click to clear the current session content and start a new session.

----End

#### Related Operations

In the "Routing Strategies" list, other supported operations are shown in Table 8-42.

**Table 8-42 Related Operations**

| Operation | Description |
|------|------|
| View Routing Strategy Details | Under the "Strategy Name" column corresponding to the routing strategy to be viewed, click the routing strategy name. |
| Modify Routing Strategy | Under the "Operation" column corresponding to the routing strategy to be modified, click "Edit". |
| Delete Routing Strategy | Under the "Operation" column corresponding to the routing strategy to be deleted, click "Delete". |

#### Related Documentation

After the routing strategy is created, users can use the routing strategy in agents and workflows. Please refer to Developing Single-Agent Applications, Developing Workflow Applications, and Developing Multi-Agent Applications.

## 8.5 Managing My Credentials

Users need authentication when calling single-agent applications, workflow applications, and multi-agent applications via API. They can use "Platform API Key" for platform authentication.

API Key is each user's individual identity authentication and the basis for individuals to use API to call single-agent applications, workflow applications, and multi-agent applications. It must be kept safe.

#### Constraints and Limitations

Each user can add up to 30 platform API Keys.

#### Prerequisites

The logged-in user is a space owner, space administrator, development engineer, or operations engineer. For details, please refer to Managing Team Space Members.

#### Creating a Platform API Key

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation, select "Development Center > Development Configuration > My Credentials".

Step 3 On the "My Credentials" page, click "New Platform API Key".

Step 4 On the "New Platform API Key" page, configure parameter information. For specific parameter descriptions, please refer to Table 8-43.

**Table 8-43 New Platform API Key**

| Parameter | Description | Example |
|------|------|------|
| Name | Platform API Key name. Composed of 2~36 characters, supports Chinese, English, numbers, -_., starting with Chinese or English. | test |
| Description | Platform API Key description information. Composed of 0~1000 characters. | - |

Step 5 Click "OK".

After creation, it is displayed in the "My Credentials" list.

Step 6 In the popup "Your API Key" page, click to copy the API Key and save it, then click "I have saved, confirm to close".

The platform API Key is displayed once after creation. Please copy and save it in a timely manner. If the platform API Key is lost, please create a new platform API Key.

----End

#### Related Operations

In the "My Credentials" list, other supported operations are shown in Table 8-44.

**Table 8-44 Related Operations**

| Operation | Description |
|------|------|
| Delete Platform API Key | Under the "Operation" column corresponding to the platform API Key to be deleted, click "Delete". |

#### Related Documentation

After the platform API Key is created, users can use this API Key for authentication when using API to call single-agent applications, workflow applications, and multi-agent applications. Please refer to "Agent Development Platform 26.2.1 API Reference" in the "Calling Workflow Applications" chapter and "Agent Development Platform 26.2.1 API Reference" in the "Calling Agent Applications" chapter.


# 9 Workspaces and Permissions

## 9.1 Workspace and Permissions Introduction

To facilitate multi-person collaboration and resource sharing, OpenJiuwen introduces the concept of workspaces. Workspaces provide users with flexible resource management and team collaboration capabilities.

Workspaces are divided into Personal Space and Team Space.

Personal Space: Each OpenJiuwen user has a personal space by default. The default personal space cannot be deleted, edited, or shared, and is only for managing personal development and resource management.

Team Space: Team spaces are designed to provide users with flexible and efficient asset management and collaboration methods. OpenJiuwen supports users to customize and create independent team spaces according to business needs or team structure. Through this approach, users can better organize and manage resources, improving team collaboration efficiency.

Team spaces are completely isolated at the asset level, ensuring asset security and operational independence, effectively avoiding risks brought by cross-interference or permission misconfiguration. Users can combine actual use scenarios, such as different project management, department operations, or specific R&D needs, to divide multiple team spaces, achieving fine-grained asset management and orderly allocation, helping users efficiently plan and allocate tasks, making team collaboration more efficient.

In addition, OpenJiuwen is equipped with a comprehensive space role permission system. Through flexible permission settings, each user can safely and efficiently operate OpenJiuwen functions within their corresponding permission scope, thereby maximizing data security and work efficiency.

### Team Space Personnel Roles and Permissions

OpenJiuwen team space personnel roles are as follows. Each role has different operation permissions for team spaces. For specific operation permissions, please refer to Table 12-1.

For how to manage team space members, please refer to Managing Team Space Members.

Note

"鈭? indicates supported, "脳" indicates not yet supported.

**Table 9-1 Team Space Personnel Roles and Permissions**

| Module | Permission | Space Owner | Space Administrator | Development Engineer | Operations Engineer |
|------|------|------------|------------|------------|------------|
| Space Management | Add Space | 鈭?| 鈭?| 鈭?| 鈭?|
| | Modify Space Name, Description | 鈭?| 鈭?| 脳 | 脳 |
| | View Space | 鈭?| 鈭?| 鈭?| 鈭?|
| | Add Members | 鈭?| 鈭?| 脳 | 脳 |
| | Modify Roles | 鈭?| 鈭?| 脳 | 脳 |
| | | Cannot change own role | Cannot change space owner's role | | |
| | Transfer Owner | 鈭?| 脳 | 脳 | 脳 |
| | Remove Members | 鈭?| 鈭?| 脳 | 脳 |
| | | Cannot remove space owner | | | |
| | Leave Space | 脳 | 鈭?| 鈭?| 鈭?|
| | Delete Space | 鈭?| 脳 | 脳 | 脳 |
| Development Center | Create | 鈭?| 鈭?| 鈭?| 脳 |
| | View & Debug & Trial Run | 鈭?| 鈭?| 鈭?| 脳 |
| | Copy | 鈭?| 鈭?| 鈭?| 脳 |
| | Modify | 鈭?| 鈭?| 鈭?| 脳 |
| | Publish | 鈭?| 鈭?| 鈭?| 脳 |
| | Import & Export | 鈭?| 鈭?| 鈭?| 脳 |
| | Delete | 鈭?| 鈭?| 鈭?| 脳 |
| Operations & Maintenance | Observe All Operations | 鈭?| 鈭?| 脳 | 鈭?|
| | Evaluate All Operations | 鈭?| 鈭?| 鈭?| 鈭?|
| Model Center | Model Service All Operations | 鈭?| 鈭?| 鈭?| 鈭?|
| | Routing Strategy All Operations | 鈭?| 鈭?| 鈭?| 鈭?|
| | Model Testing All Operations | 鈭?| 鈭?| 鈭?| 鈭?|
| Asset Center | Asset View | 鈭?| 鈭?| 鈭?| 鈭?|
| | Template - Online Debug | 鈭?| 鈭?| 鈭?| 鈭?|
| | Template Copy | 鈭?| 鈭?| 鈭?| 脳 |
| | Template Share | 鈭?| 鈭?| 鈭?| 脳 |
| | MCP - Install | 鈭?| 鈭?| 鈭?| 脳 |
| | Plugin - Authentication Configuration, etc. | 鈭?| 鈭?| 鈭?| 脳 |
| | Plugin Share | 鈭?| 鈭?| 鈭?| 脳 |
| Overview | Overview Page View | 鈭?| 鈭?| 鈭?| 鈭?|
| | Create, Component Management, Copy Template | 鈭?| 鈭?| 鈭?| 脳 |

Users with OBS file upload permissions can customize all user role permissions.

Note

- This operation is high-risk, please proceed with caution.
- If you need to customize role permissions, you need to enable the custom role permission configuration item during installation. For specific operations, please refer to "Agent Development Platform 26.2.1 Installation Guide" in "Installation Process > K8s-based Installation > Installing Agent-manager".
1. Modify the role permission example locally according to role permissions, and save as JSON format.
2. Upload the file prepared in step 1 to OBS.
- role_permissions.json is the path set in "Agent Development Platform 26.2.1 Installation Guide" in "Installation Process > K8s-based Installation > Installing Agent-manager".
- Load the permission file according to the refresh time set in "Agent Development Platform 26.2.1 Installation Guide" in "Installation Process > K8s-based Installation > Installing Agent-manager". It will take effect after loading.

## 9.2 Creating and Managing Team Spaces

In the development process, a development task often requires the collaboration of multiple team members to complete. At this time, a team space can be created to provide team members with a centralized platform for task allocation, progress tracking, file sharing, and instant communication. Through this approach, team work efficiency can be significantly improved, ensuring the smooth progress and high-quality completion of development tasks.

### Creating a Team Space

Step 1 Log in to the OpenJiuwen Agent Development Platform.

Step 2 In the left navigation, select "Personal Space > Create Team Space", as shown in Figure 12-1.

If a team space has already been selected, the interface displays the actual team space name instead of "Personal Space".

Step 3 On the "Create Space" page, configure space information. For creating space parameter descriptions, please refer to Creating Team Space. Click "OK".

The created team space is displayed in the "Personal Space" dropdown list.

If team spaces already exist, the interface displays the actual team space name instead of "Personal Space".

**Table 9-2 Create Space Parameter Description**

| Parameter | Description | Example |
|------|------|------|
| Space Name | Team space name. Composed of 1~50 characters, including Chinese, numbers, letters, hyphens, underscores, parentheses, exclamation marks. | Development Department |
| Space Description | Optional. Team space description information. Composed of 0~1000 characters. | This space is for developing applications. |
| Space Image | System default team space avatar, users can also customize the image. 1. Move the mouse over the system default image and left-click. 2. In the dashed box, left-click to upload a prepared team space image. Supports jpg, jpeg, png, gif format images, no larger than 200KB. | System default image |

----End

### Managing Team Spaces

Step 1 Log in to the OpenJiuwen Agent Development Platform.

Step 2 In the left navigation, click "Personal Space" and select the created team space, as shown in Figure 12-3.

If a team space has already been selected, the interface displays the actual team space name instead of "Personal Space".

After selecting a team space, "System Management > Team Space Management" is displayed at the bottom of the left navigation bar.

Step 3 In the left navigation bar, select "System Management > Team Space Management" to enter the "Team Space Management" page.

Step 4 On the "Team Space Management" page, other operations supported for team spaces are shown in Table 12-3.

**Table 9-3 Managing Team Spaces**

| Operation | Description |
|------|------|
| Edit Team Space Basic Information | To the right of "Basic Information", click to edit the team space name, space description, and space image. After completion, click "OK". Space owners and space administrators support editing space basic information. |
| Delete Team Space | Warning: After deleting a space, the corresponding resources will also be deleted and cannot be recovered. Click "Delete Space", in the popup, enter "DELETE", and click "OK". Space administrators support deleting team spaces. |
| Transfer Team Space | Click "Transfer Space", on the "Transfer Space" page, select the member to transfer to, and click "OK". Space owners support transferring team spaces. After transfer, the owner becomes a space administrator. |
| Leave Team Space | Click "Leave Space" to exit from this space. After leaving the space, you cannot view this space's resources. Space administrators, development engineers, and operations engineers support leaving team spaces. |

----End

## 9.3 Managing Team Space Members

After users create team spaces, to make the team space operate more efficiently, members can be added to the team space.

### Prerequisites

- A team space has been created.
- The logged-in user is the space owner or space administrator of the team space. For details, please refer to Managing Team Space Members.

### Adding Users to Space

Step 1 Log in to the OpenJiuwen Agent Development Platform, and in the "Personal Space" area on the left navigation bar, select the target space.

Step 2 In the left navigation bar, select "System Management > Team Space Management" to enter the "Team Space Management" page.

Step 3 On the "Team Space Management" page, click "Add Members".

Step 4 On the "Add Members" page, search for user names, check the checkboxes to the left of users to be added, set member roles, and click "OK".

For member role introduction, please refer to Team Space Personnel Roles and Permissions. The user who created the team space is the space owner by default.

Added members are displayed in the member list.

----End

### Related Operations

In the "Member Management" area of "Team Space Management", other supported operations are shown in Table 12-4.

**Table 9-4 Member Management Related Operations**

| Operation | Description |
|------|------|
| Switch User Role | Under the "Role" column corresponding to the user whose role needs to be switched, click the member role to reselect the role. Space owners do not support role switching. |
| Delete Member | Single delete: Under the "Operation" column corresponding to the user to be deleted, click "Delete". Batch delete: Check the checkboxes to the left of users to be deleted, and click "Delete". Space owners do not support deletion. |


