package cn.xbhel.flink.table;

import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.core.type.TypeReference;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.JsonNode;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.node.ArrayNode;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.node.MissingNode;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.node.NullNode;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.apache.flink.util.TimeUtils;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.math.BigDecimal;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class ConfigurationSource {

    private static final String DASH = "/";
    private static final String DOT = ".";
    private static final String EMPTY = "";
    private static final String USER_HOME_SCHEMA = "~";
    private static final String CLASSPATH_SCHEMA = "classpath:";
    private static final List<String> DEFAULT_SEARCH_PATHS = List.of(
            "~/config/config.yaml",
            "./config/config.yaml",
            "classpath:config/config.yaml"
    );
    private static final String ARRAY_ITEM_FORMAT = "%s[%s]";
    private static final Pattern ARRAY_ITEM_PATTERN = Pattern.compile("^(.+)\\[(\\d+)]$");

    protected static final ObjectMapper MAPPER = new YAMLMapper().findAndRegisterModules();
    protected final JsonNode rootNode;

    protected ConfigurationSource(JsonNode rootNode) {
        this.rootNode = rootNode;
    }

    public static ConfigurationSource loadDefault() throws IOException {
        return load(getDefaultConfigPath());
    }

    public static ConfigurationSource load(Path path) throws IOException {
        try (var reader = Files.newBufferedReader(path)) {
            return new ConfigurationSource(MAPPER.readTree(reader));
        }
    }

    public static ConfigurationSource load(Map<String, ?> properties) {
        return new ConfigurationSource(fromProperties(properties));
    }

    public static ConfigurationSource load(Properties properties) {
        var propertiesMap = properties.entrySet()
                .stream()
                .collect(Collectors.toMap(
                        e -> String.valueOf(e.getKey()),
                        e -> String.valueOf(e.getValue())
                ));
        return load(propertiesMap);
    }

    public ConfigurationSource mergeWith(ConfigurationSource configurationSource) throws IOException {
        return new ConfigurationSource(MAPPER.readerForUpdating(this.rootNode)
                .readValue(configurationSource.rootNode));
    }

    public <T> T get(String configOptionName, TypeReference<T> type) {
        return getJsonNode(configOptionName).map(n -> MAPPER.convertValue(n, type)).orElse(null);
    }

    public <T> T get(String configOptionName, Class<T> clazz) {
        return getJsonNode(configOptionName).map(n -> MAPPER.convertValue(n, clazz)).orElse(null);
    }

    public <T> T getRequired(String configOptionName, Class<T> clazz) {
        return getJsonNode(configOptionName)
                .map(n -> MAPPER.convertValue(n, clazz))
                .orElseThrow(() -> new IllegalArgumentException("Missing required config: " + configOptionName));
    }

    public <T> T getRequired(String configOptionName, TypeReference<T> type) {
        return getJsonNode(configOptionName)
                .map(n -> MAPPER.convertValue(n, type))
                .orElseThrow(() -> new IllegalArgumentException("Missing required config: " + configOptionName));
    }

    public String getString(String configOptionName, String defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::textValue).orElse(defaultValue);
    }

    public String getString(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::textValue).orElse(null);
    }

    public Integer getInt(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::intValue).orElse(null);
    }

    public int getInt(String configOptionName, int defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::intValue).orElse(defaultValue);
    }

    public Long getLong(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::longValue).orElse(null);
    }

    public long getInt(String configOptionName, long defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::longValue).orElse(defaultValue);
    }

    public Float getFloat(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::floatValue).orElse(null);
    }

    public float getFloat(String configOptionName, float defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::floatValue).orElse(defaultValue);
    }

    public Double getDouble(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::doubleValue).orElse(null);
    }

    public double getDouble(String configOptionName, double defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::doubleValue).orElse(defaultValue);
    }

    public BigDecimal getDecimal(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::decimalValue).orElse(null);
    }

    public BigDecimal getDecimal(String configOptionName, BigDecimal defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::decimalValue).orElse(defaultValue);
    }

    public Boolean getBoolean(String configOptionName) {
        return getJsonNode(configOptionName).map(JsonNode::booleanValue).orElse(null);
    }

    public boolean getBoolean(String configOptionName, Boolean defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::booleanValue).orElse(defaultValue);
    }

    public Duration getDuration(String configOptionName) {
        return getDuration(configOptionName, null);
    }

    public Duration getDuration(String configOptionName, Duration defaultValue) {
        return getJsonNode(configOptionName).map(JsonNode::textValue)
                .map(TimeUtils::parseDuration).orElse(defaultValue);
    }

    public Properties toProperties() {
        var properties = new Properties();
        properties.putAll(toMap());
        return properties;
    }

    public Map<String, String> toMap() {
        var configProperties = new LinkedHashMap<String, String>();
        this.rootNode.fields().forEachRemaining(entry ->
                flattenToProperties(entry.getKey(), entry.getValue(), configProperties)
        );
        return configProperties;
    }

    Optional<JsonNode> getJsonNode(String configOptionName) {
        var node = this.rootNode.get(configOptionName);
        if (node == null) {
            // json-pointer expression
            var path = DASH + configOptionName.replace(DOT, DASH);
            node = this.rootNode.at(path);
        }
        if (node instanceof NullNode || node instanceof MissingNode) {
            return Optional.empty();
        }
        return Optional.ofNullable(node);
    }

    static Path getDefaultConfigPath() throws FileNotFoundException {
        var configPath = DEFAULT_SEARCH_PATHS
                .stream()
                .map(ConfigurationSource::normalizePath)
                .filter(path -> path != null && Files.exists(path))
                .findFirst();

        if (configPath.isEmpty()) {
            throw new FileNotFoundException(String.format(
                    "Cannot find the default configuration from the paths [%s]",
                    String.join(System.lineSeparator(), DEFAULT_SEARCH_PATHS)));
        }
        return configPath.get();
    }

    static Path normalizePath(String path) {
        if (path.startsWith(CLASSPATH_SCHEMA)) {
            var url = Thread.currentThread()
                    .getContextClassLoader()
                    .getResource(path.substring(CLASSPATH_SCHEMA.length()));
            if (url != null) {
                try {
                    return Path.of(url.toURI());
                } catch (URISyntaxException e) {
                    // do nothing
                }
            }
            return null;
        }

        if (path.startsWith(USER_HOME_SCHEMA)) {
            var userHome = System.getProperty("user.home");
            return Path.of(userHome, path.substring(USER_HOME_SCHEMA.length()));
        }

        return Path.of(path);
    }

    static void flattenToProperties(String prefix, JsonNode node, Map<String, String> configProperties) {
        if (node instanceof ArrayNode arrayNode) {
            var index = 0;
            for (var item : arrayNode) {
                flattenToProperties(String.format(ARRAY_ITEM_FORMAT, prefix, index++), item, configProperties);
            }
        } else if (node instanceof ObjectNode) {
            node.fields().forEachRemaining(entry -> flattenToProperties(
                    prefix + DOT + entry.getKey(), entry.getValue(), configProperties));
        } else {
            configProperties.put(prefix, node.asText(EMPTY));
        }
    }

    static JsonNode fromProperties(Map<String, ?> properties) {
        var root = MAPPER.createObjectNode();
        properties.forEach((key, value) -> {
            var current = root;
            var parts = key.split("\\.");
            var lastIndex = parts.length - 1;
            for (int i = 0; i < parts.length; i++) {
                var isLast = i == lastIndex;
                var propertyName = parts[i];
                var matcher = ARRAY_ITEM_PATTERN.matcher(propertyName);
                if (matcher.matches()) {
                    current = handleArrayNode(
                            current, matcher.group(1), Integer.parseInt(matcher.group(2)), value, isLast);
                } else {
                    current = handleObjectNode(current, propertyName, value, isLast);
                }
            }
        });
        return root;
    }

    static ObjectNode handleArrayNode(
            ObjectNode current, String propertyName, int index, Object value, boolean isLast) {
        ArrayNode arrayNode;
        if (current.get(propertyName) instanceof ArrayNode node) {
            arrayNode = node;
        } else {
            arrayNode = current.putArray(propertyName);
        }

        while (arrayNode.size() <= index) {
            arrayNode.addNull();
        }

        if (isLast) {
            arrayNode.set(index, MAPPER.valueToTree(value));
        } else {
            if (arrayNode.get(index) instanceof ObjectNode node) {
                current = node;
            } else {
                var objectNode = current.objectNode();
                arrayNode.set(index, objectNode);
                current = objectNode;
            }
        }

        return current;
    }

    static ObjectNode handleObjectNode(
            ObjectNode current, String propertyName, Object value, boolean isLast) {
        if (isLast) {
            current.set(propertyName, MAPPER.valueToTree(value));
        } else {
            if (current.get(propertyName) instanceof ObjectNode node) {
                current = node;
            } else {
                current = current.putObject(propertyName);
            }
        }
        return current;
    }

}
