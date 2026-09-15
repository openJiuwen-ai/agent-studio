# 对话工作台 Skill 目录注入、按需激活与 `/` 推荐实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在不修改官方 Skill、Agent、IR 与通用 Runtime 实现的前提下，让对话工作台顶层执行 Agent 始终获知当前工作空间全部可用 Skill，并支持用户通过 `/` 多选、按本轮推荐、按需下载和激活 Skill。

**架构：** Manager 在用户与工作空间权限边界内解析可信 Skill 目录，校验浏览器提交的推荐 ID，并把内部制品路径仅发送给 Runtime。Runtime 把目录描述和推荐区挂到本轮顶层 Agent，注册统一的 `activate_skill` 工具，并用进程级版本缓存安全下载、校验和读取 `SKILL.md`；前端只管理目录展示和推荐 ID，不解析或接触制品路径。

**技术栈：** Angular 20 / TypeScript 5.8 / ng-zorro，Java 17 / Spring MVC / MyBatis / JUnit 5 / Mockito，Python 3.11 / FastAPI / Pydantic 2 / pytest / openJiuwen ReActAgent，共享 `storage` 对象存储包。

## 全局约束

- 只修改 `frontend/src/routes/conversation-workspace/**`、`backend/studio-manager-service/src/**/com/openjiuwen/studio/conversation/**`、`agent-runtime/agent_runtime/supervisor/**`、`agent-runtime/agent_runtime/serve/apis/conversation_team.py` 及对应测试。
- 只调用现有 `SkillMapper`、共享对象存储和 openJiuwen 公共 API；不修改官方 Skill 管理、`react_agent_runner.py`、Agent 发布或 IR 生成逻辑。
- 不修改数据库结构，不持久化推荐 ID、激活轨迹或临时 Skill—Agent 关联。
- Skill 目录只包含当前 `project_id + workspace_id + domain_id` 下 `status=developed`、最新版本与制品路径非空的记录。
- 浏览器只提交 `recommended_skill_ids`；对象存储路径只允许出现在 Manager → Runtime 内部请求。
- 所有合法 Skill 均可发现、推荐和激活；不根据 Skill 能力类型提前过滤。实际执行能力由本轮 Agent 已注册工具和运行环境决定。
- 不设置单轮 Skill 人为数量上限；推荐 ID 去重并保留选择顺序。
- `/` 推荐只影响本轮优先级，不强制使用；手写 `/skill-name` 不产生推荐语义。
- Skill 只挂到本轮顶层执行者，不修改同事的 `+` 智能体选择状态，也不传播到多智能体子 Agent。
- 全部 Skill 描述每轮注入；ZIP 制品只在 Agent 调用 `activate_skill(skill_id)` 时下载和激活。
- 当前首轮联调使用三个纯文本 Skill，但运行时不得把“纯文本”做成类型白名单。
- 开发文档、代码注释中的业务说明和全部 Git 提交说明使用中文。
- 开始实现前使用 `superpowers:using-git-worktrees` 检查隔离条件；每次触碰热点文件前重新执行 `git fetch origin` 并检查 `origin/studio-2.0-dev-0804`。

---

## 文件结构与职责

### Manager

- 新建 `application/dto/ConversationSkillVo.java`：浏览器可见的最小目录项，仅含 ID、名称和描述。
- 新建 `application/dto/ConversationSkillDescriptor.java`：Manager → Runtime 内部目录项，额外含版本 ID 和对象键。
- 新建 `application/dto/ConversationSkillContext.java`：本轮可信目录与有序推荐 ID 的不可变容器。
- 新建 `application/ConversationSkillResolver.java`：复用现有 `SkillMapper` 分页查询、过滤、去重和鉴权。
- 修改 `ConversationWorkspaceController.java`：增加工作台专用 Skill 目录端点。
- 修改 `SendMessageCmd.java`：增加 `recommended_skill_ids`。
- 修改 `ConversationWorkspaceAppService.java`：在落用户消息前完成推荐校验。
- 修改 `AgentRuntimeAdapter.java`：将 `skillCatalog` 与 `recommendedSkillIds` 追加到内部请求。

### Runtime

- 新建 `supervisor/skill_model.py`：声明可信 Skill 描述值对象。
- 新建 `supervisor/skill_artifact_cache.py`：版本缓存、对象存储下载、ZIP 安全校验和 `SKILL.md` 读取。
- 新建 `supervisor/tool/activate_skill_tool.py`：从请求级上下文读取可信目录的无状态激活工具。
- 新建 `supervisor/skill_context.py`：生成目录/推荐提示段，用 `ContextVar` 隔离请求上下文，并把无状态激活工具挂到顶层 Agent。
- 修改 `supervisor/common/constants.py` 与 `supervisor/event/adapt.py`：增加非持久化 `skill_activated` SSE 事件。
- 修改 `supervisor/builder.py`：在监督者构建完成后挂载 Skill 上下文。
- 修改 `supervisor/runner.py`：在一轮运行期间绑定并最终清理请求级 Skill 上下文。
- 修改 `serve/apis/conversation_team.py`：接收内部 Skill 契约并传给顶层构建器。

### 前端

- 新建 `conversation-skill.model.ts`：目录项、选择项和发送请求类型。
- 新建 `skill-selector/skill-selector.component.{ts,html,less}`：输入框、`/` 菜单、多选标签与键盘操作。
- 修改 `conversation-workspace.service.ts`：获取最小 Skill 目录并声明发送请求类型。
- 修改 `conversation-workspace.component.{ts,html,less}`：加载目录、发送推荐 ID、清理状态和展示激活事件。

---

### 任务 1：Manager 工作空间 Skill 目录与最小查询接口

**文件：**

- 新建：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/dto/ConversationSkillVo.java`
- 新建：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/dto/ConversationSkillDescriptor.java`
- 新建：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/dto/ConversationSkillContext.java`
- 新建：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/ConversationSkillResolver.java`
- 修改：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/interfaces/controller/ConversationWorkspaceController.java`
- 修改：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/ConversationWorkspaceAppService.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/application/ConversationSkillResolverTest.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/application/ConversationWorkspaceAppServiceTest.java`

**接口：**

- 消费：现有 `SkillMapper.search(SkillEntity, int, int, String, String, int)`。
- 产出：`List<ConversationSkillVo> listAvailable(String projectId, String workspaceId, String domainId)`。
- 产出：`ConversationSkillContext resolveForRun(String projectId, String workspaceId, String domainId, List<String> requestedIds)`。
- HTTP：`GET /v1/{project_id}/conversation/sessions/skills?workspace_id={workspace_id}`，响应只含 `skill_id`、`name`、`description`。

- [ ] **步骤 1：先写 Resolver 失败测试**

