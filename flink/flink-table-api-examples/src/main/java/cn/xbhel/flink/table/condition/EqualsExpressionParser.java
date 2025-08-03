package cn.xbhel.flink.table.condition;

import lombok.RequiredArgsConstructor;
import org.apache.commons.lang3.StringUtils;

import java.util.Arrays;
import java.util.List;
import java.util.function.BiFunction;
import java.util.function.Predicate;
import java.util.stream.Collectors;

@RequiredArgsConstructor
public class EqualsExpressionParser<T> implements ConditionExpressionParser<T> {
    private static final String EQ_CONDITION_SEPARATOR = "=";
    private static final String EQ_CONDITION_VALUE_SEPARATOR = "\\|";
    private final BiFunction<String, T, Object> fieldExtractor;

    @Override
    public boolean isSupported(String conditionExpression) {
        var fieldAndValues = conditionExpression.split(EQ_CONDITION_SEPARATOR);
        return fieldAndValues.length == 2 && StringUtils.isNotBlank(fieldAndValues[0]);
    }

    @Override
    public Predicate<T> parseCondition(String conditionExpression) {
        ensureSupported("equals", conditionExpression);
        var fieldAndValues = conditionExpression.split(EQ_CONDITION_SEPARATOR);
        var fieldName = fieldAndValues[0].trim();
        var expectedValues = Arrays
                .stream(fieldAndValues[1].trim().split(EQ_CONDITION_VALUE_SEPARATOR))
                .filter(StringUtils::isNotBlank)
                .collect(Collectors.toSet());
        return event -> {
            var value = fieldExtractor.apply(fieldName, event);
            return value != null && expectedValues.contains(value.toString());
        };
    }

    @Override
    public List<String> parseFields(String conditionExpression) {
        ensureSupported("equals", conditionExpression);
        var fieldAndValues = conditionExpression.split(EQ_CONDITION_SEPARATOR);
        return List.of(fieldAndValues[0].trim());
    }
}
