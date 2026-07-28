/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.impl;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;

import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.netty.channel.ReflectiveChannelFactory;
import io.netty.resolver.dns.DefaultDnsCache;
import io.netty.resolver.dns.DefaultDnsCnameCache;
import io.netty.resolver.dns.DnsAddressResolverGroup;
import io.netty.resolver.dns.DnsNameResolverBuilder;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.redisson.Redisson;
import org.redisson.api.HostPortNatMapper;
import org.redisson.api.RAtomicLong;
import org.redisson.api.RBucket;
import org.redisson.api.RLock;
import org.redisson.api.RScoredSortedSet;
import org.redisson.api.RedissonClient;
import org.redisson.api.options.CommonOptions;
import org.redisson.client.codec.Codec;
import org.redisson.client.codec.StringCodec;
import org.redisson.codec.JsonJacksonCodec;
import org.redisson.config.ClusterServersConfig;
import org.redisson.config.Config;
import org.redisson.config.ReadMode;
import org.redisson.config.SentinelServersConfig;
import org.redisson.config.SingleServerConfig;
import org.redisson.config.SubscriptionMode;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
public class RedisClientRedisson implements RedisClient {
    private static final String REDIS_PREFIX = "redis://";

    private static final String REDISSON_PREFIX = "redisson://";

    private static final String SYMBOL_CONCAT = ":";

    private static final String SYMBOL_SPLIT = ",";

    private final RedissonClient redissonClient;

    public RedisClientRedisson(RedisClientConfig redisClientConfig) {
        Config config = new Config();
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.getFactory().setStreamReadConstraints(
            StreamReadConstraints.builder().maxStringLength(redisClientConfig.getJsonMaxStringLength()).build());
        config.setCodec(new JsonJacksonCodec(objectMapper));
        // 禁用 DNS 解析
        config.setAddressResolverGroupFactory((dataChannel, socketChannel, provider) -> {
            DnsNameResolverBuilder dnsResolverBuilder = new DnsNameResolverBuilder();
            dnsResolverBuilder.nameServerProvider(provider)
                .resolveCache(new DefaultDnsCache())
                .datagramChannelFactory(new ReflectiveChannelFactory<>(dataChannel))
                .cnameCache(new DefaultDnsCnameCache());
            dnsResolverBuilder.localAddress(null);
            return new DnsAddressResolverGroup(dnsResolverBuilder);
        });

        if (StringUtils.isNotBlank(redisClientConfig.getClusterNodeList())) {
            initClusterServer(config, redisClientConfig);
        } else if (StringUtils.isNotBlank(redisClientConfig.getNodeAddrList())) {
            initSentinelServer(config, redisClientConfig);
        } else {
            initSingleServer(config, redisClientConfig);
        }

        redissonClient = Redisson.create(config);
    }

    private void initSingleServer(Config config, RedisClientConfig redisClientConfig) {
        log.info("Init SingleServer redissonClient, host: {}, port: {}", redisClientConfig.getRedisHost(),
            redisClientConfig.getRedisPort());

        SingleServerConfig singleConfig = config.useSingleServer();
        singleConfig.setAddress(
            REDIS_PREFIX + redisClientConfig.getRedisHost() + SYMBOL_CONCAT + redisClientConfig.getRedisPort());
        if (StringUtils.isNotBlank(redisClientConfig.getRedisPassword())) {
            singleConfig.setPassword(redisClientConfig.getRedisPassword());
        }
        singleConfig.setConnectionMinimumIdleSize(redisClientConfig.getConnectionMinimumIdleSize());
        singleConfig.setConnectionPoolSize(redisClientConfig.getConnectionPoolSize());
    }

