package cn.xbhel.flink.udf;

import java.io.Serial;
import java.time.Duration;
import java.util.Collections;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.metrics.Counter;
import org.apache.flink.metrics.ThreadSafeSimpleCounter;
import org.apache.flink.shaded.netty4.io.netty.util.concurrent.DefaultThreadFactory;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.functions.async.RichAsyncFunction;
import org.apache.flink.util.function.SerializableSupplier;

import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public abstract class AbstractAsyncFunction<IN, OUT> extends RichAsyncFunction<IN, OUT> {

    @Serial
    private static final long serialVersionUID = 1954155896213202242L;

    /**
     * The number of tasks in the same taskManager
     */
    static int counter = 0;
    /**
     * The thread pool for async execution, the tasks in the same taskManager share
     * a threadPool
     */
    static ExecutorService executorService;

    @Setter
    private int threadNum = Math.max(1, Runtime.getRuntime().availableProcessors() * 2);
    @Setter
    private Duration terminationTimeout = Duration.ofMinutes(1);
    @Setter
    private boolean logFailureOnly = false;
    @Setter
    private SerializableSupplier<ExecutorService> executorServiceFactory;

    transient Counter errorCounter;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        // Singleton ExecutorService
        synchronized (AbstractAsyncFunction.class) {
            if (counter == 0) {
                executorService = Optional.ofNullable(executorServiceFactory)
                        .map(SerializableSupplier::get)
                        .orElseGet(() -> Executors.newFixedThreadPool(threadNum,
                                new DefaultThreadFactory("asyncThreadPool")));
            }
            counter++;
        }

        this.errorCounter = getRuntimeContext().getMetricGroup()
                .counter("numRecordsError", new ThreadSafeSimpleCounter());
    }

    protected abstract OUT invoke(IN input) throws Exception;

    @Override
    public void asyncInvoke(IN input, ResultFuture<OUT> resultFuture) throws Exception {
        try {
            CompletableFuture.<Tuple2<OUT, Throwable>>supplyAsync(() -> {
                try {
                    return Tuple2.of(invoke(input), null);
                } catch (Exception exception) {
                    // hold the exception instead of throw it in order to avoid the error is wrapped
                    // to CompletionException by CompletableFuture.
                    return Tuple2.of(null, exception);
                }
            }, executorService).whenComplete((result, ex) -> {
                var error = ex;
                // the result may be null (such as the executorService shutdown/crash)
                if (result != null) {
                    // use f1 != null because the invoke(input) may return null.
                    if (result.f1 == null) {
                        onSuccess(input, result.f0, resultFuture);
                        return;
                    }
                    error = result.f1;
                }

                errorCounter.inc();
                onError(input, error, resultFuture);
            });
        } catch (Exception exception) {
            errorCounter.inc();
            onError(input, exception, resultFuture);
        }
    }

    protected void onSuccess(IN input, OUT result, ResultFuture<OUT> resultFuture) {
        log.debug("Successfully executed [{}].", input);
        resultFuture.complete(Collections.singletonList(result));
    }

    protected void onError(IN input, Throwable error, ResultFuture<OUT> resultFuture) {
        log.error("Failed to execute [{}].", input, error);
        if (logFailureOnly) {
            resultFuture.complete(Collections.emptyList());
        } else {
            resultFuture.completeExceptionally(error);
        }
    }

    @Override
    public void timeout(IN input, ResultFuture<OUT> resultFuture) throws Exception {
        errorCounter.inc();
        onError(input, new TimeoutException("Async function call has timed out."), resultFuture);
    }

    @Override
    public void close() throws Exception {
        super.close();
        synchronized (AbstractAsyncFunction.class) {
            counter--;
            if (counter == 0) {
                gracefulShutdown();
            }
        }
    }

    protected void gracefulShutdown() {
        // shuts down an ExecutorService in two phases, first by calling shutdown to
        // reject incoming tasks, and then calling shutdownNow
        if (executorService != null) {
            // Disable new tasks from being submitted
            executorService.shutdown();
            try {
                if (!executorService.awaitTermination(terminationTimeout.toMillis(), TimeUnit.MILLISECONDS)) {
                    executorService.shutdownNow();
                }
                // Keep waiting
                // while (!executorService.awaitTermination( // NOSONAR
                // terminationTimeout.toMillis(), TimeUnit.MILLISECONDS)) {}
            } catch (InterruptedException e) {
                // (Re-)Cancel if current thread also interrupted
                executorService.shutdownNow();
                // Preserve interrupt status
                Thread.currentThread().interrupt();
            }
        }
    }

}