```java
@Test
void listAvailable_只返回当前边界内可执行目录项() {
    when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0)))
        .thenReturn(List.of(
            skill("s1", "d1", "p1", "w1", "developed", "v1", "u1/skills/s1/v1/a.zip"),
            skill("s2", "d1", "p1", "w1", "developing", "v2", "u1/skills/s2/v2/b.zip"),
            skill("s3", "d1", "p1", "w1", "developed", "v3", "")));

    List<ConversationSkillVo> result = resolver.listAvailable("p1", "w1", "d1");

    assertEquals(List.of("s1"), result.stream().map(ConversationSkillVo::getSkillId).toList());
}

@Test
void listAvailable_达到页大小时继续读取下一页() {
    List<SkillDetails> firstPage = IntStream.range(0, 1000)
        .mapToObj(i -> skill("s" + i, "d1", "p1", "w1", "developed", "v" + i,
            "u1/skills/s" + i + "/v" + i + "/a.zip"))
        .toList();
    when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0))).thenReturn(firstPage);
    when(skillMapper.search(any(), eq(1000), eq(1000), isNull(), isNull(), eq(0))).thenReturn(List.of());

    assertEquals(1000, resolver.listAvailable("p1", "w1", "d1").size());
    verify(skillMapper).search(any(), eq(1000), eq(1000), isNull(), isNull(), eq(0));
}

private SkillDetails skill(String id, String domainId, String projectId, String workspaceId,
        String status, String versionId, String objectKey) {
    return new SkillDetails().setSkillId(id).setDomainId(domainId).setProjectId(projectId)
        .setWorkspaceId(workspaceId).setStatus(status).setLatestVersion(versionId)
        .setName("skill-" + id).setDescription("description-" + id).setObsPath(objectKey);
}
```

- [ ] **步骤 2：运行测试并确认因 Resolver 和 DTO 不存在而失败**

```powershell
cd E:\Desktop\test\agent-studio\backend
mvn -pl studio-manager-service -am "-Dtest=ConversationSkillResolverTest" "-Dsurefire.failIfNoSpecifiedTests=false" test
```

预期：测试编译失败，提示 `ConversationSkillResolver` 或 DTO 类型不存在。

- [ ] **步骤 3：实现最小 DTO、分页查询和过滤**

`ConversationSkillDescriptor` 固定字段如下：

```java
@Value
@Builder
public class ConversationSkillDescriptor {
    String skillId;
    String versionId;
    String name;
    String description;
    String objectKey;
}
```

浏览器 DTO 明确使用下划线字段且不声明版本或对象键：

```java
@Value
@Builder
public class ConversationSkillVo {
    @JsonProperty("skill_id")
    String skillId;
    String name;
    String description;
}
```

本轮上下文对列表做防御性复制：

```java
@Getter
public final class ConversationSkillContext {
    private final List<ConversationSkillDescriptor> catalog;
    private final List<String> recommendedSkillIds;

    public ConversationSkillContext(List<ConversationSkillDescriptor> catalog, List<String> recommendedSkillIds) {
        this.catalog = List.copyOf(catalog);
        this.recommendedSkillIds = List.copyOf(recommendedSkillIds);
    }

    public static ConversationSkillContext empty() {
        return new ConversationSkillContext(List.of(), List.of());
    }
}
```

`ConversationSkillResolver` 使用 1000 条一页，查询条件必须由服务端生成：

```java
private static final int PAGE_SIZE = 1000;

private List<ConversationSkillDescriptor> loadCatalog(String projectId, String workspaceId, String domainId) {
    SkillEntity condition = new SkillEntity()
        .setProjectId(projectId)
        .setWorkspaceId(workspaceId)
        .setDomainId(domainId)
        .setStatus(SkillStatus.DEVELOPED.getValue());
    List<ConversationSkillDescriptor> result = new ArrayList<>();
    for (int offset = 0; ; offset += PAGE_SIZE) {
        List<SkillDetails> page = skillMapper.search(condition, offset, PAGE_SIZE, null, null, 0);
        page.stream()
            .filter(item -> Objects.equals(domainId, item.getDomainId()))
            .filter(item -> Objects.equals(projectId, item.getProjectId()))
            .filter(item -> Objects.equals(workspaceId, item.getWorkspaceId()))
            .filter(item -> Objects.equals(SkillStatus.DEVELOPED.getValue(), item.getStatus()))
            .filter(item -> StringUtils.isNotBlank(item.getSkillId()))
            .filter(item -> StringUtils.isNotBlank(item.getLatestVersion()))
            .filter(item -> StringUtils.isNotBlank(item.getObsPath()))
            .map(this::toDescriptor)
            .forEach(result::add);
        if (page.size() < PAGE_SIZE) {
            return result;
        }
    }
}
```

不要修改 `SkillMapper.java` 或 XML；`toDescriptor()` 中 `versionId` 必须取 `latestVersion`，`objectKey` 必须取 `obsPath`。

- [ ] **步骤 4：给 AppService 和 Controller 增加最小目录端点测试与实现**

测试断言浏览器响应不含内部字段：

```java
@Test
void listSkills_只返回浏览器可见字段() {
    when(skillResolver.listAvailable("p1", "w1", "d1"))
        .thenReturn(List.of(ConversationSkillVo.builder()
            .skillId("s1").name("会议纪要").description("整理会议内容").build()));

    List<ConversationSkillVo> result = appService.listSkills("p1", "w1");

    assertEquals("s1", result.get(0).getSkillId());
}
```

Controller 方法签名固定为：

```java
@GetMapping("/skills")
public List<ConversationSkillVo> listSkills(
        @PathVariable("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId) {
    return conversationWorkspaceAppService.listSkills(projectId, workspaceId);
}
```

`ConversationWorkspaceAppService` 构造器增加 `ConversationSkillResolver` 依赖，测试 `setUp()` 同步创建 mock 并传入；`listSkills()` 使用 `RequestContextUtils.getRequestUserDomainId()`，不能接受浏览器提交的 domain ID。

- [ ] **步骤 5：运行 Manager 定向测试**

```powershell
cd E:\Desktop\test\agent-studio\backend
mvn -pl studio-manager-service -am "-Dtest=ConversationSkillResolverTest,ConversationWorkspaceAppServiceTest" "-Dsurefire.failIfNoSpecifiedTests=false" test
```

预期：全部通过；现有会话 CRUD 测试无回归。

- [ ] **步骤 6：提交任务 1**

```powershell
git add backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation
git commit -m "功能(对话工作台): 增加工作空间技能目录查询"
```

---

### 任务 2：Manager 本轮推荐校验、落库顺序与 Runtime 契约

**文件：**

- 修改：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/dto/SendMessageCmd.java`
- 修改：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/ConversationSkillResolver.java`
- 修改：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/application/ConversationWorkspaceAppService.java`
- 修改：`backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/infrastructure/adapter/AgentRuntimeAdapter.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/application/dto/SendMessageCmdTest.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/application/ConversationSkillResolverTest.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/application/ConversationWorkspaceAppServiceTest.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/infrastructure/adapter/AgentRuntimeAdapterTest.java`
- 测试：`backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/infrastructure/adapter/ConversationRunEventSourceListenerTest.java`

**接口：**

- 浏览器字段：`recommended_skill_ids: string[]`。
- Manager 内部：`ConversationSkillContext(catalog, recommendedSkillIds)`。
- Runtime JSON：`skillCatalog[{skillId,versionId,name,description,objectKey}]` 和 `recommendedSkillIds[]`。

- [ ] **步骤 1：先扩展 DTO 序列化失败测试**

```java
@Test
void serialization_推荐技能使用下划线字段且保留顺序() throws Exception {
    SendMessageCmd cmd = new SendMessageCmd();
    cmd.setQuery("整理并润色");
    cmd.setModelDeploymentId("m1");
    cmd.setRecommendedSkillIds(List.of("s2", "s1"));

    JsonNode json = new ObjectMapper().readTree(new ObjectMapper().writeValueAsString(cmd));

    assertEquals(List.of("s2", "s1"),
        StreamSupport.stream(json.get("recommended_skill_ids").spliterator(), false)
            .map(JsonNode::asText).toList());
    assertFalse(json.has("recommendedSkillIds"));
}
```

- [ ] **步骤 2：增加 Resolver 顺序、去重、越权和降级测试**

```java
@Test
void resolveForRun_去重并保留推荐顺序() {
    mockCatalog("s1", "s2");
    ConversationSkillContext context = resolver.resolveForRun(
        "p1", "w1", "d1", List.of("s2", "s1", "s2"));
    assertEquals(List.of("s2", "s1"), context.getRecommendedSkillIds());
}

