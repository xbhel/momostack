package cn.xbhel.http;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class ThreadUtilsTest {

    @Test
    void testSilentSleep_withPositiveDuration() {
        var sleepTime = 500;
        var startTime = System.currentTimeMillis();

        ThreadUtils.silentSleep(sleepTime);
        var elapsedTime = System.currentTimeMillis() - startTime;

        assertTrue(elapsedTime >= sleepTime,
                "Sleep duration should be at least the specified time");
    }

    @Test
    void testSilentSleep_WhenInterrupted_ShouldThrowIllegalStateException() {
        var testThread = new Thread(() -> {
            assertThrows(IllegalStateException.class,
                    () -> ThreadUtils.silentSleep(1000),
                    "Should throw IllegalStateException when interrupted");
        });

        testThread.start();
        testThread.interrupt();

        assertTrue(testThread.isInterrupted(),
                "Thread interrupt flag should be preserved");
    }

}
