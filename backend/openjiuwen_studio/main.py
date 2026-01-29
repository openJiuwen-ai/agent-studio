import io
import os
import sys
from contextlib import asynccontextmanager

# 添加项目根目录到 Python 路径，以便直接运行时能找到所有模块
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from project root (上级目录)
project_root = os.path.dirname(backend_dir)
load_dotenv(os.path.join(project_root, '.env'))

from openjiuwen_studio.ops.modules.prompt.infra.database import create_database_tables
from openjiuwen_studio.memory_engine_start import MemoryEngineManager

from openjiuwen_studio.routers import register
from openjiuwen_studio.core.database import engine
from openjiuwen_studio.models.db_fun_base import Base
# Import all models to ensure they are registered with SQLAlchemy
from openjiuwen_studio.models import ModelConfig, ModelUsageLog, EmbeddingModelConfig, AgentBaseDB, AgentPublishDB, \
    PromptRelationDB, TagDB, UserDB, SpaceDB, SpaceUserDB, WorkflowBaseDB, WorkflowPublishDB, PluginBaseDB, \
    PluginPublishDB, ToolBaseDB, \
    WorkflowExecutionDB, WorkflowExecutionDetailsDB, AgentExecutionDB, AgentExecutionDetailsDB, \
    AgentWorkflowRelationDB, KnowledgeBaseDB, KnowledgeBaseDocumentDB, ReferenceDB, SystemEmbeddingModelDB, \
    SystemLLMModelDB
# Import database sync tool
from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.db_sync import run_database_sync
from openjiuwen_studio.ops.config import settings as ops_settings
# Import Trace models
from openjiuwen_studio.models.trace_detail import TraceDetailDB
from openjiuwen_studio.models.trace_summary import TraceSummaryDB
from openjiuwen_studio.models.tag import workflow_tag_association

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


@asynccontextmanager
async def lifespan_func(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Jiuwen Agent Studio Backend...")

    target_tables = [
        ModelConfig.__table__,
        ModelUsageLog.__table__,
        EmbeddingModelConfig.__table__,
        AgentBaseDB.__table__,
        AgentPublishDB.__table__,
        PromptRelationDB.__table__,
        TagDB.__table__,
        UserDB.__table__,
        SpaceDB.__table__,
        SpaceUserDB.__table__,
        WorkflowBaseDB.__table__,
        WorkflowPublishDB.__table__,
        PluginBaseDB.__table__,
        PluginPublishDB.__table__,
        ToolBaseDB.__table__,
        WorkflowExecutionDB.__table__,
        WorkflowExecutionDetailsDB.__table__,
        AgentExecutionDB.__table__,
        AgentExecutionDetailsDB.__table__,
        AgentWorkflowRelationDB.__table__,
        ReferenceDB.__table__,
        # Trace tables
        TraceDetailDB.__table__,
        TraceSummaryDB.__table__,
        # Knowledge Base tables
        KnowledgeBaseDB.__table__,
        KnowledgeBaseDocumentDB.__table__,
        # System model tables
        SystemLLMModelDB.__table__,
        SystemEmbeddingModelDB.__table__,
    ]

    if engine.url.drivername == "sqlite":
        renamed_count = 0
        for table in target_tables:
            # Skip if table has no index attribute
            if not hasattr(table, "indexes"):
                logger.warning(f"Table {table.name} has no indexes attribute, skipping...")
                continue
                # Iterate all indexes of the table
            for idx in table.indexes:
                old_idx_name = idx.name
                idx.name = f"{old_idx_name}_{table.name}"
                logger.info(f"{table.name}: Renamed index: {old_idx_name} ---> {idx.name}")
                renamed_count += 1
        logger.info(f"Duplicate index renaming completed. Total renamed indexes: {renamed_count}")

    # Create database tables with checkfirst=True to avoid creating existing indexes
    Base.metadata.create_all(
        bind=engine,
        tables=target_tables,
        checkfirst=True
    )
    await MemoryEngineManager.init()

    # Create workflow_tag_association table if it doesn't exist
    workflow_tag_association.create(bind=engine, checkfirst=True)

    # 运行数据库字段同步（添加新字段）
    run_database_sync()
    logger.info("✅ Database field sync completed")

    # ops数据库相关表自动创建
    create_database_tables()
    logger.info("✅ Database tables created")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Jiuwen Agent Studio Backend...")


# Create FastAPI app
app = FastAPI(
    title="Jiuwen Agent Studio API",
    description="Backend API for Jiuwen Agent Studio - Professional LLM Agent Development Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan_func,
    # 添加Swagger UI的OAuth2配置
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "appName": "Jiuwen Agent Studio API",
        "clientId": "swagger-ui",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Jiuwen Agent Studio Backend",
        "docs": "/api/docs",
        "health": "/api/health"
    }


register.router_register(app)


def main():
    # Development configuration
    config = {
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("BACKEND_PORT", "8000")),
        "reload": False,
        "log_level": "info",
        "access_log": True,
        "workers": int(os.getenv("WORKER_NUM", 1))
        if (os.getenv("INDEX_MANAGER_TYPE") == "milvus" and os.getenv("DB_TYPE") == "mysql")
        else 1,
    }

    logger.info("🚀 Starting Jiuwen Agent Studio Backend in development mode...")
    logger.info(f"📍 Server will be available at: http://{config['host']}:{config['port']}")
    logger.info(f"📚 API Documentation: http://{config['host']}:{config['port']}/api/docs")
    logger.info(f"🔍 Health Check: http://{config['host']}:{config['port']}/api/health")
    logger.info("🔄 Auto-reload enabled for development")
    logger.info("⏹️  Press Ctrl+C to stop the server")
    logger.info("-" * 60)

    # Start the server；force asyncio loop to avoid uvloop + nest_asyncio conflict
    uvicorn.run(
        "openjiuwen_studio.main:app",
        loop="asyncio",
        **config
    )


if __name__ == "__main__":
    main()
