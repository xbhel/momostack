package cn.xbhel.util;

public final class ThreadUtils {

    private ThreadUtils() {}

    public static void silentSleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while sleeping", e);
        }
    }
    
}
