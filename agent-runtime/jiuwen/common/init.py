#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
A module for project initialization.
It is used to register and load prompt templates, plugins, and environment variables.
"""

import importlib.util
import inspect
import json
import os
import sys
from json import JSONDecodeError
from os import listdir
from pathlib import Path
from typing import Optional, List, Callable

import yaml
from jiuwen.common.config import config
from jiuwen.common.configs.env_constants import (
    DATASOURCE_GAUSSDB_PASSWORD_KEY,
    RAILS_CUSTOM_RAILS_PATH_KEY,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.extension.wrapper.plugin_base import PluginBase
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.log.base import logger
from jiuwen.common.security.util.fileutil import validate_path_traversal
from jiuwen.common.store.gauss import DBUtil
from jiuwen.orchestration.flow.agent_strategy_registry import AgentStrategyRegistry
from jiuwen.orchestration.flow.component_class_pool import component_class_pool
from jiuwen.planner.rails.common.utils import (
    import_all_modules_user_directory,
    import_all_modules_from_default_directory,
)
from jiuwen.prompt import TemplateManager, Template

YAML_FILE_NAME = "prompts.yaml"
# 定义顶级配置项白名单
TOP_LEVEL_WHITELIST = {
    "datasource",
    "llm_service_url",
    "encrypt_n",
    "prompt",
    "plugin",
    "executor",
    "model_cfg",
    "default_models",
    "security_sandbox",
    "workflow",
    "execution",
    "insight",
    "sts",
    "cloud_map",
    "service",
    "examples",
    "store",
    "embedding_base_url",
    "embedding_api",
}


class JiuWen:
    """
    项目初始化相关的类，提供初始化方法用于注册提示模板、插件并加载用户定义的环境变量信息。
    """

    @staticmethod
    def init(
        prompt_dir: Optional[str] = None,
        plugin_dir: Optional[str] = None,
        model_resolver: Optional[Callable] = None,
        cfg_file: Optional[str] = ...,
    ) -> None:
        """
        初始化方法，注册指定目录下的所有提示模板和插件，并加载用户定义的环境变量信息。

        Args:
            prompt_dir (Optional[str]): 提示模板的文件夹目录，用于注册提示模板。
            plugin_dir (Optional[str]): 插件的文件夹目录，用于注册插件。
            model_resolver (Optional[Callable]): 第三方模型配置的回调函数。
            cfg_file (Optional[str]): 配置文件路径，用于加载用户定义的环境变量信息。

        Returns:
            None

        Raises:
            JiuWenException: 如果配置文件不是合法的YAML文件，将抛出此异常。
        """
        # Try to load yaml file of user configurations to environ.
        init_cfg(cfg_file=cfg_file)
        init_db_connections()
        # Loading prompt and plugin.
        # if no path specific, try to use the path defined in config.yaml
        init_prompt_and_plugin(prompt_dir=prompt_dir, plugin_dir=plugin_dir)
        init_rails()
        init_agent_strategies()
        ModelFactory().init_resolver(model_resolver)

    @staticmethod
    def server_init(
        prompt_files: List[str], plugin_files: List[str], userid: str = None
    ) -> None:
        """init function for server api"""
        init_db_connections()
        server_init_plugins(plugin_files=plugin_files, userid=userid)
        server_init_prompts(prompt_files=prompt_files, userid=userid)


def _config_to_env(yaml_cfg, prefix=""):
    for key, value in yaml_cfg.items():
        if value is None:
            continue
        # 检查白名单：如果是顶级配置且不在白名单中，则跳过
        if prefix == "" and key not in TOP_LEVEL_WHITELIST:
            continue
        if isinstance(value, dict):
            _config_to_env(value, prefix + key.upper() + "_")
        elif isinstance(value, str):
            os.environ[prefix + key.upper()] = value
        else:
            os.environ[prefix + key.upper()] = json.dumps(value)


def _env_to_config(yaml_cfg, prefix=""):
    for key, value in yaml_cfg.items():
        if isinstance(value, dict):
            _env_to_config(value, prefix + key.upper() + "_")
        else:
            env_var_name = prefix + key.upper()
            if env_var_name and os.environ.get(env_var_name):
                env_var_value = os.environ.get(env_var_name)
                try:
                    yaml_cfg[key] = json.loads(env_var_value)
                except JSONDecodeError:
                    yaml_cfg[key] = env_var_value


def init_agent_strategies():
    """加载策略"""
    registry = AgentStrategyRegistry()
    registry.initialize(
        builtin_strategy_path="jiuwen.orchestration.flow.components.flow_agent.strategies",
    )


def init_rails():
    """加载预置护栏动作"""
    custom_rails_config_dir_str = os.environ.get(
        RAILS_CUSTOM_RAILS_PATH_KEY, config.get("rails", {}).get("custom_rails_path")
    )
    if custom_rails_config_dir_str:
        validate_path_traversal(custom_rails_config_dir_str)
        import_all_modules_user_directory(custom_rails_config_dir_str)
    import_all_modules_from_default_directory()


def init_cfg(cfg_file: str = ...) -> None:
    """
    加载用户定义的环境变量信息。

    Args:
        cfg_file: 包含配置的 YAML 文件的文件路径。
            传递 `None` 以跳过加载。
    """
    if cfg_file is None:
        logger.info("User skip loading yaml configuration file by cfg_file=None")
        return
    if cfg_file is ...:
        # Default init mode.
        # Get default application.yaml from processing working directory.
        cfg_file = os.path.join("./", "application.yaml")
        if not os.path.exists(cfg_file):
            logger.warning(
                "Try to load config by using default path but the default file"
                " 'application.yaml' cannot be found in working directory "
                f"'{os.getcwd()}'. Skip loading configuration."
            )
            return
        logger.info(
            "Loading config from default 'application.yaml'"
            f" in working directory '{os.getcwd()}'."
        )
    else:
        try:
            if not os.path.isfile(cfg_file):
                from jiuwen.common.exception import FileNotFoundException

                raise FileNotFoundException(
                    f"Specified configuration file was not found or is not a file: {cfg_file}"
                )
            logger.info("Loading config from the manually specified.")
        except TypeError as e:
            logger.error(f"[TypeError]: {e}")
            raise e

    # loading from specified yaml file.
    with open(cfg_file, "r", encoding="utf-8") as file:
        try:
            cfg_data = yaml.safe_load(file)
        except Exception as e:
            msg = (
                "Configuration loader terminated.It may caused by"
                f"the config file is not a legal yaml file. Detail: [{type(e).__name__}]{e}"
            )
            logger.error(msg)
            from jiuwen.common.exception import JiuWenException

            raise JiuWenException(msg) from e
        _env_to_config(cfg_data)
        _config_to_env(cfg_data)


def init_db_connections() -> None:
    """
    初始化数据库连接。

    此函数用于初始化数据库连接，通过检查环境变量中是否存在指定的数据库密码键来判断是否成功初始化。
    如果环境变量中存在DATASOURCE_GAUSSDB_PASSWORD_KEY，则调用DBUtil.init()方法进行数据库工具的初始化。
    """
    if os.environ.get(DATASOURCE_GAUSSDB_PASSWORD_KEY):
        DBUtil.init()


def init_prompt_and_plugin(prompt_dir: str = None, plugin_dir: str = None) -> None:
    """
    Register all prompt templates under prompt_dir and all plugins under plugin_dir.

    Args:
        prompt_dir: folder directory for registering prompt templates.
        plugin_dir: folder directory for registering plugins.

    Returns:
        None
    """
    init_prompt(prompt_dir)
    init_plugin(plugin_dir)


def get_plugins_from_dir(dir_path: str) -> list:
    """
    Get all plugin instances from dir_path,
        first, read .py file or .yaml file from dir_path
        second, if .py file, this function will recognize the FunctionPlugin Class and initialize them,
        if .yaml file, this function will use from_yaml() to get a list of RestFulAPIPlugin
        third, return the list of plugins(including RestFulAPIPlugin and FunctionPlugin)
    """
    plugins = []
    dir_path = os.path.abspath(os.path.realpath(dir_path))
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if filename.endswith(".py") and os.path.isfile(file_path):
            module_name = os.path.splitext(filename)[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == "jiuwen.plugin.decorator.plugin":
                    instance = obj()
                    plugins.append(instance)
        elif (
            filename.endswith(".yaml") or filename.endswith(".yml")
        ) and os.path.isfile(file_path):
            from jiuwen.plugin import from_yaml

            restful_api_plugins = from_yaml(file_path)
            plugins.extend(restful_api_plugins)

    return plugins


def init_plugin(plugin_dir: str = None) -> None:
    """
    Register plugins,
        first, get the plugin_dir, if plugin_dir is not existed, no plugin will be registered.
        second, get all plugins(including RestFulAPIPlugin and FunctionPlugin) need to be registered by
        get_plugins_from_dir().
        third, use the PluginManager to register all plugins.
    """
    # If plugin_dir is provided by the user, verify its existence
    # Otherwise, use user-provided plugin_dir or get the default one from config.yaml
    if plugin_dir is not None:
        if not isdir_strict(plugin_dir):
            from jiuwen.common.exception import FileNotFoundException

            raise FileNotFoundException(
                "The specified plugin directory was not found or is not a directory"
            )
    else:
        plugin_dir = config.get("plugin", dict()).get("default_dir")
        if (plugin_dir is None) or not isdir_strict(plugin_dir):
            logger.warning(
                "User does not specific a plugin directory,"
                " and the default directory is not found."
                " Skip init the PluginManager."
            )
            return
        logger.info(
            "User does not specific a plugin directory,"
            " and use the default directory"
            " to init the PluginManager."
        )

    plugins = get_plugins_from_dir(plugin_dir)
    from jiuwen.plugin import PluginManager

    plugin_manager = PluginManager()
    result = plugin_manager.register(plugins, force=True)
    from jiuwen.plugin.common.exception import CommonMessage

    if result.get("message") == CommonMessage.SuccessMsg:
        for plugin in plugins:
            logger.info(
                f"Add plugin to PluginManager:{plugin.name}",
                simple_log="Add plugin to PluginManager",
            )
    else:
        logger.error(f"Auto register plugins failed: {result.get('message')}")


def server_init_plugins(plugin_files: list, userid) -> None:
    """
    init plugins for server api.

    Args:
        plugin_files(List[Tuple]): plugin file contents.
        userid(str): for future usage.

    Returns: None

    """
    plugins = []
    from jiuwen.plugin import from_yaml

    for _, plugin_file in plugin_files:
        restful_api_plugins = from_yaml(plugin_file)
        plugins.extend(restful_api_plugins)
    from jiuwen.plugin import PluginManager

    plugin_manager = PluginManager()
    result = plugin_manager.register(plugins, force=True)
    from jiuwen.plugin.common.exception import CommonMessage

    if result.get("message") == CommonMessage.SuccessMsg:
        for plugin in plugins:
            keys = plugin.api_map.keys()
            logger.info(
                f"Succeed to register plugin {plugin.name!r} with {len(keys)} "
                f"RestfulAPIPlugin(s): {', '.join(repr(k) for k in keys)}"
            )
    else:
        logger.error(f"Auto register plugins failed: {result.get('message')}")


def init_prompt(prompt_dir: str = None) -> None:
    """
    Register prompts,
        use the TemplateManager to register all prompts.
    """
    # Use the user-provided prompt_dir or the default one
    template_manager = TemplateManager()
    # loading customer templates
    template_manager.init_prompt_templates()
    if prompt_dir:
        template_manager.register_in_bulk(prompt_dir)
    else:
        # Get the default prompt_dir from "config.yaml"
        prompt_dir = config.get("prompt", dict()).get("default_dir")
        if (prompt_dir is None) or not os.path.exists(prompt_dir):
            logger.warning(
                "User does not specific a prompt directory,"
                " and the default directory is not found."
                " Skip init the TemplateManager of prompt."
            )
            return
        logger.info(
            "User does not specific a prompt directory,"
            " and use the default directory"
            " to init the TemplateManager of prompt."
        )
        template_manager.register_in_bulk(prompt_dir)


def server_init_prompts(prompt_files: list, userid: str) -> None:
    """
    init prompts for server api.
    Args:
        prompt_files: prompts file contents
        userid: for future usage.

    Returns: None

    """
    prompt_info_list = [
        prompt_tuple
        for prompt_tuple in prompt_files
        if isinstance(prompt_tuple[1], dict)
    ]
    metadata = dict()
    length_prompt_info = len(prompt_info_list)
    if not prompt_info_list:
        logger.debug(
            "If user wants to add descriptions for prompts,"
            "please identify the description yaml file"
        )
    elif length_prompt_info > 1:
        desc_filename, _ = prompt_info_list[0]
        logger.warning(
            f"Found more than 1 prompt description yaml files, only the file named {desc_filename}.yaml will be used."
        )
    else:
        _, desc_dict = prompt_info_list[0]
        metadata = desc_dict
    templates = []
    # prompt_tuple include (name, content)
    files = [
        prompt_tuple
        for prompt_tuple in prompt_files
        if isinstance(prompt_tuple[1], str)
    ]
    for name, content in files:
        # Add the name, description, and content to the result list
        description = (
            metadata.get(name).get("description") if metadata.get(name) else ""
        )
        templates.append(Template(name=name, description=description, content=content))
    for template in templates:
        TemplateManager().register(template, force=True)
        logger.info(
            f"Add prompt to TemplateManager: {template.name}",
            simple_log="Add prompt to TemplateManager",
        )


def isdir_strict(path: str) -> bool:
    """Test if `path` is a directory (case-sensitive)"""
    abs_path = Path(path).absolute()
    if not abs_path.is_dir():
        return False
    resolved = abs_path.resolve()
    if str(abs_path) == str(resolved):
        return True
    if str(abs_path).lower() == str(resolved).lower():
        # is same regardless of case, reject (for case-sensitive)
        return False
    # using listdir to ignore symbol link
    cur = abs_path
    for parent in abs_path.parents:
        if cur.name not in listdir(parent):
            return False
        cur = parent
    return True


def load_components(extension_path: str = ""):
    """
    初始化Flow自定义组件池。

    该函数用于加载自定义组件，通过读取指定路径下的组件文件夹中的JSON文件来获取组件信息，
    并动态加载对应的Python文件中的类，将其注册到组件池中。

    单个插件加载失败不会中断整体初始化，仅记录 warning 日志并跳过该插件。

    Args:
        extension_path (str): 拓展路径，用于指定自定义组件的根目录。如果未提供，基于代码文件位置自动推导。

    Returns:
        None
    """
    if not extension_path:
        extension_path = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    custom_components_path = os.path.join(extension_path, "extensions", "components")
    if not os.path.isdir(custom_components_path):
        logger.info(
            f"Custom components directory not found: {custom_components_path}, skipping"
        )
        return
    for folder_name in os.listdir(custom_components_path):
        if ".." in folder_name:
            logger.warning(f"Skip suspicious folder name: {folder_name}")
            continue
        folder_path = os.path.join(custom_components_path, folder_name)
        if not os.path.isdir(folder_path):
            continue
        try:
            _load_single_component(extension_path, folder_path)
        except Exception as e:
            logger.warning(
                f"Failed to load custom component from {folder_path}: {e}"
            )


def _load_single_component(extension_path: str, folder_path: str):
    """加载单个自定义插件组件。

    Args:
        extension_path: 拓展根路径，用于拼接 Python 文件绝对路径。
        folder_path: 插件文件夹路径。

    Raises:
        JiuWenBaseException: 加载失败时抛出，由调用方捕获并记录日志。
    """
    json_file = os.path.join(folder_path, "component.json")
    if not os.path.isfile(json_file):
        raise JiuWenBaseException(
            error_code=StatusCode.COMPONENT_POOL_INIT_ERROR.code,
            message=StatusCode.COMPONENT_POOL_INIT_ERROR.errmsg.format(
                reason=f"Missing component.json in folder: {folder_path}"
            ),
        )
    with open(json_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    type_key = json_data.get("type")
    class_name = json_data.get("classInfo", {}).get("className")
    file_path_str = json_data.get("classInfo", {}).get("filePath")
    if file_path_str and ".." in file_path_str:
        raise JiuWenBaseException(
            error_code=StatusCode.COMPONENT_POOL_INIT_ERROR.code,
            message=StatusCode.COMPONENT_POOL_INIT_ERROR.errmsg.format(
                reason=f"Path traversal detected in filePath: {file_path_str}"
            ),
        )
    if file_path_str and os.path.isabs(file_path_str):
        raise JiuWenBaseException(
            error_code=StatusCode.COMPONENT_POOL_INIT_ERROR.code,
            message=StatusCode.COMPONENT_POOL_INIT_ERROR.errmsg.format(
                reason=f"Absolute filePath is not allowed: {file_path_str}"
            ),
        )
    py_file = os.path.join(extension_path, file_path_str)

    if not (type_key and class_name and py_file):
        raise JiuWenBaseException(
            error_code=StatusCode.COMPONENT_POOL_INIT_ERROR.code,
            message=StatusCode.COMPONENT_POOL_INIT_ERROR.errmsg.format(
                reason=f"Invalid JSON data in {json_file}: missing type or className or file_path"
            ),
        )
    module_name = f"custom_plugin_{os.path.basename(folder_path)}_{os.path.splitext(os.path.basename(py_file))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, py_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    cls = getattr(module, class_name, None)
    if cls:
        if not issubclass(cls, PluginBase):
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_POOL_INIT_ERROR.code,
                message=StatusCode.COMPONENT_POOL_INIT_ERROR.errmsg.format(
                    reason=f"Class '{class_name}' in {py_file} does not inherit from PluginBase"
                ),
            )
        component_class_pool.register_component_class(type_key, cls)
        logger.info(f"Loaded custom component: {type_key} from {py_file}")
    else:
        raise JiuWenBaseException(
            error_code=StatusCode.COMPONENT_POOL_INIT_ERROR.code,
            message=StatusCode.COMPONENT_POOL_INIT_ERROR.errmsg.format(
                reason=f"Class '{class_name}' not found in {py_file}"
            ),
        )
