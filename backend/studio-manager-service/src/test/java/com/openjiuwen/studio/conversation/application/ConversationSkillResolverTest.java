package com.openjiuwen.studio.conversation.application;

import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillContext;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillVo;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Arrays;
import java.util.stream.IntStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ConversationSkillResolverTest {

    private final SkillMapper skillMapper = mock(SkillMapper.class);
    private final ConversationSkillResolver resolver = new ConversationSkillResolver(skillMapper);

    @Test
    void listAvailable_只返回当前边界内可执行目录项() {
        when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0)))
            .thenReturn(List.of(
                skill("s1", "d1", "p1", "w1", "developed", "v1", "u1/skills/s1/v1/a.zip"),
                skill("s2", "d1", "p1", "w1", "developing", "v2", "u1/skills/s2/v2/b.zip"),
                skill("s3", "d1", "p1", "w1", "developed", "v3", ""),
                skill("s4", "d2", "p1", "w1", "developed", "v4", "u1/skills/s4/v4/a.zip"),
                skill("s5", "d1", "p2", "w1", "developed", "v5", "u1/skills/s5/v5/a.zip"),
                skill("s6", "d1", "p1", "w2", "developed", "v6", "u1/skills/s6/v6/a.zip"),
                skill("s7", "d1", "p1", "w1", "developed", "", "u1/skills/s7/v7/a.zip"),
                skill("s8", "d1", "p1", "w1", "developed", " ", "u1/skills/s8/v8/a.zip")));

        List<ConversationSkillVo> result = resolver.listAvailable("p1", "w1", "d1");
        ConversationSkillContext context = resolver.resolveForRun("p1", "w1", "d1", List.of("s1"));

        assertEquals(List.of("s1"), result.stream().map(ConversationSkillVo::getSkillId).toList());
        assertEquals(List.of("s1"), context.getCatalog().stream().map(item -> item.getSkillId()).toList());
        assertEquals(List.of("s1"), context.getRecommendedSkillIds());
        org.mockito.ArgumentCaptor<SkillEntity> condition = org.mockito.ArgumentCaptor.forClass(SkillEntity.class);
        verify(skillMapper, times(2)).search(condition.capture(), eq(0), eq(1000), isNull(), isNull(), eq(0));
        assertEquals("p1", condition.getValue().getProjectId());
        assertEquals("w1", condition.getValue().getWorkspaceId());
        assertEquals("d1", condition.getValue().getDomainId());
        assertEquals("developed", condition.getValue().getStatus());
    }

    @Test
    void listAvailable_达到页大小时继续读取下一页() {
        List<SkillDetails> firstPage = IntStream.range(0, 1000)
            .mapToObj(i -> skill("s" + i, "d1", "p1", "w1", "developed", "v" + i,
                "u1/skills/s" + i + "/v" + i + "/a.zip"))
            .toList();
        when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0))).thenReturn(firstPage);
        when(skillMapper.search(any(), eq(1000), eq(1000), isNull(), isNull(), eq(0))).thenReturn(List.of(
            skill("s1000", "d1", "p1", "w1", "developed", "v1000", "u1/skills/s1000/v1000/a.zip")));

        List<ConversationSkillVo> result = resolver.listAvailable("p1", "w1", "d1");

        assertEquals(1001, result.size());
        assertEquals("s1000", result.get(1000).getSkillId());
        verify(skillMapper).search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0));
        verify(skillMapper).search(any(), eq(1000), eq(1000), isNull(), isNull(), eq(0));
    }

    @Test
    void resolveForRun_仅构建当前边界内的可信目录() {
        when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0)))
            .thenReturn(List.of(
                skill("s1", "d1", "p1", "w1", "developed", "v1", "u1/skills/s1/v1/a.zip"),
                skill("s2", "d1", "p1", "w1", "developing", "v2", "u1/skills/s2/v2/b.zip")));

        ConversationSkillContext result = resolver.resolveForRun("p1", "w1", "d1", List.of("s1"));

        assertEquals(List.of("s1"), result.getCatalog().stream().map(item -> item.getSkillId()).toList());
        assertEquals(List.of("s1"), result.getRecommendedSkillIds());
        assertEquals("v1", result.getCatalog().get(0).getVersionId());
        assertEquals("u1/skills/s1/v1/a.zip", result.getCatalog().get(0).getObjectKey());
    }

    @Test
    void resolveForRun_去重并保留推荐顺序() {
        mockCatalog("s1", "s2");

        ConversationSkillContext context = resolver.resolveForRun("p1", "w1", "d1", List.of("s2", "s1", "s2"));

        assertEquals(List.of("s2", "s1"), context.getRecommendedSkillIds());
    }

    @Test
    void resolveForRun_目录外推荐被拒绝() {
        mockCatalog("s1");

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> resolver.resolveForRun("p1", "w1", "d1", List.of("other")));

        assertEquals(StudioError.METHOD_ARGUMENT_NOT_VALID, exception.getErrorCode());
    }

    @Test
    void resolveForRun_无推荐时目录异常降级为空目录() {
        when(skillMapper.search(any(), any(Integer.class), any(Integer.class), any(), any(), any(Integer.class)))
            .thenThrow(new RuntimeException("db unavailable"));

        ConversationSkillContext context = resolver.resolveForRun("p1", "w1", "d1", List.of());

        assertTrue(context.getCatalog().isEmpty());
        assertTrue(context.getRecommendedSkillIds().isEmpty());
    }

    @Test
    void resolveForRun_有推荐时目录异常不得静默执行() {
        when(skillMapper.search(any(), any(Integer.class), any(Integer.class), any(), any(), any(Integer.class)))
            .thenThrow(new RuntimeException("db unavailable"));

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> resolver.resolveForRun("p1", "w1", "d1", List.of("s1")));

        assertEquals(StudioError.METHOD_ARGUMENT_NOT_VALID, exception.getErrorCode());
    }

    private void mockCatalog(String... ids) {
        List<SkillDetails> items = Arrays.stream(ids)
            .map(id -> skill(id, "d1", "p1", "w1", "developed", "v-" + id,
                "u1/skills/" + id + "/v-" + id + "/a.zip"))
            .toList();
        when(skillMapper.search(any(), eq(0), eq(1000), isNull(), isNull(), eq(0))).thenReturn(items);
    }

    private SkillDetails skill(String id, String domainId, String projectId, String workspaceId,
                               String status, String versionId, String objectKey) {
        return new SkillDetails().setSkillId(id).setDomainId(domainId).setProjectId(projectId)
            .setWorkspaceId(workspaceId).setStatus(status).setLatestVersion(versionId)
            .setName("skill-" + id).setDescription("description-" + id).setObsPath(objectKey);
    }
}
