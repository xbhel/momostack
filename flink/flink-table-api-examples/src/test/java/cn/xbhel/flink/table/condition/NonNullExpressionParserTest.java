package cn.xbhel.flink.table.condition;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class NonNullExpressionParserTest {

    @Test
    void test_parseCondition() {
        var conditionExpression = "nonnull(task)";
        var parser = new NonNullExpressionParser<Map<String, String>>((field, e) -> e.get(field));
        assertThat(parser.isSupported(conditionExpression)).isTrue();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of())).isFalse();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of("task", "task_1"))).isTrue();
    }
}