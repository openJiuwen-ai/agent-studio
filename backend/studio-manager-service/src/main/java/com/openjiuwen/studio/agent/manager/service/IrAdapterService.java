/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.FAQ_THRESHOLD;
import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.NEED_EXTRAS_FAQ_SEARCH;
import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.RECALL_THRESHOLD;
import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.RETRIEVE_IMAGE;
import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.SEARCH_MODE;
import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.SHOW_SOURCE;
import static com.openjiuwen.studio.agent.common.constant.Constants.KnowledgeBase.TOP_K;
import static com.openjiuwen.studio.agent.common.constant.Constants.TOOL_USE;
import static com.openjiuwen.studio.agent.common.constant.Constants.Workflow.ENABLED;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.MCP_AUTH_TYPE.IAM_TOKEN;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.MCP_AUTH_TYPE.USE_IAM_TOKEN;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.MEMORY;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.MEMORY_REPO_ID;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.ModelParam.DEFAULT_MODEL;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.QUERY;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.TOOL;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.WORKFLOW;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.Workflow.MODEL;
import static com.openjiuwen.studio.agent.manager.utils.CommonUtil.parseMcpConfigHeaderInfo;
import static com.openjiuwen.studio.agent.agentbase.converter.KbConnectionConverter.DEFAULT_CONNECTION_ID;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONException;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.enums.CredentialType;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.TypeEnum;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.bo.SkillIrInfo;
import com.openjiuwen.studio.agent.manager.bo.WorkflowNodeInfo;
import com.openjiuwen.studio.agent.manager.bo.WorkflowParallelEndNode;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.PromptPath;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentVariable;
import com.openjiuwen.studio.agent.manager.dto.Extension;
import com.openjiuwen.studio.agent.manager.dto.Guideline;
import com.openjiuwen.studio.agent.manager.dto.InputVariable;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRepoReference;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRetrievePolicy;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolEntity;
import com.openjiuwen.studio.agent.manager.dto.MemoryConfigIR;
import com.openjiuwen.studio.agent.manager.dto.MemoryUserProfileExtractConfigIR;
import com.openjiuwen.studio.agent.manager.dto.MemoryUserProfileIR;
import com.openjiuwen.studio.agent.manager.dto.MemoryUserProfileTagInfoIR;
import com.openjiuwen.studio.agent.manager.dto.MemoryUserProfileTopicInfoIR;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.Scene;
import com.openjiuwen.studio.agent.manager.dto.ToolCredential;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.ToolSkills;
import com.openjiuwen.studio.agent.manager.dto.UserProfileMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.UserProfileTagInfo;
import com.openjiuwen.studio.agent.manager.dto.UserProfileTopicInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVOErrors;
import com.openjiuwen.studio.agent.manager.dto.plugin.KnowledgeReqIrBody;
import com.openjiuwen.studio.agent.manager.dto.plugin.ResourceParam;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.ir.ConversationInputVariable;
import com.openjiuwen.studio.agent.manager.entity.ir.ConversationVariable;
import com.openjiuwen.studio.agent.manager.entity.ir.IrContext;
import com.openjiuwen.studio.agent.manager.enums.JsonSchemaType;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolCredentialMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.models.knowledge.BoolQueryNode;
import com.openjiuwen.studio.agent.manager.service.mcp.McpServiceManager;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.nodes.ParamExtractionNodeService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMappingService;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.IRUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.McpJsonUtils;
import com.openjiuwen.studio.agent.manager.utils.WorkflowUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt.IRAdapter;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt.PrePluginAuthServiceConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt.StartNodeAdapter;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthIamConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthServiceConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthUserConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import jakarta.annotation.Resource;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.apache.commons.lang3.math.NumberUtils;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.ObjectUtils;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Function;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;

/**
 * IR转换服务
 *
 */
@Slf4j
@Service
public class IrAdapterService {
    /**
     * STREAM
     */
    public static final String STREAMING = "streaming";

    /**
     * ID
     */
    private static final String ID = "id";

    /**
     * 插件鉴权字段
     */
    private static final String AUTH = "auth";


    /**
     * 参数名称
     */
    private static final String NAME = "name";

    /**
     * 参数描述
     */
    private static final String DESCRIPTION = "description";

    /**
     * 插件Url
     */
    private static final String URL = "url";

    /**
     * 插件Url对应类型
     */
    private static final String URL_TYPE = "string";

    /**
     * 插件节点请求方法
     */
    private static final String METHOD = "method";

    /**
     * MCP可使用的工具
     */
    private static final String MCP_CHOOSE_TOOLS = "mcp_choose_tools";

    /**
     * 参数类型
     */
    private static final String TYPE = "type";

    /**
     * 插件额外header字段
     */
    private static final String HEADERS = "headers";

    /**
     * 插件参数字段
     */
    private static final String ARGUMENTS = "arguments";

    /**
     * file类型前缀
     */
    private static final String FILE_TYPE = "file/";

    /**
     * 插件返回值字段
     */
    private static final String RESPONSE = "response";

    /**
     * 提问器默认值
     */
    private static final String DEFAULT_VALUE = "default_value";

    /**
     * 参数是否必选
     */
    private static final String REQUIRED = "required";

    /**
     * 校验开关
     */
    private static final String VALIDATED = "validated";

    /**
     * 校验类型
     */
    private static final String VALIDATE_TYPE = "validateType";

    /**
     * 校验规则
     */
    private static final String VALIDATE_RULE = "validateRule";

    /**
     * 对接九问参数
     */
    private static final String ACTUAL_TYPE = "actualType";

    /**
     * 插件依赖
     */
    private static final String PLUGIN_DEPENDENCY = "pluginDependency";

    /**
     * 插件凭证类型
     */
    private static final String CREDENTIAL_TYPE = "credential_type";

    /**
     * 插件凭证所有者
     */
    private static final String CREDENTIAL_OWNER_ID = "credential_owner_id";

    /**
     * 参数相关修饰字段
     */
    private static final String PARAMS_WRAPPER = "paramsWrapper";

    /**
     * 参数相关修饰字段
     */
    private static final String HOOK_FUNCTION = "hook_function";

    /**
     * 插件输入结构字段
     */
    private static final String INPUT_LIST = "inputList";

    /**
     * 插件输出结构字段
     */
    private static final String OUTPUT_LIST = "outputList";

    /**
     * mcp默认VALIDATE_TYPE类型
     */
    private static final String MCP_VALIDATE_TYPE = "CHAR";

    /**
     * mcp默认YPE类型
     */
    private static final String MCP_TYPE = "string";

    /**
     * mcp默认YPE类型
     */
    private static final String MCP_METHOD = "Headers";

    /**
     * ir路径
     */
    private static final String IR_PATH = "ir_path";

    /**
     * 工作流参数结构体定义字段
     */
    private static final String SCHEMA = "schema";

    /**
     * 默认开始节点id
     */
    private static final String INPUT_KEY = "node_start";

    /**
     * 默认结束节点id
     */
    private static final String OUTPUT_KEY = "node_end";

    /**
     * 知识库相关信息键值
     */
    private static final String REPOS = "repos";

    /**
     * 知识库检索标签普通检索配置
     */
    private static final String COMMON_TAGS = "common_tags";

    /**
     * 知识库检索标签普通检索配置
     */
    private static final String ADVANCED_TAGS = "advanced_tags";

    /**
     * 并行生成id常量
     */
    private static final int PARALLEL_RANDOM_NUM = 16;

    /**
     * 开始
     */
    private static final String INPUT = "input";

    /**
     * 记忆变量开关
     */
    private static final String LONG_MEMORY_ENABLED = "long_memory_enabled";

    /**
     * 全局配置开场白
     */
    private static final String PROLOGUE = "prologue";

    private static final String PLAN_EXECUTE = "PlanExecute";

    /**
     * mcp npx/uvx
     */
    private static final String STDIO = "stdio";

    /**
     * agent默认最大迭代深度
     */
    @Value("${agent.max-iteration:15}")
    private int maxIteration;

    /**
     * DR最大章节数
     */
    @Value("${agent.deepresearch-character:10}")
    private int outlinerMaxSectionNum;

    /**
     * 默认值最大长度
     */
    @Value("${controller.default-value-max-length}")
    private int maxDefaultValueLength;

    @Value("${asset.free.trial-quota-limit:10}")
    private int pluginMaxFreeTrialTimes;

    private static final String PLUGIN_FREE_TRIAL_USAGE_QUOTA_RW_LOCK_FORMAT
            = "agent.manager.asset.plugin.free.trial.usage.quota.rw.lock.asset_%s.month_%d.domain_%s.lock";

    private static final String PLUGIN_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT
            = "agent.manager.asset.plugin.free.trial.usage.quota.asset_%s.month_%d.domain_%s";


    /**
     * 异常情况下正常分支
     */
    private static final String NORMAL_BRANCH = "@@branch_0";

    /**
     * 异常分支
     */
    private static final String EXCEPTION_BRANCH = "@@branch_1";

    /**
     * 大模型节点深度思考开关
     */
    private static final String ENABLE_THINKING_ENABLED = "enabled";

    private static final String ENABLE_THINKING_DISABLED = "disabled";

    /**
     * 参数可见性
     */
    private static final String VISIBLE = "visible";

    /**
     * 输入参数
     */
    private static final String INPUT_PARAMETERS = "inputParameters";

    /**
     * 用户输入参数
     */
    private static final String INPUT_PARAMETERS_TYPE = "input_ref";

    /**
     * 记忆变量参数
     */
    private static final String MEMORY_PARAMETERS_TYPE = "mem_ref";

    /**
     * 引用变量类型
     */
    private static final String REF_PARAMETERS_TYPE = "ref";

    /**
     * deepresearch info_collector_search_method 字段变量
     */
    private static final String ALL = "all";

    private static final String LOCAL = "local";

    private static final String WEB = "web";

    @Value("${workflow.version}")
    private String workflowVersion;

    @Value("${workflow.parallel.interactive-node-count}")
    private int maxInteractiveNodeCount;

    @Value("${workflow.parallel.interactive-node-type}")
    private String interactiveNodeType;

    @Value("${workflow.parallel.branch-node-type}")
    private String branchNodeType;

    @Value("${workflow.exception-support-nodes}")
    private String workflowExceptionSupportNodes;

    @Value("${agent.ir-version}")
    private String agentIrVersion;

    @Value("${op.svc.project-id}")
    private String opProjectId;

    @Value("${knowledge.agent-response-ir}")
    private String knowledgeAgentResponseIr;

    @Value("${knowledge.workflow-response-ir}")
    private String knowledgeWorkflowResponseIr;

    @Getter
    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${agent-builder.agent-manager.domain:}")
    private String managerEndpoint;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private IPlugin pluginService;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private RelationManagementService relationManagementService;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Autowired
    private RedisClient redisClient;

    @Resource
    private McpServiceDao serviceDao;

    private List<String> interactiveNodeTypes;

    private List<String> branchNodeTypes;

    @Getter
    private List<String> exceptionNodeTypes;

    @Value("${knowledge.complex-intent-repo-id}")
    private String complexIntentRepoId;

    @Value("${tool.hook-function-path:/usr/local/lib/python3.11/site-packages/jiuwen/custom_auth/iam_auth.py:auth}")
    private String hookFunctionPath;

    @Value("${tool.mcp-hook-function-path:/usr/local/lib/python3.11/site-packages/jiuwen/custom_auth/mcp_auth.py:auth}")
    private String mcpHookFunctionPath;

    @Value("${mas.appcode}")
    private String masAppcode;

    @Value("${tool.preset-plugin-hook-function-path:/usr/local/lib/python3.11/site-packages/jiuwen/custom_auth/pre_plugin.py:auth}")
    private String prePluginHookFunctionPath;


    @Autowired
    private ToolCredentialMapper toolCredentialMapper;

    @Autowired
    private ParamExtractionNodeService paramExtractionNodeService;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private PluginBaseImpl pluginBaseImpl;

    @Autowired
    private WorkspaceMappingService workspaceMappingService;

    @Autowired
    private McpServiceManager mcpServiceManager;

    @Autowired
    private SkillMapper skillMapper;

    @Autowired
    private KnowledgeBaseServiceImpl knowledgeBaseService;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    private static void markEndBranchId(Map<String, WorkflowEdgeVO> edgeVoMap, WorkflowParallelEndNode parallelEndNode,
        String parallelBranchUuid) {
        for (String edgeId : parallelEndNode.getEdgeIds()) {
            WorkflowEdgeVO edgeVo = edgeVoMap.get(edgeId);
            String existId = edgeVo.getTargetBranchId();
            edgeVo.setTargetBranchId(StringUtils.isEmpty(existId) ? parallelBranchUuid
                : existId + CommonConstant.SEPARATOR + parallelBranchUuid);
        }
    }

    @PostConstruct
    private void init() {
        interactiveNodeTypes = Arrays.stream(interactiveNodeType.split(CommonConstant.SEPARATOR)).toList();
        branchNodeTypes = Arrays.stream(branchNodeType.split(CommonConstant.SEPARATOR)).toList();
        exceptionNodeTypes = Arrays.stream(workflowExceptionSupportNodes.split(CommonConstant.SEPARATOR)).toList();
    }

    /**
     * 工作流ir转换
     *
     * @param workflowVo 工作流信息
     * @param metadata 额外参数
     * @return 工作流IR
     */
    public Map<String, Object> adaptWorkflow(WorkflowVO workflowVo, Map<String, Object> metadata) {
        // 工作流全局变量中设置了记忆变量
        if (workflowVo.getConfigs() != null && workflowVo.getConfigs().get(MEMORY) != null) {
            addMemoryVariableParam(workflowVo);
        }
        WorkflowVO adaptedWorkflow = paramExtractionNodeService.adaptParamExtractionNode(workflowVo);

        IRAdapter irAdapter = new IRAdapter();
        Map<String, String> complexNodePair = parseComplexNodePair(workflowVo);
        Map<String, Object> result = new HashMap<>();
        result.put("workflowId", adaptedWorkflow.getId());
        result.put("workflowName", adaptedWorkflow.getName());
        result.put(DESCRIPTION, adaptedWorkflow.getDescription());
        result.put("workflowVersion", workflowVersion);
        result.put("schemaVersion", workflowVersion);
        result.put("configs", adaptConfigs(adaptedWorkflow.getConfigs()));
        result.put("components", irAdapter.adaptComponents(filterInnerNodes(adaptedWorkflow), complexNodePair));

        Map<String, String> reflection = new HashMap<>();
        adaptedWorkflow.getNodes().forEach(m -> reflection.put(m.getId(), m.getType()));

        // 添加并行标记位，如果添加失败，不做报错处理，在校验接口做强校验
        List<WorkflowEdgeVO> edges = addEdgeExceptionBranch(adaptedWorkflow, reflection);
        List<WorkflowNodeVO> nodes = addNodeExceptionBranch(adaptedWorkflow, reflection);
        addParallelTag(nodes, edges, null);
        result.put("connections", irAdapter.adaptConnections(edges, reflection, complexNodePair));
        result.put("metadata", metadata);
        return result;
    }

    /**
     * 根据异常标记给对应节点新增异常分支
     *
     * @param workflowVo 工作流信息
     * @param reflection id类型映射
     * @return 转换后的边
     */
    public List<WorkflowEdgeVO> addEdgeExceptionBranch(WorkflowVO workflowVo, Map<String, String> reflection) {
        // 深拷贝edges，对edges进行修改
        List<WorkflowEdgeVO> edges = new ArrayList<>(workflowVo.getEdges());
        Set<String> exceptionNormalNodeIds = new HashSet<>();
        Set<String> exceptionBranchNodeIds = new HashSet<>();
        for (WorkflowEdgeVO edge : edges) {
            // 删选开启异常分支的非分支节点
            if (!Boolean.TRUE.equals(edge.isExceptionBranch())) {
                continue;
            }
            // 记录包含异常分支的节点
            if (branchNodeTypes.contains(reflection.get(edge.getSource()))) {
                exceptionBranchNodeIds.add(edge.getSource());
            } else {
                exceptionNormalNodeIds.add(edge.getSource());
            }
        }
        // 非分支节点且包含异常情况的节点认为所有正常边都为branch_0分支
        edges.forEach(edge -> {
            if (exceptionNormalNodeIds.contains(edge.getSource())) {
                edge.setBranch(Boolean.TRUE.equals(edge.isExceptionBranch()) ? EXCEPTION_BRANCH : NORMAL_BRANCH);
                edge.setExceptionBranch(true);
            }
            if (exceptionBranchNodeIds.contains(edge.getSource()) && Boolean.TRUE.equals(edge.isExceptionBranch())) {
                edge.setBranch(EXCEPTION_BRANCH);
            }
        });
        return edges;
    }

