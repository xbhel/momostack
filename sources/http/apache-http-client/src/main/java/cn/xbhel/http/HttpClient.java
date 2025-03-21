package cn.xbhel.http;

import java.io.Closeable;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;

import cn.xbhel.util.ThreadUtils;
import org.apache.http.HttpEntity;
import org.apache.http.HttpHeaders;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpUriRequest;
import org.apache.http.client.methods.RequestBuilder;
import org.apache.http.client.protocol.HttpClientContext;
import org.apache.http.entity.ByteArrayEntity;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.FileEntity;
import org.apache.http.entity.InputStreamEntity;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.protocol.HttpContext;
import org.apache.http.util.EntityUtils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import lombok.extern.slf4j.Slf4j;

/**

 * A wrapper for Apache HttpClient providing enhanced functionality including:
 * <ol>
 * <li>Automatic retry handling</li>
 * <li>JSON serialization/deserialization</li>
 * <li>Flexible request/response handling</li>
 * <li>Connection pooling</li>
 * </ol>
 *<p>
 * Note: The caller is responsible for closing the response in order to reuse
 * the connection even it is not used.
 * </p>
 *
 * @author xbhel
 */
@Slf4j
public class HttpClient implements Closeable {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper()
            .disable(DeserializationFeature.FAIL_ON_IGNORED_PROPERTIES)
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .disable(SerializationFeature.WRITE_DATE_KEYS_AS_TIMESTAMPS);

    final CloseableHttpClient internalHttpClient;
    final HttpRetryStrategy retryStrategy;

    private HttpClient(CloseableHttpClient internalHttpClient, HttpRetryStrategy retryStrategy) {
        this.internalHttpClient = internalHttpClient;
        this.retryStrategy = retryStrategy;
    }

    /**
     * Using the shared instance is enough in the most case.
     */
    public static HttpClient getInstance() {
        return Builder.INSTANCE;
    }

    /**
     * Use the builder to create a new instance.
     */
    public static Builder builder() {
        return new Builder();
    }

    public String executeAsString(HttpRequest request) throws Exception {
        var charset = Optional.ofNullable(request.getCharset()).orElse(StandardCharsets.UTF_8);
        try (var response = execute(request)) {
            return EntityUtils.toString(response.getEntity(), charset);
        }
    }

    public <T> T execute(HttpRequest request, Class<T> type) throws Exception {
        try (var response = execute(request)) {
            return OBJECT_MAPPER.readValue(response.getEntity().getContent(), type);
        }
    }

    public <T> T execute(HttpRequest request, TypeReference<T> typeReference) throws Exception {
        try (var response = execute(request)) {
            return OBJECT_MAPPER.readValue(response.getEntity().getContent(), typeReference);
        }
    }

    public <T> T execute(HttpRequest request, Function<CloseableHttpResponse, T> responseHandler) throws Exception {
        try (var response = execute(request)) {
            return responseHandler.apply(response);
        }
    }

    public CloseableHttpResponse execute(HttpRequest request) throws Exception {
        // You can set any attribute to the context for your own purpose.
        var context = HttpClientContext.create();
        context.setAttribute("request-id", UUID.randomUUID().toString());
        return this.execute(request, context, null);
    }

    public CloseableHttpResponse execute(HttpRequest request, RequestConfig requestConfig) throws Exception {
        var context = HttpClientContext.create();
        context.setAttribute("request-id", UUID.randomUUID().toString());
        return this.execute(request, context, requestConfig);
    }

