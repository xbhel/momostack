package cn.xbhel.flink.udf;

import java.io.Serial;
import java.util.Objects;
import java.util.Optional;

import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.datastream.AsyncDataStream;
import org.apache.flink.streaming.api.functions.async.AsyncRetryStrategy;
import org.apache.flink.util.function.SerializableFunction;
import org.apache.flink.util.function.SerializableSupplier;
import org.apache.http.HttpResponse;

import cn.xbhel.http.DefaultHttpRetryStrategy;
import cn.xbhel.http.HttpClient;
import cn.xbhel.http.HttpRequest;
import cn.xbhel.http.HttpRetryStrategy;
import lombok.Setter;

/**
 * How to use the retry mechanism provided by
 * {@link AsyncDataStream#unorderedWaitWithRetry} instead of the retry mechanism
 * provided by {@link HttpClient} class:
 * <ol>
 * <li>Create a class that implements the {@link HttpRetryStrategy}
 * interface.</li>
 * <li>Override the {@link HttpRetryStrategy#isRetryable} method to always
 * return false.</li>
 * <li>Override the {@link HttpRetryStrategy#failed} method to throw a specific
 * exception.</li>
 * <li>Use {@link AsyncDataStream#unorderedWaitWithRetry} with
 * {@link AsyncRetryStrategy} to
 * handle retries based on the specific exception.</li>
 * </ol>
 * 
 * @author xbhel
 */
public class AsyncHttpFunction<T extends HttpRequest, R> extends AbstractAsyncFunction<T, R> {

    @Serial
    private static final long serialVersionUID = 6198636126630226028L;

    @Setter
    private SerializableSupplier<HttpClient> httpClientFactory;
    private final SerializableFunction<HttpResponse, R> responseHandler;

    private transient HttpClient httpClient;

    public AsyncHttpFunction(SerializableFunction<HttpResponse, R> responseHandler) {
        this.responseHandler = Objects.requireNonNull(
                responseHandler, "responseHandler cannot be null");
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        this.httpClient = Optional.ofNullable(httpClientFactory)
                .map(SerializableSupplier::get)
                .orElseGet(() -> HttpClient.builder()
                        .retryStrategy(new DefaultHttpRetryStrategy()
                                .setFailedAtRetriesExhausted(true))
                        .build());
    }

    @Override
    protected R invoke(T request) throws Exception {
        return httpClient.execute(request, responseHandler);
    }

    @Override
    public void close() throws Exception {
        super.close();
        if (httpClient != null) {
            httpClient.close();
        }
    }
}
