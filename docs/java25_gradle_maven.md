# Java 25, Maven y Gradle

Esta guía documenta el entorno Java validado en la Orange Pi 5 Plus.

## Estado validado

| Herramienta | Versión | Ruta |
|---|---:|---|
| OpenJDK | 25.0.3 | `/usr/lib/jvm/java-25-openjdk-arm64` |
| `javac` | 25.0.3 | `/usr/bin/javac` |
| Maven | 3.9.16 | `/opt/maven/apache-maven-3.9.16` |
| Gradle | 9.6.1 | `/opt/gradle/gradle-9.6.1` |
| Arquitectura | aarch64 | RK3588 |

Los binarios activos son:

```bash
which java javac mvn gradle
```

Resultado esperado:

```text
/usr/bin/java
/usr/bin/javac
/usr/local/bin/mvn
/usr/local/bin/gradle
```

## Instalación de Maven oficial

```bash
cd /tmp
curl -fL -O https://dlcdn.apache.org/maven/maven-3/3.9.16/binaries/apache-maven-3.9.16-bin.tar.gz
curl -fL -O https://dlcdn.apache.org/maven/maven-3/3.9.16/binaries/apache-maven-3.9.16-bin.tar.gz.sha512
printf '%s  apache-maven-3.9.16-bin.tar.gz\n' "$(tr -d ' \n\r' < apache-maven-3.9.16-bin.tar.gz.sha512)" | sha512sum -c -
sudo mkdir -p /opt/maven
sudo tar -xzf apache-maven-3.9.16-bin.tar.gz -C /opt/maven
sudo ln -sfn /opt/maven/apache-maven-3.9.16/bin/mvn /usr/local/bin/mvn
```

## Instalación de Gradle oficial

```bash
cd /tmp
curl -fL -O https://services.gradle.org/distributions/gradle-9.6.1-bin.zip
printf '%s  gradle-9.6.1-bin.zip\n' '9c0f7faeeb306cb14e4279a3e084ca6b596894089a0638e68a07c945a32c9e14' | sha256sum -c -
sudo mkdir -p /opt/gradle
sudo unzip -q gradle-9.6.1-bin.zip -d /opt/gradle
sudo ln -sfn /opt/gradle/gradle-9.6.1/bin/gradle /usr/local/bin/gradle
```

## Limpieza de paquetes antiguos

Ubuntu 22.04 ofrece Gradle 4.4.1 y Maven 3.6.3 por `apt`. Gradle 4.4.1 no es
compatible con Java moderno en esta placa. Si esos paquetes fueron instalados,
se pueden retirar:

```bash
sudo apt remove -y gradle libgradle-core-java libgradle-plugins-java maven
sudo apt autoremove -y
sudo apt purge -y maven groovy
```

## Verificación

```bash
java -version
javac -version
mvn -version
gradle -version
```

## Proyecto Gradle con Java 25

```bash
mkdir mi-proyecto-java25
cd mi-proyecto-java25

gradle init \
  --type java-application \
  --dsl groovy \
  --test-framework junit-jupiter \
  --package com.ejemplo \
  --project-name mi-proyecto-java25
```

En `app/build.gradle`, fijar Java 25:

```groovy
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}
```

Ejecutar:

```bash
./gradlew run
./gradlew test
```

## Prueba mínima de Gradle

```bash
mkdir -p /tmp/gradle-app/src/main/java/demo
cd /tmp/gradle-app

cat > settings.gradle <<'EOF'
pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { mavenCentral() }
}
rootProject.name = 'gradle-app'
EOF

cat > build.gradle <<'EOF'
plugins { id 'application' }
application { mainClass = 'demo.App' }
EOF

cat > src/main/java/demo/App.java <<'EOF'
package demo;
public class App {
    public static void main(String[] args) {
        System.out.println("gradle-app-ok:" + Runtime.version() + ":" + System.getProperty("os.arch"));
    }
}
EOF

gradle --no-daemon -q run
```

## Prueba mínima de Maven

```bash
mkdir -p /tmp/maven-app/src/main/java/demo
cd /tmp/maven-app

cat > pom.xml <<'EOF'
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>demo</groupId>
  <artifactId>maven-app</artifactId>
  <version>1.0.0</version>
  <properties>
    <maven.compiler.release>25</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.14.1</version>
      </plugin>
      <plugin>
        <groupId>org.codehaus.mojo</groupId>
        <artifactId>exec-maven-plugin</artifactId>
        <version>3.5.0</version>
        <configuration>
          <mainClass>demo.App</mainClass>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
EOF

cat > src/main/java/demo/App.java <<'EOF'
package demo;
public class App {
    public static void main(String[] args) {
        System.out.println("maven-app-ok:" + Runtime.version() + ":" + System.getProperty("os.arch"));
    }
}
EOF

mvn -q compile exec:java
```
