#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
""" "Module providing manager interface for plugin."""

import inspect
import json
import os
import threading
from typing import List, Union, Dict

from jiuwen.common.config import config
from jiuwen.common.configs.env_constants import (
    PLUGIN_CACHE_SIZE_KEY,
    PLUGIN_RECALL_EMB_CLASS_KEY,
    PLUGIN_RECALL_EMB_DIM_KEY,
    PLUGIN_RECALL_EMB_SERVICE_URL_KEY,
    PLUGIN_RECALL_INFER_FIELDS_KEY,
    PLUGIN_STORE_KEY,
)
from jiuwen.common.embedding.bert import TextEmbeddingService
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import safe_json_loads_raise_exception
from jiuwen.plugin.common import constant
from jiuwen.plugin.common import exception
from jiuwen.plugin.common.constant import MOCK_QUERY_EMBEDDING_RESULT
from jiuwen.plugin.common.constant import SearchPolicy
from jiuwen.plugin.common.utils.db_mapper import (
    PluginDB,
    GaussConn,
    PluginInMemory,
    FuncitonInMemory,
)
from jiuwen.plugin.common.utils.plugin_flow_db_mapper import (
    PluginFlowRefDB,
    PluginFlowGaussDB,
)
from jiuwen.plugin.models import request_model
from jiuwen.plugin.models.base_model import Field
from jiuwen.plugin.models.plugin import BasePlugin, RestFulAPIPlugin, FunctionPlugin
from jiuwen.plugin.models.request_model import RegisterItem, UpdateItem
from jiuwen.plugin.transform import Transform


