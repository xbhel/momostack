package cn.xbhel.flink.table.condition;

import java.util.function.Predicate;

public interface ConditionExpressionParser<T> {
    boolean isSupported(String conditionExpression);
    Predicate<T> parseCondition(String conditionExpression);

    default void ensureSupported(String parserName, String conditionExpression) {
        if(!isSupported(conditionExpression)) {
            throw new IllegalStateException(String.format(
                    "Invalid '%s' expression: '%s'", parserName, conditionExpression));
        }
    }
}
