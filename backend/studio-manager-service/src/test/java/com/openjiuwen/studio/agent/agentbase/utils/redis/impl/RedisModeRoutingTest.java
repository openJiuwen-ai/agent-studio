/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.utils.redis.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.impl.RedisClientRedisson;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;

/**
 * 验证 redisMode 与 cluster_node_list / node_addr_list 各种组合下，RedisClientRedisson 实际走的初始化路径。
 *
 * 判定方式：构造 RedisClientRedisson 后，捕获传入 Redisson.create(config) 的 Config 对象，
 * 通过反射读取 clusterServersConfig / sentinelServersConfig / singleServerConfig 字段，
 * 哪个非 null 即确认走了哪条路径。
 *
 * 路由逻辑（RedisClientRedisson 构造器）：
 *   mode 显式声明时，mode 优先（大小写不敏感）
 *   mode 为空/null 时，回退到 cluster_node_list / node_addr_list 非空判断
 *
 * 注意：单元测试不经过 Spring 注入，@Value 默认值不生效，String 字段为 null。
 * init* 方法内部会对 String 字段调用 .split()，所以需把所有 String 字段初始化为 ""。
 */
@ExtendWith(MockitoExtension.class)
class RedisModeRoutingTest {

    private MockedStatic<Redisson> redissonStatic;

    @BeforeEach
    void setUp() {
        redissonStatic = org.mockito.Mockito.mockStatic(Redisson.class);
        redissonStatic.when(() -> Redisson.create(org.mockito.ArgumentMatchers.any(Config.class)))
            .thenReturn(org.mockito.Mockito.mock(RedissonClient.class));
    }

    @AfterEach
    void tearDown() {
        if (redissonStatic != null) {
            redissonStatic.close();
        }
    }

    /** 创建配置并初始化所有 String 字段为空字符串，避免 init* 方法内 .split() NPE */
    private RedisClientConfig newConfig() {
        RedisClientConfig config = new RedisClientConfig(new Ciphers(null, null));
        config.setJsonMaxStringLength(10000);
        config.setRedisHost("127.0.0.1");
        config.setRedisPort(6379);
        config.setRedisPassword("");
        config.setNodeAddrList("");
        config.setMasterName("mymaster");
        config.setSentinelPorts("");
        config.setTargetPorts("");
        config.setClusterNodeList("");
        return config;
    }

    /** 捕获 Redisson.create 收到的 Config，通过反射判定走了哪条初始化路径 */
    private String resolveActualMode(RedisClientConfig config) {
        ArgumentCaptor<Config> captor = ArgumentCaptor.forClass(Config.class);
        new RedisClientRedisson(config);
        redissonStatic.verify(() -> Redisson.create(captor.capture()));
        Config captured = captor.getValue();

        Object clusterCfg = getConfigField(captured, "clusterServersConfig");
        Object sentinelCfg = getConfigField(captured, "sentinelServersConfig");
        Object singleCfg = getConfigField(captured, "singleServerConfig");

        int nonNull = (clusterCfg != null ? 1 : 0) + (sentinelCfg != null ? 1 : 0) + (singleCfg != null ? 1 : 0);
        assertEquals(1, nonNull, "应恰好有一条路径被初始化");

        if (clusterCfg != null) return "cluster";
        if (sentinelCfg != null) return "sentinel";
        return "single";
    }

    private Object getConfigField(Config config, String fieldName) {
        try {
            java.lang.reflect.Field field = Config.class.getDeclaredField(fieldName);
            field.setAccessible(true);
            return field.get(config);
        } catch (NoSuchFieldException | IllegalAccessException e) {
            return null;
        }
    }

    // ====================================================================
    // 一、mode=single（默认值），无节点列表 → single
    // ====================================================================

    @Test
    @DisplayName("mode=single + 无 cluster_node_list + 无 node_addr_list → single")
    void modeSingle_noNodes_shouldRouteSingle() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("single");

