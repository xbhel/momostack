package cn.xbhel.flink.table.condition;

import java.util.List;
import java.util.function.Predicate;

public interface ConditionExpressionParser<T> {
    boolean isSupported(String conditionExpression);
    Predicate<T> parseCondition(String conditionExpression);

    List<String> parseFields(String conditionExpression);

    default void ensureSupported(String parserName, String conditionExpression) {
        if(!isSupported(conditionExpression)) {
            throw new IllegalStateException(String.format(
                    "Invalid '%s' expression: '%s'", parserName, conditionExpression));
        }
    }
}
