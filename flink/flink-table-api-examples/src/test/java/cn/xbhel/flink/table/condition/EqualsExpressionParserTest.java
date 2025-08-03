package cn.xbhel.flink.table.condition;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class EqualsExpressionParserTest {

    @Test
    void test_parseCondition() {
        var conditionExpression = "task=task_1|task_2";
        var parser = new EqualsExpressionParser<Map<String, String>>((field, e) -> e.get(field));
        assertThat(parser.isSupported(conditionExpression)).isTrue();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of())).isFalse();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of("task", "task_1"))).isTrue();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of("task", "task_2"))).isTrue();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of("task", "task_3"))).isFalse();
    }

}