    /**
     * 根据异常标记给对应节点新增异常分支
     *
     * @param workflowVo 工作流信息
     * @param reflection id类型映射
     * @return 转换后的节点
     */
    public List<WorkflowNodeVO> addNodeExceptionBranch(WorkflowVO workflowVo, Map<String, String> reflection) {
        // 深拷贝nodes，对nodes进行修改
        List<WorkflowNodeVO> nodes = new ArrayList<>(workflowVo.getNodes());
        Set<String> exceptionNormalNodeIds = new HashSet<>();
        Set<String> exceptionBranchNodeIds = new HashSet<>();
        for (WorkflowEdgeVO edge : workflowVo.getEdges()) {
            // 删选开启异常分支的非分支节点
            if (!Boolean.TRUE.equals(edge.isExceptionBranch())) {
                continue;
            }
            // 记录包含异常分支的节点
            if (branchNodeTypes.contains(reflection.get(edge.getSource()))) {
                exceptionBranchNodeIds.add(edge.getSource());
            } else {
                exceptionNormalNodeIds.add(edge.getSource());
            }
        }
        nodes.forEach(node -> {
            if (exceptionNormalNodeIds.contains(node.getId())) {
                List<WorkflowBranchVO> branches = new ArrayList<>();
                branches.add(new WorkflowBranchVO().setId(NORMAL_BRANCH));
                branches.add(new WorkflowBranchVO().setId(EXCEPTION_BRANCH));
                node.setBranches(branches);
            }
            if (exceptionBranchNodeIds.contains(node.getId())) {
                node.getBranches().add(new WorkflowBranchVO().setId(EXCEPTION_BRANCH));
            }
        });
        return nodes;
    }

    private Map<String, Object> adaptConfigs(Map<String, Object> configs) {
        Map<String, Object> irConfigs = new HashMap<>();
        if (configs == null) {
            return irConfigs;
        }
        // 替换模型配置
        if (configs.get(DEFAULT_MODEL) != null) {
            configs.put(MODEL, configs.get(DEFAULT_MODEL));
            new StartNodeAdapter().adaptModel(irConfigs, configs);
        }
        // 转存记忆变量
        if (configs.get(MEMORY) != null) {
            irConfigs.put(CommonConstant.Workflow.VARIABLES, configs.get(CommonConstant.Workflow.VARIABLES));
        }
        // 替换开场白
        if (configs.get(PROLOGUE) != null) {
            irConfigs.put(PROLOGUE, configs.get(PROLOGUE));
        }
        // 替换记忆开关
        if (configs.get(LONG_MEMORY_ENABLED) != null) {
            irConfigs.put(IRUtils.adaptKey(LONG_MEMORY_ENABLED), configs.get(LONG_MEMORY_ENABLED));
        }
        // 内容审核
        if (configs.get(Constants.Workflow.CONTENT_REVIEW) != null) {
            Map<String, Object> reviewObject = JsonUtils.objectToClass(configs.get(Constants.Workflow.CONTENT_REVIEW));
            if (reviewObject != null && reviewObject.get(ENABLED) != null && (boolean) reviewObject.get(ENABLED)) {
                irConfigs.put(Constants.Workflow.CONTENT_REVIEW, reviewObject);
            }
        }
        // 安全护栏
        if (configs.get(Constants.Workflow.SAFETY_BARRIER) != null) {
            Boolean isSafetyBarrier = JsonUtils.objectToClass(configs.get(Constants.Workflow.SAFETY_BARRIER));
            irConfigs.put(Constants.Workflow.SAFETY_BARRIER, isSafetyBarrier);
        }
        if (configs.get(Constants.Workflow.MEMORY_CONFIG) != null) {
            Map<String, String> agentMemoryConfig = JsonUtils.objectToClass(configs.get(Constants.Workflow.MEMORY_CONFIG));
            if (agentMemoryConfig != null && StringUtils.isNotBlank(agentMemoryConfig.get(MEMORY_REPO_ID))) {
                String repoId = agentMemoryConfig.get(MEMORY_REPO_ID);

                // Verify the memory repo still exists — skip if it was deleted
                MemoryRepoEntity repoEntity = null;
                try {
                    repoEntity = memoryRepoMapper.selectById(repoId);
                } catch (Exception e) {
                    org.slf4j.LoggerFactory.getLogger(IrAdapterService.class)
                        .warn("Failed to lookup memory repo {} during IR generation: {}", repoId, e.getMessage());
                }
                if (repoEntity == null) {
                    org.slf4j.LoggerFactory.getLogger(IrAdapterService.class)
                        .info("Memory repo {} not found, skipping memory config in IR", repoId);
                } else {
                    MemoryConfigIR memoryConfigIr = new MemoryConfigIR();
                    memoryConfigIr.setMemoryRepoId(repoId);
                    // 绑定记忆库即启用 LLM 节点的记忆注入。
                    memoryConfigIr.setEnable(true);

                    if (repoEntity.getConversationRound() != null || repoEntity.getTimeSpan() != null) {
                        MemoryConfigIR.ExtractConfig extractConfig = new MemoryConfigIR.ExtractConfig();
                        extractConfig.setMaxChatTurn(repoEntity.getConversationRound());
                        extractConfig.setTimeWindow(repoEntity.getTimeSpan());
                        memoryConfigIr.setExtractConfig(extractConfig);
                    }
                    if (repoEntity.getLongTermMemoryStrategies() != null && !repoEntity.getLongTermMemoryStrategies().isEmpty()) {
                        memoryConfigIr.setStrategies(repoEntity.getLongTermMemoryStrategies());
                    }
                    irConfigs.put(Constants.Workflow.MEMORY, memoryConfigIr);
                }
            }
        }
        return irConfigs;
    }

    private void addMemoryVariableParam(WorkflowVO workflowVo) {
        List<WorkflowNodeVO> nodes = workflowVo.getNodes();

        // 调用公共方法获取start节点并处理outputs
        WorkflowNodeVO start = getStartNodeWithOutputs(nodes, NodeType.START);

        // 创建memory
        WorkflowFieldVOValue value =
            new WorkflowFieldVOValue().setType(WorkflowFieldVOValue.TypeEnum.GENERATED).setContent("").setHint("");
        WorkflowFieldVO memoryOutput = new WorkflowFieldVO().setName(MEMORY)
            .setType(TypeEnum.OBJECT.toString())
            .setRequired(true)
            .setFieldType(INPUT)
            .setReflection(false)
            .setSource(WorkflowFieldVO.SourceEnum.PRE_DEFINED)
            .setValue(value);

        Map<String, Object> workflowConfigs = workflowVo.getConfigs();
        Object memoryLists = workflowConfigs.get(MEMORY);
        memoryOutput.setSchema(memoryLists);
        start.getOutputs().add(memoryOutput);
    }

    /**
     * 用户画像相关的IR记忆配置
     *
     * @param userProfileMemoryConfig userProfileMemoryConfig
     * @return MemoryUserProfileIR
     */
    private MemoryUserProfileIR userProfileToIr(UserProfileMemoryConfig userProfileMemoryConfig) {
        MemoryUserProfileIR memoryUserProfileIr = new MemoryUserProfileIR();
        memoryUserProfileIr.setEnable(Optional.ofNullable(userProfileMemoryConfig)
            .map(UserProfileMemoryConfig::isUserProfileEnable)
            .orElse(false));
        Optional.ofNullable(userProfileMemoryConfig)
            .map(UserProfileMemoryConfig::getTimeWindow)
            .ifPresent(extractConfig -> memoryUserProfileIr.setExtractConfig(
                new MemoryUserProfileExtractConfigIR().setMaxChatTurn(extractConfig.getConversationRound())
                    .setTimeWindow(extractConfig.getTimeSpan())));
        List<MemoryUserProfileTopicInfoIR> topicIrs = new ArrayList<>();
        List<UserProfileTopicInfo> topicConfigs = Optional.ofNullable(userProfileMemoryConfig)
            .map(UserProfileMemoryConfig::getTopics)
            .orElse(new ArrayList<>());
        for (UserProfileTopicInfo topicConfig : topicConfigs) {
            MemoryUserProfileTopicInfoIR topicIr = new MemoryUserProfileTopicInfoIR();
            topicIr.setName(topicConfig.getTopicName());
            List<UserProfileTagInfo> tagConfigs = Optional.of(topicConfig)
                .map(UserProfileTopicInfo::getTags)
                .orElse(Collections.emptyList());
            topicIr.setTags(tagConfigs.stream()
                .map(item -> new MemoryUserProfileTagInfoIR().setName(item.getTagName())
                    .setDescription(item.getTagDescription()))
                .toList());
            topicIrs.add(topicIr);
        }
        memoryUserProfileIr.setTopics(topicIrs);
        return memoryUserProfileIr;
    }

    /**
     * 获取起始节点并处理其输出字段
     *
     * @param nodes 节点列表
     * @param start 起始节点类型
     * @return 包含输出字段的起始节点
     * @throws AgentStudioException 如果未找到起始节点
     */
    public WorkflowNodeVO getStartNodeWithOutputs(List<WorkflowNodeVO> nodes, NodeType start) {
        // 获取start节点
        WorkflowNodeVO startNode =
            nodes.stream().filter(node -> Strings.CS.equals(start.getType(), node.getType())).findFirst().orElse(null);

        if (startNode == null) {
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }

        return startNode;
    }

    /**
     * 工作流添加并行标记
     *
     * @param workflowVo 工作流信息
     * @param freeNodeIds 游离节点id
     * @return 工作流校验结果
     */
    public List<WorkflowValidationVOErrors> addParallelTag(WorkflowVO workflowVo, Set<String> freeNodeIds) {
        return addParallelTag(workflowVo.getNodes(), workflowVo.getEdges(), freeNodeIds);
    }

    /**
     * 工作流添加并行标记
     *
     * @param workflowNodes 工作流节点信息
     * @param workflowEdges 工作流边信息
     * @param freeNodeIds 游离节点id
     * @return 工作流校验结果
     */
    public List<WorkflowValidationVOErrors> addParallelTag(List<WorkflowNodeVO> workflowNodes,
        List<WorkflowEdgeVO> workflowEdges, Set<String> freeNodeIds) {
        // 构建邻接表（每个节点连了哪些边，被哪些边链接，以及节点自身的属性）
        Map<String, WorkflowNodeVO> nodeMap =
            workflowNodes.stream().collect(Collectors.toMap(WorkflowNodeVO::getId, workflowNodeVO -> workflowNodeVO));

        // key为节点id或节点+分支id
        Map<String, WorkflowNodeInfo> adjacencyMap = new HashMap<>();

        // 如果id为节点+分支，WorkflowNodeInfo中的WorkflowNodeVO为节点本身（例如意图识别节点、判断节点）
        Map<String, WorkflowEdgeVO> edgeMap = new HashMap<>();

        // 通过邻接表的边，无法找到id为节点+分支的WorkflowNodeInfo
        for (WorkflowEdgeVO edge : workflowEdges) {
            // 跳过连接游离节点的边
            if (freeNodeIds != null && freeNodeIds.contains(edge.getSource())) {
                continue;
            }

            // 为边添加UUID
            if (StringUtils.isEmpty(edge.getId())) {
                edge.setId(UUID.randomUUID().toString());
            }
            edgeMap.put(edge.getId(), edge);

            // 将节点加入邻接表
            addAdjacency(edge, adjacencyMap, nodeMap, false);

            // 如果边包含branch，则将这个分支的连接点作为节点加入邻接表
            if (StringUtils.isNotEmpty(edge.getBranch())) {
                addAdjacency(edge, adjacencyMap, nodeMap, true);
            }
        }

        List<WorkflowValidationVOErrors> errors = new ArrayList<>();

        // 记录所有节点，可能包含游离节点
        for (WorkflowNodeInfo nodeInfo : adjacencyMap.values()) {
            // 除end节点和循环输出节点，所有节点（包括分支的锚点）必须有出去的边
            if (nodeInfo.getNode() != null && !Objects.equals(NodeType.END.getType(), nodeInfo.getNode().getType())
                && !Objects.equals(NodeType.LOOP_OUTPUT.getType(), nodeInfo.getNode().getType())) {
                if (nodeInfo.getEdgesOut().isEmpty()) {
                    errors.add(buildError(nodeInfo, i18nUtil.getMessage("workflow.validate.output")));
                }
            }
            // 除start节点和循环输入节点，所有节点（不包括分支的锚点）必须有进入的边
            if (nodeInfo.getNode() != null && !Objects.equals(NodeType.START.getType(), nodeInfo.getNode().getType())
                && !nodeInfo.isBranch() && !Objects.equals(NodeType.LOOP_INPUT.getType(),
                nodeInfo.getNode().getType())) {
                if (nodeInfo.getEdgesIn().isEmpty()) {
                    errors.add(buildError(nodeInfo, i18nUtil.getMessage("workflow.validate.input")));
                }
            }
        }

        // 从开始节点递归遍历
        Set<String> visited = new HashSet<>();
        try {
            addParallelTag(CommonConstant.Workflow.NODE_START, adjacencyMap, edgeMap, visited, errors);
        } catch (Exception e) {
            log.error("addParallelTag unexpected error {}", e);
            return errors;
        }
        logAddParallelTagResult(workflowEdges, errors);
        return errors;
    }

    private void addParallelTag(String nodeId, Map<String, WorkflowNodeInfo> adjacencyMap,
        Map<String, WorkflowEdgeVO> edgeVoMap, Set<String> visited, List<WorkflowValidationVOErrors> errors) {
        // 访问过或非并行开始节点，含子节点递归子节点后直接返回
        if (isNonParallelNode(nodeId, adjacencyMap, edgeVoMap, visited, errors)) {
            return;
        }

        WorkflowNodeInfo workflowNodeInfo = adjacencyMap.get(nodeId);
        List<WorkflowEdgeVO> edgesOut = workflowNodeInfo.getEdgesOut();

        // 为并行起点，添加tag
        printNodeInfo("parallel start", workflowNodeInfo);
        String parallelBranchUuid = IRUtils.generateRandomLetters(PARALLEL_RANDOM_NUM);

        // 寻找并行终点
        Map<String, WorkflowParallelEndNode> candidate = new HashMap<>();
        Set<Integer> allFlags = new HashSet<>();
        for (int i = 0; i < edgesOut.size(); i++) {
            WorkflowEdgeVO workflowEdgeVo = edgesOut.get(i);
            findParallelEnd(workflowEdgeVo, i, edgesOut.size(), adjacencyMap, candidate, nodeId);
            allFlags.add(i);
        }
        Set<String> parallelEndNodeIds = findParallelEndNodes(candidate, edgesOut, allFlags, adjacencyMap);

        // 未找到并行终点，报错
        if (parallelEndNodeIds.isEmpty()) {
            log.error("parallel end node not found");
            errors.add(buildError(workflowNodeInfo,
                i18nUtil.getMessage("workflow.validate.invalid.parallel") + workflowNodeInfo.getNode().getId()));
            return;
        }

        // 获取起点到每个终点之间（不包含起点和终点），包含的所有节点，并计算交互式节点的数量
        Map<String, WorkflowNodeInfo> nodesBetweenStartEnd = new HashMap<>();
        for (String parallelEndNodeId : parallelEndNodeIds) {
            for (WorkflowEdgeVO edgeVo : edgesOut) {
                walkToParallelEnd(edgeVo, parallelEndNodeId, adjacencyMap, nodesBetweenStartEnd);
            }
        }
        long interactiveNodeCount = nodesBetweenStartEnd.values().stream().filter(this::isInteractiveNode).count();

        // 交互式节点数量超过最大值
        if (interactiveNodeCount > maxInteractiveNodeCount) {
            log.warn("interactive node count = {}, exceed max interactive node count {}", interactiveNodeCount,
                maxInteractiveNodeCount);
            errors.add(buildError(workflowNodeInfo,
                i18nUtil.getMessage("workflow.validate.interactive") + maxInteractiveNodeCount + ")"));
            nodesBetweenStartEnd.values()
                .stream()
                .filter(this::isInteractiveNode)
                .forEach(interactiveNode -> errors
                    .add(buildError(interactiveNode, i18nUtil.getMessage("workflow.validate.interactive.branch"))));
            return;
        }

        // 标记并行终点
        for (WorkflowParallelEndNode parallelEndNode : candidate.values()) {
            Set<Integer> flags = parallelEndNode.getFlags();
            if (flags.size() > 1 && allFlags.containsAll(flags)) {
                markEndBranchId(edgeVoMap, parallelEndNode, parallelBranchUuid);
            }
        }

        for (WorkflowEdgeVO edge : edgesOut) {
            // 标记并行起点
            String existId = edge.getSourceBranchId();
            edge.setSourceBranchId(StringUtils.isEmpty(existId) ? parallelBranchUuid
                : existId + CommonConstant.SEPARATOR + parallelBranchUuid);

            // 每个并行的边继续递归
            addParallelTag(edge.getTarget(), adjacencyMap, edgeVoMap, visited, errors);
        }
    }

