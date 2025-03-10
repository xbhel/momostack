package cn.xbhel.function;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.core.JsonProcessingException;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.DeserializationFeature;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.SerializationFeature;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.functions.async.RichAsyncFunction;
import org.apache.flink.util.Preconditions;
import org.apache.flink.util.function.SerializableFunction;
import org.apache.http.HttpStatus;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.HttpUriRequest;
import org.apache.http.client.methods.RequestBuilder;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.util.EntityUtils;

import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
public class HttpAsyncFunction<R> extends RichAsyncFunction<HttpRequest, R> {

    private static final Set<Integer> RETRYABLE_STATUS_CODES = Set.of(429, 503);

    private transient CloseableHttpClient httpClient;
    private transient ObjectMapper objectMapper;
    private final SerializableFunction<InputStream, R> responseExtractor;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        // 1. Request Configuration
        var requestConfig = RequestConfig.custom()
                // Determines the timeout in milliseconds until a connection is established.
                .setConnectTimeout(30000)
                // Defines the socket timeout (SO_TIMEOUT) in milliseconds, which is the timeout
                // for waiting for data or, put differently,
                // a maximum period inactivity between two consecutive data packets.
                .setSocketTimeout(60000)
                // Returns the timeout in milliseconds used when requesting a connection from
                // the connection manager.
                .setConnectionRequestTimeout(60000)
                // Determines whether redirects should be handled automatically.
                .setRedirectsEnabled(true)
                // Returns the maximum number of redirects to be followed.
                .setMaxRedirects(3)
                // Determines whether circular redirects (redirects to the same location) should
                // be allowed.
                .setCircularRedirectsAllowed(false)
                // Determines whether authentication should be handled automatically.
                .setAuthenticationEnabled(true)
                .build();

        // 2. Http Connection Manager Configration
        // Set TTL to 5min.
        // TTL defines maximum life span of persistent connections regardless of their
        // expiration setting.
        // No persistent connection will be re-used past its TTL value.
        var manager = new PoolingHttpClientConnectionManager(5, TimeUnit.MINUTES);
        // Dncrease max total connection from 20 to 10.
        manager.setMaxTotal(10);
        // Increase default max connection per route from 2 to 10.
        // Since I'm always use the same route.
        manager.setDefaultMaxPerRoute(10);
        // Checks the connection if the elapsed time since
        // the last use of the connection exceeds the timeout that has been set.
        // Increase re-validated connection time from 2s to 5s.
        manager.setValidateAfterInactivity(5000);

        this.httpClient = HttpClientBuilder
                .create()
                .setDefaultRequestConfig(requestConfig)
                .setConnectionManager(manager)
                // By default, Apache HttpClient retries at most 3 times all idempotent requests
                // completed with IOException,
                // Here are some IOException subclasses that HttpClient considers non-retryable.
                // More specifically, they are:
                // InterruptedIOException, ConnectException, UnknownHostException, SSLException
                // and NoRouteToHostException.
                .disableAutomaticRetries()
                .build();

        this.objectMapper = new ObjectMapper()
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
                .disable(DeserializationFeature.FAIL_ON_IGNORED_PROPERTIES);

    }

    @Override
    public void asyncInvoke(HttpRequest httpRequest, ResultFuture<R> resultFuture) throws Exception {
        Preconditions.checkNotNull(httpRequest, "The HttpRequest must be not null.");
        Preconditions.checkArgument(StringUtils.isNotEmpty(httpRequest.getUrl()), "The request URL is required.");
        Preconditions.checkArgument(StringUtils.isNotEmpty(httpRequest.getMethod()), "The request method is required.");

        CompletableFuture.supplyAsync(() -> executeHttpRequest(httpRequest))
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        resultFuture.completeExceptionally(ex);
                    } else {
                        resultFuture.complete(Collections.singletonList(result));
                    }
                });
    }

    R executeHttpRequest(HttpRequest httpRequest) {
        int statusCode = -1;
        String errorMessage = null;
        boolean isRetryable = false;
        try {
            var response = httpClient.execute(createApacheHttpRequest(httpRequest));
            statusCode = response.getStatusLine().getStatusCode();
            if (statusCode == HttpStatus.SC_OK || statusCode == HttpStatus.SC_ACCEPTED) {
                try (var is = response.getEntity().getContent()) {
                    return responseExtractor.apply(is);
                }
            }
            isRetryable = RETRYABLE_STATUS_CODES.contains(statusCode);
            errorMessage = EntityUtils.toString(response.getEntity());
        } catch (IOException e) {
            isRetryable = false;
        }

        if (isRetryable) {
            throw new RetryableException(statusCode, errorMessage);
        }

        throw new IllegalStateException(statusCode + "|" + errorMessage);
    }

    HttpUriRequest createApacheHttpRequest(HttpRequest httpRequest) {
        // Convert My's HttpRequest to Apache HttpUriRequest
        var requestBuilder = RequestBuilder.create(httpRequest.getMethod());
        Optional.ofNullable(httpRequest.getHeaders())
                .ifPresent(headers -> headers.forEach(requestBuilder::addHeader));
        Optional.ofNullable(httpRequest.getQueryParams())
                .ifPresent(params -> params.forEach(requestBuilder::addHeader));
        var charset = Optional.ofNullable(httpRequest.getCharset()).orElse(StandardCharsets.UTF_8);
        try {
            return requestBuilder
                    .setUri(httpRequest.getUrl())
                    // The defalut value is set to "ISO-8859-1"
                    .setCharset(charset)
                    .setEntity(new StringEntity(objectMapper.writeValueAsString(httpRequest.getData()), charset))
                    .build();
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException(e);
        }
    }

    @Override
    public void close() throws Exception {
        if (httpClient != null) {
            httpClient.close();
        }
    }

}