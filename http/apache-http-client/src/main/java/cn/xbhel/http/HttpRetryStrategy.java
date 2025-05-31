package cn.xbhel.http;

import javax.annotation.Nullable;

import org.apache.http.protocol.HttpContext;

/**
 * @author xbhel
 */
public interface HttpRetryStrategy {

    /**
     * Determines if a request should be retried based on the current state.
     * Note: The http request object is not passed here, avoid it being modified.
     *
     * @param attempts Number of attempts made so far
     * @param statusCode HTTP status code from the response, may be null
     * @param exception Exception that occurred during the request, may be null  
     * @param context HTTP context containing request state
     * @return true if the request should be retried, false otherwise
     */
    boolean isRetryable(
            int attempts,
            Integer statusCode, 
            Exception exception,
            HttpContext context);

    /**
     * Calculates the backoff time to wait before the next retry attempt.
     *
     * @param attempts Number of attempts made so far
     * @return Time to wait in milliseconds before next retry
     */
    long getBackoffTimeMillis(int attempts);

    /**
     * Called when a request fails to handle any cleanup or logging.
     * By default, re-throws any exception that occurred.
     *
     * @param request The failed HTTP request
     * @param statusCode HTTP status code from the response, may be null
     * @param exception Exception that occurred during the request, may be null
     * @param context HTTP context containing request state
     * @throws Exception if an error occurs during failure handling
     */
    default void failed(
            HttpRequest request,
            @Nullable Integer statusCode,
            @Nullable Exception exception, 
            HttpContext context) throws Exception {
        if (exception != null) {
            throw exception;
        }
    }

}
