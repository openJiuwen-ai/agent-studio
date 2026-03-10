#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
N8N Node Type Mappings

Contains all mapping constants for converting n8n node types to OpenJiuwen format:
- N8N_TO_OPENJIUWEN: Main node type → ComponentType mapping
- AI_SUBNODES: AI sub-nodes that get embedded into LLM nodes
- APP_NODE_PATTERNS: App integration detection patterns

Version: 2.0.0
"""

from typing import Dict, List, Tuple

from openjiuwen_studio.core.common.dsl import ComponentType


# =============================================================================
# MAIN NODE TYPE MAPPING: n8n → OpenJiuwen ComponentType
# =============================================================================

N8N_TO_OPENJIUWEN: Dict[str, ComponentType] = {
    # =========================================================================
    # TRIGGERS → Start (merged into workflow input)
    # =========================================================================
    "n8n-nodes-base.manualTrigger": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.webhook": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.scheduleTrigger": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.executeWorkflowTrigger": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.formTrigger": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.errorTrigger": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.emailTrigger": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-base.cron": ComponentType.COMPONENT_TYPE_START,
    "n8n-nodes-langchain.chatTrigger": ComponentType.COMPONENT_TYPE_START,
    "@n8n/n8n-nodes-langchain.chatTrigger": ComponentType.COMPONENT_TYPE_START,

    # =========================================================================
    # AI/LLM NODES → LLM
    # =========================================================================
    "n8n-nodes-langchain.agent": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.agent": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.chainLlm": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.chainLlm": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.chainRetrievalQa": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.chainRetrievalQa": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.chainSummarization": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.chainSummarization": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.informationExtractor": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.informationExtractor": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.textClassifier": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.textClassifier": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.sentimentAnalysis": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.sentimentAnalysis": ComponentType.COMPONENT_TYPE_LLM,
    # Vector stores also use LLM infrastructure
    "n8n-nodes-langchain.vectorStoreInMemory": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.vectorStoreInMemory": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.vectorStorePinecone": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.vectorStorePinecone": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.vectorStoreSupabase": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.vectorStoreSupabase": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.vectorStoreQdrant": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.vectorStoreQdrant": ComponentType.COMPONENT_TYPE_LLM,
    "n8n-nodes-langchain.vectorStorePgVector": ComponentType.COMPONENT_TYPE_LLM,
    "@n8n/n8n-nodes-langchain.vectorStorePgVector": ComponentType.COMPONENT_TYPE_LLM,

    # =========================================================================
    # CONDITIONALS → IF/Selector
    # =========================================================================
    "n8n-nodes-base.if": ComponentType.COMPONENT_TYPE_IF,
    "n8n-nodes-base.switch": ComponentType.COMPONENT_TYPE_IF,
    "n8n-nodes-base.filter": ComponentType.COMPONENT_TYPE_IF,

    # =========================================================================
    # LOOPS → Loop
    # =========================================================================
    "n8n-nodes-base.splitInBatches": ComponentType.COMPONENT_TYPE_LOOP,
    "n8n-nodes-base.loop": ComponentType.COMPONENT_TYPE_LOOP,

    # =========================================================================
    # DATA TRANSFORMATION → Code
    # =========================================================================
    "n8n-nodes-base.code": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.function": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.functionItem": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.set": ComponentType.COMPONENT_TYPE_CODE,  # Converted with actual Set logic
    "n8n-nodes-base.itemLists": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.splitOut": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.aggregate": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.removeDuplicates": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.sort": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.limit": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.compareDatasets": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.noOp": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.wait": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.respondToWebhook": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.stopAndError": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.html": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.markdown": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.xml": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.crypto": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.dateTime": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.compression": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.readBinaryFiles": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.writeBinaryFile": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.spreadsheetFile": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.readWriteFile": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.convertToFile": ComponentType.COMPONENT_TYPE_CODE,
    "n8n-nodes-base.extractFromFile": ComponentType.COMPONENT_TYPE_CODE,

    # =========================================================================
    # HTTP/API → Plugin
    # =========================================================================
    "n8n-nodes-base.httpRequest": ComponentType.COMPONENT_TYPE_PLUGIN,

    # =========================================================================
    # MERGE → Variable Merge
    # =========================================================================
    "n8n-nodes-base.merge": ComponentType.COMPONENT_TYPE_VARIABLE_MERGE,

    # =========================================================================
    # WORKFLOW CALLS → Workflow
    # =========================================================================
    "n8n-nodes-base.executeWorkflow": ComponentType.COMPONENT_TYPE_SUB_WORKFLOW,
}


# =============================================================================
# AI SUB-NODE MAPPINGS
# =============================================================================

# AI Sub-nodes that get EMBEDDED into LLM nodes (not converted separately)
AI_SUBNODES: Dict[str, Tuple[str, str]] = {
    # Chat Models (with and without @n8n/ prefix)
    "n8n-nodes-langchain.lmChatOpenAi": ("ai_languageModel", "openai"),
    "@n8n/n8n-nodes-langchain.lmChatOpenAi": ("ai_languageModel", "openai"),
    "n8n-nodes-langchain.lmChatAnthropic": ("ai_languageModel", "anthropic"),
    "@n8n/n8n-nodes-langchain.lmChatAnthropic": ("ai_languageModel", "anthropic"),
    "n8n-nodes-langchain.lmChatGoogleGemini": ("ai_languageModel", "gemini"),
    "@n8n/n8n-nodes-langchain.lmChatGoogleGemini": ("ai_languageModel", "gemini"),
    "n8n-nodes-langchain.lmChatAzureOpenAi": ("ai_languageModel", "azure-openai"),
    "@n8n/n8n-nodes-langchain.lmChatAzureOpenAi": ("ai_languageModel", "azure-openai"),
    "n8n-nodes-langchain.lmChatOllama": ("ai_languageModel", "ollama"),
    "@n8n/n8n-nodes-langchain.lmChatOllama": ("ai_languageModel", "ollama"),
    "n8n-nodes-langchain.lmChatGroq": ("ai_languageModel", "groq"),
    "@n8n/n8n-nodes-langchain.lmChatGroq": ("ai_languageModel", "groq"),
    "n8n-nodes-langchain.lmChatMistralCloud": ("ai_languageModel", "mistral"),
    "@n8n/n8n-nodes-langchain.lmChatMistralCloud": ("ai_languageModel", "mistral"),
    "n8n-nodes-langchain.lmChatDeepSeek": ("ai_languageModel", "deepseek"),
    "@n8n/n8n-nodes-langchain.lmChatDeepSeek": ("ai_languageModel", "deepseek"),
    "n8n-nodes-langchain.lmChatCohere": ("ai_languageModel", "cohere"),
    "@n8n/n8n-nodes-langchain.lmChatCohere": ("ai_languageModel", "cohere"),
    "n8n-nodes-langchain.lmChatAwsBedrock": ("ai_languageModel", "aws-bedrock"),
    "@n8n/n8n-nodes-langchain.lmChatAwsBedrock": ("ai_languageModel", "aws-bedrock"),
    "n8n-nodes-langchain.lmChatGoogleVertex": ("ai_languageModel", "google-vertex"),
    "@n8n/n8n-nodes-langchain.lmChatGoogleVertex": ("ai_languageModel", "google-vertex"),
    "n8n-nodes-langchain.lmChatOpenRouter": ("ai_languageModel", "openrouter"),
    "@n8n/n8n-nodes-langchain.lmChatOpenRouter": ("ai_languageModel", "openrouter"),
    # Basic LLMs
    "n8n-nodes-langchain.lmCohere": ("ai_languageModel", "cohere"),
    "@n8n/n8n-nodes-langchain.lmCohere": ("ai_languageModel", "cohere"),
    "n8n-nodes-langchain.lmOllama": ("ai_languageModel", "ollama"),
    "@n8n/n8n-nodes-langchain.lmOllama": ("ai_languageModel", "ollama"),
    # Memory
    "n8n-nodes-langchain.memoryBufferWindow": ("ai_memory", "buffer"),
    "@n8n/n8n-nodes-langchain.memoryBufferWindow": ("ai_memory", "buffer"),
    "n8n-nodes-langchain.memoryRedisChat": ("ai_memory", "redis"),
    "@n8n/n8n-nodes-langchain.memoryRedisChat": ("ai_memory", "redis"),
    "n8n-nodes-langchain.memoryPostgresChat": ("ai_memory", "postgres"),
    "@n8n/n8n-nodes-langchain.memoryPostgresChat": ("ai_memory", "postgres"),
    "n8n-nodes-langchain.memoryMongoChat": ("ai_memory", "mongodb"),
    "@n8n/n8n-nodes-langchain.memoryMongoChat": ("ai_memory", "mongodb"),
    "n8n-nodes-langchain.memoryXata": ("ai_memory", "xata"),
    "@n8n/n8n-nodes-langchain.memoryXata": ("ai_memory", "xata"),
    "n8n-nodes-langchain.memoryZep": ("ai_memory", "zep"),
    "@n8n/n8n-nodes-langchain.memoryZep": ("ai_memory", "zep"),
    # Embeddings
    "n8n-nodes-langchain.embeddingsOpenAi": ("ai_embedding", "openai"),
    "@n8n/n8n-nodes-langchain.embeddingsOpenAi": ("ai_embedding", "openai"),
    "n8n-nodes-langchain.embeddingsAzureOpenAi": ("ai_embedding", "azure"),
    "@n8n/n8n-nodes-langchain.embeddingsAzureOpenAi": ("ai_embedding", "azure"),
    "n8n-nodes-langchain.embeddingsGoogleGemini": ("ai_embedding", "gemini"),
    "@n8n/n8n-nodes-langchain.embeddingsGoogleGemini": ("ai_embedding", "gemini"),
    "n8n-nodes-langchain.embeddingsCohere": ("ai_embedding", "cohere"),
    "@n8n/n8n-nodes-langchain.embeddingsCohere": ("ai_embedding", "cohere"),
    "n8n-nodes-langchain.embeddingsOllama": ("ai_embedding", "ollama"),
    "@n8n/n8n-nodes-langchain.embeddingsOllama": ("ai_embedding", "ollama"),
    # Tools
    "n8n-nodes-langchain.toolCalculator": ("ai_tool", "calculator"),
    "@n8n/n8n-nodes-langchain.toolCalculator": ("ai_tool", "calculator"),
    "n8n-nodes-langchain.toolCode": ("ai_tool", "code"),
    "@n8n/n8n-nodes-langchain.toolCode": ("ai_tool", "code"),
    "n8n-nodes-langchain.toolHttpRequest": ("ai_tool", "http"),
    "@n8n/n8n-nodes-langchain.toolHttpRequest": ("ai_tool", "http"),
    "n8n-nodes-langchain.toolWorkflow": ("ai_tool", "workflow"),
    "@n8n/n8n-nodes-langchain.toolWorkflow": ("ai_tool", "workflow"),
    "n8n-nodes-langchain.toolWikipedia": ("ai_tool", "wikipedia"),
    "@n8n/n8n-nodes-langchain.toolWikipedia": ("ai_tool", "wikipedia"),
    "n8n-nodes-langchain.toolSerpApi": ("ai_tool", "serpapi"),
    "@n8n/n8n-nodes-langchain.toolSerpApi": ("ai_tool", "serpapi"),
    "n8n-nodes-langchain.toolWolframAlpha": ("ai_tool", "wolfram"),
    "@n8n/n8n-nodes-langchain.toolWolframAlpha": ("ai_tool", "wolfram"),
    "n8n-nodes-langchain.toolVectorStore": ("ai_tool", "vectorstore"),
    "@n8n/n8n-nodes-langchain.toolVectorStore": ("ai_tool", "vectorstore"),
    "n8n-nodes-langchain.toolMcp": ("ai_tool", "mcp"),
    "@n8n/n8n-nodes-langchain.toolMcp": ("ai_tool", "mcp"),
    # Document Loaders
    "n8n-nodes-langchain.documentDefaultDataLoader": ("ai_document", "default"),
    "@n8n/n8n-nodes-langchain.documentDefaultDataLoader": ("ai_document", "default"),
    "n8n-nodes-langchain.documentGithubLoader": ("ai_document", "github"),
    "@n8n/n8n-nodes-langchain.documentGithubLoader": ("ai_document", "github"),
    # Text Splitters
    "n8n-nodes-langchain.textSplitterCharacter": ("ai_splitter", "character"),
    "@n8n/n8n-nodes-langchain.textSplitterCharacter": ("ai_splitter", "character"),
    "n8n-nodes-langchain.textSplitterRecursiveCharacter": ("ai_splitter", "recursive"),
    "@n8n/n8n-nodes-langchain.textSplitterRecursiveCharacter": ("ai_splitter", "recursive"),
    # Output Parsers
    "n8n-nodes-langchain.outputParserStructured": ("ai_parser", "structured"),
    "@n8n/n8n-nodes-langchain.outputParserStructured": ("ai_parser", "structured"),
    "n8n-nodes-langchain.outputParserAutofixing": ("ai_parser", "autofixing"),
    "@n8n/n8n-nodes-langchain.outputParserAutofixing": ("ai_parser", "autofixing"),
}


# =============================================================================
# APP INTEGRATION PATTERNS
# =============================================================================

# App integration patterns (detected by substring matching)
APP_NODE_PATTERNS: List[str] = [
    "slack", "discord", "telegram", "gmail", "google", "microsoft",
    "github", "gitlab", "jira", "notion", "airtable", "mysql", "postgres",
    "mongodb", "redis", "elasticsearch", "aws", "azure", "openai",
    "stripe", "twilio", "sendgrid", "mailchimp", "hubspot", "salesforce",
    "shopify", "wordpress", "dropbox", "box", "onedrive", "ftp", "ssh",
    "jenkins", "docker", "kubernetes", "grafana", "prometheus", "datadog",
    "splunk", "pagerduty", "opsgenie", "zendesk", "freshdesk", "intercom",
    "asana", "trello", "monday", "clickup", "basecamp", "todoist", "linear",
    "figma", "miro", "confluence", "bitbucket", "circleci", "travisci",
    "netlify", "vercel", "heroku", "digitalocean", "linode", "vultr",
    "cloudflare", "fastly", "akamai", "auth0", "okta", "keycloak",
    "segment", "mixpanel", "amplitude", "heap", "fullstory", "hotjar",
    "supabase", "firebase", "appwrite", "hasura", "directus", "strapi",
    "contentful", "sanity", "prismic", "storyblok", "webflow", "bubble",
    "zapier", "make", "ifttt", "pipedream", "tray", "workato",
]