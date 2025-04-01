package cn.xbhel.flink.function;

import cn.xbhel.http.HttpRequest;
import lombok.extern.slf4j.Slf4j;
import org.apache.flink.streaming.api.datastream.AsyncDataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.http.util.EntityUtils;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

@Slf4j
public class Application {

    public static void main(String[] args) throws Exception {
        // 同一个 taskManager 的 task 应该共享一个 threadPool
        // The tasks in the same taskManager should share a threadPool/HttpPool
        var environment = StreamExecutionEnvironment.getExecutionEnvironment();
        var streamSource = environment.fromSequence(0, 22)
                .map(x -> new HttpRequest("https://www.baidu.com/", "GET"));
        AsyncDataStream.unorderedWait(streamSource, new HttpAsyncFunction<>(
                        response -> {
                            try {
                                return EntityUtils.toString(response.getEntity());
                            } catch (IOException e) {
                                throw new IllegalStateException(e);
                            }
                        }
                ), 5, TimeUnit.MINUTES)
                .returns(String.class);
        environment.execute("async");
    }
}
