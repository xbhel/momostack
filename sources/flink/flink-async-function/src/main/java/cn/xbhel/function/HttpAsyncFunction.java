package cn.xbhel.function;

import java.io.IOException;
import java.io.Serial;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.core.JsonProcessingException;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.DeserializationFeature;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.SerializationFeature;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.apache.flink.streaming.api.datastream.AsyncDataStream;
import org.apache.flink.streaming.api.functions.async.AsyncRetryStrategy;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.functions.async.RichAsyncFunction;
import org.apache.flink.util.Preconditions;
import org.apache.flink.util.function.SerializableFunction;
import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.HttpUriRequest;
import org.apache.http.client.methods.RequestBuilder;
import org.apache.http.client.protocol.HttpClientContext;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.util.EntityUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * How to use the retry mechanism provided by {@link AsyncDataStream#unorderedWaitWithRetry} instead of the retry mechanism provided by this class:
 * <ol>
 * <li>Create a class that implements the {@link HttpRetryStrategy} interface.</li>
 * <li>Override the {@link HttpRetryStrategy#isRetryable} method to always return false.</li>
 * <li>Override the {@link HttpRetryStrategy#failed} method to throw a specific exception.</li>
 * <li>Use {@link AsyncDataStream#unorderedWaitWithRetry} with {@link AsyncRetryStrategy} to handle retries based on the specific exception.</li>
 * </ol>
 */
@Slf4j
@RequiredArgsConstructor
public class HttpAsyncFunction<R> extends RichAsyncFunction<HttpRequest, R> {

    @Serial
    private static final long serialVersionUID = -1805514922755278162L;

    private final HttpConfig httpConfig;
    private final boolean logFailureOnly;
    private final HttpRetryStrategy retryStrategy;
    private final SerializableFunction<HttpResponse, R> responseParser;

    transient CloseableHttpClient httpClient;
    transient ObjectMapper objectMapper;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        this.httpClient = createHttpClient();
        this.objectMapper = new ObjectMapper()
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
                .disable(DeserializationFeature.FAIL_ON_IGNORED_PROPERTIES);
    }

    public HttpAsyncFunction(SerializableFunction<HttpResponse, R> responseParser) {
        this.responseParser = responseParser;
        this.httpConfig = new HttpConfig();
        this.retryStrategy = new DefaultHttpRetryStrategy();
        this.logFailureOnly = false;
    }

    @Override
    public void asyncInvoke(HttpRequest httpRequest, ResultFuture<R> resultFuture) {
        Preconditions.checkNotNull(httpRequest, "The HttpRequest must be not null.");
        Preconditions.checkArgument(StringUtils.isNotEmpty(httpRequest.getUrl()), "The request URL is required.");
        Preconditions.checkArgument(StringUtils.isNotEmpty(httpRequest.getMethod()), "The request method is required.");

        CompletableFuture.supplyAsync(() -> executeHttpRequest(httpRequest))
                .whenComplete((result, ex) -> {
                    if (ex == null) {
                        result.ifPresentOrElse(r -> resultFuture.complete(Collections.singletonList(r)),
                                () -> resultFuture.complete(Collections.emptyList()));
                    } else {
                        var origin = Optional.ofNullable(ex.getCause()).orElse(ex);
                        log.error("Error executing {}, Error: {}", httpRequest, ex.getMessage(), origin);
                        if (logFailureOnly) {
                            resultFuture.complete(Collections.emptyList());
                        } else {
                            resultFuture.completeExceptionally(ex);
                        }
                    }
                });
    }

    Optional<R> executeHttpRequest(HttpRequest httpRequest) {
        int attempts = 0;
        Integer statusCode = null;
        String respErrorMessage = null;
        IOException lastException = null;

        var request = convertToHttpUriRequest(httpRequest);
        var requestContext = HttpClientContext.create();
        // add some custom attributes
        requestContext.setAttribute("request-id", UUID.randomUUID().toString());

        do {
            try (var response = httpClient.execute(request, requestContext)) {
                statusCode = response.getStatusLine().getStatusCode();
                if (statusCode == HttpStatus.SC_OK || statusCode == HttpStatus.SC_ACCEPTED) {
                    return Optional.ofNullable(responseParser.apply(response));
                }
                respErrorMessage = praseResponseErrorMessage(response);
            } catch (IOException exception) {
                lastException = exception;
            }

            if (attempts > 0) {
                var backoffTime = retryStrategy.getBackoffTimeMills(attempts);
                log.warn("Attempts #{} to request [{}] failed. Retrying in {} ms.",
                        attempts, request, backoffTime);
                silentSleep(backoffTime);
            }
            attempts++;

        } while (retryStrategy.isRetryable(attempts, statusCode, respErrorMessage, lastException));

        retryStrategy.failed(httpRequest, statusCode, respErrorMessage, lastException);
        return Optional.empty();
    }

    CloseableHttpClient createHttpClient() {
        // 1. Request Configuration
        var requestConfig = RequestConfig.custom()
                // Determines the timeout in milliseconds until a connection is established.
                .setConnectTimeout((int) httpConfig.getConnectTimeoutMs())
                // Defines the socket timeout (SO_TIMEOUT) in milliseconds, which is the timeout
                // for waiting for data or, put differently,
                // a maximum period inactivity between two consecutive data packets.
                .setSocketTimeout((int) httpConfig.getConnectTimeoutMs())
                // Returns the timeout in milliseconds used when requesting a connection from
                // the connection manager.
                .setConnectionRequestTimeout((int) httpConfig.getConnectionRequestTimeoutMs())
                // Determines whether redirects should be handled automatically.
                .setRedirectsEnabled(true)
                // Returns the maximum number of redirects to be followed.
                .setMaxRedirects(50)
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
        var connectionManager = new PoolingHttpClientConnectionManager(
                httpConfig.getConnectionTtlTimeMs(), TimeUnit.MILLISECONDS);
        // Checks the connection if the elapsed time since
        // the last use of the connection exceeds the timeout that has been set.
        // Increase re-validated connection time from 2s to 5s.
        connectionManager.setValidateAfterInactivity((int) httpConfig.getValidateAfterInactivityMs());
        // Increase default max connection per route from 2 to 10.
        // Since I'm always use the same route.
        connectionManager.setDefaultMaxPerRoute(httpConfig.getMaxTotalPerRoute());
        // Decrease max total connection from 20 to 10.
        connectionManager.setMaxTotal(httpConfig.getMaxTotal());

        var httpClientBuilder = HttpClientBuilder.create()
                .setDefaultRequestConfig(requestConfig)
                .setConnectionManager(connectionManager)
                // By default, Apache HttpClient retries at most 3 times all idempotent requests
                // completed with IOException,
                // Here are some IOException subclasses that HttpClient considers non-retryable.
                // More specifically, they are:
                // InterruptedIOException, ConnectException, UnknownHostException, SSLException
                // and NoRouteToHostException.
                .disableAutomaticRetries();
        if (httpConfig.getConnectionTtlTimeMs() > 0 && httpConfig.getMaxIdleTimeMs() > 0) {
            httpClientBuilder.evictIdleConnections(httpConfig.getMaxIdleTimeMs(), TimeUnit.MILLISECONDS);
        }
        return httpClientBuilder.build();

    }

    String praseResponseErrorMessage(HttpResponse response) {
        try {
            return EntityUtils.toString(response.getEntity());
        } catch (IOException e) {
            throw new IllegalStateException("Error while parsing error message.", e);
        }
    }

    HttpUriRequest convertToHttpUriRequest(HttpRequest httpRequest) {
        var charset = Optional.ofNullable(httpRequest.getCharset())
                .orElse(StandardCharsets.UTF_8);
        var requestBuilder = RequestBuilder.create(httpRequest.getMethod())
                // The defalut value is set to "ISO-8859-1"
                .setCharset(charset)
                .setUri(httpRequest.getUrl());
        Optional.ofNullable(httpRequest.getHeaders())
                .ifPresent(headers -> headers.forEach(requestBuilder::addHeader));
        Optional.ofNullable(httpRequest.getQueryParams())
                .ifPresent(params -> params.forEach(requestBuilder::addHeader));
        try {
            if (Objects.nonNull(httpRequest.getData())) {
                requestBuilder.setEntity(new StringEntity(
                        objectMapper.writeValueAsString(httpRequest.getData()), charset));
            }
            return requestBuilder.build();
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Failed to serialize request data.", e);
        }
    }

    void silentSleep(long sleepTime) {
        try {
            Thread.sleep(sleepTime);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Sleep interrupted", e);
        }
    }

    @Override
    public void close() throws Exception {
        if (httpClient != null) {
            httpClient.close();
        }
    }

}