package cn.xbhel.http;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.net.ConnectException;
import java.net.UnknownHostException;
import java.util.Set;

import javax.annotation.Nullable;
import javax.net.ssl.SSLException;

import org.apache.http.protocol.HttpContext;

import lombok.RequiredArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

/**
 * @author xbhel
 */
@Setter
@Accessors(chain = true)
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
    private static final Set<Class<? extends Throwable>> DEFAULT_NO_RETRYABLE_IO_EXCEPTIONS = Set.of(
            InterruptedIOException.class,
            UnknownHostException.class,
            ConnectException.class,
            SSLException.class);
    private static final Set<Class<? extends Throwable>> DEFAULT_RETRYABLE_EXCEPTIONS = Set.of(
            IOException.class);
     
    public static final DefaultHttpRetryStrategy INSTANCE = new DefaultHttpRetryStrategy();

    private final int maxAttempts;
    private final double backoffFactor;

    /**
     * <p>
     * The flag to determine whether to fail when the maximum number of retries is
     * exhausted. If it is set to true, the failed will be thrown due to unexpected
     * HTTP status codes when the max attempts is reached.
     * </p>
     * <b>Note:</b> Exceptions thrown during HTTP request execution are never
     * hidden.
     * The failedAtRetriesExhausted flag only affects failures due to
     * unexpected HTTP status codes.
     */
    private boolean failedIfRetriesExhausted = false;
    private Set<Integer> retryableStatusCodes = DEFAULT_RETRYABLE_STATUS_CODES;
    private Set<Class<? extends Throwable>> retryableExceptions = DEFAULT_RETRYABLE_EXCEPTIONS;
    private Set<Class<? extends Throwable>> nonRetryableExceptions = DEFAULT_NO_RETRYABLE_IO_EXCEPTIONS;

    public DefaultHttpRetryStrategy() {
        this(DEFAULT_MAX_ATTEMPTS, DEFAULT_BACKOFF_FACTOR);
    }

    @Override
    public long getBackoffTimeMillis(int attempts) {
        return (long) (backoffFactor * Math.pow(2, attempts) * 1000);
    }

    @Override
    public boolean isRetryable(int attempts, @Nullable Integer statusCode, @Nullable Exception exception, HttpContext context) {
        if (attempts > maxAttempts) {
            return false;
        }

        if (exception != null) {
            var isNonRetryableEx = nonRetryableExceptions.stream().anyMatch(cls -> cls.isInstance(exception));

            if (isNonRetryableEx) {
                return false;
            }

            return retryableExceptions.stream().anyMatch(cls -> cls.isInstance(exception));
        }

        if (statusCode != null) {
            return retryableStatusCodes.contains(statusCode);
        }
        return false;
    }

    @Override
    public void failed(HttpRequest request, @Nullable Integer statusCode, @Nullable Exception exception,
            HttpContext context) throws Exception {
        HttpRetryStrategy.super.failed(request, statusCode, exception, context);
        if (failedIfRetriesExhausted && statusCode != null) {
            var errorMessage = context.getAttribute(HttpUtils.ERROR_MESSAGE_ATTRIBUTE);
            throw new HttpExecutionException(String.format(
                    "Failed to execute request [%s] due to unexpected http status code %s, error: %s",
                    request, statusCode, errorMessage));
        }
    }

}
