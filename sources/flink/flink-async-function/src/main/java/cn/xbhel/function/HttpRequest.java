package cn.xbhel.function;

import java.nio.charset.Charset;
import java.util.Map;

import lombok.Data;
import lombok.NonNull;

@Data
public class HttpRequest {
    @NonNull
    private String url;
    @NonNull
    private String method;
    private Map<String, String> headers;
    private Map<String, String> queryParams;
    private Object data;
    private Charset charset;

    @Override
    public String toString() {
        return "HttpRequest [url=" + url + ", method=" + method + "]";
    }
}
