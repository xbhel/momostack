package cn.xbhel.flink.table.condition;

import lombok.RequiredArgsConstructor;
import org.apache.flink.util.Preconditions;

import java.util.List;
import java.util.function.BiFunction;
import java.util.function.Predicate;
import java.util.regex.Pattern;

@RequiredArgsConstructor
public class RegexExpressionParser<T> implements ConditionExpressionParser<T> {

    private static final Pattern PATTERN = Pattern.compile("^regex\\(\\s*([^,]+?)\\s*,\\s*\"(.*?)\"\\s*\\)$");
    private final BiFunction<String, T, Object> fieldExtractor;

    @Override
    public boolean isSupported(String conditionExpression) {
        return PATTERN.matcher(conditionExpression).matches();
    }

    @Override
    public Predicate<T> parseCondition(String conditionExpression) {
        ensureSupported("regex", conditionExpression);

        var matcher = PATTERN.matcher(conditionExpression);
        Preconditions.checkState(matcher.matches());
        var fieldName = matcher.group(1).trim();
        var compiledPattern = Pattern.compile(matcher.group(2));

        return event -> {
            var value = fieldExtractor.apply(fieldName, event).toString();
            return compiledPattern.matcher(value).matches();
        };
    }

    @Override
    public List<String> parseFields(String conditionExpression) {
        ensureSupported("regex", conditionExpression);
        var matcher = PATTERN.matcher(conditionExpression);
        Preconditions.checkState(matcher.matches());
        return List.of(matcher.group(1).trim());
    }


}
