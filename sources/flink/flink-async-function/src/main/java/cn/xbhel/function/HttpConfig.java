package cn.xbhel.function;

import java.io.Serial;
import java.io.Serializable;

import lombok.Data;
import lombok.experimental.Accessors;

@Data
@Accessors(chain = true)
public class HttpConfig implements Serializable {

    @Serial
    private static final long serialVersionUID = 526912735513806969L;

    private long connectTimeoutMs;
    private long socketTimeoutMs;
    private long connectionRequestTimeoutMs;

    private int maxTotal;
    private int maxTotalPerRoute;
    private long maxIdleTimeMs;
    private long connectionTtlTimeMs;
    private long validateAfterInactivityMs;

    public HttpConfig() {
        this.connectTimeoutMs = 60000L;
        this.socketTimeoutMs = 60000L;
        this.connectionRequestTimeoutMs = 60000L;
        this.maxTotal = 10;
        this.maxTotalPerRoute = 10;
        this.maxIdleTimeMs = -1L;
        this.connectionTtlTimeMs = -1L;
        this.validateAfterInactivityMs = 2000L;
    }
    
}
