package cn.xbhel.flink.table.condition;

import lombok.RequiredArgsConstructor;
import org.apache.flink.util.Preconditions;

import java.util.List;
import java.util.function.BiFunction;
import java.util.function.Predicate;
import java.util.regex.Pattern;

@RequiredArgsConstructor
public class NonNullExpressionParser<T> implements ConditionExpressionParser<T> {

    private static final Pattern PATTERN = Pattern.compile("^nonnull\\(([^\\s()][^)]*)\\)$");
    private final BiFunction<String, T, Object> fieldExtractor;

    @Override
    public boolean isSupported(String conditionExpression) {
        return PATTERN.matcher(conditionExpression).matches();
    }

    @Override
    public Predicate<T> parseCondition(String conditionExpression) {
        ensureSupported("nonnull", conditionExpression);
        var matcher = PATTERN.matcher(conditionExpression);
        Preconditions.checkState(matcher.matches());
        var fieldName = matcher.group(1).trim();
        return event -> fieldExtractor.apply(fieldName, event) != null;
    }

    @Override
    public List<String> parseFields(String conditionExpression) {
        ensureSupported("nonnull", conditionExpression);
        var matcher = PATTERN.matcher(conditionExpression);
        Preconditions.checkState(matcher.matches());
        return List.of(matcher.group(1).trim());
    }
}
