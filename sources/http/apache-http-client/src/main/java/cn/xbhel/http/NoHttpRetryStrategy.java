package cn.xbhel.http;

import org.apache.http.protocol.HttpContext;

/**
 * @author xbhel
 */
public class NoHttpRetryStrategy implements HttpRetryStrategy {

    @Override
    public boolean isRetryable(int attempts, Integer statusCode, Exception exception, HttpContext context) {
        return false;
    }

    @Override
    public long getBackoffTimeMillis(int attempts) {
        return 0;
    }

}
