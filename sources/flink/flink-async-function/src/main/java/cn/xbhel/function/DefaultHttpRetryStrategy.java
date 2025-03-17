package cn.xbhel.function;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.net.ConnectException;
import java.net.UnknownHostException;
import java.util.Set;

import javax.annotation.Nullable;
import javax.net.ssl.SSLException;

import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
public class DefaultHttpRetryStrategy implements HttpRetryStrategy {

    private final int maxAttempts;
    private final double backoffFactor;
    private final Set<Integer> retryableStatusCodes;
    private final Set<Class<? extends IOException>> noRetryableExceptions;

    public DefaultHttpRetryStrategy() {
        this.maxAttempts = 3;
        this.backoffFactor = 0.5d;
        this.retryableStatusCodes = Set.of(429, 502, 504, 503, 500);
        this.noRetryableExceptions = Set.of(
                InterruptedIOException.class,
                UnknownHostException.class,
                ConnectException.class,
                SSLException.class);

    }

    @Override
    public boolean isRetryable(int attempts, @Nullable Integer statusCode,
            @Nullable String resonseErrorMessage, @Nullable IOException exception) {
        var retryable = false;
        if (attempts <= maxAttempts) {
            if (statusCode != null) {
                retryable |= retryableStatusCodes.contains(statusCode);
            }
            if (exception != null) {
                retryable |= noRetryableExceptions.stream().noneMatch(cls -> cls.isInstance(exception));
            }
        }
        return retryable;
    }

    @Override
    public long getBackoffTimeMills(int attempts) {
        return (long) (backoffFactor * Math.pow(2, attempts) * 1000);
    }

}
