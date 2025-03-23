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
 * An enhanced HTTP client that wraps Apache HttpClient with additional
 * features.
 * 
 * <p>
 * Key features:
 * </p>
 * <ul>
 * <li><b>Automatic Retry</b> - Configurable retry logic for failed
 * requests</li>
 * <li><b>JSON Handling</b> - Built-in JSON serialization and
 * deserialization</li>
 * <li><b>Flexible Response Processing</b> - Support for custom response
 * handlers</li>
 * <li><b>Connection Pooling</b> - Efficient connection reuse and
 * management</li>
 * </ul>
 * 
 * <p>
 * Usage example:
 * </p>
 * 
 * <pre>
 * // Using shared instance (recommended for most cases)
 * HttpClient client = HttpClient.getInstance();
 * 
 * // Or create custom instance
 * HttpClient client = HttpClient.builder()
 *         .connectTimeout(5000)
 *         .maxConnTotal(50)
 *         .build();
 * </pre>
 * 
 * <p>
 * <b>Important:</b> Always close the response after use to properly release
 * the connection back to the pool:
 * </p>
 * 
 * <pre>
 * try (CloseableHttpResponse response = client.execute(request)) {
 *     // Process response
 * }
 * </pre>
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

    HttpClient(CloseableHttpClient internalHttpClient, HttpRetryStrategy retryStrategy) {
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
        // The HttpContext allows storing custom attributes that can be accessed
        // throughout the request execution lifecycle
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

                if (!retryStrategy.isRetryable(++attempts, holder.statusCode, holder.exception, context)) {
                    break;
                }
                // Close failed response that is required in order to reuse the underlying
                // connection
                holder.close();

                var delay = retryStrategy.getBackoffTimeMillis(attempts);
                log.warn("Request failed for {}. Retrying attempt #{} after {} ms delay", request, attempts, delay);
                TimeUnit.MILLISECONDS.sleep(delay);
            }
            retryStrategy.failed(request, holder.statusCode, holder.exception, context);
        } catch (Exception e) {
            // Close failed response that is required in order to reuse the underlying
            // connection
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
            return ResponseHolder.withException(e);
        }
    }

    static HttpUriRequest createRequest(HttpRequest request, RequestConfig requestConfig) throws IOException {
        var defaultRequestHeaders = new HashMap<String, String>();
        // use application/json;charset=UTF-8 as the default accept type
        defaultRequestHeaders.put(HttpHeaders.ACCEPT, ContentType.APPLICATION_JSON.toString());

        var charset = Optional.ofNullable(request.getCharset()).orElse(StandardCharsets.UTF_8);
        var requestBuilder = RequestBuilder.create(request.getMethod());
        Optional.ofNullable(requestConfig).ifPresent(requestBuilder::setConfig);
        Optional.ofNullable(request.getQueryParams()).ifPresent(params -> params.forEach(requestBuilder::addParameter));
        Optional.ofNullable(request.getHeaders()).ifPresent(defaultRequestHeaders::putAll);
        if (request.getData() != null) {
            var entity = createEntity(request.getData(), charset, defaultRequestHeaders.get(HttpHeaders.CONTENT_TYPE));
            if(entity.getContentType() != null) {
                defaultRequestHeaders.putIfAbsent(HttpHeaders.CONTENT_TYPE, entity.getContentType().toString());
            }
            requestBuilder.setEntity(entity);
        }
        defaultRequestHeaders.forEach(requestBuilder::addHeader);

        return requestBuilder
                .setCharset(charset)
                .setUri(request.getUrl())
                .build();
    }

    static HttpEntity createEntity(Object data, Charset charset, String contentType) throws IOException {
        if (data instanceof HttpEntity httpEntity) {
            return httpEntity;
        }

        var ct = Optional.ofNullable(contentType)
                .map(x -> ContentType.parse(x).withCharset(charset)).orElse(null);

        if (data instanceof CharSequence str) {
            return new StringEntity(str.toString(), ct);
        }

        if (data instanceof byte[] bytes) {
            return new ByteArrayEntity(bytes, ct);
        }

        if (data instanceof File file) {
            return new FileEntity(file, ct);
        }

        if (data instanceof InputStream input) {
            return new InputStreamEntity(input, ct);
        }
        
        // use application/json;charset=UTF-8 as the default content type
        if (contentType == null || ContentType.APPLICATION_JSON.getMimeType().equals(contentType)) {
            return new StringEntity(OBJECT_MAPPER.writeValueAsString(data),
                    ContentType.APPLICATION_JSON.withCharset(charset));
        }

        throw new UnsupportedOperationException(String.format(
                "Unsupported data type: %s with contentType: %s", data.getClass().getName(), contentType));
    }

    @Override
    public void close() throws java.io.IOException {
        if (internalHttpClient != null) {
            internalHttpClient.close();
        }
    }

    static class ResponseHolder {
        CloseableHttpResponse response;
        IOException exception;
        Integer statusCode;

        static ResponseHolder withResponse(CloseableHttpResponse response) {
            var holder = new ResponseHolder();
            holder.response = response;
            holder.statusCode = response.getStatusLine().getStatusCode();
            return holder;
        }

        static ResponseHolder withException(IOException lastException) {
            var holder = new ResponseHolder();
            holder.exception = lastException;
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
        // A singleton instance that is lazily initialized for thread safety.
        // This ensures the HttpClient is only created when first accessed.
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