        assertEquals("single", resolveActualMode(cfg));
    }

    // ====================================================================
    // 二、mode 显式声明，与节点列表一致
    // ====================================================================

    @Test
    @DisplayName("mode=cluster + cluster_node_list 有值 → cluster")
    void modeCluster_withNodes_shouldRouteCluster() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("cluster");
        cfg.setClusterNodeList("127.0.0.1:7001,127.0.0.1:7002");

        assertEquals("cluster", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=sentinel + node_addr_list 有值 → sentinel")
    void modeSentinel_withNodes_shouldRouteSentinel() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("sentinel");
        cfg.setNodeAddrList("127.0.0.1:26379");
        cfg.setSentinelPorts("26379");
        cfg.setTargetPorts("6379");

        assertEquals("sentinel", resolveActualMode(cfg));
    }

    // ====================================================================
    // 三、mode 显式声明，节点列表为空（仅靠 mode 驱动）
    // ====================================================================

    @Test
    @DisplayName("mode=cluster + cluster_node_list 为空 → cluster（仅靠 mode 驱动）")
    void modeCluster_noNodes_shouldStillRouteCluster() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("cluster");

        assertEquals("cluster", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=sentinel + node_addr_list 为空 → sentinel（仅靠 mode 驱动）")
    void modeSentinel_noNodes_shouldStillRouteSentinel() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("sentinel");
        cfg.setSentinelPorts("26379");
        cfg.setTargetPorts("6379");

        assertEquals("sentinel", resolveActualMode(cfg));
    }

    // ====================================================================
    // 四、mode=single 显式声明，但填了集群/哨兵节点 → 仍走 single（mode 优先）
    // ====================================================================

    @Test
    @DisplayName("mode=single + cluster_node_list 有值 → single（mode 优先，不走集群）")
    void modeSingle_withClusterNodes_shouldRouteSingle() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("single");
        cfg.setClusterNodeList("127.0.0.1:7001");

        assertEquals("single", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=single + node_addr_list 有值 → single（mode 优先，不走哨兵）")
    void modeSingle_withSentinelNodes_shouldRouteSingle() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("single");
        cfg.setNodeAddrList("127.0.0.1:26379");

        assertEquals("single", resolveActualMode(cfg));
    }

    // ====================================================================
    // 五、mode 与节点列表冲突时，mode 优先
    // ====================================================================

    @Test
    @DisplayName("mode=cluster + node_addr_list 有值(但 cluster_node_list 空) → cluster（mode 优先于哨兵非空判断）")
    void modeCluster_butSentinelNodesFilled_shouldRouteCluster() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("cluster");
        cfg.setNodeAddrList("127.0.0.1:26379");
        cfg.setSentinelPorts("26379");
        cfg.setTargetPorts("6379");

        assertEquals("cluster", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=sentinel + cluster_node_list 有值 → sentinel（mode 优先于集群非空判断）")
    void modeSentinel_butClusterNodesFilled_shouldRouteSentinel() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("sentinel");
        cfg.setClusterNodeList("127.0.0.1:7001");
        cfg.setSentinelPorts("26379");
        cfg.setTargetPorts("6379");

        assertEquals("sentinel", resolveActualMode(cfg));
    }

    // ====================================================================
    // 六、mode 大小写不敏感
    // ====================================================================

    @Test
    @DisplayName("mode=CLUSTER（大写）→ cluster")
    void modeCluster_uppercase_shouldRouteCluster() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("CLUSTER");

        assertEquals("cluster", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=Sentinel（混合大小写）→ sentinel")
    void modeSentinel_mixedCase_shouldRouteSentinel() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("Sentinel");
        cfg.setSentinelPorts("26379");
        cfg.setTargetPorts("6379");

        assertEquals("sentinel", resolveActualMode(cfg));
    }

    // ====================================================================
    // 七、mode 为空/null（未配置），靠节点列表非空判断（旧逻辑兼容）
    // ====================================================================

    @Test
    @DisplayName("mode=null + cluster_node_list 有值 → cluster（旧逻辑兼容）")
    void modeNull_withClusterNodes_shouldRouteCluster() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode(null);
        cfg.setClusterNodeList("127.0.0.1:7001");

        assertEquals("cluster", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=null + node_addr_list 有值 → sentinel（旧逻辑兼容）")
    void modeNull_withSentinelNodes_shouldRouteSentinel() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode(null);
        cfg.setNodeAddrList("127.0.0.1:26379");
        cfg.setSentinelPorts("26379");
        cfg.setTargetPorts("6379");

        assertEquals("sentinel", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=null + 无任何节点列表 → single（旧逻辑兼容）")
    void modeNull_noNodes_shouldRouteSingle() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode(null);

        assertEquals("single", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=空字符串 + cluster_node_list 有值 → cluster（空字符串等同于未设置）")
    void modeEmpty_withClusterNodes_shouldRouteCluster() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("");
        cfg.setClusterNodeList("127.0.0.1:7001");

        assertEquals("cluster", resolveActualMode(cfg));
    }

    @Test
    @DisplayName("mode=空字符串 + 无节点列表 → single（空字符串等同于未设置）")
    void modeEmpty_noNodes_shouldRouteSingle() {
        RedisClientConfig cfg = newConfig();
        cfg.setRedisMode("");

        assertEquals("single", resolveActualMode(cfg));
    }
}
