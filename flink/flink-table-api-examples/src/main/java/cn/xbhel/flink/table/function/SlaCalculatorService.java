package cn.xbhel.flink.table.function;

import lombok.RequiredArgsConstructor;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.core.fs.Path;
import org.apache.flink.util.TimeUtils;

import java.sql.Timestamp;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@RequiredArgsConstructor
public class SlaCalculatorService {

    private final LocalDateTime availableLatestDataTime;
    private final Duration windowSize;


    Map<String, Tuple2<LocalDateTime, LocalDateTime>> getSlaViolationWindows(Map<String, String> sysWithSlaMap) {
        return sysWithSlaMap.entrySet()
                .stream()
                .collect(Collectors.toMap(Map.Entry::getKey, sysWithSla ->
                        calculateSlaViolationWindow(availableLatestDataTime,
                                TimeUtils.parseDuration(sysWithSla.getValue()), windowSize)));
    }

    List<Path> getPaths(Map<String, Tuple2<LocalDateTime, LocalDateTime>> windows) {
        var dates = windows.values().stream()
                .flatMap(e -> Stream.of(e.f0, e.f1))
                .map(LocalDateTime::toLocalDate)
                .toList();

        var minWindowStartDate = Collections.min(dates);
        var maxWindowEndDate = Collections.max(dates);

        var dateStrings = new ArrayList<String>();
        while (!minWindowStartDate.isAfter(maxWindowEndDate)) {
            dateStrings.add(minWindowStartDate.format(DateTimeFormatter.ISO_DATE));
            minWindowStartDate = minWindowStartDate.plusDays(1);
        }

        var basicPath = getBasicPath();
        return dateStrings.stream()
                .map(d -> new Path(String.format("%s/date=%s", basicPath, d)))
                .toList();
    }

    static boolean isInWindow(Timestamp timestamp, Tuple2<LocalDateTime, LocalDateTime> window) {
        var time = timestamp.toLocalDateTime();
        return !time.isBefore(window.f0) && time.isBefore(window.f1);
    }

    static Tuple2<LocalDateTime, LocalDateTime> calculateSlaViolationWindow(
            LocalDateTime availableLatestDataTime, Duration sla, Duration windowSize) {
        var slaDeadline = availableLatestDataTime.minus(sla.toMillis(), ChronoUnit.MILLIS);
        var alignedEnd = alignToHourWithOffset(slaDeadline, 0, TimeUnit.MINUTES);
        return Tuple2.of(alignedEnd.minus(windowSize.toMillis(), ChronoUnit.MILLIS), alignedEnd);
    }

    static LocalDateTime alignToHourWithOffset(LocalDateTime time, long offset, TimeUnit unit) {
        return time.truncatedTo(ChronoUnit.HOURS).plus(offset, unit.toChronoUnit());
    }

    String getBasicPath() {
        return "";
    }


}
