package cn.xbhel.function;

import java.io.IOException;
import java.io.Serializable;

import javax.annotation.Nullable;

public interface HttpRetryStrategy extends Serializable {

    boolean isRetryable(
            int attempts,
            @Nullable Integer statusCode,
            @Nullable String resonseErrorMessage,
            @Nullable IOException exception);

    long getBackoffTimeMills(int attempts);

    default void failed(
            HttpRequest request,
            @Nullable Integer statusCode,
            @Nullable String resonseErrorMessage,
            @Nullable IOException exception) {
        throw new IllegalStateException(String.format(
                "Failed to request %s with statusCode: %d, errorMessage: %s.",
                request, statusCode, resonseErrorMessage), exception);
    }

}
