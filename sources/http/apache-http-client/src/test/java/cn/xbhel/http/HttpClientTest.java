package cn.xbhel.http;

import static cn.xbhel.http.HttpClient.Builder.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.*;

import java.io.IOException;

import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
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
        assertNull(holder.lastException);
    }

    @Test
    void testResponseHolder_createInstanceWithLastException() {
        var exception = new IOException("test");
        var holder = HttpClient.ResponseHolder.withLastException(exception);
        assertEquals(exception, holder.lastException);
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
        var holder = HttpClient.ResponseHolder.withLastException(exception);
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
        var holder = HttpClient.ResponseHolder.withLastException(exception);
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
                .containsExactly(DEFAULT_MAX_CONN_TOTAL, DEFAULT_MAX_CONN_PER_ROUTE, DEFAULT_VALIDATE_CONN_AFTER_INACTIVITY);

        assertEquals(httpClient.internalHttpClient, closeableHttpClient);
        assertThat(httpClient.retryStrategy).isEqualTo(DefaultHttpRetryStrategy.INSTANCE);
    }

}
