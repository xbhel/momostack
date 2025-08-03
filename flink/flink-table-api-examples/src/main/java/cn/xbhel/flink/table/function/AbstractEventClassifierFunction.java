package cn.xbhel.flink.table.function;

import cn.xbhel.flink.table.condition.*;
import lombok.RequiredArgsConstructor;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.table.data.RowData;
import org.apache.flink.table.types.logical.RowType;
import org.apache.flink.util.Collector;

import java.io.Serial;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;
import java.util.function.Function;
import java.util.stream.Collectors;

@RequiredArgsConstructor
public abstract class AbstractEventClassifierFunction extends ProcessFunction<RowData, RowData> {

    @Serial
    private static final long serialVersionUID = 1723284669432551554L;
    private final RowType rowType;
    private transient Map<String, Classifier> eventClassifiers;

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        var fieldExtractor = createFieldExtractor();
        this.eventClassifiers = parseEventClassifiers(new HashMap<>(),
                new RuleExpressionParser<>(List.of(
                        new NonNullExpressionParser<>(fieldExtractor),
                        new EqualsExpressionParser<>(fieldExtractor),
                        new RegexExpressionParser<>(fieldExtractor)
                )));
    }

    @Override
    public void processElement(RowData event,
                               ProcessFunction<RowData, RowData>.Context ctx,
                               Collector<RowData> out) throws Exception {
        for (Map.Entry<String, Classifier> entry : this.eventClassifiers.entrySet()) {
            var classifier = entry.getValue();
            if (classifier.anyMatch(event)) {
                processClassifierEvent(entry.getKey(), event, ctx, out);
            } else {
                processUnknownEvent(event, ctx, out);
            }
        }
    }

    protected abstract void processClassifierEvent(String eventName,
                                                   RowData event,
                                                   ProcessFunction<RowData, RowData>.Context ctx,
                                                   Collector<RowData> out) throws Exception;

    protected abstract void processUnknownEvent(RowData event,
                                                ProcessFunction<RowData, RowData>.Context ctx,
                                                Collector<RowData> out) throws Exception;

    @SuppressWarnings("unchecked")
    Map<String, Classifier> parseEventClassifiers(Map<String, Object> conf, RuleExpressionParser<RowData> parser) {
        return conf.entrySet().stream().map(entry -> {
            var ruleDefinitions = (Map<String, Object>) entry.getValue();
            var rules = ((Map<String, String>) ruleDefinitions.get("rules")).values().stream()
                    .map(parser::parseRuleExpression)
                    .toList();
            return new Classifier(entry.getKey(), rules);
        }).collect(Collectors.toMap(Classifier::eventName, Function.identity()));
    }

    BiFunction<String, RowData, Object> createFieldExtractor() {
        Map<String, RowData.FieldGetter> fieldGetterMap = rowType.getFields().stream()
                .collect(Collectors.toMap(RowType.RowField::getName, rowField ->
                        RowData.createFieldGetter(rowField.getType(),
                                rowType.getFieldIndex(rowField.getName()))));
        return (fieldName, row) -> fieldGetterMap.get(fieldName).getFieldOrNull(row);
    }

    record Classifier(String eventName, List<Rule<RowData>> rules) {
        boolean allMatch(RowData event) {
            return this.rules.stream().allMatch(r -> r.isMatch(event));
        }

        boolean anyMatch(RowData event) {
            return this.rules.stream().anyMatch(r -> r.isMatch(event));
        }
    }
}