    private void initSentinelServer(Config config, RedisClientConfig redisClientConfig) {
        log.info("Init SentinelServers client, addr list: {}", redisClientConfig.getNodeAddrList());

        // 设置网络映射：redis节点 -> itep
        SentinelServersConfig sentinelServersConfig = config.useSentinelServers();
        HostPortNatMapper hostPortNatMapper = new HostPortNatMapper();
        Map<String, String> natMapperMap = new HashMap<>();
        String[] redisNodeAddrArray = redisClientConfig.getNodeAddrList().split(SYMBOL_SPLIT);
        String[] redisNodePorts = redisClientConfig.getTargetPorts().split(SYMBOL_SPLIT);
        for (int i = 0; i < redisNodeAddrArray.length && i < redisNodePorts.length; i++) {
            natMapperMap.put(redisNodeAddrArray[i],
                redisClientConfig.getRedisHost() + SYMBOL_CONCAT + redisNodePorts[i]);
            String[] sentiPorts = redisClientConfig.getSentinelPorts().split(SYMBOL_SPLIT);
            for (String port : sentiPorts) {
                String[] parts = redisNodeAddrArray[i].split(SYMBOL_CONCAT);
                if (parts.length > 0) {
                    natMapperMap.put(parts[0] + SYMBOL_CONCAT + port,
                        redisClientConfig.getRedisHost() + SYMBOL_CONCAT + port);
                }
            }
        }
        hostPortNatMapper.setHostsPortMap(natMapperMap);
        sentinelServersConfig.setNatMapper(hostPortNatMapper);

        // 设置哨兵节点
        List<String> redisSentinelAddrList = new ArrayList<>();
        String[] sentiPorts = redisClientConfig.getSentinelPorts().split(SYMBOL_SPLIT);
        for (String port : sentiPorts) {
            redisSentinelAddrList.add(redisClientConfig.getRedisHost() + SYMBOL_CONCAT + port);
        }
        sentinelServersConfig.setCheckSentinelsList(false).setMasterName(redisClientConfig.getMasterName())
            // apikey 功能依赖从主节点读取
            .setReadMode(ReadMode.MASTER).setSentinelAddresses(redisSentinelAddrList.stream().map(url -> {
                if (url.startsWith(REDIS_PREFIX) || url.startsWith(REDISSON_PREFIX)) {
                    return url;
                }
                return REDIS_PREFIX + url;
            }).collect(Collectors.toList()));
        if (StringUtils.isNotBlank(redisClientConfig.getRedisPassword())) {
            sentinelServersConfig.setPassword(redisClientConfig.getRedisPassword());
        }

        sentinelServersConfig.setMasterConnectionPoolSize(redisClientConfig.getConnectionPoolSize());
        sentinelServersConfig.setMasterConnectionMinimumIdleSize(redisClientConfig.getConnectionMinimumIdleSize());
    }

    private void initClusterServer(Config config, RedisClientConfig redisClientConfig) {
        log.info("Init ClusterServer redissonClient, node list: {}", redisClientConfig.getClusterNodeList());
        ClusterServersConfig clusterServersConfig = config.useClusterServers();

        List<String> nodesList = new ArrayList<>();
        String[] nodes = redisClientConfig.getClusterNodeList().split(SYMBOL_SPLIT);
        for (String addr : nodes) {
            nodesList.add(REDIS_PREFIX + addr);
        }
        clusterServersConfig.setNodeAddresses(nodesList);

        if (StringUtils.isNotBlank(redisClientConfig.getRedisPassword())) {
            clusterServersConfig.setPassword(redisClientConfig.getRedisPassword());
        }

        clusterServersConfig.setMasterConnectionPoolSize(redisClientConfig.getConnectionPoolSize());
        clusterServersConfig.setMasterConnectionMinimumIdleSize(redisClientConfig.getConnectionMinimumIdleSize());

        // apikey 功能依赖从主节点读取
        clusterServersConfig.setReadMode(ReadMode.MASTER);
        clusterServersConfig.setSubscriptionMode(SubscriptionMode.MASTER);
    }

    @Override
    public boolean exists(String key) {
        return redissonClient.getBucket(key).isExists();
    }

    @Override
    public String get(String key) {
        RBucket<String> bucket = redissonClient.getBucket(key);
        return bucket.get();
    }

