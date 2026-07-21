/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.repository;

import com.openjiuwen.studio.agent.manager.entity.Session;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.Optional;

/**
 * 会话数据访问层
 */
@Repository
public interface SessionRepository extends JpaRepository<Session, Long> {

    Optional<Session> findBySessionId(String sessionId);

    @Modifying
    @Query("UPDATE Session s SET s.lastActivityTime = :activityTime WHERE s.sessionId = :sessionId")
    int updateLastActivity(@Param("sessionId") String sessionId, @Param("activityTime") LocalDateTime activityTime);

    @Modifying
    @Query("UPDATE Session s SET s.status = 'EXPIRED' WHERE s.expireTime < :currentTime AND s.status = 'ACTIVE'")
    int expireSessions(@Param("currentTime") LocalDateTime currentTime);

    @Modifying
    @Query(value = "DELETE FROM t_sessions WHERE login_time < :retentionTime", nativeQuery = true)
    int deleteOldSessions(@Param("retentionTime") LocalDateTime retentionTime);

}
