package cn.xbhel.http;

import org.apache.http.client.protocol.HttpClientContext;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

class NoHttpRetryStrategyTest {

    @Test
    void testIsRetryable_alwaysFalse() {
        var retryStrategy = new NoHttpRetryStrategy();
        var retryable = retryStrategy.isRetryable(1, 200, null, HttpClientContext.create());
        Assertions.assertFalse(retryable);
    }

    @Test
    void testGetBackoffTimeMillis_alwaysZero() {
        var retryStrategy = new NoHttpRetryStrategy();
        var backoffTime = retryStrategy.getBackoffTimeMillis(1);
        Assertions.assertEquals(0, backoffTime);
    }
}
