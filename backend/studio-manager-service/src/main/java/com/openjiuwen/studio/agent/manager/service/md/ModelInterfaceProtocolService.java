/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.md;

import com.openjiuwen.studio.agent.manager.entity.md.MdInterfaceProtocol;
import com.openjiuwen.studio.agent.manager.mapper.md.MdInterfaceProtocolMapper;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

@Slf4j
@Service
public class ModelInterfaceProtocolService {
    private static final long ONE_HOUR = 60L * 60 * 1000;

    private static final String POC_AGENT_BUILDER = "002";

    private static final String HIS_INTERFACE_ID = "008";

    @Value("${model.interface.protocol.poc_agentBuilder_enable:false}")
    private boolean pocAgentBuilderEnable;

    @Value("${model.interface.protocol.his_openai_enable:false}")
    private boolean hisEnable;

    @Value("${model.interface.protocol.update.delay:30000}")
    private int delayTime;

    @Autowired
    private MdInterfaceProtocolMapper mapper;

    /**
     * 延迟预热迁入受管 ThreadPoolTaskScheduler（COM-02：取代占用工作线程睡眠的 Thread.sleep）；
     * schedule 提交失败外层 catch 记告警，不阻断启动
     */
    @Autowired
    @Qualifier("delayWarmupTaskScheduler")
    private ThreadPoolTaskScheduler delayWarmupTaskScheduler;

    private List<MdInterfaceProtocol> cache = new ArrayList<>(0);

    private long lastRefreshTime;

    @PostConstruct
    public void postConstruct() {
        try {
            delayWarmupTaskScheduler.schedule(() -> {
                try {
                    mapper.updateVisible(POC_AGENT_BUILDER, pocAgentBuilderEnable ? "true" : "false");
                    mapper.updateVisible(HIS_INTERFACE_ID, hisEnable ? "true" : "false");
                } catch (Exception e) {
                    // 任务体记录完整异常栈（ErrorHandler 只收未捕获异常，此处已捕获故自带栈）
                    log.warn("Fail update MdInterfaceProtocol visible.", e);
                }
            }, delayWarmupTaskScheduler.getClock().instant().plusMillis(delayTime));
        } catch (org.springframework.core.task.TaskRejectedException e) {
            log.warn("startup delay-warmup schedule rejected, skip MdInterfaceProtocol visible update.", e);
        }
    }

    private List<MdInterfaceProtocol> getAllProtocols() {
        if (System.currentTimeMillis() - lastRefreshTime > ONE_HOUR) {
            mapper.updateVisible(POC_AGENT_BUILDER, pocAgentBuilderEnable ? "true" : "false");
            mapper.updateVisible(HIS_INTERFACE_ID, hisEnable ? "true" : "false");
            cache = mapper.queryAllProtocols();
            lastRefreshTime = System.currentTimeMillis();
        }
        return cache;
    }

    public List<MdInterfaceProtocol> queryProtocols(String modelType, String visible) {
        Stream<MdInterfaceProtocol> protocols = new ArrayList<>(getAllProtocols()).stream();
        if (!StringUtils.isEmpty(modelType)) {
            protocols = protocols.filter(protocol -> protocol.getModelTypes().contains(modelType));
        }
        if (!StringUtils.isEmpty(visible)) {
            protocols = protocols.filter(protocol -> protocol.getVisible().equals(visible));
        }
        return protocols.toList();
    }
}
