package cn.xbhel.example.micronaut;

import io.micronaut.runtime.ApplicationConfiguration;
import io.micronaut.runtime.Micronaut;
import io.micronaut.runtime.server.EmbeddedServer;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class Application {

    public static void main(String[] args) {
        var appCtx = Micronaut.run(Application.class, args);
        var server = appCtx.getBean(EmbeddedServer.class);
        var appName = appCtx.getProperty(ApplicationConfiguration.APPLICATION_NAME, String.class);
        log.info("[{}] is running at {}", appName.orElseThrow(), server.getContextURI());
    }
    
}