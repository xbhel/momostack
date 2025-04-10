package cn.xbhel.http;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.util.Set;

import org.apache.http.client.protocol.HttpClientContext;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class DefaultHttpRetryStrategyTest {

    @ParameterizedTest
    @CsvSource({
            "1, 500, true",
            "1, 400, false",
            "1, 200, false",
            "1, 429, true",
    })
    void testIsRetryable_withinLimitAndRetryableStatusCode(int attempts, int statusCode, boolean expected) {
        var retryStrategy = new DefaultHttpRetryStrategy();
        var retryable = retryStrategy.isRetryable(attempts, statusCode, null, HttpClientContext.create());
        Assertions.assertEquals(expected, retryable);
    }

    @Test
    void testIsRetryable_withinLimitAndNonRetryableStatusCode() {
        var retryStrategy = new DefaultHttpRetryStrategy();
        var retryable = retryStrategy.isRetryable(1, 300, null, HttpClientContext.create());
        Assertions.assertFalse(retryable);
    }

    @Test
    void testIsRetryable_withinLimitAndRetryableException() {
        var retryStrategy = new DefaultHttpRetryStrategy();
        var retryable = retryStrategy.isRetryable(1, null, new IOException(), HttpClientContext.create());
        Assertions.assertTrue(retryable);
    }

    @Test
    void testIsRetryable_withinLimitAndNonRetryableException() {
        var retryStrategy = new DefaultHttpRetryStrategy();
        var retryable = retryStrategy.isRetryable(1, null, new InterruptedIOException(), HttpClientContext.create());
        Assertions.assertFalse(retryable);
    }

    @Test
    void testIsRetryable_exceedsLimit() {
        var retryStrategy = new DefaultHttpRetryStrategy();
        var retryable = retryStrategy.isRetryable(4, 500, null, HttpClientContext.create());
        Assertions.assertFalse(retryable);
    }

    @Test
    void testIsRetryable_withCustomStatusCodes() {
        var retryStrategy = new DefaultHttpRetryStrategy(3, 0.1);
        retryStrategy.setRetryableStatusCodes(Set.of(9999));
        var retryable9999 = retryStrategy.isRetryable(1, 9999, null, HttpClientContext.create());
        var retryable500 = retryStrategy.isRetryable(1, 500, null, HttpClientContext.create());
        Assertions.assertTrue(retryable9999);
        Assertions.assertFalse(retryable500);
    }

    @Test
    void testIsRetryable_withCustomExceptions() {
        var retryStrategy = new DefaultHttpRetryStrategy(3, 0.1);
        retryStrategy.setRetryableExceptions(Set.of(RuntimeException.class));
        var retryableRuntimeEx = retryStrategy.isRetryable(1, null, new RuntimeException(), HttpClientContext.create());
        var retryableIOEx = retryStrategy.isRetryable(1, null, new IOException(), HttpClientContext.create());
        Assertions.assertTrue(retryableRuntimeEx);
        Assertions.assertFalse(retryableIOEx);
    }

    @Test
    void testGetBackoffTimeMillis() {
        var retryStrategy = new DefaultHttpRetryStrategy();
        Assertions.assertEquals(1000, retryStrategy.getBackoffTimeMillis(1));
        Assertions.assertEquals(2000, retryStrategy.getBackoffTimeMillis(2));
        Assertions.assertEquals(4000, retryStrategy.getBackoffTimeMillis(3));
    }

    @Test
    void testFailed_withException() {
        var request = new HttpRequest("http://test.com", "GET");
        var retryStrategy = new DefaultHttpRetryStrategy();
        Assertions.assertThrows(IOException.class,
                () -> retryStrategy.failed(request, null, new IOException(), HttpClientContext.create()));
    }

    @Test
    void testFailed_DefaultSilentWithStatusCode() {
        var request = new HttpRequest("http://test.com", "GET");
        var retryStrategy = new DefaultHttpRetryStrategy();

        Assertions.assertDoesNotThrow(() -> retryStrategy.failed(request, 500, null, HttpClientContext.create()));
    }

    @Test
    void testFailed_ErrorWithUnexpectedStatusCode() {
        var request = new HttpRequest("http://test.com", "GET");
        var retryStrategy = new DefaultHttpRetryStrategy()
                .setFailedAtRetriesExhausted(true);
        Assertions.assertThrows(HttpExecutionException.class,
                () -> retryStrategy.failed(request, 500, null, HttpClientContext.create()));
    }

    @Test
    void testFailed_ErrorWithUnexpectedStatusCodeAndMessage() {
        var request = new HttpRequest("http://test.com", "GET");
        var retryStrategy = new DefaultHttpRetryStrategy()
                .setFailedAtRetriesExhausted(true);
        var context = HttpClientContext.create();
        context.setAttribute(HttpUtils.ERROR_MESSAGE_ATTRIBUTE, "internal server error");

        assertThatThrownBy(() -> retryStrategy.failed(request, 500, null, context))
                .isInstanceOf(HttpExecutionException.class)
                .hasMessage(String.format(
                        "Failed to execute request [%s] due to unexpected http status code %s, error: %s",
                        request, 500, "internal server error"));
    }

    @Test
    void testInitialize_withCustomMaxAttemptsAndFactor() {
        var retryStrategy = new DefaultHttpRetryStrategy(3, 0.1);
        Assertions.assertEquals(200, retryStrategy.getBackoffTimeMillis(1));
        Assertions.assertEquals(400, retryStrategy.getBackoffTimeMillis(2));
        Assertions.assertEquals(800, retryStrategy.getBackoffTimeMillis(3));
    }

}