class PluginManager:
    """
    plugin maneger. the register, retrieve and get function support user-defined function and restful api.

    Args:
        search_policy (SearchPolicy): search_policy, defaults to similarity search
    """

    plugin_mapper: PluginDB
    plugin_flow_ref_mapper: PluginFlowRefDB
    emb: TextEmbeddingService

    _singleton_lock = threading.Lock()
    _instance = None
    _init_flag = False
    _compare_scope = [
        m[0] for m in inspect.getmembers(RegisterItem) if isinstance(m[1], Field)
    ]
    _emb_model_class = {"TextEmbeddingService": TextEmbeddingService}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(
                cls, *args, **kwargs
            )  # 调用父类的__new__方法创建一个新的对象
        return cls._instance

    def __init__(self, search_policy: SearchPolicy = SearchPolicy.SIMILARITY):
        # PluginManager还未初始化的时候进入初始化阶段获得锁
        # 如果已经实例化好了就不需要获得锁了，所以这里才需要判断两次
        if not PluginManager._init_flag:
            with PluginManager._singleton_lock:
                if not PluginManager._init_flag:
                    data_store = os.environ.get(
                        PLUGIN_STORE_KEY, config["plugin"]["store"]
                    )
                    if data_store == "in_memory":
                        logger.warning(
                            "PLUGIN_STORE: in_memory is not supported in agent builder yet"
                        )
                    cache_size = int(
                        os.environ.get(
                            PLUGIN_CACHE_SIZE_KEY, config["plugin"]["cache_maxsize"]
                        )
                    )
                    self.search_policy: SearchPolicy = search_policy
                    self.transform = Transform()
                    self._service_init(
                        db_wrapper=PluginInMemory(maxsize=cache_size)
                        if data_store == "in_memory"
                        else GaussConn(),
                        db_plugin_flow_ref_wrapper=PluginFlowGaussDB(),
                    )
                    FuncitonInMemory().set_config(maxsize=cache_size)
                    PluginManager._init_flag = True

    @staticmethod
    def select_infer_fields(item: Union[RegisterItem, UpdateItem]):
        """select fields from plugin used for infer"""
        default_fields = config.get("plugin", {}).get("recall", {}).get("infer_fields")
        environ_infer_fields = os.environ.get(PLUGIN_RECALL_INFER_FIELDS_KEY)
        try:
            fields = (
                default_fields
                if not environ_infer_fields
                else safe_json_loads_raise_exception(environ_infer_fields)
            )
        except Exception:
            logger.error("plugin parse infer fields error.")
            fields = default_fields
        select_fields = []
        for field in fields:
            if hasattr(item, field):
                select_fields.append(getattr(item, field).strip())
        if not select_fields:
            return item.func_description
        return " ".join(select_fields).strip()

    @staticmethod
    def from_openai_function_json(json_data):
        """process json data before transform openai json to jiuwen json"""
        if isinstance(json_data, str):
            json_list = [json_data]
        elif not isinstance(json_data, list):
            logger.error("json data is not list")
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        else:
            json_list = json_data

        res = []
        try:
            json_list = [json.loads(x) for x in json_list]
        except json.decoder.JSONDecodeError as e:
            logger.error("json decoder error")
            raise e

        for item in json_list:
            trans_dict = PluginManager._trans_openai2jiuwen(item)
            if trans_dict:
                res.append(trans_dict)

        return res

    @staticmethod
    def get_all_from_base_plugin(plugin: BasePlugin):
        """
        get all Function or RestFulAPI by BasePlugin

        Args:
            plugin (BasePlugin): FunctionPlugin/RestFulApiPlugin
        Returns:
            List[Function]/List[RestFulApi]
        """
        if isinstance(plugin, FunctionPlugin):
            return plugin.function_list
        if isinstance(plugin, RestFulAPIPlugin):
            return plugin.api_list
        raise NotImplementedError("Plugin type is not supported")

    @staticmethod
    def _trans_openai2jiuwen(json_item):
        """transfer openai json to jiuwen json"""
        if "function" in json_item:
            json_item = json_item.get("function")
        param_name = "name"
        param_desc = "description"
        convert_key = {
            constant.PLUGIN_NAME: param_name,
            constant.PLUGIN_DESCRIPTION: param_desc,
        }
        res = {}
        for key in convert_key:
            value = json_item.get(convert_key.get(key), None)
            if not value:
                logger.error("json must have key")
                return {}
            res[key] = value

        res["label"] = "openai_function"
        res["plugin_dependency"] = ""

        function = {
            constant.FUNCTION_NAME: json_item.get(param_name),
            constant.FUNCTION_DESCRIPTION: json_item.get(param_desc),
        }
        params = json_item.get("parameters", None)
        if not params:
            logger.error("not have parameters")
            return {}
        required = set(params.get("required", []))
        properties = params.get("properties", {})

        args = []
        for key, item in properties.items():
            p_desc = item.get(param_desc, None)
            if not p_desc:
                logger.error("params not have description")
                return {}
            args.append(
                {
                    param_name: key,
                    param_desc: p_desc,
                    "type": item.get("type", "string"),
                    "required": key in required,
                }
            )
        function["arguments"] = args
        res["functions"] = [function]
        return res

    @staticmethod
    def _load_function_plugin(
        function_plugin: FunctionPlugin, item_type_name: str = RegisterItem.__name__
    ):
        """
        Args:
            function_plugin: FunctionPlugin
        Return:
            plugin_list: List[BaseModel]
        """
        plugin_list = []
        function_map = function_plugin.function_map
        for _, func_inst in function_map.items():
            necessary_field = PluginManager._get_necessary_filed(func_inst)
            # 因Function中属性定义与数据库中的数据定义不一致，所以需要自己写下字段映射的逻辑，映射名称不同的字段，后续统一后可以删除下列映射逻辑。
            arguments = (
                [parm.__dict__ for parm in func_inst.params] if func_inst.params else []
            )
            arguments_str = json.dumps(arguments, ensure_ascii=False)
            func_key = str(func_inst.callable_function)
            FuncitonInMemory().set(func_key, func_inst.callable_function)
            necessary_field.update(
                {
                    "func_name": func_inst.name,
                    "func_description": func_inst.description,
                    "plugin_name": func_inst.plugin_name
                    if func_inst.plugin_name
                    else function_plugin.name,
                    "plugin_description": func_inst.plugin_desc
                    if func_inst.plugin_desc
                    else function_plugin.description,
                    "plugin_dependency": function_plugin.dependency,
                    "callable_function": func_key,
                    "arguments": arguments_str,
                }
            )
            necessary_field = {
                key: value
                for key, value in necessary_field.items()
                if value or value is False
            }
            if item_type_name == RegisterItem.__name__:
                plugin_list.append(RegisterItem(**necessary_field))
            elif item_type_name == UpdateItem.__name__:
                plugin_list.append(UpdateItem(**necessary_field))
            else:
                logger.error(f"Unsupported item type : '{item_type_name}'")
                raise TypeError(f"Unsupported item type : '{item_type_name}'")
        return plugin_list

    @staticmethod
    def _get_necessary_filed(instance, item=RegisterItem):
        field_map = {
            m[0]: m[1] for m in inspect.getmembers(item) if isinstance(m[1], Field)
        }
        necessary_field = {}
        for field in field_map:
            if getattr(instance, field, "") or getattr(instance, field, "") is False:
                necessary_field[field] = getattr(instance, field)
        return necessary_field

    @staticmethod
    def _load_restfulapi_plugin(
        restfulapi_plugin: RestFulAPIPlugin, item_type_name: str = RegisterItem.__name__
    ):
        """
        Args:
            restfulapi_plugin: RestFulAPIPlugin
        Return:
            plugin_list: List[RegisterItem]
        """
        plugin_list = []
        for restful_api in restfulapi_plugin.api_list:
            necessary_field = PluginManager._get_necessary_filed(restful_api)
            arguments = (
                [parm.__dict__ for parm in restful_api.params]
                if restful_api.params
                else []
            )
            responses = (
                [parm.__dict__ for parm in restful_api.response]
                if restful_api.response
                else []
            )
            necessary_field.update(
                {
                    constant.FUNCTION_NAME: restful_api.name,
                    constant.FUNCTION_DESCRIPTION: restful_api.description,
                    constant.PLUGIN_NAME: restful_api.plugin_name
                    if restful_api.plugin_name
                    else restfulapi_plugin.name,
                    constant.PLUGIN_ARGUMENTS: json.dumps(
                        arguments, ensure_ascii=False
                    ),
                    constant.PLUGIN_RESULT: json.dumps(responses, ensure_ascii=False),
                    constant.PLUGIN_URL: restful_api.path,
                }
            )
            default_dict_val = "{}"
            necessary_field[constant.PLUGIN_DESCRIPTION] = (
                restful_api.plugin_desc
                if restful_api.plugin_desc
                else (restfulapi_plugin.description)
            )
            necessary_field[constant.PLUGIN_HEADERS] = (
                default_dict_val
                if isinstance(restful_api.headers, str)
                else (json.dumps(restful_api.headers, ensure_ascii=False))
            )
            necessary_field[constant.PLUGIN_AUTH] = (
                default_dict_val
                if isinstance(restful_api.auth, str)
                else (json.dumps(restful_api.auth, ensure_ascii=False))
            )
            necessary_field[constant.PLUGIN_DEPENDENCY] = (
                default_dict_val
                if isinstance(restful_api.plugin_dependency, str)
                else (json.dumps(restful_api.plugin_dependency, ensure_ascii=False))
            )
            necessary_field = {
                key: value
                for key, value in necessary_field.items()
                if value or value is False
            }
            if item_type_name == RegisterItem.__name__:
                plugin_list.append(RegisterItem(**necessary_field))
            elif item_type_name == UpdateItem.__name__:
                plugin_list.append(UpdateItem(**necessary_field))
            else:
                raise TypeError(f"Unsupported item type : '{item_type_name}'")
        return plugin_list

    def register(
        self,
        plugins: Union[List[BasePlugin], BasePlugin],
        force: bool = False,
        create_by: str = "",
        user_id: str = "",
        **kwargs,
    ):
        """
        register plugins.

        Args:
            user_id: plugin owner
            plugins(List[BasePlugin] or BasePlugin): BasePlugin list.
            force(bool):
                True: Force coverage
            create_by(str): plugin's owner
        """
        processed_plugin_list = self._baseplugin_to_items(plugins)
        plugins = [plugins] if isinstance(plugins, BasePlugin) else plugins
        plugin_map = {plugin.name: plugin for plugin in plugins}
        exist_plugin = []
        id_list = []
        for register_item in processed_plugin_list:
            # create_by 空值后面会被过滤掉
            db_plugin = self.plugin_mapper.get_plugin(
                plugin_name=register_item.plugin_name,
                func_name=register_item.func_name,
                create_by=create_by,
                user_id=user_id,
                **kwargs,
            )
            register_item.method = register_item.method.lower()
            plugin_dict = register_item.dict(exclude_unset=True)
            if constant.PLUGIN_RELATED_INFO in plugin_dict:
                plugin_dict[constant.PLUGIN_RELATED_INFO] = json.dumps(
                    plugin_dict[constant.PLUGIN_RELATED_INFO], ensure_ascii=False
                )
            if not db_plugin:
                plugin_dict["embedding"] = str(
                    self._generate_embedding(self.select_infer_fields(register_item))
                )
                plugin_dict.update({"create_by": create_by, "user_id": user_id})
                plugin_dict.update(kwargs)
                plugin_dict.update(
                    {
                        k: json.dumps(v)
                        for k, v in plugin_dict.items()
                        if isinstance(v, dict)
                    }
                )
                result = self.plugin_mapper.add_plugin(**plugin_dict)
                if result:
                    id_list = id_list + [item[0] for item in result[0]]
            elif self._is_plugin_exactly_same(db_plugin[0], register_item.dict()):
                continue
            else:
                if force:
                    id_list = id_list + self.update(
                        plugin_map.get(plugin_dict["plugin_name"]),
                        create_by=create_by,
                        user_id=user_id,
                        **kwargs,
                    ).get(constant.ID_LIST, [])
                else:
                    exist_plugin.append(register_item)
        if exist_plugin:
            return {
                constant.CODE: exception.ErrorCode.PLUGIN_ALREADY_EXISTS,
                constant.MESSAGE: exception.ExceptionsMessage.AlreadyExistErrorJson,
                constant.BODY: [
                    item.plugin_name + "-" + item.func_name for item in exist_plugin
                ],
                constant.ID_LIST: id_list,
            }
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: exist_plugin,
            constant.ID_LIST: id_list,
        }

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        create_by: str = "",
        offset: int = 0,
        status: int = 0,
    ):
        """
        find top_k plugin's function by search_policy

        Args:
            query (str): user query for retrieve plugin.
            top_k (int): number of retrieve plugin, defaults to 3
            create_by (str): plugin's creater
            offset (int): record offset
            status (int): 1: private 2:public

        Returns:
            List[Function or RestFulAPI], top_k plugin's function
        """
        if not isinstance(top_k, int) or not isinstance(query, str):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        if not query:
            raise exception.PluginCommonException(
                message=exception.ExceptionsMessage.QueryMissingErrorJson
            )
        request_model.FindTopKItem(query=query, top_k=top_k)
        embedding = self._generate_embedding(query)
        if not embedding:
            logger.error("query_embedding failed!")
            raise exception.PluginEmbeddingException()
        embedding_str = str(embedding)
        results = self.plugin_mapper.find_top_k_plugins(
            embedding_str=embedding_str,
            top_k=top_k,
            create_by=create_by,
            offset=offset,
            status=status,
        )
        format_results = []
        id_list = []
        for result in results:
            if result.get("callable_function", None):
                format_results.append(self.transform.dict_to_function(result))
            else:
                format_results.append(self.transform.dict_to_restfulapi(result))
            if result.get("id", None):
                id_list.append(result.get("id"))
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: format_results,
            constant.ID_LIST: id_list,
        }

    def get(
        self,
        plugin_name: str = "",
        func_name: str = "",
        create_by: str = "",
        status: int = 0,
        args: dict = None,
        user_id: str = "",
        **kwargs,
    ):
        """
        get plugins by given condistions

        Args:
            user_id: plugin owner
            plugin_name (str): plugin name
            func_name (str): plugin's function name
            create_by (str): plugin's creater
            status (int): 1:private 2:public
            args (dict):
                offset: default 0
                limit: default 10000
                order_by: default "id"

        Returns:
            Union[Function, List[Function], RestFulAPI, List[RestFulAPI]], selected plugin's function

        """
        if not isinstance(plugin_name, str) or not isinstance(func_name, str):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        results = self.plugin_mapper.get_plugin(
            plugin_name=plugin_name,
            func_name=func_name,
            create_by=create_by,
            status=status,
            args=args,
            user_id=user_id,
            **kwargs,
        )
        if not results:
            logger.warning(exception.ExceptionsMessage.NotFoundErrorJson)
            return {
                constant.CODE: exception.ErrorCode.PLUGIN_NOT_FOUND,
                constant.MESSAGE: exception.ExceptionsMessage.NotFoundErrorJson,
                constant.BODY: [],
                constant.ID_LIST: [],
            }
        plugin_get = list()
        id_list = []
        for plugin in results:
            if plugin.get("callable_function", None):
                plugin_get.append(self.transform.dict_to_function(plugin))
            else:
                plugin_get.append(self.transform.dict_to_restfulapi(plugin))
            if plugin.get("id", None):
                id_list.append(plugin.get("id"))
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: plugin_get[0] if func_name else plugin_get,
            constant.ID_LIST: id_list,
        }

    def get_plugin_count(self, **kwargs):
        """get plugin count"""
        return self.plugin_mapper.cal_record_num(**kwargs)

    def get_plugin_by_id(self, plugin_ids: Union[List[int], int]):
        """get plugin instance by plugin_id"""
        if isinstance(plugin_ids, int):
            plugin_ids = [plugin_ids]
        if not isinstance(plugin_ids, list) or not all(
            isinstance(plugin_id, int) for plugin_id in plugin_ids
        ):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        result = []
        plugin_list = self.plugin_mapper.get_plugin(id=plugin_ids)
        id_list = []
        for plugin in plugin_list:
            id_list.append(plugin.get("id"))
            if plugin.get("callable_function", None):
                result.append(self.transform.dict_to_function(plugin))
            else:
                result.append(self.transform.dict_to_restfulapi(plugin))
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: result,
            constant.ID_LIST: id_list,
        }

    def update(
        self,
        plugins: Union[List[BasePlugin], BasePlugin],
        create_by: str = "",
        status: int = 0,
        user_id: str = "",
        plugin_id: int = -1,
        **kwargs,
    ):
        """
        update plugins.

        Args:
            plugins(List[BasePlugin] or BasePlugin): BasePlugin list.
            create_by: plugin's creater
            status (int): 1: private 2:public
            user_id: plugin's userid
            plugin_id: plugin's id

        """
        update_item_list = self._baseplugin_to_items(plugins, UpdateItem.__name__)
        if not update_item_list:
            return {
                constant.CODE: exception.ErrorCode.UNEXPECTED_ERROR,
                constant.MESSAGE: exception.ExceptionsMessage.UnknownErrorJson,
                constant.BODY: [],
                constant.ID_LIST: [],
            }

        nonexistent_plugin = []
        id_list = []
        for update_item in update_item_list:
            if plugin_id == -1:
                db_plugin = self.plugin_mapper.get_plugin(
                    plugin_name=update_item.plugin_name,
                    func_name=update_item.func_name,
                    create_by=create_by,
                    status=status,
                    user_id=user_id,
                    **kwargs,
                )
                conditions = {
                    "create_by": create_by,
                    "status": status,
                    "user_id": user_id,
                }
                conditions.update(kwargs)
            else:
                db_plugin = self.plugin_mapper.get_plugin(id=plugin_id)
                conditions = {"id": plugin_id}
            if not db_plugin:
                nonexistent_plugin.append(update_item)
            elif self._is_plugin_exactly_same(db_plugin[0], update_item.dict()):
                continue
            else:
                id_list += self._process_update_item(update_item, conditions, plugin_id)
        if nonexistent_plugin:
            return {
                constant.CODE: exception.ErrorCode.PLUGIN_NOT_FOUND,
                constant.MESSAGE: exception.ExceptionsMessage.NotFoundErrorJson,
                constant.BODY: [
                    item.plugin_name + "-" + item.func_name
                    for item in nonexistent_plugin
                ],
                constant.ID_LIST: id_list,
            }
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: [],
            constant.ID_LIST: id_list,
        }

    def delete(
        self,
        plugin_name: str = "",
        func_name: str = "",
        create_by: str = "",
        plugin_id: Union[List[int], int] = 0,
        user_id: str = "",
    ):
        """
        delete plugin's funciton by name

        Args:
            plugin_name (str): plugin name
            func_name (str): plugin's function name
            create_by (str): plugin's creater
            plugin_id (Union[List[int], int]): plugin's id
            user_id (str): plugin's user id
        """
        id_list = []
        if not isinstance(plugin_name, str) or not isinstance(func_name, str):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        if not self.plugin_mapper.get_plugin(
            plugin_name=plugin_name,
            func_name=func_name,
            create_by=create_by,
            id=plugin_id,
            user_id=user_id,
        ):
            return {
                constant.CODE: exception.ErrorCode.SUCCESS,
                constant.MESSAGE: exception.ExceptionsMessage.NotFoundErrorJson,
                constant.BODY: [plugin_name + "-" + func_name],
                constant.ID_LIST: id_list,
            }
        result = self.plugin_mapper.delete_plugin(
            plugin_name=plugin_name,
            func_name=func_name,
            create_by=create_by,
            id=plugin_id,
            user_id=user_id,
        )
        if result:
            id_list = id_list + [item[0] for item in result[0]]
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: [],
            constant.ID_LIST: id_list,
        }

    def plugin_flow_ref_register(
        self, version: str, workflow_id: str, data: Dict, force: bool = False
    ):
        """
        register ref of plugin and workflow
        """
        result = self._get_plugin_info_by_id(data)
        if result.get(constant.CODE) != exception.ErrorCode.SUCCESS:
            return result
        plugin_id2info = result.get(constant.BODY, {})
        if force:
            self.plugin_flow_ref_mapper.delete_ref(
                version=version, workflow_id=workflow_id
            )
        for task_id, plugin_ids in data.items():
            for plugin_id in plugin_ids:
                plugin_info = plugin_id2info.get(plugin_id)
                conditions = {
                    constant.VERSION: version,
                    constant.WORKFLOW_ID: workflow_id,
                    constant.TASK_ID: task_id,
                    constant.REF_PLUGIN_ID: plugin_id,
                }
                db_plugin_flow_ref = self.plugin_flow_ref_mapper.get_ref(**conditions)
                register_item = {
                    constant.PLUGIN_USER_ID: plugin_info[0].get(
                        constant.PLUGIN_USER_ID, ""
                    ),
                    constant.PLUGIN_NAME: plugin_info[0].get(constant.PLUGIN_NAME, ""),
                    constant.FUNCTION_NAME: plugin_info[0].get(
                        constant.FUNCTION_NAME, ""
                    ),
                }
                register_item.update(conditions)
                if not db_plugin_flow_ref:
                    self.plugin_flow_ref_mapper.add_ref(**register_item)
                else:
                    self.plugin_flow_ref_mapper.update_ref(
                        **register_item, conditions=conditions
                    )
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: {},
        }

    def plugin_flow_ref_delete(
        self, version: str, workflow_id: str, data: Dict, force: bool = False
    ):
        """
        delete ref of plugin and workflow
        """
        if force:
            self.plugin_flow_ref_mapper.delete_ref(
                version=version, workflow_id=workflow_id
            )
            return {
                constant.CODE: exception.ErrorCode.SUCCESS,
                constant.MESSAGE: exception.CommonMessage.SuccessMsg,
                constant.BODY: [],
            }
        for key, value in data.items():
            task_id = key
            if not isinstance(value, list):
                logger.error("value is not list")
                return {
                    constant.CODE: exception.ErrorCode.PLUGIN_PARAMS_CHECK_ERROR,
                    constant.MESSAGE: exception.ValidatorErrorMsg.TypeErrorMsg,
                    constant.BODY: [],
                }
            for plugin_id in value:
                conditions = {
                    constant.VERSION: version,
                    constant.WORKFLOW_ID: workflow_id,
                    constant.TASK_ID: task_id,
                    constant.REF_PLUGIN_ID: plugin_id,
                }
                self.plugin_flow_ref_mapper.delete_ref(**conditions)
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: [],
        }

    def get_workflow_info(self, workflow_id: str, version: str):
        """
        get workflow info according to workflow id and version
        Return:
            {
                "default": [int,],
                "task1": [int]
            }
        """
        if not workflow_id or not version:
            raise exception.PluginParamException(
                message="workflow_id or version is empty"
            )
        if not isinstance(workflow_id, str) or not isinstance(version, str):
            raise exception.PluginParamException(
                message="workflow_id or version is not str"
            )
        result = self.plugin_flow_ref_mapper.get_ref(
            workflow_id=workflow_id, version=version
        )
        response = {}
        for ref_info in result:
            task_id = ref_info.get(constant.TASK_ID)
            plugin_id = ref_info.get(constant.REF_PLUGIN_ID)
            response.setdefault(task_id, []).append(plugin_id)
        return response

    def copy_workflow_ref(self, old_workflow_info: Dict, new_workflow_info: Dict):
        """copy workflow ref
        Args:
            old_workflow_info = {"workflow_id": str, "version": str}
            new_workflow_info = {"workflow_id": str, "version": str}
        Return:
            bool
        """
        workflow_id = old_workflow_info.get(constant.WORKFLOW_ID, "")
        version = old_workflow_info.get(constant.VERSION, "")
        if not workflow_id or not version:
            raise exception.PluginParamException(
                message="workflow_id or version is empty in old_workflow_info"
            )
        if not isinstance(workflow_id, str) or not isinstance(version, str):
            raise exception.PluginParamException(
                message="workflow_id or version is not str in old_workflow_info"
            )

        new_workflow_id = new_workflow_info.get(constant.WORKFLOW_ID, "")
        new_version = new_workflow_info.get(constant.VERSION, "")
        if not new_workflow_id or not new_version:
            raise exception.PluginParamException(
                message="workflow_id or version is empty in new_workflow_info"
            )
        if not isinstance(new_workflow_id, str) or not isinstance(new_version, str):
            raise exception.PluginParamException(
                message="workflow_id or version is not str in new_workflow_info"
            )

        data = self.get_workflow_info(workflow_id=workflow_id, version=version)
        response = self.plugin_flow_ref_register(new_version, new_workflow_id, data)
        if response.get(constant.CODE) != exception.ErrorCode.SUCCESS:
            return False
        return True

    def del_workflow_ref(self, workflow_info: Dict):
        """delete workflow ref
        Args:
            workflow_info = {"workflow_id": str, "version": str}
        Return:
            bool
        """
        workflow_id = workflow_info.get(constant.WORKFLOW_ID, "")
        version = workflow_info.get(constant.VERSION, "")
        if not workflow_id or not version:
            raise exception.PluginParamException(
                message="workflow_id or version is empty in workflow_info"
            )
        if not isinstance(workflow_id, str) or not isinstance(version, str):
            raise exception.PluginParamException(
                message="workflow_id or version is not str in workflow_info"
            )
        self.plugin_flow_ref_mapper.delete_ref(version=version, workflow_id=workflow_id)
        return True

    def _get_plugin_info_by_id(self, data):
        """plugin_id2plugin_info"""
        result = {}
        plugin_id2info = {}
        for key, value in data.items():
            if not isinstance(value, list):
                logger.error("plugin_workflow_info plugin_list should be list")
                return {
                    constant.CODE: exception.ErrorCode.PLUGIN_PARAMS_CHECK_ERROR,
                    constant.MESSAGE: exception.ValidatorErrorMsg.TypeErrorMsg,
                    constant.BODY: result,
                }
            for plugin_id in value:
                plugin_info = self.plugin_mapper.get_plugin(id=plugin_id)
                if not plugin_info:
                    logger.error("plugin_workflow_info plugin_id dose not exist")
                    result.setdefault(key, []).append(plugin_id)
                    continue
                plugin_id2info[plugin_id] = plugin_info
        if result:
            return {
                constant.CODE: exception.ErrorCode.PLUGIN_NOT_FOUND,
                constant.MESSAGE: exception.ExceptionsMessage.NotFoundErrorJson,
                constant.BODY: result,
            }
        return {
            constant.CODE: exception.ErrorCode.SUCCESS,
            constant.MESSAGE: exception.CommonMessage.SuccessMsg,
            constant.BODY: plugin_id2info,
        }

    def _service_init(
        self,
        db_wrapper=PluginInMemory(),
        emb_wrapper=None,
        db_plugin_flow_ref_wrapper=None,
    ):
        self.emb = emb_wrapper
        self.plugin_mapper = db_wrapper
        self.plugin_flow_ref_mapper = db_plugin_flow_ref_wrapper

    def _baseplugin_to_items(
        self, plugins, item_type_name: str = RegisterItem.__name__
    ):
        if isinstance(plugins, BasePlugin):
            plugin_list = [plugins]
        elif isinstance(plugins, list):
            plugin_list = plugins
        else:
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        processed_plugin_list = []
        for import_item in plugin_list:
            if isinstance(import_item, FunctionPlugin):
                processed_plugin_list += self._load_function_plugin(
                    import_item, item_type_name
                )
            elif isinstance(import_item, RestFulAPIPlugin):
                processed_plugin_list += self._load_restfulapi_plugin(
                    import_item, item_type_name
                )
            else:
                logger.error("the plugin type is error!")
        return processed_plugin_list

    def _is_plugin_exactly_same(self, origin_plugin: dict, target_plugin: dict):
        for key in self._compare_scope:
            if origin_plugin.get(key) != target_plugin.get(key):
                return False
        return True

    def _generate_embedding(self, query: str):
        try:
            recall_config = config.get("plugin", {}).get("recall", {})
            emb_dim = int(
                os.environ.get(
                    PLUGIN_RECALL_EMB_DIM_KEY, recall_config.get("emb_dim", 256)
                )
            )
            if not self.emb:
                dft_emb_class = recall_config.get("emb_class")
                model_class_name = os.environ.get(
                    PLUGIN_RECALL_EMB_CLASS_KEY, dft_emb_class
                )
                class_object = self._emb_model_class.get(model_class_name)
                if not class_object:
                    logger.info("plugin emb is closed")
                    return MOCK_QUERY_EMBEDDING_RESULT[:emb_dim]
                self.emb = class_object()
            if isinstance(self.emb, TextEmbeddingService):
                if not os.environ.get(
                    PLUGIN_RECALL_EMB_SERVICE_URL_KEY,
                    recall_config.get("emb_service_url"),
                ):
                    logger.error("TextEmbeddingService miss url")
                    return MOCK_QUERY_EMBEDDING_RESULT[:emb_dim]
            return self.emb.query_embedding(query)[0][:emb_dim]
        except Exception as e:
            logger.error("query_embedding failed!")
            raise exception.PluginEmbeddingException(
                message=exception.ExceptionsMessage.EmbeddingErrorJson
            ) from e

    def _process_update_item(self, update_item, conditions, plugin_id=-1):
        """process update item"""
        if update_item.method:
            update_item.method = update_item.method.lower()
        plugin_dict = update_item.dict(exclude_unset=True)
        if constant.PLUGIN_RELATED_INFO in plugin_dict:
            plugin_dict[constant.PLUGIN_RELATED_INFO] = json.dumps(
                plugin_dict[constant.PLUGIN_RELATED_INFO], ensure_ascii=False
            )
        plugin_text = self.select_infer_fields(update_item)
        if plugin_text:
            plugin_dict["embedding"] = str(self._generate_embedding(plugin_text))
        if plugin_id == -1:
            conditions.update(
                {
                    "plugin_name": plugin_dict["plugin_name"],
                    "func_name": plugin_dict["func_name"],
                }
            )
        result = self.plugin_mapper.update_plugin(**plugin_dict, conditions=conditions)
        if result:
            return [item[0] for item in result[0]]
        return []
