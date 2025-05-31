package cn.xbhel.http;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.io.UnsupportedEncodingException;

import static cn.xbhel.http.HttpUtils.*;

import org.apache.http.HttpResponse;
import org.apache.http.entity.StringEntity;
import org.assertj.core.api.Assertions;
import org.junit.jupiter.api.Test;

class HttpUtilsTest {

    @Test
    void testCheckResponseSuccess() {
        var response = mock(HttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(200);
        assertDoesNotThrow(() -> checkResponse(response, 200));
    }

    @Test
    void testCheckResponseFailedWithEmptyErrorMessage() {
        var response = mock(HttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(400);
        when(response.getEntity()).thenReturn(null);
        Assertions.assertThatThrownBy(() -> checkResponse(response, 200))
        .isInstanceOf(IOException.class)
        .hasMessage("Unexpected status code: 400, error message: ");
    }

    @Test
    void testCheckResponseFailedWithErrorMessage() throws UnsupportedEncodingException {
        var response = mock(HttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(400);
        when(response.getEntity()).thenReturn(new StringEntity("EOF exception"));
        Assertions.assertThatThrownBy(() -> checkResponse(response, 200))
        .isInstanceOf(IOException.class)
        .hasMessage("Unexpected status code: 400, error message: EOF exception");
    }
}
