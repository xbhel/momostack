# Java JDBC Abstract Template

- SQL DSL
  - [jOOQ](https://www.jooq.org/)
  - [QueryDSL](https://querydsl.com/)
  - [MyBatis Dynamic SQL](https://github.com/mybatis/mybatis-dynamic-sql)

## Annotation Processor

- [Use the Google’s auto-service library to generate processor metadata file.](https://github.com/google/auto/tree/main/service)
- [Java Annotation Processing and Creating a Builder](https://www.baeldung.com/java-annotation-processing-builder)
- [ASM](https://asm.ow2.io/)
- [Byte Buddy](https://bytebuddy.net/#/)
- [A Guide to Java bytecode manipulation with ASM](https://www.baeldung.com/java-asm)
- [A Guide to Byte Buddy](https://www.baeldung.com/byte-buddy)

### Handle serialization and deserialization based on Annotation Processor

The source-level annotation processing first appeared in Java 5. It is a handy technique for generating additional source files during the compilation stage.

The source files don’t have to be Java files — you can generate any kind of description, metadata, documentation, resources, or any other type of files, based on annotations in your source code.

Annotation processing is actively used in many ubiquitous Java libraries, for instance, to generate metaclasses in QueryDSL and JPA, to augment classes with boilerplate code in Lombok library.

An important thing to note is the limitation of the annotation processing API — it can only be used to generate new files, not to change existing ones.

The notable exception is the Lombok library which uses annotation processing as a bootstrapping mechanism to include itself into the compilation process and modify the AST via some internal compiler APIs.


BeanIntrospectionFactory<T>
Introspection<T>
BeanProperty<T, ReturnType>

- erroneously 
- so let’s separate the wheat from the chaff. 因此，让我们把好坏区分开来。