@Test
void resolveForRun_目录外推荐被拒绝() {
    mockCatalog("s1");
    assertThrows(AgentStudioException.class,
        () -> resolver.resolveForRun("p1", "w1", "d1", List.of("other")));
}

@Test
void resolveForRun_无推荐时目录异常降级为空目录() {
    when(skillMapper.search(any(), anyInt(), anyInt(), any(), any(), anyInt()))
        .thenThrow(new RuntimeException("db unavailable"));
    ConversationSkillContext context = resolver.resolveForRun("p1", "w1", "d1", List.of());
    assertTrue(context.getCatalog().isEmpty());
}

@Test
void resolveForRun_有推荐时目录异常不得静默执行() {
    when(skillMapper.search(any(), anyInt(), anyInt(), any(), any(), anyInt()))
        .thenThrow(new RuntimeException("db unavailable"));
    assertThrows(AgentStudioException.class,
        () -> resolver.resolveForRun("p1", "w1", "d1", List.of("s1")));
}

private void mockCatalog(String... ids) {
    List<SkillDetails> items = Arrays.stream(ids)
        .map(id -> skill(id, "d1", "p1", "w1", "developed", "v-" + id,
            "u1/skills/" + id + "/v-" + id + "/a.zip"))
        .toList();
    when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0))).thenReturn(items);
}
```

- [ ] **步骤 3：运行测试确认新行为尚未实现**

```powershell
cd E:\Desktop\test\agent-studio\backend
mvn -pl studio-manager-service -am "-Dtest=SendMessageCmdTest,ConversationSkillResolverTest" "-Dsurefire.failIfNoSpecifiedTests=false" test
```

预期：新增用例失败。

- [ ] **步骤 4：实现推荐字段和可信上下文解析**

`SendMessageCmd` 新字段：

```java
@JsonProperty("recommended_skill_ids")
private List<String> recommendedSkillIds = new ArrayList<>();
```

Resolver 使用 `LinkedHashSet<String>` 去重；只要任一 ID 不在当轮目录，以 `METHOD_ARGUMENT_NOT_VALID` 拒绝整个请求。目录查询异常且推荐为空时记录 `warn` 并返回空上下文；推荐非空时转换为可识别的 `AgentStudioException`。

- [ ] **步骤 5：先写“校验必须早于落库”的 AppService 失败测试**

```java
@Test
void sendMessage_推荐技能非法时不写用户消息() {
    Conversation conv = ownedConversation("c1");
    when(repository.findById("c1")).thenReturn(Optional.of(conv));
    SendMessageCmd cmd = validCmd(List.of("forbidden"));
    when(skillResolver.resolveForRun("p1", "w1", "d1", List.of("forbidden")))
        .thenThrow(new AgentStudioException(
            StudioError.METHOD_ARGUMENT_NOT_VALID, List.of("recommended skill is unavailable")));

    assertThrows(AgentStudioException.class,
        () -> appService.sendMessage("p1", "w1", "c1", cmd, new HttpHeaders()));
    verify(repository, never()).appendMessages(anyString(), anyList());
    verifyNoInteractions(runtimeAdapter);
}

private SendMessageCmd validCmd(List<String> recommendedIds) {
    SendMessageCmd cmd = new SendMessageCmd();
    cmd.setQuery("整理会议");
    cmd.setModelDeploymentId("m1");
    cmd.setRecommendedSkillIds(recommendedIds);
    return cmd;
}
```

`ownedConversation()` 必须补齐 `domainId="d1"`；`sendMessage()` 顺序固定为：基础参数校验 → 会话归属校验 → Skill 上下文解析 → 生成 execution ID → 写 user 消息 → 组装历史 → 调 Runtime。

- [ ] **步骤 6：给 Adapter 写内部请求体失败测试并实现最小接线**

```java
@Test
void buildRequestBody_包含可信技能目录和有序推荐() {
    ConversationSkillDescriptor skill = ConversationSkillDescriptor.builder()
        .skillId("s1").versionId("v1").name("meeting-minutes")
        .description("整理会议内容").objectKey("u1/skills/s1/v1/a.zip").build();
    ConversationSkillContext skillContext = new ConversationSkillContext(List.of(skill), List.of("s1"));

    Map<String, Object> body = adapter.buildRequestBody(conv(), cmd(), List.of(), skillContext);

    assertEquals(List.of("s1"), body.get("recommendedSkillIds"));
    Map<String, Object> item = ((List<Map<String, Object>>) body.get("skillCatalog")).get(0);
    assertEquals("u1/skills/s1/v1/a.zip", item.get("objectKey"));
}

private Conversation conv() {
    return Conversation.builder().conversationId("c1").projectId("p1").workspaceId("w1").build();
}

private SendMessageCmd cmd() {
    SendMessageCmd cmd = new SendMessageCmd();
    cmd.setQuery("整理会议");
    cmd.setModelDeploymentId("m1");
    return cmd;
}
```

将 Adapter 方法签名改成：

```java
public SseEmitter run(Conversation conversation, SendMessageCmd cmd, List<Message> histories,
        ConversationSkillContext skillContext, String executionId, HttpHeaders requestHeaders)
```

新增私有 `appendSkillContext(Map<String,Object>, ConversationSkillContext)`，避免在同事将来修改 `subAgentIds` 时扩大冲突面。

- [ ] **步骤 7：运行全部 Manager 对话工作台测试**

先补充激活事件不落库的回归：

```java
@Test
void testSkillActivatedEvent_ForwardOnlyAndNeverPersisted() {
    feedEvent("{\"event\":\"skill_activated\",\"data\":{\"skillId\":\"s1\","
        + "\"name\":\"会议纪要\",\"versionId\":\"v1\"},\"executionId\":\"exec-1\"}");
    listener.onClosed(mock(EventSource.class));
    verify(conversationRepository, never()).appendMessages(anyString(), anyList());
}
```

随后运行全部 Manager 对话工作台测试：

```powershell
cd E:\Desktop\test\agent-studio\backend
mvn -pl studio-manager-service -am "-Dtest=**/conversation/**/*Test" "-Dsurefire.failIfNoSpecifiedTests=false" test
```

预期：对话工作台测试全部通过。

- [ ] **步骤 8：提交任务 2**

```powershell
git add backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation
git commit -m "功能(对话工作台): 校验并透传本轮推荐技能"
```

---

### 任务 3：Runtime Skill 值对象与安全版本缓存

**文件：**

- 新建：`agent-runtime/agent_runtime/supervisor/skill_model.py`
- 新建：`agent-runtime/agent_runtime/supervisor/skill_artifact_cache.py`
- 测试：`agent-runtime/tests/unit_tests/supervisor/test_skill_artifact_cache.py`

**接口：**

- 产出：`SkillDescriptor(skill_id, version_id, name, description, object_key)`。
- 产出：`await SkillArtifactCache.load_instructions(skill: SkillDescriptor) -> str`。
- 产出：`default_cache() -> SkillArtifactCache`，返回进程级缓存单例。
- 消费：`storage.get_storage_provider().get_object_bytes(object_key)`。

- [ ] **步骤 1：先写缓存命中、版本隔离和 ZIP 安全失败测试**

```python
@pytest.mark.asyncio
async def test_same_skill_version_downloads_once(tmp_path):
    downloader = AsyncMock(return_value=skill_zip("meeting-minutes", "正文标记"))
    cache = SkillArtifactCache(tmp_path, downloader=downloader)
    skill = descriptor("s1", "v1", "meeting-minutes", "u1/skills/s1/v1/a.zip")

    first = await cache.load_instructions(skill)
    second = await cache.load_instructions(skill)

    assert first == second
    downloader.assert_awaited_once_with(skill.object_key)