    public CloseableHttpResponse execute(HttpRequest request, HttpContext context, RequestConfig requestConfig)
            throws Exception {
        Objects.requireNonNull(request, "The request is required");
        Objects.requireNonNull(request.getMethod(), "The request method is required");
        Objects.requireNonNull(request.getUrl(), "The request url is required");

        int attempts = 0;
        var holder = new ResponseHolder();
        var httpUriRequest = createRequest(request, requestConfig);

        try {
            while (true) {
                holder = executeRequest(httpUriRequest, context);
                if (holder.isSuccessful()) {
                    return holder.response;
                }

                if (!retryStrategy.isRetryable(++attempts, holder.statusCode, holder.lastException, context)) {
                    break;
                }
                // Close failed response that is required in order to reuse connection
                holder.close();

                var delay = retryStrategy.getBackoffTimeMillis(attempts);
                log.warn("Failed to request {}, attempt #{} after {}ms", request, attempts, delay);
                ThreadUtils.silentSleep(delay);
            }
            retryStrategy.failed(request, holder.statusCode, holder.lastException, context);
        } catch (Exception e) {
            // Close failed response that is required in order to reuse connection
            holder.close();
            throw e;
        }
        return holder.response;
    }

    ResponseHolder executeRequest(HttpUriRequest httpRequest, HttpContext context) {
        try {
            var response = internalHttpClient.execute(httpRequest, context);
            return ResponseHolder.withResponse(response);
        } catch (IOException e) {
            return ResponseHolder.withLastException(e);
        }
    }

    HttpUriRequest createRequest(HttpRequest request, RequestConfig requestConfig) throws IOException {
        var defaultRequestHeaders = new HashMap<String, String>();
        defaultRequestHeaders.put(HttpHeaders.CONTENT_TYPE, ContentType.APPLICATION_JSON.toString());
        defaultRequestHeaders.put(HttpHeaders.ACCEPT, ContentType.APPLICATION_JSON.toString());
        var charset = Optional.ofNullable(request.getCharset()).orElse(StandardCharsets.UTF_8);

        var requestBuilder = RequestBuilder.create(request.getMethod());
        Optional.ofNullable(requestConfig).ifPresent(requestBuilder::setConfig);
        Optional.ofNullable(request.getQueryParams()).ifPresent(params -> params.forEach(requestBuilder::addParameter));
        Optional.ofNullable(request.getHeaders()).ifPresent(headers -> {
            defaultRequestHeaders.putAll(headers);
            headers.forEach(requestBuilder::addHeader);
        });
        if (request.getData() != null) {
            requestBuilder.setEntity(createEntity(request.getData(),
                    charset, defaultRequestHeaders.get(HttpHeaders.CONTENT_TYPE)));
        }
        return requestBuilder
                .setCharset(charset)
                .setUri(request.getUrl())
                .build();
    }

    HttpEntity createEntity(Object data, Charset charset, String contentType) throws IOException {
        if (data instanceof String str) {
            return new StringEntity(str, charset);
        }
        if (ContentType.APPLICATION_JSON.getMimeType().equals(contentType)) {
            return new StringEntity(OBJECT_MAPPER.writeValueAsString(data), charset);
        }
        if (data instanceof HttpEntity httpEntity) {
            return httpEntity;
        }
        if (data instanceof byte[] bytes) {
            return new ByteArrayEntity(bytes);
        }
        if (data instanceof File file) {
            return new FileEntity(file, ContentType.create(contentType, charset));
        }
        if (data instanceof InputStream input) {
            return new InputStreamEntity(input, ContentType.create(contentType, charset));
        }
        throw new UnsupportedOperationException("Unsupported data type: " + data.getClass().getName());
    }

    @Override
    public void close() throws java.io.IOException {
        if (internalHttpClient != null) {
            internalHttpClient.close();
        }
    }

    static class ResponseHolder {
        CloseableHttpResponse response;
        IOException lastException;
        Integer statusCode;

        static ResponseHolder withResponse(CloseableHttpResponse response) {
            var holder = new ResponseHolder();
            holder.response = response;
            holder.statusCode = response.getStatusLine().getStatusCode();
            return holder;
        }

        static ResponseHolder withLastException(IOException lastException) {
            var holder = new ResponseHolder();
            holder.lastException = lastException;
            return holder;
        }

        boolean isSuccessful() {
            return statusCode != null && statusCode >= 200 && statusCode < 300;
        }

        void close() throws IOException {
            if (response != null) {
                response.close();
            }
        }
    }

