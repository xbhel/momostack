package cn.xbhel.http;

import org.apache.http.HttpEntity;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.entity.ByteArrayEntity;
import org.apache.http.entity.FileEntity;
import org.apache.http.entity.InputStreamEntity;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.util.EntityUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

import static cn.xbhel.http.HttpClient.Builder.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

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
        assertNotNull(HttpClient.builder());
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
            httpClient = HttpClient.builder().build();
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
        try (var httpClientBuilderStatic = mockStatic(HttpClientBuilder.class)) {
            httpClientBuilderStatic.when(HttpClientBuilder::create).thenReturn(mockHttpClientBuilder);
            httpClient = HttpClient.builder()
                    .connectTimeout(1000)
                    .socketTimeout(1000)
                    .connectionRequestTimeout(1000)
                    .retryStrategy(NoHttpRetryStrategy.INSTANCE)
                    .build();
        }

        verify(mockHttpClientBuilder).setDefaultRequestConfig(requestConfigCaptor.capture());

        assertThat(requestConfigCaptor.getValue())
                .extracting("connectTimeout", "socketTimeout", "connectionRequestTimeout", "redirectsEnabled")
                .containsExactly(1000, 1000, 1000, true);

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
        HttpEntity entity = HttpClient.createEntity(data, StandardCharsets.UTF_8, null);
        assertThat(entity).isInstanceOf(StringEntity.class);
        assertThat(EntityUtils.toString(entity)).contains("\"key\":\"value\"");
    }

    @Test
    void testCreateEntity_UnsupportedType() {
        assertThatThrownBy(() -> HttpClient.createEntity(new Object(), StandardCharsets.UTF_8, "text/plain"))
                .isInstanceOf(UnsupportedOperationException.class)
                .hasMessageContaining("Unsupported data type: java.lang.Object with contentType: text/plain");
    }

}
