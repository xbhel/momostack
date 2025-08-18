package cn.xbhel.flink.table.condition;

import lombok.RequiredArgsConstructor;
import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.function.Predicate;

@RequiredArgsConstructor
public class RuleExpressionParser<T> {

    private static final String CONDITION_SEPARATOR = "&";
    private final List<ConditionExpressionParser<T>> conditionParsers;

    public Rule<T> parseRuleExpression(String ruleExpression) {
        return parseRuleExpression(null, ruleExpression);
    }

    public Rule<T> parseRuleExpression(String ruleName, String ruleExpression) {
        var conditionExpressions = ruleExpression.split(CONDITION_SEPARATOR);
        var definedFields = new ArrayList<String>();
        var conditions = new LinkedHashMap<String, Predicate<T>>(conditionExpressions.length);
        for (var conditionExpression : conditionExpressions) {
            conditionExpression = conditionExpression.trim();
            if (StringUtils.isEmpty(conditionExpression)) {
                continue;
            }
            var parser = findFirstConditionParser(conditionExpression);
            conditions.put(conditionExpression, parser.parseCondition(conditionExpression));
            definedFields.addAll(parser.parseFields(conditionExpression));
        }
        return new Rule<>(ruleName, ruleExpression, conditions, definedFields);
    }

    protected ConditionExpressionParser<T> findFirstConditionParser(String conditionExpression) {
        return conditionParsers.stream()
                .filter(e -> e.isSupported(conditionExpression))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException(String.format(
                        "Expression '%s' is not supported.", conditionExpression)));
    }

}
