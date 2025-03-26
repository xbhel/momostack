package cn.xbhel.http;

/**
 * @author xbhel
 */
public class HttpExecutionException extends RuntimeException {
    
    public HttpExecutionException(String message) {
        super(message);
    }

    public HttpExecutionException(String message, Throwable cause) {
        super(message, cause);
    }

    public HttpExecutionException(Throwable cause) {
        super(cause);
    }

}
