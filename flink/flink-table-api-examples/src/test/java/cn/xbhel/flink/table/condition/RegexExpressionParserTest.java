package cn.xbhel.flink.table.condition;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class RegexExpressionParserTest {

    @Test
    void test_parseCondition() {
        var conditionExpression = "regex(task, \"^(?!.*_2$).*\")";
        var parser = new RegexExpressionParser<Map<String, String>>((field, e) -> e.get(field));
        assertThat(parser.isSupported(conditionExpression)).isTrue();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of("task", "task_2"))).isFalse();
        assertThat(parser.parseCondition(conditionExpression).test(Map.of("task", "task_1"))).isTrue();
    }
}