//package cn.xbhel.flink.table.function;
//
//import cn.xbhel.flink.table.condition.*;
//import lombok.RequiredArgsConstructor;
//import org.apache.flink.configuration.Configuration;
//import org.apache.flink.shaded.guava30.com.google.common.io.Resources;
//import org.apache.flink.streaming.api.functions.ProcessFunction;
//import org.apache.flink.table.data.RowData;
//import org.apache.flink.table.types.logical.RowType;
//import org.apache.flink.util.Collector;
//
//import java.io.Serial;
//import java.util.HashMap;
//import java.util.List;
//import java.util.Map;
//import java.util.Optional;
//import java.util.function.BiFunction;
//import java.util.function.Function;
//import java.util.stream.Collectors;
//
//@RequiredArgsConstructor
//public abstract class AbstractEventClassifierFunction<T> extends ProcessFunction<T, T> {
//
//    @Serial
//    private static final long serialVersionUID = 1723284669432551554L;
//    public static final String DEFAULT_CONFIG_OPTION_NAME = "event.classifiers";
//
//    private final String configOptionName;
//    protected final FieldExtractor<T> fieldExtractor;
//
//    transient Map<String, Classifier<T>> eventClassifiers;
//
//    protected AbstractEventClassifierFunction(FieldExtractor<T> fieldExtractor) {
//        this(DEFAULT_CONFIG_OPTION_NAME, fieldExtractor);
//    }
//
//    protected AbstractEventClassifierFunction(String configOptionName, FieldExtractor<T> fieldExtractor) {
//        this.configOptionName = configOptionName;
//        this.fieldExtractor = fieldExtractor;
//    }
//
//
//    Map<String, Classifier<T>> parserConfiguration() {
//
//        Resources.getResource("config/config.yaml")
//
//    }
//
//    @Override
//    public void open(Configuration parameters) throws Exception {
//        super.open(parameters);
//        var fieldExtractor = createFieldExtractor();
//        var ruleExpressionParser = new RuleExpressionParser<>(List.of(
//                new NonNullExpressionParser<>(fieldExtractor),
//                new EqualsExpressionParser<>(fieldExtractor),
//                new RegexExpressionParser<>(fieldExtractor)
//        ));
//        this.eventClassifiers = parseEventClassifiers(new HashMap<>(), ruleExpressionParser);
//    }
//
//    @Override
//    public void processElement(RowData event,
//                               ProcessFunction<RowData, RowData>.Context ctx,
//                               Collector<RowData> out) throws Exception {
//        var matchedClassifiers = this.eventClassifiers
//                .entrySet()
//                .stream()
//                .filter(entry -> entry.getValue().anyMatch(event))
//                .map(Map.Entry::getKey)
//                .toList();
//
//        if (matchedClassifiers.isEmpty()) {
//            processUnknownEvent(event, ctx, out);
//        } else {
//            for (var classifier : matchedClassifiers) {
//                processClassifierEvent(classifier, event, ctx, out);
//            }
//        }
//    }
//
//    protected abstract void processClassifierEvent(String eventName,
//                                                   RowData event,
//                                                   ProcessFunction<RowData, RowData>.Context ctx,
//                                                   Collector<RowData> out) throws Exception;
//
//    protected abstract void processUnknownEvent(RowData event,
//                                                ProcessFunction<RowData, RowData>.Context ctx,
//                                                Collector<RowData> out) throws Exception;
//
//
//    BiFunction<String, RowData, Object> createFieldExtractor() {
//        Map<String, RowData.FieldGetter> fieldGetterMap = rowType.getFields().stream()
//                .collect(Collectors.toMap(RowType.RowField::getName, rowField ->
//                        RowData.createFieldGetter(rowField.getType(),
//                                rowType.getFieldIndex(rowField.getName()))));
//        return (fieldName, row) -> fieldGetterMap.get(fieldName).getFieldOrNull(row);
//    }
//
//    @SuppressWarnings("unchecked")
//    Map<String, Classifier> parseEventClassifiers(Map<String, Object> conf, RuleExpressionParser<RowData> parser) {
//        return conf.entrySet().stream().map(entry -> {
//            var ruleDefinitions = (Map<String, Object>) entry.getValue();
//            var rules = ((Map<String, String>) ruleDefinitions.get("rules")).values().stream()
//                    .map(parser::parseRuleExpression)
//                    .toList();
//            return new Classifier(entry.getKey(), rules);
//        }).collect(Collectors.toMap(Classifier::eventName, Function.identity()));
//    }
//
//    record Classifier<T>(String eventName, List<Rule<T>> rules) {
//        boolean allMatch(T event) {
//            return this.rules.stream().allMatch(r -> r.isMatch(event));
//        }
//
//        boolean anyMatch(T event) {
//            return this.rules.stream().anyMatch(r -> r.isMatch(event));
//        }
//
//        Optional<Rule<T>> firstMatchedRule(T event) {
//            return this.rules.stream().filter(r -> r.isMatch(event)).findFirst();
//        }
//    }
//}