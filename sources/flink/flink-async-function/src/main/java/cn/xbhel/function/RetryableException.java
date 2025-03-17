package cn.xbhel.function;

public class RetryableException extends RuntimeException {

    public RetryableException(String message, Throwable ex) {
        super(message, ex);
    }

}
