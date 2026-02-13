"""
n8n Workflow Parser Utility
===========================
Parse n8n workflow JSON exports and extract structured information
for conversion to other agentic frameworks (LangChain, CrewAI, AutoGen, etc.)

Author: Generated for CodyFix/Jiuwen framework integration
Version: 1.0.0
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class NodeCategory(Enum):
    """Categories of n8n nodes"""
    TRIGGER = "trigger"
    CORE = "core"
    AI_ROOT = "ai_root"
    AI_SUBNODE = "ai_subnode"
    APP_ACTION = "app_action"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """Types of node connections"""
    MAIN = "main"
    AI_LANGUAGE_MODEL = "ai_languageModel"
    AI_MEMORY = "ai_memory"
    AI_TOOL = "ai_tool"
    AI_EMBEDDING = "ai_embedding"
    AI_RETRIEVER = "ai_retriever"
    AI_OUTPUT_PARSER = "ai_outputParser"
    AI_DOCUMENT = "ai_document"
    AI_TEXT_SPLITTER = "ai_textSplitter"
    AI_VECTOR_STORE = "ai_vectorStore"


@dataclass
class N8nNode:
    """Represents a parsed n8n node"""
    id: str
    name: str
    type: str
    type_version: float
    position: Tuple[int, int]
    parameters: Dict[str, Any]
    credentials: Dict[str, Any] = field(default_factory=dict)
    disabled: bool = False
    notes: str = ""
    category: NodeCategory = NodeCategory.UNKNOWN
    
    # For AI nodes
    is_ai_root: bool = False
    is_ai_subnode: bool = False
    subnode_connection_type: Optional[str] = None


@dataclass
class N8nConnection:
    """Represents a connection between nodes"""
    source_node: str
    target_node: str
    connection_type: str
    source_index: int
    target_index: int


@dataclass
class N8nTool:
    """Represents a tool connected to an AI agent"""
    name: str
    type: str
    description: str
    parameters: Dict[str, Any]
    tool_category: str  # builtin, custom, api, workflow, search, etc.


@dataclass
class N8nAgent:
    """Represents an AI Agent with all its components"""
    name: str
    node_id: str
    system_prompt: Optional[str]
    model: Optional[N8nNode]
    memory: Optional[N8nNode]
    tools: List[N8nTool]
    output_parser: Optional[N8nNode]
    parameters: Dict[str, Any]


@dataclass
class ParsedWorkflow:
    """Complete parsed workflow structure"""
    name: str
    nodes: List[N8nNode]
    connections: List[N8nConnection]
    triggers: List[N8nNode]
    agents: List[N8nAgent]
    ai_root_nodes: List[N8nNode]
    ai_subnodes: List[N8nNode]
    core_nodes: List[N8nNode]
    app_nodes: List[N8nNode]


# Node type patterns for classification
TRIGGER_PATTERNS = [
    r".*Trigger$",
    r".*trigger$",
    r"n8n-nodes-base\.webhook$",
]

AI_ROOT_TYPES = {
    "n8n-nodes-langchain.agent",
    "n8n-nodes-langchain.chainLlm",
    "n8n-nodes-langchain.chainRetrievalQa",
    "n8n-nodes-langchain.chainSummarization",
    "n8n-nodes-langchain.informationExtractor",
    "n8n-nodes-langchain.textClassifier",
    "n8n-nodes-langchain.sentimentAnalysis",
    "n8n-nodes-langchain.code",
    "n8n-nodes-langchain.vectorStoreInMemory",
    "n8n-nodes-langchain.vectorStorePinecone",
    "n8n-nodes-langchain.vectorStoreSupabase",
    "n8n-nodes-langchain.vectorStoreQdrant",
    "n8n-nodes-langchain.vectorStorePgVector",
    "n8n-nodes-langchain.vectorStoreMilvus",
    "n8n-nodes-langchain.vectorStoreWeaviate",
    "n8n-nodes-langchain.vectorStoreMongoDBAtlas",
    "n8n-nodes-langchain.vectorStoreRedis",
    "n8n-nodes-langchain.vectorStoreZep",
    "n8n-nodes-langchain.vectorStoreAzureAISearch",
}

AI_SUBNODE_MAPPING = {
    # Chat Models
    "n8n-nodes-langchain.lmChatOpenAi": ("ai_languageModel", "openai"),
    "n8n-nodes-langchain.lmChatAnthropic": ("ai_languageModel", "anthropic"),
    "n8n-nodes-langchain.lmChatGoogleGemini": ("ai_languageModel", "google"),
    "n8n-nodes-langchain.lmChatAzureOpenAi": ("ai_languageModel", "azure"),
    "n8n-nodes-langchain.lmChatOllama": ("ai_languageModel", "ollama"),
    "n8n-nodes-langchain.lmChatGroq": ("ai_languageModel", "groq"),
    "n8n-nodes-langchain.lmChatMistralCloud": ("ai_languageModel", "mistral"),
    "n8n-nodes-langchain.lmChatDeepSeek": ("ai_languageModel", "deepseek"),
    "n8n-nodes-langchain.lmChatCohere": ("ai_languageModel", "cohere"),
    "n8n-nodes-langchain.lmChatAwsBedrock": ("ai_languageModel", "aws"),
    "n8n-nodes-langchain.lmChatGoogleVertex": ("ai_languageModel", "google_vertex"),
    "n8n-nodes-langchain.lmChatOpenRouter": ("ai_languageModel", "openrouter"),
    "n8n-nodes-langchain.lmChatXaiGrok": ("ai_languageModel", "xai"),
    "n8n-nodes-langchain.lmChatVercel": ("ai_languageModel", "vercel"),
    # Basic LLMs
    "n8n-nodes-langchain.lmCohere": ("ai_languageModel", "cohere"),
    "n8n-nodes-langchain.lmOllama": ("ai_languageModel", "ollama"),
    "n8n-nodes-langchain.lmOpenHuggingFaceInference": ("ai_languageModel", "huggingface"),
    # Memory
    "n8n-nodes-langchain.memoryBufferWindow": ("ai_memory", "in_memory"),
    "n8n-nodes-langchain.memoryRedisChat": ("ai_memory", "redis"),
    "n8n-nodes-langchain.memoryPostgresChat": ("ai_memory", "postgres"),
    "n8n-nodes-langchain.memoryMongoChat": ("ai_memory", "mongodb"),
    "n8n-nodes-langchain.memoryXata": ("ai_memory", "xata"),
    "n8n-nodes-langchain.memoryZep": ("ai_memory", "zep"),
    "n8n-nodes-langchain.memoryMotorhead": ("ai_memory", "motorhead"),
    "n8n-nodes-langchain.memoryManager": ("ai_memory", "manager"),
    # Embeddings
    "n8n-nodes-langchain.embeddingsOpenAi": ("ai_embedding", "openai"),
    "n8n-nodes-langchain.embeddingsAzureOpenAi": ("ai_embedding", "azure"),
    "n8n-nodes-langchain.embeddingsGoogleGemini": ("ai_embedding", "google"),
    "n8n-nodes-langchain.embeddingsGoogleVertex": ("ai_embedding", "google_vertex"),
    "n8n-nodes-langchain.embeddingsGooglePalm": ("ai_embedding", "google_palm"),
    "n8n-nodes-langchain.embeddingsCohere": ("ai_embedding", "cohere"),
    "n8n-nodes-langchain.embeddingsOllama": ("ai_embedding", "ollama"),
    "n8n-nodes-langchain.embeddingsHuggingFaceInference": ("ai_embedding", "huggingface"),
    "n8n-nodes-langchain.embeddingsAwsBedrock": ("ai_embedding", "aws"),
    "n8n-nodes-langchain.embeddingsMistralCloud": ("ai_embedding", "mistral"),
    # Tools
    "n8n-nodes-langchain.toolCalculator": ("ai_tool", "builtin"),
    "n8n-nodes-langchain.toolCode": ("ai_tool", "custom"),
    "n8n-nodes-langchain.toolHttpRequest": ("ai_tool", "api"),
    "n8n-nodes-langchain.toolWorkflow": ("ai_tool", "workflow"),
    "n8n-nodes-langchain.toolWikipedia": ("ai_tool", "search"),
    "n8n-nodes-langchain.toolSerpApi": ("ai_tool", "search"),
    "n8n-nodes-langchain.toolWolframAlpha": ("ai_tool", "computation"),
    "n8n-nodes-langchain.toolVectorStore": ("ai_tool", "retrieval"),
    "n8n-nodes-langchain.toolMcp": ("ai_tool", "protocol"),
    "n8n-nodes-langchain.toolSearxng": ("ai_tool", "search"),
    "n8n-nodes-langchain.toolThink": ("ai_tool", "reasoning"),
    "n8n-nodes-langchain.toolAiAgent": ("ai_tool", "agent"),
    # Document Loaders
    "n8n-nodes-langchain.documentDefaultDataLoader": ("ai_document", "default"),
    "n8n-nodes-langchain.documentGitHubLoader": ("ai_document", "github"),
    # Text Splitters
    "n8n-nodes-langchain.textSplitterCharacterTextSplitter": ("ai_textSplitter", "character"),
    "n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter": ("ai_textSplitter", "recursive"),
    "n8n-nodes-langchain.textSplitterTokenSplitter": ("ai_textSplitter", "token"),
    # Retrievers
    "n8n-nodes-langchain.retrieverVectorStore": ("ai_retriever", "vector_store"),
    "n8n-nodes-langchain.retrieverMultiQuery": ("ai_retriever", "multi_query"),
    "n8n-nodes-langchain.retrieverContextualCompression": ("ai_retriever", "compression"),
    "n8n-nodes-langchain.retrieverWorkflow": ("ai_retriever", "workflow"),
    # Output Parsers
    "n8n-nodes-langchain.outputParserStructured": ("ai_outputParser", "structured"),
    "n8n-nodes-langchain.outputParserItemList": ("ai_outputParser", "item_list"),
    "n8n-nodes-langchain.outputParserAutoFixing": ("ai_outputParser", "auto_fixing"),
    # Other
    "n8n-nodes-langchain.rerankerCohere": ("ai_reranker", "cohere"),
    "n8n-nodes-langchain.modelSelector": ("ai_languageModel", "selector"),
}

CORE_NODE_TYPES = {
    "n8n-nodes-base.code",
    "n8n-nodes-base.if",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.merge",
    "n8n-nodes-base.splitInBatches",
    "n8n-nodes-base.set",
    "n8n-nodes-base.filter",
    "n8n-nodes-base.sort",
    "n8n-nodes-base.limit",
    "n8n-nodes-base.aggregate",
    "n8n-nodes-base.splitOut",
    "n8n-nodes-base.removeDuplicates",
    "n8n-nodes-base.renameKeys",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.wait",
    "n8n-nodes-base.executeWorkflow",
    "n8n-nodes-base.respondToWebhook",
    "n8n-nodes-base.stopAndError",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.html",
    "n8n-nodes-base.xml",
    "n8n-nodes-base.markdown",
    "n8n-nodes-base.crypto",
    "n8n-nodes-base.dateTime",
    "n8n-nodes-base.jwt",
    "n8n-nodes-base.totp",
    "n8n-nodes-base.compression",
    "n8n-nodes-base.convertToFile",
    "n8n-nodes-base.extractFromFile",
    "n8n-nodes-base.readWriteFile",
    "n8n-nodes-base.graphql",
    "n8n-nodes-base.ftp",
    "n8n-nodes-base.ssh",
    "n8n-nodes-base.git",
    "n8n-nodes-base.ldap",
    "n8n-nodes-base.sendEmail",
    "n8n-nodes-base.rssRead",
    "n8n-nodes-base.summarize",
    "n8n-nodes-base.compareDatasets",
    "n8n-nodes-base.aiTransform",
    "n8n-nodes-base.debugHelper",
    "n8n-nodes-langchain.respondToChat",
    "n8n-nodes-langchain.guardrails",
}


class N8nWorkflowParser:
    """Parser for n8n workflow JSON exports"""
    
    def __init__(self, workflow_json: Dict[str, Any]):
        self.raw = workflow_json
        self.nodes_by_name: Dict[str, N8nNode] = {}
        self.nodes_by_id: Dict[str, N8nNode] = {}
        
    def parse(self) -> ParsedWorkflow:
        """Parse the complete workflow"""
        # Parse all nodes
        nodes = self._parse_nodes()
        
        # Build lookup dictionaries
        for node in nodes:
            self.nodes_by_name[node.name] = node
            self.nodes_by_id[node.id] = node
        
        # Parse connections
        connections = self._parse_connections()
        
        # Categorize nodes
        triggers = [n for n in nodes if n.category == NodeCategory.TRIGGER]
        ai_roots = [n for n in nodes if n.category == NodeCategory.AI_ROOT]
        ai_subs = [n for n in nodes if n.category == NodeCategory.AI_SUBNODE]
        core = [n for n in nodes if n.category == NodeCategory.CORE]
        apps = [n for n in nodes if n.category == NodeCategory.APP_ACTION]
        
        # Extract agents with their tools
        agents = self._extract_agents(ai_roots, connections)
        
        return ParsedWorkflow(
            name=self.raw.get("name", "Unnamed Workflow"),
            nodes=nodes,
            connections=connections,
            triggers=triggers,
            agents=agents,
            ai_root_nodes=ai_roots,
            ai_subnodes=ai_subs,
            core_nodes=core,
            app_nodes=apps
        )
    
    def _parse_nodes(self) -> List[N8nNode]:
        """Parse all nodes from workflow"""
        nodes = []
        for raw_node in self.raw.get("nodes", []):
            node = self._parse_single_node(raw_node)
            nodes.append(node)
        return nodes
    
    def _parse_single_node(self, raw: Dict[str, Any]) -> N8nNode:
        """Parse a single node"""
        node_type = raw.get("type", "")
        category = self._classify_node(node_type)
        
        node = N8nNode(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            type=node_type,
            type_version=raw.get("typeVersion", 1),
            position=tuple(raw.get("position", [0, 0])),
            parameters=raw.get("parameters", {}),
            credentials=raw.get("credentials", {}),
            disabled=raw.get("disabled", False),
            notes=raw.get("notes", ""),
            category=category
        )
        
        # Set AI-specific attributes
        if category == NodeCategory.AI_ROOT:
            node.is_ai_root = True
        elif category == NodeCategory.AI_SUBNODE:
            node.is_ai_subnode = True
            if node_type in AI_SUBNODE_MAPPING:
                node.subnode_connection_type = AI_SUBNODE_MAPPING[node_type][0]
        
        return node
    
    def _classify_node(self, node_type: str) -> NodeCategory:
        """Classify a node by its type"""
        # Check for triggers
        for pattern in TRIGGER_PATTERNS:
            if re.match(pattern, node_type):
                return NodeCategory.TRIGGER
        
        # Check for AI root nodes
        if node_type in AI_ROOT_TYPES:
            return NodeCategory.AI_ROOT
        
        # Check for AI sub-nodes
        if node_type in AI_SUBNODE_MAPPING:
            return NodeCategory.AI_SUBNODE
        
        # Check for core nodes
        if node_type in CORE_NODE_TYPES:
            return NodeCategory.CORE
        
        # Default to app action (integration nodes)
        if node_type.startswith("n8n-nodes-"):
            return NodeCategory.APP_ACTION
        
        return NodeCategory.UNKNOWN
    
    def _parse_connections(self) -> List[N8nConnection]:
        """Parse all connections from workflow"""
        connections = []
        raw_conns = self.raw.get("connections", {})
        
        for source_name, outputs in raw_conns.items():
            for conn_type, output_arrays in outputs.items():
                for source_idx, targets in enumerate(output_arrays):
                    for target in targets:
                        conn = N8nConnection(
                            source_node=source_name,
                            target_node=target.get("node", ""),
                            connection_type=conn_type,
                            source_index=source_idx,
                            target_index=target.get("index", 0)
                        )
                        connections.append(conn)
        
        return connections
    
    def _extract_agents(self, ai_roots: List[N8nNode], 
                        connections: List[N8nConnection]) -> List[N8nAgent]:
        """Extract agent definitions with their connected components"""
        agents = []
        
        for root in ai_roots:
            if root.type != "n8n-nodes-langchain.agent":
                continue
            
            # Find connected components
            model = self._find_connected_subnode(root.name, "ai_languageModel", connections)
            memory = self._find_connected_subnode(root.name, "ai_memory", connections)
            output_parser = self._find_connected_subnode(root.name, "ai_outputParser", connections)
            tools = self._extract_agent_tools(root.name, connections)
            
            # Extract system prompt
            options = root.parameters.get("options", {})
            system_prompt = options.get("systemMessage")
            
            agent = N8nAgent(
                name=root.name,
                node_id=root.id,
                system_prompt=system_prompt,
                model=model,
                memory=memory,
                tools=tools,
                output_parser=output_parser,
                parameters=root.parameters
            )
            agents.append(agent)
        
        return agents
    
    def _find_connected_subnode(self, target_name: str, conn_type: str,
                                 connections: List[N8nConnection]) -> Optional[N8nNode]:
        """Find a subnode connected to target with specific connection type"""
        for conn in connections:
            if conn.target_node == target_name and conn.connection_type == conn_type:
                return self.nodes_by_name.get(conn.source_node)
        return None
    
    def _extract_agent_tools(self, agent_name: str, 
                             connections: List[N8nConnection]) -> List[N8nTool]:
        """Extract all tools connected to an agent"""
        tools = []
        
        for conn in connections:
            if conn.target_node == agent_name and conn.connection_type == "ai_tool":
                tool_node = self.nodes_by_name.get(conn.source_node)
                if tool_node:
                    # Determine tool category
                    tool_category = "unknown"
                    if tool_node.type in AI_SUBNODE_MAPPING:
                        tool_category = AI_SUBNODE_MAPPING[tool_node.type][1]
                    
                    # Extract description
                    desc = tool_node.parameters.get("description", "")
                    if not desc:
                        desc = tool_node.parameters.get("toolDescription", "")
                    
                    tool = N8nTool(
                        name=tool_node.name,
                        type=tool_node.type,
                        description=desc,
                        parameters=tool_node.parameters,
                        tool_category=tool_category
                    )
                    tools.append(tool)
        
        return tools


def parse_workflow_file(filepath: str) -> ParsedWorkflow:
    """Parse an n8n workflow from a JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    parser = N8nWorkflowParser(data)
    return parser.parse()


