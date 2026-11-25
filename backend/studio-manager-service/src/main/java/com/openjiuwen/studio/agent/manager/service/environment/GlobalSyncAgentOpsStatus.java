/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.environment;

import com.openjiuwen.studio.agent.manager.observability.MdcScope;
import com.openjiuwen.studio.agent.manager.observability.MdcSnapshot;

import lombok.extern.slf4j.Slf4j;

import java.util.Objects;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.function.Consumer;

/**
 * 全局待同步数据队列，用户异步同步数据信息
 *
 */
@Slf4j
public class GlobalSyncAgentOpsStatus<T> {
    private static volatile GlobalSyncAgentOpsStatus<?> instance;

    /**
     * 线程安全的队列（元素携带入队时的 MDC 快照，供处理线程按项传播）
     */
    private final ConcurrentLinkedQueue<QueuedItem<T>> queue;

    /**
     * 处理数据的消费者
     */
    private Consumer<T> dataProcessor;

    /**
     * 是否运行
     */
    private final boolean isRunning;

    /**
     * 私有构造函数，防止外部实例化
     *
     */
    private GlobalSyncAgentOpsStatus() {
        queue = new ConcurrentLinkedQueue<>();
        isRunning = false;
    }

    /**
     * 同步实例
     */
    private static final Object INSTANCE_LOCK = new Object();

    /**
     * 获取单例实例
     *
     */
    @SuppressWarnings("unchecked")
    public static <T> GlobalSyncAgentOpsStatus<T> getInstance() {
        if (instance == null) {
            synchronized (INSTANCE_LOCK) {
                if (instance == null) {
                    instance = new GlobalSyncAgentOpsStatus<>();
                }
            }
        }
        return (GlobalSyncAgentOpsStatus<T>) instance;
    }

    /**
     * 处理方法
     *
     */
    public void setDataProcessor(Consumer<T> processor) {
        this.dataProcessor = processor;
    }

    /**
     * 启动线程
     *
     */
    public void start() {
        if (isRunning || dataProcessor == null) {
            return;
        }

        // 队列空时休眠，减少CPU消耗；处理每项时安装入队时捕获的 MDC 快照
        Thread processThread = new Thread(() -> {
            while (true) {
                try {
                    QueuedItem<T> item = queue.poll();
                    if (item != null) {
                        try (MdcScope scope = item.snapshot.openScope()) {
                            dataProcessor.accept(item.data);
                        }
                    } else {
                        // 队列空时休眠，减少CPU消耗
                        Thread.sleep(3000);
                    }
                } catch (Exception e) {
                    log.error("Sync data error: {}", e.getMessage());
                }
            }
        }, "Sync-Env-STATE-Queue-Processor");
        processThread.start();
    }

    /**
     * 添加数据到队列（在提交线程捕获 MDC 四 key，供处理线程关联请求日志）
     *
     */
    public void addData(T data) {
        if (data != null && !this.contains(data)) {
            queue.add(new QueuedItem<>(data, MdcSnapshot.capture()));
        }
    }

    public boolean contains(T data) {
        for (QueuedItem<T> item : queue) {
            if (Objects.equals(item.data, data)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 获取队列大小
     *
     */
    public int size() {
        return queue.size();
    }

    /**
     * 清空队列
     *
     */
    public void clear() {
        queue.clear();
    }

    private static final class QueuedItem<T> {
        private final T data;
        private final MdcSnapshot snapshot;

        private QueuedItem(T data, MdcSnapshot snapshot) {
            this.data = data;
            this.snapshot = snapshot;
        }
    }
}
