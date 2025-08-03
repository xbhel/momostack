package cn.xbhel.flink.table.condition;

import java.util.Map;
import java.util.function.Predicate;

public record Rule<T>(String ruleExpression, Map<String, Predicate<T>> conditions) {

    public boolean isMatch(T event) {
        return this.conditions
                .values()
                .stream()
                .allMatch(condition -> condition.test(event));
    }
}