@pytest.mark.asyncio
async def test_new_version_uses_new_cache_entry(tmp_path):
    downloader = AsyncMock(side_effect=[skill_zip("x", "v1"), skill_zip("x", "v2")])
    cache = SkillArtifactCache(tmp_path, downloader=downloader)
    assert await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")) != \
           await cache.load_instructions(descriptor("s1", "v2", "x", "u/skills/s1/v2/a.zip"))

@pytest.mark.asyncio
@pytest.mark.parametrize("member", ["../escape", "/absolute", "C:/escape"])
async def test_path_traversal_is_rejected(tmp_path, member):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=zip_with(member, b"x")))
    with pytest.raises(SkillArtifactError, match="unsafe zip path"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))

def descriptor(skill_id, version_id, name, object_key):
    return SkillDescriptor(
        skill_id=skill_id,
        version_id=version_id,
        name=name,
        description=f"description-{name}",
        object_key=object_key,
    )

def zip_with(member, data):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, data)
    return output.getvalue()

def skill_zip(name, body):
    markdown = f"---\nname: {name}\ndescription: test skill\n---\n\n{body}"
    return zip_with(f"{name}/SKILL.md", markdown.encode("utf-8"))
```

再覆盖：嵌套 ZIP、符号链接、超过 500 条目、压缩包超过 10 MiB、解压总量超过 100 MiB、超过 10 层、没有或存在多个 `SKILL.md`。

- [ ] **步骤 2：运行测试确认类型不存在**

```powershell
cd E:\Desktop\test\agent-studio
$env:PYTHONPATH="$PWD\agent-runtime;$PWD\packages\storage;$PWD\packages\model_service;$PWD\packages\common_utils"
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/supervisor/test_skill_artifact_cache.py -q
```

预期：导入失败。

- [ ] **步骤 3：实现不可变值对象和缓存键**

```python
@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    skill_id: str
    version_id: str
    name: str
    description: str
    object_key: str

    @property
    def cache_key(self) -> str:
        return hashlib.sha256(f"{self.skill_id}\0{self.version_id}".encode()).hexdigest()
```

缓存根目录固定为 `settings.skill_storage.skill_storage_dir/conversation-skills`；磁盘目录只使用 `cache_key`，不能拼接 Skill 名称或浏览器输入。

- [ ] **步骤 4：实现安全下载、校验、原子发布与异步锁**

固定限制与 Java 导入校验一致：压缩包 10 MiB、解压后 100 MiB、500 个条目、10 层、禁止嵌套 ZIP和符号链接。每个 `cache_key` 使用一把 `asyncio.Lock`；在锁内二次检查缓存。下载到随机临时目录，校验后逐条解压，确认恰好一个 `SKILL.md`，最后用原子目录替换发布；异常时清理临时文件。

默认下载器必须复用共享存储：

```python
async def _download(object_key: str) -> bytes:
    provider = get_storage_provider()
    return await provider.get_object_bytes(object_key)
```

进程级单例只保存缓存锁和缓存根目录，不保存用户目录：

```python
_default_cache: SkillArtifactCache | None = None

def default_cache() -> SkillArtifactCache:
    global _default_cache
    if _default_cache is None:
        root = Path(settings.skill_storage.skill_storage_dir) / "conversation-skills"
        _default_cache = SkillArtifactCache(root, downloader=_download)
    return _default_cache
```

对象键在 Runtime 再校验一次：必须是相对 POSIX 路径、不得含 `.`/`..` 段，并且连续包含 `skills/{skill_id}/{version_id}` 三个路径段。

- [ ] **步骤 5：运行缓存测试并确认通过**

```powershell
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/supervisor/test_skill_artifact_cache.py -q
```

- [ ] **步骤 6：提交任务 3**

```powershell
git add agent-runtime/agent_runtime/supervisor/skill_model.py agent-runtime/agent_runtime/supervisor/skill_artifact_cache.py agent-runtime/tests/unit_tests/supervisor/test_skill_artifact_cache.py
git commit -m "功能(对话工作台): 增加技能制品安全缓存"
```

---

### 任务 4：统一激活工具、提示段与激活事件

**文件：**

- 新建：`agent-runtime/agent_runtime/supervisor/tool/activate_skill_tool.py`
- 新建：`agent-runtime/agent_runtime/supervisor/skill_context.py`
- 修改：`agent-runtime/agent_runtime/supervisor/common/constants.py`
- 修改：`agent-runtime/agent_runtime/supervisor/event/adapt.py`
- 测试：`agent-runtime/tests/unit_tests/supervisor/test_skill_context.py`
- 测试：`agent-runtime/tests/unit_tests/supervisor/test_activate_skill_tool.py`

**接口：**

- 产出：`build_skill_prompt(catalog, recommended_skill_ids) -> str`。
- 产出：`await attach(top_level_agent, catalog, recommended_skill_ids, artifact_cache=None) -> None`。
- 内部：`attach_agent_context(agent, catalog, recommended_skill_ids, artifact_cache) -> None`，只保存本轮 Agent 的上下文数据，不注册全局状态。
- 产出：`bind_agent_skill_context(agent) -> Token` 与 `reset_skill_context(token) -> None`，由 `run_supervisor()` 用 `try/finally` 管理。
- 工具：`activate_skill`，输入 `{"skill_id":"skill-id"}`，输出 `skillId/name/versionId/instructions`。
- SSE：`skill_activated`，数据为 `skillId/name/versionId`，仅透传、不落库。

请求级上下文类型固定为：

```python
@dataclass(frozen=True, slots=True)
class SkillExecutionContext:
    catalog_by_id: Mapping[str, SkillDescriptor]
    recommended_skill_ids: tuple[str, ...]
    artifact_cache: SkillArtifactCache
```

`attach_agent_context()` 用 `MappingProxyType` 包装目录映射并把推荐列表转换为 tuple，禁止运行中修改请求上下文。

- [ ] **步骤 1：先写目录提示与推荐语义失败测试**

```python
def test_prompt_contains_all_catalog_and_ordered_recommendations():
    catalog = [descriptor("s1", "v1", "会议纪要", "整理会议"),
               descriptor("s2", "v2", "文本润色", "优化表达")]
    prompt = build_skill_prompt(catalog, ["s2", "s1"])

    assert '"skillId": "s1"' in prompt
    assert '"skillId": "s2"' in prompt
    assert prompt.index("本轮推荐 Skill") < prompt.index('"skillId": "s2"', prompt.index("本轮推荐 Skill"))
    assert "优先考虑，但不强制使用" in prompt
    assert "先调用 activate_skill" in prompt