    private boolean isNonParallelNode(String nodeId, Map<String, WorkflowNodeInfo> adjacencyMap,
        Map<String, WorkflowEdgeVO> edgeVoMap, Set<String> visited, List<WorkflowValidationVOErrors> errors) {
        // 如果已经处理过，返回，避免环
        if (visited.contains(nodeId)) {
            return true;
        }
        visited.add(nodeId);
        WorkflowNodeInfo workflowNodeInfo = adjacencyMap.get(nodeId);
        List<WorkflowEdgeVO> edgesOut = workflowNodeInfo.getEdgesOut();

        // 结束节点
        if (edgesOut.isEmpty()) {
            return true;
        }

        // 分支节点（意图、判断等），每个分支算一个节点，递归执行
        if (isBranchNode(workflowNodeInfo)) {
            printNodeInfo("branch", workflowNodeInfo);
            for (WorkflowBranchVO branch : workflowNodeInfo.getNode().getBranches()) {
                addParallelTag(getBranchNodeId(nodeId, branch.getId()), adjacencyMap, edgeVoMap, visited, errors);
            }
            return true;
        }
        // 循环节点内，从LoopInput节点开始递归执行
        if (NodeType.LOOP.getType().equalsIgnoreCase(workflowNodeInfo.getNode().getType())) {
            printNodeInfo("loop", workflowNodeInfo);
            addParallelTag(nodeId + CommonConstant.LOOP_INPUT, adjacencyMap, edgeVoMap, visited, errors);
        }

        // 非分支节点，且只有一条边，为单节点，递归
        if (edgesOut.size() <= 1) {
            printNodeInfo("single", workflowNodeInfo);
            addParallelTag(edgesOut.get(0).getTarget(), adjacencyMap, edgeVoMap, visited, errors);
            return true;
        }
        return false;
    }

    private Set<String> findParallelEndNodes(Map<String, WorkflowParallelEndNode> candidate,
        List<WorkflowEdgeVO> edgesOut, Set<Integer> allFlags, Map<String, WorkflowNodeInfo> adjacencyMap) {
        Set<String> parallelEndNodeIds = new HashSet<>();
        for (WorkflowParallelEndNode parallelEndNode : candidate.values()) {
            Set<Integer> flags = parallelEndNode.getFlags();
            if (flags.size() == edgesOut.size()) {
                // 拿到所有边的token的节点，为并行终点
                parallelEndNodeIds.add(parallelEndNode.getNodeId());
                printNodeInfo("parallel end", adjacencyMap.get(parallelEndNode.getNodeId()));
            } else if (flags.size() > 1 && allFlags.containsAll(flags)) {
                // 拿到部分边的token的节点，为中继并行终点，也需要标记
                printNodeInfo("parallel relay", adjacencyMap.get(parallelEndNode.getNodeId()));
            }
        }
        return parallelEndNodeIds;
    }

    @NotNull
    private WorkflowValidationVOErrors buildError(WorkflowNodeInfo workflowNodeInfo, String reason) {
        WorkflowValidationVOErrors error = new WorkflowValidationVOErrors();
        WorkflowNodeVO node = workflowNodeInfo.getNode();
        error.setId(node.getId());
        error.setReason(reason);
        error.setType(node.getType());
        return error;
    }

    private void findParallelEnd(WorkflowEdgeVO workflowEdgeVo, Integer flag, int flagCount,
        Map<String, WorkflowNodeInfo> adjacencyMap, Map<String, WorkflowParallelEndNode> candidate,
        String currentNodeId) {
        String nodeId = workflowEdgeVo.getTarget();
        if (StringUtils.isEmpty(nodeId)) {
            return;
        }

        WorkflowNodeInfo workflowNodeInfo = adjacencyMap.get(nodeId);
        if (workflowNodeInfo == null) {
            return;
        }

        WorkflowParallelEndNode workflowParallelEndNode = candidate.get(nodeId);
        if (workflowParallelEndNode != null && workflowParallelEndNode.getFlags().contains(flag)) {
            // 如果已经被标记过了，不再递归
            workflowParallelEndNode.getEdgeIds().add(workflowEdgeVo.getId());
            return;
        }

        // 如找终点发现成环，中止寻找
        AtomicBoolean isCycle = new AtomicBoolean(false);
        workflowNodeInfo.getEdgesIn().forEach(edge -> {
            if (Strings.CS.equals(edge.getTarget(), currentNodeId)) {
                isCycle.set(true);
            }
        });
        if (isCycle.get()) {
            return;
        }

        // 入度大于1，标记为候选节点
        if (workflowNodeInfo.getEdgesIn().size() > 1) {
            if (workflowParallelEndNode == null) {
                workflowParallelEndNode = new WorkflowParallelEndNode();
                workflowParallelEndNode.setNodeId(nodeId);
                workflowParallelEndNode.getFlags().add(flag);
                workflowParallelEndNode.getEdgeIds().add(workflowEdgeVo.getId());

                candidate.put(nodeId, workflowParallelEndNode);
            } else {
                // 不包含标记，添加标记
                workflowParallelEndNode.getFlags().add(flag);
                workflowParallelEndNode.getEdgeIds().add(workflowEdgeVo.getId());

                // 标记齐全了，已经找到了结束点
                if (workflowParallelEndNode.getFlags().size() == flagCount) {
                    return;
                }
            }
        }

        // 继续寻找
        if (!workflowNodeInfo.getEdgesOut().isEmpty()) {
            // 如果为分支节点，每个路径需要独立寻找，即判断节点额不同分支不可能同时走，不同的分支为不同的图，当前暂时无法检测，可能会出现异常
            if (isBranchNode(workflowNodeInfo)) {
                log.warn("parallel branch contain branch node");
            }
            for (WorkflowEdgeVO edgeVo : workflowNodeInfo.getEdgesOut()) {
                findParallelEnd(edgeVo, flag, flagCount, adjacencyMap, candidate, currentNodeId);
            }
        }
    }

    private void walkToParallelEnd(WorkflowEdgeVO workflowEdgeVo, String parallelEndNodeId,
        Map<String, WorkflowNodeInfo> adjacencyMap, Map<String, WorkflowNodeInfo> nodes) {
        String nodeId = workflowEdgeVo.getTarget();
        if (StringUtils.isEmpty(nodeId)) {
            return;
        }

        // 已经遍历过或已经到达终点
        if (nodes.containsKey(nodeId) || nodeId.equals(parallelEndNodeId)) {
            return;
        }

        // 从该节点出发，无法到达parallelEndNodeId
        if (!canReach(nodeId, parallelEndNodeId, adjacencyMap)) {
            return;
        }

        // 添加到遍历过的集合
        WorkflowNodeInfo workflowNodeInfo = adjacencyMap.get(nodeId);
        if (workflowNodeInfo == null) {
            return;
        }
        nodes.put(nodeId, workflowNodeInfo);

        // 继续寻找
        if (!workflowNodeInfo.getEdgesOut().isEmpty()) {
            for (WorkflowEdgeVO edgeVo : workflowNodeInfo.getEdgesOut()) {
                walkToParallelEnd(edgeVo, parallelEndNodeId, adjacencyMap, nodes);
            }
        }
    }

    /**
     * 从edge出发，是否可达nodeId
     */
    private boolean canReach(String startNode, String endNode, Map<String, WorkflowNodeInfo> adjacencyMap) {
        HashSet<String> nodes = new HashSet<>();
        walkToEnd(startNode, endNode, adjacencyMap, nodes);
        return nodes.contains(endNode);
    }

    private void walkToEnd(String startNode, String endNode, Map<String, WorkflowNodeInfo> adjacencyMap,
        Set<String> nodes) {
        if (StringUtils.isEmpty(startNode)) {
            return;
        }

        // 已经遍历过或已经到达终点
        if (nodes.contains(startNode)) {
            return;
        }
        if (startNode.equals(endNode)) {
            nodes.add(endNode);
            return;
        }

        // 添加到遍历过的集合
        nodes.add(startNode);

        // 继续寻找
        WorkflowNodeInfo workflowNodeInfo = adjacencyMap.get(startNode);
        if (workflowNodeInfo == null) {
            return;
        }
        if (!workflowNodeInfo.getEdgesOut().isEmpty()) {
            for (WorkflowEdgeVO edgeVo : workflowNodeInfo.getEdgesOut()) {
                walkToEnd(edgeVo.getTarget(), endNode, adjacencyMap, nodes);
            }
        }
    }

    private void printNodeInfo(String type, WorkflowNodeInfo nodeInfo) {
        WorkflowNodeVO node = nodeInfo.getNode();
        log.debug("\n{} type={} name={}{}id={} edgeNum={}", type, node.getType(), node.getName(),
            nodeInfo.isBranch() ? "-anchor " : " ", node.getId(), nodeInfo.getEdgesOut().size());
    }

    private void addAdjacency(WorkflowEdgeVO edge, Map<String, WorkflowNodeInfo> adjacencyMap,
        Map<String, WorkflowNodeVO> nodeMap, boolean isBranch) {
        // 添加出去的边
        String sourceNodeId = isBranch ? getBranchNodeId(edge.getSource(), edge.getBranch()) : edge.getSource();
        WorkflowNodeInfo sourceNode = adjacencyMap.get(sourceNodeId);
        if (sourceNode == null) {
            sourceNode = new WorkflowNodeInfo();
            sourceNode.setNode(nodeMap.get(edge.getSource()));
            sourceNode.setBranch(isBranch);
            adjacencyMap.put(sourceNodeId, sourceNode);
        }
        sourceNode.getEdgesOut().add(edge);

        // 如果为分支节点，不需要添加进入的边
        if (isBranch) {
            return;
        }

        // 添加进入的边
        String targetNodeId = edge.getTarget();
        WorkflowNodeInfo targetNode = adjacencyMap.get(targetNodeId);
        if (targetNode == null) {
            targetNode = new WorkflowNodeInfo();
            targetNode.setNode(nodeMap.get(targetNodeId));
            adjacencyMap.put(targetNodeId, targetNode);
        }
        targetNode.getEdgesIn().add(edge);
    }

    private boolean isInteractiveNode(WorkflowNodeInfo nodeInfo) {
        String type = nodeInfo.getNode().getType();

        // 提问器、输入节点、子workflow当前认为是交互式节点
        for (String interactiveNodeType : interactiveNodeTypes) {
            if (interactiveNodeType.equals(type)) {
                // 任务型工作流为非交互节点
                if (isTaskWorkflow(nodeInfo)) {
                    return false;
                }
                return true;
            }
        }
        return false;
    }

    private boolean isTaskWorkflow(WorkflowNodeInfo nodeInfo) {
        String nodeType = nodeInfo.getNode().getType();

        // 如果是工作流节点
        if (NodeType.WORKFLOW.getType().equalsIgnoreCase(nodeType)) {
            Object type = nodeInfo.getNode().getConfigs().get("type");

            // 如果工作流类型是task类型
            return !ObjectUtils.isEmpty(type) && type.toString().equalsIgnoreCase(CommonConstant.Workflow.TASK);
        }
        return false;
    }

    private boolean isBranchNode(WorkflowNodeInfo nodeInfo) {
        // 如果是分支上的锚点，非分支节点本身
        if (nodeInfo.isBranch()) {
            return false;
        }

        String type = nodeInfo.getNode().getType();

        // 判断节点、意图识别节点当前认为是会产生分支的节点
        if (branchNodeTypes.contains(type)) {
            return true;
        }
        // 异常节点看作分支节点
        return !nodeInfo.getEdgesOut().isEmpty()
            && Boolean.TRUE.equals(nodeInfo.getEdgesOut().get(0).isExceptionBranch());
    }

    private String getBranchNodeId(String nodeId, String branchId) {
        return nodeId + "-" + branchId;
    }

    private List<WorkflowNodeVO> filterInnerNodes(WorkflowVO workflow) {
        List<WorkflowNodeVO> workflowNodes = new ArrayList<>();
        for (WorkflowNodeVO node : workflow.getNodes()) {
            NodeType nodeType = NodeType.fromType(node.getType());
            if (Objects.isNull(nodeType)) {
                workflowNodes.add(node);
                continue;
            }
            // 内部节点不参与实际判断
            if (nodeType.isInnerNode()) {
                continue;
            }
            workflowNodes.add(node);
        }
        return workflowNodes;
    }

    /**
     * 解析 workflow mcp ir 配置
     *
     * @param serverId mcp 服务 id
     * @param toolName mcp 工具名称
     * @param projectId project id
     * @param userId user id
     * @return 返回 mcp ir config
     */
    public Map<String, Object> parseMcpConfigForWorkflow(String serverId, String toolName, String projectId,
        String userId, String workspaceId) {
        McpServiceEntity serviceEntity =
            serviceDao.selectById(serverId, CommonUtil.getTenantId(), CommonUtil.getDeptCode(), workspaceId);
        if (Objects.isNull(serviceEntity)) {
            throw new AgentStudioException(StudioError.MCP_ADAPT_IR_FAILED, serverId);
        }
        McpServiceToolEntity serverTool = null;
        if (!Objects.isNull(toolName)) {
            // 适配数据加工节点转IR，预制的加工节点不预制工具信息，需要根据用户信息进行实时查询。
            if (Strings.CI.equals(serviceEntity.getVisibility(), "global")) {
                serviceEntity.setTools(mcpServiceManager.getMcpServiceToolList(serviceEntity));
            }
            serverTool = McpJsonUtils.parseToolFromString(serviceEntity.getTools(), serviceEntity.getName())
                .stream()
                .filter(tool -> Objects.equals(toolName, tool.getName()))
                .findFirst()
                .orElse(null);

            if (serverTool == null) {
                throw new AgentStudioException(StudioError.MCP_SERVER_TOOL_NOT_EXIST, serverId, toolName);
            }
        }
        Map<String, Object> result = new HashMap<>();
        result.put(ID, serverId);
        result.put(NAME, serviceEntity.getName());

        // mcp url带着query保存
        if (serviceEntity.getDeployType().equals(STDIO)) {
            result.put(URL, WorkflowUtils.removeQueryParamsFromUrl(serviceEntity.getFcInstanceUrl()));
        } else {
            JSONObject jsonObject = JSONObject.parseObject(encryptionAdapter.decrypt(serviceEntity.getServerConfig()));
            result.put(URL, CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));
        }

