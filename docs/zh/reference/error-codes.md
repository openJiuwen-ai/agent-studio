# Studio 2.0 错误码目录

> Studio 2.0 错误码治理初版；已同步可观测性协议 v1.2，仅展示已通过准入规则的 definition
>
> 事实源：[`tools/observability/error-codes.yaml`](../../../tools/observability/error-codes.yaml)
>
> 本文件由 `tools/observability/scripts/generate_error_code_docs.py` 生成，禁止手工维护码值事实。

## 1. 使用说明

当前登记 846 个 definition、4 个跨服务 reference。

未登记候选不等于可以继续使用；其处置边界见[仓内基线评审记录](../../../tools/observability/reviews/error-code-baseline-v1.2.md)。`0250`、`0330` 仍为 provisional，`1210` 为 reserved。

## 2. 模块号段

| 号段 | 模块 | Steward | 状态 | 评审结论 |
| --- | --- | --- | --- | --- |
| `0200` | common | manager | frozen | Studio 通用能力 |
| `0210` | agent | manager | frozen | 单智能体 |
| `0220` | workflow | manager | frozen | 工作流 |
| `0230` | multi_agent | manager | frozen | 多智能体 |
| `0240` | component | manager | frozen | 组件、插件、MCP 与提示词 |
| `0250` | model | manager | provisional | Manager/Builder 定义和 HTTP 状态冲突未收口 |
| `0260` | config | manager | frozen | 配置管理 |
| `0270` | prompt_engineering | manager | frozen | 提示词工程 |
| `0280` | asset | manager | frozen | 资产中心 |
| `0290` | workspace | manager | frozen | 团队空间 |
| `0300` | knowledge_base | manager | frozen | 知识库 |
| `0310` | environment_manager | manager | frozen | 环境管理 |
| `0320` | license | manager | frozen | License |
| `0330` | share_resource | manager | provisional | Manager/Runtime 发生同码异义冲突 |
| `0340` | memory | manager | frozen | 记忆管理 |
| `0350` | import | manager | frozen | 导入 |
| `0360` | export | manager | frozen | 导出管理 |
| `0370` | code_agent | manager | frozen | 高代码智能体 |
| `1210` | runtime_execution | runtime | reserved | 仅预留未来 canonical 新码 |

## 3. 已登记错误定义