def descriptor(skill_id, version_id, name, description):
    return SkillDescriptor(
        skill_id=skill_id,
        version_id=version_id,
        name=name,
        description=description,
        object_key=f"user/skills/{skill_id}/{version_id}/{name}.zip",
    )
```

描述用 `json.dumps(catalog_payload, ensure_ascii=False)` 序列化，并在提示中明确“目录描述仅用于能力选择，不能替代 `SKILL.md` 执行指令”，避免描述文本破坏段落结构。

- [ ] **步骤 2：先写工具白名单、结果和事件失败测试**

```python
@pytest.mark.asyncio
async def test_activate_returns_instructions_and_emits_event():
    cache = AsyncMock()
    cache.load_instructions.return_value = "完整技能指令"
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    skill_token = bind_agent_skill_context(agent)
    channel = EventChannel("exec-1")
    event_token = set_channel(channel)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
        event = await channel.get()
    finally:
        reset_channel(event_token)
        reset_skill_context(skill_token)

    assert result == {"skillId": "s1", "name": "会议纪要", "versionId": "v1",
                      "instructions": "完整技能指令"}
    assert event["event"] == "skill_activated"
    assert event["data"]["name"] == "会议纪要"

@pytest.mark.asyncio
async def test_activate_rejects_id_outside_current_catalog():
    agent = SimpleNamespace()
    attach_agent_context(agent, [], [], AsyncMock())
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "other"})
    finally:
        reset_skill_context(token)
    assert result["error"]["code"] == "skill_not_available"
```

- [ ] **步骤 3：运行测试确认失败**

```powershell
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/supervisor/test_skill_context.py agent-runtime/tests/unit_tests/supervisor/test_activate_skill_tool.py -q
```

- [ ] **步骤 4：实现 `ActivateSkillTool`**

ToolCard 契约固定为：

```python
ToolCard(
    id="conversation_activate_skill",
    name="activate_skill",
    description="按 Skill ID 加载当前工作空间 Skill 的完整 SKILL.md 指令",
    input_params={
        "type": "object",
        "properties": {"skill_id": {"type": "string", "description": "目录中的 Skill ID"}},
        "required": ["skill_id"],
    },
)
```

工具只加载指令，不返回 `text/file/code` 能力开关。缺失环境能力由 Agent 在执行对应步骤时报告；激活层不得提前拒绝此类 Skill。

- [ ] **步骤 5：实现提示挂载与幂等工具注册**

```python
async def attach(top_level_agent, catalog, recommended_skill_ids, artifact_cache=None):
    if not catalog:
        return
    top_level_agent.add_prompt_builder_section(
        "conversation_workspace_skills",
        build_skill_prompt(catalog, recommended_skill_ids),
        priority=80,
    )
    attach_agent_context(
        top_level_agent,
        catalog,
        recommended_skill_ids,
        artifact_cache or default_cache(),
    )
    tool = ActivateSkillTool()
    result = top_level_agent.ability_manager.add(tool.card)
    if result.added and Runner.resource_mgr.get_tool(tool.card.id) is None:
        Runner.resource_mgr.add_tool(tool)
```

`attach_agent_context()` 只把 `SkillExecutionContext(catalog_by_id, recommended_skill_ids, artifact_cache)` 保存在本轮 Agent 自身；`run_supervisor()` 开始时把它绑定到 `ContextVar`，结束时在 `finally` 中重置。`ActivateSkillTool` 实例不得持有目录或用户状态，只能在 `invoke()` 时读取当前 `ContextVar`。这样即使 `Runner.resource_mgr` 全局复用同一个工具，也不会在并发用户之间串目录。

激活失败返回结构化结果，不让单个 Skill 失败中止整轮：

```python
{
    "error": {
        "code": "skill_artifact_invalid",
        "message": "Skill s1 activation failed: archive rejected",
    }
}
```

只有成功读取 `SKILL.md` 后才发送 `skill_activated`。未知 ID、下载失败、非法 ZIP 和缺失 `SKILL.md` 分别使用稳定错误码，且不得在错误文本中暴露对象存储凭据或本地绝对路径。

- [ ] **步骤 6：实现 `skill_activated` 事件构造并运行测试**

在 `TeamEventType` 增加 `SKILL_ACTIVATED`，在 `TeamEventField` 增加 `SKILL_ID`、`NAME`、`VERSION_ID`，并在 `adapt.py` 增加：

```python
def build_skill_activated(execution_id, skill_id, name, version_id, index=None):
    return _build_event(TeamEventType.SKILL_ACTIVATED, execution_id, {
        TeamEventField.SKILL_ID: skill_id,
        TeamEventField.NAME: name,
        TeamEventField.VERSION_ID: version_id,
    }, index)
```

随后运行：

```powershell
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/supervisor/test_skill_context.py agent-runtime/tests/unit_tests/supervisor/test_activate_skill_tool.py -q
```

- [ ] **步骤 7：提交任务 4**

```powershell
git add agent-runtime/agent_runtime/supervisor agent-runtime/tests/unit_tests/supervisor
git commit -m "功能(对话工作台): 增加技能按需激活工具"
```

---

### 任务 5：Runtime 请求契约与顶层 Agent 接线

**文件：**

- 修改：`agent-runtime/agent_runtime/serve/apis/conversation_team.py`
- 修改：`agent-runtime/agent_runtime/supervisor/builder.py`
- 修改：`agent-runtime/agent_runtime/supervisor/runner.py`
- 测试：`agent-runtime/tests/unit_tests/serve/apis/test_conversation_team.py`
- 测试：`agent-runtime/tests/unit_tests/supervisor/test_builder.py`
- 测试：`agent-runtime/tests/unit_tests/supervisor/test_runner.py`

**接口：**

- `ConversationTeamReq.skill_catalog` 使用别名 `skillCatalog`。
- `ConversationTeamReq.recommended_skill_ids` 使用别名 `recommendedSkillIds`。
- `build_supervisor(sub_agent_ids, model_deployment_id, conversation_history=None, skill_catalog=None, recommended_skill_ids=None)` 始终返回已挂载 Skill 的顶层监督者。

- [ ] **步骤 1：先写 Pydantic 契约失败测试**

```python
def test_request_accepts_manager_skill_contract():
    req = ConversationTeamReq.model_validate({
        "conversationId": "c1",
        "query": "整理会议",
        "subAgentIds": ["a1"],
        "modelDeploymentId": "m1",
        "skillCatalog": [{
            "skillId": "s1", "versionId": "v1", "name": "会议纪要",
            "description": "整理会议", "objectKey": "u/skills/s1/v1/a.zip"
        }],
        "recommendedSkillIds": ["s1"],
    })
    assert req.skill_catalog[0].skill_id == "s1"
    assert req.recommended_skill_ids == ["s1"]
