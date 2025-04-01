package cn.xbhel;

import cn.xbhel.http.HttpClient;
import cn.xbhel.http.HttpRequest;
import lombok.extern.slf4j.Slf4j;
import org.apache.http.util.EntityUtils;

@Slf4j
public class Main {

    public static void main(String[] args) throws Exception {
        var httpClient = HttpClient.getInstance();
        try(var response = httpClient.execute(
                new HttpRequest("https://www.baidu.com/", "GET")
        )){
            log.info("status code: {}, response: {}",
                    response.getStatusLine().getStatusCode(), EntityUtils.toString(response.getEntity()));
        }
    }
}
