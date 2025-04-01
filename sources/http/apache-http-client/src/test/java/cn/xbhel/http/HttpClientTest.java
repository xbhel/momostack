package cn.xbhel.http;

import static cn.xbhel.http.HttpClient.builder;
import static cn.xbhel.http.HttpClient.Builder.DEFAULT_MAX_CONN_PER_ROUTE;
import static cn.xbhel.http.HttpClient.Builder.DEFAULT_MAX_CONN_TOTAL;
import static cn.xbhel.http.HttpClient.Builder.DEFAULT_VALIDATE_CONN_AFTER_INACTIVITY;
import static cn.xbhel.http.HttpClient.Builder.ONE_MINUTE_IN_MILLIS;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.RETURNS_SELF;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

import org.apache.http.HttpEntity;
import org.apache.http.HttpEntityEnclosingRequest;
import org.apache.http.HttpHeaders;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpEntityEnclosingRequestBase;
import org.apache.http.client.methods.HttpUriRequest;
import org.apache.http.client.methods.RequestBuilder;
import org.apache.http.client.protocol.HttpClientContext;
import org.apache.http.entity.ByteArrayEntity;
import org.apache.http.entity.FileEntity;
import org.apache.http.entity.InputStreamEntity;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.protocol.HttpContext;
import org.apache.http.util.EntityUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class HttpClientTest {

    @Test
    void testResponseHolder_createInstanceWithResponse() {
        var response = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(200);
        var holder = HttpClient.ResponseHolder.withResponse(response);
        assertEquals(200, holder.statusCode);
        assertEquals(response, holder.response);
        assertNull(holder.exception);
    }

    @Test
    void testResponseHolder_createInstanceWithLastException() {
        var exception = new IOException("test");
        var holder = HttpClient.ResponseHolder.withException(exception);
        assertEquals(exception, holder.exception);
        assertNull(holder.response);
        assertNull(holder.statusCode);
    }

    @Test
    void testResponseHolderIsSuccessful_withSuccessfulResponse() {
        var response = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(200);
        var holder = HttpClient.ResponseHolder.withResponse(response);
        assertTrue(holder.isSuccessful());
    }

    @Test
    void testResponseHolderIsSuccessful_withFailedResponse() {
        var response = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(500);
        var holder = HttpClient.ResponseHolder.withResponse(response);
        assertFalse(holder.isSuccessful());
    }

    @Test
    void testResponseHolderIsSuccessful_withException() {
        var exception = new IOException("test");
        var holder = HttpClient.ResponseHolder.withException(exception);
        assertFalse(holder.isSuccessful());
    }

    @Test
    void testResponseHolderClose_withResponse() throws IOException {
        var response = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(response.getStatusLine().getStatusCode()).thenReturn(200);
        var holder = HttpClient.ResponseHolder.withResponse(response);
        holder.close();
        verify(response, times(1)).close();
    }

    @Test
    void testResponseHolderClose_withException() {
        var exception = new IOException("test");
        var holder = HttpClient.ResponseHolder.withException(exception);
        assertDoesNotThrow(holder::close);
    }

    @Test
    void testCreateBuilder() {
        assertNotNull(builder());
    }

    @Test
    void testGetInstance_ReturningSharedInstance() {
        assertThat(HttpClient.getInstance()).isEqualTo(HttpClient.Builder.INSTANCE);
    }

    @Test
    void testCreateHttpClient_withDefaultConfiguration() {
        // Immediately call to initialize the lazy instance, otherwise to
        // verify(mockHttpClientBuilder) will fail.
        // because the lazy instance Builder#INSTANCE will be also created in the
        // Builder.class is loaded,
        // the mockHttpClientBuilder#setDefaultRequestConfig will be called at two
        // times.
        testGetInstance_ReturningSharedInstance();

        // The Answer, Mockito#RETURNS_SELF, is used to support Builder.
        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);

        HttpClient httpClient;
        var requestConfigCaptor = ArgumentCaptor.forClass(RequestConfig.class);
        var connManagerCaptor = ArgumentCaptor.forClass(PoolingHttpClientConnectionManager.class);
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            httpClient = builder().build();
        }

        verify(mockHttpClientBuilder).setDefaultRequestConfig(requestConfigCaptor.capture());
        verify(mockHttpClientBuilder).setConnectionManager(connManagerCaptor.capture());
        verify(mockHttpClientBuilder).disableAutomaticRetries();

        assertThat(requestConfigCaptor.getValue())
                .extracting("connectTimeout", "socketTimeout", "connectionRequestTimeout", "redirectsEnabled")
                .containsExactly(ONE_MINUTE_IN_MILLIS, ONE_MINUTE_IN_MILLIS, ONE_MINUTE_IN_MILLIS, true);

        assertThat(connManagerCaptor.getValue())
                .extracting(PoolingHttpClientConnectionManager::getMaxTotal,
                        PoolingHttpClientConnectionManager::getDefaultMaxPerRoute,
                        PoolingHttpClientConnectionManager::getValidateAfterInactivity)
                .containsExactly(DEFAULT_MAX_CONN_TOTAL, DEFAULT_MAX_CONN_PER_ROUTE,
                        DEFAULT_VALIDATE_CONN_AFTER_INACTIVITY);

        assertEquals(httpClient.internalHttpClient, closeableHttpClient);
        assertThat(httpClient.retryStrategy).isEqualTo(DefaultHttpRetryStrategy.INSTANCE);
    }

    @Test
    void testCreateHttpClient_withCustomConfiguration() {
        testGetInstance_ReturningSharedInstance();

        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);

        HttpClient httpClient;
        var requestConfigCaptor = ArgumentCaptor.forClass(RequestConfig.class);
        var connManagerCaptor = ArgumentCaptor.forClass(PoolingHttpClientConnectionManager.class);
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            httpClient = builder()
                    .connectTimeout(1000)
                    .socketTimeout(1000)
                    .connectionRequestTimeout(1000)
                    .retryStrategy(NoHttpRetryStrategy.INSTANCE)
                    .disableRedirect()
                    .connKeepAliveTime(30000)
                    .maxConnIdleTime(30000)
                    .maxConnPerRoute(10)
                    .maxConnTotal(10)
                    .validateConnAfterInactivity(1000)
                    .build();
        }
        verify(mockHttpClientBuilder).setConnectionManager(connManagerCaptor.capture());
        verify(mockHttpClientBuilder).setDefaultRequestConfig(requestConfigCaptor.capture());

        assertThat(requestConfigCaptor.getValue())
                .extracting("connectTimeout", "socketTimeout", "connectionRequestTimeout", "redirectsEnabled")
                .containsExactly(1000, 1000, 1000, false);

        assertThat(connManagerCaptor.getValue())
                .extracting(PoolingHttpClientConnectionManager::getMaxTotal,
                        PoolingHttpClientConnectionManager::getDefaultMaxPerRoute,
                        PoolingHttpClientConnectionManager::getValidateAfterInactivity)
                .containsExactly(10, 10, 1000);

        assertEquals(httpClient.internalHttpClient, closeableHttpClient);
        assertThat(httpClient.retryStrategy).isEqualTo(NoHttpRetryStrategy.INSTANCE);
    }

    @Test
    void testCreateEntity_HttpEntityInput() throws IOException {
        HttpEntity entity = new StringEntity("test");
        assertThat(HttpClient.createEntity(entity, StandardCharsets.UTF_8, null))
                .isSameAs(entity);
    }

    @Test
    void testCreateEntity_CharSequenceInput() throws IOException {
        CharSequence data = new StringBuilder("test");
        HttpEntity entity = HttpClient.createEntity(data, StandardCharsets.UTF_8, "text/plain");
        assertThat(entity).isInstanceOf(StringEntity.class);
        assertThat(EntityUtils.toString(entity)).isEqualTo("test");
    }

    @Test
    void testCreateEntity_ByteArrayInput() throws IOException {
        byte[] data = "test".getBytes(StandardCharsets.UTF_8);
        HttpEntity entity = HttpClient.createEntity(data, StandardCharsets.UTF_8, "application/octet-stream");
        assertThat(entity).isInstanceOf(ByteArrayEntity.class);
        assertThat(EntityUtils.toByteArray(entity)).isEqualTo(data);
    }

    @Test
    void testCreateEntity_FileInput() throws IOException {
        File tempFile = File.createTempFile("test", ".txt");
        tempFile.deleteOnExit();
        HttpEntity entity = HttpClient.createEntity(tempFile, StandardCharsets.UTF_8, "text/plain");
        assertThat(entity).isInstanceOf(FileEntity.class);
    }

    @Test
    void testCreateEntity_InputStreamInput() throws IOException {
        InputStream inputStream = new ByteArrayInputStream("test".getBytes(StandardCharsets.UTF_8));
        HttpEntity entity = HttpClient.createEntity(inputStream, StandardCharsets.UTF_8, "application/octet-stream");
        assertThat(entity).isInstanceOf(InputStreamEntity.class);
    }

    @Test
    void testCreateEntity_CustomObject() throws IOException {
        Map<String, String> data = new HashMap<>();
        data.put("key", "value");
        HttpEntity entity = HttpClient.createEntity(data, StandardCharsets.UTF_8, "application/json");
        assertThat(entity).isInstanceOf(StringEntity.class);
        assertThat(EntityUtils.toString(entity)).contains("\"key\":\"value\"");
        assertThat(entity.getContentType().getValue()).isEqualTo("application/json; charset=UTF-8");
    }

    @Test
    void testCreateEntity_CustomObjectAndEmptyContentType() throws IOException {
        Map<String, String> data = new HashMap<>();
        data.put("key", "value");
        HttpEntity entity = HttpClient.createEntity(data, StandardCharsets.UTF_8, null);
        assertThat(entity).isInstanceOf(StringEntity.class);
        assertThat(EntityUtils.toString(entity)).contains("\"key\":\"value\"");
        assertThat(entity.getContentType().getValue()).isEqualTo("application/json; charset=UTF-8");
    }

    @Test
    void testCreateEntity_UnsupportedType() {
        assertThatThrownBy(() -> HttpClient.createEntity(new Object(), StandardCharsets.UTF_8, "text/plain"))
                .isInstanceOf(UnsupportedOperationException.class)
                .hasMessageContaining("Unsupported data type: java.lang.Object with contentType: text/plain");
    }

    @Test
    void testCreateRequest_BasicRequest() throws IOException {
        var request = new HttpRequest("http://example.com", "GET");
        var httpRequest = HttpClient.createRequest(request, null);
        assertEquals("GET", httpRequest.getMethod());
        assertEquals("http://example.com", httpRequest.getURI().toString());
        assertThat(httpRequest.getFirstHeader(HttpHeaders.ACCEPT).getValue())
                .isEqualTo("application/json; charset=UTF-8");
    }

    @Test
    void testCreateRequest_WithCustomHeaders() throws IOException {
        var request = new HttpRequest("http://example.com", "POST");
        request.setHeaders(Map.of(
                "Custom-Header", "custom-value",
                HttpHeaders.ACCEPT, "text/plain"));
        var httpRequest = HttpClient.createRequest(request, null);
        assertEquals("custom-value",
                httpRequest.getFirstHeader("Custom-Header").getValue());
        assertEquals("text/plain",
                httpRequest.getFirstHeader(HttpHeaders.ACCEPT).getValue());
    }

    @Test
    void testCreateRequest_WithQueryParams() throws IOException {
        var request = new HttpRequest("http://example.com", "GET");
        request.setQueryParams(Map.of(
                "param1", "value1",
                "param2", "value2"));

        var httpRequest = HttpClient.createRequest(request, null);
        assertTrue(httpRequest.getURI().toString().contains("param1=value1"));
        assertTrue(httpRequest.getURI().toString().contains("param2=value2"));
    }

    @Test
    void testCreateRequest_WithRequestConfig() throws IOException {
        var mockRequestBuilder = mock(RequestBuilder.class, RETURNS_SELF);
        try (var requestBuilderStatic = mockStatic(RequestBuilder.class)) {
            requestBuilderStatic.when(() -> RequestBuilder.create("GET")).thenReturn(mockRequestBuilder);
            var request = new HttpRequest("http://example.com", "GET");
            var requestConfig = RequestConfig.custom()
                    .setConnectTimeout(1000)
                    .build();
            HttpClient.createRequest(request, requestConfig);
            verify(mockRequestBuilder).setConfig(requestConfig);
        }
    }

    @Test
    void testCreateRequest_WithRequestBody() throws IOException {
        var request = new HttpRequest("http://example.com", "POST");
        request.setData("test body");
        request.setCharset(StandardCharsets.UTF_8);

        var httpRequest = HttpClient.createRequest(request, null);
        assertInstanceOf(HttpEntityEnclosingRequest.class, httpRequest);
        var entity = ((HttpEntityEnclosingRequest) httpRequest).getEntity();
        assertEquals("test body", EntityUtils.toString(entity));
        assertNull(httpRequest.getFirstHeader(HttpHeaders.CONTENT_TYPE));
    }

    @Test
    void testCreateRequest_WithCustomContentType() throws IOException {
        var request = new HttpRequest("http://example.com", "POST");
        request.setData("test body");
        request.setHeaders(Map.of(
                HttpHeaders.CONTENT_TYPE, "text/plain"));
        var httpRequest = HttpClient.createRequest(request, null);
        var entity = ((HttpEntityEnclosingRequestBase) httpRequest).getEntity();
        assertEquals("text/plain; charset=UTF-8", entity.getContentType().getValue());
    }

    @Test
    void testCreateRequest_AssignDefaultContentTypeForSerializableObjectToJsonString() throws IOException {
        var request = new HttpRequest("http://example.com", "POST");
        request.setData(Map.of("key", "value"));
        var httpRequest = HttpClient.createRequest(request, null);
        var entity = ((HttpEntityEnclosingRequestBase) httpRequest).getEntity();
        assertEquals("{\"key\":\"value\"}", EntityUtils.toString(entity));
        assertEquals("application/json; charset=UTF-8", entity.getContentType().getValue());
    }

    @Test
    void testClose() throws IOException {
        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            var httpClient = builder().build();
            httpClient.close();
            verify(httpClient.internalHttpClient, times(1)).close();
        }
    }

    @Test
    void testClose_withException() throws IOException {
        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);
        doThrow(new IOException("test")).when(closeableHttpClient).close();
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            var httpClient = builder().build();
            assertThrows(IOException.class, httpClient::close);
        }
    }

    @Test
    void testExecute_successfulResponse() throws Exception {
        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);
        HttpClient httpClient;
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            httpClient = builder().build();
        }

        var mockCloseableHttpResponse = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(mockCloseableHttpResponse.getStatusLine().getStatusCode()).thenReturn(200);
        when(closeableHttpClient.execute(any(HttpUriRequest.class), any(HttpContext.class)))
                .thenReturn(mockCloseableHttpResponse);
        var request = new HttpRequest("http://example.com", "GET");
        var response = httpClient.execute(request, HttpClientContext.create(), null);
        assertEquals(200, response.getStatusLine().getStatusCode());
    }

    @Test
    void testExecute_failedResponse() throws Exception {
        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);
        HttpClient httpClient;
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            httpClient = builder()
                    .retryStrategy(new DefaultHttpRetryStrategy().setFailedAtRetriesExhausted(true))
                    .build();
        }
        var mockCloseableHttpResponse = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(mockCloseableHttpResponse.getStatusLine().getStatusCode()).thenReturn(400);
        when(closeableHttpClient.execute(any(HttpUriRequest.class), any(HttpContext.class)))
                .thenReturn(mockCloseableHttpResponse);
        var request = new HttpRequest("http://example.com", "GET");
        assertThrows(HttpExecutionException.class, () ->
                httpClient.execute(request, HttpClientContext.create(), null));
    }

    @Test
    void testExecute_exception() throws Exception {
        var mockHttpClientBuilder = mock(HttpClientBuilder.class, RETURNS_SELF);
        var closeableHttpClient = mock(CloseableHttpClient.class);
        when(mockHttpClientBuilder.build()).thenReturn(closeableHttpClient);
        HttpClient httpClient;
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            httpClient = builder().build();
        }
        doThrow(new IOException("test")).when(closeableHttpClient).execute(any(HttpUriRequest.class),
                any(HttpContext.class));
        var request = new HttpRequest("http://example.com", "GET");
        assertThrows(IOException.class, () -> httpClient.execute(request, HttpClientContext.create(), null));
    }

    @Test
    void testExecute_failedResponseAndRetries() throws Exception {
        var mockCloseableHttpClient = mock(CloseableHttpClient.class);
        var mockCloseableHttpResponse = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(mockCloseableHttpResponse.getStatusLine().getStatusCode()).thenReturn(500);
        when(mockCloseableHttpClient.execute(any(HttpUriRequest.class), any(HttpContext.class)))
                .thenReturn(mockCloseableHttpResponse);
        var spyHttpRetryStrategy = spy(new DefaultHttpRetryStrategy(3, 0.1).setFailedAtRetriesExhausted(false));
        var httpClient = new HttpClient(mockCloseableHttpClient, spyHttpRetryStrategy);
        var responseHolder = spy(HttpClient.ResponseHolder.withResponse(mockCloseableHttpResponse));
        try (var responseHolderStatic = mockStatic(HttpClient.ResponseHolder.class)) {
            responseHolderStatic.when(() -> HttpClient.ResponseHolder.withResponse(any()))
                    .thenReturn(responseHolder);

            var request = new HttpRequest("http://example.com", "GET");
            var response = httpClient.execute(request, HttpClientContext.create(), null);
            assertEquals(500, response.getStatusLine().getStatusCode());
            verify(mockCloseableHttpClient, times(4)).execute(any(HttpUriRequest.class), any(HttpContext.class));
            verify(spyHttpRetryStrategy).failed(eq(request), eq(500), eq(null), any());
            verify(responseHolder, times(3)).close();
        }
        httpClient.close();
    }

    @Test
    void testExecute_withArgsRequestAndRequestConfig_successfulResponse() throws Exception {
        var mockCloseableHttpResponse = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(mockCloseableHttpResponse.getStatusLine().getStatusCode()).thenReturn(200);

        var httpClient = spy(HttpClient.getInstance());
        doReturn(mockCloseableHttpResponse)
                .when(httpClient).execute(any(HttpRequest.class), any(HttpContext.class), any(RequestConfig.class));

        var request = new HttpRequest("https://api.example.com/test", "GET");
        var requestConfig = RequestConfig.custom()
                .setConnectTimeout(5000)
                .setSocketTimeout(5000)
                .build();

        var response = httpClient.execute(request, requestConfig);
        assertNotNull(response);
        assertEquals(200, response.getStatusLine().getStatusCode());
    }

    @Test
    void testExecute_withArgsRequestAndRequestConfig_failedResponse() throws Exception {
        var mockCloseableHttpResponse = mock(CloseableHttpResponse.class, RETURNS_DEEP_STUBS);
        when(mockCloseableHttpResponse.getStatusLine().getStatusCode()).thenReturn(400);

        var httpClient = spy(HttpClient.getInstance());
        doReturn(mockCloseableHttpResponse)
                .when(httpClient).execute(any(HttpRequest.class), any(HttpContext.class), any(RequestConfig.class));

        var request = new HttpRequest("https://api.example.com/test", "GET");
        var requestConfig = RequestConfig.custom().build();
        var response = httpClient.execute(request, requestConfig);
        assertNotNull(response);
        assertEquals(400, response.getStatusLine().getStatusCode());
    }

    @Test
    void testExecute_withArgsRequestAndRequestConfig_exception() throws Exception {
        var httpClient = spy(HttpClient.getInstance());
        doThrow(new IOException("test")).when(httpClient)
                .execute(any(HttpRequest.class), any(HttpContext.class), any(RequestConfig.class));

        var request = new HttpRequest("https://api.example.com/test", "GET");
        var requestConfig = RequestConfig.custom().build();
        assertThrows(IOException.class, () -> httpClient.execute(request, requestConfig));
    }

}
