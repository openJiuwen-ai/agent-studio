/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.startup;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AgentVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.prompt.engineering.service.stratup.UpdatePromptService;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.core.io.support.ResourcePatternResolver;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.time.Duration;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.concurrent.ThreadPoolExecutor;

import javax.sql.DataSource;

@Slf4j
@Component
public class SyncAgentWorkflowObsTask implements CommandLineRunner {
    private final static String OBS_PATH = "classpath:obs/**/*";

    private static final String SYNC_PRE_AGENT_WORKFLOW_OBS_LOCK = "SYNC_PRE_AGENT_WORKFLOW_OBS_LOCK";

    @Autowired
    private RedisClient redisClient;

    @Autowired
    MgObsService obsService;

    @Autowired
    private DataSource dataSource;

    @Autowired
    private AppMapper appMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private AgentVersionMapper agentVersionMapper;

    @Autowired
    private ReleaseChannelMapper releaseChannelMapper;

    @Autowired
    private UpdatePromptService updatePromptService;

    @Value("${isHcs:false}")
    private Boolean isHcs;

    @Value("${plugin-publish:false}")
    private Boolean isCustom;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    private final ResourcePatternResolver resolver;

    @Autowired
    @Qualifier("taskExecutor")
    private Executor taskExecutor;

    public SyncAgentWorkflowObsTask(ResourceLoader resourceLoader) {
        // 使用PathMatchingResourcePatternResolver来支持通配符路径
        this.resolver = new PathMatchingResourcePatternResolver(resourceLoader);
    }

