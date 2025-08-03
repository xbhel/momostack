package cn.xbhel.flink.table.condition;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;

import static org.assertj.core.api.Assertions.assertThat;

class RuleExpressionParserTest {

    private final BiFunction<String, Map<String, Object>, Object> fieldExtractor
            = (field, e) -> e.get(field);
    private final RuleExpressionParser<Map<String, Object>> ruleExpressionParser =
            new RuleExpressionParser<>(List.of(
                    new NonNullExpressionParser<>(fieldExtractor),
                    new EqualsExpressionParser<>(fieldExtractor),
                    new RegexExpressionParser<>(fieldExtractor)
            ));

    @Test
    void test_parseRuleExpression_matched() {
        var rule = ruleExpressionParser.parseRuleExpression(
                "nonnull(start_time)&feature=loader&service=prod&regex(task,\"^(?!.*_2$).*\")");
        var match = rule.isMatch(Map.of(
                "start_time", 1, "feature", "loader", "service", "prod", "task", "task_1"));
        assertThat(match).isTrue();
    }

    @Test
    void test_parseRuleExpression_isNotMatched() {
        var rule = ruleExpressionParser.parseRuleExpression(
                "nonnull(start_time)&feature=loader&service=prod&regex(task,\"^(?!.*_2$).*\")");
        var match = rule.isMatch(Map.of(
                "start_time", 1, "feature", "loader", "service", "prod2", "task", "task_1"));
        assertThat(match).isFalse();
    }
}