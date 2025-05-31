package cn.xbhel.http;

import org.apache.http.protocol.HttpContext;

/**
 * A retry strategy implementation that never retries failed requests.
 * This is useful when you want to disable retries completely and have requests fail fast.
 * 
 * <p>This strategy will:
 * <ul>
 *   <li>Always return false for {@link #isRetryable}, preventing any retries
 *   <li>Return 0 for {@link #getBackoffTimeMillis}, since no retries are performed
 * </ul>
 * 
 * <p>Use the {@link #INSTANCE} singleton to get a shared instance.
 * 
 * @author xbhel
 */
public class NoHttpRetryStrategy implements HttpRetryStrategy {

    public static final HttpRetryStrategy INSTANCE = new NoHttpRetryStrategy();

    @Override
    public boolean isRetryable(int attempts, Integer statusCode, Exception exception, HttpContext context) {
        return false;
    }

    @Override
    public long getBackoffTimeMillis(int attempts) {
        return 0;
    }

}