| 错误码 | 格式 | 含义 | 名称 | 模块 | Owner | 分类 | HTTP | 级别 | 生命周期 | i18n 根键 | 引用服务 | 兼容说明 |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| `openjiuwen.121007` | legacy_other | 事件封装失败 | `Runtime.EventHandler.EVENT_ENCAPSULATION_FAILED` | runtime_execution | runtime | system | 500 | ERROR | active | `121007` | — | Runtime 内部整数键 121007 经 ErrorContextBuilder 映射为对外值 openjiuwen.121007；i18n 根键保留 121007，SSE legacy code=121007 只作为同源兼容别名 |
| `openjiuwen.02001001` | canonical8 | 鉴权失败。 | `StudioError.POC_AUTH_FAILED` | common | manager | security | 401 | WARN | active | `openjiuwen.02001001` | — | — |
| `openjiuwen.02001002` | canonical8 | 服务内部错误。 | `StudioError.UNEXPECTED_ERROR` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001002` | — | — |
| `openjiuwen.02001003` | canonical8 | 接口参数校验异常。 | `StudioError.METHOD_ARGUMENT_NOT_VALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001003` | runtime | — |
| `openjiuwen.02001004` | canonical8 | OBS服务出错。 | `StudioError.OBS_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001004` | — | — |
| `openjiuwen.02001005` | canonical8 | css uni-search服务调用异常。 | `StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001005` | — | — |
| `openjiuwen.02001006` | canonical8 | 非法文件名。 | `StudioError.ILLEGAL_FILE_NAME` | common | manager | business | 400 | WARN | active | `openjiuwen.02001006` | — | — |
| `openjiuwen.02001007` | canonical8 | 非法文件类型。 | `StudioError.ILLEGAL_FILE_TYPE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001007` | — | — |
| `openjiuwen.02001008` | canonical8 | 上传文件总大小超过系统限制。 | `StudioError.FILE_SIZE_EXCEED_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001008` | — | — |
| `openjiuwen.02001009` | canonical8 | 工作空间ID格式无效。 | `StudioError.WORKSPACE_FORMAT_INVALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001009` | — | — |
| `openjiuwen.02001010` | canonical8 | 项目ID无效或者不匹配。 | `StudioError.PROJECT_ID_INVALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001010` | — | — |
| `openjiuwen.02001011` | canonical8 | 工作空间ID无效或者不匹配。 | `StudioError.WORKSPACE_ID_INVALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001011` | — | — |
| `openjiuwen.02001012` | canonical8 | 用户没有该空间的权限。 | `StudioError.USER_WORKSPACE_PERMISSION_INVALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001012` | — | — |
| `openjiuwen.02001013` | canonical8 | 文件大小超过系统限制。 | `StudioError.PICTURE_FILE_SIZE_EXCEED_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001013` | — | — |
| `openjiuwen.02001014` | canonical8 | obs桶容量告急。 | `StudioError.OBS_BUCKET_CAPACITY_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001014` | — | — |
| `openjiuwen.02001015` | canonical8 | 名称查询仅允许包含汉字、英文字母、数字、下划线、连字符)、\ | `StudioError.SEARCH_NAME_FORMAT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001015` | — | — |
| `openjiuwen.02001016` | canonical8 | 名称格式需要满足条件：以中文、英文字母开头，只能包含中文、英文字母、数字、下划线 _ 和连字符 -，长度在2 到 64 个字符之间。 | `StudioError.NAME_FORMAT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001016` | — | — |
| `openjiuwen.02001017` | canonical8 | 智能体API调用量超过套餐额度。 | `StudioError.AGENT_API_INVOKE_EXCEEDED_QUOTA` | common | manager | security | 403 | WARN | active | `openjiuwen.02001017` | — | — |
| `openjiuwen.02001018` | canonical8 | 语音识别超时。 | `StudioError.SIS_VOICE_DURATION_EXCEEDED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001018` | — | — |
| `openjiuwen.02001019` | canonical8 | 语音识别失败。 | `StudioError.SIS_VOICE_RECOGNITION_FAILED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001019` | — | — |
| `openjiuwen.02001020` | canonical8 | 配额超出套餐限制，请升级套餐。 | `StudioError.SKU_ATTR_LIMIT_EXCEEDED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001020` | — | — |
| `openjiuwen.02001021` | canonical8 | 套餐功能不支持，请升级套餐。 | `StudioError.SKU_ATTR_IS_NOT_ENABLE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001021` | — | — |
| `openjiuwen.02001022` | canonical8 | 文件不能为空。 | `StudioError.FILE_CANNOT_BE_EMPTY` | common | manager | security | 403 | WARN | active | `openjiuwen.02001022` | — | — |
| `openjiuwen.02001023` | canonical8 | OBS对象拷贝失败。 | `StudioError.COPY_FROM_OBS_FAIL` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001023` | — | — |
| `openjiuwen.02001024` | canonical8 | 上传文件到OBS失败。 | `StudioError.UPLOAD_FILE_TO_OBS_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001024` | — | — |
| `openjiuwen.02001025` | canonical8 | 没有修改权限。 | `StudioError.NO_PERMISSION_MODIFY` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001025` | — | — |
| `openjiuwen.02001026` | canonical8 | 非法的URL。 | `StudioError.INVALID_URL` | common | manager | business | 400 | WARN | active | `openjiuwen.02001026` | — | — |
| `openjiuwen.02001027` | canonical8 | URL被黑名单拦截。 | `StudioError.URL_BLOCKED_BLOCK_LIST` | common | manager | business | 400 | WARN | active | `openjiuwen.02001027` | — | — |
| `openjiuwen.02001028` | canonical8 | 禁止访问内网地址。 | `StudioError.ACCESS_INTER_NETWORK_FORBIDDEN` | common | manager | business | 400 | WARN | active | `openjiuwen.02001028` | — | — |
| `openjiuwen.02001029` | canonical8 | 工作流Config为空。 | `StudioError.GENERATE_PROLOGUE_FAILED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001029` | — | — |
| `openjiuwen.02001030` | canonical8 | 非法文件。 | `StudioError.ILLEGAL_FILE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001030` | — | — |
| `openjiuwen.02001031` | canonical8 | 图标名称无效。 | `StudioError.INVALID_ICON_NAME` | common | manager | business | 400 | WARN | active | `openjiuwen.02001031` | — | — |
| `openjiuwen.02001032` | canonical8 | 工具信息不正确。 | `StudioError.TOOL_INFO_INCORRECT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001032` | — | — |
| `openjiuwen.02001033` | canonical8 | TTS API服务异常。 | `StudioError.TST_API_SERVICE_EXCEPTION` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001033` | — | — |
| `openjiuwen.02001034` | canonical8 | 接口调用异常，queryDomainToken错误。 | `StudioError.INTERFACE_CALL_EXCEPTION` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001034` | — | — |
| `openjiuwen.02001035` | canonical8 | 您没有执行此操作的权限，因为您不是创建者。 | `StudioError.NO_CREATOR_PERMISSION` | common | manager | security | 403 | WARN | active | `openjiuwen.02001035` | — | — |
| `openjiuwen.02001036` | canonical8 | API删除接口错误。 | `StudioError.API_DELETE_API_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001036` | — | — |
| `openjiuwen.02001037` | canonical8 | 文件上传超出速率限制，请稍后重试。 | `StudioError.UPLOAD_FILE_EXCEED_LIMITS` | common | manager | business | 400 | WARN | active | `openjiuwen.02001037` | — | — |
| `openjiuwen.02001038` | canonical8 | 流式接口执行超时。 | `StudioError.STREAM_INTERFACE_EXECUTE_TIMEOUT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001038` | — | — |
| `openjiuwen.02001039` | canonical8 | 模型不存在或模型配置转换失败。 | `StudioError.GENERATE_PROLOGUE_FAILED_MODEL` | common | manager | business | 400 | WARN | active | `openjiuwen.02001039` | — | — |
| `openjiuwen.02001040` | canonical8 | Redisson获取bucket失败。 | `StudioError.REDISSON_GET_BUCKET_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001040` | — | — |
| `openjiuwen.02001041` | canonical8 | 获取用户token错误。 | `StudioError.IAM_GET_USERINFO_EXCEPTION` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001041` | — | — |
| `openjiuwen.02001042` | canonical8 | SQL执行失败。 | `StudioError.SQL_EXECUTE_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001042` | — | — |
| `openjiuwen.02001043` | canonical8 | 获取提供方认证元数据失败。项目：{0}，提供方：{1}。 | `StudioError.FAIL_GET_PROVIDE_AUTH_METADATA` | common | manager | business | 400 | WARN | active | `openjiuwen.02001043` | — | — |
| `openjiuwen.02001044` | canonical8 | 节点类型不支持。 | `StudioError.NODE_TYPE_NOT_SUPPORT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001044` | — | — |
| `openjiuwen.02001045` | canonical8 | 不支持的数据源类型。 | `StudioError.UNSUPPORTED_DATA_SOURCE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001045` | — | — |
| `openjiuwen.02001046` | canonical8 | 解析事件数据答案失败。 | `StudioError.FAIL_TO_PARSE_DATA` | common | manager | business | 400 | WARN | active | `openjiuwen.02001046` | — | — |
| `openjiuwen.02001047` | canonical8 | 导入agents\|workflows\|tools失败。 | `StudioError.IMPORT_AGENT_WORKFLOW_TOOL_ERROR` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001047` | — | — |
| `openjiuwen.02001048` | canonical8 | 认证类型不支持。 | `StudioError.AUTH_TYPE_UNSUPPORTED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001048` | — | — |
| `openjiuwen.02001049` | canonical8 | HTTP客户端初始化失败。 | `StudioError.HTTP_CLIENT_INIT_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001049` | — | — |
| `openjiuwen.02001050` | canonical8 | 获取请求IAM上下文失败。 | `StudioError.GET_REQUEST_IAM_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001050` | — | — |
| `openjiuwen.02001053` | canonical8 | 无法找到endpoint。 | `StudioError.ENDPOINT_CAN_NOT_FOUND` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001053` | — | — |
| `openjiuwen.02001054` | canonical8 | 由于版本冲突，无法加载JsonReadFeature和JsonWriteFeature类，将使用已弃用的JsonParser和JsonGenerator替代。 | `StudioError.JSON_PARSER_INSTEAD` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001054` | — | — |
| `openjiuwen.02001055` | canonical8 | 文件转换为Base64字符串失败。 | `StudioError.BASE_CONVERT_FAILED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001055` | — | — |
| `openjiuwen.02001056` | canonical8 | 获取图标图片失败。 | `StudioError.FAILED_ICON_IMAGE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001056` | — | — |
| `openjiuwen.02001057` | canonical8 | 当前租户下的应用数量已经超过了套餐配额。 | `StudioError.APP_COUNT_EXCEEDED_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001057` | — | — |
| `openjiuwen.02001058` | canonical8 | 导出结构化消息失败。 | `StudioError.EXPORT_STRUCTURED_MESSAGES_FAILED` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001058` | — | — |
| `openjiuwen.02001059` | canonical8 | 请刷新环境。 | `StudioError.ERROR_REFRESH_ENVIRONMENT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001059` | — | — |
| `openjiuwen.02001060` | canonical8 | 消息模板名称不合法。 | `StudioError.STRUCTURED_MESSAGES_NAME_INVALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001060` | — | — |
| `openjiuwen.02001061` | canonical8 | 导入数据应不超过200条。 | `StudioError.MESSAGE_TEMPLATE_SIZE_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001061` | — | — |
| `openjiuwen.02001062` | canonical8 | 消息模板名称重复。 | `StudioError.MESSAGE_TEMPLATE_NAME_REPETITION` | common | manager | business | 400 | WARN | active | `openjiuwen.02001062` | — | — |
| `openjiuwen.02001063` | canonical8 | 被授权空间不存在。 | `StudioError.AUTH_WORKSPACE_NOT_FOUNT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001063` | — | — |
| `openjiuwen.02001064` | canonical8 | 共享的资源类型不合法。 | `StudioError.RESOURCE_TYPE_NOT_VALID` | common | manager | business | 400 | WARN | active | `openjiuwen.02001064` | — | — |
| `openjiuwen.02001065` | canonical8 | 共享资源不存在。 | `StudioError.SHARE_RESOURCE_NOT_FOUNT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001065` | — | — |
| `openjiuwen.02001066` | canonical8 | 存在引用资源的对象不能共享。 | `StudioError.EXIST_SHARE_REFERENCE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001066` | — | — |
| `openjiuwen.02001067` | canonical8 | 当前空间不在资源共享范围内，不允许导入。 | `StudioError.CURRENT_WORKSPACE_IS_NOT_IN_SHARE_SCOPE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001067` | — | — |
| `openjiuwen.02001068` | canonical8 | 调用AgentService错误，请确认配置正确。 | `StudioError.CALL_RUNTIME_ERROR` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001068` | — | — |
| `openjiuwen.02001069` | canonical8 | Api key 缺失。 | `StudioError.POC_API_KEY_MISSING` | common | manager | security | 401 | WARN | active | `openjiuwen.02001069` | — | — |
| `openjiuwen.02001070` | canonical8 | Api key 错误或者和当前用户不匹配。 | `StudioError.POC_API_KEY_INCORRECT` | common | manager | security | 401 | WARN | active | `openjiuwen.02001070` | — | — |
| `openjiuwen.02001071` | canonical8 | 当前租户无权限执行。 | `StudioError.PROJECT_ID_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001071` | — | — |
| `openjiuwen.02001072` | canonical8 | 当日调用次数已达到上限。 | `StudioError.CALL_LIMIT_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001072` | — | — |
| `openjiuwen.02001073` | canonical8 | 获取分布式锁失败。 | `StudioError.OBTAIN_DISTRIBUTED_LOCK_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001073` | — | — |
| `openjiuwen.02001074` | canonical8 | JSON解析失败。 | `StudioError.JSON_CONVERT_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001074` | — | — |
| `openjiuwen.02001075` | canonical8 | 您的账号已被冻结。 | `StudioError.FREEZE_TENANT` | common | manager | security | 403 | WARN | active | `openjiuwen.02001075` | — | — |
| `openjiuwen.02001076` | canonical8 | {0}功能未开通。 | `StudioError.TENANT_NOT_ACTIVATED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001076` | — | — |
| `openjiuwen.02001077` | canonical8 | 消息模板仅支持异常类型。 | `StudioError.ONLY_SUPPORTED_EXCEPTION_TYPE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001077` | — | — |
| `openjiuwen.02001078` | canonical8 | 租户资源清理权限不足，期望的租户：{0}，实际租户：{1}。 | `StudioError.TENANT_DATA_CLEAN_FORBIDDEN` | common | manager | security | 403 | WARN | active | `openjiuwen.02001078` | — | — |
| `openjiuwen.02001079` | canonical8 | 消息模板未找到。 | `StudioError.MESSAGE_TEMPLATE_NOT_FOUND_OR_PERMISSION_DENIED` | common | manager | security | 403 | WARN | active | `openjiuwen.02001079` | — | — |
| `openjiuwen.02001080` | canonical8 | URL不在白名单中。 | `StudioError.URL_WHITELIST_CHECK_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001080` | — | — |
| `openjiuwen.02001081` | canonical8 | 未能获取到KMS工作秘钥。 | `StudioError.NOT_FOUND_KMS_DATA_KEY` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001081` | — | — |
| `openjiuwen.02001082` | canonical8 | 使用KMS加解密失败。 | `StudioError.KMS_CRYPTO_ERROR` | common | manager | business | 500 | ERROR | active | `openjiuwen.02001082` | — | — |
| `openjiuwen.02001083` | canonical8 | 调用过于频繁，请稍后再试。 | `StudioError.CALL_EXCEED_LIMIT` | common | manager | security | 403 | WARN | active | `openjiuwen.02001083` | — | — |
| `openjiuwen.02001084` | canonical8 | 资源读取错误。 | `StudioError.RESOURCE_READER_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001084` | — | — |
| `openjiuwen.02001085` | canonical8 | 无法将对象转换为JSON字符串。 | `StudioError.COULD_NOT_CONVERT_OBJECT_TO_JSON` | common | manager | business | 400 | WARN | active | `openjiuwen.02001085` | — | — |
| `openjiuwen.02001086` | canonical8 | 无法将JSON字符串转换为对象。 | `StudioError.COULD_NOT_CONVERT_JSON_STRING_TO_OBJECT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001086` | — | — |
| `openjiuwen.02001087` | canonical8 | 将列表转换为JSON 时出错。 | `StudioError.LIST_TO_JSON_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001087` | — | — |
| `openjiuwen.02001088` | canonical8 | 将JSON 转换为列表时出错。 | `StudioError.JSON_TO_LIST_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001088` | — | — |
| `openjiuwen.02001089` | canonical8 | 签名验证失败。 | `StudioError.VERIFY_SIGNATURE_FAILED` | common | manager | security | 403 | WARN | active | `openjiuwen.02001089` | — | — |
| `openjiuwen.02001090` | canonical8 | 您未订阅AgentBuilder云服务，无法使用该功能。 | `StudioError.SERVICE_NOT_ACTIVATE` | common | manager | business | 400 | WARN | active | `openjiuwen.02001090` | — | — |
| `openjiuwen.02001091` | canonical8 | 隐私协议验证失败。 | `StudioError.VERIFY_AGREEMENT_FAILED` | common | manager | security | 403 | WARN | active | `openjiuwen.02001091` | — | — |
| `openjiuwen.02001092` | canonical8 | 上传的文件数量超过 {0} 个限制。 | `StudioError.FILE_COUNT_EXCEED_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001092` | — | — |
| `openjiuwen.02001093` | canonical8 | 用户domainId校验失败。 | `StudioError.HOST_VALIDATION_DOMAIN_FAILED` | common | manager | security | 403 | WARN | active | `openjiuwen.02001093` | — | — |
| `openjiuwen.02001094` | canonical8 | 无效的主机域名。 | `StudioError.HOST_VALIDATION_INVALID` | common | manager | security | 403 | WARN | active | `openjiuwen.02001094` | — | — |
| `openjiuwen.02001095` | canonical8 | zip嵌套。 | `StudioError.FILE_NESTED_ZIP` | common | manager | business | 400 | WARN | active | `openjiuwen.02001095` | — | — |
| `openjiuwen.02001096` | canonical8 | zip路径深度小于等于10层。 | `StudioError.ZIP_PATH_TOO_DEEP` | common | manager | business | 400 | WARN | active | `openjiuwen.02001096` | — | — |
| `openjiuwen.02001097` | canonical8 | skill制品包异常。 | `StudioError.FILES_NUMBER_DOES_NOT_MATCH` | common | manager | business | 400 | WARN | active | `openjiuwen.02001097` | — | — |
| `openjiuwen.02001098` | canonical8 | 缺少必填字段。 | `StudioError.DESCRIPTION_FIELD_MISSING` | common | manager | business | 400 | WARN | active | `openjiuwen.02001098` | — | — |
| `openjiuwen.02001099` | canonical8 | 描述长度超过限制。 | `StudioError.DESCRIPTION_LENGTH_EXCEED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001099` | — | — |
| `openjiuwen.02001100` | canonical8 | 含有非法字符。 | `StudioError.INVALID_CHARACTER` | common | manager | business | 400 | WARN | active | `openjiuwen.02001100` | — | — |
| `openjiuwen.02001109` | canonical8 | 长度超过限制。 | `StudioError.COMPATIBILITY_LENGTH_EXCEED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001109` | — | — |
| `openjiuwen.02001110` | canonical8 | 缺少技能id。 | `StudioError.SKILL_ID_IS_EMPTY` | common | manager | business | 400 | WARN | active | `openjiuwen.02001110` | — | — |
| `openjiuwen.02001111` | canonical8 | 缺少技能包。 | `StudioError.SKILL_NOT_EXISTS` | common | manager | business | 400 | WARN | active | `openjiuwen.02001111` | — | — |
| `openjiuwen.02001112` | canonical8 | 技能版本异常。 | `StudioError.SKILL_VERSION_IS_INCORRECT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001112` | — | — |
| `openjiuwen.02001113` | canonical8 | obs路径异常。 | `StudioError.OBS_URL_NOT_EXISTS` | common | manager | business | 400 | WARN | active | `openjiuwen.02001113` | — | — |
| `openjiuwen.02001114` | canonical8 | 预签名obs路径异常。 | `StudioError.GET_OBS_TEMPORARY_URL_NOT_EXIST` | common | manager | business | 400 | WARN | active | `openjiuwen.02001114` | — | — |
| `openjiuwen.02001115` | canonical8 | SKILL.md文件异常。 | `StudioError.SKILL_MD_IS_MISSING` | common | manager | business | 400 | WARN | active | `openjiuwen.02001115` | — | — |
| `openjiuwen.02001116` | canonical8 | IO异常。 | `StudioError.IO_ERROR` | common | manager | business | 400 | WARN | active | `openjiuwen.02001116` | — | — |
| `openjiuwen.02001117` | canonical8 | 技能已存在。 | `StudioError.SKILL_ALREADY_EXIST` | common | manager | business | 400 | WARN | active | `openjiuwen.02001117` | — | — |
| `openjiuwen.02001118` | canonical8 | 同步删除高码数据失败。 | `StudioError.SYNC_DELETE_CODE_AGENT_FAILED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001118` | — | — |
| `openjiuwen.02001121` | canonical8 | 文件大小超出限制。 | `StudioError.SKILL_SIZE_EXCEED_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001121` | — | — |
| `openjiuwen.02001122` | canonical8 | 文件数量超出限制。 | `StudioError.ZIP_FILE_COUNT_EXCEED_LIMIT` | common | manager | business | 400 | WARN | active | `openjiuwen.02001122` | — | — |
| `openjiuwen.02001123` | canonical8 | 文件名包含不安全路径。 | `StudioError.INSECURE_PATH` | common | manager | business | 400 | WARN | active | `openjiuwen.02001123` | — | — |
| `openjiuwen.02001124` | canonical8 | 文件包含符号链接。 | `StudioError.UNSAFE_PATH` | common | manager | business | 400 | WARN | active | `openjiuwen.02001124` | — | — |
| `openjiuwen.02001125` | canonical8 | 元数据字段无效。 | `StudioError.SKILL_MD_INVALID_FIELD` | common | manager | business | 400 | WARN | active | `openjiuwen.02001125` | — | — |
| `openjiuwen.02001126` | canonical8 | 名称字段缺失。 | `StudioError.NAME_FIELD_MISSING` | common | manager | business | 400 | WARN | active | `openjiuwen.02001126` | — | — |
| `openjiuwen.02001127` | canonical8 | 名称格式不符合规范 | `StudioError.NAME_FORMAT_MISMATCH` | common | manager | business | 400 | WARN | active | `openjiuwen.02001127` | — | — |
| `openjiuwen.02001128` | canonical8 | 上传大小超出最大限制。 | `StudioError.MAX_UPLOAD_SIZE_EXCEEDED` | common | manager | business | 400 | WARN | active | `openjiuwen.02001128` | — | — |
| `openjiuwen.02101001` | canonical8 | 单智能体应用名称已存在。 | `StudioError.AGENT_NAME_INVALID` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101001` | — | — |
| `openjiuwen.02101002` | canonical8 | 触发器不存在。 | `StudioError.AGENT_TRIGGER_EXIST` | agent | manager | business | 404 | WARN | active | `openjiuwen.02101002` | — | — |
| `openjiuwen.02101003` | canonical8 | 触发器类型错误。 | `StudioError.AGENT_TRIGGER_TYPE_INCORRECT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101003` | — | — |
| `openjiuwen.02101004` | canonical8 | 触发器数量已达到上限。 | `StudioError.AGENT_TRIGGER_SIZE_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101004` | — | — |
| `openjiuwen.02101005` | canonical8 | 单智能体应用图标不存在。 | `StudioError.AGENT_ICON_EXIST` | agent | manager | business | 404 | WARN | active | `openjiuwen.02101005` | — | — |
| `openjiuwen.02101006` | canonical8 | 单智能体应用图标超过了上传最大尺寸。 | `StudioError.AGENT_ICON_SIZE_EXCEEDS_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101006` | — | — |
| `openjiuwen.02101007` | canonical8 | 智能体应用不存在。 | `StudioError.AGENT_NOT_EXIST` | agent | manager | business | 404 | WARN | active | `openjiuwen.02101007` | — | — |
| `openjiuwen.02101008` | canonical8 | 单智能体应用导入失败。 | `StudioError.AGENT_IMPORT_FILE` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101008` | — | — |
| `openjiuwen.02101009` | canonical8 | 单智能体应用导出失败。 | `StudioError.AGENT_EXPORT_FILE` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101009` | — | — |
| `openjiuwen.02101010` | canonical8 | 单智能体应用绑定的工具数量超过上限。 | `StudioError.TOOL_NUMBER_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101010` | — | — |
| `openjiuwen.02101011` | canonical8 | 单智能体应用绑定的知识库数量超过上限。 | `StudioError.KNOWLEDGE_REPO_NUMBER_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101011` | — | — |
| `openjiuwen.02101012` | canonical8 | 单智能体应用绑定的工作流数量超过上限。 | `StudioError.WORKFLOW_NUMBER_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101012` | — | — |
| `openjiuwen.02101013` | canonical8 | 单智能体应用发布通道类型错误。 | `StudioError.AGENT_CHANNEL_TYPE_INCORRECT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101013` | — | — |
| `openjiuwen.02101014` | canonical8 | 不支持单智能体应用类型。 | `StudioError.UNSUPPORTED_AGENT_TYPE` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101014` | — | — |
| `openjiuwen.02101015` | canonical8 | 智能体应用已被更新。 | `StudioError.AGENT_HAS_BEEN_UPDATED` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101015` | — | — |
| `openjiuwen.02101016` | canonical8 | 智能体应用执行权限不足。 | `StudioError.INSUFFICIENT_AGENT_RUN_PRIVILEGES` | agent | manager | security | 403 | WARN | active | `openjiuwen.02101016` | runtime | — |
| `openjiuwen.02101017` | canonical8 | 单智能体应用名称为null。 | `StudioError.CHECK_AGENT_INFO_FAILED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101017` | — | — |
| `openjiuwen.02101018` | canonical8 | 单智能体应用信息发送失败。 | `StudioError.AGENT_INFO_SEND_FAILED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101018` | — | — |
| `openjiuwen.02101019` | canonical8 | 单智能体应用运行超时。 | `StudioError.AGENT_RUN_TIMEOUT` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101019` | — | — |
| `openjiuwen.02101020` | canonical8 | 单智能体应用发布版本数量超过上限。 | `StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101020` | — | — |
| `openjiuwen.02101021` | canonical8 | 智能体应用版本不存在。 | `StudioError.AGENT_VERSION_NOT_EXIST` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101021` | — | — |
| `openjiuwen.02101022` | canonical8 | 单智能体应用发布通道不存在。 | `StudioError.AGENT_PUBLISH_CHANNEL_NOT_EXIST` | agent | manager | business | 404 | WARN | active | `openjiuwen.02101022` | — | — |
| `openjiuwen.02101023` | canonical8 | 检查单智能体应用信息失败。 | `StudioError.CHECK_APP_INFO_FAILED` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101023` | — | — |
| `openjiuwen.02101024` | canonical8 | 单智能体应用绑定的MCP数量超过上限。 | `StudioError.MCP_NUMBER_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101024` | — | — |
| `openjiuwen.02101025` | canonical8 | 调度器删除作业失败。 | `StudioError.SCHEDULER_EXCEPTION` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101025` | — | — |
| `openjiuwen.02101026` | canonical8 | 执行任务失败。 | `StudioError.SCHEDULER_EXCEPTION_RUN_JOB` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101026` | — | — |
| `openjiuwen.02101027` | canonical8 | 调用获取代理令牌API时发生异常。 | `StudioError.CALL_GET_AGENCY_TOKEN_API_EXCEPTION` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101027` | — | — |
| `openjiuwen.02101028` | canonical8 | 转换UUID失败。 | `StudioError.ID_TO_UUID_FAIL` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101028` | — | — |
| `openjiuwen.02101029` | canonical8 | 不支持非流式调用。 | `StudioError.NO_SUPPORT_NON_STREAMING_CALL` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101029` | — | — |
| `openjiuwen.02101030` | canonical8 | 上传文件数量超出限制。 | `StudioError.AGENT_UPLOAD_FILE_NUM` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101030` | — | — |
| `openjiuwen.02101031` | canonical8 | Agent不存在或无权限。 | `StudioError.AGENT_NOT_EXIST_OR_NO_PERMISSION` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101031` | — | — |
| `openjiuwen.02101032` | canonical8 | 当前Agent版本不存在。 | `StudioError.AGENT_OR_VERSION_NOT_EXIST` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101032` | — | — |
| `openjiuwen.02101033` | canonical8 | 单次会话超过上传文件个数。 | `StudioError.AGENT_CONVERSATION_FILE_NUM` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101033` | — | — |
| `openjiuwen.02101034` | canonical8 | Agent中变量名称重复。 | `StudioError.AGENT_VARIABLE_DUPLICATE` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101034` | — | — |
| `openjiuwen.02101035` | canonical8 | Agent解析全局变量失败。 | `StudioError.AGENT_PARSE_VARIABLE_FAILED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101035` | — | — |
| `openjiuwen.02101036` | canonical8 | 获取会话变量失败。 | `StudioError.AGENT_GET_VARIABLE_FAILED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101036` | — | — |
| `openjiuwen.02101037` | canonical8 | 版本名称已经存在。 | `StudioError.VERSION_NAME_ALREADY_EXISTED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101037` | — | — |
| `openjiuwen.02101038` | canonical8 | 发布百宝箱失败。 | `StudioError.OP_ACCOUNT_ONLY_ALLOWED_TO_PUBLISH` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101038` | — | — |
| `openjiuwen.02101039` | canonical8 | 当前发布渠道类型不支持删除。 | `StudioError.AGENT_CHANNEL_NOT_SUPPORT_DELETE` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101039` | — | — |
| `openjiuwen.02101040` | canonical8 | Excel文件行数超过限制。 | `StudioError.EXCEL_ROW_COUNT_EXCEEDED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101040` | — | — |
| `openjiuwen.02101041` | canonical8 | Excel文件列数超过限制。 | `StudioError.EXCEL_COLUMN_COUNT_EXCEEDED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101041` | — | — |
| `openjiuwen.02101042` | canonical8 | Excel文件格式无效。 | `StudioError.EXCEL_FILE_FORMAT_INVALID` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101042` | — | — |
| `openjiuwen.02101043` | canonical8 | 应用发布通道不存在。 | `StudioError.APPLICATION_PUBLISH_CHANNEL_NOT_EXIST` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101043` | — | — |
| `openjiuwen.02101044` | canonical8 | 缺少输入参数。 | `StudioError.MISSING_REQUIRED_PARAMETERS` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101044` | — | — |
| `openjiuwen.02101045` | canonical8 | 智能生成图标失败。 | `StudioError.GENERATE_ICON_FAILED` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101045` | — | — |
| `openjiuwen.02101046` | canonical8 | 指南数量超过最大限制。 | `StudioError.GUIDELINE_NUM_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101046` | — | — |
| `openjiuwen.02101047` | canonical8 | 不支持非流式调用。 | `StudioError.NOT_SUPPORT_UN_STREAM_INVOKE` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101047` | — | — |
| `openjiuwen.02101048` | canonical8 | 不支持的关联资源类型。 | `StudioError.UNSUPPORTED_RESOURCE_TYPE` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101048` | — | — |
| `openjiuwen.02101049` | canonical8 | Skill数量超过最大限制。 | `StudioError.SKILL_NUM_EXCEED_LIMIT` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101049` | — | — |
| `openjiuwen.02101050` | canonical8 | Skill不存在。 | `StudioError.SKILL_NOT_EXIST` | agent | manager | business | 404 | WARN | active | `openjiuwen.02101050` | — | — |
| `openjiuwen.02101051` | canonical8 | Skill版本无效。 | `StudioError.SKILL_VERSION_INVALID` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101051` | — | — |
| `openjiuwen.02101052` | canonical8 | Skill或版本不存在或不匹配。 | `StudioError.SKILL_ID_OR_VERSION_NOT_MATCH` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101052` | — | — |
| `openjiuwen.02101053` | canonical8 | 缺少输入参数。 | `StudioError.MISSING_REQUIRED_INSTRUCTIONS` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101053` | — | — |
| `openjiuwen.02101054` | canonical8 | 复制智能体失败。 | `StudioError.AGENT_COPY_FAIL` | agent | manager | business | 500 | ERROR | active | `openjiuwen.02101054` | — | — |
| `openjiuwen.02101056` | canonical8 | {{latest}}变量对应的资源不存在。 | `StudioError.LATEST_REPLACE_NOT_EXISTS` | agent | manager | business | 400 | WARN | active | `openjiuwen.02101056` | — | — |
| `openjiuwen.02201001` | canonical8 | 工作流导入失败。 | `StudioError.WORKFLOW_IMPORT_FILE` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201001` | — | — |
| `openjiuwen.02201002` | canonical8 | 工作流组件ID不存在。 | `StudioError.WORKFLOW_NODE_ID_NULL` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201002` | — | — |
| `openjiuwen.02201003` | canonical8 | 工作流节点执行异常。 | `StudioError.WORKFLOW_NODE_EXECUTE_FAILED` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201003` | — | — |
| `openjiuwen.02201004` | canonical8 | 工作流或该工作流版本号不存在。 | `StudioError.WORKFLOW_NOT_EXIST` | workflow | manager | business | 404 | WARN | active | `openjiuwen.02201004` | — | — |
| `openjiuwen.02201005` | canonical8 | 工作流信息校验失败。 | `StudioError.CHECK_WORKFLOW_INFO_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201005` | — | — |
| `openjiuwen.02201006` | canonical8 | 工作流中文名称超出字符限制。 | `StudioError.WORKFLOW_NAME_EXCEEDS_LIMIT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201006` | — | — |
| `openjiuwen.02201007` | canonical8 | 工作流图标名为空。 | `StudioError.WORKFLOW_ICON_EMPTY` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201007` | — | — |
| `openjiuwen.02201008` | canonical8 | 工作流导出失败。 | `StudioError.WORKFLOW_EXPORT_FILE` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201008` | — | — |
| `openjiuwen.02201009` | canonical8 | 当前工作流不是最新。 | `StudioError.WORKFLOW_VERSION_NOT_MATCH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201009` | — | — |
| `openjiuwen.02201010` | canonical8 | 工作流版本无权限删除。 | `StudioError.NO_PERMISSION_DELETE_WORKFLOW_VERSION` | workflow | manager | security | 403 | WARN | active | `openjiuwen.02201010` | — | — |
| `openjiuwen.02201011` | canonical8 | 工作流发布通道类型错误。 | `StudioError.WORKFLOW_CHANNEL_TYPE_INCORRECT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201011` | — | — |
| `openjiuwen.02201012` | canonical8 | 工作流嵌套超过最大层级。 | `StudioError.WORKFLOW_NESTED_CHECK` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201012` | — | — |
| `openjiuwen.02201013` | canonical8 | 导出依赖的工作流版本不存在。 | `StudioError.DEPEND_WORKFLOW_VERSION` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201013` | — | — |
| `openjiuwen.02201014` | canonical8 | 工作流中文名称重复。 | `StudioError.WORKFLOW_NAME_REPEATED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201014` | — | — |
| `openjiuwen.02201015` | canonical8 | 工作流英文名称重复。 | `StudioError.WORKFLOW_EN_NAME_REPEATED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201015` | — | — |
| `openjiuwen.02201016` | canonical8 | 工作流非游离节点数量超过最大限制。 | `StudioError.WORKFLOW_NODE_EXCEED_LIMITS` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201016` | — | — |
| `openjiuwen.02201017` | canonical8 | 工作流校验接口异常。 | `StudioError.WORKFLOW_VALIDATE_VERSION_ERROR` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201017` | — | — |
| `openjiuwen.02201018` | canonical8 | 工作流内容审核错误。 | `StudioError.CONTENT_REVIEW_ERROR` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201018` | — | — |
| `openjiuwen.02201019` | canonical8 | 控制器绑定工作流节点不合法。 | `StudioError.CONTROLLER_INVALID_WORKFLOW` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201019` | — | — |
| `openjiuwen.02201020` | canonical8 | 工作流执行权限不足。 | `StudioError.INSUFFICIENT_WORKFLOW_RUN_PRIVILEGES` | workflow | manager | security | 403 | WARN | active | `openjiuwen.02201020` | runtime | — |
| `openjiuwen.02201021` | canonical8 | 不是最新的工作流。 | `StudioError.NOT_LATEST_WORKFLOW` | workflow | manager | security | 403 | WARN | active | `openjiuwen.02201021` | runtime | — |
| `openjiuwen.02201022` | canonical8 | 工作流运行超时。 | `StudioError.WORKFLOW_RUN_TIMEOUT` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201022` | — | — |
| `openjiuwen.02201023` | canonical8 | 工作流异步任务ID不存在。 | `StudioError.WORKFLOW_ASYNC_TASK_NOT_FOUND` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201023` | — | — |
| `openjiuwen.02201024` | canonical8 | 工作流异步任务需要为阻塞状态。 | `StudioError.WORKFLOW_ASYNC_NOT_PENDING` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201024` | — | — |
| `openjiuwen.02201025` | canonical8 | 其他节点正在处理异步任务! | `StudioError.WORKFLOW_ASYNC_GET_LOCK_FAILED` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201025` | — | — |
| `openjiuwen.02201026` | canonical8 | 执行异步工作流任务失败。 | `StudioError.WORKFLOW_ASYNC_EXECUTE_FAILED` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201026` | — | — |
| `openjiuwen.02201027` | canonical8 | 此工作流并非由您创建，您无权对其进行修改。 | `StudioError.PRIVILEGE_ERROR` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201027` | — | — |
| `openjiuwen.02201028` | canonical8 | 工作流{0}的子工作流{1}不存在。 | `StudioError.SUB_WORKFLOW_NOT_EXIST` | workflow | manager | business | 404 | WARN | active | `openjiuwen.02201028` | — | — |
| `openjiuwen.02201029` | canonical8 | 未找到工作流版本。 | `StudioError.WORKFLOW_VERSION_NOT_FOUND` | workflow | manager | business | 404 | WARN | active | `openjiuwen.02201029` | — | — |
| `openjiuwen.02201030` | canonical8 | 工作流尚未发布。 | `StudioError.WORKFLOW_NOT_PUBLISHED` | workflow | manager | business | 404 | WARN | active | `openjiuwen.02201030` | — | — |
| `openjiuwen.02201031` | canonical8 | 任务型工作流不允许添加{0}节点。 | `StudioError.WORKFLOW_TASK_INVALID_NODE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201031` | — | — |
| `openjiuwen.02201032` | canonical8 | 该租户没有发布工作流权限。 | `StudioError.WORKFLOW_TENANT_NOT_PERMISSION` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201032` | — | — |
| `openjiuwen.02201033` | canonical8 | 输出参数:{0},未正确引用变量。 | `StudioError.WORKFLOW_IR_FAILED_OUTPUT_TYPE_INVALID` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201033` | — | — |
| `openjiuwen.02201034` | canonical8 | 该节点没有被连接。 | `StudioError.WORKFLOW_IR_ERROR_COMPLEX_INTENT_NODE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201034` | — | — |
| `openjiuwen.02201035` | canonical8 | 安全护栏错误。 | `StudioError.SAFETY_BARRIER_ERROR` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201035` | — | — |
| `openjiuwen.02201036` | canonical8 | 没有发布的插件/工作流不能设置为自定义节点。 | `StudioError.PUBLISH_CUSTOMIZE_NODE_ERROR` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201036` | — | — |
| `openjiuwen.02201037` | canonical8 | 工作流图标大小超过限制。 | `StudioError.CHECK_WORKFLOW_INFO_FAILED_ICON` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201037` | — | — |
| `openjiuwen.02201038` | canonical8 | 工作流信息校验失败，不支持的工作流字段值类型。 | `StudioError.CHECK_WORKFLOW_INFO_FAILED_VALUE_TYPE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201038` | — | — |
| `openjiuwen.02201039` | canonical8 | 工作流信息校验失败，JSON Schema超过最大深度。 | `StudioError.CHECK_WORKFLOW_INFO_FAILED_DEPTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201039` | — | — |
| `openjiuwen.02201040` | canonical8 | 自定义节点数量超过最大限制。 | `StudioError.CUSTOMIZE_NODE_NUMBER_EXCEED_LIMIT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201040` | — | — |
| `openjiuwen.02201041` | canonical8 | 项目ID：{0} 没有权限发布或取消发布自定义节点。 | `StudioError.NO_PERMISSION_PUBLISH_CUSTOMIZE_NODE` | workflow | manager | security | 403 | WARN | active | `openjiuwen.02201041` | — | — |
| `openjiuwen.02201042` | canonical8 | 内容审核错误, {1}类型大小超过{0}。 | `StudioError.CONTENT_REVIEW_ERROR_SIZE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201042` | — | — |
| `openjiuwen.02201043` | canonical8 | 内容审核错误, {1}类型长度超过{0}。 | `StudioError.CONTENT_REVIEW_ERROR_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201043` | — | — |
| `openjiuwen.02201044` | canonical8 | 输入审核错误, {1}类型长度超过{0}。 | `StudioError.INPUT_TEXT_ERROR_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201044` | — | — |
| `openjiuwen.02201045` | canonical8 | 输出审核错误, {1}类型长度超过{0}。 | `StudioError.OUTPUT_TEXT_ERROR_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201045` | — | — |
| `openjiuwen.02201046` | canonical8 | 替换词审核错误, {1}类型长度超过{0}。 | `StudioError.REPLACE_WORD_ERROR_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201046` | — | — |
| `openjiuwen.02201047` | canonical8 | 子工作流不可用，ID为：{0}。 | `StudioError.SUB_WORKFLOW_CANNOT_USE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201047` | — | — |
| `openjiuwen.02201048` | canonical8 | 工作流分支字段值类型不受支持。 | `StudioError.WORKFLOW_BRANCH_FIELD_VALUE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201048` | — | — |
| `openjiuwen.02201049` | canonical8 | 不受支持的验证器类型:{0}。 | `StudioError.CONVERT_NODE_FAILED_VALIDATOR` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201049` | — | — |
| `openjiuwen.02201050` | canonical8 | 提问器节点解析日期时间格式失败。 | `StudioError.CONVERT_NODE_FAILED_PARSE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201050` | — | — |
| `openjiuwen.02201051` | canonical8 | 提问器节点解析长度限制格式失败。 | `StudioError.CONVERT_NODE_FAILED_PARSE_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201051` | — | — |
| `openjiuwen.02201052` | canonical8 | 提问器节点解析数字格式失败。 | `StudioError.CONVERT_NODE_FAILED_NUM_FORMAT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201052` | — | — |
| `openjiuwen.02201053` | canonical8 | 提问器节点解析整数格式失败。 | `StudioError.CONVERT_NODE_FAILED_INT_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201053` | — | — |
| `openjiuwen.02201054` | canonical8 | 提问器节点解析枚举格式失败。 | `StudioError.CONVERT_NODE_FAILED_ENUM_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201054` | — | — |
| `openjiuwen.02201055` | canonical8 | 提问器节点解析数字范围参数失败。 | `StudioError.CONVERT_NODE_FAILED_PARAM_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201055` | — | — |
| `openjiuwen.02201056` | canonical8 | 提问器节点设置格式无效。 | `StudioError.CONVERT_NODE_FAILED_INVALID_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201056` | — | — |
| `openjiuwen.02201057` | canonical8 | 未知的操作符：{0}。 | `StudioError.WORKFLOW_UNEXPECTED_OPERATOR` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201057` | — | — |
| `openjiuwen.02201058` | canonical8 | Runtime Service调用失败。 | `StudioError.JIU_WEN_SERVICE_EXCEPTION` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201058` | — | — |
| `openjiuwen.02201059` | canonical8 | 客户端断开流式接口请求。 | `StudioError.CLIENT_ABORT_REQUEST` | workflow | manager | business | 500 | ERROR | active | `openjiuwen.02201059` | — | — |
| `openjiuwen.02201060` | canonical8 | 工作流循环节点按次数循环范围应该为1-1000之间。 | `StudioError.WORKFLOW_LOOP_EXCEED_RANGE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201060` | — | — |
| `openjiuwen.02201061` | canonical8 | 无权限使用该工作流，工作流id为：{0}。 | `StudioError.WORKFLOW_NO_PERMISSION` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201061` | — | — |
| `openjiuwen.02201062` | canonical8 | 知识库节点绑定知识库过多。 | `StudioError.WORKFLOW_KNOWLEDGE_REPO_NUM` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201062` | — | — |
| `openjiuwen.02201063` | canonical8 | 运行工作流失败。 | `StudioError.WORKFLOW_RUN_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201063` | — | — |
| `openjiuwen.02201064` | canonical8 | 节点异常处理配置不合法；节点名称：{0}。 | `StudioError.WORKFLOW_EXCEPTION_CONFIG_INVALID` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201064` | — | — |
| `openjiuwen.02201065` | canonical8 | 节点:"{0}"超时时间设置不合法。 | `StudioError.WORKFLOW_TIME_RANGE_INVALID` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201065` | — | — |
| `openjiuwen.02201066` | canonical8 | 子工作流不存在。 | `StudioError.CHILD_WORKFLOW_NOT_EXIST` | workflow | manager | business | 404 | WARN | active | `openjiuwen.02201066` | — | — |
| `openjiuwen.02201067` | canonical8 | 工作流节点引用的资源不存在或异常。 | `StudioError.WORKFLOW_FLOW_RESOURCE_IMPORT_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201067` | — | — |
| `openjiuwen.02201069` | canonical8 | 异步执行任务需账号开启IAM委托。 | `StudioError.ASYNC_TASK_ACCOUNT_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201069` | — | — |
| `openjiuwen.02201070` | canonical8 | 异步执行任务超时。 | `StudioError.ASYNC_TASK_EXECUTE_TIMEOUT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201070` | — | — |
| `openjiuwen.02201071` | canonical8 | 异步执行任务失败，原因：{0}。 | `StudioError.ASYNC_TASK_EXECUTE_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201071` | — | — |
| `openjiuwen.02201072` | canonical8 | 代码节点已不支持沙箱执行方式。 | `StudioError.CODE_NOT_SUPPORT_SANDBOX` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201072` | — | — |
| `openjiuwen.02201073` | canonical8 | 工作流应用发布通道不存在。 | `StudioError.WORKFLOW_CHANNEL_NOT_EXIST` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201073` | — | — |
| `openjiuwen.02201074` | canonical8 | 当前发布渠道类型不支持删除。 | `StudioError.WORKFLOW_CHANNEL_NOT_SUPPORT_DELETE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201074` | — | — |
| `openjiuwen.02201077` | canonical8 | 节点:"{0}"异常重试次数配置不合法。 | `StudioError.WORKFLOW_EXCEPTION_RETRY_TIMES_INVALID` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201077` | — | — |
| `openjiuwen.02201078` | canonical8 | 流式输出节点:"{0}"异常设置不合法。 | `StudioError.WORKFLOW_EXCEPTION_STREAM_INVALID` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201078` | — | — |
| `openjiuwen.02201079` | canonical8 | 大模型节点:"{0}"，异常处理方式配置不合法。 | `StudioError.WORKFLOW_EXCEPTION_LLM_HANDLE_TYPE_INVALID` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201079` | — | — |
| `openjiuwen.02201080` | canonical8 | 工作流节点:"{0}"，重试设置不合法。 | `StudioError.WORKFLOW_EXCEPTION_WORKFLOW_NOT_SUPPORT_RETRY` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201080` | — | — |
| `openjiuwen.02201081` | canonical8 | 节点:"{0}"，异常处理方式配置不合法。 | `StudioError.WORKFLOW_EXCEPTION_NOT_SUPPORT_HANDLER` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201081` | — | — |
| `openjiuwen.02201082` | canonical8 | 工作流未试运行成功不能发布。 | `StudioError.WORKFLOW_CANNOT_RELEASE_FOR_NOT_TEST_SUCCESS` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201082` | — | — |
| `openjiuwen.02201083` | canonical8 | 资源:{0}不存在。 | `StudioError.RESOURCE_NOT_EXISTS` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201083` | — | — |
| `openjiuwen.02201084` | canonical8 | 获取调试事件失败。 | `StudioError.OBTAIN_DEBUG_EVENT_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201084` | — | — |
| `openjiuwen.02201085` | canonical8 | 工作流包含受限节点: "{0}"。 | `StudioError.WORKFLOW_BLOCK_NODE_EXIST` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201085` | — | — |
| `openjiuwen.02201086` | canonical8 | 运行时引擎连接异常 | `StudioError.JIUWEN_CONNECTION_EXCEPTION` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201086` | — | — |
| `openjiuwen.02201087` | canonical8 | 运行时引擎连接超时 | `StudioError.JIUWEN_CONNECTION_TIMEOUT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201087` | — | — |
| `openjiuwen.02201088` | canonical8 | 提问器节点配置参数长度超出最大限制 | `StudioError.QUESTIONER_CONFIG_EXCEED_MAX_LENGTH` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201088` | — | — |
| `openjiuwen.02201090` | canonical8 | 解析第三方工作流文件失败 | `StudioError.PARSE_THIRD_PARTY_WORKFLOW_FILE_FAILED` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201090` | — | — |
| `openjiuwen.02201093` | canonical8 | 提问器节点在关闭参数提取时，问题配置为空。 | `StudioError.MISSING_FRAME_TEMPLATE` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201093` | — | — |
| `openjiuwen.02201094` | canonical8 | 流式消息节点缺少定义输出的流式消息内容。 | `StudioError.FRAME_TEMPLATE_INVALID_JSON` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201094` | — | — |
| `openjiuwen.02201095` | canonical8 | 流式消息内容解析失败 | `StudioError.MISSING_TRANSFORMER` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201095` | — | — |
| `openjiuwen.02201097` | canonical8 | 导入的文件中存在不支持的资源：{0}。 | `StudioError.UNSUPPORTED_RESOURCE_IMPORT` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201097` | — | — |
| `openjiuwen.02201098` | canonical8 | 异常节点template字段不是合法的JSON格式字符串，节点名称：{0} | `StudioError.WORKFLOW_TEMPLATE_INVALID_JSON` | workflow | manager | business | 400 | WARN | active | `openjiuwen.02201098` | — | — |
| `openjiuwen.02301001` | canonical8 | 多智能体缺失控制器节点 | `StudioError.MULTI_AGENT_LACK_CONTROLLER_NODE` | multi_agent | manager | business | 400 | WARN | active | `openjiuwen.02301001` | — | — |
| `openjiuwen.02301002` | canonical8 | 多智能体节点为空 | `StudioError.MULTI_AGENT_NODES_IS_EMPTY` | multi_agent | manager | business | 400 | WARN | active | `openjiuwen.02301002` | — | — |
| `openjiuwen.02301003` | canonical8 | 多智能体存在重复的子工作流 | `StudioError.MULTI_AGENT_HAVE_DUPLICATE_SON_WORKFLOW` | multi_agent | manager | business | 400 | WARN | active | `openjiuwen.02301003` | — | — |
| `openjiuwen.02301004` | canonical8 | 多智能体控制器节点配置为空 | `StudioError.MULTI_AGENT_CONTROLLER_CONFIGS_NULL` | multi_agent | manager | business | 400 | WARN | active | `openjiuwen.02301004` | — | — |
| `openjiuwen.02301005` | canonical8 | 多智能体不支持的工作流类型 | `StudioError.MULTI_AGENT_UNSUPPORTED_WORKFLOW_TYPE` | multi_agent | manager | business | 400 | WARN | active | `openjiuwen.02301005` | — | — |
| `openjiuwen.02301006` | canonical8 | 意图工作流配置无效！ | `StudioError.MULTI_AGENT_WORKFLOW_CONFIG_VALID` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301006` | — | — |
| `openjiuwen.02301007` | canonical8 | 意图工作流的输入或输出不能为空 | `StudioError.MULTI_AGENT_WORKFLOW_INPUT_EMPTY` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301007` | — | — |
| `openjiuwen.02301008` | canonical8 | 存在重复的意图节点 | `StudioError.MULTI_AGENT_DUPLICATED_NODE` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301008` | — | — |
| `openjiuwen.02301009` | canonical8 | 意图工作流参数查询无效 | `StudioError.MULTI_AGENT_WORKFLOW_PARAM_VALID` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301009` | — | — |
| `openjiuwen.02301010` | canonical8 | 意图工作流输入参数 minScore 无效 | `StudioError.MULTI_AGENT_WORKFLOW_MIN_SCORE_VALID` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301010` | — | — |
| `openjiuwen.02301011` | canonical8 | 意图工作流缺少必需的输入参数 | `StudioError.MULTI_AGENT_WORKFLOW_MISSING` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301011` | — | — |
| `openjiuwen.02301012` | canonical8 | 意图工作流输出参数intent_id无效 | `StudioError.MULTI_AGENT_WORKFLOW_INTENT_VALID` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301012` | — | — |
| `openjiuwen.02301013` | canonical8 | 意图工作流缺少输出参数：{0} | `StudioError.MULTI_AGENT_WORKFLOW_OUTPUT_MISSING` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301013` | — | — |
| `openjiuwen.02301014` | canonical8 | 意图工作流输入参数 messages 的子参数 {0} 无效 | `StudioError.MULTI_AGENT_WORKFLOW_INPUT_SUB_PARAM_VALID` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301014` | — | — |
| `openjiuwen.02301015` | canonical8 | 意图工作流 message 参数缺少属性：{0} | `StudioError.MULTI_AGENT_WORKFLOW_MESSAGE_MISSING` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301015` | — | — |
| `openjiuwen.02301019` | canonical8 | 未找到子工作流版本 {0}！ | `StudioError.MULTI_AGENT_SUB_WORKFLOW_VERSION_NOT_FOUND` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301019` | — | — |
| `openjiuwen.02301020` | canonical8 | 多智能体名称冲突 | `StudioError.MULTI_AGENT_NAME_CONFLICT` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301020` | — | — |
| `openjiuwen.02301021` | canonical8 | 绑定子智能体重复：{0} | `StudioError.MULTI_AGENT_HAVE_DUPLICATE_SON_AGENT` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301021` | — | — |
| `openjiuwen.02301022` | canonical8 | 绑定的子智能体达到最大限制 | `StudioError.MULTI_AGENT_NUMBER_EXCEED_LIMIT` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301022` | — | — |
| `openjiuwen.02301023` | canonical8 | 当前子智能体版本不存在。智能体ID：{0}, 版本：{1} | `StudioError.MULTI_AGENT_VERSION_NOT_EXIST` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301023` | — | — |
| `openjiuwen.02301024` | canonical8 | 多智能体导出失败 | `StudioError.MULTI_AGENT_EXPORT_FAILED` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301024` | — | — |
| `openjiuwen.02301025` | canonical8 | 绑定子智能体达到最大深度限制 | `StudioError.MULTI_AGENT_EXCEED_MAX_DEPTH` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301025` | — | — |
| `openjiuwen.02301026` | canonical8 | 多智能体全局配置输入参数默认值达到最大长度限制 | `StudioError.MULTI_AGENT_INPUT_DEFAULT_VALUE_MAX_LENGTH` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301026` | — | — |
| `openjiuwen.02301027` | canonical8 | 多智能体全局变量默认值达到最大长度限制 | `StudioError.MULTI_AGENT_GLOBAL_VARIABLE_VALUE_MAX_LENGTH` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301027` | — | — |
| `openjiuwen.02301028` | canonical8 | 多智能体模型配置或意图识别为空 | `StudioError.MULTI_AGENT_MODEL_OR_INTENT_IS_NULL` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301028` | — | — |
| `openjiuwen.02301029` | canonical8 | 控制器挂载单智能体失败 | `StudioError.MULTI_AGENT_ONLY_ONE_PLAN_EXECUTE_AGENT` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301029` | — | — |
| `openjiuwen.02301030` | canonical8 | 绑定子控制器失败 | `StudioError.MULTI_AGENT_PLAN_EXECUTE_ONLY_IN_TOP_CONTROLLER` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301030` | — | — |
| `openjiuwen.02301031` | canonical8 | 绑定子多智能体失败 | `StudioError.MULTI_AGENT_CANNOT_ASSOCIATE_SELF` | multi_agent | manager | business | 500 | ERROR | active | `openjiuwen.02301031` | — | — |
| `openjiuwen.02401001` | canonical8 | 工具信息格式错误 | `StudioError.TOOL_INPUT_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401001` | — | — |
| `openjiuwen.02401002` | canonical8 | 入参格式错误 | `StudioError.TOOL_INPUT_SCHEMA_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401002` | — | — |
| `openjiuwen.02401003` | canonical8 | 出参格式错误 | `StudioError.TOOL_OUTPUT_SCHEMA_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401003` | — | — |
| `openjiuwen.02401004` | canonical8 | 工具名称已存在 | `StudioError.TOOL_NAME_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401004` | — | — |
| `openjiuwen.02401005` | canonical8 | 工具不存在 | `StudioError.TOOL_NOT_EXIST` | component | manager | business | 404 | WARN | active | `openjiuwen.02401005` | — | — |
| `openjiuwen.02401006` | canonical8 | 工作流校验失败 | `StudioError.CONVERT_NODE_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401006` | — | — |
| `openjiuwen.02401007` | canonical8 | 无修改权限 | `StudioError.NO_PERMISSION_MODIFY_TOOL` | component | manager | security | 403 | WARN | active | `openjiuwen.02401007` | — | — |
| `openjiuwen.02401008` | canonical8 | 无删除权限 | `StudioError.NO_PERMISSION_DELETE_TOOL` | component | manager | security | 403 | WARN | active | `openjiuwen.02401008` | — | — |
| `openjiuwen.02401009` | canonical8 | 插件导入失败 | `StudioError.TOOL_IMPORT_FILE` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401009` | — | — |
| `openjiuwen.02401010` | canonical8 | 插件导出失败 | `StudioError.TOOL_EXPORT_FILE` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401010` | — | — |
| `openjiuwen.02401011` | canonical8 | 文件内容为空 | `StudioError.DEPENDENCY_FILE_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401011` | — | — |
| `openjiuwen.02401012` | canonical8 | 文件大小超限 | `StudioError.DEPENDENCY_FILE_TOO_LARGE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401012` | — | — |
| `openjiuwen.02401013` | canonical8 | 文件类型不支持 | `StudioError.DEPENDENCY_FILE_TYPE_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401013` | — | — |
| `openjiuwen.02401014` | canonical8 | 依赖项已存在 | `StudioError.DEPENDENCY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401014` | — | — |
| `openjiuwen.02401015` | canonical8 | 依赖项未找到 | `StudioError.DEPENDENCY_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401015` | — | — |
| `openjiuwen.02401018` | canonical8 | 数据格式错误 | `StudioError.DATA_FORMAT_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401018` | — | — |
| `openjiuwen.02401019` | canonical8 | 名称已存在 | `StudioError.DEPENDENCY_NAME_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401019` | — | — |
| `openjiuwen.02401020` | canonical8 | 范围无效 | `StudioError.INVALID_SCOPE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401020` | — | — |
| `openjiuwen.02401021` | canonical8 | 请求函数图失败 | `StudioError.REQUEST_DEPEND_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401021` | — | — |
| `openjiuwen.02401022` | canonical8 | 更新依赖项失败 | `StudioError.UPDATE_DEPENDENCY_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401022` | — | — |
| `openjiuwen.02401023` | canonical8 | 依赖项被占用 | `StudioError.DEPENDENCY_DELETE_FAILED_IS_USED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401023` | — | — |
| `openjiuwen.02401024` | canonical8 | 删除依赖项失败 | `StudioError.DEPENDENCY_DELETE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401024` | — | — |
| `openjiuwen.02401025` | canonical8 | 内存设置超限 | `StudioError.FUNCTION_MEMORY_SIZE_TOO_BIG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401025` | — | — |
| `openjiuwen.02401026` | canonical8 | UTF-8解析异常 | `StudioError.PARSE_UTF8_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401026` | — | — |
| `openjiuwen.02401027` | canonical8 | 不支持Python | `StudioError.FUNCTION_NOT_SUPPORTED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401027` | — | — |
| `openjiuwen.02401028` | canonical8 | 获取代码失败 | `StudioError.FUNCTION_GET_CODE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401028` | — | — |
| `openjiuwen.02401029` | canonical8 | Java11参数缺失 | `StudioError.FUNCTION_PARAMETERS_NOT_SUPPORTED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401029` | — | — |
| `openjiuwen.02401031` | canonical8 | 函数数量超限 | `StudioError.FUNCTION_NUMBER_OVER_THRESHOLD` | component | manager | business | 400 | WARN | active | `openjiuwen.02401031` | — | — |
| `openjiuwen.02401032` | canonical8 | 函数不存在 | `StudioError.FUNCTION_NOT_FOUND` | component | manager | business | 400 | WARN | active | `openjiuwen.02401032` | — | — |
| `openjiuwen.02401033` | canonical8 | 运行时不支持 | `StudioError.FUNCTION_RUNTIME_NOT_SUPPORT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401033` | — | — |
| `openjiuwen.02401034` | canonical8 | 代码更新失败 | `StudioError.FUNCTION_CODE_UPDATE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401034` | — | — |
| `openjiuwen.02401035` | canonical8 | 函数名称已存在 | `StudioError.FUNCTION_NAME_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401035` | — | — |
| `openjiuwen.02401036` | canonical8 | 检查工具信息失败 | `StudioError.GET_TOOL_INFO_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401036` | — | — |
| `openjiuwen.02401037` | canonical8 | 插件权限错误 | `StudioError.PLUGIN_PRIVILEGE_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401037` | — | — |
| `openjiuwen.02401038` | canonical8 | 工具信息不匹配 | `StudioError.TOOL_PROJECT_DONE_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401038` | — | — |
| `openjiuwen.02401039` | canonical8 | 文件解析失败 | `StudioError.FILE_RESOLVE_FILE` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401039` | — | — |
| `openjiuwen.02401040` | canonical8 | 文件格式错误 | `StudioError.FILE_FORMAT_INCORRECT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401040` | — | — |
| `openjiuwen.02401041` | canonical8 | 导出数量超限 | `StudioError.EXPORT_LENGTH_TOO_LARGE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401041` | — | — |
| `openjiuwen.02401042` | canonical8 | 版本不存在 | `StudioError.TOOL_VERSION_NOT_EXIST` | component | manager | business | 404 | WARN | active | `openjiuwen.02401042` | — | — |
| `openjiuwen.02401043` | canonical8 | 获取OBS URL失败 | `StudioError.GET_OBS_TEMPORARY_URL_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401043` | — | — |
| `openjiuwen.02401044` | canonical8 | 可见性值无效 | `StudioError.INVALID_VISIBILITY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401044` | — | — |
| `openjiuwen.02401045` | canonical8 | OpenAPI生成失败 | `StudioError.OPEN_API_GEN_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401045` | — | — |
| `openjiuwen.02401046` | canonical8 | 发布未经测试组件 | `StudioError.PUBLISH_UNTESTED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401046` | — | — |
| `openjiuwen.02401047` | canonical8 | 插件鉴权失败 | `StudioError.TOOL_AUTHENTICATION_FAILED` | component | manager | security | 401 | WARN | active | `openjiuwen.02401047` | — | — |
| `openjiuwen.02401048` | canonical8 | 插件凭证缺失 | `StudioError.TOOL_CREDENTIAL_NOT_EXIST` | component | manager | security | 401 | WARN | active | `openjiuwen.02401048` | — | — |
| `openjiuwen.02401049` | canonical8 | 凭证已存在 | `StudioError.TOOL_CREDENTIAL_ALREADY_EXIST` | component | manager | security | 401 | WARN | active | `openjiuwen.02401049` | — | — |
| `openjiuwen.02401050` | canonical8 | 中文名已存在 | `StudioError.TOOL_CN_NAME_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401050` | — | — |
| `openjiuwen.02401051` | canonical8 | 英文名已存在 | `StudioError.TOOL_EN_NAME_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401051` | — | — |
| `openjiuwen.02401052` | canonical8 | MCP服务不存在 | `StudioError.MCP_SERVER_NOT_EXIST` | component | manager | business | 404 | WARN | active | `openjiuwen.02401052` | — | — |
| `openjiuwen.02401053` | canonical8 | 更新记忆参数失败 | `StudioError.UPDATE_MEMORY_VARIABLES_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401053` | — | — |
| `openjiuwen.02401054` | canonical8 | 获取记忆参数失败 | `StudioError.RETRIEVE_MEMORY_VARIABLES_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401054` | — | — |
| `openjiuwen.02401055` | canonical8 | 获取文件流失败 | `StudioError.GET_BY_URL_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401055` | — | — |
| `openjiuwen.02401056` | canonical8 | 解析文件失败 | `StudioError.RESOLVE_FILE_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401056` | — | — |
| `openjiuwen.02401057` | canonical8 | 文件不存在 | `StudioError.FILE_NOT_EXIST` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401057` | — | — |
| `openjiuwen.02401058` | canonical8 | OpenAPI解析失败 | `StudioError.OPEN_API_PARSE_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401058` | — | — |
| `openjiuwen.02401059` | canonical8 | 路径获取失败 | `StudioError.GET_PATH_FROM_URI_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401059` | — | — |
| `openjiuwen.02401060` | canonical8 | MCP服务错误 | `StudioError.MCP_REQUEST_ERROR` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401060` | — | — |
| `openjiuwen.02401061` | canonical8 | 构建文件流失败 | `StudioError.BUILD_INPUT_STREAM_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401061` | — | — |
| `openjiuwen.02401062` | canonical8 | Base64编码失败 | `StudioError.IMAGE_TO_BASE64_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401062` | — | — |
| `openjiuwen.02401063` | canonical8 | OCR识别失败 | `StudioError.OCR_RECOGNIZE_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401063` | — | — |
| `openjiuwen.02401064` | canonical8 | URL参数校验失败 | `StudioError.VALIDATE_RESOLVE_URLS_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401064` | — | — |
| `openjiuwen.02401065` | canonical8 | API未找到 | `StudioError.MCP_API_NOT_FOUND` | component | manager | business | 404 | WARN | active | `openjiuwen.02401065` | — | — |
| `openjiuwen.02401066` | canonical8 | 适配IR失败(服务缺失) | `StudioError.MCP_ADAPT_IR_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401066` | — | — |
| `openjiuwen.02401067` | canonical8 | 适配IR失败(工具缺失) | `StudioError.MCP_SERVER_TOOL_NOT_EXIST` | component | manager | business | 404 | WARN | active | `openjiuwen.02401067` | — | — |
| `openjiuwen.02401068` | canonical8 | MCP名称已存在 | `StudioError.MCP_NAME_DUPLICATE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401068` | — | — |
| `openjiuwen.02401069` | canonical8 | MCP服务不存在 | `StudioError.MCP_SERVER_ID_NOT_EXIST` | component | manager | business | 404 | WARN | active | `openjiuwen.02401069` | — | — |
| `openjiuwen.02401070` | canonical8 | MCP配置已存在 | `StudioError.MCP_CONFIG_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401070` | — | — |
| `openjiuwen.02401071` | canonical8 | MCP配置不存在 | `StudioError.MCP_CONFIG_NOT_EXIST` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401071` | — | — |
| `openjiuwen.02401072` | canonical8 | MCP服务缺失 | `StudioError.MCP_NOT_EXIST` | component | manager | business | 404 | WARN | active | `openjiuwen.02401072` | — | — |
| `openjiuwen.02401073` | canonical8 | URL不能为空 | `StudioError.MCP_SERVER_URL_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401073` | — | — |
| `openjiuwen.02401074` | canonical8 | 禁止更新URL | `StudioError.UPDATE_MCP_URL_NOT_ALLOW` | component | manager | security | 403 | WARN | active | `openjiuwen.02401074` | — | — |
| `openjiuwen.02401075` | canonical8 | MCP名称不能为空 | `StudioError.MCP_NAME_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401075` | — | — |
| `openjiuwen.02401076` | canonical8 | 英文名不能为空 | `StudioError.MCP_ENGLISH_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401076` | — | — |
| `openjiuwen.02401077` | canonical8 | 描述不能为空 | `StudioError.MCP_DESCRIPTION_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401077` | — | — |
| `openjiuwen.02401078` | canonical8 | 可见性设置无效 | `StudioError.MCP_VISIBILITY_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401078` | — | — |
| `openjiuwen.02401079` | canonical8 | 无操作权限 | `StudioError.MCP_PERMISSION_DENY` | component | manager | security | 403 | WARN | active | `openjiuwen.02401079` | — | — |
| `openjiuwen.02401080` | canonical8 | 缺少认证密钥 | `StudioError.MCP_CONFIG_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401080` | — | — |
| `openjiuwen.02401081` | canonical8 | 自定义配置失败 | `StudioError.MCP_CANNOT_CONFIG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401081` | — | — |
| `openjiuwen.02401082` | canonical8 | 公共配置失败 | `StudioError.MCP_CANNOT_CONFIG_PUBLIC` | component | manager | business | 400 | WARN | active | `openjiuwen.02401082` | — | — |
| `openjiuwen.02401083` | canonical8 | 配置字段为空 | `StudioError.MCP_CONFIG_ERROR_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401083` | — | — |
| `openjiuwen.02401084` | canonical8 | 缺少必要字段 | `StudioError.MCP_CONFIG_MISS_KEY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401084` | — | — |
| `openjiuwen.02401085` | canonical8 | 获取MCP工具失败 | `StudioError.MCP_TOOL_ERROR` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401085` | — | — |
| `openjiuwen.02401086` | canonical8 | 插件无法使用 | `StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401086` | — | — |
| `openjiuwen.02401087` | canonical8 | 非法API调用 | `StudioError.ILLEGAL_API_INVOKE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401087` | — | — |
| `openjiuwen.02401088` | canonical8 | 参数无效 | `StudioError.INVALID_PARAMETER_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401088` | — | — |
| `openjiuwen.02401089` | canonical8 | 远程调用失败 | `StudioError.REMOTE_CALL_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401089` | — | — |
| `openjiuwen.02401090` | canonical8 | 无资源访问权 | `StudioError.USER_HAS_NO_PERMISSION` | component | manager | business | 400 | WARN | active | `openjiuwen.02401090` | — | — |
| `openjiuwen.02401091` | canonical8 | 缺少输入参数 | `StudioError.MISSING_PARAM` | component | manager | business | 400 | WARN | active | `openjiuwen.02401091` | — | — |
| `openjiuwen.02401092` | canonical8 | 无法删除创建中服务 | `StudioError.MCP_SERVICE_CREATING_STATUS_NOT_DELETE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401092` | — | — |
| `openjiuwen.02401093` | canonical8 | 无法删除删除中服务 | `StudioError.MCP_SERVICE_DELETING_STATUS_NOT_DELETE` | component | manager | business | 400 | WARN | active | `openjiuwen.02401093` | — | — |
| `openjiuwen.02401094` | canonical8 | FG删除失败 | `StudioError.MCP_SERVICE_DELETE_FAILED_FROM_FG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401094` | — | — |
| `openjiuwen.02401095` | canonical8 | MCP服务不存在 | `StudioError.MCP_SERVICE_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401095` | — | — |
| `openjiuwen.02401096` | canonical8 | 配置格式错误 | `StudioError.TOOLS_DATA_NOT_JSON_FORMAT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401096` | — | — |
| `openjiuwen.02401097` | canonical8 | 属性修改失败 | `StudioError.UPDATE_OBJECT_PROPERTIES_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401097` | — | — |
| `openjiuwen.02401098` | canonical8 | MCP服务名称已存在 | `StudioError.MCP_SERVICE_IS_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401098` | — | — |
| `openjiuwen.02401099` | canonical8 | FG创建服务失败 | `StudioError.MCP_SERVICE_CREATE_FAILED_FROM_FG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401099` | — | — |
| `openjiuwen.02401100` | canonical8 | 更新等待超时 | `StudioError.APPLICATION_UPDATE_TIMEOUT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401100` | — | — |
| `openjiuwen.02401101` | canonical8 | 查询工具列表错误 | `StudioError.QUERY_MCP_SERVICE_TOOL_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401101` | — | — |
| `openjiuwen.02401102` | canonical8 | 配置格式不正确 | `StudioError.MCP_SERVICE_CONFIG_FORMAT_INCORRECT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401102` | — | — |
| `openjiuwen.02401103` | canonical8 | 工具调用错误 | `StudioError.INVOKING_MCP_SERVICE_TOOL_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401103` | — | — |
| `openjiuwen.02401104` | canonical8 | FG接口调用失败 | `StudioError.INVOKING_FG_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401104` | — | — |
| `openjiuwen.02401105` | canonical8 | 部署数量超限 | `StudioError.SERVICE_EXCEEDING_LIMIT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401105` | — | — |
| `openjiuwen.02401106` | canonical8 | 查询工具列表失败 | `StudioError.MCP_SERVICE_BUSY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401106` | — | — |
| `openjiuwen.02401107` | canonical8 | 无MCP权限 | `StudioError.NO_PERMISSION_FOR_MCP` | component | manager | business | 400 | WARN | active | `openjiuwen.02401107` | — | — |
| `openjiuwen.02401108` | canonical8 | 非法镜像格式 | `StudioError.ILLEGAL_IMAGE_FORMAT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401108` | — | — |
| `openjiuwen.02401109` | canonical8 | 镜像大小超限 | `StudioError.IMAGE_EXCEEDS_LIMIT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401109` | — | — |
| `openjiuwen.02401110` | canonical8 | 授权失败 | `StudioError.DO_AUTHORIZATION_FROM_FG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401110` | — | — |
| `openjiuwen.02401111` | canonical8 | 取消授权失败 | `StudioError.CANCEL_AUTHORIZATION_FROM_FG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401111` | — | — |
| `openjiuwen.02401112` | canonical8 | 查询授权失败 | `StudioError.QUERY_AUTHORIZATION_FROM_FG` | component | manager | business | 400 | WARN | active | `openjiuwen.02401112` | — | — |
| `openjiuwen.02401113` | canonical8 | IAM操作失败 | `StudioError.AGENCY_FAIL` | component | manager | business | 400 | WARN | active | `openjiuwen.02401113` | — | — |
| `openjiuwen.02401117` | canonical8 | 插件展示名称重复 | `StudioError.PLUGIN_CN_NAME_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401117` | — | — |
| `openjiuwen.02401118` | canonical8 | 插件名称重复 | `StudioError.PLUGIN_EN_NAME_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401118` | — | — |
| `openjiuwen.02401119` | canonical8 | 名称格式无效 | `StudioError.MCP_SERVICE_NAME_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401119` | — | — |
| `openjiuwen.02401120` | canonical8 | 配置包含非法字符 | `StudioError.MCP_SERVICE_CONFIG_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401120` | — | — |
| `openjiuwen.02401121` | canonical8 | 认证配置不可用 | `StudioError.PLUGIN_AUTH_DATA_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401121` | — | — |
| `openjiuwen.02401122` | canonical8 | 鉴权超时 | `StudioError.PLUGIN_AUTH_REQUEST_TIMEOUT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401122` | — | — |
| `openjiuwen.02401123` | canonical8 | 鉴权网络错误 | `StudioError.PLUGIN_AUTH_REQUEST_INTERNAL_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401123` | — | — |
| `openjiuwen.02401124` | canonical8 | 函数已绑定 | `StudioError.PLUGIN_FUNCTION_MAPPING_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401124` | — | — |
| `openjiuwen.02401125` | canonical8 | 函数不存在 | `StudioError.PLUGIN_FUNCTION_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401125` | — | — |
| `openjiuwen.02401126` | canonical8 | 删除函数错误 | `StudioError.FUNCTION_DELETE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401126` | — | — |
| `openjiuwen.02401127` | canonical8 | 删除失败(已绑定) | `StudioError.FUNCTION_DELETE_BIND_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401127` | — | — |
| `openjiuwen.02401128` | canonical8 | 禁止修改插件类型 | `StudioError.PLUGIN_CALL_MODE_CANNOT_MODIFFY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401128` | — | — |
| `openjiuwen.02401129` | canonical8 | 函数模板不存在 | `StudioError.GET_FUNCTION_TEMPLATE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401129` | — | — |
| `openjiuwen.02401130` | canonical8 | ID已存在 | `StudioError.PLUGIN_ID_ALREADY_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401130` | — | — |
| `openjiuwen.02401131` | canonical8 | 禁止复制API插件 | `StudioError.API_PLUGIN_CAN_NOT_COPY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401131` | — | — |
| `openjiuwen.02401132` | canonical8 | 分数范围错误 | `StudioError.SCORE_PARAM_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401132` | — | — |
| `openjiuwen.02401138` | canonical8 | 工具数量超限 | `StudioError.TOOL_NUM_EXCEEDS_LIMIT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401138` | — | — |
| `openjiuwen.02401139` | canonical8 | 重试次数无效 | `StudioError.PLUGIN_EXCEPTION_OVER_LIMIT` | component | manager | business | 400 | WARN | active | `openjiuwen.02401139` | — | — |
| `openjiuwen.02401140` | canonical8 | 无权查看插件 | `StudioError.PLUGIN_NO_PERMISSION_VIEW` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401140` | — | — |
| `openjiuwen.02401141` | canonical8 | 参数名重复 | `StudioError.DUPLICATE_PARAMETER_NAME_EXCEPTION` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401141` | — | — |
| `openjiuwen.02401142` | canonical8 | 安装方式不支持 | `StudioError.MCP_SERVICE_ORG_TYPE_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401142` | — | — |
| `openjiuwen.02401143` | canonical8 | 安装方式为空 | `StudioError.MCP_SERVICE_ORG_TYPE_EMPTY` | component | manager | business | 400 | WARN | active | `openjiuwen.02401143` | — | — |
| `openjiuwen.02401144` | canonical8 | 部署方式受限 | `StudioError.ONLY_SSE_OR_STREAMABLE_HTTP_SERVICE_ALLOWED_THIRD` | component | manager | business | 400 | WARN | active | `openjiuwen.02401144` | — | — |
| `openjiuwen.02401145` | canonical8 | IAM认证URL错误 | `StudioError.PLUGIN_IAM_AUTNEHTICATION_URL_CONFIG_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401145` | — | — |
| `openjiuwen.02401146` | canonical8 | MCP格式校验失败 | `StudioError.MCP_CONFIG_FORMAT_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401146` | — | — |
| `openjiuwen.02401147` | canonical8 | FG配额不足 | `StudioError.MCP_FG_QUOTA_EXCEEDED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401147` | — | — |
| `openjiuwen.02401148` | canonical8 | FG执行错误 | `StudioError.MCP_FG_EXECUTION_ERROR` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401148` | — | — |
| `openjiuwen.02401149` | canonical8 | 获取MCP工具错误 | `StudioError.MCP_FETCH_TOOLS_SERVER_ERROR` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401149` | — | — |
| `openjiuwen.02401150` | canonical8 | 网络连接失败 | `StudioError.MCP_NETWORK_CONNECTION_ERROR` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401150` | — | — |
| `openjiuwen.02401151` | canonical8 | 地址受限 | `StudioError.MCP_ADDRESS_RESTRICTED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401151` | — | — |
| `openjiuwen.02401152` | canonical8 | 输出列表解析失败 | `StudioError.PARSE_BUILD_OUTPUT_LIST_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401152` | — | — |
| `openjiuwen.02401153` | canonical8 | 对象解析失败 | `StudioError.PARSE_STRING_TO_OBJECT_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401153` | — | — |
| `openjiuwen.02401154` | canonical8 | RequestInfo解析失败 | `StudioError.PARSE_REQUEST_TO_TOOL_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401154` | — | — |
| `openjiuwen.02401155` | canonical8 | URL前缀不匹配 | `StudioError.URL_PREFIX_NOT_MATCH` | component | manager | business | 400 | WARN | active | `openjiuwen.02401155` | — | — |
| `openjiuwen.02401156` | canonical8 | 无法将buildIntfType 解析为 ToolInfo | `StudioError.PARSE_BUILD_INT_TYPE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401156` | — | — |
| `openjiuwen.02401157` | canonical8 | 未能将buildTestStatus 解析为 ToolInfo | `StudioError.BUILD_STATUS_TOOL_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401157` | — | — |
| `openjiuwen.02401158` | canonical8 | 无法将 buildOutputSchema 解析为 ToolInfo | `StudioError.PARSE_OUTPUT_SCHEMA_TOOL_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401158` | — | — |
| `openjiuwen.02401159` | canonical8 | 无法将 buildInputList 解析为 ToolInfo | `StudioError.PARSE_INPUT_SCHEMA_TOOL_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401159` | — | — |
| `openjiuwen.02401161` | canonical8 | MCP连接超时 | `StudioError.MCP_NETWORK_TIMEOUT` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401161` | — | — |
| `openjiuwen.02401162` | canonical8 | 连接被拒绝 | `StudioError.MCP_CONNECTION_REFUSED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401162` | — | — |
| `openjiuwen.02401163` | canonical8 | 路径错误(404) | `StudioError.MCP_TARGET_NOT_FOUND` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401163` | — | — |
| `openjiuwen.02401164` | canonical8 | 认证失败(401/403) | `StudioError.MCP_AUTHENTICATION_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401164` | — | — |
| `openjiuwen.02401165` | canonical8 | APIG创建失败 | `StudioError.CREATE_MCP_API_FAILED` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401165` | — | — |
| `openjiuwen.02401166` | canonical8 | 查询依赖包失败 | `StudioError.REQUEST_DEPEND_PACKAGE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401166` | — | — |
| `openjiuwen.02401167` | canonical8 | 查询依赖版本失败 | `StudioError.REQUEST_DEPEND_PACKAGE_VERSION_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401167` | — | — |
| `openjiuwen.02401168` | canonical8 | 依赖包版本不存在 | `StudioError.REQUEST_DEPEND_PACKAGE_VERSION_NOT_EXITS` | component | manager | business | 400 | WARN | active | `openjiuwen.02401168` | — | — |
| `openjiuwen.02401169` | canonical8 | 导入OpenAPI文件为空 | `StudioError.OPENAPI_FILE_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401169` | — | — |
| `openjiuwen.02401170` | canonical8 | 导入OpenAPI文件中Server为空 | `StudioError.SERVER_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401170` | — | — |
| `openjiuwen.02401171` | canonical8 | 导入OpenAPI文件中Server中URL为空 | `StudioError.SERVER_URL_NOT_EXIST` | component | manager | business | 400 | WARN | active | `openjiuwen.02401171` | — | — |
| `openjiuwen.02401172` | canonical8 | 解析OpenApi文件失败 | `StudioError.OPENAPI_PARSE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401172` | — | — |
| `openjiuwen.02401173` | canonical8 | 无法解析主机地址 | `StudioError.MCP_UNKNOWN_HOST` | component | manager | business | 500 | ERROR | active | `openjiuwen.02401173` | — | — |
| `openjiuwen.02401174` | canonical8 | 认证配置不可用 | `StudioError.MCP_AUTH_DATA_INVALID` | component | manager | business | 400 | WARN | active | `openjiuwen.02401174` | — | — |
| `openjiuwen.02401175` | canonical8 | 获取函数失败 | `StudioError.SHOW_FUNCTION_CODE_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401175` | — | — |
| `openjiuwen.02401176` | canonical8 | 获取函数metadata失败 | `StudioError.FUNCTION_METADATA_GET_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401176` | — | — |
| `openjiuwen.02401177` | canonical8 | OAUTH鉴权信息配置错误 | `StudioError.OAUTH_INFORMATION_OVER_LENGTH` | component | manager | business | 400 | WARN | active | `openjiuwen.02401177` | — | — |
| `openjiuwen.02401178` | canonical8 | APIKEY鉴权信息配置错误 | `StudioError.APIKEY_INFORMATION_OVER_LENGTH` | component | manager | business | 400 | WARN | active | `openjiuwen.02401178` | — | — |
| `openjiuwen.02401179` | canonical8 | 获取预置插件免费额度失败 | `StudioError.PLUGIN_FREE_TRIAL_USAGE_QUOTA_ERROR` | component | manager | business | 400 | WARN | active | `openjiuwen.02401179` | — | — |
| `openjiuwen.02401180` | canonical8 | 插件更新发布失败 | `StudioError.RELEASE_PUBLISH_FAILED` | component | manager | business | 400 | WARN | active | `openjiuwen.02401180` | — | — |
| `openjiuwen.02401181` | canonical8 | 插件鉴权方式或鉴权秘钥位置为空。 | `StudioError.PLUGIN_AUTH_KEY_DOMAIN_NOT_NULL` | component | manager | business | 400 | WARN | active | `openjiuwen.02401181` | — | — |
| `openjiuwen.02601001` | canonical8 | {0}中的分支数量超过了限制，请确认后重试 | `StudioError.BRANCHES_SIZE_EXCEEDS_LIMIT` | config | manager | business | 400 | WARN | active | `openjiuwen.02601001` | — | — |
| `openjiuwen.02601002` | canonical8 | 导入意图包失败 | `StudioError.INTENT_IMPORT_FILE_ERROR` | config | manager | business | 500 | ERROR | active | `openjiuwen.02601002` | — | — |
| `openjiuwen.02601003` | canonical8 | 导入意图包时文件大小超出限制 | `StudioError.INTENT_IMPORT_FILE_SIZE_LIMIT` | config | manager | business | 500 | ERROR | active | `openjiuwen.02601003` | — | — |
| `openjiuwen.02601004` | canonical8 | 导出意图包失败 | `StudioError.INTENT_EXPORT_FILE_ERROR` | config | manager | business | 500 | ERROR | active | `openjiuwen.02601004` | — | — |
| `openjiuwen.02601007` | canonical8 | 访问的静态资源不存在。 | `StudioError.STATIC_RESOURCE_NOT_EXIST` | config | manager | business | 404 | WARN | active | `openjiuwen.02601007` | — | — |
| `openjiuwen.02601008` | canonical8 | 资源操作失败，重复的资源名称，请检查资源名称。 | `StudioError.RESOURCE_OP_ERROR` | config | manager | business | 400 | WARN | active | `openjiuwen.02601008` | — | — |
| `openjiuwen.02601009` | canonical8 | 资源操作失败，branch_id {0} 与现有意图 {1} 冲突（分支名称：{2}）。 | `StudioError.RESOURCE_OP_ERROR_CONFLICT` | config | manager | business | 400 | WARN | active | `openjiuwen.02601009` | — | — |
| `openjiuwen.02601011` | canonical8 | 重复的资源嵌入或重排或OCR API模型名称，请检查API模型名称。 | `StudioError.RESOURCE_EMBEDDING_RERANK_API_NAME` | config | manager | business | 400 | WARN | active | `openjiuwen.02601011` | — | — |
| `openjiuwen.02601012` | canonical8 | 资源操作失败，模型名称无效！ | `StudioError.RESOURCE_MODEL_NAME_INVALID` | config | manager | business | 400 | WARN | active | `openjiuwen.02601012` | — | — |
| `openjiuwen.02601013` | canonical8 | 不支持的认证类型。 | `StudioError.RESOURCE_MODEL_UNSUPPORTED_AUTH_TYPE` | config | manager | business | 400 | WARN | active | `openjiuwen.02601013` | — | — |
| `openjiuwen.02601014` | canonical8 | "******" 不支持用于API密钥。 | `StudioError.RESOURCE_API_KEY_UNSUPPORTED` | config | manager | business | 400 | WARN | active | `openjiuwen.02601014` | — | — |
| `openjiuwen.02601015` | canonical8 | {0} 不支持用于IAM密码和IAM密钥。 | `StudioError.RESOURCE_IAM_KEY_UNSUPPORTED` | config | manager | business | 400 | WARN | active | `openjiuwen.02601015` | — | — |
| `openjiuwen.02601018` | canonical8 | 添加定时任务失败。 | `StudioError.ADD_QUARTZ_JOB_FAILED` | config | manager | business | 400 | WARN | active | `openjiuwen.02601018` | — | — |
| `openjiuwen.02601019` | canonical8 | 导入的意图包名称长度超过 {0} 字符 | `StudioError.IMPORT_BRANCH_NAME_EXCEED_LIMIT` | config | manager | business | 400 | WARN | active | `openjiuwen.02601019` | — | — |
| `openjiuwen.02601020` | canonical8 | 导入的意图样例名称超过 {0} 字符 | `StudioError.IMPORT_COMPLEX_INTENT_EXAMPLE_EXCEED_LIMIT` | config | manager | business | 400 | WARN | active | `openjiuwen.02601020` | — | — |
| `openjiuwen.02601021` | canonical8 | 导入的意图包名称 {0} 无效。 | `StudioError.IMPORT_COMPLEX_INTENT_NAME_INVALID` | config | manager | business | 400 | WARN | active | `openjiuwen.02601021` | — | — |
| `openjiuwen.02601022` | canonical8 | 导入的意图名称 {0} 无效。 | `StudioError.IMPORT_COMPLEX_INTENT_BRANCH_NAME_INVALID` | config | manager | business | 400 | WARN | active | `openjiuwen.02601022` | — | — |
| `openjiuwen.02601023` | canonical8 | 导入的意图样例 {0} 无效。 | `StudioError.IMPORT_COMPLEX_INTENT_EXAMPLE_INVALID` | config | manager | business | 400 | WARN | active | `openjiuwen.02601023` | — | — |
| `openjiuwen.02601024` | canonical8 | 意图样例重复。 | `StudioError.COMPLEX_INTENT_EXAMPLE_REPEATED` | config | manager | business | 400 | WARN | active | `openjiuwen.02601024` | — | — |
| `openjiuwen.02701002` | canonical8 | 系统错误, 添加数据集失败, 数据集名称: {0} | `StudioError.SYSTEM_ERROR_ADD_DATASET` | prompt_engineering | manager | business | 500 | ERROR | active | `openjiuwen.02701002` | — | — |
| `openjiuwen.02701003` | canonical8 | 删除数据集失败, 数据集ID: {0} | `StudioError.SYSTEM_ERROR_DELETE_DATASET_FAILED` | prompt_engineering | manager | business | 500 | ERROR | active | `openjiuwen.02701003` | — | — |
| `openjiuwen.02701004` | canonical8 | 获取OBS桶列表失败 | `StudioError.LIST_BUCKETS_GET_OBS_ERROR` | prompt_engineering | manager | business | 500 | ERROR | active | `openjiuwen.02701004` | — | — |
| `openjiuwen.02701005` | canonical8 | 获取OBS桶文件夹失败 | `StudioError.GET_OBS_BUCKET_ERROR` | prompt_engineering | manager | business | 500 | ERROR | active | `openjiuwen.02701005` | — | — |
| `openjiuwen.02701006` | canonical8 | JSON转换失败 | `StudioError.JSON_ENCODE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701006` | — | — |
| `openjiuwen.02701007` | canonical8 | JSON文件写入失败 | `StudioError.JSON_WRITE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701007` | — | — |
| `openjiuwen.02701008` | canonical8 | JSON解析失败 | `StudioError.JSON_PARSE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701008` | — | — |
| `openjiuwen.02701009` | canonical8 | 服务白名单校验失败 | `StudioError.SERVER_WHITELIST_CHECK_ERROR` | prompt_engineering | manager | security | 401 | WARN | active | `openjiuwen.02701009` | — | — |
| `openjiuwen.02701010` | canonical8 | 获取白名单状态响应失败 | `StudioError.GET_WHITELIST_RESPONSE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701010` | — | — |
| `openjiuwen.02701011` | canonical8 | 请求白名单服务异常 | `StudioError.REQUEST_MANAGER_SERVER_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701011` | — | — |
| `openjiuwen.02701012` | canonical8 | IAM Token信息缺失 | `StudioError.AUTH_TOKEN_INFO_MISSING` | prompt_engineering | manager | security | 401 | WARN | active | `openjiuwen.02701012` | — | — |
| `openjiuwen.02701013` | canonical8 | HTTP客户端初始化失败 | `StudioError.INIT_HTTP_CLIENT_ERROR` | prompt_engineering | manager | security | 401 | WARN | active | `openjiuwen.02701013` | — | — |
| `openjiuwen.02701014` | canonical8 | IAM服务响应失败 | `StudioError.GET_IAM_SERVER_RESPONSE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701014` | — | — |
| `openjiuwen.02701015` | canonical8 | 请求IAM服务异常 | `StudioError.IAM_SERVER_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701015` | — | — |
| `openjiuwen.02701016` | canonical8 | 空指针异常 | `StudioError.NULL_POINT_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701016` | — | — |
| `openjiuwen.02701017` | canonical8 | 查询模型列表失败 | `StudioError.QUERY_MODEL_LIST_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701017` | — | — |
| `openjiuwen.02701018` | canonical8 | 模型不存在 | `StudioError.PROMPT_MODEL_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701018` | — | — |
| `openjiuwen.02701019` | canonical8 | 参数校验失败 | `StudioError.ARGUMENT_VALID_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701019` | — | — |
| `openjiuwen.02701020` | canonical8 | 查询订单信息失败 | `StudioError.QUERY_ORDER_RESOURCES_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701020` | — | — |
| `openjiuwen.02701021` | canonical8 | 调用模型失败 | `StudioError.GET_NO_RESULT_FROM_LLM` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701021` | — | — |
| `openjiuwen.02701022` | canonical8 | 调用大模型接口失败 | `StudioError.OBTAIN_EMPTY_RESPONSE_FROM_LLM` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701022` | — | — |
| `openjiuwen.02701023` | canonical8 | 调用大模型接口失败 | `StudioError.CANT_OBTAIN_TEXT_FROM_LLM` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701023` | — | — |
| `openjiuwen.02701024` | canonical8 | 调用大模型接口超时 | `StudioError.CALL_LLM_TIMEOUT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701024` | — | — |
| `openjiuwen.02701025` | canonical8 | 大模型调用异常中断 | `StudioError.CALL_LLM_INTERRUPTED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701025` | — | — |
| `openjiuwen.02701026` | canonical8 | 大模型调用失败 | `StudioError.CALL_LLM_EXECUTION_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701026` | — | — |
| `openjiuwen.02701027` | canonical8 | OBS桶不存在 | `StudioError.OBS_ACCESS_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701027` | — | — |
| `openjiuwen.02701028` | canonical8 | OBS文件不存在 | `StudioError.OBS_FILE_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701028` | — | — |
| `openjiuwen.02701029` | canonical8 | OBS权限拒绝 | `StudioError.OBS_ACCESS_FAILED_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701029` | — | — |
| `openjiuwen.02701030` | canonical8 | OBS桶不存在 | `StudioError.OBS_BUCKET_DOES_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701030` | — | — |
| `openjiuwen.02701031` | canonical8 | OBS读取IO异常 | `StudioError.OBS_READ_IO_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701031` | — | — |
| `openjiuwen.02701032` | canonical8 | IAM Token校验失败 | `StudioError.IAM_SERVER_TOKEN_INVALID` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701032` | — | — |
| `openjiuwen.02701033` | canonical8 | 图片上传失败 | `StudioError.UPLOAD_FILE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701033` | — | — |
| `openjiuwen.02701034` | canonical8 | OBS文件上传失败 | `StudioError.UPLOAD_FILE_OBS_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701034` | — | — |
| `openjiuwen.02701035` | canonical8 | 文件上传失败 | `StudioError.UPLOAD_FILE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701035` | — | — |
| `openjiuwen.02701036` | canonical8 | 不支持的文件类型 | `StudioError.UPLOAD_FILE_TYPE_INVALID` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701036` | — | — |
| `openjiuwen.02701037` | canonical8 | 文件类型未定义 | `StudioError.FILE_TYPE_IS_UNDEFINED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701037` | — | — |
| `openjiuwen.02701038` | canonical8 | 文件内容类型不匹配 | `StudioError.FILE_CONTENT_TYPE_IS_UNMATCHED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701038` | — | — |
| `openjiuwen.02701039` | canonical8 | OBS客户端初始化失败 | `StudioError.OBS_RUNTIME_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701039` | — | — |
| `openjiuwen.02701040` | canonical8 | OBS服务不稳定 | `StudioError.OBS_SERVICE_NOT_STABLE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701040` | — | — |
| `openjiuwen.02701041` | canonical8 | Excel表头校验失败 | `StudioError.EXCEL_HEADER_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701041` | — | — |
| `openjiuwen.02701042` | canonical8 | 文件下载失败 | `StudioError.DOWNLOAD_FILE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701042` | — | — |
| `openjiuwen.02701043` | canonical8 | 文件名非法 | `StudioError.PE_ILLEGAL_FILE_NAME` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701043` | — | — |
| `openjiuwen.02701044` | canonical8 | 非法图片文件 | `StudioError.ILLEGAL_IMAGE_FILE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701044` | — | — |
| `openjiuwen.02701045` | canonical8 | 数据集文件格式错误 | `StudioError.DATASET_FILE_FORMAT_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701045` | — | — |
| `openjiuwen.02701046` | canonical8 | 数据集已存在 | `StudioError.DATASET_NAME_ALREADY_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701046` | — | — |
| `openjiuwen.02701047` | canonical8 | 数据集数量超配额 | `StudioError.DATASET_NUMBER_LIMIT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701047` | — | — |
| `openjiuwen.02701048` | canonical8 | 数据集被占用 | `StudioError.DATASET_IN_USING` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701048` | — | — |
| `openjiuwen.02701049` | canonical8 | 数据集内容长度超配额 | `StudioError.DATASET_CONTENT_LENGTH_LIMIT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701049` | — | — |
| `openjiuwen.02701050` | canonical8 | 读取数据集Excel失败 | `StudioError.READ_DATASET_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701050` | — | — |
| `openjiuwen.02701051` | canonical8 | 下载OBS文件失败 | `StudioError.OBS_DOWNLOAD_FILE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701051` | — | — |
| `openjiuwen.02701052` | canonical8 | ZIP文件体积过大 | `StudioError.ZIP_FILE_SIZE_LARGE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701052` | — | — |
| `openjiuwen.02701053` | canonical8 | 文件路径无效 | `StudioError.INVALID_FILE_PATH` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701053` | — | — |
| `openjiuwen.02701054` | canonical8 | 文件条目体积过大 | `StudioError.FILE_ENTRY_SIZE_LARGE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701054` | — | — |
| `openjiuwen.02701055` | canonical8 | 文件体积过大 | `StudioError.FILE_SIZE_TOO_LARGE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701055` | — | — |
| `openjiuwen.02701056` | canonical8 | ZIP炸弹检测失败 | `StudioError.OBS_FILE_CHECK_ZIP_BOMB` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701056` | — | — |
| `openjiuwen.02701057` | canonical8 | 读取数据集缓存异常 | `StudioError.READ_DATASET_CACHE_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701057` | — | — |
| `openjiuwen.02701058` | canonical8 | 数据集文件不存在 | `StudioError.DATASET_FILE_DOES_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701058` | — | — |
| `openjiuwen.02701059` | canonical8 | 数据集行号超出范围 | `StudioError.DATASET_ROW_NUM_LIMIT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701059` | — | — |
| `openjiuwen.02701060` | canonical8 | 数据集头行为空 | `StudioError.DATASET_HEADER_ROW_IS_NULL_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701060` | — | — |
| `openjiuwen.02701061` | canonical8 | 数据集存在空值行 | `StudioError.DATASET_VALUE_ROW_IS_NULL_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701061` | — | — |
| `openjiuwen.02701062` | canonical8 | 数据集表头数量超限 | `StudioError.DATASET_KEY_NUMBER_LIMIT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701062` | — | — |
| `openjiuwen.02701063` | canonical8 | 数据集表头存在空值 | `StudioError.DATASET_WITH_NULL_KEY_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701063` | — | — |
| `openjiuwen.02701064` | canonical8 | 数据集存在重复表头 | `StudioError.DATASET_WITH_SAME_KEY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701064` | — | — |
| `openjiuwen.02701065` | canonical8 | 下载变量数据集失败 | `StudioError.DOWNLOAD_VARIABLE_DATASET_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701065` | — | — |
| `openjiuwen.02701066` | canonical8 | 变量数据集为空 | `StudioError.DOWNLOAD_VARIABLE_DATASET_EMPTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701066` | — | — |
| `openjiuwen.02701067` | canonical8 | 数据集预期结果为空 | `StudioError.DATASET_RESULT_EMPTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701067` | — | — |
| `openjiuwen.02701068` | canonical8 | 任务不存在 | `StudioError.TASK_ID_IS_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701068` | — | — |
| `openjiuwen.02701069` | canonical8 | 删除任务失败 | `StudioError.FAILED_DELETE_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701069` | — | — |
| `openjiuwen.02701070` | canonical8 | 提示词工程名称重复 | `StudioError.TASK_NAME_IS_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701070` | — | — |
| `openjiuwen.02701071` | canonical8 | 创建任务失败 | `StudioError.FAILED_TO_CREATE_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701071` | — | — |
| `openjiuwen.02701072` | canonical8 | 删除提示词工程任务失败 | `StudioError.FAILED_TO_DELETE_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701072` | — | — |
| `openjiuwen.02701073` | canonical8 | 查询任务列表失败 | `StudioError.FAILED_TO_QUERY_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701073` | — | — |
| `openjiuwen.02701074` | canonical8 | 更新任务失败 | `StudioError.FAILED_TO_UPDATE_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701074` | — | — |
| `openjiuwen.02701075` | canonical8 | 提示词任务数量超配额 | `StudioError.TASK_EXCEEDS_QUOTA` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701075` | — | — |
| `openjiuwen.02701076` | canonical8 | 任务被占用无法删除 | `StudioError.TASK_HAVE_HAVE_RUNNING_EVALUATION_TASK` | prompt_engineering | manager | business | 500 | ERROR | active | `openjiuwen.02701076` | — | — |
| `openjiuwen.02701077` | canonical8 | 评估任务状态错误 | `StudioError.STATUS_ERROR` | prompt_engineering | manager | business | 500 | ERROR | active | `openjiuwen.02701077` | — | — |
| `openjiuwen.02701078` | canonical8 | 评估任务已存在 | `StudioError.EVALUATION_TASK_IS_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701078` | — | — |
| `openjiuwen.02701079` | canonical8 | 评估方法选择错误 | `StudioError.EVALUATION_METHOD_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701079` | — | — |
| `openjiuwen.02701080` | canonical8 | 评估任务不存在 | `StudioError.EVALUATION_TASK_IS_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701080` | — | — |
| `openjiuwen.02701081` | canonical8 | 查询评估任务信息失败 | `StudioError.FAILED_TO_QUERY_EVALUATION_TASK_INFO` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701081` | — | — |
| `openjiuwen.02701082` | canonical8 | 评估任务无法删除 | `StudioError.EVALUATION_TASK_RUNNING` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701082` | — | — |
| `openjiuwen.02701083` | canonical8 | 评估任务重试失败 | `StudioError.RETRY_EVALUATION_TASK_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701083` | — | — |
| `openjiuwen.02701084` | canonical8 | 更新评估任务失败 | `StudioError.EVALUATION_TASK_UPDATE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701084` | — | — |
| `openjiuwen.02701085` | canonical8 | 评估任务无法下载 | `StudioError.EXPORT_EVALUATION_RESULT_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701085` | — | — |
| `openjiuwen.02701086` | canonical8 | 导出预置提示词模板失败 | `StudioError.EXPORT_PROMPT_TEMPLATE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701086` | — | — |
| `openjiuwen.02701087` | canonical8 | 查询评估结果异常 | `StudioError.QUERY_EVALUATION_RESULT_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701087` | — | — |
| `openjiuwen.02701088` | canonical8 | 评估任务数量超配额 | `StudioError.EVALUATION_EXCEEDS_QUOTA` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701088` | — | — |
| `openjiuwen.02701089` | canonical8 | 导出文件失败 | `StudioError.EXPORT_EXCEL_VALIDATE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701089` | — | — |
| `openjiuwen.02701090` | canonical8 | 创建模板异常 | `StudioError.CREATE_TEMPLATE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701090` | — | — |
| `openjiuwen.02701091` | canonical8 | 更新模板异常 | `StudioError.UPDATE_TEMPLATE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701091` | — | — |
| `openjiuwen.02701092` | canonical8 | 查询模板失败 | `StudioError.QUERY_TEMPLATE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701092` | — | — |
| `openjiuwen.02701093` | canonical8 | 删除模板失败 | `StudioError.DELETE_TEMPLATE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701093` | — | — |
| `openjiuwen.02701094` | canonical8 | 变量处理失败 | `StudioError.HANDLE_VARIABLES_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701094` | — | — |
| `openjiuwen.02701095` | canonical8 | 提示词模板列表为空 | `StudioError.PROMPT_TEMPLATE_EMPTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701095` | — | — |
| `openjiuwen.02701096` | canonical8 | 候选模板数量超配额 | `StudioError.CANDIDATE_TEMPLATE_EXCEEDS_QUOTA` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701096` | — | — |
| `openjiuwen.02701097` | canonical8 | 变量重复 | `StudioError.VARIABLE_DUPLICATE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701097` | — | — |
| `openjiuwen.02701098` | canonical8 | 提示词被占用 | `StudioError.PROMPT_IN_USE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701098` | — | — |
| `openjiuwen.02701099` | canonical8 | 保存历史记录失败 | `StudioError.SAVE_HISTORY_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701099` | — | — |
| `openjiuwen.02701100` | canonical8 | 全局变量数量超配额 | `StudioError.VARIABLES_EXCEEDS_QUOTA` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701100` | — | — |
| `openjiuwen.02701101` | canonical8 | 数据不存在 | `StudioError.DATA_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701101` | — | — |
| `openjiuwen.02701102` | canonical8 | 候选模板名称重复 | `StudioError.DUPLICATE_PROMPT_NAME` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701102` | — | — |
| `openjiuwen.02701103` | canonical8 | 提示词名称重复 | `StudioError.NAME_IS_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701103` | — | — |
| `openjiuwen.02701104` | canonical8 | 模板数量超出{0}配额 | `StudioError.TEMPLATE_EXCEEDS_QUOTA` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701104` | — | — |
| `openjiuwen.02701105` | canonical8 | 预置模板操作权限不足 | `StudioError.AUTH_FAILED` | prompt_engineering | manager | security | 401 | WARN | active | `openjiuwen.02701105` | — | — |
| `openjiuwen.02701106` | canonical8 | 下载模板数量超配额 | `StudioError.DOWNLOAD_TEMPLATE_EXCEEDS_QUOTA` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701106` | — | — |
| `openjiuwen.02701107` | canonical8 | 模型温度参数非法 | `StudioError.TEMPLATE_MODEL_CONFIG_VALIDATE_TEMPERATURE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701107` | — | — |
| `openjiuwen.02701108` | canonical8 | 模型top_p参数非法 | `StudioError.TEMPLATE_MODEL_CONFIG_VALIDATE_TOP_P` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701108` | — | — |
| `openjiuwen.02701109` | canonical8 | 模型presence_penalty参数非法 | `StudioError.TEMPLATE_MODEL_CONFIG_VALIDATE_PRESENCE_PENALTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701109` | — | — |
| `openjiuwen.02701110` | canonical8 | 提示词ID不存在 | `StudioError.PROMPT_ID_IS_NOT_EXISTED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701110` | — | — |
| `openjiuwen.02701111` | canonical8 | 模板更新参数非法 | `StudioError.UPDATE_TEMPLATE_ERROR_PARAM` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701111` | — | — |
| `openjiuwen.02701112` | canonical8 | 提示词生成指令为空 | `StudioError.PROMPT_GENERATE_INSTRUCT_IS_EMPTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701112` | — | — |
| `openjiuwen.02701113` | canonical8 | 优化模板失败 | `StudioError.OPTIMIZE_TEMPLATE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701113` | — | — |
| `openjiuwen.02701114` | canonical8 | 删除优化模板失败 | `StudioError.OPTIMIZE_TEMPLATE_DELETE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701114` | — | — |
| `openjiuwen.02701115` | canonical8 | 访问优化模板服务失败 | `StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701115` | — | — |
| `openjiuwen.02701116` | canonical8 | 优化任务无法删除 | `StudioError.OPTIMIZATION_TASK_RUNNING` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701116` | — | — |
| `openjiuwen.02701117` | canonical8 | 优化任务已存在 | `StudioError.OPTIMIZATION_TASK_IS_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701117` | — | — |
| `openjiuwen.02701118` | canonical8 | 优化任务ID不存在 | `StudioError.OPTIMIZATION_TASK_ID_IS_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701118` | — | — |
| `openjiuwen.02701119` | canonical8 | 修改优化任务状态非法 | `StudioError.OPTIMIZATION_TASK_STATUS_IS_INVALIDATE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701119` | — | — |
| `openjiuwen.02701120` | canonical8 | 访问模板优化接口失败 | `StudioError.OPTIMIZATION_TASK_FROM_JIUWEN_SERVICE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701120` | — | — |
| `openjiuwen.02701121` | canonical8 | 创建优化任务响应为空 | `StudioError.CREATE_OPTIMIZATION_TASK_RESP_NULL` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701121` | — | — |
| `openjiuwen.02701122` | canonical8 | 删除远程优化任务失败 | `StudioError.DELETE_OPTIMIZATION_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701122` | — | — |
| `openjiuwen.02701123` | canonical8 | 获取优化任务进度失败 | `StudioError.GET_OPTIMIZATION_TASK` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701123` | — | — |
| `openjiuwen.02701124` | canonical8 | 优化任务状态码不存在 | `StudioError.OPTIMIZATION_TASK_STATUS_IS_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701124` | — | — |
| `openjiuwen.02701125` | canonical8 | 优化任务操作失败 | `StudioError.OPTIMIZATION_TASK_OPERATION_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701125` | — | — |
| `openjiuwen.02701126` | canonical8 | 模型类型码不存在 | `StudioError.MODEL_TYPE_IS_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701126` | — | — |
| `openjiuwen.02701127` | canonical8 | 优化任务已存在 | `StudioError.OPTIMIZATION_TASK_RUNNING_IS_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701127` | — | — |
| `openjiuwen.02701128` | canonical8 | 文件不存在 | `StudioError.FILE_DOES_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701128` | — | — |
| `openjiuwen.02701129` | canonical8 | 文件大小超出限制 | `StudioError.TASK_FILE_SIZE_EXCEED_LIMIT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701129` | — | — |
| `openjiuwen.02701130` | canonical8 | 分页参数无效 | `StudioError.LIMIT_OR_OFFSET_INVALID` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701130` | — | — |
| `openjiuwen.02701131` | canonical8 | 标签名称重复 | `StudioError.TAG_NAME_IS_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701131` | — | — |
| `openjiuwen.02701132` | canonical8 | 插入标签失败 | `StudioError.FAILED_TO_CREATE_TAG` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701132` | — | — |
| `openjiuwen.02701133` | canonical8 | 查询标签列表失败 | `StudioError.FAILED_TO_QUERY_TAG` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701133` | — | — |
| `openjiuwen.02701134` | canonical8 | 删除标签失败 | `StudioError.FAILED_TO_DELETE_TAG` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701134` | — | — |
| `openjiuwen.02701135` | canonical8 | 更新标签失败 | `StudioError.FAILED_TO_UPDATE_TAG` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701135` | — | — |
| `openjiuwen.02701136` | canonical8 | 行业名称重复 | `StudioError.INDUSTRY_NAME_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701136` | — | — |
| `openjiuwen.02701137` | canonical8 | 行业正在使用 | `StudioError.INDUSTRY_IN_USE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701137` | — | — |
| `openjiuwen.02701138` | canonical8 | 更新行业失败 | `StudioError.UPDATE_INDUSTRY_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701138` | — | — |
| `openjiuwen.02701139` | canonical8 | 查询行业失败 | `StudioError.QUERY_INDUSTRY_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701139` | — | — |
| `openjiuwen.02701140` | canonical8 | 插入行业失败 | `StudioError.CREATE_INDUSTRY_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701140` | — | — |
| `openjiuwen.02701141` | canonical8 | 行业ID不存在 | `StudioError.INDUSTRY_ID_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701141` | — | — |
| `openjiuwen.02701142` | canonical8 | 调用getUserModels失败 | `StudioError.MODEL_MANAGER_SERVICE_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701142` | — | — |
| `openjiuwen.02701143` | canonical8 | 获取用户模型列表失败 | `StudioError.FAILED_GET_USER_MODEL_LIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701143` | — | — |
| `openjiuwen.02701144` | canonical8 | 获取预设模型列表失败 | `StudioError.FAILED_GET_PRESET_MODEL_LIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701144` | — | — |
| `openjiuwen.02701145` | canonical8 | 查询列表失败 | `StudioError.QUERY_LIST_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701145` | — | — |
| `openjiuwen.02701146` | canonical8 | 模板ID为空 | `StudioError.TEMPLATE_ID_IS_EMPTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701146` | — | — |
| `openjiuwen.02701147` | canonical8 | 项目ID{0}不存在 | `StudioError.PROJECT_ID_NOT_FOUND` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701147` | — | — |
| `openjiuwen.02701148` | canonical8 | 工作空间ID{0}不存在 | `StudioError.WORKSPACE_ID_NOT_FOUND` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701148` | — | — |
| `openjiuwen.02701149` | canonical8 | 请求体不能为空 | `StudioError.REQUEST_BODY_NOT_EMPTY` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701149` | — | — |
| `openjiuwen.02701150` | canonical8 | 模型{0}状态校验失败 | `StudioError.MODEL_STATUS_ERROR` | prompt_engineering | manager | security | 403 | WARN | active | `openjiuwen.02701150` | — | — |
| `openjiuwen.02701151` | canonical8 | 复制超出上限 | `StudioError.COPY_LIMIT_EXCEEDED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701151` | — | — |
| `openjiuwen.02701152` | canonical8 | 上传数据失败 | `StudioError.UPLOAD_EVAL_DATA_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701152` | — | — |
| `openjiuwen.02701153` | canonical8 | 评估数据不存在 | `StudioError.PROMPT_EVAL_DATA_NOT_FOUND` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701153` | — | — |
| `openjiuwen.02701154` | canonical8 | 评估数据解析失败 | `StudioError.PROMPT_EVAL_DATA_FILE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701154` | — | — |
| `openjiuwen.02701158` | canonical8 | 查询优化任务失败！ | `StudioError.QUERY_OPTIMIZATION_TASK_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701158` | — | — |
| `openjiuwen.02701160` | canonical8 | 无该提示词优化任务评估结果！ | `StudioError.OPTIMIZATION_TASK_ITERATION_NOT_EXIST` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701160` | — | — |
| `openjiuwen.02701161` | canonical8 | 非草稿状态不能修改 | `StudioError.OPTIMIZATION_TASK_STATUS_IS_NOT_DRAFT` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701161` | — | — |
| `openjiuwen.02701162` | canonical8 | 优化任务正在运行，不能删除 | `StudioError.OPTIMIZATION_TASK_IS_RUNNING` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701162` | — | — |
| `openjiuwen.02701163` | canonical8 | 测评数据集文件超过大小限制 | `StudioError.PROMPT_DATA_SIZE_ERROR` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701163` | — | — |
| `openjiuwen.02701164` | canonical8 | 上传的json文件只能有1个 | `StudioError.UPLOAD_EVAL_DATA_NUM` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701164` | — | — |
| `openjiuwen.02701165` | canonical8 | 压缩包模板文件不存在 | `StudioError.TEMPLATE_FILE_NOT_FOUND` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701165` | — | — |
| `openjiuwen.02701166` | canonical8 | 下载模板失败 | `StudioError.DOWNLOAD_TEMPLATE_FAILED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701166` | — | — |
| `openjiuwen.02701167` | canonical8 | 定时任务注册失败 | `StudioError.SCHEDULER_REGISTER_EXCEPTION` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701167` | — | — |
| `openjiuwen.02701168` | canonical8 | Runtime优化任务还未创建 | `StudioError.OPTIMIZATION_TASK_NOT_CREATED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701168` | — | — |
| `openjiuwen.02701169` | canonical8 | 模板类型错误 | `StudioError.INVALID_PT_TYPE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701169` | — | — |
| `openjiuwen.02701170` | canonical8 | 变量类型错误 | `StudioError.INVALID_VARIABLES` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701170` | — | — |
| `openjiuwen.02701171` | canonical8 | 来源类型错误 | `StudioError.INVALID_SOURCE` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701171` | — | — |
| `openjiuwen.02701197` | canonical8 | 提示词模板导入数据超过限制 | `StudioError.PROMPT_TEMPLATE_IMPORT_NUM_EXCEED` | prompt_engineering | manager | business | 400 | WARN | active | `openjiuwen.02701197` | — | — |
| `openjiuwen.02801001` | canonical8 | 当前应用体验额度已用完 | `StudioError.CALL_ASSET_APP_EXCEED_FREE_TRIAL_TIMES` | asset | manager | business | 400 | WARN | active | `openjiuwen.02801001` | — | — |
| `openjiuwen.02901001` | canonical8 | 用户在空间下无权限执行此操作 | `StudioError.USER_NO_PERMISSION_DO_THIS` | workspace | manager | security | 403 | WARN | active | `openjiuwen.02901001` | — | — |
| `openjiuwen.02901002` | canonical8 | 工作空间名称重复，工作空间名称 {0} 已存在 | `StudioError.WORKSPACE_NAME_REPEAT` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901002` | — | — |
| `openjiuwen.02901003` | canonical8 | 成员{0}已存在于当前工作区中 | `StudioError.WORKSPACE_MEMBER_ALREADY_EXISTED` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901003` | — | — |
| `openjiuwen.02901004` | canonical8 | 成员{0}在当前工作空间中不存在 | `StudioError.WORKSPACE_MEMBER_NOT_EXIST` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901004` | — | — |
| `openjiuwen.02901005` | canonical8 | 成员角色无效,所有者角色不能被添加，请修改成员的角色 | `StudioError.INVALID_ROLE` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901005` | — | — |
| `openjiuwen.02901006` | canonical8 | 工作空间类型不是团队类型 | `StudioError.INVALID_WORKSPACE_TYPE` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901006` | — | — |
| `openjiuwen.02901007` | canonical8 | 有重复的团队空间成员 | `StudioError.REPEAT_MEMBER` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901007` | — | — |
| `openjiuwen.02901008` | canonical8 | 工作空间不存在 | `StudioError.WORKSPACE_NOT_EXISTED` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901008` | — | — |
| `openjiuwen.02901009` | canonical8 | 工作空间所有者在转让之前不能退出工作空间 | `StudioError.WORKSPACE_MEMBER_CAN_NOT_EXIT` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901009` | — | — |
| `openjiuwen.02901010` | canonical8 | 工作空间名称不合法，工作空间名称不能为空！ | `StudioError.WORKSPACE_NAME_INVALID` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901010` | — | — |
| `openjiuwen.02901011` | canonical8 | 工作空间名称不合法，工作空间名称超过限制 {0} | `StudioError.WORKSPACE_NAME_INVALID_LIMIT` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901011` | — | — |
| `openjiuwen.02901012` | canonical8 | 工作空间名称只能由中文、英文、数字、连字符、下划线、括号和感叹号组成 | `StudioError.WORKSPACE_NAME_INVALID_COMPOSED` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901012` | — | — |
| `openjiuwen.02901013` | canonical8 | 工作空间图标为空！ | `StudioError.WORKSPACE_ICON_INVALID` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901013` | — | — |
| `openjiuwen.02901014` | canonical8 | 工作空间图标文件类型无效！ | `StudioError.WORKSPACE_ICON_FILE_TYPE_INVALID` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901014` | — | — |
| `openjiuwen.02901015` | canonical8 | 工作空间图标大小超过限制 {0} KB | `StudioError.WORKSPACE_ICON_EXCEED_INVALID` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901015` | — | — |
| `openjiuwen.02901016` | canonical8 | 工作空间描述大小超过限制 {0} | `StudioError.WORKSPACE_DESCRIPTION_INVALID` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901016` | — | — |
| `openjiuwen.02901017` | canonical8 | 用户不是所要复制到的目标空间的成员 | `StudioError.USER_NOT_IN_TARGET_WORKSPACE` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901017` | — | — |
| `openjiuwen.02901018` | canonical8 | 关联空间的扩展参数不正确 | `StudioError.INVALID_EXTENSION_PARAM` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901018` | — | — |
| `openjiuwen.02901019` | canonical8 | 空间已经存在 | `StudioError.WORKSPACE_ALREADY_EXISTED` | workspace | manager | business | 400 | WARN | active | `openjiuwen.02901019` | — | — |
| `openjiuwen.03000000` | canonical8 | 系统内部错误 | `ErrorCode.SERVER_INTERNAL_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000000` | — | — |
| `openjiuwen.03000001` | canonical8 | 系统内部错误 | `ErrorCode.KOO_SEARCH_SERVICE_EXCEPTION` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000001` | — | — |
| `openjiuwen.03000002` | canonical8 | LakeSearch服务异常 | `ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000002` | — | — |
| `openjiuwen.03000003` | canonical8 | 操作失败 | `ErrorCode.OBS_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000003` | — | — |
| `openjiuwen.03000004` | canonical8 | 知识库配置信息错误 | `ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000004` | — | — |
| `openjiuwen.03000005` | canonical8 | API请求超时 | `ErrorCode.STREAM_INTERFACE_EXECUTE_TIMEOUT` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000005` | — | — |
| `openjiuwen.03000006` | canonical8 | 系统内部错误 | `ErrorCode.SSL_CONTEXT_BUILD_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000006` | — | — |
| `openjiuwen.03000007` | canonical8 | 系统内部错误 | `ErrorCode.IAM_CONTEXT_OBTAIN_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000007` | — | — |
| `openjiuwen.03000008` | canonical8 | 系统内部错误 | `ErrorCode.VIRTUAL_TOKEN_OBTAIN_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000008` | — | — |
| `openjiuwen.03000009` | canonical8 | 系统内部错误 | `ErrorCode.TOKEN_OBTAIN_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000009` | — | — |
| `openjiuwen.03000010` | canonical8 | 系统内部错误 | `ErrorCode.VIRTUAL_CREDENTIAL_OBTAIN_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000010` | — | — |
| `openjiuwen.03000011` | canonical8 | 系统内部错误 | `ErrorCode.IAM_TOKEN_READ_FILE_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000011` | — | — |
| `openjiuwen.03000012` | canonical8 | 系统内部错误 | `ErrorCode.IAM_TOKEN_CACHE_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000012` | — | — |
| `openjiuwen.03000013` | canonical8 | 系统内部错误 | `ErrorCode.IAM_TOKEN_ANALYZE_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000013` | — | — |
| `openjiuwen.03000014` | canonical8 | 系统内部错误 | `ErrorCode.IAM_TOKEN_GENERATE_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000014` | — | — |
| `openjiuwen.03000015` | canonical8 | 系统内部错误 | `ErrorCode.IAM_TOKEN_CONVERT_USER_TO_DOMAIN_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000015` | — | — |
| `openjiuwen.03000016` | canonical8 | 系统内部错误 | `ErrorCode.SYSTEM_PARAMS_CONFIG_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000016` | — | — |
| `openjiuwen.03000017` | canonical8 | 下载OBS对象失败 | `ErrorCode.OBS_EMPTY_FILE_CONTENT_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000017` | — | — |
| `openjiuwen.03000018` | canonical8 | 系统内部错误 | `ErrorCode.OBS_OBJECT_DOWNLOAD_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000018` | — | — |
| `openjiuwen.03000019` | canonical8 | 系统内部错误 | `ErrorCode.OBS_OBJECT_DELETE_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000019` | — | — |
| `openjiuwen.03000020` | canonical8 | 无法从OBS获取对象信息 | `ErrorCode.OBS_FILE_COUNT_OUT_LIMIT` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000020` | — | — |
| `openjiuwen.03000021` | canonical8 | KooSearch服务连接错误 | `ErrorCode.KOO_SEARCH_AUTH_MODE_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000021` | — | — |
| `openjiuwen.03000022` | canonical8 | LakeSearch服务连接错误 | `ErrorCode.LAKE_SEARCH_AUTH_MODE_ERROR` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000022` | — | — |
| `openjiuwen.03000023` | canonical8 | 系统内部错误 | `ErrorCode.FAILED_TO_FIND_DEFAULT_CONNECTION_INFO` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000023` | — | — |
| `openjiuwen.03000024` | canonical8 | 系统内部错误 | `ErrorCode.KNOWLEDGE_SOURCE_TYPE_IS_WRONG` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000024` | — | — |
| `openjiuwen.03000025` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_DEFAULT_CONNECTION_FAILED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000025` | — | — |
| `openjiuwen.03000026` | canonical8 | 知识库连接失败 | `ErrorCode.KNOWLEDGE_BASE_NOT_CONFIGURED` | knowledge_base | manager | system | 500 | ERROR | active | `openjiuwen.03000026` | — | — |
| `openjiuwen.03001000` | canonical8 | 参数校验失败 | `ErrorCode.METHOD_ARGUMENT_INVALID` | knowledge_base | manager | system | 400 | ERROR | active | `openjiuwen.03001000` | — | — |
| `openjiuwen.03001001` | canonical8 | 输入参数无效 | `ErrorCode.INVALID_PARAMETER` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001001` | — | — |
| `openjiuwen.03001002` | canonical8 | 操作失败 | `ErrorCode.NO_PERMISSION` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001002` | — | — |
| `openjiuwen.03001003` | canonical8 | 资源不存在 | `ErrorCode.RESOURCE_NOT_EXIST` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03001003` | — | — |
| `openjiuwen.03001004` | canonical8 | 操作失败 | `ErrorCode.RESOURCE_NAME_DUPLICATE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001004` | — | — |
| `openjiuwen.03001005` | canonical8 | 操作失败 | `ErrorCode.RESOURCE_ID_DUPLICATE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001005` | — | — |
| `openjiuwen.03001006` | canonical8 | 操作失败 | `ErrorCode.RESOURCE_CAPACITY_LIMIT_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001006` | — | — |
| `openjiuwen.03001007` | canonical8 | 操作失败 | `ErrorCode.ILLEGAL_FILE_NAME` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001007` | — | — |
| `openjiuwen.03001008` | canonical8 | 操作失败 | `ErrorCode.ILLEGAL_FILE_TYPE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001008` | — | — |
| `openjiuwen.03001009` | canonical8 | 操作失败 | `ErrorCode.FILE_SIZE_EXCEED_LIMIT` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001009` | — | — |
| `openjiuwen.03001010` | canonical8 | 图标名称无效 | `ErrorCode.INVALID_ICON_NAME` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001010` | — | — |
| `openjiuwen.03001011` | canonical8 | 获取许可项失败 | `ErrorCode.QUERY_KNOWLEDGE_BASE_LICENSE_ITEM_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03001011` | — | — |
| `openjiuwen.03001012` | canonical8 | 操作失败 | `ErrorCode.TASK_IS_ALREADY_RUNNING` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001012` | — | — |
| `openjiuwen.03001014` | canonical8 | 知识库不存在 | `ErrorCode.KNOWLEDGE_BASE_NOT_EXIST` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03001014` | — | — |
| `openjiuwen.03001015` | canonical8 | 知识片段规则不存在 | `ErrorCode.KNOWLEDGE_SEGMENT_RULE_NOT_EXIST` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03001015` | — | — |
| `openjiuwen.03001016` | canonical8 | 操作失败 | `ErrorCode.MEMORY_NOT_BELONG_AGENT` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001016` | — | — |
| `openjiuwen.03001017` | canonical8 | 操作失败 | `ErrorCode.MEMORY_NOT_BELONG_USER` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001017` | — | — |
| `openjiuwen.03001018` | canonical8 | 操作失败 | `ErrorCode.NO_PERMISSION_TO_UPLOAD_FILE` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001018` | — | — |
| `openjiuwen.03001019` | canonical8 | 操作失败 | `ErrorCode.NO_PERMISSION_TO_DELETE_FILE` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001019` | — | — |
| `openjiuwen.03001020` | canonical8 | 操作失败 | `ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001020` | — | — |
| `openjiuwen.03001021` | canonical8 | 操作失败 | `ErrorCode.EMPTY_FILE_CONTENT` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001021` | — | — |
| `openjiuwen.03001022` | canonical8 | 操作失败 | `ErrorCode.CREATE_FAQ_FILE_CHUNK_ERROR` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001022` | — | — |
| `openjiuwen.03001023` | canonical8 | 操作失败 | `ErrorCode.DELETE_FAQ_FILE_CHUNK_ERROR` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001023` | — | — |
| `openjiuwen.03001024` | canonical8 | 操作失败 | `ErrorCode.UPDATE_FAQ_FILE_CHUNK_ERROR` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001024` | — | — |
| `openjiuwen.03001025` | canonical8 | 操作失败 | `ErrorCode.FAQ_FILE_IS_EMPTY` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001025` | — | — |
| `openjiuwen.03001026` | canonical8 | 操作失败 | `ErrorCode.NO_PERMISSION_DELETE_KNOWLEDGE_REPO_FILE` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001026` | — | — |
| `openjiuwen.03001027` | canonical8 | 操作失败 | `ErrorCode.NO_PERMISSION_UPLOAD_KNOWLEDGE_REPO_FILE` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03001027` | — | — |
| `openjiuwen.03001028` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_OBS_DIRECTORY_DEPTH_OUT_OF_LIMIT` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001028` | — | — |
| `openjiuwen.03001029` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_OBS_CONFIG_NOT_EXIST` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03001029` | — | — |
| `openjiuwen.03001030` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_OBS_RESOURCE_LIST_FAILED` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03001030` | — | — |
| `openjiuwen.03001031` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_NUM_EXCEED_LIMIT` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001031` | — | — |
| `openjiuwen.03001032` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_NOT_FROM_ONE_SOURCE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001032` | — | — |
| `openjiuwen.03001033` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_CONNECTION_NOT_EXIST` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001033` | — | — |
| `openjiuwen.03001034` | canonical8 | 操作失败 | `ErrorCode.CREATE_RETRY_FILES_TASK_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001034` | — | — |
| `openjiuwen.03001035` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_CONNECTION_DELETE_FOR_OPEN` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001035` | — | — |
| `openjiuwen.03001036` | canonical8 | 外部知识库连接失败 | `ErrorCode.KNOWLEDGE_BASE_CONNECT_FAILED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001036` | — | — |
| `openjiuwen.03001037` | canonical8 | 未能获得连接能力或连接器类型 | `ErrorCode.FAIL_TO_GET_ABILITY` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03001037` | — | — |
| `openjiuwen.03002001` | canonical8 | 上传知识库文件失败 | `ErrorCode.FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002001` | — | — |
| `openjiuwen.03002002` | canonical8 | 操作失败 | `ErrorCode.INVALID_KNOWLEDGE_REPO_SOURCE` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002002` | — | — |
| `openjiuwen.03002003` | canonical8 | 操作失败 | `ErrorCode.SEARCH_MODEL_NOT_REGISTER` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002003` | — | — |
| `openjiuwen.03002004` | canonical8 | 操作失败 | `ErrorCode.SEARCH_MODEL_URL_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002004` | — | — |
| `openjiuwen.03002005` | canonical8 | 操作失败 | `ErrorCode.UNSUPPORTED_SEARCH_MODEL_TYPE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002005` | — | — |
| `openjiuwen.03002006` | canonical8 | 操作失败 | `ErrorCode.OCR_MODEL_ALREADY_EXIST` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002006` | — | — |
| `openjiuwen.03002007` | canonical8 | 操作失败 | `ErrorCode.UPLOAD_FILE_EXCEED_LIMITS` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002007` | — | — |
| `openjiuwen.03002008` | canonical8 | 操作失败 | `ErrorCode.ERROR_FILE_SIZE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002008` | — | — |
| `openjiuwen.03002010` | canonical8 | 无法在知识库【{0}】中检索 | `ErrorCode.KNOWLEDGE_CAN_NOT_RETRIEVE_FOR_DELETED_OR_CLOSED` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03002010` | — | — |
| `openjiuwen.03002012` | canonical8 | 操作失败 | `ErrorCode.UNSUPPORTED_OPERATION` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002012` | — | — |
| `openjiuwen.03002013` | canonical8 | 操作失败 | `ErrorCode.ICON_OBTAIN_FAILED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002013` | — | — |
| `openjiuwen.03002014` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_CAN_NOT_UPDATE_FOR_OPEN` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002014` | — | — |
| `openjiuwen.03002015` | canonical8 | 获取知识路由策略失败 | `ErrorCode.INVALID_KNOWLEDGE_ROUTER_STRATEGY` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002015` | — | — |
| `openjiuwen.03002016` | canonical8 | 获取检索合并策略失败 | `ErrorCode.INVALID_KNOWLEDGE_MERGING_STRATEGY` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002016` | — | — |
| `openjiuwen.03002017` | canonical8 | 操作失败 | `ErrorCode.FAILED_TO_FIND_DEFAULT_KNOWLEDGE_SOURCE` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002017` | — | — |
| `openjiuwen.03002018` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_CAN_NOT_CLOSE_FOR_PUBLISH` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002018` | — | — |
| `openjiuwen.03002019` | canonical8 | 操作失败 | `ErrorCode.FILE_NOT_EXIST_OR_EXPIRED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002019` | — | — |
| `openjiuwen.03002020` | canonical8 | 操作失败 | `ErrorCode.TAG_NAME_ALREADY_EXIST` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002020` | — | — |
| `openjiuwen.03002100` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_CONNECTION_ALREADY_EXIST` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002100` | — | — |
| `openjiuwen.03002101` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_CONNECTION_STATUS_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002101` | — | — |
| `openjiuwen.03002102` | canonical8 | 外部知识库连接错误 | `ErrorCode.CALL_EXTERNAL_KNOWLEDGE_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002102` | — | — |
| `openjiuwen.03002103` | canonical8 | 操作失败 | `ErrorCode.KNOWLEDGE_BASE_CREATE_FAILED` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002103` | — | — |
| `openjiuwen.03002104` | canonical8 | 查询第三方知识库错误 | `ErrorCode.QUERY_THIRD_PARTY_KNOWLEDGE_BASES_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002104` | — | — |
| `openjiuwen.03002105` | canonical8 | 查询第三方知识库标签错误。 | `ErrorCode.QUERY_THIRD_PARTY_KNOWLEDGE_BASES_TAGS_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002105` | — | — |
| `openjiuwen.03002106` | canonical8 | 操作失败 | `ErrorCode.EXTERNAL_KNOWLEDGE_BASE_NOT_SUPPORT_DOWNLOAD_FILE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002106` | — | — |
| `openjiuwen.03002107` | canonical8 | 操作失败 | `ErrorCode.THIRD_PARTY_KNOWLEDGE_CONNECTION_NOT_EXISTS` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03002107` | — | — |
| `openjiuwen.03002108` | canonical8 | Rag流连接错误 | `ErrorCode.RAG_FLOW_CONNECT_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002108` | — | — |
| `openjiuwen.03002109` | canonical8 | 服务桥接连接错误 | `ErrorCode.SERVICE_BRIDGE_CONNECT_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03002109` | — | — |
| `openjiuwen.03003001` | canonical8 | JSON格式错误 | `ErrorCode.JSON_FORMAT_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003001` | — | — |
| `openjiuwen.03003002` | canonical8 | 参数错误 | `ErrorCode.EMPTY_PARAM` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003002` | — | — |
| `openjiuwen.03003003` | canonical8 | URL参数解析异常 | `ErrorCode.URL_PARAM_PARSE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003003` | — | — |
| `openjiuwen.03003004` | canonical8 | URL路径非法 | `ErrorCode.URL_PATH_ILLEGAL` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003004` | — | — |
| `openjiuwen.03003005` | canonical8 | ES查询错误 | `ErrorCode.ES_QUERY_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003005` | — | — |
| `openjiuwen.03003006` | canonical8 | ES索引创建错误 | `ErrorCode.ES_INDEX_CREATE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003006` | — | — |
| `openjiuwen.03003007` | canonical8 | ES更新错误 | `ErrorCode.ES_UPDATE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003007` | — | — |
| `openjiuwen.03003008` | canonical8 | ES索引删除错误 | `ErrorCode.ES_INDEX_DELETE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003008` | — | — |
| `openjiuwen.03003009` | canonical8 | ES批量删除错误 | `ErrorCode.ES_BATCH_DELETE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003009` | — | — |
| `openjiuwen.03003010` | canonical8 | ES批量创建索引错误 | `ErrorCode.ES_INDEX_BATCH_CREATE_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003010` | — | — |
| `openjiuwen.03003011` | canonical8 | ES文档删除错误 | `ErrorCode.ES_DELETE_DOC_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003011` | — | — |
| `openjiuwen.03003012` | canonical8 | ES文档更新错误 | `ErrorCode.ES_UPDATE_DOC_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003012` | — | — |
| `openjiuwen.03003013` | canonical8 | ES批量操作错误 | `ErrorCode.ES_BATCH_OPERATION_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003013` | — | — |
| `openjiuwen.03003014` | canonical8 | 连接ES失败 | `ErrorCode.ES_CONNECT_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003014` | — | — |
| `openjiuwen.03003015` | canonical8 | ES索引配置更新错误 | `ErrorCode.ES_UPDATE_INDEX_CONFIG_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003015` | — | — |
| `openjiuwen.03003016` | canonical8 | 盘古NLP模型调用错误 | `ErrorCode.AGENT_BUILDER_NLP_CALL_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003016` | — | — |
| `openjiuwen.03003017` | canonical8 | 多轮重写服务调用错误 | `ErrorCode.MULTI_TURN_REWRITE_CALL_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003017` | — | — |
| `openjiuwen.03003018` | canonical8 | 文档解析服务调用错误 | `ErrorCode.DOC_PARSE_CALL_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003018` | — | — |
| `openjiuwen.03003019` | canonical8 | 知识库操作失败 | `ErrorCode.FILE_NOT_FOUND` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03003019` | — | — |
| `openjiuwen.03003020` | canonical8 | 读取文件内容失败 | `ErrorCode.FILE_READ_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003020` | — | — |
| `openjiuwen.03003021` | canonical8 | 文件信息数据库写入错误 | `ErrorCode.FILE_INFO_DB_WRITE_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03003021` | — | — |
| `openjiuwen.03003022` | canonical8 | 上传OBS错误 | `ErrorCode.OBS_UPLOAD_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03003022` | — | — |
| `openjiuwen.03003023` | canonical8 | JSON处理错误 | `ErrorCode.JSON_PROCESS_ERROR` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003023` | — | — |
| `openjiuwen.03003024` | canonical8 | 正在处理的文件无法删除 | `ErrorCode.FILE_PROCESSING_CANNOT_DELETE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003024` | — | — |
| `openjiuwen.03003025` | canonical8 | 数据库查询结果为空 | `ErrorCode.DB_QUERY_RESULT_EMPTY` | knowledge_base | manager | business | 404 | WARN | active | `openjiuwen.03003025` | — | — |
| `openjiuwen.03003026` | canonical8 | 数据库操作失败 | `ErrorCode.DB_OPERATION_FAILED` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03003026` | — | — |
| `openjiuwen.03003027` | canonical8 | 数据库更新错误 | `ErrorCode.DB_UPDATE_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03003027` | — | — |
| `openjiuwen.03003028` | canonical8 | 模型不可用 | `ErrorCode.MODEL_UNAVAILABLE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003028` | — | — |
| `openjiuwen.03003029` | canonical8 | 资源已存在 | `ErrorCode.RESOURCE_ALREADY_EXIST` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003029` | — | — |
| `openjiuwen.03003030` | canonical8 | JSON文件下载错误 | `ErrorCode.JSON_FILE_DOWNLOAD_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03003030` | — | — |
| `openjiuwen.03003031` | canonical8 | JSON文件写入错误 | `ErrorCode.JSON_FILE_WRITE_ERROR` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03003031` | — | — |
| `openjiuwen.03003032` | canonical8 | 验证知识库名称失败 | `ErrorCode.KNOWLEDGE_BASE_DUPLICATE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003032` | — | — |
| `openjiuwen.03003033` | canonical8 | 无法启用知识库 | `ErrorCode.KNOWLEDGE_BASE_EMPTY_CANNOT_ENABLE` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003033` | — | — |
| `openjiuwen.03003034` | canonical8 | 当前操作不允许 | `ErrorCode.KNOWLEDGE_BASE_CLOSED_OPERATION_FORBIDDEN` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03003034` | — | — |
| `openjiuwen.03003035` | canonical8 | 对话已过期 | `ErrorCode.CONVERSATION_EXPIRED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003035` | — | — |
| `openjiuwen.03003036` | canonical8 | 知识库更新失败 | `ErrorCode.KNOWLEDGE_BASE_UPDATE_FAILED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003036` | — | — |
| `openjiuwen.03003037` | canonical8 | 删除模型错误 | `ErrorCode.DELETE_MODEL_FAILED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003037` | — | — |
| `openjiuwen.03003038` | canonical8 | 操作失败 | `ErrorCode.ADDRESS_ILLEGAL` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003038` | — | — |
| `openjiuwen.03003039` | canonical8 | 操作失败 | `ErrorCode.IMAGE_NOT_EXIST_OR_EXPIRED` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03003039` | — | — |
| `openjiuwen.03004001` | canonical8 | 访问此接口失败 | `StudioError.NO_PERMISSION_ACCESS_INTERFACE` | knowledge_base | manager | security | 403 | WARN | active | `openjiuwen.03004001` | — | — |
| `openjiuwen.03004003` | canonical8 | 上传知识库文件失败 | `StudioError.FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03004003` | — | — |
| `openjiuwen.03004004` | canonical8 | 操作失败 | `StudioError.INVALID_KNOWLEDGE_REPO_SOURCE` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03004004` | — | — |
| `openjiuwen.03004013` | canonical8 | 在LakeSearch知识库{0}中创建FAQ失败 | `StudioError.LAKE_SEARCH_SERVICE_EXCEPTION_FAQ` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03004013` | — | — |
| `openjiuwen.03004015` | canonical8 | 批量删除LakeSearch知识库{0}中的FAQ失败 | `StudioError.LAKE_SEARCH_SERVICE_EXCEPTION_FAQ_DELETE_REPO` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03004015` | — | — |
| `openjiuwen.03004083` | canonical8 | 知识召回策略失败 | `StudioError.KNOW_RECALL_THRESHOLD_ILLEGAL` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03004083` | — | — |
| `openjiuwen.03004084` | canonical8 | 知识召回策略失败 | `StudioError.FAQ_THRESHOLD_ILLEGAL` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03004084` | — | — |
| `openjiuwen.03004085` | canonical8 | 操作失败 | `StudioError.KNOWLEDGE_REPO_TYPE_INCONSISTENT` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03004085` | — | — |
| `openjiuwen.03004086` | canonical8 | 操作失败 | `StudioError.INVALID_KNOWLEDGE_BASE_EXPANSION_PARAMETER` | knowledge_base | manager | business | 400 | WARN | active | `openjiuwen.03004086` | — | — |
| `openjiuwen.03004087` | canonical8 | 知识库不存在 | `StudioError.KNOWLEDGE_BASE_NOT_EXIST_IN_NODE` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03004087` | — | — |
| `openjiuwen.03004088` | canonical8 | 操作失败 | `StudioError.FREE_KNOWLEDGE_BASE_LIMIT_EXCEEDED` | knowledge_base | manager | business | 500 | ERROR | active | `openjiuwen.03004088` | — | — |
| `openjiuwen.03101001` | canonical8 | 查询VPC信息失败 | `StudioError.ENVIRONMENT_WITH_QUERY_VPC_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101001` | — | — |
| `openjiuwen.03101002` | canonical8 | 子网信息查询失败 | `StudioError.ENVIRONMENT_WITH_QUERY_SUBNET_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101002` | — | — |
| `openjiuwen.03101008` | canonical8 | 环境创建参数验证失败{0} | `StudioError.ENVIRONMENT_CREATE_PARAMETER_VERIFICATION_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101008` | — | — |
| `openjiuwen.03101014` | canonical8 | 环境创建失败 | `StudioError.CALLING_OPS_CREATE_ENVIRONMENT_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101014` | — | — |
| `openjiuwen.03101015` | canonical8 | 环境删除失败 | `StudioError.CALLING_OPS_DELETE_ENVIRONMENT_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101015` | — | — |
| `openjiuwen.03101016` | canonical8 | 查询环境失败 | `StudioError.CALLING_OPS_QUERY_ENVIRONMENT_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101016` | — | — |
| `openjiuwen.03101018` | canonical8 | 创建的环境数量达到系统最大限制 | `StudioError.ENVIRONMENT_LIMIT_EXCEEDED` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101018` | — | — |
| `openjiuwen.03101019` | canonical8 | 用户没有权限创建环境 | `StudioError.ENVIRONMENT_NOT_PERMISSION_CREATE` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101019` | — | — |
| `openjiuwen.03101020` | canonical8 | 当前空间下已经存在环境变量，无法创建 | `StudioError.ENVIRONMENT_VARIABLE_EXISTS` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101020` | — | — |
| `openjiuwen.03101021` | canonical8 | 环境变量参数不合法 | `StudioError.ENVIRONMENT_VARIABLE_NOT_EMPTY` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101021` | — | — |
| `openjiuwen.03101022` | canonical8 | 当前空间下不存在环境变量 | `StudioError.ENVIRONMENT_VARIABLE_NOT_EXISTS` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101022` | — | — |
| `openjiuwen.03101023` | canonical8 | 环境变量创建失败 | `StudioError.ENVIRONMENT_VARIABLE_CREATE_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101023` | — | — |
| `openjiuwen.03101024` | canonical8 | 环境变量删除失败 | `StudioError.ENVIRONMENT_VARIABLE_DELETE_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101024` | — | — |
| `openjiuwen.03101025` | canonical8 | 默认环境设置失败 | `StudioError.ENVIRONMENT_DEFAULT_SET_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101025` | — | — |
| `openjiuwen.03101026` | canonical8 | 环境信息修改失败 | `StudioError.ENVIRONMENT_MODIFY_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101026` | — | — |
| `openjiuwen.03101027` | canonical8 | 环境信息删除失败 | `StudioError.ENVIRONMENT_DELETE_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101027` | — | — |
| `openjiuwen.03101028` | canonical8 | 环境创建失败 | `StudioError.ENVIRONMENT_CREATE_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101028` | — | — |
| `openjiuwen.03101029` | canonical8 | 环境信息修改失败 | `StudioError.ENVIRONMENT_DEFAULT_NOT_SUPPORT` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101029` | — | — |
| `openjiuwen.03101030` | canonical8 | 工作流中使用的环境变量不合法 | `StudioError.USED_INVALID_ENVIRONMENT_VARIABLE` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101030` | — | — |
| `openjiuwen.03101031` | canonical8 | 环境信息导出失败 | `StudioError.EXPORT_ENVIRONMENT_VARIABLE_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101031` | — | — |
| `openjiuwen.03101032` | canonical8 | 环境信息导入失败 | `StudioError.IMPORT_ENVIRONMENT_VARIABLE_FAIL` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101032` | — | — |
| `openjiuwen.03101035` | canonical8 | 环境删除失败 | `StudioError.ENVIRONMENT_DELETE_NOT_SUPPORT` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101035` | — | — |
| `openjiuwen.03101036` | canonical8 | 单个环境下的环境变量数量达到系统最大限制 | `StudioError.ENVIRONMENT_VARIABLES_LIMIT_EXCEEDED` | environment_manager | manager | business | 500 | ERROR | active | `openjiuwen.03101036` | — | — |
| `openjiuwen.03201001` | canonical8 | License保存失败 | `StudioError.LICENSE_UNSAVED` | license | manager | business | 500 | ERROR | active | `openjiuwen.03201001` | — | — |
| `openjiuwen.03201002` | canonical8 | License缺失 | `StudioError.LICENSE_MISSING` | license | manager | business | 500 | ERROR | active | `openjiuwen.03201002` | — | — |
| `openjiuwen.03201003` | canonical8 | License无效或者超期 | `StudioError.LICENSE_INVALID` | license | manager | business | 500 | ERROR | active | `openjiuwen.03201003` | — | — |
| `openjiuwen.03201004` | canonical8 | 资源使用超过上限 | `StudioError.LICENSE_EXCEED` | license | manager | business | 500 | ERROR | active | `openjiuwen.03201004` | — | — |
| `openjiuwen.03201005` | canonical8 | 获取Pod资源失败 | `StudioError.LICENSE_PODS_ERROR` | license | manager | business | 500 | ERROR | active | `openjiuwen.03201005` | — | — |
| `openjiuwen.03201006` | canonical8 | 从itep获取license资源失败 | `StudioError.LICENSE_GET_RESOURCE_ERROR` | license | manager | business | 500 | ERROR | active | `openjiuwen.03201006` | — | — |
| `openjiuwen.03401001` | canonical8 | 主题定义重复 | `StudioError.PROFILE_TOPIC_DUPLICATE` | memory | manager | business | 400 | WARN | active | `openjiuwen.03401001` | — | — |
| `openjiuwen.03401002` | canonical8 | 主题下缺少标签 | `StudioError.EMPTY_TOPIC` | memory | manager | business | 400 | WARN | active | `openjiuwen.03401002` | — | — |
| `openjiuwen.03401003` | canonical8 | 标签定义重复 | `StudioError.PROFILE_TAG_DUPLICATE` | memory | manager | business | 400 | WARN | active | `openjiuwen.03401003` | — | — |
| `openjiuwen.03401004` | canonical8 | 记忆库不存在 | `StudioError.MEMORY_REPO_NOT_EXIST` | memory | manager | business | 400 | WARN | active | `openjiuwen.03401004` | — | — |
| `openjiuwen.03401005` | canonical8 | 智能体不支持记忆库 | `StudioError.AGENT_TYPE_MEMORY_REPO_NOT_SUPPORT` | memory | manager | business | 400 | WARN | active | `openjiuwen.03401005` | — | — |
| `openjiuwen.03701001` | canonical8 | 高代码智能体不存在。 | `StudioError.CODE_AGENT_NOT_EXIST` | code_agent | manager | business | 404 | WARN | active | `openjiuwen.03701001` | — | — |
| `openjiuwen.03701002` | canonical8 | 高代码智能体名称已存在。 | `StudioError.CODE_AGENT_NAME_EXIST` | code_agent | manager | business | 400 | WARN | active | `openjiuwen.03701002` | — | — |
| `openjiuwen.03701003` | canonical8 | 智能生成名称和描述失败。 | `StudioError.GENERATE_NAME_AND_DESCRIPTION_FAILED` | code_agent | manager | business | 400 | WARN | active | `openjiuwen.03701003` | — | — |
| `openjiuwen.03701004` | canonical8 | 删除Session失败。 | `StudioError.DELETE_SESSION_FAILED` | code_agent | manager | business | 400 | WARN | active | `openjiuwen.03701004` | — | — |

## 4. 未登记边界

以下内容不在本初版目录中：重复或跨服务冲突定义、Owner i18n 不完整定义、非 4xx/5xx 错误状态、未冻结号段，以及尚未证明精确对外值和消费者的 legacy 候选。已经发布链路证明的 `openjiuwen.121007` 作为 `legacy_other` 例外登记。

其余候选必须先按基线评审记录完成处置，不得直接复制进 Manifest，也不得据此认定为可对外复用的错误码。
