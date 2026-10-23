# COM-03 Manager 全量 Reactor 基线差集

> 生成日期：2026-09-15
> 基线 commit：`f01e23c5d7387b18c45c0fd3bf7fe919c0ee10a3`（origin/debug_log_20260818）
> 候选 commit：COM-03 收口提交（见 `git log --oneline -1`，feat(error-contract): COM-03 收口）
> 采集命令：`mvn test -Dmaven.test.failure.ignore=true -pl studio-common,studio-manager-service -am`
> 解析命令：`python3 -c "import xml.etree.ElementTree as ET; ..."`（Surefire XML → testcase 级失败集合）

## 聚合

| 指标 | 基线 (f01e23c5) | 候选 | 差异 |
|---|---|---|---|
| 总测试数 | 4492 | 4572 | +80（COM-03 新增） |
| failures | 3 | 2 | -1 |
| errors | 29 | 29 | 0 |
| **新增失败** | — | — | **0** |
| 消失失败 | — | — | **1** |
| 不变失败 | — | — | **31** |

## 消失的基线失败（COM-03 修复）

| 测试类.方法 | 基线失败原因 | 消失原因 |
|---|---|---|
| MgGlobalExceptionHandlerTest.testHandleAsyncRequestTimeoutException | Expected NumberFormatException to be thrown, but nothing was thrown | COM-03 新增 handler 覆盖该异常 |

## 不变的基线失败（COM-03 未触碰的业务模块预置失败，31 项）

| 测试类 | 数量 | 失败原因 |
|---|---|---|
| KnowledgeSourceEnumTest | 1 | expected: <3> but was: <4> |
| RagFlowConnectorTest | 1 | Cannot invoke (NPE) |
| AgentManagementServiceTest | 2 | Cannot invoke ThreadPoolTaskExecutor (NPE) |
| CommonManagementServiceTest | 11 | Could not find field 'obsExpires' |
| CommonUtilTest | 1 | expected nested.com but was nested.com/mcp |
| OptimizationTemplateServiceTest | 14 | Could not find field 'jiuwenBaseUrl' |
| ObsUtilTest | 1 | Cannot instantiate @InjectMocks 'obsUtil' |

## 不变的基线失败——31 个 `classname.method` 完整身份

以下 31 个测试在基线和候选中均失败（集合完全一致，无"一项消失一项新增"可能）：

| # | classname.method | 失败原因 |
|---|---|---|
| 1 | com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnumTest.testValues | expected: <3> but was: <4> |
| 2 | com.openjiuwen.studio.agent.foundation.connection.connection.ragflow.RagFlowConnectorTest.test_listKnowledgeBase_should_return_not_null_when_condition | Cannot invoke (NPE) |
| 3 | com.openjiuwen.studio.agent.manager.service.AgentManagementServiceTest.testDeleteAgent_HardDelete | Cannot invoke ThreadPoolTaskExecutor (NPE) |
| 4 | com.openjiuwen.studio.agent.manager.service.AgentManagementServiceTest.testDeleteAgent_Success | Cannot invoke ThreadPoolTaskExecutor (NPE) |
| 5 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testInit_ParsesConfigurations | Could not find field 'obsExpires' |
| 6 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testListTags_Empty | Could not find field 'obsExpires' |
| 7 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testListTags_Success | Could not find field 'obsExpires' |
| 8 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testSystemSettings_Success | Could not find field 'obsExpires' |
| 9 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testSystemSettings_WithConfigs | Could not find field 'obsExpires' |
| 10 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testUploadAvatar_EmptyFile | Could not find field 'obsExpires' |
| 11 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testUploadAvatar_FileTooLarge | Could not find field 'obsExpires' |
| 12 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testUploadAvatar_InvalidFileName | Could not find field 'obsExpires' |
| 13 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testUploadAvatar_NullFile | Could not find field 'obsExpires' |
| 14 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testUploadAvatar_Success | Could not find field 'obsExpires' |
| 15 | com.openjiuwen.studio.agent.manager.service.CommonManagementServiceTest.testUploadAvatar_UnsupportedFileType | Could not find field 'obsExpires' |
| 16 | com.openjiuwen.studio.agent.manager.utils.CommonUtilTest.testParseUrlFromMcpConfig_NestedUrl | expected nested.com but was nested.com/mcp |
| 17 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testChangeOptimization_Non2xx_Throws | Could not find field 'jiuwenBaseUrl' |
| 18 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testChangeOptimization_Restart | Could not find field 'jiuwenBaseUrl' |
| 19 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testChangeOptimization_Stop | Could not find field 'jiuwenBaseUrl' |
| 20 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testCreateOptimization_Non2xx_Throws | Could not find field 'jiuwenBaseUrl' |
| 21 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testCreateOptimization_NonOKCode_Throws | Could not find field 'jiuwenBaseUrl' |
| 22 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testCreateOptimization_NullBody_Throws | Could not find field 'jiuwenBaseUrl' |
| 23 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testCreateOptimization_ResourceAccessException_Throws | Could not find field 'jiuwenBaseUrl' |
| 24 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testCreateOptimization_Success | Could not find field 'jiuwenBaseUrl' |
| 25 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testDeleteOptimization_Non2xx_Throws | Could not find field 'jiuwenBaseUrl' |
| 26 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testDeleteOptimization_Success | Could not find field 'jiuwenBaseUrl' |
| 27 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testGetOptimizationProgress_Non2xx_Throws | Could not find field 'jiuwenBaseUrl' |
| 28 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testGetOptimizationProgress_NullBody_Throws | Could not find field 'jiuwenBaseUrl' |
| 29 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testGetOptimizationProgress_ResourceAccessException_Throws | Could not find field 'jiuwenBaseUrl' |
| 30 | com.openjiuwen.studio.prompt.engineering.service.OptimizationTemplateServiceTest.testGetOptimizationProgress_Success | Could not find field 'jiuwenBaseUrl' |
| 31 | com.openjiuwen.studio.prompt.engineering.utils.ObsUtilTest.test_checkZipBomb_IoException | Cannot instantiate @InjectMocks 'obsUtil' |

## 差集生成方法

```bash
# 基线采集
git worktree add /tmp/com03-baseline f01e23c5
cd /tmp/com03-baseline/backend
mvn test -Dmaven.test.failure.ignore=true -pl studio-common,studio-manager-service -am
# 解析 Surefire XML

# 候选采集
cd <agent-studio>/backend
mvn test -Dmaven.test.failure.ignore=true -pl studio-common,studio-manager-service -am
# 解析 Surefire XML

# 差集
python3 -c "
import xml.etree.ElementTree as ET
import glob

def collect_failures(base_dir):
    failures = set()
    for pattern in [
        'studio-manager-service/target/surefire-reports/*.xml',
        'studio-common/target/surefire-reports/*.xml',
    ]:
        for f in glob.glob(f'{base_dir}/{pattern}'):
            tree = ET.parse(f)
            for tc in tree.iter('testcase'):
                if tc.find('failure') is not None or tc.find('error') is not None:
                    cls = tc.get('classname','?')
                    name = tc.get('name','?')
                    failures.add(f'{cls}.{name}')
    return failures

baseline = collect_failures('/tmp/com03-baseline/backend')
current = collect_failures('<agent-studio>/backend')

print(f'New: {sorted(current - baseline)}')
print(f'Disappeared: {sorted(baseline - current)}')
print(f'Unchanged: {len(baseline & current)}')
"
```
