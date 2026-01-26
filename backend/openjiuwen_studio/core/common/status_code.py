#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import Enum
from openjiuwen_studio.core.common.language_thread_context import get_language

BASE_CODE = 200000


class StatusCode(Enum):
    # Agent模块 1001~1999
    AGENT_DL_FETCH_FAILED = (BASE_CODE + 1001, "获取agent描述语言失败: {msg}", "failed to fetch agent dl: {msg}")
    AGENT_TEST_FAILED = (BASE_CODE + 1002, "模型配置错误, {msg}", "model configuration error, {msg}")
    AGENT_MISSING_CONVERSATION_ID = (BASE_CODE + 1003,
                                     "缺少必填参数 conversation_id",
                                     "conversation_id not exist in inputs")
    AGENT_VALIDATION_ERROR = (BASE_CODE + 1004, "agent校验参数失败: {msg}", "validation failed: {msg}")
    AGENT_INVALID_VALUE = (BASE_CODE + 1005, "agent校验无效值: {msg}", "invalid value: {msg}")
    AGENT_MISSING_FIELD = (BASE_CODE + 1006, "agent校验缺少必要字段: {msg}", "missing required field: {msg}")
    AGENT_TIMEOUT = (BASE_CODE + 1007, "agent校验操作超时: {msg}", "operation timeout: {msg}")
    AGENT_DB_CONNECTION_ERROR = (BASE_CODE + 1008, "agent校验数据库连接错误", "database connection error")
    AGENT_INTERNAL_ERROR = (BASE_CODE + 1009, "agent校验内部服务器错误: {type}", "internal server error: {type}")
    AGENT_DATABASE_OPERATION_ERROR = (BASE_CODE + 1010,
                                      "agent校验数据库操作失败",
                                      "agent verification database operation failed")
    AGENT_NETWORK_CONNECTION_ERROR = (BASE_CODE + 1011,
                                      "agent校验网络连接错误",
                                      "agent verification network connection error")
    AGENT_PERMISSION_ERROR = (BASE_CODE + 1012,
                              "agent校验权限不足",
                              "agent verification permission denied")
    AGENT_INTERNAL_SERVER_ERROR = (BASE_CODE + 1013,
                                   "agent校验服务器内部错误: {msg}",
                                   "agent verification internal server error: {msg}")

    # Agent Import/Export 1020~1049
    AGENT_EXPORT_FAILED = (BASE_CODE + 1020, "智能体导出失败: {msg}", "agent export failed: {msg}")
    AGENT_EXPORT_AGENT_NOT_FOUND = (BASE_CODE + 1021, "导出失败，智能体不存在", "agent not found for export")
    AGENT_EXPORT_DEPENDENCY_ERROR = (BASE_CODE + 1022, "导出失败，获取依赖项错误: {msg}", "failed to collect dependencies: {msg}")
    
    AGENT_IMPORT_FAILED = (BASE_CODE + 1030, "智能体导入失败: {msg}", "agent import failed: {msg}")
    AGENT_IMPORT_FILE_FORMAT_ERROR = (BASE_CODE + 1031, "导入文件格式错误: {msg}", "invalid import file format: {msg}")
    AGENT_IMPORT_CONFIG_MISSING = (BASE_CODE + 1032, "导入包中缺少配置文件", "missing configuration file in import package")
    AGENT_IMPORT_DATA_VALIDATION_ERROR = (BASE_CODE + 1033, "导入数据校验失败: {msg}", "import data validation failed: {msg}")
    AGENT_IMPORT_DEPENDENCY_ERROR = (BASE_CODE + 1034, "导入依赖项失败: {msg}", "failed to import dependencies: {msg}")
    AGENT_IMPORT_PLUGIN_ERROR = (BASE_CODE + 1035, "导入插件失败: {msg}", "failed to import plugin: {msg}")
    AGENT_IMPORT_WORKFLOW_ERROR = (BASE_CODE + 1036, "导入工作流失败: {msg}", "failed to import workflow: {msg}")
    AGENT_IMPORT_KB_ERROR = (BASE_CODE + 1037, "导入知识库失败: {msg}", "failed to import knowledge base: {msg}")
    AGENT_IMPORT_PROMPT_ERROR = (BASE_CODE + 1038, "导入提示词模板失败: {msg}", "failed to import prompt template: {msg}")
    AGENT_IMPORT_AGENT_CREATE_ERROR = (BASE_CODE + 1039, 
                                          "创建智能体失败: {msg}", 
                                          "failed to create agent from import data: {msg}")

    # Workflow模块 2001~2999
    WORKFLOW_DL_FETCH_FAILED = (BASE_CODE + 2001, "获取工作流描述语言失败: {msg}",
                                "Failed to fetch workflow dl: {msg}")
    WORKFLOW_GRAPH_CIRCLE_ERROR = (BASE_CODE + 2002, "工作流图中存在环: {msg}",
                                   "There are circles in workflow graph: {msg}")
    WORKFLOW_GRAPH_BRANCH_REDUCE_ERROR = (BASE_CODE + 2003,
                                          "不同源的分支在同一节点汇合",

                                          "These edges have different branch ancestors and cannot be reduced")
    WORKFLOW_GRAPH_LOOP_CONTROL_NODE_REDUCE_ERROR = (BASE_CODE + 2004,
                                                     "循环控制节点:{msg}存在未汇合的非switch类型的分支祖先",
                                                     "loop control node:{msg} has none switch-like branch ancestor and cannot be reduced")
    WORKFLOW_RUNNER_ERROR = (BASE_CODE + 2005,
                             "工作流执行失败: {msg}",
                             "Failed to execute Workflow: {msg}")

    WORKFLOW_GRAPH_CONNECTIVITY_ERROR = (BASE_CODE + 2006,
                                         "工作流图/循环体中从开始节点到结束节点没有连通的路径: {msg}",
                                         "No connected path from start node to end node in workflow/loop graph: {msg}")

    WORKFLOW_NESTING_DEPTH_ERROR = (BASE_CODE + 2007,
                                         "工作流嵌套深度超过最大限制: {msg}",
                                         "Workflow nesting depth exceeds the maximum limit: {msg}")

    WORKFLOW_EXECUTION_CONFLICT_ERROR = (BASE_CODE + 2008,
                                         "该会话正在执行中，请等待完成, conversation_id: {msg}",
                                         "This session: {msg} is still running, please try again later.")

    WORKFLOW_EXECUTION_CANCEL_ERROR = (BASE_CODE + 2009,
                                         "该会话取消执行失败, conversation_id: {msg}",
                                         "This session: {msg} cannot be canceled by some error.")

    WORKFLOW_GRAPH_START_NODE_ERROR = (BASE_CODE + 2010,
                                         "工作流图中存在非开始类型的孤立起始节点",
                                         "Workflow graph contains non-start type isolated source node")

    # Component模块 3001~3999
    COMPONENT_UNSUPPORT_RUN_ERROR = (BASE_CODE + 3001, "不支持该组件单独运行",
                                     "Unsupported component type for single component run")
    # 组件执行报错
    TEXTEDITOR_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3002, "文本编辑组件执行失败: {msg}",
                                         "Texteditor component invoke error: {msg}")
    USERINPUT_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3003, "用户输入节点返回结果异常",
                                        "Invalid result get from user input component")
    CODE_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3004, "代码组件执行异常",
                                   "Code component invoke error")
    USER_OUTPUT_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3005, "输出组件执行异常: {msg}",
                                          "User output component invoke error: {msg}")
    VARIABLE_MERGE_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3006, "变量聚合组件执行异常",
                                             "Variable merge component invoke error")
    EMPTY_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3007, "空组件执行异常",
                                    "Empty component invoke error")

    # 组件转换报错
    COMPONENT_CONVERT_FAILED = (BASE_CODE + 3025, "组件转换失败: {msg}",
                                "Component conversion failed: {msg}")
    START_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3026, "开始节点转换失败: {msg}",
                                      "Start component convert failed: {msg}")
    LLM_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3027, "LLM节点转换失败: {msg}",
                                    "LLM component convert failed: {msg}")
    END_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3028, "结束节点转换失败: {msg}",
                                    "End component convert failed: {msg}")
    IF_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3029, "选择器节点转换失败: {msg}",
                                   "If component convert failed: {msg}")
    LOOP_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3030, "循环节点转换失败: {msg}",
                                     "Loop component convert failed: {msg}")
    INPUT_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3031, "输入节点转换失败: {msg}",
                                      "Input component convert failed: {msg}")
    OUTPUT_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3032, "输出节点转换失败: {msg}",
                                       "Output component convert failed: {msg}")
    QUESTION_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3033, "提问器节点转换失败: {msg}",
                                         "Question component convert failed: {msg}")
    CONTINUE_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3034, "继续节点转换失败: {msg}",
                                         "Continue component convert failed: {msg}")
    BREAK_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3035, "中断节点转换失败: {msg}",
                                      "Break component convert failed: {msg}")
    TEXTEDITOR_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3036, "文本编辑节点转换失败: {msg}",
                                           "Text editor component convert failed: {msg}")
    INTENT_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3037, "意图识别节点转换失败: {msg}",
                                       "Intent component convert failed: {msg}")
    SUBWORKFLOW_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3038, "子工作流节点转换失败: {msg}",
                                            "Sub workflow component convert failed: {msg}")
    EMPTY_START_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3039, "空开始节点转换失败: {msg}",
                                            "Empty start component convert failed: {msg}")
    EMPTY_END_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3040, "空结束节点转换失败: {msg}",
                                          "Empty end component convert failed: {msg}")
    CODE_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3041, "代码组件节点转换失败: {msg}",
                                     "Code component convert failed: {msg}")
    VARIABLE_MERGE_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3042, "变量聚合节点转换失败: {msg}",
                                               "Variable merge component convert failed: {msg}")
    SET_VARIABLE_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3043, "设置变量节点转换失败: {msg}",
                                             "Set variable component convert failed: {msg}")
    PLUGIN_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3044, "插件节点转换失败: {msg}",
                                       "Plugin component convert failed: {msg}")
    BRANCH_COMPONENT_COMPILE_FAILED = (BASE_CODE + 3045, "选择器节点 {msg} 编译失败: 没有设置分支",
                                       "The branches in component id: {msg} is empty, please check!")

    # 组件编译错误
    COMPONENT_COMPILE_ERROR = (BASE_CODE + 3050, "组件编译失败: {msg}",
                               "Component compile failed: {msg}")
    LLM_COMPONENT_COMPILE_ERROR = (BASE_CODE + 3051, "LLM组件编译失败: {msg}",
                                   "LLM component compile failed: {msg}")
    CODE_COMP_COMPILER_ERROR = (BASE_CODE + 3052, "代码组件编译失败: {msg}",
                                "Code component compiler failed: {msg}")
    INTENT_DETECTION_COMP_COMPILER_ERROR = (BASE_CODE + 3053, "意图识别组件编译失败: {msg}",
                                            "Intent detection component compiler failed: {msg}")
    QUESTIONER_COMP_COMPILER_ERROR = (BASE_CODE + 3054, "提问器组件编译失败: {msg}",
                                      "Questioner component compiler failed: {msg}")
    TEXT_EDITOR_COMP_COMPILER_ERROR = (BASE_CODE + 3055, "文本编辑器组件编译失败: {msg}",
                                       "Text editor component compiler failed: {msg}")
    USER_INPUT_COMP_COMPILER_ERROR = (BASE_CODE + 3056, "用户输入组件编译失败: {msg}",
                                      "User input component compiler failed: {msg}")
    USER_OUTPUT_COMP_COMPILER_ERROR = (BASE_CODE + 3057, "用户输出组件编译失败: {msg}",
                                       "User output component compiler failed: {msg}")
    VARIABLE_MERGE_COMP_COMPILER_ERROR = (BASE_CODE + 3058, "变量聚合组件编译失败: {msg}",
                                          "Variable merge component compiler failed: {msg}")
    BRANCH_COMPONENT_COMPILE_ERROR = (BASE_CODE + 3059, "选择器组件编译失败: {msg}",
                                      "Branch component compiler failed: {msg}")

    # 单组建执行报错
    COMPONENT_RUN_ERROR = (BASE_CODE + 3060, "组件执行失败: {msg}",
                           "Component run failed: {msg}")
    LLM_COMPONENT_RUN_ERROR = (BASE_CODE + 3061, "LLM组件执行失败: {msg}",
                               "LLM component run failed: {msg}")

    # plugin模块 4001~4999
    PLUGIN_DL_FETCH_FAILED = (BASE_CODE + 4001, "获取插件描述语言失败: {msg}",
                              "Failed to fetch plugin dl: {msg}")
    PLUGIN_COMPILE_FAILED = (BASE_CODE + 4002, "插件编译失败: {msg}",
                              "Failed to compile plugin: {msg}")
    PLUGIN_CODE_TOOL_INVOKE_ERROR = (BASE_CODE + 4003, "代码插件执行异常: {msg}",
                                   "Code tool invoke error: {msg}")
    # 通用组件配置错误
    COMPONENT_CONFIG_INVALID = (BASE_CODE + 4501, "组件配置错误: {msg}",
                                "Component config invalid: {msg}")
    LLM_COMPONENT_CONFIG_INVALID = (BASE_CODE + 4502, "LLM组件配置错误: {msg}",
                                    "LLM component config invalid: {msg}")

    @property
    def code(self):
        return self.value[0]

    @property
    def errmsg(self):
        language = get_language()
        if language == 'zh-cn' or language == 'zh':
            return self.value[1]
        else:
            return self.value[2]
