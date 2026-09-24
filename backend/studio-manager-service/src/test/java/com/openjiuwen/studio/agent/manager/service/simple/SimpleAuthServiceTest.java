package com.openjiuwen.studio.agent.manager.service.simple;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.simple.SimpleAuthUtils;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class SimpleAuthServiceTest {

    @InjectMocks
    private SimpleAuthService simpleAuthService;

    @Test
    void testValidateToken_Success() {
        SimpleUser user = new SimpleUser();
        user.setUserId("test-user");
        user.setToken("test-token");

        try (MockedStatic<SimpleAuthUtils> authUtilsMock = mockStatic(SimpleAuthUtils.class)) {
            authUtilsMock.when(() -> SimpleAuthUtils.tokenToUser("test-token")).thenReturn(user);

            ResponseEntity<SimpleUser> result = simpleAuthService.validateToken("test-token");

            assertEquals(200, result.getStatusCode().value());
            assertEquals(user, result.getBody());
            assertEquals("test-token", result.getHeaders().getFirst("X-Subject-Token"));
        }
    }

    @Test
    void testValidateToken_NullUser() {
        try (MockedStatic<SimpleAuthUtils> authUtilsMock = mockStatic(SimpleAuthUtils.class)) {
            authUtilsMock.when(() -> SimpleAuthUtils.tokenToUser("invalid-token")).thenReturn(null);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> simpleAuthService.validateToken("invalid-token"));
            assertEquals(StudioError.POC_AUTH_FAILED, ex.getErrorCode());
        }
    }

    @Test
    void testValidateToken_AuthUtilsThrowsException() {
        try (MockedStatic<SimpleAuthUtils> authUtilsMock = mockStatic(SimpleAuthUtils.class)) {
            authUtilsMock.when(() -> SimpleAuthUtils.tokenToUser("bad-token"))
                .thenThrow(new AgentStudioException(StudioError.POC_AUTH_FAILED));

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> simpleAuthService.validateToken("bad-token"));
            assertEquals(StudioError.POC_AUTH_FAILED, ex.getErrorCode());
        }
    }
}
