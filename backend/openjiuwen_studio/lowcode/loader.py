#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
低代码Agent加载器 - 将导出的Agent配置转换为可执行实例
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import json
import zipfile
import io
import logging
from datetime import datetime

from openjiuwen_studio.lowcode.schemas import (
    AgentExportData,
    ModelOverride,
    ValidationResult,
    ValidationError
)
from openjiuwen_studio.lowcode.config_adapter import ConfigAdapter
from openjiuwen_studio.lowcode.model_resolver import ModelResolver
from openjiuwen_studio.lowcode.dependency_processor import DependencyProcessor

logger = logging.getLogger(__name__)


class LowCodeAgentLoader:
    """
    低代码Agent加载器
    
    负责将导出的Agent JSON配置转换为可执行的Agent实例
    """
    
    def __init__(
        self,
        workflow_runner: Optional[Any] = None,
        plugin_manager: Optional[Any] = None
    ):
        self.config_adapter = ConfigAdapter()
        self.model_resolver = ModelResolver()
        self.dep_processor = DependencyProcessor(
            workflow_runner=workflow_runner,
            plugin_manager=plugin_manager
        )
    
    async def load_from_export_data(
        self,
        export_data: Dict[str, Any],
        model_overrides: Optional[Dict[str, ModelOverride]] = None,
        current_user: Optional[Dict] = None,
        use_env_config: bool = True
    ) -> Any:
        """
        从导出数据加载Agent
        
        Args:
            export_data: 导出的Agent数据
            model_overrides: 模型覆盖配置
            current_user: 当前用户信息
            use_env_config: 是否使用环境变量配置（默认True）
            
        Returns:
            可执行的Agent实例
        """
        logger.info("Starting to load agent from export data")
        
        LowCodeAgentLoader._validate_export_data(export_data)
        
        agent_config = export_data.get("agent", {})
        model_references = export_data.get("model_references", {})
        dependencies = export_data.get("dependencies", {})
        
        agent_config = self.model_resolver.resolve(
            agent_config,
            model_references,
            model_overrides,
            use_env_config=use_env_config
        )
        
        # 4. 验证模型配置
        is_valid, errors = self.model_resolver.validate_model_config(agent_config)
        if not is_valid:
            raise ValueError(f"Invalid model configuration: {', '.join(errors)}")
        
        # 5. 处理依赖项
        workflows, plugins, knowledge_bases = await self.dep_processor.process(
            dependencies,
            current_user
        )
        
        # 6. 转换配置为DL格式
        dl_config = self.config_adapter.convert_to_agent_dl_config(
            agent_config=agent_config,
            workflows=workflows,
            plugins=plugins,
            knowledge_bases=knowledge_bases
        )
        
        # 7. 创建并编译Agent
        # 注意：这里我们返回配置对象，实际的Agent编译由调用方完成
        # 这样可以避免循环导入和复杂的依赖关系
        return {
            "config": dl_config,
            "workflows": workflows,
            "plugins": plugins,
            "knowledge_bases": knowledge_bases,
            "agent_config": agent_config
        }
    
    async def load_from_config_file(
        self,
        config_path: Union[str, Path, io.BytesIO],
        model_overrides: Optional[Dict[str, ModelOverride]] = None,
        current_user: Optional[Dict] = None,
        use_env_config: bool = True
    ) -> Any:
        """
        从配置文件加载（支持JSON和ZIP）
        
        Args:
            config_path: 配置文件路径或BytesIO对象
            model_overrides: 模型覆盖配置
            current_user: 当前用户信息
            use_env_config: 是否使用环境变量配置（默认True）
            
        Returns:
            可执行的Agent实例
        """
        logger.info(f"Loading agent from config file: {config_path}")
        
        if isinstance(config_path, io.BytesIO):
            export_data = LowCodeAgentLoader._load_from_zip_bytes(config_path)
        elif isinstance(config_path, (str, Path)) and zipfile.is_zipfile(config_path):
            export_data = LowCodeAgentLoader._load_from_zip(config_path)
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                export_data = json.load(f)
        
        return await self.load_from_export_data(
            export_data=export_data,
            model_overrides=model_overrides,
            current_user=current_user,
            use_env_config=use_env_config
        )
    
    @staticmethod
    def _load_from_zip(
        config_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        从 ZIP 文件加载配置
        
        Args:
            config_path: ZIP 文件路径
            
        Returns:
            导出的 Agent 数据
        """
        with zipfile.ZipFile(config_path, 'r') as zf:
            # 查找主配置文件
            json_files = [f for f in zf.namelist() if f.endswith('.json')]
            if not json_files:
                raise ValueError("No JSON file found in ZIP archive")
            
            # 通常主配置文件是第一个 JSON 文件
            main_config_file = json_files[0]
            
            with zf.open(main_config_file) as f:
                export_data = json.loads(f.read().decode('utf-8'))
            
            # 处理知识库文档（如果有）
            LowCodeAgentLoader._process_zip_documents(zf, export_data)
        
        return export_data
    
    @staticmethod
    def _load_from_zip_bytes(
        zip_buffer: io.BytesIO
    ) -> Dict[str, Any]:
        """
        从 ZIP 字节流加载配置
        
        Args:
            zip_buffer: ZIP 文件字节流
            
        Returns:
            导出的 Agent 数据
        """
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            json_files = [f for f in zf.namelist() if f.endswith('.json')]
            if not json_files:
                raise ValueError("No JSON file found in ZIP archive")
            
            main_config_file = json_files[0]
            
            with zf.open(main_config_file) as f:
                export_data = json.loads(f.read().decode('utf-8'))
            
            LowCodeAgentLoader._process_zip_documents(zf, export_data)
        
        return export_data
    
    @staticmethod
    def _process_zip_documents(
        zf: zipfile.ZipFile,
        export_data: Dict[str, Any]
    ):
        """
        处理 ZIP 中的文档
        
        Args:
            zf: ZIP 文件对象
            export_data: 导出数据
        """
        # 查找 documents 目录下的文件
        documents = {}
        for file_name in zf.namelist():
            if file_name.startswith('documents/'):
                parts = file_name.split('/')
                if len(parts) >= 3:
                    kb_id = parts[1]
                    doc_name = parts[2]
                    
                    if kb_id not in documents:
                        documents[kb_id] = []
                    
                    documents[kb_id].append({
                        "file_name": doc_name,
                        "file_path": file_name
                    })
        
        # 更新知识库配置
        if "dependencies" in export_data and "knowledge_bases" in export_data["dependencies"]:
            for kb in export_data["dependencies"]["knowledge_bases"]:
                kb_id = kb.get("knowledge_base_id") or kb.get("id")
                if kb_id and kb_id in documents:
                    kb["documents"] = documents[kb_id]
    
    @staticmethod
    def _validate_export_data(
        export_data: Dict[str, Any]
    ):
        """
        验证导出数据格式
        
        Args:
            export_data: 导出数据
            
        Raises:
            ValueError: 如果数据格式无效
        """
        if not isinstance(export_data, dict):
            raise ValueError("Export data must be a dictionary")
        
        if "agent" not in export_data:
            raise ValueError("Missing 'agent' field in export data")
        
        agent = export_data["agent"]
        if not isinstance(agent, dict):
            raise ValueError("'agent' field must be a dictionary")
        
        # 检查必要的字段
        if "agent_id" not in agent:
            logger.warning("Missing 'agent_id' in agent configuration")
        
        if "agent_name" not in agent:
            logger.warning("Missing 'agent_name' in agent configuration")
    
    async def validate_export_data(
        self,
        export_data: Dict[str, Any],
        model_overrides: Optional[Dict[str, ModelOverride]] = None
    ) -> ValidationResult:
        """
        验证导出数据
        
        Args:
            export_data: 导出数据
            model_overrides: 模型覆盖配置
            
        Returns:
            验证结果
        """
        errors = []
        checks = {}
        
        # 1. 验证基本结构
        try:
            LowCodeAgentLoader._validate_export_data(export_data)
            checks["basic_structure"] = "passed"
        except ValueError as e:
            errors.append(ValidationError(
                field="export_data",
                message=str(e),
                severity="error"
            ))
            checks["basic_structure"] = "failed"
        
        # 2. 验证agent配置
        agent_config = export_data.get("agent", {})
        
        # 验证模型配置
        is_valid, model_errors = self.model_resolver.validate_model_config(agent_config)
        if is_valid:
            checks["model_config"] = "passed"
        else:
            checks["model_config"] = "failed"
            for error in model_errors:
                errors.append(ValidationError(
                    field="agent.model",
                    message=error,
                    severity="error"
                ))
        
        # 3. 验证依赖项
        dependencies = export_data.get("dependencies", {})
        is_valid, dep_errors = self.dep_processor.validate_dependencies(dependencies)
        if is_valid:
            checks["dependencies"] = "passed"
        else:
            checks["dependencies"] = "failed"
            for error in dep_errors:
                errors.append(ValidationError(
                    field="dependencies",
                    message=error,
                    severity="warning"
                ))
        
        # 4. 验证提示词模板
        prompt_template = agent_config.get("prompt_template", [])
        if prompt_template:
            checks["prompt_template"] = "passed"
        else:
            checks["prompt_template"] = "warning"
            errors.append(ValidationError(
                field="agent.prompt_template",
                message="Prompt template is empty",
                severity="warning"
            ))
        
        return ValidationResult(
            valid=len([e for e in errors if e.severity == "error"]) == 0,
            checks=checks,
            errors=errors
        )