    @Override
    public String get(String key, Codec codec) {
        RBucket<String> bucket = redissonClient.getBucket(key, codec);
        return bucket.get();
    }

    @Override
    public void set(String key, String value, Duration duration) {
        redissonClient.getBucket(key).set(value, duration);
    }

    @Override
    public void set(String key, String value) {
        redissonClient.getBucket(key).set(value);
    }

    @Override
    public void setObj(String key, Object value) {
        RBucket<Object> bucket = redissonClient.getBucket(key, StringCodec.INSTANCE);
        bucket.set(value);
    }

    @Override
    public boolean expire(String key, Duration duration) {
        return redissonClient.getBucket(key).expire(duration);
    }

    @Override
    public boolean delete(String key) {
        return redissonClient.getBucket(key).delete();
    }

    @Override
    public void scoredSortedSet(String key, Long timeStamp, String str) {
        // 根据set中的元素判断，如果是新元素则添加，如果是相同元素则更新
        RScoredSortedSet<String> sortedSet = redissonClient.getScoredSortedSet(key);
        sortedSet.add(timeStamp, str);
    }

    @Override
    public List<String> scoredSortedGet(String key, Long startTime, Long endTime) {
        // 查询set中指定时间范围内的元素
        RScoredSortedSet<String> sortedSet = redissonClient.getScoredSortedSet(key);
        Collection<String> inRangeList = sortedSet.valueRange(startTime, true, endTime, true);
        return inRangeList.stream().toList();
    }

    @Override
    public void scoredSortedRemoveList(String key, Long startTime, Long endTime) {
        // 删除set中指定时间范围内的元素
        RScoredSortedSet<String> sortedSet = redissonClient.getScoredSortedSet(key);
        sortedSet.removeRangeByScore(startTime, true, endTime, true);
    }

    @Override
    public void scoredSortedRemove(String key, String str) {
        // 删除set中指定元素
        RScoredSortedSet<String> sortedSet = redissonClient.getScoredSortedSet(key);
        sortedSet.remove(str);
    }

    @Override
    public Map<String, Object> getAll(List<String> keyList) {
        return redissonClient.getBuckets().get(keyList.toArray(new String[0]));
    }

    @Override
    public RedisLock getLock(String key) {
        RLock lock = redissonClient.getLock(key);
        return new RedisLockRedisson(lock);
    }

    private record RedisLockRedisson(RLock lock) implements RedisLock {
        @Override
        public boolean tryLock(Duration maxWait) throws Exception {
            if (lock == null) {
                return false;
            }
            return lock.tryLock(maxWait.toNanos(), TimeUnit.NANOSECONDS);
        }

        @Override
        public void unlock() {
            if (lock != null && lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    @Override
    public long getAndIncrement(String key, long timeoutSeconds) {
        RAtomicLong atomicLong = redissonClient.getAtomicLong(
            CommonOptions.name(key).timeout(Duration.ofSeconds(timeoutSeconds)));

        return atomicLong.getAndIncrement();
    }

    @Override
    public long addAndGet(String key, long dela, long timeoutSeconds) {
        RAtomicLong atomicLong = redissonClient.getAtomicLong(
            CommonOptions.name(key).timeout(Duration.ofSeconds(timeoutSeconds)));
        if (dela == 0) {
            return atomicLong.get();
        }

        return atomicLong.addAndGet(dela);
    }

    @Override
    public void deleteByPrefix(String prefix) {
        redissonClient.getKeys().deleteByPattern(prefix + "*");
    }

    @Override
    public void setAndKeepTtl(String key, String value, Duration initialDuration) {
        RBucket<String> bucket = redissonClient.getBucket(key);
        long remainTtl = bucket.remainTimeToLive();
        if (remainTtl < 0 || remainTtl > initialDuration.toMillis()) {
            bucket.set(value, initialDuration);
        } else {
            bucket.set(value, Duration.ofMillis(remainTtl));
        }
    }
}