```

- [ ] **步骤 2：先写“只挂顶层监督者”的 Builder 失败测试**

```python
@pytest.mark.asyncio
async def test_build_supervisor_attaches_skills_only_to_returned_top_level(monkeypatch):
    attach = AsyncMock()
    monkeypatch.setattr("agent_runtime.supervisor.builder.attach_skill_context", attach)
    agent = await build_supervisor([], "m1", skill_catalog=[SkillDescriptor(**descriptor_dict("s1"))],
                                   recommended_skill_ids=["s1"])
    attach.assert_awaited_once()
    assert attach.await_args.args[0] is agent

def descriptor_dict(skill_id):
    return {
        "skill_id": skill_id,
        "version_id": "v1",
        "name": f"name-{skill_id}",
        "description": f"description-{skill_id}",
        "object_key": f"user/skills/{skill_id}/v1/{skill_id}.zip",
    }
```

测试不要求、也不允许调用 `_runner.register_agent_tools()` 给子 Agent 注入工作空间 Skill。

- [ ] **步骤 3：运行新增测试确认失败**

```powershell
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/serve/apis/test_conversation_team.py agent-runtime/tests/unit_tests/supervisor/test_builder.py -q
```

- [ ] **步骤 4：实现请求模型和传递**

```python
class SkillCatalogItemReq(BaseModel):
    skill_id: str = Field(alias="skillId")
    version_id: str = Field(alias="versionId")
    name: str
    description: str
    object_key: str = Field(alias="objectKey")

class ConversationTeamReq(BaseModel):
    # 保留现有字段
    skill_catalog: list[SkillCatalogItemReq] = Field(default_factory=list, alias="skillCatalog")
    recommended_skill_ids: list[str] = Field(default_factory=list, alias="recommendedSkillIds")
```

`team_sse_stream()` 将请求项转换为 `SkillDescriptor` 后传给 `build_supervisor()`；Runtime 再次校验推荐 ID 必须属于目录，防止绕过 Manager 直接请求内部端点。

- [ ] **步骤 5：在顶层监督者配置后调用单一挂载入口**

`builder.py` 使用明确别名导入，避免函数名在各文件间漂移：

```python
from agent_runtime.supervisor.skill_context import attach as attach_skill_context
```

`builder.py` 只增加参数和以下一行接线：

```python
agent.configure(build_react_config(system_prompt, model_deployment_id))
await attach_skill_context(agent, skill_catalog or [], recommended_skill_ids or [])
```

保持 HandoffTool 循环与子 Agent IR 加载逻辑原样。未来同事把顶层执行者换成单智能体或其他协调者时，只需把同一 `attach_skill_context(top_level_agent, skill_catalog, recommended_skill_ids)` 调用移动到其顶层构建完成处。

- [ ] **步骤 6：在运行生命周期绑定并清理 Skill ContextVar**

先在 `test_runner.py` 断言无论正常完成还是 `agent.stream()` 抛异常，`reset_skill_context()` 都会执行。`run_supervisor()` 的结构固定为：

```python
skill_token = bind_agent_skill_context(agent)
channel = EventChannel(execution_id)
token = set_channel(channel)
```

并把现有 `finally` 改成：

```python
finally:
    reset_channel(token)
    reset_skill_context(skill_token)
```

实现时把现有 runner 主体原样置于该生命周期内，不改变 HandoffTool 事件顺序。

- [ ] **步骤 7：运行 Runtime 对话工作台回归测试**

```powershell
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/supervisor agent-runtime/tests/unit_tests/serve/apis/test_conversation_team.py -q
```

- [ ] **步骤 8：提交任务 5**

```powershell
git add agent-runtime/agent_runtime/serve/apis/conversation_team.py agent-runtime/agent_runtime/supervisor/builder.py agent-runtime/agent_runtime/supervisor/runner.py agent-runtime/tests/unit_tests/serve/apis/test_conversation_team.py agent-runtime/tests/unit_tests/supervisor/test_builder.py agent-runtime/tests/unit_tests/supervisor/test_runner.py
git commit -m "功能(对话工作台): 将技能上下文挂载到顶层智能体"
```

---

### 任务 6：前端 `/` 多选组件

**文件：**

- 新建：`frontend/src/routes/conversation-workspace/conversation-skill.model.ts`
- 新建：`frontend/src/routes/conversation-workspace/skill-selector/skill-selector.component.ts`
- 新建：`frontend/src/routes/conversation-workspace/skill-selector/skill-selector.component.html`
- 新建：`frontend/src/routes/conversation-workspace/skill-selector/skill-selector.component.less`
- 测试：`frontend/src/routes/conversation-workspace/skill-selector/skill-selector.component.spec.ts`

**接口：**

- 输入：`skills: ConversationSkillItem[]`、`disabled: boolean`、`value: string`。
- 双向输出：`valueChange: EventEmitter<string>`、`selectedSkillsChange: EventEmitter<ConversationSkillItem[]>`。
- 发送输出：`sendRequested: EventEmitter<void>`。
- 公开方法：`clearRecommendations()`、`setSkills(items)`。

- [ ] **步骤 1：先写纯组件行为失败测试**

```typescript
it('输入斜杠后按关键词过滤并由 Enter 选择', () => {
  component.skills = [skill('s1', 'meeting-minutes'), skill('s2', 'professional-rewriter')];
  component.value = '请处理 /meet';
  component.onValueInput(component.value);
  expect(component.menuOpen).toBeTrue();
  expect(component.filteredSkills.map((item) => item.skillId)).toEqual(['s1']);

  component.onKeydown(new KeyboardEvent('keydown', { key: 'Enter' }));
  expect(component.selectedSkills.map((item) => item.skillId)).toEqual(['s1']);
  expect(component.value).toBe('请处理 ');
});

it('支持多选去重并保留选择顺序', () => {
  component.selectSkill(skill('s2', 'b'));
  component.selectSkill(skill('s1', 'a'));
  component.selectSkill(skill('s2', 'b'));
  expect(component.selectedSkills.map((item) => item.skillId)).toEqual(['s2', 's1']);
});

it('手写未从菜单确认的斜杠文本不产生推荐', () => {
  component.value = '/meeting-minutes 直接发送';
  component.onValueInput(component.value);
  component.closeMenu();
  expect(component.selectedSkills).toEqual([]);
  expect(component.value).toBe('/meeting-minutes 直接发送');
});

function skill(skillId: string, name: string): ConversationSkillItem {
  return {skillId, name, description: `description-${name}`};
}
```

再覆盖上下键循环、Esc 关闭、标签单项删除、Shift+Enter 换行、普通 Enter 发送、禁用态不打开菜单。

- [ ] **步骤 2：运行前端测试确认组件不存在**

```powershell
cd E:\Desktop\test\agent-studio\frontend
$env:CI="true"
pnpm exec ng test --watch=false --browsers=ChromeHeadless --include="src/routes/conversation-workspace/skill-selector/skill-selector.component.spec.ts"
```

预期：测试编译失败。若本机 pnpm 因 Node 运行时切换要求重建 `node_modules`，先按 `docs/本地开发快速启动.md` 固定 Node 22 与 pnpm 10 后执行 `pnpm install --ignore-scripts`，不得用 pnpm 11 改写锁文件。

- [ ] **步骤 3：实现模型和输入解析**

```typescript
export interface ConversationSkillItem {
  skillId: string;
  name: string;
  description: string;
}

export interface ConversationSendRequest {
  query: string;
  model_deployment_id: string;
  recommended_skill_ids: string[];
}