def parse_workflow_json(json_str: str) -> ParsedWorkflow:
    """Parse an n8n workflow from a JSON string"""
    data = json.loads(json_str)
    parser = N8nWorkflowParser(data)
    return parser.parse()


def workflow_to_dict(parsed: ParsedWorkflow) -> Dict[str, Any]:
    """Convert parsed workflow to a dictionary for serialization"""
    return {
        "name": parsed.name,
        "summary": {
            "total_nodes": len(parsed.nodes),
            "triggers": len(parsed.triggers),
            "agents": len(parsed.agents),
            "ai_root_nodes": len(parsed.ai_root_nodes),
            "ai_subnodes": len(parsed.ai_subnodes),
            "core_nodes": len(parsed.core_nodes),
            "app_nodes": len(parsed.app_nodes),
        },
        "triggers": [
            {"name": n.name, "type": n.type}
            for n in parsed.triggers
        ],
        "agents": [
            {
                "name": a.name,
                "system_prompt": a.system_prompt,
                "model": a.model.type if a.model else None,
                "memory": a.memory.type if a.memory else None,
                "tools": [
                    {
                        "name": t.name,
                        "type": t.type,
                        "category": t.tool_category,
                        "description": t.description
                    }
                    for t in a.tools
                ]
            }
            for a in parsed.agents
        ],
        "nodes_by_category": {
            "triggers": [{"name": n.name, "type": n.type} for n in parsed.triggers],
            "ai_root": [{"name": n.name, "type": n.type} for n in parsed.ai_root_nodes],
            "ai_subnode": [{"name": n.name, "type": n.type} for n in parsed.ai_subnodes],
            "core": [{"name": n.name, "type": n.type} for n in parsed.core_nodes],
            "app": [{"name": n.name, "type": n.type} for n in parsed.app_nodes],
        }
    }


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        parsed = parse_workflow_file(filepath)
        result = workflow_to_dict(parsed)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python n8n_workflow_parser.py <workflow.json>")
        print("\nThis utility parses n8n workflow exports and extracts:")
        print("  - All nodes categorized by type")
        print("  - AI agents with their tools, models, and memory")
        print("  - Connections between nodes")
        print("  - Tool configurations for agent frameworks")
