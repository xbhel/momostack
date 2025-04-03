package cn.xbhel.flink.udf;

import java.io.Serial;
import java.time.Duration;
import java.util.Collections;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.apache.flink.configuration.Configuration;
import org.apache.flink.metrics.Counter;
import org.apache.flink.metrics.ThreadSafeSimpleCounter;
import org.apache.flink.shaded.netty4.io.netty.util.concurrent.DefaultThreadFactory;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.functions.async.RichAsyncFunction;
import org.apache.flink.types.Either;
import org.apache.flink.util.function.SerializableSupplier;

import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public abstract class AbstractAsyncFunction<IN, OUT> extends RichAsyncFunction<IN, OUT> {

    @Serial
    private static final long serialVersionUID = 1954155896213202242L;
    private static final int DEFAULT_POOL_SIZE = Math.max(1, Runtime.getRuntime().availableProcessors() * 2);

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
    private Duration terminationTimeout = Duration.ofMinutes(1);
    @Setter
    private boolean logFailureOnly = false;
    @Setter
    private SerializableSupplier<ExecutorService> executorServiceFactory;

    transient Counter errorCounter;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        synchronized (AbstractAsyncFunction.class) {
            if (counter == 0) {
                executorService = Optional.ofNullable(executorServiceFactory)
                        .map(SerializableSupplier::get)
                        .orElseGet(() -> Executors.newFixedThreadPool(
                                DEFAULT_POOL_SIZE,
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
        CompletableFuture.<Either<OUT, Throwable>>supplyAsync(() -> {
            try {
                return Either.Left(invoke(input));
            } catch (Exception exception) {
                // hold the exception instead of throw it because
                return Either.Right(exception);
            }
        }, executorService).whenComplete((result, ex) -> {
            var error = ex;

            if(result != null) {
                if(result.isLeft()) {
                    onSuccess(input, result.left(), resultFuture);
                    return;
                }
                error = result.right();
            }

            errorCounter.inc();
            onError(input, error, resultFuture);
        });
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
        log.error("Failed to execute [{}] due to async function call has timed out.", input);
        errorCounter.inc();
        if (logFailureOnly) {
            resultFuture.complete(Collections.emptyList());
        } else {
            // completeExceptionally with a TimeoutException
            super.timeout(input, resultFuture);
        }
    }

    @Override
    public void close() throws Exception {
        super.close();
        // shuts down an ExecutorService in two phases, first by calling shutdown to
        // reject incoming tasks, and then calling shutdownNow
        synchronized (AbstractAsyncFunction.class) {
            counter--;
            if (counter == 0 && executorService != null) {
                try {
                    // Disable new tasks from being submitted
                    executorService.shutdown();
                    // Wait a while for existing tasks to terminate
                    if (!executorService.awaitTermination(terminationTimeout.toMillis(), TimeUnit.MILLISECONDS)) {
                        executorService.shutdownNow();
                    }
                } catch (InterruptedException interrupted) {
                    // (Re-)Cancel if current thread also interrupted
                    executorService.shutdownNow();
                    // Preserve interrupt status
                    Thread.currentThread().interrupt();
                }
            }
        }
    }

}