export interface ConversationSseCallbacks {
  onStatus?: (event: unknown) => void;
  onOpen?: () => void;
  onMessage?: (event: MessageEvent) => void;
  onModeration?: (event: unknown) => void;
  onTimeout?: () => void;
  onDone?: () => void;
  onError?: () => void;
  onAbort?: () => void;
  onReadyStateChange?: (event: unknown) => void;
}
```

斜杠触发只识别光标前最后一个由行首或空白引导的 `/关键词` 片段；选择菜单项时删除该触发片段并保留此前文本。不得通过最终文本反向解析推荐 ID。

- [ ] **步骤 4：实现独立选择器模板和样式**

组件使用 `standalone: true` 并在 `imports` 中复用 `COMMON_MODULES` 与 `LIB_MODULES`。组件内部包含：已选标签行、textarea、浮动菜单、空结果状态。菜单项展示名称与描述；标签删除只改变推荐状态，不修改正文。组件不包含 `+` 智能体按钮，为同事保留父级输入工具栏。`onValueInput(value, cursorPosition)` 使用 textarea 的 `selectionStart`；测试未显式传光标时默认使用 `value.length`。

- [ ] **步骤 5：运行定向测试和 Angular 类型检查**

```powershell
pnpm exec ng test --watch=false --browsers=ChromeHeadless --include="src/routes/conversation-workspace/skill-selector/skill-selector.component.spec.ts"
pnpm exec ng build --configuration development
```

- [ ] **步骤 6：提交任务 6**

```powershell
git add frontend/src/routes/conversation-workspace/conversation-skill.model.ts frontend/src/routes/conversation-workspace/skill-selector
git commit -m "功能(对话工作台): 增加斜杠技能多选组件"
```

---

### 任务 7：前端工作台请求、清理规则与激活展示集成

**文件：**

- 修改：`frontend/src/routes/conversation-workspace/conversation-workspace.service.ts`
- 修改：`frontend/src/routes/conversation-workspace/conversation-workspace.component.ts`
- 修改：`frontend/src/routes/conversation-workspace/conversation-workspace.component.html`
- 修改：`frontend/src/routes/conversation-workspace/conversation-workspace.component.less`
- 测试：`frontend/src/routes/conversation-workspace/conversation-workspace.component.spec.ts`

**接口：**

- `listSkills(): Promise<ConversationSkillItem[]>`。
- `chatSSE(conversationId: string, params: ConversationSendRequest, callbacks: ConversationSseCallbacks)`。
- SSE `skill_activated` 更新当前页面的 `activatedSkills`，刷新历史不恢复。

- [ ] **步骤 1：在修改热点文件前检查同事远端变更**

```powershell
cd E:\Desktop\test\agent-studio
git fetch origin
git diff --name-status HEAD..origin/studio-2.0-dev-0804 -- frontend/src/routes/conversation-workspace agent-runtime/agent_runtime/serve/apis/conversation_team.py agent-runtime/agent_runtime/supervisor/builder.py
```

如果出现同事的 `+` 相关提交，先使用 `superpowers:receiving-code-review` 核对其顶层执行者字段与本计划接口；Skill 选择组件保持为父级工具栏的独立子组件，不改写其智能体状态。

- [ ] **步骤 2：先写请求和状态清理失败测试**

```typescript
it('发送时只提交有序推荐 ID 并在 SSE open 后清空', () => {
  component.recommendedSkills = [skill('s2'), skill('s1')];
  component.inputText = '整理会议';
  component.currentSession = session('c1');
  component.send();

  expect(service.chatSSE).toHaveBeenCalledWith('c1', jasmine.objectContaining({
    query: '整理会议',
    recommended_skill_ids: ['s2', 's1'],
  }), jasmine.any(Object));
  const callbacks = service.chatSSE.calls.mostRecent().args[2];
  callbacks.onOpen();
  expect(component.recommendedSkills).toEqual([]);
});

it('连接前失败保留输入与推荐以便重试', () => {
  const callbacks = startRunWithRecommendations();
  callbacks.onError();
  expect(component.inputText).toBe('整理会议');
  expect(component.recommendedSkills.map((item) => item.skillId)).toEqual(['s1']);
  expect(service.listSkills).toHaveBeenCalled();
});

it('接收技能激活事件后只在当前页面显示标签', () => {
  dispatchSse({event: 'skill_activated', data: {skillId: 's1', name: '会议纪要', versionId: 'v1'}});
  expect(component.activatedSkills.map((item) => item.skillId)).toEqual(['s1']);
});

function skill(skillId: string): ConversationSkillItem {
  return {skillId, name: `name-${skillId}`, description: `description-${skillId}`};
}

function session(conversationId: string): any {
  return {conversation_id: conversationId, title: '会话', status: 'ACTIVE'};
}

function startRunWithRecommendations(): ConversationSseCallbacks {
  let captured!: ConversationSseCallbacks;
  service.chatSSE.and.callFake((_id, _request, callbacks) => {
    captured = callbacks;
    return {close: jasmine.createSpy('close')};
  });
  component.currentSession = session('c1');
  component.inputText = '整理会议';
  component.recommendedSkills = [skill('s1')];
  component.send();
  return captured;
}

function dispatchSse(payload: object): void {
  const assistant = {role: 'assistant' as const, content: '', loading: true};
  (component as any).handleMessage({data: JSON.stringify(payload)}, assistant);
}
```

- [ ] **步骤 3：运行测试确认失败**

```powershell
cd E:\Desktop\test\agent-studio\frontend
$env:CI="true"
pnpm exec ng test --watch=false --browsers=ChromeHeadless --include="src/routes/conversation-workspace/conversation-workspace.component.spec.ts"
```

- [ ] **步骤 4：实现最小目录 API 与页面加载状态**

`ConversationWorkspaceService.listSkills()` 调用：

```typescript
return this.http.getAsync({
  url: `${this.sessionsUrl}/skills`,
  query: { workspace_id: this.http.getWorkspaceId() },
}).then((items: any[]) => (items ?? []).map((item) => ({
  skillId: item.skill_id,
  name: item.name,
  description: item.description,
})));
```

页面初始化时并行加载模型、会话与 Skill。目录加载失败设置 `skillCatalogUnavailable=true` 并显示“当前无法加载工作空间 Skill，本轮仍可普通对话”，不得阻止发送。

- [ ] **步骤 5：集成选择器和发送生命周期**

将原 textarea 替换为独立 `<app-conversation-skill-selector>`，并把 `SkillSelectorComponent` 加入父级 standalone `imports`；`+` 按钮保持父级同级节点。调用 `chatSSE` 前复制本轮快照并清空上一轮 `activatedSkills`：

```typescript
const request: ConversationSendRequest = {
  query,
  model_deployment_id: this.selectedModel,
  recommended_skill_ids: this.recommendedSkills.map((item) => item.skillId),
};
```

使用局部布尔值 `streamOpened` 区分“连接前失败”和“运行中失败”：在 `onOpen` 中置为 `true` 并清空推荐和输入；只有 `streamOpened === false` 的 `onError/onTimeout` 才恢复本轮输入与推荐，并重新调用 `listSkills()` 刷新可能已经失效的推荐项。新建会话、切换会话都清空推荐与激活标签，不从历史恢复；检测到工作空间 ID 变化时同样清空并重新加载目录。

- [ ] **步骤 6：处理 `skill_activated` 事件**

在 `handleMessage()` 增加：

```typescript
case 'skill_activated':
  if (!this.activatedSkills.some((item) => item.skillId === d.skillId && item.versionId === d.versionId)) {
    this.activatedSkills.push({skillId: d.skillId, name: d.name, versionId: d.versionId});
  }
  break;
