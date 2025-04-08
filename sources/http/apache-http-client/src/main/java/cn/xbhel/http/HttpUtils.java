package cn.xbhel.http;

import org.apache.http.HttpResponse;
import org.apache.http.util.EntityUtils;

import java.io.IOException;
import java.util.Arrays;

public final class HttpUtils {
    private HttpUtils() {
    }

    public static void checkResponse(HttpResponse response, int... expectedStatusCodes) throws IOException {
        var statusCode = response.getStatusLine().getStatusCode();
        var match = Arrays.stream(expectedStatusCodes).anyMatch(code -> code == statusCode);
        if (!match) {
            var errorMessage = "";
            if (response.getEntity() != null) {
                errorMessage = EntityUtils.toString(response.getEntity());
            }
            throw new IOException(String.format("Unexpected status code: %s, error message: %s",
                    statusCode, errorMessage));
        }
    }
}