        if (Strings.CI.equals(CommonConstant.MCP_SERVER_TYPE.STREAMABLE_HTTP, serviceEntity.getOrgType())) {
            result.put(TYPE, CommonConstant.MCP_SERVER_TYPE.STREAMABLE_HTTP);
        } else {
            // 其他的包括走FG的，都是SSE
            result.put(TYPE, CommonConstant.MCP_SERVER_TYPE.SSE);
        }
        McpServerManagerService.recoveryAuthInfo(serviceEntity);
        result.put(AUTH, WorkflowUtils.parseAuthInfo(serviceEntity.getOrgType(),
            encryptionAdapter.decrypt(serviceEntity.getServerConfig()), serviceEntity.getAuthInfo()));
        result.put(HEADERS, WorkflowUtils.parseHeadersOfServerConfig(serviceEntity.getOrgType(),
                encryptionAdapter.decrypt(serviceEntity.getServerConfig())));
        if (!StringUtils.isEmpty(serviceEntity.getAuthType())
            && Strings.CI.equals(serviceEntity.getAuthType(), USE_IAM_TOKEN)) {
            // 云商城、ROMA对接MCP，需要在运行时填入用户token，由于下面代码使用了IAM-TOKEN作为判断条件，且有条件抛出异常。为了避免混淆，
            // 使用USE-IAM-TOKEN作为判断条件，满足条件依然填入IAM-TOKEN
            result.put("auth_type", IAM_TOKEN);
        }
        if (!StringUtils.isEmpty(serviceEntity.getAuthType())
            && Strings.CI.equals(serviceEntity.getAuthType(), "IAM-TOKEN")) {
            result.put("auth_type", serviceEntity.getAuthType());
            List<Extension> masExtensions = workspaceMappingService.queryMappingWorkspaceExtensionInfo(workspaceId,
                CommonConstant.MAS.WORKSPACE_SOURCE_TYPE);
            if (CollectionUtils.isEmpty(masExtensions)) {
                log.error("The agent-builder workspace and mas not connected, current mcp node cannot be invoked.");
                throw new AgentStudioException(StudioError.INVALID_EXTENSION_PARAM);
            }
            AuthServiceConfig authServiceConfig = new AuthServiceConfig();
            authServiceConfig.setScope("SERVICE");
            Map<String, String> query = new HashMap<>();
            authServiceConfig.setQuery(query);
            Map<String, String> headers = new HashMap<>();
            masExtensions.forEach(extension -> {
                if (Strings.CI.equals(CommonConstant.MAS.APIKEY, extension.getKey())) {
                    // 直接透传
                    headers.put(CommonConstant.MAS.APIKEY, extension.getValue());
                }
            });
            headers.put(CommonConstant.MAS.APPCODE, masAppcode);
            authServiceConfig.setHeaders(headers);
            authServiceConfig.setCryptMethod("scc");
            result.put(AUTH, authServiceConfig);
        }
        // 请求头解析适配到arguments
        List<Map<String, Object>> argumentsList = parseAgentMcpParams(serviceEntity, true);
        if (!Objects.isNull(serverTool)) {
            SchemaConfig inputSchema = JSON.parseObject(serverTool.getInput(), SchemaConfig.class);
            argumentsList.addAll(parseWorkflowPluginParams(inputSchema, false));
            result.put(DESCRIPTION, serverTool.getDescription());
            result.put(CommonConstant.TOOL_NAME, serverTool.getName());
            SchemaConfig outputSchema = JSON.parseObject(serverTool.getOutput(), SchemaConfig.class);
            result.put(RESPONSE, parseWorkflowPluginParams(outputSchema, false));
        }
        // 用户参数（输入参数+请求头）加入arguments
        result.put(ARGUMENTS, argumentsList);
        // 添加hook function自定义鉴权认证
        result.put(PLUGIN_DEPENDENCY, parseMcpParamsWrapper(serviceEntity.getAuthInfo()));
        return result;
    }

    /**
     * 获取知识库信息
     *
     * @param nodeConfigs 节点配置
     * @param projectId project id
     * @return 知识库表
     */
    public List<KnowledgeRepoEntity> getReposFromWorkflowNode(Map<String, Object> nodeConfigs, String projectId) {
        try {
            String jsonStr = JSON.toJSONString(nodeConfigs.get(REPOS));
            Map<String, Object> repoIdsMap = new HashMap<>();
            List<String> repoIds = new ArrayList<>();
            for (Object object : JSON.parseArray(jsonStr)) {
                JSONObject jsonObject = (JSONObject) object;
                repoIdsMap.put(jsonObject.getString(ID), object);
                repoIds.add(jsonObject.getString(ID));
            }
            // 知识库类型是CUSTOM，则不走数据库查询知识库信息
            if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
                return getCustomKnowledgeRepoEntities(repoIdsMap, projectId);
            }
            List<KnowledgeRepoEntity> knowledgeRepoEntities = new ArrayList<>();
            if (!CollectionUtils.isEmpty(repoIdsMap)) {
                ListKnowledgeBasesQo queryKnowledgeBaseQo = new ListKnowledgeBasesQo();
                queryKnowledgeBaseQo.setKnowledgeBaseIds(repoIds);
                queryKnowledgeBaseQo.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
                queryKnowledgeBaseQo.setShareScope("ALL");
                ListKnowledgeBasesResponseBody listKnowledgeBases
                    = knowledgeBaseService.listKnowledgeBaseByShareScope(projectId, queryKnowledgeBaseQo);
                if (listKnowledgeBases != null && listKnowledgeBases.getItems() != null) {
                    listKnowledgeBases.getItems()
                        .forEach(item -> knowledgeRepoEntities
                            .add(convertToKnowledgeRepoEntity(projectId, item, repoIdsMap)));
                }
            }

            // 使用统一配置标签过滤条件
            String logicString = null;
            Object advancedTagsObj = nodeConfigs.get(ADVANCED_TAGS);
            Object commonTagsObj = nodeConfigs.get(COMMON_TAGS);
            if (!ObjectUtils.isEmpty(advancedTagsObj)) {
                // 标签高级检索模式（复杂布尔运算）
                String boolJsonStr = JSON.toJSONString(advancedTagsObj);
                BoolQueryNode rootNode = JSON.parseObject(boolJsonStr, BoolQueryNode.class);
                logicString = BoolQueryParserService.buildEsQuery(rootNode);
                log.info("update knowledge retrieval node, advanced bool logic string: {}", logicString);
            } else if (!ObjectUtils.isEmpty(commonTagsObj)) {
                // 标签普通检索模式（OR运算）
                String boolJsonStr = JSON.toJSONString(commonTagsObj);
                BoolQueryNode rootNode = JSON.parseObject(boolJsonStr, BoolQueryNode.class);
                logicString = BoolQueryParserService.buildEsQuery(rootNode);
                log.info("update knowledge retrieval node, common bool logic string: {}", logicString);
            }
            // 解析出有效字符串时才设置标签过滤条件
            if (StringUtils.isNotBlank(logicString) && !CollectionUtils.isEmpty(knowledgeRepoEntities)) {
                // 最后生成的字符串左右有一对括号，并作为列表的唯一元素
                knowledgeRepoEntities.get(0).setTag(Collections.singletonList(logicString));
            }

            return knowledgeRepoEntities;
        } catch (JSONException e) {
            log.error("Fail to parse workflow repos [{}] for [{}]", nodeConfigs.get(REPOS), e.getMessage());
            return new ArrayList<>();
        }
    }

    public KnowledgeRepoEntity convertToKnowledgeRepoEntity(String projectId, KnowledgeBaseListItem item,
        Map<String, Object> repoIdsMap) {
        KnowledgeRepoEntity knowledgeRepoEntity = new KnowledgeRepoEntity();
        knowledgeRepoEntity.setKnowledgeRepoId(item.getKnowledgeBaseId());
        knowledgeRepoEntity.setProjectId(projectId);
        knowledgeRepoEntity.setDisplayName(item.getName());
        knowledgeRepoEntity.setDesc(item.getDescription());
        if (item.getType() != null) {
            knowledgeRepoEntity.setType(item.getType().toString());
        }
        Object value = repoIdsMap.get(item.getKnowledgeBaseId());
        knowledgeRepoEntity.setIcon(item.getIcon());
        knowledgeRepoEntity.setCreator(item.getCreatedUserName());
        knowledgeRepoEntity.setCreatorId(item.getCreatedUserId());
        knowledgeRepoEntity.setConnectionId(item.getKnowledgeBaseConnectionId());
        if (item.getStatus() != null) {
            knowledgeRepoEntity.setStatus(item.getStatus().toString());
        }
        if (item.getCreateTime() != null) {
            knowledgeRepoEntity.setCreatedOn(new Date(item.getCreateTime()));
        }
        if (item.getUpdateTime() != null) {
            knowledgeRepoEntity.setUpdatedOn(new Date(item.getUpdateTime()));
        }
        return knowledgeRepoEntity;
    }

    private List<KnowledgeRepoEntity> getCustomKnowledgeRepoEntities(Map<String, Object> repoIds, String projectId) {
        List<KnowledgeRepoEntity> knowledgeRepoEntities = new ArrayList<>();
        repoIds.forEach((key, value) -> {
            KnowledgeRepoEntity knowledgeRepoEntity = new KnowledgeRepoEntity();
            knowledgeRepoEntity.setKnowledgeRepoId(key);
            if (!ObjectUtils.isEmpty(value)) {
                knowledgeRepoEntity.setFilterString(((JSONObject) value).getString(key));
            }
            knowledgeRepoEntity.setProjectId(projectId);
            knowledgeRepoEntity.setType(KnowledgeBaseListItem.TypeEnum.INTERNAL.toString());
            knowledgeRepoEntity.setSource(KnowledgeSourceEnum.CUSTOM.toString());
            knowledgeRepoEntity.setConnectionId(DEFAULT_CONNECTION_ID);
            knowledgeRepoEntities.add(knowledgeRepoEntity);

        });
        return knowledgeRepoEntities;
    }

    /**
     * 根据id插件信息
     *
     * @param projectId project id
     * @param pluginConfig pluginConfig
     * @return 插件信息
     */
    public ToolEntity getPluginToolEntity(String projectId, Map<String, Object> pluginConfig) {
        if (!pluginConfig.get(Constants.ID).toString().contains("#")) {
            if (pluginConfig.containsKey("tool_id")) {
                pluginConfig.put(ID, pluginConfig.get(ID) + "#" + pluginConfig.get("tool_id"));
            } else {
                String suffix = pluginService.getToolIdFromPlugin(pluginConfig.get(Constants.ID).toString());
                if (suffix == null) {
                    suffix = "0";
                }
                pluginConfig.put(ID, pluginConfig.get(ID) + "#" + suffix);
            }
        }
        // 新的插件场景，当前id为插件ID#工具ID格式，老的插件仅为插件ID
        Object idConfig = pluginConfig.get(Constants.ID);
        Object versionIdConfig = pluginConfig.get(Constants.VERSION_ID);
        if (idConfig == null) {
            log.error("tool id not exist when selectPluginToolEntity");
            throw new AgentStudioException(StudioError.TOOL_INPUT_INVALID);
        }

        String toolId = idConfig.toString();
        String versionId = versionIdConfig == null ? null : versionIdConfig.toString();

        ToolEntity toolEntity = pluginService.getToolEntity(toolId, projectId, opProjectId, versionId);

        if (toolEntity == null) {
            log.error("tool {} is not exist", toolId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        return toolEntity;
    }

    private String pluginIdAdapter(String pluginToolId) {
        String[] ids = pluginToolId.split("#");
        String pluginId = ids[0]; // 获取 pluginId
        return pluginId;
    }

    /**
     * 解析插件ir config配置
     *
     * @param pluginConfig pluginConfig
     * @param projectId project id
     * @param isAgentPlugin 是否为agent中插件
     * @return 插件ir config
     */
    public Map<String, Object> parsePluginConfig(Map<String, Object> pluginConfig, String projectId,
        boolean isAgentPlugin) {
        Map<String, Object> result = new HashMap<>();
        ToolEntity toolEntity = getPluginToolEntity(projectId, pluginConfig);
        String[] ids = toolEntity.getToolId().split("#");
        String pluginId = ids[0]; // 获取 pluginId
        ToolCredential toolCredential = toolCredentialMapper.selectByToolIdAndDomainId(pluginId, RequestContextUtils.getRequestUserDomainId(), RequestContextUtils.getRequestWorkspaceId());
        result.put(ID, pluginIdAdapter(toolEntity.getToolId()));
        if (!isAgentPlugin) {
            boolean isStream = !StringUtils.isEmpty(toolEntity.getIntfType())
                && CommonConstant.Plugin.INTF_TYPE_STREAMING.equalsIgnoreCase(toolEntity.getIntfType());
            result.put(STREAMING, isStream);
        }
        result.put(NAME, toolEntity.getToolDisplayName());
        result.put(DESCRIPTION, toolEntity.getToolDesc());
        result.put(URL, toolEntity.getRequestInfo().getUrl());
        result.put(METHOD, toolEntity.getRequestInfo().getMethod());
        Map<String, String> headers = toolEntity.getRequestInfo().getHeaders() != null
            ? toolEntity.getRequestInfo().getHeaders() : new HashMap<>();
        if (!CollectionUtils.isEmpty(headers)) {
            // 存量未加密数据无需解密
            headers.forEach((key, value) -> {
                try {
                    String decryptedValue = encryptionAdapter.decrypt(value);
                    headers.put(key, decryptedValue);
                } catch (Exception e) {
                    log.warn("Fail to decrypt plugin header [{}].", key);
                }
            });
        }
        SchemaConfig inputSchema = JSON.parseObject(toolEntity.getInputSchema(), SchemaConfig.class);
        fillHeaders(inputSchema, headers);
        fillInputSchemaByRequestInfo(inputSchema, toolEntity.getRequestInfo());

        result.put(HEADERS, headers);
        result.put(AUTH, WorkflowUtils.parseAuthInfo(toolEntity.getAuthInfo()));
        if (ToolType.INNER.type.equals(toolEntity.getType()) && toolEntity.getIsFree() != null && toolEntity.getIsFree() == 1 && toolEntity.getAuthRequired()) {
            if (toolCredential == null) {
                PrePluginAuthServiceConfig authServiceConfig = new PrePluginAuthServiceConfig();
                String domainId = RequestContextUtils.getRequestUserDomainId();
                String pluginFreeTrialUsageRecords = redisClient.get(getPluginFreeTrialUsageQuotaKey(domainId, pluginId));
                authServiceConfig.setUsage(NumberUtils.toInt(pluginFreeTrialUsageRecords));
                authServiceConfig.setLimit(pluginMaxFreeTrialTimes);
                authServiceConfig.setDomainId(domainId);
                authServiceConfig.setProjectId(projectId);
                authServiceConfig.setBaseUrl(managerEndpoint);
                authServiceConfig.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
                AuthInfo authInfo = toolEntity.getAuthInfo();
                if (authInfo != null && authInfo.getScope() != null
                        && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
                    log.info("The scope of the plugin is service, and the service id is [{}].", authInfo.getDomain());
                    authServiceConfig.setScope(authInfo.getScope().toString());
                    Map<String, String> serviceMap = new HashMap<>();
                    authInfo.getAuthKeys().forEach(m -> serviceMap.put(m.getTargetName(), m.getAuthKey()));
                    if (authInfo.getDomain() == AuthInfo.DomainEnum.HEADERS) {
                        authServiceConfig.setHeaders(serviceMap);
                        authServiceConfig.setQuery(new HashMap<>());
                    } else {
                        authServiceConfig.setQuery(serviceMap);
                        authServiceConfig.setHeaders(new HashMap<>());
                    }
                }
                result.put(AUTH, authServiceConfig);
            }
        }
        if (toolEntity.getAuthInfo() != null && toolEntity.getAuthInfo().getScope() != null
            && AuthInfo.ScopeEnum.IAM.equals(toolEntity.getAuthInfo().getScope())) {
            if (Objects.isNull(toolEntity.getAuthInfo().getIamCredentials())) {
                log.error("There is no iam credentials when convert to IR.");
                throw new AgentStudioException(StudioError.TOOL_INFO_INCORRECT);
            }
            String callPluginProjectId = toolEntity.getAuthInfo().getIamCredentials().get(CommonConstant.PROJECT_ID);
            String callPluginDomainId = toolEntity.getAuthInfo().getIamCredentials().get(CommonConstant.DOMAIN_ID);
            AuthIamConfig authIamConfig =
                JSONObject.parseObject(JSONObject.toJSONString(result.get(AUTH)), AuthIamConfig.class);
            authIamConfig.setProjectId(callPluginProjectId);
            authIamConfig.setDomainId(callPluginDomainId);
            result.put(AUTH, authIamConfig);
        }

        result.put(ARGUMENTS,
            isAgentPlugin ? parseAgentPluginParams(inputSchema, true) : parseWorkflowPluginParams(inputSchema, true));
        SchemaConfig outputSchema = JSON.parseObject(toolEntity.getOutputSchema(), SchemaConfig.class);
        result.put(RESPONSE, isAgentPlugin ? parseAgentPluginParams(outputSchema, false)
            : parseWorkflowPluginParams(outputSchema, false));
        result.put(PLUGIN_DEPENDENCY,
            parseParamsWrapper(toolEntity, Optional.ofNullable(toolEntity.getIsInputList()).orElse(false),
                Optional.ofNullable(toolEntity.getIsOutputList()).orElse(false)));

        // 如果是需要鉴权的预置插件
        if (isAuthRequiredPresetPlugin(toolEntity.getToolId()) && toolCredential != null) {
            // 设置插件的凭证类型
            result.put(CREDENTIAL_TYPE, CredentialType.OBS.toString());
            // 设置插件的凭证创建人
            result.put(CREDENTIAL_OWNER_ID, RequestContextUtils.getRequestUserId());
        }

        return result;
    }

    private String getPluginFreeTrialUsageQuotaKey(String domainId, String pluginId) {
        return String.format(Locale.ROOT, PLUGIN_FREE_TRIAL_USAGE_QUOTA_KEY_FORMAT, pluginId,
                LocalDate.now().getMonthValue(), domainId);
    }

    private void fillHeaders(SchemaConfig schemaConfig, Map<String, String> headers) {
        if (ObjectUtils.isEmpty(schemaConfig)) {
            return;
        }
        // 1. 先查找是否存在Headers参数
        Map<String, SchemaConfig> propertiesNode = schemaConfig.getProperties();
        for (Map.Entry<String, SchemaConfig> entry : propertiesNode.entrySet()) {
            if (Strings.CS.equals("Headers", entry.getValue().getLocation())) {
                headers.put(entry.getKey(), entry.getValue().getDefaultValue());
            }
        }
    }

    private void fillInputSchemaByRequestInfo(SchemaConfig schemaConfig, RequestInfo requestInfo) {
        if (Objects.isNull(requestInfo) || StringUtils.isBlank(requestInfo.getInputSchema())) {
            return;
        }
        SchemaConfig input = JSON.parseObject(requestInfo.getInputSchema(), SchemaConfig.class);
        schemaConfig.getProperties().putAll(input.getProperties());
        schemaConfig.getRequired().addAll(input.getRequired());
    }

    /**
     * 判断插件是否为预置插件
     *
     * @param pluginToolId
     * @return
     */
    private boolean isAuthRequiredPresetPlugin(String pluginToolId) {
        String[] ids = pluginToolId.split("#");
        String pluginId = ids[0]; // 获取 pluginId

        // 确保 toolId 存在
        String toolId = ids.length > 1 ? ids[1] : "0"; // 如果存在 toolId, 否则为 null
        ToolEntity toolEntity = pluginBaseImpl.buildToolByPlugin(null, null, pluginId, toolId);
        if (toolEntity == null) {
            log.error("tool {} is not exist", toolId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }

        return ToolType.INNER.type.equals(toolEntity.getType()) && Boolean.TRUE.equals(toolEntity.getAuthRequired());
    }

    /**
     * 解析MCP server irConfig配置
     *
     * @param mcpId MCP serverId
     * @param projectId project id
     * @return MCP server irConfig
     */
    public Map<String, Object> parseMcpConfig(String mcpId, String projectId, String workspaceId,
                                              Map<String, List<String>> mcpChooseTools) {
        McpServiceEntity mcpServerInfo = serviceDao.selectById(mcpId, CommonUtil.getTenantId(),
            CommonUtil.getDeptCode(), StringUtils.isBlank(workspaceId) ? "default" : workspaceId);
        if (mcpServerInfo == null) {
            log.error("MCP service does not exist.");
            throw new AgentStudioException(StudioError.MCP_SERVER_NOT_EXIST);
        }

        // ir转换
        Map<String, Object> result = new HashMap<>();
        result.put(ID, mcpId);
        result.put(NAME, mcpServerInfo.getName());
        result.put(DESCRIPTION, mcpServerInfo.getDescription());
        result.put(ARGUMENTS, parseAgentMcpParams(mcpServerInfo, true));
        if (Strings.CI.equals(CommonConstant.MCP_SERVER_TYPE.STREAMABLE_HTTP, mcpServerInfo.getOrgType())) {
            result.put(TYPE, CommonConstant.MCP_SERVER_TYPE.STREAMABLE_HTTP);
        } else {
            // 其他的包括走FG的，都是SSE
            result.put(TYPE, CommonConstant.MCP_SERVER_TYPE.SSE);
        }

        // mcp url带着query保存
        if (mcpServerInfo.getDeployType().equals(STDIO)) {
            result.put(URL, WorkflowUtils.removeQueryParamsFromUrl(mcpServerInfo.getFcInstanceUrl()));
        } else {
            JSONObject jsonObject = JSONObject.parseObject(encryptionAdapter.decrypt(mcpServerInfo.getServerConfig()));
            result.put(URL, CommonUtil.parseUrlFromMcpConfig(jsonObject, 0));
        }

        McpServerManagerService.recoveryAuthInfo(mcpServerInfo);
        String serverConfig = getServiceConfig(mcpServerInfo);
        result.put(AUTH, WorkflowUtils.parseAuthInfo(mcpServerInfo.getOrgType(), serverConfig, mcpServerInfo.getAuthInfo()));
        result.put(HEADERS, WorkflowUtils.parseHeadersOfServerConfig(mcpServerInfo.getOrgType(),
                encryptionAdapter.decrypt(mcpServerInfo.getServerConfig())));
        if (!StringUtils.isEmpty(mcpServerInfo.getAuthType())
            && (Strings.CI.equals(mcpServerInfo.getAuthType(), "IAM-TOKEN")
                || Strings.CI.equals(mcpServerInfo.getAuthType(), "USE-IAM-TOKEN"))) {
            result.put("auth_type", "IAM-TOKEN");
        }
        // mcp选择的工具
        if (mcpChooseTools != null && mcpChooseTools.containsKey(mcpId)) {
            List<String> mcpToolNames = mcpChooseTools.get(mcpId);
            log.info("user choose agent mcp tools, tools size is {}", mcpToolNames.size());
            result.put(MCP_CHOOSE_TOOLS, mcpToolNames);
        }
        // 支持hook function自定义鉴权
        result.put(PLUGIN_DEPENDENCY, parseMcpParamsWrapper(mcpServerInfo.getAuthInfo()));
        return result;
    }

    public String getServiceConfig(McpServiceEntity mcpServerInfo) {
        String serverConfig;
        try {
            serverConfig = encryptionAdapter.decrypt(mcpServerInfo.getServerConfig());
        } catch (Exception exception) {
            serverConfig = "";
        }
        return serverConfig;
    }

    /**
     * 提取搜索API密钥
     *
     * @param toolEntity 工具实体
     * @param toolId 工具ID
     * @return 搜索API密钥
     */
    private String extractSearchApiKey(ToolEntity toolEntity, String toolId) {

        // 从数据库中获取认证密钥
        if (Boolean.TRUE.equals(toolEntity.getAuthRequired())) {
            return extractAuthKeyFromDatabase(toolId);
        }
        // 直接从工具实体中获取认证密钥
        else if (Boolean.FALSE.equals(toolEntity.getAuthRequired())) {
            return extractAuthKeyFromToolEntity(toolEntity);
        }
        log.warn("Unexpected auth required value: {} for tool: {}", toolEntity.getAuthRequired(), toolId);
        return null;
    }

    /**
     * 从数据库中提取认证密钥
     *
     * @param toolId 工具ID
     * @return 认证密钥
     */
    private String extractAuthKeyFromDatabase(String toolId) {
        try {
            String cleanToolId = toolId.split("#")[0];
            List<String> authKeys = toolCredentialMapper.selectAuthKeysByToolId(cleanToolId);
            String authKeyJson = authKeys.get(0);
            JSONArray authKeyArray = JSONArray.parseArray(authKeyJson);
            JSONObject firstAuthKey = authKeyArray.getJSONObject(0);
            return firstAuthKey.getString("auth_key");
        } catch (Exception e) {
            log.error("Failed to parse auth keys from database for tool: {}", toolId, e);
            return null;
        }
    }

    /**
     * 从工具实体中提取认证密钥
     *
     * @param toolEntity 工具实体
     * @return 认证密钥
     */
    private String extractAuthKeyFromToolEntity(ToolEntity toolEntity) {
        try {
            if (toolEntity.getAuthInfo().getAuthKeys().get(0) == null) {
                log.warn("First auth key is null for tool: {}", toolEntity.getToolId());
                return null;
            }
            return toolEntity.getAuthInfo().getAuthKeys().get(0).getAuthKey();
        } catch (Exception e) {
            log.error("Failed to extract auth key from tool entity: {}", toolEntity.getToolId(), e);
            return null;
        }
    }

    private Object parseParamsWrapper(ToolEntity toolEntity, boolean isInputList, boolean isOutputList) {
        Map<String, Boolean> paramsWrapperMap = new HashMap<>();
        paramsWrapperMap.put(INPUT_LIST, isInputList);
        paramsWrapperMap.put(OUTPUT_LIST, isOutputList);
        Map<String, Object> pluginDependencyMap = new HashMap<>();
        pluginDependencyMap.put(PARAMS_WRAPPER, paramsWrapperMap);
        if (ToolType.INNER.type.equals(toolEntity.getType()) && toolEntity.getIsFree() != null && 1 == toolEntity.getIsFree() && toolEntity.getAuthRequired()) {
            Map<String, String> hookFunction = new HashMap<>();
            log.info("now hookFunctionPath is: {}", prePluginHookFunctionPath);
            hookFunction.put("plugin_auth", prePluginHookFunctionPath);
            pluginDependencyMap.put(HOOK_FUNCTION, hookFunction);
        }
        if (ObjectUtils.isEmpty(toolEntity.getAuthInfo())) {
            return pluginDependencyMap;
        }
        if (AuthInfo.ScopeEnum.SGOV.equals(toolEntity.getAuthInfo().getScope())
            || AuthInfo.ScopeEnum.HIS_IAM.equals(toolEntity.getAuthInfo().getScope())
            || AuthInfo.ScopeEnum.CUSTOM_IAM.equals(toolEntity.getAuthInfo().getScope())) {
            Map<String, String> hookFunction = new HashMap<>();
            log.info("now hookFunctionPath is: {}", hookFunctionPath);
            hookFunction.put("plugin_auth", hookFunctionPath);
            pluginDependencyMap.put(HOOK_FUNCTION, hookFunction);
        }
        return pluginDependencyMap;
    }

    private Object parseMcpParamsWrapper(AuthInfo authInfo) {
        Map<String, Boolean> paramsWrapperMap = new HashMap<>();
        Map<String, Object> pluginDependencyMap = new HashMap<>();
        pluginDependencyMap.put(PARAMS_WRAPPER, paramsWrapperMap);
        if (Objects.isNull(authInfo)) {
            return pluginDependencyMap;
        }
        if (AuthInfo.ScopeEnum.OAUTH.equals(authInfo.getScope())) {
            Map<String, String> hookFunction = new HashMap<>();
            log.info("now hookFunctionPath is: {}", mcpHookFunctionPath);
            hookFunction.put("mcp_auth", mcpHookFunctionPath);
            pluginDependencyMap.put(HOOK_FUNCTION, hookFunction);
        }
        return pluginDependencyMap;
    }

    private List<Map<String, Object>> parseAgentPluginParams(SchemaConfig schemaConfig, boolean shouldValidate) {
        if (Objects.isNull(schemaConfig) || Objects.isNull(schemaConfig.getType())) {
            return new ArrayList<>();
        }
        List<Map<String, Object>> paramList = new ArrayList<>();
        if (schemaConfig.getProperties() == null)
            return paramList;

        for (Map.Entry<String, SchemaConfig> properties : schemaConfig.getProperties().entrySet()) {
            Map<String, Object> param = new HashMap<>();
            param.put(NAME, properties.getKey());
            param.put(DESCRIPTION, properties.getValue().getDescription());
            if (shouldValidate) {
                param.put(VALIDATED, properties.getValue().isShouldValidate());
                param.put(VALIDATE_TYPE, properties.getValue().getValidateType());
                param.put(VALIDATE_RULE, properties.getValue().getValidateRule());
            }

            String paramType = properties.getValue().getType();
            if (paramType != null && paramType.startsWith(FILE_TYPE)) {
                param.put(ACTUAL_TYPE, properties.getValue().getType());
                param.put(TYPE, URL_TYPE);
            } else {
                param.put(TYPE, JsonSchemaType.ARRAY.type.equals(paramType) ? String.format("array<%s>",  properties.getValue().getItems().getType()) : paramType);
            }

            param.put(DEFAULT_VALUE,
                    convertDefaultValue(properties.getValue().getDefaultValue(), properties.getValue().getType()));

            param.put(DEFAULT_VALUE, convertDefaultValue(properties.getValue().getDefaultValue(), properties.getValue().getType()));
            param.put(METHOD, properties.getValue().getLocation());
            if (schemaConfig.getRequired() != null && !schemaConfig.getRequired().isEmpty()) {
                param.put(REQUIRED, schemaConfig.getRequired().contains(properties.getKey()));
            } else {
                param.put(REQUIRED, false);
            }
            // array<object>类型
            if (JsonSchemaType.ARRAY.type.equals(properties.getValue().getType())
                && JsonSchemaType.OBJECT.type.equals(properties.getValue().getItems().getType())) {
                param.put(SCHEMA, parseAgentPluginParams(properties.getValue().getItems(), false));
            }
            // object类型
            if (JsonSchemaType.OBJECT.type.equals(properties.getValue().getType())) {
                param.put(SCHEMA, parseAgentPluginParams(properties.getValue(), false));
            }
            param.entrySet().removeIf(entry -> Objects.isNull(entry.getValue()));
            paramList.add(param);
        }
        return paramList;
    }

    /**
     * 解析serverConfig中的请求头信息，为输入参数。
     * @param mcpEntity mcp 数据库中的信息
     * @param shouldValidate 是否需要校验
     * @return mcp config中的入参
     */
    public List<Map<String, Object>> parseAgentMcpParams(McpServiceEntity mcpEntity, boolean shouldValidate) {
        List<Map<String, Object>> paramList = new ArrayList<>();

        if (Objects.isNull(mcpEntity) || Objects.isNull(mcpEntity.getServerConfig())) {
            return paramList;
        }

        // serverConfig 信息 headers转换
        Map<String, String> headers = parseMcpConfigHeaderInfo(encryptionAdapter.decrypt(mcpEntity.getServerConfig()));
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            String key = entry.getKey();
            String value = entry.getValue();

            // 构造arguments
            Map<String, Object> param = new HashMap<>();
            param.put(NAME, key);
            param.put(DESCRIPTION, value);

            if (shouldValidate) {
                param.put(VALIDATED, false);
                param.put(VALIDATE_TYPE, MCP_VALIDATE_TYPE);
                param.put(VALIDATE_RULE, "");
            }

            // 配置校验参数
            param.put(TYPE, MCP_TYPE);
            param.put(DEFAULT_VALUE, value);
            param.put(METHOD, MCP_METHOD);
            param.put(REQUIRED, false);

            // 添加参数
            paramList.add(param);
        }

        return paramList;
    }

    private Object convertDefaultValue(String defaultValue, String type) {
        if (StringUtils.isBlank(defaultValue)) {
            return null;
        }
        if (type == null) {
            return defaultValue;
        }
        try {
            return switch (JsonSchemaType.valueOf(type.toUpperCase(Locale.ROOT))) {
                case NUMBER -> Double.parseDouble(defaultValue);
                case INTEGER -> Integer.parseInt(defaultValue);
                case BOOLEAN -> Boolean.parseBoolean(defaultValue);
                default -> defaultValue;
            };
        } catch (NumberFormatException exception) {
            log.error("Fail to convert default value [{}] with type [{}].", defaultValue, type);
            return defaultValue;
        }
    }

    private List<Map<String, Object>> parseWorkflowPluginParams(SchemaConfig schemaConfig, boolean shouldValidate) {
        if (Objects.isNull(schemaConfig) || Objects.isNull(schemaConfig.getType())) {
            return new ArrayList<>();
        }
        List<Map<String, Object>> paramList = new ArrayList<>();
        if (schemaConfig.getProperties() == null)
            return paramList;

        for (Map.Entry<String, SchemaConfig> properties : schemaConfig.getProperties().entrySet()) {
            Map<String, Object> param = new HashMap<>();
            param.put(NAME, properties.getKey());
            param.put(DESCRIPTION, Optional.ofNullable(properties.getValue().getDescription()).orElse(""));
            if (shouldValidate) {
                // 子项schema无需添加校验字段
                param.put(VALIDATED, properties.getValue().isShouldValidate());
                param.put(VALIDATE_TYPE, properties.getValue().getValidateType());
                param.put(VALIDATE_RULE, properties.getValue().getValidateRule());
            }
            param.put(DEFAULT_VALUE,
                convertDefaultValue(properties.getValue().getDefaultValue(), properties.getValue().getType()));
            String paramType = properties.getValue().getType();
            if (paramType != null && paramType.startsWith(FILE_TYPE)) {
                param.put(ACTUAL_TYPE, properties.getValue().getType());
                param.put(TYPE, URL_TYPE);
            } else {
                param.put(TYPE, properties.getValue().getType());
            }
            param.put(METHOD, properties.getValue().getLocation());
            if (schemaConfig.getRequired() != null && !schemaConfig.getRequired().isEmpty()) {
                param.put(REQUIRED, schemaConfig.getRequired().contains(properties.getKey()));
            } else {
                param.put(REQUIRED, false);
            }
            // array类型
            if (JsonSchemaType.ARRAY.type.equals(properties.getValue().getType())) {
                String type = properties.getValue().getItems().getType();
                Map<String, Object> sonMap = new HashMap<>();
                sonMap.put(TYPE, type);
                if (JsonSchemaType.OBJECT.type.equals(type)) {
                    sonMap.put(SCHEMA, parseWorkflowPluginParams(properties.getValue().getItems(), false));
                }
                param.put(SCHEMA, sonMap);
            }
            // object类型
            if (JsonSchemaType.OBJECT.type.equals(properties.getValue().getType())) {
                param.put(SCHEMA, parseWorkflowPluginParams(properties.getValue(), false));
            }
            param.entrySet().removeIf(entry -> Objects.isNull(entry.getValue()));
            paramList.add(param);
        }
        return paramList;
    }

    private List<Map<String, Object>> parseWorkflowPluginParams(List<WorkflowFieldVO> workflowFieldList) {
        if (workflowFieldList == null) {
            return null;
        }
        List<Map<String, Object>> paramList = new ArrayList<>();
        for (WorkflowFieldVO workflowField : workflowFieldList) {
            Map<String, Object> param = new HashMap<>();
            param.put(NAME, workflowField.getName());
            param.put(DESCRIPTION, workflowField.getDescription());
            parsePluginParamType(param, workflowField);
            paramList.add(param);
        }
        return paramList;
    }

    /**
     * Agent ir转换
     *
     * @param agent agent信息
     * @param metadata 额外参数
     * @return Agent IR
     */
    public Map<String, Object> adaptAgent(Agent agent, Map<String, Object> metadata) {
        Map<String, Object> result = new HashMap<>();
        result.put("agentId", agent.getAgentId());
        result.put("agentName", agent.getName());
        /// 用户入参变量转ir
        if (!CollectionUtils.isEmpty(agent.getInputVariables())) {
            result.put("inputs", parseInputVariables(agent.getInputVariables()));
        }
        result.put(DESCRIPTION, agent.getDescription());
        result.put("agentVersion", agentIrVersion);
        result.put("schemaVersion", agentIrVersion);

        // 如果为PlanExecute模式，存在agentType字段
        if (Strings.CS.equals(PLAN_EXECUTE, agent.getSchedulingMode())) {
            result.put("agentType", PLAN_EXECUTE);
        }

        // 解析agent关联插件配置
        String projectId = agent.getProjectId();
        List<MappingEntity> agentToolList =
            mappingMapper.selectByAppIdAndResourceType(agent.getAgentId(), CommonConstant.TOOL_TYPE);
        List<Map<String, Object>> pluginConfigs = new ArrayList<>();
        for (MappingEntity entity : agentToolList) {
            Map<String, Object> pluginConfig = new HashMap<>();
            pluginConfig.put(Constants.ID, entity.getResourceId());
            pluginConfig.put(Constants.VERSION_ID, entity.getResourceVersion());
            pluginConfig.put(Constants.NAME, entity.getResourceName());
            Map<String, Object> pluginConfigAfterParse = parsePluginConfig(pluginConfig, projectId, true);
            // 用户可配置参数值和参数可见性
            if (entity.getExtendInfo() != null) {
                pluginConfigAfterParse = setUserConfig(pluginConfigAfterParse, entity.getExtendInfo(), TOOL);
            }
            pluginConfigs.add(pluginConfigAfterParse);
        }

        // 解析agent关联知识库，作为插件信息配置
        parseAgentKnowledgeRepo(agent, projectId, agent.getWorkspaceId(), pluginConfigs);

        // 解析agent关联的MCP server
        List<MappingEntity> agentMcpList =
                mappingMapper.selectByAppIdAndResourceType(agent.getAgentId(), CommonConstant.MCP_TYPE);
        List<MappingEntity> validAgentMcpList = agentMcpList.stream().filter(MappingEntity::isValid).toList();
        Map<String, List<String>> mcpChooseTools = agent.getMcpChooseTools();
        List<Map<String, Object>> mcpConfigs = new ArrayList<>();

        for (MappingEntity entity : validAgentMcpList) {
            Map<String, Object> mcpConfig =
                    parseMcpConfig(entity.getResourceId(), projectId, agent.getWorkspaceId(), mcpChooseTools);
            // 用户可配置参数值和参数可见性
            if (entity.getExtendInfo() != null) {
                mcpConfig = setUserConfig(mcpConfig, entity.getExtendInfo(), TOOL);
            }

            // 利用config中的arguments，替换headers中的值
            parseMcpConfigAndReplaceHeaders(mcpConfig);

            mcpConfigs.add(mcpConfig);
        }

        Map<String, Object> modelConfig = new HashMap<>();
        Map<String, Object> configs = new HashMap<>();
        if (agent.getModelConfig() != null) {
            modelConfig.put("modelName",
                agent.getModelDeploymentId() + (StringUtils.isEmpty(agent.getModel()) ? "" : "|" + agent.getModel()));
            modelConfig.put("modelType",
                Optional.ofNullable(agent.getModelType()).orElse(CommonConstant.AGENT_BUILDER_MODEL_TYPE));
            modelConfig.put("historySize", agent.getModelConfig().getHistorySize());
            modelConfig.put("outputFormat", agent.getModelConfig().getOutputFormat());
            Map<String, Object> hyperParameters = new HashMap<>();
            hyperParameters.put("temperature", agent.getModelConfig().getTemperature());
            hyperParameters.put("top_p", agent.getModelConfig().getTopP());
            String type = Strings.CI.equals(agent.getModelConfig().isEnableThinking().toString(),
                Boolean.TRUE.toString()) ? ENABLE_THINKING_ENABLED : ENABLE_THINKING_DISABLED;
            HashMap<String, String> typeMap = new HashMap<>();
            typeMap.put(CommonConstant.ModelParam.TYPE, type);
            hyperParameters.put(CommonConstant.ModelParam.THINKING, typeMap);
            if (agent.getModelConfig().getFrequencyPenalty() != null) {
                hyperParameters.put(CommonConstant.ModelParam.FREQUENCY_PENALTY,
                    agent.getModelConfig().getFrequencyPenalty());
            }
            if (agent.getModelConfig().getMaxTokens() != null) {
                hyperParameters.put(CommonConstant.ModelParam.MAX_TOKENS, agent.getModelConfig().getMaxTokens());
            }
            modelConfig.put("hyperParameters", hyperParameters);
            Map<String, Object> extension = modelServiceManager.parseModelExtension(agent.getModelDeploymentId(),
                projectId, agent.getWorkspaceId(), false);
            if (!Objects.isNull(extension)) {
                modelConfig.put("extension", extension);
            }
            // 适配模型extension参数
            IRUtils.adaptModelExtension(modelConfig);
            configs.put("modelConfig", modelConfig);
        } else {
            configs.put("modelConfig", null);
        }

        // 仅工具优先支持规划模型配置
        if (Strings.CS.equals(TOOL_USE, agent.getSchedulingMode()) && agent.getPlanQaIndependent() != null
            && agent.getPlanQaIndependent() && agent.getPlanModelConfig() != null) {
            Map<String, Object> planModelConfig = new HashMap<>();
            planModelConfig.put("modelName", agent.getPlanModelDeploymentId()
                + (StringUtils.isEmpty(agent.getPlanModel()) ? "" : "|" + agent.getPlanModel()));
            planModelConfig.put("modelType",
                Optional.ofNullable(agent.getPlanModelType()).orElse(CommonConstant.AGENT_BUILDER_MODEL_TYPE));
            planModelConfig.put("historySize", agent.getPlanModelConfig().getHistorySize());
            planModelConfig.put("outputFormat", agent.getPlanModelConfig().getOutputFormat());
            Map<String, Object> planHyperParameters = new HashMap<>();
            planHyperParameters.put("temperature", agent.getPlanModelConfig().getTemperature());
            planHyperParameters.put("top_p", agent.getPlanModelConfig().getTopP());
            if (agent.getPlanModelConfig().getMaxTokens() != null) {
                planHyperParameters.put(CommonConstant.ModelParam.MAX_TOKENS,
                    agent.getPlanModelConfig().getMaxTokens());
            }
            planModelConfig.put("hyperParameters", planHyperParameters);
            Map<String, Object> extension = modelServiceManager.parseModelExtension(agent.getPlanModelDeploymentId(),
                projectId, agent.getWorkspaceId(), false);
            if (!Objects.isNull(extension)) {
                planModelConfig.put("extension", extension);
            }
            // 适配模型extension参数
            IRUtils.adaptModelExtension(planModelConfig);
            configs.put("planModelConfig", planModelConfig);
        }

        // 解析agent关联工作流
        List<MappingEntity> agentWorkflowList =
            mappingMapper.selectByAppIdAndResourceType(agent.getAgentId(), CommonConstant.WORKFLOW_TYPE);
        Map<String, MappingEntity> agentWorkflowMap =
            agentWorkflowList.stream().collect(Collectors.toMap(MappingEntity::getResourceId, Function.identity()));
        List<WorkflowEntity> workflowEntityList = relationManagementService
            .listAgentWorkflowVersions(agent.getProjectId(), agent.getWorkspaceId(), agentWorkflowMap);
        Map<String, WorkflowEntity> workflowMap =
            workflowEntityList.stream().collect(Collectors.toMap(WorkflowEntity::getId, Function.identity()));
        List<Map<String, Object>> workflowConfigs = new ArrayList<>();
        for (MappingEntity entity : agentWorkflowList) {
            // workflowEntity中的id与mappingEntity中的ResourceId匹配
            WorkflowEntity matchingWorkflow = workflowMap.get(entity.getResourceId());
            if (matchingWorkflow != null) {
                Map<String, Object> workflowConfigAfterParse = parseWorkflowPlugin(matchingWorkflow);
                // 用户可配置参数值和参数可见性
                if (entity.getExtendInfo() != null) {
                    workflowConfigAfterParse =
                        setUserConfig(workflowConfigAfterParse, entity.getExtendInfo(), WORKFLOW);
                }
                workflowConfigs.add(workflowConfigAfterParse);
            }
        }

        // 关联Agent关联Skill
        // 1. 获取有效的skillDetails信息
        List<String> agentSkillIds = mappingMapper.selectByAppIdAndResourceType(agent.getAgentId(),
                ResourceTypeEnum.SKILL.toString())
            .stream()
            .filter(MappingEntity::isValid)
            .map(MappingEntity::getResourceId)
            .toList();
        List<SkillDetails> skillDetails = skillMapper.searchBySkillIds(agentSkillIds);
        // 2.生成skill相关配置
        Map<String, Object> skillConfigs = new HashMap<>();
        skillConfigs.put("skill_dir", "skills" + CommonConstant.FOLDER_SEPARATOR + agent.getAgentId());
        List<SkillIrInfo> skillIrInfos = new ArrayList<>();
        skillDetails.forEach(skillDetail -> {
                SkillIrInfo skillIrInfo = new SkillIrInfo().setName(skillDetail.getName())
                    .setDescription(skillDetail.getDescription())
                    .setSkillPath(skillDetail.getObsPath());
                skillIrInfos.add(skillIrInfo);
            });
        skillConfigs.put("skill_info", skillIrInfos);

        // 仅自主规划模式支持场景配置
        if (Strings.CS.equals(PLAN_EXECUTE, agent.getSchedulingMode()) && agent.getDslPath() != null) {
            // 获取dsl，Scene定义放在了dsl中
            String agentDslJson = mgObsService.downloadObsFile(agent.getDslPath());
            AgentInfo agentInfo = JSON.parseObject(agentDslJson, AgentInfo.class);
            Map<String, Object> planningConfig = new HashMap<>();
            planningConfig.put("max_steps", 10);
            planningConfig.put("allow_replanning", false);
            List<Map<String, Object>> sceneConfigs = new ArrayList<>();

            if (agentInfo.getScenes() != null) {
                List<Scene> scenes = agentInfo.getScenes();
                // 把每个scene里的每个guidelines里的tools，只取name，并记录每个name,放在每个scene里的tools中
                for (Scene scene : scenes) {
                    Map<String, Object> sceneConfig = new HashMap<>();
                    // id
                    sceneConfig.put("id", scene.getId());
                    // name
                    sceneConfig.put("name", scene.getName());
                    // description
                    sceneConfig.put("description", scene.getDescription());
                    List<Guideline> guidelines = scene.getGuidelines();

                    Set<Object> tools = new HashSet<>();
                    List<Map<String, Object>> guidelineIrMaps = new ArrayList<>();
                    guidelines.forEach(guideline -> {
                        Map<String, Object> guidelineIrMap = new LinkedHashMap<>();
                        List<ToolSkills> guidelineTools = guideline.getTools();
                        List<String> toolArray = new ArrayList<>();
                        if (guidelineTools != null && !guidelineTools.isEmpty()) {
                            toolArray = guidelineTools.stream().map(ToolSkills::getName).toList();
                            for (ToolSkills tool : guidelineTools) {
                                Map<String, String> mpt = new HashMap<>();
                                mpt.put(CommonConstant.NAME, tool.getName());
                                tools.add(mpt);
                            }
                        }
                        guidelineIrMap.put("id", guideline.getId());
                        guidelineIrMap.put("condition", guideline.getCondition());
                        guidelineIrMap.put("action", guideline.getAction());
                        guidelineIrMap.put("tools", toolArray);
                        guidelineIrMaps.add(guidelineIrMap);
                    });
                    // tools
                    sceneConfig.put("tools", tools);
                    // guideline
                    sceneConfig.put("guidelines", guidelineIrMaps);
                    // relations
                    if (scene.getRelations() != null) {
                        sceneConfig.put("relations", scene.getRelations());
                    }
                    sceneConfigs.add(sceneConfig);
                }
            }
            configs.put("scenes", sceneConfigs);
            configs.put("planning", planningConfig);

            // 添加记忆相关配置 — 从 DB 查询完整策略和提取频率，与 workflow IR 路径保持一致
            AgentMemoryConfig memoryConfig = agent.getMemoryConfig();
            if (memoryConfig != null && StringUtils.isNotBlank(memoryConfig.getMemoryRepoId())) {
                String repoId = memoryConfig.getMemoryRepoId();
                MemoryRepoEntity repoEntity = null;
                try {
                    repoEntity = memoryRepoMapper.selectById(repoId);
                } catch (Exception e) {
                    log.warn("Failed to lookup memory repo {} during agent IR generation: {}", repoId, e.getMessage());
                }
                if (repoEntity != null) {
                    MemoryConfigIR memoryConfigIr = new MemoryConfigIR();
                    memoryConfigIr.setMemoryRepoId(repoId);
                    memoryConfigIr.setEnable(true);
                    if (repoEntity.getConversationRound() != null || repoEntity.getTimeSpan() != null) {
                        MemoryConfigIR.ExtractConfig extractConfig = new MemoryConfigIR.ExtractConfig();
                        extractConfig.setMaxChatTurn(repoEntity.getConversationRound());
                        extractConfig.setTimeWindow(repoEntity.getTimeSpan());
                        memoryConfigIr.setExtractConfig(extractConfig);
                    }
                    if (repoEntity.getLongTermMemoryStrategies() != null && !repoEntity.getLongTermMemoryStrategies().isEmpty()) {
                        memoryConfigIr.setStrategies(repoEntity.getLongTermMemoryStrategies());
                    }
                    configs.put("memory", memoryConfigIr);
                } else {
                    log.info("Memory repo {} not found during agent IR generation, using bare config", repoId);
                    configs.put("memory", memoryConfig);
                }
            }
        }

        configs.put("sysPromptTemplate", getSysPromptTemplate(agent));
        configs.put("inputVariables", agent.getInputVariables());
        configs.put("plugins", pluginConfigs);
        configs.put("mcps", mcpConfigs);
        configs.put("mode", StringUtils.isBlank(agent.getSchedulingMode()) ? "ReAct" : agent.getSchedulingMode());
        configs.put("maxIteration", maxIteration);
        configs.put("workflows", workflowConfigs);
        configs.put("workflowSwitchEnabled", agent.getWorkflowSwitchEnabled());
        configs.put("skills", skillConfigs);

        // 内容审核开关打开时，存入IR
        Map<String, Object> reviewObject = JsonUtils.json2Obj(agent.getContentReview(), Constants.MAP_TYPE_REFERENCE);
        Boolean enabled = null;
        if (reviewObject != null) {
            enabled = reviewObject.get(ENABLED) != null ? (Boolean) reviewObject.get(ENABLED) : Boolean.FALSE;
        }
        Boolean safetyBarrier = agent.getSafetyBarrier() != null ? agent.getSafetyBarrier() : Boolean.FALSE;

        configs.put(Constants.Workflow.CONTENT_REVIEW, reviewObject);
        configs.put(Constants.Workflow.SAFETY_BARRIER, safetyBarrier);
        configs.put("context", parseIrContext(agent));

        result.put("configs", configs);
        result.put("metadata", metadata);
        return result;
    }

    /**
     * 根据是否开启引用和归属，选择合适的系统提示词
     * @param agent
     * @return 返回引用的提示词
     */
    private String getSysPromptTemplate(Agent agent) {
        if (agent.getReference() == null || !agent.getReference().isSwitch()) {
            return Optional.ofNullable(agent.getInstructions()).orElse("");
        }
        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(
            isChinese ? PromptPath.REFERENCE_TEMPLATE : PromptPath.REFERENCE_TEMPLATE_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String referenceContent = null;
        if (agent.getReference().isJsonFormat()) {
            referenceContent = CommonUtil.getResourceContent(
                isChinese ? PromptPath.REFERENCE_JSON_FORMATE : PromptPath.REFERENCE_JSON_FORMATE_EN);
        } else {
            referenceContent = CommonUtil.getResourceContent(
                isChinese ? PromptPath.REFERENCE : PromptPath.REFERENCE_EN);
        }

        String query = promptTemplate.format(
            KV.of(CommonConstant.INSTRUCTIONS, Optional.ofNullable(agent.getInstructions()).orElse("")),
            KV.of(CommonConstant.TEMPLATE, referenceContent));

        return query;
    }

    /**
     * 用户输入参数变量转IR
     *
     * @param inputVariables 用户入参
     * @return ir 输入参数结构体
     */
    private List<ConversationInputVariable> parseInputVariables(List<InputVariable> inputVariables) {
        if (CollectionUtils.isEmpty(inputVariables)) {
            log.info("No input variables found");
            return new ArrayList<>();
        }
        List<ConversationInputVariable> conversationInputVariables = new ArrayList<>();
        for (InputVariable inputVariable : inputVariables) {
            ConversationInputVariable conversationInputVariable = new ConversationInputVariable();
            conversationInputVariable.setName(inputVariable.getVariableKey());
            conversationInputVariable.setType(inputVariable.getInputType());
            conversationInputVariable.setDescription(inputVariable.getDescription());
            conversationInputVariable.setDefaultValue(inputVariable.getDefaultValue());
            conversationInputVariable.setRequired(inputVariable.isRequired());
            conversationInputVariables.add(conversationInputVariable);
        }
        return conversationInputVariables;
    }


    /**
     * Agent DeepResearch IR 转换
     * 此方法专为执行深度研究、网络搜索和信息聚合任务的 Agent 进行适配。
     * 其配置侧重于强大的搜索能力、可靠的知识源和分析模型。
     *
     * @param agent agent信息
     * @param metadata 额外参数
     * @return Agent DeepResearch IR
     */
    public Map<String, Object> adaptAgentDeepResearch(AgentInfo agent, Map<String, Object> metadata) {
        Map<String, Object> result = new HashMap<>();

        // 先处理 configs 部分
        Map<String, Object> configs = new HashMap<>();

        configs.put("deep_search_execute_mode", "commercial");

        configs.put("workflow_human_in_the_loop", true);

        configs.put("outliner_max_section_num", agent.getCharacterDr() == null ? outlinerMaxSectionNum : agent.getCharacterDr());

        configs.put("source_tracer_research_trace_source_switch", true);

        // 5. llm_config
        if (agent.getModelConfig() != null) {
            Map<String, Object> modelConfig = new HashMap<>();
            modelConfig.put("model_name",
                agent.getModelDeploymentId() + (StringUtils.isEmpty(agent.getModel()) ? "" : "|" + agent.getModel()));
            modelConfig.put("model_type", "openai");
            modelConfig.put("base_url", "");
            modelConfig.put("api_key", "");
            Map<String, Object> hyperParameters = new HashMap<>();
            hyperParameters.put("temperature",
                Optional.ofNullable(agent.getModelConfig().getTemperature()).orElse(0.2));
            hyperParameters.put("top_p", agent.getModelConfig().getTopP());
            if (agent.getModelConfig().getMaxTokens() != null) {
                hyperParameters.put(CommonConstant.ModelParam.MAX_TOKENS, agent.getModelConfig().getMaxTokens());
            }
            if (agent.getModelConfig().getFrequencyPenalty() != null) {
                hyperParameters.put(CommonConstant.ModelParam.FREQUENCY_PENALTY,
                    agent.getModelConfig().getFrequencyPenalty());
            }
            modelConfig.put("hyperParameters", hyperParameters);

            Map<String, Object> extension = modelServiceManager.parseModelExtension(agent.getModelDeploymentId(),
                agent.getProjectId(), agent.getWorkspaceId(), false);
            if (!Objects.isNull(extension)) {
                modelConfig.put("extension", extension);
            }
            IRUtils.adaptModelExtension(modelConfig);
            configs.put("llm_config", modelConfig);
        } else {
            configs.put("llm_config", null);
        }

        boolean hasSearchEngine = false;
        boolean hasKnowledgeRepos = false;

        // 6. web_search_engine_config
        Map<String, Object> searchEngineConfigs = new HashMap<>();
        if (agent.getSearchEngine() != null && StringUtils.isNotBlank(agent.getSearchEngine().getToolId())) {
            hasSearchEngine = true;
            try {
                ToolReference tool = agent.getSearchEngine();
                String toolId = tool.getToolId();
                if (StringUtils.isNotBlank(toolId)) {
                    ToolEntity toolEntity = pluginService.getToolEntity(toolId, "", "", "");
                    String searchUrl = toolEntity.getRequestInfo() != null ? toolEntity.getRequestInfo().getUrl() : "";
                    String searchApiKey = extractSearchApiKey(toolEntity, toolId);
                    searchEngineConfigs.put("search_engine_name", toolEntity.getToolDisplayName());
                    searchEngineConfigs.put("search_api_key", searchApiKey != null ? searchApiKey : "");
                    searchEngineConfigs.put("search_url", StringUtils.isNotBlank(searchUrl) ? searchUrl : "");
                    searchEngineConfigs.put("max_web_search_results", 5);
                    searchEngineConfigs.put("extension", new HashMap<>());
                }
                if (searchEngineConfigs.isEmpty()) {
                    log.warn("No websearch tool found for agent: {}", agent.getAgentId());
                }
            } catch (Exception e) {
                log.error("Failed to process search engine configuration for agent: {}", agent.getAgentId(), e);
            }
        } else {
            searchEngineConfigs.put("search_engine_name", "petal");
            searchEngineConfigs.put("search_api_key", "");
            searchEngineConfigs.put("search_url", "");
        }
        configs.put("web_search_engine_config", searchEngineConfigs);

        // 7. local_search_engine_config
        Map<String, Object> knowledgeConfigs = new HashMap<>();
        if (agent.getKnowledgeRepos() != null) {
            hasKnowledgeRepos = true;
            knowledgeConfigs.put("search_engine_name", "openapi");
            knowledgeConfigs.put("search_api_key", "");
            List<String> repoIds = agent.getKnowledgeRepos()
                .stream()
                .map(KnowledgeRepoReference::getKnowledgeRepoId)
                .collect(Collectors.toList());
            knowledgeConfigs.put("recall_threshold", 0.5);
            knowledgeConfigs.put("search_datasets", repoIds);
            // 知识库检索改由 Python 端 FlowKnowledgeRetrieval 直接消费 knowledgeConfig，不再回环 HTTP
            List<KnowledgeRepoEntity> knowledgeRepoEntities = relationManagementService.getExistKnowledgeRepos(
                agent.getProjectId(), agent.getWorkspaceId(), repoIds);
            knowledgeConfigs.put("knowledgeConfig",
                buildKnowledgeConfig(knowledgeRepoEntities, agent.getKnowledgeRetrievePolicy(), null));
        } else {
            knowledgeConfigs.put("search_engine_name", "openapi");
            knowledgeConfigs.put("search_api_key", "");
        }
        configs.put("local_search_engine_config", knowledgeConfigs);

        // 8. info_collector_search_method
        // 只有搜索引擎就填web，只有本地知识库就填local，两者都有就all
        String infoCollectorSearchMethod;
        if (hasSearchEngine && hasKnowledgeRepos) {
            infoCollectorSearchMethod = ALL;
        } else if (hasSearchEngine) {
            infoCollectorSearchMethod = WEB;
        } else if (hasKnowledgeRepos) {
            infoCollectorSearchMethod = LOCAL;
        } else {
            infoCollectorSearchMethod = ALL;
        }
        configs.put("info_collector_search_method", infoCollectorSearchMethod);

        // 9. custom_web_search_config
        Map<String, Object> customWebSearchConfig = new HashMap<>();
        customWebSearchConfig.put("custom_web_search_file", "");
        customWebSearchConfig.put("custom_web_search_func", "");
        configs.put("custom_web_search_config", customWebSearchConfig);

        // 10. custom_local_search_config
        Map<String, Object> customLocalSearchConfig = new HashMap<>();
        customLocalSearchConfig.put("custom_local_search_file", "");
        customLocalSearchConfig.put("custom_local_search_func", "");
        configs.put("custom_local_search_config", customLocalSearchConfig);

        // 11. has_template
        configs.put("has_template", agent.getWritingTemplate() != null);

        // 12. is_template
        configs.put("is_template", Boolean.TRUE.equals(agent.isIsTemplate()));

        // 处理 configs 部分结束

        // 现在处理根级别的字段，按照要求的顺序
        result.put("configs", configs);

        result.put("metadata", metadata);

        result.put("schemaVersion", agentIrVersion);

        result.put("agentName", agent.getName());

        result.put("description", agent.getDescription());

        result.put("agentVersion", agentIrVersion);

        // 处理模板路径（如果存在）
        if (agent.getWritingTemplate() != null) {
            result.put("template_path", agent.getWritingTemplate());
        }

        result.put("agentId", agent.getAgentId());

        return result;
    }

    /**
     * 用户可配置参数值和参数可见性
     *
     * @param resourceConfig 资源参数
     * @param extendInfo 用户配置信息
     * @param resourceType 资源类型
     * @return Map<String, Object> pluginConfigAfterParse
     */
    private Map<String, Object> setUserConfig(Map<String, Object> resourceConfig, String extendInfo,
        String resourceType) {
        if (extendInfo == null) {
            return resourceConfig;
        }
        if (resourceConfig.get(ARGUMENTS) != null) {
            // 资源参数
            List<Map<String, Object>> argumentsList =
                objectMapper.convertValue(resourceConfig.get(ARGUMENTS), new TypeReference<>() {});
            // 用户所配置的信息
            List<Map<String, Object>> argumentSettings = parseExtendInfo(extendInfo);
            // 记录引用关系
            Map<String, String> refMap = new HashMap<>();
            // 更新参数
            setArguments(argumentSettings, argumentsList, true, resourceType, refMap, null);

            resourceConfig.put(ARGUMENTS, argumentsList);
            resourceConfig.put(INPUT_PARAMETERS, refMap);
        }
        return resourceConfig;
    }

    /**
     * 处理mcp header 替换记忆变量、引用变量
     * @param resourceConfig mcp config配置
     * @return config
     */
    public Map<String, Object> parseMcpConfigAndReplaceHeaders(Map<String, Object> resourceConfig) {
        log.info("start to parseMcpConfig and replaceHeaders resourceConfig!");
        if (resourceConfig.get(ARGUMENTS) != null) {
            // 资源参数
            List<Map<String, Object>> argumentsList =
                    objectMapper.convertValue(resourceConfig.get(ARGUMENTS), new TypeReference<>() {});

            // headers 参数
            Map<String, Object> headers =
                    objectMapper.convertValue(resourceConfig.get(HEADERS), new TypeReference<>() {});
            Map<String, Object> header =
                    objectMapper.convertValue(headers.get(HEADERS), new TypeReference<>() {});

            if (header == null) {
                resourceConfig.put(HEADERS, new HashMap<>());
                return resourceConfig;
            }

            header.forEach((key, value) -> {
                // 处理每个header
                String userValue = getValueFromArgumentOfMcp(argumentsList, key);

                // 若当前argument中的值，不为null 空，则替换
                if (StringUtils.isNotBlank(userValue)) {
                    header.put(key, CryptoUtils.encrypt(userValue));
                }
            });
            headers.put(HEADERS, header);
            resourceConfig.put(HEADERS, headers);
        }
        return resourceConfig;
    }

    /**
     * 获取用户变量中的参数
     * @param argumentsList 用户配置的用户变量
     * @param targetKey 需要替换的header的key
     * @return value
     */
    private String getValueFromArgumentOfMcp(List<Map<String, Object>> argumentsList, String targetKey) {
        for (Map<String, Object> argumentSetting : argumentsList) {
            // 获取用户变量key value
            String key = String.valueOf(argumentSetting.get("name"));
            String value = String.valueOf(argumentSetting.get("default_value"));

            if (StringUtils.isBlank(key)) {
                continue;
            }

            // 匹配则返回
            if (key.equals(targetKey)) {
                return value;
            }
        }
        return "";
    }

    /**
     * 根据资源类型配置用户参数
     * @param argumentSettings 用户配置信息
     * @param argumentsList 资源参数信息
     * @param isRoot 是否是根
     * @param resourceType 资源类型
     * @param refMap 引用map
     * @param nestedName 引用参数嵌套关系
     */
    private void setArguments(List<Map<String, Object>> argumentSettings, List<Map<String, Object>> argumentsList,
        Boolean isRoot, String resourceType, Map<String, String> refMap, String nestedName) {
        for (Map<String, Object> argumentSetting : argumentSettings) {
            // 参数名称
            String name = String.valueOf(argumentSetting.get("name"));
            // 参数类型
            String type = String.valueOf(argumentSetting.get("type"));
            // 参数是否存在引用
            boolean isRef = false;
            String refKey = null;
            String refDefaultValue = null;

            if (argumentSetting.get("value") != null) {
                String valueString = JSON.toJSONString(argumentSetting.get("value"));
                ResourceParam.ValueDTO value = JSON.parseObject(valueString, ResourceParam.ValueDTO.class);
                String valueType = value.getType();
                // 参数存在引用，需更新refMap，以及defaultValue替换为引用变量的默认值
                if (StringUtils.isNotEmpty(valueType) && valueType.contains(REF_PARAMETERS_TYPE)) {
                    isRef = true;
                    refKey = JSONArray.parseArray(JSONArray.toJSONString(value.getContent()))
                        .getJSONObject(0)
                        .getString("variable_key");
                    refDefaultValue = JSONArray.parseArray(JSONArray.toJSONString(value.getContent()))
                        .getJSONObject(0)
                        .getString("default_value");
                    String finalName = nestedName == null ? name : nestedName + name;
                    // literal手动输入 mem_ref 记忆动参变量  input_ref 用户动参变量
                    if (REF_PARAMETERS_TYPE.equalsIgnoreCase(valueType) || MEMORY_PARAMETERS_TYPE.equalsIgnoreCase(
                        valueType)) {
                        refMap.put(finalName, "{{memory." + refKey + "}}");
                    } else if (INPUT_PARAMETERS_TYPE.equalsIgnoreCase(valueType)) {
                        refMap.put(finalName, "{{inputs." + refKey + "}}");
                    }
                }

                // 查找匹配的参数，避免重复遍历
                Map<String, Object> matchedArgument = null;
                for (Map<String, Object> argument : argumentsList) {
                    if (name.equals(argument.get(NAME))) {
                        matchedArgument = argument;
                        break;
                    }
                }
                if (matchedArgument == null) {
                    continue;
                }

                // TOOL
                if (TOOL.equals(resourceType)) {
                    // visibility字段放在根处
                    if (isRoot) {
                        matchedArgument.put(VISIBLE, argumentSetting.get(VISIBLE));
                    }
                    // 参数为Object类型，叶子节点参数设置需要放在schema叶子节点配置处
                    if ("object".equals(type)) {
                        // 处理Object类型，schema字段
                        List<Map<String, Object>> schemaUserSetting =
                            objectMapper.convertValue(argumentSetting.get("schema"), new TypeReference<>() {});
                        List<Map<String, Object>> schemaPlugin =
                            objectMapper.convertValue(matchedArgument.get("schema"), new TypeReference<>() {});
                        nestedName = name + ".";
                        setArguments(schemaUserSetting, schemaPlugin, false, TOOL, refMap, nestedName);
                        matchedArgument.put("schema", schemaPlugin);
                    } else {
                        // 将默认值替换为用户输入的值，若参数引用，其为引用参数的默认值
                        Object defaultValue =
                            isRef ? refDefaultValue : convertDefaultValue(String.valueOf(value.getContent()), type);
                        matchedArgument.put(DEFAULT_VALUE, defaultValue);
                    }
                }
                // WORKFLOW
                if (WORKFLOW.equals(resourceType)) {
                    // visibility, required字段放在根处
                    if (isRoot) {
                        matchedArgument.put(VISIBLE, argumentSetting.get(VISIBLE));
                        matchedArgument.put(REQUIRED, argumentSetting.get(REQUIRED));
                    }

                    // 参数为Object类型，叶子节点参数设置需要放在schema叶子节点配置处
                    if ("object".equals(type)) {
                        // 处理Object类型，schema字段
                        List<Map<String, Object>> schemaUserSetting =
                            objectMapper.convertValue(argumentSetting.get("schema"), new TypeReference<>() {});
                        List<Map<String, Object>> schemaPlugin =
                            objectMapper.convertValue(matchedArgument.get("schema"), new TypeReference<>() {});
                        nestedName = name + ".";
                        setArguments(schemaUserSetting, schemaPlugin, false, WORKFLOW, refMap, nestedName);
                        matchedArgument.put("schema", schemaPlugin);
                    } else {
                        // 将默认值替换为用户输入的值，若参数引用，其为引用参数的默认值
                        Object defaultValue =
                            isRef ? refDefaultValue : convertDefaultValue(String.valueOf(value.getContent()), type);
                        matchedArgument.put(DEFAULT_VALUE, defaultValue);
                    }
                }

                // MCP
                if (MCP_TYPE.equals(resourceType)) {
                    // visibility, mcp默认都使用false
                    if (isRoot) {
                        matchedArgument.put(VISIBLE, false);
                        matchedArgument.put(REQUIRED, false);
                    }

                    // 将默认值替换为用户输入的值，若参数引用，其为引用参数的默认值
                    Object defaultValue =
                            isRef ? refDefaultValue : convertDefaultValue(String.valueOf(value.getContent()), type);
                    matchedArgument.put(DEFAULT_VALUE, defaultValue);
                }
            }
        }
    }

    /**
     * 解析extendInfo
     * @param extendInfo 额外用户配置信息
     * @return List<Map<String, Object>>
     */
    public List<Map<String, Object>> parseExtendInfo(String extendInfo) {
        // 解析JSON字符串为List<ResourceParam>
        List<ResourceParam> resourceParams = JSON.parseArray(extendInfo, ResourceParam.class);
        List<Map<String, Object>> filteredParams = new ArrayList<>();
        // 遍历解析后的对象，提取所需字段
        for (ResourceParam param : resourceParams) {
            Map<String, Object> filteredParam = new HashMap<>();
            filteredParam.put("name", param.getName());
            filteredParam.put("description", param.getDescription());
            filteredParam.put("type", param.getType());
            filteredParam.put("required", param.isRequired());
            filteredParam.put("visible", param.isVisibility());
            if (param.getValue() != null) {
                filteredParam.put("value", param.getValue());
            }
            if (param.getSchema() != null) {
                filteredParam.put("schema", param.getSchema());
            }
            filteredParams.add(filteredParam);
        }
        return filteredParams;
    }

    private void parseAgentKnowledgeRepo(Agent agent, String projectId, String workspaceId,
        List<Map<String, Object>> pluginConfigs) {
        List<MappingEntity> agentKnowledgeList =
            mappingMapper.selectByAppIdAndResourceType(agent.getAgentId(), CommonConstant.REPO_TYPE);
        List<String> agentKnowledgeIdList = agentKnowledgeList.stream().map(MappingEntity::getResourceId).toList();
        if (!CollectionUtils.isEmpty(agentKnowledgeIdList)) {
            List<KnowledgeRepoEntity> knowledgeRepoEntities =
                relationManagementService.getExistKnowledgeRepos(projectId, workspaceId, agentKnowledgeIdList);
            if (!CollectionUtils.isEmpty(knowledgeRepoEntities)) {
                Map<String, Object> repoPlugin =
                    parseKnowledgeRepoPlugin(knowledgeRepoEntities, agent.getKnowledgeRetrievePolicy(), true);
                pluginConfigs.add(repoPlugin);
            }
        }
    }

    /**
     * 转换知识库对应的IR（将知识库看做插件）
     *
     * @param knowledgeRepoEntities 知识库列表
     * @param policy KnowledgeRetrievePolicy
     * @param isAgent 是否是AI应用绑定的知识库
     * @return IR
     */
    public Map<String, Object> parseKnowledgeRepoPlugin(List<KnowledgeRepoEntity> knowledgeRepoEntities,
        KnowledgeRetrievePolicy policy, boolean isAgent) {
        return parseKnowledgeRepoPlugin(knowledgeRepoEntities, policy, isAgent, null);
    }

    /**
     * 转换知识库对应的IR（将知识库看做插件）
     *
     * @param knowledgeRepoEntities 知识库列表
     * @param policy                KnowledgeRetrievePolicy
     * @param isAgent               是否是AI应用绑定的知识库
     * @param tags                  知识库标签列表
     * @return IR
     */
    public Map<String, Object> parseKnowledgeRepoPlugin(List<KnowledgeRepoEntity> knowledgeRepoEntities,
        KnowledgeRetrievePolicy policy, boolean isAgent, List<String> tags) {
        Map<String, Object> repoPlugin = new HashMap<>();
        KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoEntities.get(0);
        repoPlugin.put(ID, knowledgeRepoEntity.getKnowledgeRepoId());
        repoPlugin.put(NAME, "retrieval");
        String name = String.join("|", knowledgeRepoEntities.stream().map(KnowledgeRepoEntity::getDisplayName).toList());
        repoPlugin.put(DESCRIPTION, "useful for when you want to answer queries about the " + name);

        repoPlugin.put(METHOD, CommonConstant.POST_METHOD);
        // 定义知识库插件的鉴权信息，调用Agent-Runtime
        repoPlugin.put(AUTH, getRetrievalAuth());
        // 补充与工作流知识库节点一致的内部配置，供 Python 运行时直接消费。
        repoPlugin.put("knowledgeConfig", buildKnowledgeConfig(knowledgeRepoEntities, policy, tags));

        // 定义知识库插件的输入参数和输出参数
        List<KnowledgeReqIrBody> knowledgeReqIrBodies = generateKnowledgeBody(knowledgeRepoEntities, policy);
        repoPlugin.put(ARGUMENTS, getKnowledgePluginIrElements(JsonUtils.toJson(knowledgeReqIrBodies)));
        repoPlugin.put(RESPONSE,
            getKnowledgePluginIrElements(isAgent ? knowledgeAgentResponseIr : knowledgeWorkflowResponseIr));

        return repoPlugin;
    }

    private Map<String, Object> buildKnowledgeConfig(List<KnowledgeRepoEntity> knowledgeRepoEntities,
        KnowledgeRetrievePolicy policy, List<String> tags) {
        Map<String, Object> knowledgeConfig = new HashMap<>();
        if (CollectionUtils.isEmpty(knowledgeRepoEntities)) {
            return knowledgeConfig;
        }

        knowledgeConfig.put("connectionId", knowledgeRepoEntities.get(0).getConnectionId());
        knowledgeConfig.put("knowledgeBaseIds", knowledgeRepoEntities.stream()
            .map(KnowledgeRepoEntity::getKnowledgeRepoId)
            .toList());

        Map<String, Object> retrievalConfig = new HashMap<>();
        if (policy != null) {
            if (policy.getTopK() != null) {
                retrievalConfig.put("topK", policy.getTopK());
            }
            if (policy.getRecallThreshold() != null) {
                retrievalConfig.put("scoreThreshold", policy.getRecallThreshold());
                retrievalConfig.put("recallThreshold", policy.getRecallThreshold());
            }
            if (policy.getFaqThreshold() != null) {
                retrievalConfig.put("faqThreshold", policy.getFaqThreshold());
            }
            if (policy.getSearchMode() != null) {
                retrievalConfig.put("searchMode", policy.getSearchMode().toString());
            }
            retrievalConfig.put("needExtrasFaqSearch", policy.isNeedExtrasFaqSearch());
            retrievalConfig.put("retrieveImage", policy.isRetrieveImage());
            retrievalConfig.put("showSource", policy.isShowSource());
        }

        List<String> mergedTags = !CollectionUtils.isEmpty(tags)
            ? new ArrayList<>(tags)
            : knowledgeRepoEntities.stream()
                .filter(item -> !CollectionUtils.isEmpty(item.getTag()))
                .flatMap(item -> item.getTag().stream())
                .collect(Collectors.toCollection(ArrayList::new));
        if (!CollectionUtils.isEmpty(mergedTags)) {
            retrievalConfig.put("tags", mergedTags);
        }

        knowledgeConfig.put("retrievalConfig", retrievalConfig);
        return knowledgeConfig;
    }

    private KnowledgeReqIrBody generateSingleBodyField(List<KnowledgeReqIrBody> schema, String name, String description,
        Object defaultValue, String type) {
        return KnowledgeReqIrBody.builder()
            .schema(schema)
            .name(name)
            .description(description)
            .defaultValue(defaultValue)
            .type(type)
            .visible(false)
            .build();
    }

    private KnowledgeReqIrBody generateSingleSchema(String name, String type) {
        return KnowledgeReqIrBody.builder().name(name).type(type).build();
    }

    private List<KnowledgeReqIrBody> generateKnowledgeBody(List<KnowledgeRepoEntity> knowledgeRepoEntities,
        KnowledgeRetrievePolicy policy) {
        List<Map<String, Object>> knowledgeBases = getKnowledgeBases(knowledgeRepoEntities);

        List<KnowledgeReqIrBody> knowledgeReqIrBodies = new ArrayList<>();

        KnowledgeReqIrBody queryReq = KnowledgeReqIrBody.builder()
            .name(QUERY)
            .description("Query for the dataset to be used to retrieve the dataset.")
            .type(JsonSchemaType.STRING.type)
            .visible(true)
            .build();

        KnowledgeReqIrBody knowledgeId = generateSingleSchema(ID, JsonSchemaType.STRING.type);
        KnowledgeReqIrBody knowledgeTags = generateSingleSchema("tags", JsonSchemaType.ARRAY_STRING.type);
        List<KnowledgeReqIrBody> schema = new ArrayList<>();
        schema.add(knowledgeId);
        schema.add(knowledgeTags);
        knowledgeReqIrBodies.add(queryReq);
        knowledgeReqIrBodies.add(
            generateSingleBodyField(schema, "knowledge_bases", "知识库id和标签集合", knowledgeBases, JsonSchemaType.ARRAY_OBJECT.type));

        if (!Objects.isNull(policy)) {
            if (!Objects.isNull(policy.getTopK())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, TOP_K, "知识库节点文档返回数目", policy.getTopK(),
                        JsonSchemaType.INTEGER.type));
            }
            if (!Objects.isNull(policy.getRecallThreshold())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, RECALL_THRESHOLD, "知识库阈值", policy.getRecallThreshold(),
                        JsonSchemaType.NUMBER.type));
            }
            if (!Objects.isNull(policy.getFaqThreshold())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, FAQ_THRESHOLD, "知识库FAQ直出阈值键值", policy.getFaqThreshold(),
                        JsonSchemaType.NUMBER.type));
            }
            if (!Objects.isNull(policy.getSearchMode())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, SEARCH_MODE, "知识库检索模式", policy.getSearchMode(),
                        JsonSchemaType.STRING.type));
            }
            if (!Objects.isNull(policy.isNeedExtrasFaqSearch())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, NEED_EXTRAS_FAQ_SEARCH, "FAQ拓展搜索", policy.isNeedExtrasFaqSearch(),
                        JsonSchemaType.BOOLEAN.type));
            }
            if (!Objects.isNull(policy.isRetrieveImage())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, RETRIEVE_IMAGE, "召回图片", policy.isRetrieveImage(),
                        JsonSchemaType.BOOLEAN.type));
            }
            if (!Objects.isNull(policy.isShowSource())) {
                knowledgeReqIrBodies.add(
                    generateSingleBodyField(null, SHOW_SOURCE, "展示来源", policy.isShowSource(),
                        JsonSchemaType.BOOLEAN.type));
            }
        }
        return knowledgeReqIrBodies;
    }

    public Map<String, Object> parseWorkflowPlugin(WorkflowEntity workflowEntity) {
        Map<String, Object> workflowPlugin = new HashMap<>();
        workflowPlugin.put(ID, workflowEntity.getId());
        workflowPlugin.put(NAME, workflowEntity.getCode());
        workflowPlugin.put(DESCRIPTION, workflowEntity.getDescription());
        workflowPlugin.put(IR_PATH, workflowEntity.getIrPath());

        // 解析workflow输入输出参数
        String workflowJson = mgObsService.downloadObsFile(workflowEntity.getDslPath());
        WorkflowVO workflowDetail = JSON.parseObject(workflowJson, WorkflowVO.class);
        List<WorkflowNodeVO> workflowNodes = workflowDetail.getNodes();
        WorkflowNodeVO startNode = WorkflowUtils.getWorkflowNodeID(INPUT_KEY, workflowNodes);
        List<WorkflowFieldVO> inputs = startNode == null ? null : startNode.getOutputs();
        WorkflowNodeVO endNode = WorkflowUtils.getWorkflowNodeID(OUTPUT_KEY, workflowNodes);
        List<WorkflowFieldVO> outputs = endNode == null ? null : endNode.getInputs();

        // 过滤sys参数
        List<Map<String, Object>> arguments = parseWorkflowPluginParams(inputs);
        if (arguments != null) {
            arguments = arguments.stream()
                .filter(m -> m.get(NAME) != null && !Strings.CS.equals(m.get(NAME).toString(), CommonConstant.SYS))
                .toList();
        }
        workflowPlugin.put(ARGUMENTS, arguments);
        workflowPlugin.put(RESPONSE, parseWorkflowPluginParams(outputs));
        return workflowPlugin;
    }

    private void parsePluginParamType(Map<String, Object> param, WorkflowFieldVO workflowField) {
        String fieldType = WorkflowUtils.formatWorkflowType(workflowField.getType());
        param.put(TYPE,
            JsonSchemaType.ARRAY.type.equals(fieldType)
                ? String.format("array<%s>",
                WorkflowUtils
                    .formatWorkflowType(JSON.parseObject(workflowField.getSchema().toString()).getString("type")))
                : fieldType);

        // array<object>类型
        if (JsonSchemaType.ARRAY.type.equals(fieldType) && JsonSchemaType.OBJECT.type.equals(
            WorkflowUtils.formatWorkflowType(JSON.parseObject(workflowField.getSchema().toString()).getString(TYPE)))) {
            param.put(SCHEMA, parseWorkflowPluginParams(JSON.parseArray(
                JSON.parseObject(workflowField.getSchema().toString()).getString(SCHEMA), WorkflowFieldVO.class)));
        }

        // object类型
        if (JsonSchemaType.OBJECT.type.equals(fieldType)) {
            param.put(SCHEMA, parseWorkflowPluginParams(
                JSON.parseArray(workflowField.getSchema().toString(), WorkflowFieldVO.class)));
        }
        param.entrySet().removeIf(entry -> Objects.isNull(entry.getValue()));
    }

    /**
     * 将知识库插件IR中的元素字符串（arguments/response），转换成java对象
     *
     * @param jsonStr 知识库插件IR中的元素字符串
     * @return JSONArray
     */
    private JSONArray getKnowledgePluginIrElements(String jsonStr) {
        try {
            JSONArray jsonArray = JSON.parseArray(jsonStr);
            if (Objects.isNull(jsonArray)) {
                log.warn("Knowledge plugin elements is null after parse [{}]", jsonStr);
                return new JSONArray();
            }
            return jsonArray;
        } catch (JSONException exception) {
            log.warn("Fail to parse knowledge plugin elements [{}], for [{}]", jsonStr, exception.getMessage());
            return new JSONArray();
        }
    }

    private List<Map<String, Object>> getKnowledgeBases(List<KnowledgeRepoEntity> knowledgeRepoEntities) {
        return knowledgeRepoEntities.stream().map(item -> {
            Map<String, Object> map = new HashMap<>();
            map.put(ID, item.getKnowledgeRepoId());
            map.put("tags", item.getTag());
            map.put("connection_id", item.getConnectionId());
            return map;
        }).collect(Collectors.toList());
    }

    /**
     * 获取知识库插件的鉴权信息
     *
     * @return 鉴权信息IR
     */
    private AuthUserConfig getRetrievalAuth() {
        AuthUserConfig authUserConfig = new AuthUserConfig();
        authUserConfig.setScope(AuthInfo.ScopeEnum.USER.toString());
        AuthUserConfig.Info authInfo = new AuthUserConfig.Info();
        authInfo.setDomain(HEADERS);
        List<String> params = new ArrayList<>();
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            HttpHeaders header = RequestContextUtils.getHeader();
            if (!CollectionUtils.isEmpty(header.get(Constants.CustomModel.CUSTOM_USER_ID))) {
                params.add(CommonConstant.CustomModel.CUSTOM_USER_ID);
            }
            if (!CollectionUtils.isEmpty(header.get(Constants.CustomModel.CUSTOM_TOKEN))) {
                params.add(CommonConstant.CustomModel.CUSTOM_TOKEN);
            }
        }
        params.add(CommonConstant.X_AUTH_TOKEN);
        authInfo.setAuthKeys(params);
        authUserConfig.setSource(authInfo);
        authUserConfig.setTarget(authInfo);
        return authUserConfig;
    }

    // 解析复杂节点
    private Map<String, String> parseComplexNodePair(WorkflowVO workflow) {
        Map<String, String> complexIntentMap = new HashMap<>();
        String intentField = "intent";
        for (WorkflowNodeVO node : workflow.getNodes()) {
            if (node.getType().equals(NodeType.INTENT_COMPLEX_INTENT.getType())
                && !Objects.isNull(node.getConfigs().get(intentField))) {
                Map<String, String> intents = JsonUtils.objectToClass(node.getConfigs().get(intentField));
                if (intents != null) {
                    intents.put("repo_id", complexIntentRepoId);
                }
                node.getConfigs().put(intentField, intents);
            }

            if (StringUtils.isEmpty(node.getType())
                || !node.getType().equals(NodeType.INTENT_DETECTION_CONTAINER.getType())) {
                continue;
            }

            boolean isCorrect = false;
            for (WorkflowEdgeVO edge : workflow.getEdges()) {
                if (node.getId().equals(edge.getTarget())) {
                    complexIntentMap.put(edge.getSource(), edge.getTarget());
                    isCorrect = true;
                    break;
                }
            }

            if (!isCorrect) {
                throw new AgentStudioException(StudioError.WORKFLOW_IR_ERROR_COMPLEX_INTENT_NODE);
            }
        }
        return complexIntentMap;
    }

    private void logAddParallelTagResult(List<WorkflowEdgeVO> workflowEdges, List<WorkflowValidationVOErrors> errors) {
        if (!errors.isEmpty()) {
            log.warn("addParallelTag errors: {}",
                errors.stream()
                    .map(error -> String.format("nodeId=%s type=%s \nreason: %s", error.getId(), error.getType(),
                        error.getReason()))
                    .collect(Collectors.joining(", ")));
        } else {
            log.info("add parallel tags to workflow node finished:\n{}",
                workflowEdges.stream()
                    .filter(edge -> !StringUtils.isAllEmpty(edge.getSourceBranchId(), edge.getTargetBranchId()))
                    .map(workflowEdgeVo -> String.format("[%s(%s)->%s%s%s]", workflowEdgeVo.getSource(),
                        StringUtils.defaultString(workflowEdgeVo.getBranch()), workflowEdgeVo.getTarget(),
                        StringUtils.isEmpty(workflowEdgeVo.getSourceBranchId()) ? ""
                            : " source_" + workflowEdgeVo.getSourceBranchId(),
                        StringUtils.isEmpty(workflowEdgeVo.getTargetBranchId()) ? ""
                            : " target_" + workflowEdgeVo.getTargetBranchId()))
                    .collect(Collectors.joining("\n")));
        }
    }

    private IrContext parseIrContext(Agent agent) {
        boolean agentVariablesEnable = !CollectionUtils.isEmpty(agent.getAgentVariables());
        IrContext context = new IrContext();
        context.setOpenMemory(agentVariablesEnable);
        List<ConversationVariable> variables = org.apache.commons.lang3.ObjectUtils
            .firstNonNull(agent.getAgentVariables(), Collections.<AgentVariable>emptyList())
            .stream()
            .map(item -> ConversationVariable.builder()
                .name(item.getVariableKey())
                .description(item.getDescription())
                .defaultValue(item.getDefaultValue())
                .build())
            .toList();
        context.setConversationVariables(variables);
        return context;
    }

    private String getKnowledgeFilterString(List<String> tags) {
        StringBuilder filterString = new StringBuilder();

        if (!KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            filterString.append("tags:");
        }
        filterString.append(escapeQueryValue(tags.get(0)));
        for (int i = 1; i < tags.size(); i++) {
            filterString.append(" OR ").append(escapeQueryValue(tags.get(i)));
        }
        return filterString.toString();
    }

    // 转义Elasticsearch特殊字符
    private String escapeQueryValue(String value) {
        // 转义保留字符: + - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ /
        return value.replaceAll("([\\\\+\\-=&|!(){}\\[\\]^\"~*?:/])", "\\\\$1").replace(" ", "\\ ");
    }

    // 对默认值的最大长度进行校验
    public Boolean validMaxDefaultValueLength(Object object) {
        return Objects.requireNonNull(JsonUtils.toJson(object)).length() <= maxDefaultValueLength + 2;
    }
}
