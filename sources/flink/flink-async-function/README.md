# Flink Async Function

## References

- [Flink Async I/O](https://nightlies.apache.org/flink/flink-docs-master/docs/dev/datastream/operators/asyncio/)
- [Initialization of static variables in Flink](https://lists.apache.org/thread/5z8wzym6t9jp41xdymh5bx940dswtfkn)


## What is the purpose of the project?

- How to use the Async Function provided by Flink?
- How is the Async Function implemented with retry and timeout semantics?
- How to implement an asynchronous HTTP sink function in Flink using the Async Function and Apache HttpClient.

## Async Function

Sync I/O vs Async I/O:

![Sync I/O vs Async I/O](../../../docs/.assets/flink-async-io.png)

Async Function interfaces:

- AsyncFunction
- RichAsyncFunction

## Test Async Function

- [AsyncWaitOperatorTest.java](https://github.com/apache/flink/blob/master/flink-streaming-java/src/test/java/org/apache/flink/streaming/api/operators/async/AsyncWaitOperatorTest.java#L1506)

### StreamTaskMailboxTestHarness

[StreamTaskMailboxTestHarness](https://github.com/apache/flink/blob/master/flink-streaming-java/src/test/java/org/apache/flink/streaming/runtime/tasks/StreamTaskMailboxTestHarness.java) is a testing utility in Apache Flink that allows fine-grained control over the execution of a StreamTask in a unit test environment. It is particularly useful for testing Flink's mailbox model, which governs how tasks process input records and control events asynchronously. It provides direct access to the mailbox, allowing the simulation of task behavior under different execution conditions.

StreamTaskMailboxTestHarness does not automatically call open() or close(). Unlike StreamOperatorTestHarness, StreamTaskMailboxTestHarness does not manage the complete lifecycle of operators. It does not replicate the full execution of a StreamTask as it would run in a real Flink job. It is more suited for unit testing specific behaviors rather than full end-to-end task validation.

Here's a practical example demonstrating how to leverage StreamTaskMailboxTestHarness for testing Async Functions:

```java
StreamTaskMailboxTestHarnessBuilder<Integer> builder =
                new StreamTaskMailboxTestHarnessBuilder<>(
                        OneInputStreamTask::new, BasicTypeInfo.INT_TYPE_INFO)
                        .addInput(BasicTypeInfo.INT_TYPE_INFO);

try (StreamTaskMailboxTestHarness<Integer> testHarness =
        builder.setupOutputForSingletonOperatorChain(
            new AsyncWaitOperatorFactory<>(
                userFunction, timeout, capacity,
                AsyncDataStream.OutputMode.UNORDERED))
            .build()
) {
    testHarness.processElement(new StreamRecord<>(input, timestamp)); 
       
    testHarness.endInput();
    testHarness.waitForTaskCompletion();             
    assertThat(testHarness.getOutput()).isNotEmpty();
}
```
