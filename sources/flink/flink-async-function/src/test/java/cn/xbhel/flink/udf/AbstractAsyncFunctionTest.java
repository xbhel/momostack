package cn.xbhel.flink.udf;

import static org.apache.flink.streaming.api.datastream.AsyncDataStream.OutputMode.UNORDERED;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import java.io.Serial;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeoutException;

import org.apache.flink.api.common.functions.RuntimeContext;
import org.apache.flink.api.common.typeutils.base.IntSerializer;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.operators.async.AsyncWaitOperatorFactory;
import org.apache.flink.streaming.runtime.streamrecord.StreamRecord;
import org.apache.flink.streaming.util.OneInputStreamOperatorTestHarness;
import org.apache.flink.streaming.util.TestHarnessUtil;
import org.apache.flink.util.ExceptionUtils;
import org.apache.flink.util.function.SerializableFunction;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import lombok.RequiredArgsConstructor;

@ExtendWith(MockitoExtension.class)
class AbstractAsyncFunctionTest {

    @Captor
    private ArgumentCaptor<List<Integer>> resultCaptor;

    @Test
    void testSuccessfulExecution() throws Exception {
        var timeout = 10;
        var asyncFunction = new TestAsyncFunction(x -> x << 1);
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));

        try (var testHarness = new OneInputStreamOperatorTestHarness<>(
                new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED),
                IntSerializer.INSTANCE)) {
            testHarness.open();
            testHarness.processElement(new StreamRecord<>(1, 1));
            testHarness.processElement(new StreamRecord<>(2, 2));
            testHarness.processElement(new StreamRecord<>(3, 3));
            testHarness.endInput();

            var expectedOutput = new ArrayDeque<>();
            expectedOutput.add(new StreamRecord<>(2, 1));
            expectedOutput.add(new StreamRecord<>(4, 2));
            expectedOutput.add(new StreamRecord<>(6, 3));

            TestHarnessUtil.assertOutputEquals("Output with watermark was not correct.",
                    expectedOutput, testHarness.getOutput());
        }
    }

    @Test
    void testFailedExecution() throws Exception {
        var timeout = 10;
        var asyncFunction = new TestAsyncFunction(x -> {
            throw new RuntimeException("test");
        });
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));
        try (var testHarness = new OneInputStreamOperatorTestHarness<>(
                new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED),
                IntSerializer.INSTANCE)) {
            var mockEnvironment = testHarness.getEnvironment();
            mockEnvironment.setExpectedExternalFailureCause(Throwable.class);

            testHarness.open();
            // The MockEnvironment only allows an exception(one times) to be thrown from the
            // async function otherwise the test will blocked.
            // See
            // org.apache.flink.runtime.operators.testutils.MockEnvironment#failExternally
            testHarness.processElement(new StreamRecord<>(1, 1));
            testHarness.endInput();

            assertThat(mockEnvironment.getActualExternalFailureCause()).isPresent();
            assertThat(asyncFunction.errorCounter.getCount()).isEqualTo(1);
            var throwable = ExceptionUtils.findThrowable(
                    mockEnvironment.getActualExternalFailureCause().get(), RuntimeException.class);
            assertThat(throwable).isPresent();
            assertThat(throwable.get()).hasMessage("test");
        }
    }

    @Test
    void testFailedWithCompletionException() throws Exception {
        var timeout = 10;
        var asyncFunction = new TestAsyncFunction(x -> x);
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));

        var ignore = mockStatic(CompletableFuture.class, invocation -> {
            if (Objects.equals(invocation.getMethod().getName(), "supplyAsync")) {
                return CompletableFuture.failedFuture(new CompletionException(new RuntimeException("test")));
            }
            return invocation.callRealMethod();
        });

        try (ignore;
                var testHarness = new OneInputStreamOperatorTestHarness<>(
                        new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED), IntSerializer.INSTANCE)) {
            var mockEnvironment = testHarness.getEnvironment();
            mockEnvironment.setExpectedExternalFailureCause(Throwable.class);

            testHarness.open();
            testHarness.processElement(new StreamRecord<>(1, 1));
            testHarness.endInput();

            assertThat(mockEnvironment.getActualExternalFailureCause()).isPresent();
            assertThat(asyncFunction.errorCounter.getCount()).isEqualTo(1);
            var throwable = ExceptionUtils.findThrowable(
                    mockEnvironment.getActualExternalFailureCause().get(), CompletionException.class);
            assertThat(throwable).isPresent();
            assertThat(throwable.get()).hasCause(new RuntimeException("test"));
        }
    }

    @Test
    void testFailedExecutionWithLogFailureOnly() throws Exception {
        var timeout = 10;
        var asyncFunction = new TestAsyncFunction(x -> {
            throw new RuntimeException("test");
        });
        asyncFunction.setLogFailureOnly(true);
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));
        try (var testHarness = new OneInputStreamOperatorTestHarness<>(
                new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED),
                IntSerializer.INSTANCE)) {
            var mockEnvironment = testHarness.getEnvironment();
            mockEnvironment.setExpectedExternalFailureCause(Throwable.class);
            testHarness.open();

            testHarness.processElement(new StreamRecord<>(1, 1));

            testHarness.endInput();

            assertThat(mockEnvironment.getActualExternalFailureCause()).isEmpty();
            assertThat(asyncFunction.errorCounter.getCount()).isEqualTo(1);
            assertThat(testHarness.getOutput()).isEmpty();
        }

    }

    @Test
    void testTimeout() throws Exception {
        var timeout = 10L;
        final var initialTime = 0L;
        var countDownLatch = new CountDownLatch(1);
        var asyncFunction = new TestAsyncFunction(x -> {
            try {
                countDownLatch.await();
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
            return x << 1;
        });
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));

        try (var testHarness = new OneInputStreamOperatorTestHarness<>(
                new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED),
                IntSerializer.INSTANCE)) {
            var mockEnvironment = testHarness.getEnvironment();
            mockEnvironment.setExpectedExternalFailureCause(Throwable.class);

            testHarness.open();

            testHarness.processElement(new StreamRecord<>(1, initialTime));
            testHarness.setProcessingTime(initialTime + 5L);
            testHarness.processElement(new StreamRecord<>(2, initialTime + 5L));

            // trigger the timeout of the first stream record
            testHarness.setProcessingTime(initialTime + timeout + 1L);
            // allow the second async stream record to be processed
            countDownLatch.countDown();
            // wait until all async collectors in the buffer have been emitted out.
            testHarness.endInput();

            var expectedOutput = new ArrayDeque<>();
            expectedOutput.add(new StreamRecord<>(4, initialTime + 5L));

            TestHarnessUtil.assertOutputEquals(
                    "Output with watermark was not correct.", expectedOutput, testHarness.getOutput());
            assertThat(mockEnvironment.getActualExternalFailureCause()).isPresent();
            assertThat(asyncFunction.errorCounter.getCount()).isEqualTo(1);
            assertThat(ExceptionUtils.findThrowable(
                    mockEnvironment.getActualExternalFailureCause().get(), TimeoutException.class))
                    .isPresent();
        }
    }

    @Test
    void testTimeoutWithLogFailureOnly() throws Exception {
        var timeout = 10L;
        final var initialTime = 0L;
        var countDownLatch = new CountDownLatch(1);
        var asyncFunction = new TestAsyncFunction(x -> {
            try {
                countDownLatch.await();
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
            return x << 1;
        });
        asyncFunction.setLogFailureOnly(true);
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));

        try (var testHarness = new OneInputStreamOperatorTestHarness<>(
                new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED), IntSerializer.INSTANCE)) {
            var mockEnvironment = testHarness.getEnvironment();
            mockEnvironment.setExpectedExternalFailureCause(Throwable.class);

            testHarness.open();

            testHarness.processElement(new StreamRecord<>(1, initialTime));
            testHarness.setProcessingTime(initialTime + 5L);
            testHarness.processElement(new StreamRecord<>(2, initialTime + 5L));

            // trigger the timeout of the first stream record
            testHarness.setProcessingTime(initialTime + timeout + 1L);
            // allow the second async stream record to be processed
            countDownLatch.countDown();
            // wait until all async collectors in the buffer have been emitted out.
            testHarness.endInput();

            var expectedOutput = new ArrayDeque<>();
            expectedOutput.add(new StreamRecord<>(4, initialTime + 5L));

            TestHarnessUtil.assertOutputEquals(
                    "Output with watermark was not correct.", expectedOutput, testHarness.getOutput());
            assertThat(mockEnvironment.getActualExternalFailureCause()).isEmpty();
            assertThat(asyncFunction.errorCounter.getCount()).isEqualTo(1);
            assertThat(mockEnvironment.getActualExternalFailureCause()).isEmpty();
        }
    }

    @Test
    void testGracefulShutdown(@Mock ResultFuture<Integer> mockResultFuture) throws Exception {
        var asyncFunction = spy(new TestAsyncFunction(x -> {
            try {
                Thread.sleep(x * 100);
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
            return x << 1;
        }));
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));
        doReturn(mock(RuntimeContext.class, RETURNS_DEEP_STUBS)).when(asyncFunction).getRuntimeContext();
        asyncFunction.open(new Configuration());

        asyncFunction.asyncInvoke(1, mockResultFuture);
        asyncFunction.asyncInvoke(2, mockResultFuture);
        asyncFunction.asyncInvoke(4, mockResultFuture);

        asyncFunction.close();
        assertThat(AbstractAsyncFunction.executorService.isShutdown()).isTrue();
        verify(mockResultFuture, times(3)).complete(resultCaptor.capture());
        assertThat(resultCaptor.getAllValues()).containsExactlyInAnyOrder(
                List.of(2), List.of(4), List.of(8));
    }

    @Test
    void testGracefulShutdownWithTerminationTimeout(@Mock ResultFuture<Integer> mockResultFuture) throws Exception {
        var asyncFunction = spy(new TestAsyncFunction(x -> {
            try {
                Thread.sleep(x * 100);
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
            return x << 1;
        }));
        asyncFunction.setExecutorServiceFactory(() -> Executors.newFixedThreadPool(5));
        asyncFunction.setTerminationTimeout(Duration.ofMillis(300));
        doReturn(mock(RuntimeContext.class, RETURNS_DEEP_STUBS)).when(asyncFunction).getRuntimeContext();
        asyncFunction.open(new Configuration());

        asyncFunction.asyncInvoke(1, mockResultFuture);
        asyncFunction.asyncInvoke(2, mockResultFuture);
        asyncFunction.asyncInvoke(4, mockResultFuture);

        asyncFunction.close();
        assertThat(AbstractAsyncFunction.executorService.isShutdown()).isTrue();
        verify(mockResultFuture, times(2)).complete(resultCaptor.capture());
        assertThat(resultCaptor.getAllValues()).containsExactlyInAnyOrder(
                List.of(2), List.of(4));
    }

    @Test
    void testExecutionWithDefaultExecutorService() throws Exception {
        var timeout = 10;
        var asyncFunction = new TestAsyncFunction(x -> x << 1);

        try (var testHarness = new OneInputStreamOperatorTestHarness<>(
                new AsyncWaitOperatorFactory<>(asyncFunction, timeout, 2, UNORDERED),
                IntSerializer.INSTANCE)) {
            testHarness.open();
            testHarness.processElement(new StreamRecord<>(1, 1));
            testHarness.processElement(new StreamRecord<>(2, 2));
            testHarness.processElement(new StreamRecord<>(3, 3));
            testHarness.endInput();

            var expectedOutput = new ArrayDeque<>();
            expectedOutput.add(new StreamRecord<>(2, 1));
            expectedOutput.add(new StreamRecord<>(4, 2));
            expectedOutput.add(new StreamRecord<>(6, 3));

            TestHarnessUtil.assertOutputEquals("Output with watermark was not correct.",
                    expectedOutput, testHarness.getOutput());
        }
    }

    @RequiredArgsConstructor
    static class TestAsyncFunction extends AbstractAsyncFunction<Integer, Integer> {
        @Serial
        private static final long serialVersionUID = 99528203186017581L;
        private final SerializableFunction<Integer, Integer> function;

        @Override
        protected Integer invoke(Integer input) {
            return function.apply(input);
        }
    }

}