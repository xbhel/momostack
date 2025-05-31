package cn.xbhel.http;

import java.nio.charset.Charset;
import java.util.Map;

import lombok.Data;
import lombok.RequiredArgsConstructor;

import javax.annotation.Nonnull;

/**
 * @author xbhel
 */
@Data
@RequiredArgsConstructor
public class HttpRequest {

    @Nonnull
    private final String url;
    @Nonnull
    private final String method;
    private Map<String, String> headers;
    private Map<String, String> queryParams;
    private Object data;
    private Charset charset;

    @Override
    public String toString() {
        return "HttpRequest [url=" + url + ", method=" + method + "]";
    }
}