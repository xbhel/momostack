package cn.xbhel.flink.table.function;

import java.io.Serializable;
import java.util.function.BiFunction;

@FunctionalInterface
public interface FieldExtractor<T> extends BiFunction<String, T, Object>, Serializable {
}
