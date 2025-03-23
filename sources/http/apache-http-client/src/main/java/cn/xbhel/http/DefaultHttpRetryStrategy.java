package cn.xbhel.http;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.net.ConnectException;
import java.net.UnknownHostException;
import java.util.Set;

import javax.net.ssl.SSLException;

import org.apache.http.protocol.HttpContext;

import lombok.RequiredArgsConstructor;

/**
 * @author xbhel
 */
@RequiredArgsConstructor
public class DefaultHttpRetryStrategy implements HttpRetryStrategy {

    private static final int DEFAULT_MAX_ATTEMPTS = 3;
    private static final double DEFAULT_BACKOFF_FACTOR = 0.5d;
    private static final Set<Integer> DEFAULT_RETRYABLE_STATUS_CODES = Set.of(
            429, // Too Many Requests
            502, // Bad Gateway
            504, // Gateway Timeout
            503, // Service Unavailable
            500 // Internal Server Error
    );
    private static final Set<Class<? extends Exception>> DEFAULT_NO_RETRYABLE_EXCEPTIONS = Set.of(
            InterruptedIOException.class,
            UnknownHostException.class,
            ConnectException.class,
            SSLException.class);

    public static final DefaultHttpRetryStrategy INSTANCE = new DefaultHttpRetryStrategy();

    private final int maxAttempts;
    private final double backoffFactor;
    private final Set<Integer> retryableStatusCodes;
    private final Set<Class<? extends Exception>> noRetryableExceptions;

    public DefaultHttpRetryStrategy() {
        this(DEFAULT_MAX_ATTEMPTS, DEFAULT_BACKOFF_FACTOR,
                DEFAULT_RETRYABLE_STATUS_CODES, DEFAULT_NO_RETRYABLE_EXCEPTIONS);
    }

    public DefaultHttpRetryStrategy(int maxAttempts, double backoffFactor) {
        this(maxAttempts, backoffFactor, DEFAULT_RETRYABLE_STATUS_CODES, DEFAULT_NO_RETRYABLE_EXCEPTIONS);
    }

    @Override
    public boolean isRetryable(int attempts, Integer statusCode, Exception exception, HttpContext context) {
        var retryable = false;
        if (attempts <= maxAttempts) {
            if (statusCode != null) {
                retryable |= retryableStatusCodes.contains(statusCode);
            }
            if (exception != null) {
                retryable |= exception instanceof IOException
                        && noRetryableExceptions.stream().noneMatch(cls -> cls.isInstance(exception));
            }
        }
        return retryable;
    }

    @Override
    public long getBackoffTimeMillis(int attempts) {
        return (long) (backoffFactor * Math.pow(2, attempts) * 1000);
    }
}
