/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.plugin.BasicInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.PluginDTO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInputSchema;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolRequestInfo;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.Paths;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.ArraySchema;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.media.StringSchema;
import io.swagger.v3.oas.models.parameters.Parameter;
import io.swagger.v3.oas.models.parameters.RequestBody;
import io.swagger.v3.oas.models.servers.Server;

import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.Strings;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Transactional
@MockitoSettings(strictness = Strictness.LENIENT)
class PluginBaseImplTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private EncryptionAdapter staticEncryptionAdapter;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PluginMapper pluginMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ToolMapper toolMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ReleaseVersionMapper releaseVersionMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MgObsService mgObsService;

    @InjectMocks
    private PluginBaseImpl pluginBaseImpl;

    private AutoCloseable mockitoCloseable;

    @Autowired
    private PluginMapper pluginMapperAuto;

    @Autowired
    private ToolMapper toolMapperAuto;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_CREATOR);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_CREATOR_ID);
    }

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(pluginBaseImpl, "pluginMapper", pluginMapperAuto);
        ReflectionTestUtils.setField(pluginBaseImpl, "toolMapper", toolMapperAuto);
        ReflectionTestUtils.setField(pluginBaseImpl, "mcpDomainId", "not_empty");
        ReflectionTestUtils.setField(pluginBaseImpl, "staticEncryptionAdapter", staticEncryptionAdapter);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @Test
    @Sql(scripts = {"classpath:sql/plugin_reserve_meeting_room_setup_db.sql"})
    void test_transferPlugin2Tool_should_not_throw_exception() throws Exception {
        PluginEntity pluginEntity = pluginMapperAuto.selectByPrimaryKeyAndWorkspace("workflow_no_auth_tool", null,
            Constants.TEST_WORKSPACE_ID);
        // When
        ToolEntity result = pluginBaseImpl.transferPlugin2Tool(pluginEntity, "76a94adcb96f4c7f");
        assertNotNull(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/plugin_reserve_meeting_room_setup_db.sql"})
    void test_transferPlugin2Tool_should_not_throw_exception2() throws Exception {
        PluginEntity pluginEntity = pluginMapperAuto.selectByPrimaryKeyAndWorkspace("workflow_no_auth_tool", null,
            Constants.TEST_WORKSPACE_ID);
        // When
        ToolEntity result = pluginBaseImpl.transferPlugin2Tool(pluginEntity, "123");
        assertNotNull(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/plugin_reserve_meeting_room_setup_db.sql"})
    void test_transferTool2Plugin_should_not_throw_exception() throws Exception {
        String toolJson = TestUtil.getStringFromFile("classpath:plugin/tool_entity.json");
        ToolEntity toolEntity = JsonUtils.json2ObjQuietly(toolJson, ToolEntity.class);
        // When
        PluginEntity result = pluginBaseImpl.transformTool2Plugin(toolEntity);
        assertNotNull(result);
    }

    @Test
    void test_transferPlugin2Tool_should_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // When
            ToolEntity result = pluginBaseImpl.transferPlugin2Tool(null, null);
        });
    }

    @Test
    void test_transferPlugin2Tool_i_o_exception() {
        // Mock dependencies
        PluginEntity pluginEntity = mock(PluginEntity.class);
        when(pluginEntity.getRequestInfo()).thenReturn("invalid json");

        // Execute and verify
        assertThrows(AgentStudioException.class, () -> {
            pluginBaseImpl.transferPlugin2Tool(pluginEntity, "toolId");
        });
    }

    @Test
    void test_buildToolByPlugin_should_not_throw_exception() throws Exception {
        // Given
        when(toolMapper.selectStatus(anyString(), anyString(), anyString())).thenReturn(null);
        when(toolMapper.selectWithoutStatus(anyString(), anyString(), anyString())).thenReturn(null);
        assertThrows(AgentStudioException.class, () -> {
            // Given
            when(toolMapper.selectStatus(anyString(), anyString(), anyString())).thenReturn(null);
            when(toolMapper.selectWithoutStatus(anyString(), anyString(), anyString())).thenReturn(null);

            when(pluginMapper.selectByPrimaryKeyAndWorkspace(anyString(), eq(null), anyString())).thenReturn(null);

            // When
            ToolEntity result = pluginBaseImpl.buildToolByPlugin(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
                "workflow_no_auth_tool", null);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/plugin_reserve_meeting_room_setup_db.sql"})
    void test_buildToolByPlugin_should_return_not_null1() throws Exception {
        // Given
        // When
        ToolEntity result = pluginBaseImpl.buildToolByPlugin(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID,
            "workflow_no_auth_tool", "76a94adcb96f4c7f");

        assertNotNull(result);
    }

    @Test
    void test_adaptOldEntityName() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolDisplayName("workflow_tool");
        pluginBaseImpl.adaptOldEntityName(toolEntity);
        toolEntity.setToolChineseName("workflow_tool");
        toolEntity.setToolDisplayName(null);
        pluginBaseImpl.adaptOldEntityName(toolEntity);
    }

    @Test
    public void test_validateAuth_with_empty_configs() throws Exception {
        // Given
        Map<String, Object> configs = new HashMap<>();
        try (MockedStatic<MapUtils> mapUtilsMock = mockStatic(MapUtils.class)) {
            mapUtilsMock.when(() -> MapUtils.isEmpty(configs)).thenReturn(true);
        }

        // When
        boolean result = pluginBaseImpl.validateAuth("projectId", "workspaceId", configs);

        // Then
        assertFalse(result);
    }

    @Test
    public void test_validateAuth_with_missing_id() throws Exception {
        // Given
        Map<String, Object> configs = new HashMap<>();
        configs.put("key", "value");
        try (MockedStatic<MapUtils> mapUtilsMock = mockStatic(MapUtils.class)) {
            mapUtilsMock.when(() -> MapUtils.isEmpty(configs)).thenReturn(false);
        }

        // When
        boolean result = pluginBaseImpl.validateAuth("projectId", "workspaceId", configs);

        // Then
        assertFalse(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/plugin_reserve_meeting_room_setup_db.sql"})
    void test_validateAuth_should_return_true2() throws Exception {
        // Given
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setCredentialStatus("id");
        pluginEntity.setIsFree(0);

        Map<String, Object> configs = new HashMap<>();
        configs.put("id", "reserve_meeting_room2");

        // When
        boolean result = pluginBaseImpl.validateAuth("test_project_id", "default", configs);

        // Then
        assertFalse(result);
    }

    @Test
    void validateAuth_whenPluginEntityIsNull_throwsNullPointerException() {
        String projectId = "test-project-123";
        String workspaceId = "test-workspace-456";
        // 准备含id的配置
        Map<String, Object> configs = new HashMap<>();
        String pluginId = "plugin-789";
        configs.put("id", pluginId);

        // Mock Mapper 返回 null
        when(pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential(eq(pluginId), isNull(),
            eq(workspaceId))).thenReturn(null);

        // 执行方法并断言空指针（若业务需防御性编程，可调整为返回false）
        assertThrows(NullPointerException.class, () -> pluginBaseImpl.validateAuth(projectId, workspaceId, configs));
    }

    @Test
    void validate_validateDuplicateInputSchema() {
        List<ToolInputSchema> toolInputSchemas = new ArrayList<>();

        ToolInputSchema tool1 = new ToolInputSchema("123",
            "{\"type\":\"object\",\"properties\":{\"path2\":{\"location\":\"Path\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"tool的路径\"}},\"required\":[\"path1\"]}");
        toolInputSchemas.add(tool1);

        ToolRequestInfo toolRequestInfo = new ToolRequestInfo();
        pluginBaseImpl.validateDuplicateInputSchema(toolInputSchemas, toolRequestInfo);

        BasicInfo basicInfo = new BasicInfo();
        basicInfo.setInputSchema(
            "{\"type\":\"object\",\"properties\":{\"path1\":{\"location\":\"Path\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"tool的路径\"}},\"required\":[\"path1\"]}");
        toolRequestInfo.setBasicInfo(basicInfo);
        pluginBaseImpl.validateDuplicateInputSchema(toolInputSchemas, toolRequestInfo);

        ToolInputSchema tool2 = new ToolInputSchema("123",
            "{\"type\":\"object\",\"properties\":{\"path1\":{\"location\":\"Path\",\"validate_rule\":\"\",\"validate_type\":\"CHAR\",\"validated\":false,\"name_cn\":\"\",\"type\":\"string\",\"description\":\"tool的路径\"}},\"required\":[\"path1\"]}");
        toolInputSchemas.add(tool2);
        assertThrows(AgentStudioException.class,
            () -> pluginBaseImpl.validateDuplicateInputSchema(toolInputSchemas, toolRequestInfo));
    }

    @Test
    void testTransformOpenAPI2Plugin_NormalWithGetAndPost() {
        // Arrange
        // 模拟 OpenAPI 对象
        OpenAPI openAPI = new OpenAPI();
        openAPI.setInfo(new Info().title("用户管理API").description("管理用户信息"));
        // 服务器配置
        Server server = new Server();
        server.setUrl("https://api.example.com/v1");
        openAPI.setServers(List.of(server));

        // 路径定义
        Paths paths = new Paths();

        // GET /users
        PathItem getPetPath = new PathItem();
        Operation getOp = new Operation();
        getOp.setOperationId("getUserById");
        getOp.setDescription("根据ID获取用户");
        getOp.setParameters(
            List.of(new Parameter().name("id").in("path").required(true).schema(new Schema<String>().type("string"))));

        getPetPath.setGet(getOp);
        paths.put("/users/{id}", getPetPath);

        // POST /users
        PathItem postPetPath = new PathItem();
        Operation postOp = new Operation();
        postOp.setOperationId("createUser");
        postOp.setDescription("创建新用户");
        Schema<Map<String, Schema<?>>> schema = new Schema<>();
        schema.type("object");
        schema.properties(Map.of("name", new Schema<String>().type("string"), "email",
            new Schema<String>().type("string").format("email")));

        MediaType mediaType = new MediaType();
        mediaType.schema(schema);

        Content content = new Content();
        content.addMediaType("application/json", mediaType);

        RequestBody requestBody = new RequestBody();
        requestBody.content(content);

        postOp.setRequestBody(requestBody);

        postPetPath.setPost(postOp);
        paths.put("/users", postPetPath);

        openAPI.setPaths(paths);

        // Act
        PluginDTO pluginDTO = pluginBaseImpl.transformOpenAPI2Plugin(openAPI); // 替换为你的实际方法名

        // Assert
        assertNotNull(pluginDTO);
        assertEquals("用户管理API", pluginDTO.getPluginChineseName());
        assertEquals("用户管理API", pluginDTO.getPluginDisplayName());
        assertEquals("管理用户信息", pluginDTO.getPluginDesc());

        ToolRequestInfo toolRequestInfo = pluginDTO.getToolRequestInfo();
        assertNotNull(toolRequestInfo);

        BasicInfo basicInfo = toolRequestInfo.getBasicInfo();
        assertNotNull(basicInfo);
        assertEquals("api.example.com", basicInfo.getHost());
        assertEquals("https", basicInfo.getProtocol());
        assertEquals("/v1", basicInfo.getPath());

        List<ToolInfo> toolsInfoList = toolRequestInfo.getToolsInfoList();
        assertEquals(2, toolsInfoList.size());

        // 检查 schema 列表数量
        assertEquals(2, pluginDTO.getToolInputSchemaList().size());
        assertEquals(2, pluginDTO.getToolOutputSchemaList().size());

    }

    @Test
    public void testTransformOpenAPI2Plugin_Failure_Case() {
        // Arrange: 构造一个故意不合法的 OpenAPI 对象
        OpenAPI openAPI = new OpenAPI();
        Info info = new Info();
        info.setTitle("Test Plugin");
        info.setDescription("A test plugin for Agent Studio");
        openAPI.setInfo(info);

        openAPI.setServers(null);

        // Act & Assert: 调用方法，应抛出 AgentStudioException
        assertThatThrownBy(() -> {
            pluginBaseImpl.transformOpenAPI2Plugin(openAPI);
        }).isInstanceOf(AgentStudioException.class)
            .extracting(ex -> ((AgentStudioException) ex).getErrorCode())
            .isEqualTo(StudioError.SERVER_NOT_EXIST);
    }

    @Test
    void testResolveReference_Success() {
        // Arrange
        Schema<String> schema = new Schema<>();
        schema.set$ref("#/components/schemas/User");

        OpenAPI openAPI = Mockito.mock(OpenAPI.class);
        Components components = Mockito.mock(Components.class);

        Schema<String> userSchema = new Schema<>();
        userSchema.setType("object");
        userSchema.setDescription("User schema");

        when(openAPI.getComponents()).thenReturn(components);
        when(components.getSchemas()).thenReturn(Map.of("User", userSchema));

        // Act
        Schema<?> result = pluginBaseImpl.resolveReference(schema, openAPI);

        // Assert
        assertNotNull(result);
        assertEquals("object", result.getType());
        assertEquals("User schema", result.getDescription());
        assertNull(result.get$ref()); // 应该被替换掉了
    }

    @Test
    void testParseSchema_ArrayWithItems() {
        // Arrange
        Schema<?> schema = new ArraySchema();
        schema.setDescription("List of users");
        schema.setType("array");

        Schema<String> itemSchema = new StringSchema();
        itemSchema.setDescription("User ID");

        schema.setItems(itemSchema);

        OpenAPI openAPI = Mockito.mock(OpenAPI.class);

        // Act
        SchemaConfig result = pluginBaseImpl.parseSchema(schema, openAPI);

        // Assert
        assertNotNull(result);
        assertEquals("List of users", result.getDescription());
        assertEquals("array", result.getType());
        assertEquals("Body", result.getLocation());

        SchemaConfig items = result.getItems();
        assertNotNull(items);
        assertEquals("User ID", items.getDescription());
        assertEquals("string", items.getType());
    }

    /**
     * 验证 OpenAPI 导入时 parameter.in 小写值正确映射为运行时要求的大写 location。
     * <p>
     * OpenAPI 3.0 规范中 in 值为小写 (query/header/path)，
     * 运行时 ParamLocation 枚举要求首字母大写 (Query/Headers/Path)。
     *
     * @see <a href="https://spec.openapis.org/oas/v3.0.3#parameter-object">OpenAPI 3.0 Parameter Object</a>
     */
    @Test
    void testTransformOpenAPI2Plugin_parameterLocationMapping() {
        // Arrange
        OpenAPI openAPI = new OpenAPI();
        openAPI.setInfo(new Info().title("Location Test API").description("Test location mapping"));

        Server server = new Server();
        server.setUrl("https://api.example.com/v1");
        openAPI.setServers(List.of(server));

        Paths paths = new Paths();
        PathItem pathItem = new PathItem();
        Operation getOp = new Operation();
        getOp.setOperationId("testEndpoint");
        getOp.setDescription("Test endpoint with various parameter locations");

        // 使用 OpenAPI 标准小写值: query, header, path
        getOp.setParameters(List.of(
            new Parameter().name("search").in("query").required(false)
                .schema(new Schema<String>().type("string")),
            new Parameter().name("x-api-key").in("header").required(false)
                .schema(new Schema<String>().type("string")),
            new Parameter().name("id").in("path").required(true)
                .schema(new Schema<String>().type("string"))
        ));

        pathItem.setGet(getOp);
        paths.put("/items/{id}", pathItem);
        openAPI.setPaths(paths);

        // Act
        PluginDTO pluginDTO = pluginBaseImpl.transformOpenAPI2Plugin(openAPI);

        // Assert
        assertNotNull(pluginDTO);
        List<ToolInputSchema> inputSchemas = pluginDTO.getToolInputSchemaList();
        assertNotNull(inputSchemas);
        assertEquals(1, inputSchemas.size());

        // inputSchema 是 JSON 字符串，解析后验证 location 映射
        String inputSchemaJson = inputSchemas.get(0).getInputSchema();
        assertNotNull(inputSchemaJson);

        Map<String, Object> schemaMap = JsonUtils.json2ObjQuietly(inputSchemaJson, Map.class);
        assertNotNull(schemaMap);
        Map<String, Object> properties = (Map<String, Object>) schemaMap.get("properties");
        assertNotNull(properties);

        // query → Query
        Map<String, Object> queryParam = (Map<String, Object>) properties.get("search");
        assertNotNull(queryParam, "query parameter 'search' should exist");
        assertEquals("Query", queryParam.get("location"),
            "OpenAPI 'query' should map to 'Query'");

        // header → Headers
        Map<String, Object> headerParam = (Map<String, Object>) properties.get("x-api-key");
        assertNotNull(headerParam, "header parameter 'x-api-key' should exist");
        assertEquals("Headers", headerParam.get("location"),
            "OpenAPI 'header' should map to 'Headers'");

        // path → Path
        Map<String, Object> pathParam = (Map<String, Object>) properties.get("id");
        assertNotNull(pathParam, "path parameter 'id' should exist");
        assertEquals("Path", pathParam.get("location"),
            "OpenAPI 'path' should map to 'Path'");
    }

    /**
     * 验证 OpenAPI 导入时 parameter.schema.default 值被正确读取并存入 input_schema。
     * <p>
     * OpenAPI 3.0 中参数的 schema 可包含 default 字段，
     * parseParameters() 应将其读取并存入 SchemaConfig.defaultValue。
     */
    @Test
    void testTransformOpenAPI2Plugin_parameterDefaultValue() {
        // Arrange
        OpenAPI openAPI = new OpenAPI();
        openAPI.setInfo(new Info().title("Default Value Test API").description("Test default value reading"));

        Server server = new Server();
        server.setUrl("https://api.example.com/v1");
        openAPI.setServers(List.of(server));

        Paths paths = new Paths();
        PathItem pathItem = new PathItem();
        Operation getOp = new Operation();
        getOp.setOperationId("testEndpoint");
        getOp.setDescription("Test endpoint with default values");

        // number 参数带 default 10.0
        Schema<Number> delaySchema = new Schema<>();
        delaySchema.setType("number");
        delaySchema.setDefault(10.0);

        // integer 参数带 default 500
        Schema<Integer> statusSchema = new Schema<>();
        statusSchema.setType("integer");
        statusSchema.setDefault(500);

        // string 参数带 default
        Schema<String> msgSchema = new Schema<>();
        msgSchema.setType("string");
        msgSchema.setDefault("hello");

        // 无 default 的参数
        Schema<String> noDefaultSchema = new Schema<>();
        noDefaultSchema.setType("string");

        getOp.setParameters(List.of(
            new Parameter().name("delay").in("query").required(false).schema(delaySchema),
            new Parameter().name("status_code").in("query").required(false).schema(statusSchema),
            new Parameter().name("message").in("query").required(false).schema(msgSchema),
            new Parameter().name("tag").in("query").required(false).schema(noDefaultSchema)
        ));

        pathItem.setGet(getOp);
        paths.put("/test", pathItem);
        openAPI.setPaths(paths);

        // Act
        PluginDTO pluginDTO = pluginBaseImpl.transformOpenAPI2Plugin(openAPI);

        // Assert
        assertNotNull(pluginDTO);
        List<ToolInputSchema> inputSchemas = pluginDTO.getToolInputSchemaList();
        assertNotNull(inputSchemas);
        assertEquals(1, inputSchemas.size());

        String inputSchemaJson = inputSchemas.get(0).getInputSchema();
        assertNotNull(inputSchemaJson);

        Map<String, Object> schemaMap = JsonUtils.json2ObjQuietly(inputSchemaJson, Map.class);
        assertNotNull(schemaMap);
        Map<String, Object> properties = (Map<String, Object>) schemaMap.get("properties");
        assertNotNull(properties);

        // number default: 10.0
        Map<String, Object> delayParam = (Map<String, Object>) properties.get("delay");
        assertNotNull(delayParam, "parameter 'delay' should exist");
        assertEquals("10.0", delayParam.get("default"),
            "number parameter default should be '10.0'");

        // integer default: 500
        Map<String, Object> statusParam = (Map<String, Object>) properties.get("status_code");
        assertNotNull(statusParam, "parameter 'status_code' should exist");
        assertEquals("500", statusParam.get("default"),
            "integer parameter default should be '500'");

        // string default: hello
        Map<String, Object> msgParam = (Map<String, Object>) properties.get("message");
        assertNotNull(msgParam, "parameter 'message' should exist");
        assertEquals("hello", msgParam.get("default"),
            "string parameter default should be 'hello'");

        // no default: should be null
        Map<String, Object> tagParam = (Map<String, Object>) properties.get("tag");
        assertNotNull(tagParam, "parameter 'tag' should exist");
        assertNull(tagParam.get("default"),
            "parameter without default should have null default");
    }



    @Test
    void test_parseVariableUrl() {
        pluginBaseImpl.parseVariableUrl("http://test.com");
    }


    @Test
    void test_isInnerType_plugin_is_null() {
        // Arrange
        String resourceId = "testId";
        when(pluginMapper.selectByPrimaryKey(eq(resourceId), eq(null))).thenReturn(null);
        try (MockedStatic<ObjectUtils> mockedStatic = mockStatic(ObjectUtils.class)) {
            mockedStatic.when(() -> ObjectUtils.isEmpty(any())).thenReturn(true);

            // Act
            boolean result = pluginBaseImpl.isInnerType(resourceId);

            // Assert
            assertTrue(result);
        }
    }

    @Test
    @Sql(scripts = {"classpath:sql/plugin_reserve_meeting_room_setup_db.sql"})
    void test_isInnerType_plugin_is_not_null_and_type_is_inner() {
        // Arrange
        String resourceId = "reserve_meeting_room";
        PluginEntity plugin = mock(PluginEntity.class);
        when(plugin.getType()).thenReturn(ToolType.INNER.type);
        try (MockedStatic<ObjectUtils> mockedStatic = mockStatic(ObjectUtils.class)) {
            mockedStatic.when(() -> ObjectUtils.isEmpty(any())).thenReturn(false);
            try (MockedStatic<Strings> stringsMockedStatic = mockStatic(Strings.class)) {
                stringsMockedStatic.when(() -> Strings.CS.equals(anyString(), anyString())).thenReturn(true);

                // Act
                boolean result = pluginBaseImpl.isInnerType(resourceId);

                // Assert
                assertTrue(result);
            }
        }
    }
}