    // 配置Spring TaskExecutor（通过@Bean定义，由Spring管理）
    @Component
    static class TaskExecutorConfig {
        @Bean("taskExecutor")
        public ThreadPoolTaskExecutor taskExecutor() {
            ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
            // 核心线程数
            executor.setCorePoolSize(5);
            // 最大线程数
            executor.setMaxPoolSize(10);
            // 队列容量
            executor.setQueueCapacity(25);
            // 线程名称前缀（便于日志排查）
            executor.setThreadNamePrefix("obs-sync-");
            // 线程空闲超时时间（秒）
            executor.setKeepAliveSeconds(60);
            // 拒绝策略（当任务满时如何处理）
            executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
            // 初始化
            executor.initialize();
            return executor;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void run(String... args) {
        RedisLock lock = null;
        log.info("Start sync platform agent workflow obs to obs, isHcs: {}", isHcs);
        if (isHcs) {
            try {
                lock = redisClient.getLock(SYNC_PRE_AGENT_WORKFLOW_OBS_LOCK);
                if (lock.tryLock(Duration.ofSeconds(3))) {
                    taskExecutor.execute(() -> {
                        log.info("Start sync platform agent workflow obs to obs.");
                        uploadPreObsFiles(OBS_PATH);
                    });
                    taskExecutor.execute(() -> {
                        log.info("Start sync update platform prompt");
                        updatePromptService.updatePrompt();
                    });
                } else {
                    log.warn("Fail get {} lock.", SYNC_PRE_AGENT_WORKFLOW_OBS_LOCK);
                }
            } catch (Exception e) {
                log.error("Sync platform agent workflow obs to obs exception.", e);
            } finally {
                if (lock != null) {
                    lock.unlock();
                }
            }
        }
    }

    public void updateProjectId() {

        List<String> appIds = Arrays.asList("e87a3373-4fa2-4a44-b9f4-b9e7de441111",
            "da72792a-085c-469b-a6d7-5ca8c9fe1111", "deaf428c-76c3-4bdb-88f5-8c5f51b11111",
            "d0847695-7d47-4136-9f4b-86cff0561111", "c5a8d153-6afe-4a46-9c0e-5dfa63611111",
            "a7414e1f-656c-4d6f-9557-30f7cf9b1111", "a08cd6fb-e838-456b-a2ad-2e001aae1111",
            "94679be9-d0c3-49f4-aeae-85f5f1e01111", "60d46798-f9cc-4612-b5e9-e79b628c1111",
            "7aa63ae1-88c2-41c3-bf4c-ec0c345d1111", "819c4036-7fc1-41df-8e44-60f3f0ea77eb",
            "85a7466a-5863-40c0-9a07-11e71937f3af", "901e5a78-873b-4db8-bc23-d4b277f8749a",
            "901e5a78-873b-4db8-bc23-d4b277f81111", "901e5a78-873b-4db8-bc23-d4b277f82222",
            "901e5a78-873b-4db8-bc23-d4b277f83333", "901e5a78-873b-4db8-bc23-d4b277f84444");

        appMapper.updateProjectIdByAppIds(opSvcProjectId, appIds);

        List<String> agentIds = Arrays.asList("1d8b9c6e-9c61-4059-8c9f-89e30c4e12ea",
            "1dc29182-b0fe-4a76-8b3f-5795f8486542", "2f5dc8b8-5779-4d6c-8259-3421c4947f02",
            "40958692-9adb-42c1-a28c-f460ced4667d", "70ee3233-9fe4-4128-a244-d028179df486",
            "b4c3cad3-f312-4700-8d23-fb986a3b578c", "c2984499-223a-4ee8-8d2f-22597358dbf5",
            "d34ede8a-5619-4567-8010-4091f1cbc4d7", "e37eccd1-d3a5-491d-a1f5-83e37661c492",
            "fb15da21-b5f5-4511-a48b-04ddcda24ea3");

        agentMapper.updateProjectIdByAgentIds(opSvcProjectId, agentIds);

        List<String> workflowIds = Arrays.asList("1c0e0f70-ca4b-43cf-99ca-d8126fb70ed4",
            "e5caa392-1808-4d20-90fc-54fbe74c8734", "2fdc9e50-161b-4a52-83db-bb583aa86992",
            "7bc4b323-809e-4fce-a907-ccc1d18385e5", "7e99041f-6e5a-479c-a557-c66af2bf0451",
            "86dc0d48-6268-4252-9dd1-f935f2691b72", "ce6d9a5a-3c4c-4e69-a1fb-b41f8e0be1eb");

        workflowMapper.updateProjectIdByIds(opSvcProjectId, workflowIds);

        List<String> versionIds = Arrays.asList("007faff2-f29b-4244-9c88-7c9a6dedac9e",
            "048aaad3-edcb-44cf-8a85-ddeb758eaa28", "08891c2f-b231-42a7-ad54-0d7044ce49be",
            "088f37c1-9f56-4fa4-b719-e42dbd8a5f27", "09221763-4cce-4e5c-befe-0297359ae1e4",
            "0a9992ac-c29c-448b-88fd-e7f0adf663d0", "0cd6b4ff-c35d-4675-aa52-3d99b885fee2",
            "108977d9-52ae-4147-a703-34f6d42c7c03", "162597e4-6d35-4957-8cab-d6961f263014",
            "16615e6e-2225-4867-aafe-443080b6c0a7", "1e9b6bf7-5ffd-467d-919e-95b5ce31ad06",
            "20250907-1234-5678-abcd-def123451111", "20250907-1234-5678-abcd-def123451122",
            "20250907-1234-5678-abcd-def123452222", "214714a2-74ba-41de-84c7-ade9956e4bf1",
            "270c13d6-1e49-410e-8390-011870ae5730", "339e4b21-492c-470c-aee5-7ff6ef6b03d9",
            "388a7fe6-8200-4749-a6d2-b5a622716bfc", "3e9c89fb-7d2b-454b-a098-deacf1a7d501",
            "3ed7a263-3f69-47a4-b76c-65370677a128", "3f75a29a-d8e6-4c56-9ae9-ab9c9d8ef3c0",
            "42ef6e83-67e1-4e27-9488-a1985458c562", "451326f6-1d56-4797-8503-1445b2ea5015",
            "4545fc71-8040-45c7-9e4e-f437b0522452", "46fcd577-17f9-4d4e-b5d5-deffc003cf60",
            "4a644c44-e4c8-4680-aeec-1d9d51929d83", "4cd340c0-481b-4407-a819-15d838efd552",
            "4fb6c6b7-68b8-4867-8cd6-cfb31b728720", "518b3e5d-aaf2-4ba6-bc98-dd712c6cf539",
            "54057978-5903-4b5b-93a0-e3eb48537cb9", "5727d0bc-998f-482e-b48e-0efdacb6ad3f",
            "5aaf0225-c496-419c-98e3-56d0531a27a4", "5aca5292-b66e-46bb-80ca-2c20a260c59a",
            "5cd50f2d-e76c-4526-a858-d9e15921d750", "5e995439-478b-40b4-b8d9-5f412d50087a",
            "5fb71cdc-0e69-4e3c-b308-10854f08b6a3", "60879441-6fa8-4859-b5ee-c7b7e2919dc9",
            "622ba516-d5e1-431f-8352-42c553bc231c", "67cf0631-3835-4504-b3d9-937c49fadd1e",
            "692c34aa-48ee-4f3d-af64-40373a9f173a", "69b39f7a-3019-4115-908b-6d189eeb5860",
            "6c661a48-bc92-49e1-940a-9c51ff2d2e08", "6e5d9acc-b857-4728-8354-ca5aa75dd5bf",
            "703498e5-ca5c-476a-832b-ae6ddb580ea0", "70d10621-efeb-4e71-a204-164dc264d537",
            "74468ff4-64c2-4097-9d6f-0985999567dd", "7563dcf4-b3a6-4789-897b-ccf630e416e9",
            "77c7e7fb-3606-4d06-9226-1337901fbabf", "79ee0020-4ce3-4256-92f6-cfd504827eda",
            "7bc3691d-1346-4374-a9bf-4c7515798791", "7bdfb5a7-a2fc-49e2-886e-cc7ae862cfb9",
            "7d520e4f-d14b-4970-80ae-12a329820c03", "7dc3ecc4-f10a-4598-a5ab-52f708c7fb53",
            "800e8d9f-f9f5-465d-9ac9-bef7e5dd0c96", "82a4b993-2700-4568-9bae-6fb1ae4a4611",
            "83abb835-dcaf-4e3c-a4b1-23990b73c9bb", "864c7604-93cf-4a55-911d-c5866008764c",
            "8886d4d9-f0a8-447d-9ffd-c8fcf32eb40a", "89adf652-1cd8-4e72-af43-71b8ac31bd71",
            "9770274e-1113-423c-a725-15479f285dc2", "990d046a-be77-449c-b66c-27a42d2c65ab",
            "9d70d26d-05f9-4459-9aea-920f7c7e0d91", "9f088354-163c-458d-9d65-4a39e951d560",
            "a1e79c5e-6d52-4957-a868-4dabde9c3d32", "a3b2fe41-2060-49a2-9fa6-f7341f6616f9",
            "a4021e92-f82c-40da-bbf1-559308925f2c", "a47cbf23-f5e3-44be-ba99-c882452f830c",
            "abb640cc-db87-46ea-9250-ff5068a95201", "ad9ebdf0-3e3d-41cb-8cfc-dd6b2d0d6fe4",
            "add99263-e1e1-439c-baec-5564c3c5c2de", "b2158765-4432-4e84-870d-d3f94e1480e4",
            "b28140a9-3c28-4235-9bdd-fb06a73c6421", "bff90f70-0ff9-42d1-aba1-bdc1f4161d12",
            "c1a40652-b217-473d-8ed6-a5ea7b9683ac", "c208ba68-38a0-477f-ac7d-5aba39baa714",
            "c431eea3-9760-4961-9711-78c856058496", "c6a2983d-a6c3-4fd6-a73e-9696eed3e4ec",
            "c94776bd-94ea-4de8-8717-ddfda290e07b", "cab65395-e3ec-4460-9d21-18122e641814",
            "cb6f04f9-5f06-4d47-8f44-402b569a303d", "d2353b59-22be-4ece-947f-eb1f2d7f3baf",
            "d717bc38-16b4-4b8c-b7b5-b7eb3e31c58d", "da555d07-001e-4feb-aadf-32662d972858",
            "e129dea0-99ca-4310-a771-e6aa19e97c62", "e258e257-286a-4e24-80a9-fc4144c0db12",
            "e77968fb-eb77-4fbb-89ed-a2b15c175d5b", "e7a02f29-19cf-49cf-ab1d-8c234d5875d3",
            "e7c8c4d5-2f12-407e-a9d1-5b0e7c3397bb", "edb9e249-9fb7-4456-8c9e-6cb1d77629c5",
            "ef808d3e-0640-438f-9de2-5549613f9296", "f002604e-d852-4e41-bf3e-b27e73423dab",
            "f5916f20-d096-4913-ae1a-2e491eab000a", "f6ba35ec-4580-4c3e-9c4d-6182c323346c",
            "fb3d6a46-adcb-4d58-87fa-e2bf4122fc7e", "fe9ddc15-65af-45db-b0e0-f8d2eef0e464",
            "ffb4cc17-7601-442c-97c1-0b74de3a7151");

        agentVersionMapper.updateProjectIdByVersionIds(opSvcProjectId, versionIds);

        List<String> releaseChannelIds = Arrays.asList("2ddb0ad8-8ff2-44fd-bd22-3109b9213a9f",
            "3bc68ad3-db98-44c9-bf0b-3628e6bbf819", "3f2f8dfc-7827-4d92-9ae9-99c2e472f10c",
            "455a151d-9eeb-4b2f-9001-e6a371b1936a", "5196a2c9-1518-42e0-b74b-1ef47491d584",
            "555cdcad-a9b8-4d0a-b515-cc19f8b8ee60", "62e446f0-e3b1-4086-92a6-bb76fe959572",
            "6e41f00a-5f34-4c74-a6ca-89e0a184ecdf", "738359ae-6f09-45c0-b27d-b0aa6ca55b79",
            "739a4ceb-9485-4a9e-b255-51493cc8d926", "7da3078d-21dc-459c-b7b9-2f1b3bd8dd74",
            "95b81f10-bef4-4c24-9c30-2dd4e1d35135", "a37abab3-dbab-48e9-bbb7-f781d34a1a10",
            "a5c5124f-b68c-477b-81da-a92bd5b0c3fc", "b6e5ecbc-71a5-44aa-83fd-8c518cecac15",
            "bdfb88be-d417-4e6e-8788-f4a17f75842e", "c4153922-c573-4c46-af63-cd8bfc5c0c61",
            "c9a725c3-70a1-4629-88a7-ac28acb34575");
        releaseChannelMapper.updateProjectIdByIds(opSvcProjectId, releaseChannelIds);

        log.info("update successfully!!!");

    }

    public void uploadPreObsFiles(String filePath) {
        try {
            if (filePath == null || filePath.isEmpty()) {
                return;
            }
            Resource[] resources = resolver.getResources(filePath);
            int uploadCount = 0;
            for (Resource resource : resources) {
                if (resource.exists()) {
                    // 检查是否为目录
                    boolean isDirectory = false;
                    // 对于JAR包内资源，通过URL判断
                    String resourceUrl = resource.getURL().toString();
                    isDirectory = resourceUrl.endsWith("/") || resource.getFilename() == null;

                    if (!isDirectory) {
                        // 获取文件名和内容（同上）
                        String obsPath = getOBSPath(resource.getURL().getPath());

                        try (InputStream inputStream = resource.getInputStream()) {
                            byte[] contentBytes = inputStream.readAllBytes();
                            String content = new String(contentBytes, StandardCharsets.UTF_8);
                            obsService.putObject(obsPath, content);
                            uploadCount++;
                            log.info("upload file {} to obs path successfully", obsPath);
                        }
                    }
                }
            }
            log.info("upload {} files to obs successfully", uploadCount);
        } catch (IOException e) {
            log.error("upload obs file failed", e);
        }
    }

    public static String getOBSPath(String url) {
        if (url == null) {
            return null;
        }
        // 查找"obs/"的位置
        int index = url.indexOf("obs/");
        if (index != -1) {
            // 截取"obs/"之后的部分（index + 4是因为"obs/"长度为4）
            return url.substring(index + 4);
        }
        // 如果没有找到"obs/"，返回空字符串或原字符串
        return null;
    }

    public void executeEntireSqlFile(String sqlFilePath) {
        try (Connection connection = dataSource.getConnection()) {
            // 加载SQL文件资源
            Resource sqlResource = resolver.getResource(sqlFilePath);

            if (!sqlResource.exists()) {
                log.error("SQL file is not exist: {}", sqlFilePath);
                throw new IllegalArgumentException("SQL file not found: " + sqlFilePath);
            }

            // 执行整个SQL脚本
            ScriptUtils.executeSqlScript(connection, sqlResource);

            log.info("SQL execute successfully: {}", sqlFilePath);
        } catch (Exception e) {
            log.error("SQL execute failed: {}", sqlFilePath, e);
        }
    }

}
