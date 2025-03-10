package cn.xbhel.function;

import lombok.Getter;

@Getter
public class RetryableException extends RuntimeException {

    private final int statusCode;

    public RetryableException(int statusCode, String message) {
        this(statusCode, message, null);
    }

    public RetryableException(int statusCode, String message, Throwable ex) {
        super(statusCode + "|" + message, ex);
        this.statusCode = statusCode;
    }

}
