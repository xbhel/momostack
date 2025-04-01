package cn.xbhel.flink.function;

import cn.xbhel.http.DefaultHttpRetryStrategy;
import cn.xbhel.http.HttpClient;
import cn.xbhel.http.HttpRequest;
import cn.xbhel.http.HttpRetryStrategy;
import lombok.RequiredArgsConstructor;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.metrics.Counter;
import org.apache.flink.metrics.ThreadSafeSimpleCounter;
import org.apache.flink.streaming.api.datastream.AsyncDataStream;
import org.apache.flink.streaming.api.functions.async.AsyncRetryStrategy;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.functions.async.RichAsyncFunction;
import org.apache.flink.types.Either;
import org.apache.flink.util.function.SerializableFunction;
import org.apache.flink.util.function.SerializableSupplier;
import org.apache.http.HttpResponse;

import java.io.Serial;
import java.util.Collections;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ForkJoinPool;

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
 */
@Slf4j
@RequiredArgsConstructor
public class HttpAsyncFunction<T extends HttpRequest, R> extends RichAsyncFunction<T, R> {

    @Serial
    private static final long serialVersionUID = -1805514922755278162L;
    private static final HttpRetryStrategy RETRY_STRATEGY = new DefaultHttpRetryStrategy()
            .setFailedAtRetriesExhausted(true);

    @Setter
    private boolean logFailureOnly;
    @Setter
    private SerializableSupplier<HttpClient> httpClientFactory;
    @Setter
    private SerializableSupplier<ExecutorService> executorServiceFactory;
    private final SerializableFunction<HttpResponse, R> responseHandler;

    private transient Counter errorCounter;
    private transient HttpClient httpClient;
    private transient ExecutorService workerExecutor;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        this.httpClient = Optional.ofNullable(httpClientFactory)
                .map(SerializableSupplier::get)
                .orElseGet(() -> HttpClient.builder().retryStrategy(RETRY_STRATEGY).build());
        this.workerExecutor = Optional.ofNullable(executorServiceFactory)
                .map(SerializableSupplier::get)
                .orElseGet(ForkJoinPool::commonPool);
        this.errorCounter = getRuntimeContext().getMetricGroup()
                .counter("http_errors_total", new ThreadSafeSimpleCounter());
    }

    @Override
    public void asyncInvoke(T request, ResultFuture<R> resultFuture) {
        CompletableFuture.<Either<R, Throwable>>supplyAsync(() -> {
                    try {
                        return Either.Left(httpClient.execute(request, responseHandler));
                    } catch (Exception exception) {
                        return Either.Right(exception);
                    }
                }, workerExecutor
        ).whenCompleteAsync((result, ex) -> {
            if (result.isLeft()) {
                onSuccess(request, result.left(), resultFuture);
            } else {
                onFailure(request, result.isRight() ? result.right() : ex, resultFuture);
            }
        });
    }

    void onSuccess(T request, R result, ResultFuture<R> resultFuture) {
        log.debug("Successfully executed request [{}].", request);

        resultFuture.complete(Collections.singletonList(result));
    }

    void onFailure(T request, Throwable error, ResultFuture<R> resultFuture) {
        log.error("Failed to execute request [{}].", request, error);

        errorCounter.inc();
        if (logFailureOnly) {
            resultFuture.complete(Collections.emptyList());
        } else {
            resultFuture.completeExceptionally(error);
        }
    }

    @Override
    public void close() throws Exception {
        super.close();
        if (httpClient != null) {
            httpClient.close();
        }
        if (workerExecutor != null) {
            workerExecutor.shutdown();
        }
    }

}