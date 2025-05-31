# Micronaut

Micronaut is a modern, JVM-based framework for building modular and testable applications in Java, Kotlin, and Groovy. It is designed for scenarios ranging from monoliths to microservices, with focus on performance and low resource usage. It is inspired by Spring, Spring Boot and Grails framework.

**Useful Links**

- [Micronaut Core](https://docs.micronaut.io/latest/guide/index.html)
- [Micronaut Validation](https://micronaut-projects.github.io/micronaut-validation/latest/guide/)
  - [Custom constraint annotation for validation](https://guides.micronaut.io/latest/micronaut-custom-validation-annotation-gradle-java.html) 
  - [Jakarta Bean Validation specification](https://beanvalidation.org/2.0/spec/)
- [Commercial Support](https://micronaut.io/support/)
- [Creating your first Micronaut application
](https://guides.micronaut.io/latest/creating-your-first-micronaut-app-maven-java.html)

**Key Features**

- Core Capabilities
    - Dependency Injection (IoC)
    - Aspect-Oriented Programming (AOP)
    - Auto-Configuration with sensible defaults

- Microservices Support
    - Distributed Configuration
    - Service Discovery
    - HTTP Routing
    - Client-Side Load Balancing

Advantages Over Traditional Frameworks(like Spring, Spring Boot and Grails)

- Fast startup time
- Reduced memory footprint
- Minimal use of reflection
- Minimal use of proxies
- No runtime bytecode generation
- Easy Unit testing

Designed For

- Serverless functions
- Android apps
- Low-memory microservices

Historically, frameworks such as Spring and Grails were not designed to run in scenarios such as serverless functions, Android apps, or low memory footprint microservices. In contrast, the Micronaut framework is designed to be suitable for all of these scenarios.

## Configurations

### Configuration properties

- Application: `io.micronaut.runtime.ApplicationConfiguration`
- Http Server: `io.micronaut.http.server.HttpServerConfiguration`

#### Retrieve Configurations

There are servals main ways to retrieve configurations in Micronaut:

1. Via ApplicationContext

```java
ApplicationContext appCtx = Micronaut.run(Application.class);
Optional<String> appName = appCtx.getProperty("micronaut.application.name", String.class);
Map<String, Object> properties = appCtx.getProperties("micronaut.application");
```

2. Via ConfigurationProperties beans

```java
ApplicationConfiguration bean = appCtx.getBean(ApplicationConfiguration.class);
```

## Dependency Injection

### Bean Introspection

- [Introspector (Java SE 17)](https://docs.oracle.com/en/java/javase/17/docs//api/java.desktop/java/beans/Introspector.html)
- [Bean Introspection](https://docs.micronaut.io/4.8.11/guide/#introspection)

## HTTP Server

### Request Binding

- [Simple Request Binding](https://docs.micronaut.io/4.8.11/guide/#binding)

> Warning: Avoid using lombok to generate code for `@Introspected` beans.
> Micronaut relies heavily on compile-time processing and introspection to manage beans and their properties. If lombok is used to generate code for these beans, it might interfere with the framework's ability to correctly process or bind the bean's properties. This could result in runtime errors or unexpected behavior, such as the inability to properly bind value to the bean.

MetricService 应该接受一个普适性的对象，而不是带有具体协议的 QueryParams(如 Http)