    public static class Builder {
        // a lazy initialization singleton for thread safety
        static final HttpClient INSTANCE = builder().build();

        static final int UNLIMITED = -1;
        static final int ONE_MINUTE_IN_MILLIS = 60_000;
        static final int DEFAULT_MAX_CONN_TOTAL = 20;
        static final int DEFAULT_MAX_CONN_PER_ROUTE = 5;
        static final int DEFAULT_VALIDATE_CONN_AFTER_INACTIVITY = 2_000;

        private boolean isDisableRedirect = false;
        private int connectTimeout = ONE_MINUTE_IN_MILLIS;
        private int socketTimeout = ONE_MINUTE_IN_MILLIS;
        private int connectionRequestTimeout = ONE_MINUTE_IN_MILLIS;
        private int maxConnTotal = DEFAULT_MAX_CONN_TOTAL;
        private int maxConnPerRoute = DEFAULT_MAX_CONN_PER_ROUTE;
        private long maxConnIdleTime = UNLIMITED;
        private long connKeepAliveTime = UNLIMITED;
        private int validateConnAfterInactivity = DEFAULT_VALIDATE_CONN_AFTER_INACTIVITY;
        private HttpRetryStrategy retryStrategy = DefaultHttpRetryStrategy.INSTANCE;

        public Builder retryStrategy(HttpRetryStrategy retryStrategy) {
            this.retryStrategy = retryStrategy;
            return this;
        }

        public Builder connectTimeout(int connectTimeoutMillis) {
            this.connectTimeout = connectTimeoutMillis;
            return this;
        }

        public Builder socketTimeout(int socketTimeoutMillis) {
            this.socketTimeout = socketTimeoutMillis;
            return this;
        }

        public Builder connectionRequestTimeout(int connectionRequestTimeoutMillis) {
            this.connectionRequestTimeout = connectionRequestTimeoutMillis;
            return this;
        }

        public Builder disableRedirect() {
            this.isDisableRedirect = true;
            return this;
        }

        public Builder connKeepAliveTime(long connKeepAliveTimeMillis) {
            this.connKeepAliveTime = connKeepAliveTimeMillis;
            return this;
        }

        public Builder maxConnTotal(int maxConnTotal) {
            this.maxConnTotal = maxConnTotal;
            return this;
        }

        public Builder maxConnPerRoute(int maxConnPerRoute) {
            this.maxConnPerRoute = maxConnPerRoute;
            return this;
        }

        public Builder validateConnAfterInactivity(int validateConnAfterInactivityMillis) {
            this.validateConnAfterInactivity = validateConnAfterInactivityMillis;
            return this;
        }

        public Builder maxConnIdleTime(long maxConnIdleTimeMillis) {
            this.maxConnIdleTime = maxConnIdleTimeMillis;
            return this;
        }

        public HttpClient build() {
            var requestConfig = RequestConfig.custom()
                    .setConnectTimeout(connectTimeout)
                    .setSocketTimeout(socketTimeout)
                    .setConnectionRequestTimeout(connectionRequestTimeout)
                    .setRedirectsEnabled(!isDisableRedirect)
                    .build();
            var connManager = new PoolingHttpClientConnectionManager(connKeepAliveTime, TimeUnit.MILLISECONDS);
            connManager.setMaxTotal(maxConnTotal);
            connManager.setDefaultMaxPerRoute(maxConnPerRoute);
            connManager.setValidateAfterInactivity(validateConnAfterInactivity);
            var httpClientBuilder = HttpClientBuilder.create();
            if (connKeepAliveTime > 0 && maxConnIdleTime > 0) {
                httpClientBuilder.evictIdleConnections(maxConnIdleTime, TimeUnit.MILLISECONDS);
            }
            var closeableHttpClient = httpClientBuilder
                    .setConnectionManager(connManager)
                    .setDefaultRequestConfig(requestConfig)
                    .disableAutomaticRetries()
                    .build();
            return new HttpClient(closeableHttpClient, retryStrategy);
        }
    }
}
