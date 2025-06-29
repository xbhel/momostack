package cn.xbhel.jdbc.common;

import java.util.List;

public interface JdbcTemplate<T> {

    void execute(String sql, Object... args);

    void update(T t);

    void save(T t);

    void delete(T t);

    T get(Class<T> clazz, WhereCondition whereCondition);

    List<T> list(Class<T> clazz, WhereCondition whereCondition);

} 