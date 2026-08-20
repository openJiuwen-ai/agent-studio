/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

import java.util.Calendar;
import java.util.TimeZone;

public class SAMLUtilTest {

    @Test
    public void testToDate_ValidInput() {
        String input = "2023-10-10T12:34:56Z";
        Calendar expected = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
        expected.set(2023, Calendar.OCTOBER, 10, 12, 34, 56);
        expected.set(Calendar.MILLISECOND, 0);

        Calendar actual = SAMLUtil.toDate(input);

        assertEquals(expected.get(Calendar.YEAR), actual.get(Calendar.YEAR));
        assertEquals(expected.get(Calendar.MONTH), actual.get(Calendar.MONTH));
        assertEquals(expected.get(Calendar.DAY_OF_MONTH), actual.get(Calendar.DAY_OF_MONTH));
        assertEquals(expected.get(Calendar.MINUTE), actual.get(Calendar.MINUTE));
        assertEquals(expected.get(Calendar.SECOND), actual.get(Calendar.SECOND));
    }

    @Test
    public void testToDate_InvalidInput() {
        String input = "invalid-date";
        assertThrows(StringIndexOutOfBoundsException.class, () -> SAMLUtil.toDate(input));
    }
}