```

当前页展示“已激活技能：名称”；不要把对象键、本地路径或 `SKILL.md` 正文渲染到页面。

- [ ] **步骤 7：运行前端测试与构建**

```powershell
pnpm exec ng test --watch=false --browsers=ChromeHeadless --include="src/routes/conversation-workspace/**/*.spec.ts"
pnpm exec ng build --configuration development
```

- [ ] **步骤 8：提交任务 7**

```powershell
git add frontend/src/routes/conversation-workspace
git commit -m "功能(对话工作台): 接入技能推荐与激活状态"
```

---

### 任务 8：三层回归、并发隔离、真实联调与合并准备

**文件：**

- 按失败结果最小修改：任务 1—7 已列出的对话工作台文件
- 修改：`docs/superpowers/specs/2026-08-17-conversation-workspace-skill-design.md`（仅当实现接口与已确认设计存在可说明的细节差异）
- 新建：`docs/superpowers/verification/2026-08-17-conversation-workspace-skill-verification.md`

**接口：**

- 验收闭环：浏览器推荐 ID → Manager 鉴权 → Runtime 目录注入 → Agent 激活 → SSE 标签。
- 合并边界：同事 `+` 状态与 `recommended_skill_ids` 并列，最终只向顶层执行者调用一次 `attach_skill_context()`。

- [ ] **步骤 1：执行全量定向自动化测试**

```powershell
cd E:\Desktop\test\agent-studio\backend
mvn -pl studio-manager-service -am "-Dtest=**/conversation/**/*Test" "-Dsurefire.failIfNoSpecifiedTests=false" test

cd E:\Desktop\test\agent-studio
$env:PYTHONPATH="$PWD\agent-runtime;$PWD\packages\storage;$PWD\packages\model_service;$PWD\packages\common_utils"
.\.venv\Scripts\python.exe -m pytest agent-runtime/tests/unit_tests/supervisor agent-runtime/tests/unit_tests/serve/apis/test_conversation_team.py -q

cd E:\Desktop\test\agent-studio\frontend
$env:CI="true"
pnpm exec ng test --watch=false --browsers=ChromeHeadless --include="src/routes/conversation-workspace/**/*.spec.ts"
pnpm exec ng build --configuration development
```

预期：三组测试和前端构建全部通过。

- [ ] **步骤 2：增加并发请求隔离回归**

用两个并发 `team_sse_stream()` 请求分别传 `s1` 和 `s2` 目录，模拟两个 Agent 同时调用 `activate_skill`，断言每个工具只能读取自身目录，且两个请求的 `skill_activated` 事件不会串流。该测试放入 `test_conversation_team.py`，使用 `asyncio.gather()` 与独立 `EventChannel`。

核心并发断言如下：

```python
def agent_with_catalog(skill_id):
    agent = SimpleNamespace()
    cache = AsyncMock()
    cache.load_instructions.return_value = f"instructions-{skill_id}"
    attach_agent_context(
        agent,
        [SkillDescriptor(
            skill_id=skill_id,
            version_id="v1",
            name=f"name-{skill_id}",
            description=f"description-{skill_id}",
            object_key=f"user/skills/{skill_id}/v1/{skill_id}.zip",
        )],
        [],
        cache,
    )
    return agent

async def invoke_in_context(agent, skill_id, execution_id):
    skill_token = bind_agent_skill_context(agent)
    channel = EventChannel(execution_id)
    event_token = set_channel(channel)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": skill_id})
        event = await channel.get()
        return result, event
    finally:
        reset_channel(event_token)
        reset_skill_context(skill_token)

(result_a, event_a), (result_b, event_b) = await asyncio.gather(
    invoke_in_context(agent_with_catalog("s1"), "s1", "exec-1"),
    invoke_in_context(agent_with_catalog("s2"), "s2", "exec-2"),
)
assert result_a["skillId"] == event_a["data"]["skillId"] == "s1"
assert result_b["skillId"] == event_b["data"]["skillId"] == "s2"
```

- [ ] **步骤 3：按本地快速启动文档启动三层服务**

保持已经配置好的本地开发环境和外部依赖，依次启动 Manager、Runtime、Frontend；不要把任务上下文中的测试环境地址写入源码或提交。启动命令以 `docs/本地开发快速启动.md` 第 9 章为准。

- [ ] **步骤 4：使用三个已导入 Skill 做浏览器验收**

依次验证：

1. 不输入 `/` 发送会议整理请求，网络请求含完整 `skillCatalog`，模型可以自主调用 `activate_skill`。
2. 菜单推荐 `professional-rewriter-cn`，Manager 收到对应 ID，Runtime 推荐区顺序正确。
3. 同时推荐 `meeting-minutes-cn` 与 `professional-rewriter-cn`，两项均可按需激活。
4. 手写 `/meeting-minutes-cn` 但不点菜单，请求的 `recommended_skill_ids` 为空。
5. 篡改推荐 ID 为其他工作空间 ID，Manager 在写 user 消息前返回错误。
6. 激活标签实时出现；刷新历史后不恢复标签。
7. 依赖当前未注册命令或沙箱工具的 Skill 可以激活，但执行到缺失工具时明确说明能力缺失，不伪造结果。

- [ ] **步骤 5：重新同步并检查同事 `+` 功能兼容性**

```powershell
cd E:\Desktop\test\agent-studio
git fetch origin
git log --oneline HEAD..origin/studio-2.0-dev-0804
git diff --name-status HEAD..origin/studio-2.0-dev-0804 -- frontend/src/routes/conversation-workspace backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation agent-runtime/agent_runtime/serve/apis/conversation_team.py agent-runtime/agent_runtime/supervisor
```

若基线已前进，先暂停合并并向用户列出冲突文件；获得确认后再 rebase。组合验收必须证明：`+` 选单智能体时 Skill 挂到该单智能体，选多智能体时只挂顶层协调者，Skill 标签操作不改变同事的 Agent 选择。

- [ ] **步骤 6：记录验证证据**

验证文档记录：测试命令与结果、三个 Skill ID/版本但不记录对象存储密钥或临时 URL、七个浏览器场景结果、已知未注册工具导致的预期能力缺失、与最新 `0804` 的提交差异。

- [ ] **步骤 7：提交验证记录**

```powershell
git add docs/superpowers/verification/2026-08-17-conversation-workspace-skill-verification.md docs/superpowers/specs/2026-08-17-conversation-workspace-skill-design.md
git commit -m "测试(对话工作台): 记录技能推荐与激活验证结果"
```

如果设计文档未发生变化，只添加验证文档，不制造无内容修改。

- [ ] **步骤 8：进入完成分支流程**

调用 `superpowers:verification-before-completion` 获取最新测试证据，再调用 `superpowers:requesting-code-review` 审查需求覆盖和越权边界。审查通过后使用 `superpowers:finishing-a-development-branch`，向用户提供“保留个人分支、推送后发起合并”或“经确认后本地合并到 `studio-2.0-dev-0804`”的选择；未经用户确认不得合并或推送。
