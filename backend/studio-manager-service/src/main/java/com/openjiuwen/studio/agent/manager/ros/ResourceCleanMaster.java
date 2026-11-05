/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.ros;

import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.NotifyReq;
import com.openjiuwen.studio.agent.manager.dto.NotifyResp;
import com.openjiuwen.studio.agent.manager.ros.service.CleanResource;
import com.openjiuwen.studio.agent.manager.ros.service.CommonResCleanService;

import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;

/**
 * 资源清理驱动类
 *
 */
@Service
@Slf4j
public class ResourceCleanMaster {

    @Autowired
    private CommonResCleanService commonResCleanService;

    @Autowired
    private ResourceLoader resourceLoader;

    private CleanResource[] cleanResources;

    @Autowired
    private RedisClient redisClient;

    @Value("${tenant.resourceclean.time-window:0,6}")
    private String timeWindowStr;

    private static final int DOMAIN_CLEAN_LOCK_TIME = 10;

    private static final int DOMAIN_CLEAN_RESULT_KEEP_TIME = 2;

    private static final String DOMAIN_CLEAN_LOCK_KEY = "domain:resourceclean:lock:%s";

    /**
     * 清理时间窗
     */
    private List<Integer> timeWindow;

    @PostConstruct
    public void init() throws Exception {
        // 加载资源清理配置
        Resource resource = resourceLoader.getResource("classpath:ros_clean_resource.json");

        // 解析JSON到对象列表
        ObjectMapper objectMapper = new ObjectMapper();
        cleanResources = objectMapper.readValue(resource.getInputStream(), CleanResource[].class);

        timeWindow = Arrays.stream(timeWindowStr.split(",")).map(s -> Integer.parseInt(s)).toList();
    }

    /**
     * 执行清理
     *
     * @param notifyReq 通知请求
     */
    public NotifyResp clean(NotifyReq notifyReq) {
        RedisLock lock = null;
        NotifyResp resp = new NotifyResp();
        try {
            // 加锁，防止重复请求
            lock = redisClient.getLock(String.format(DOMAIN_CLEAN_LOCK_KEY, notifyReq.getDomainId()));
            if (lock.tryLock(Duration.ofSeconds(DOMAIN_CLEAN_LOCK_TIME))) {
                long begin = System.currentTimeMillis();
                List<SingleResResult> resultList = new ArrayList<SingleResResult>();
                if (cleanResources != null && cleanResources.length > 0) {
                    for (CleanResource cleanResource : cleanResources) {
                        SingleResResult res;
                        try {
                            res = cleanSingleResource(notifyReq, cleanResource);
                            // 如果超过时间窗，则停止
                            if (SingleResEnum.OUTOFTIME.equals(res.getResult())) {
                                resultList.add(res);
                                break;
                            }
                        } catch (Exception e) {
                            // 清理异常可以继续清理其他资源
                            String errorInfo = String.format("Resource:%s clean failed.", cleanResource.getResource());
                            log.error(errorInfo, e);

                            // 构造失败结果
                            res = new SingleResResult(cleanResource.getResource());
                            res.setResult(SingleResEnum.FAILED);
                            res.setMsg(errorInfo);
                        }
                        resultList.add(res);
                    }
                }

                // resultMap为空或者没有失败的，则调用管理面接口通知清理成功
                resp.setModuleName(RosConstants.MODULE_NAME);
                // 如果所有资源都清理成功，通知成功
                if (CollectionUtils.isEmpty(resultList)
                    || resultList.stream().allMatch(res -> SingleResEnum.SUCCESS == res.getResult())) {
                    resp.setResCode(RosConstants.SUCCESS);
                    resp.setResMsg(CommonConstant.SUCCESS);
                    resp.setResult(CommonConstant.SUCCESS);
                    resp.setStatus(RosConstants.STATUS_SUCCESS);
                } else {// 否则通知失败
                    resp.setResCode(RosConstants.FAILED);
                    resp.setResMsg(CommonConstant.FAILED);
                    resp.setResult(
                        resultList.stream().map(SingleResResult::getMsg).collect(Collectors.joining(", ", "[", "]")));
                    resp.setStatus(RosConstants.STATUS_FAILED);
                }

                log.info("clean resource domainId:{}, cost:{}, result{}.", notifyReq.getDomainId(),
                    System.currentTimeMillis() - begin, resp);

                // 清理结果记录到redis
                redisClient.set(String.format(RosConstants.DOMAIN_CLEAN_KEY, notifyReq.getDomainId()),
                    JSONObject.toJSONString(resp), Duration.ofDays(DOMAIN_CLEAN_RESULT_KEEP_TIME));

            }
        } catch (Exception e) {
            log.error("clean domainId:{} failed.", notifyReq.getDomainId(), e);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
        return resp;
    }

    private SingleResResult cleanSingleResource(NotifyReq notifyReq, CleanResource cleanResource) {
        long begin = System.currentTimeMillis();
        int sizeSum = 0;
        List<String> ids;
        SingleResResult res = new SingleResResult(cleanResource.getResource());
        do {
            long batchBegin = System.currentTimeMillis();
            LocalDateTime now = LocalDateTime.now();
            int curHour = now.getHour();
            // 超过清理时间窗，停止清理
            if (curHour < timeWindow.get(0) || curHour >= timeWindow.get(1)) {
                String msg = String.format("clean domain:%s, resource:%s exceed the time window.",
                    notifyReq.getDomainId(), cleanResource.getResource());
                log.info(msg);
                res.setResult(SingleResEnum.OUTOFTIME);
                res.setMsg(msg);
                return res;
            }
            ids = commonResCleanService.cleanByDomain(cleanResource, notifyReq.getDomainId());
            int size = CollectionUtils.isEmpty(ids) ? 0 : ids.size();
            sizeSum += size;
            log.info("clean one batch domain:{}, resource:{}, size:{}, cost:{}.", notifyReq.getDomainId(),
                cleanResource.getResource(), size, System.currentTimeMillis() - batchBegin);
        } while (ids.size() > 0);
        log.info("clean summary domain:{}, resource:{}, size:{}, cost:{}.", notifyReq.getDomainId(),
            cleanResource.getResource(), sizeSum, System.currentTimeMillis() - begin);
        return res;
    }

    public enum SingleResEnum {
        SUCCESS,
        FAILED,
        OUTOFTIME
    }

    @Data
    @RequiredArgsConstructor
    public static class SingleResResult {
        private final String resource;

        private SingleResEnum result = SingleResEnum.SUCCESS;

        private String msg;
    }
}
