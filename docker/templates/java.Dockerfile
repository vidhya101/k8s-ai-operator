# syntax=docker/dockerfile:1.7
# Multi-stage Maven build -> distroless Java runtime. Adjust the `mvn` invocation / jar name if
# the project uses Gradle instead (swap builder base to gradle:8-jdk21-alpine, `gradle build`).

ARG JAVA_VERSION=21

# ---------- builder ----------
FROM maven:3.9-eclipse-temurin-${JAVA_VERSION} AS builder
WORKDIR /build
COPY pom.xml ./
RUN mvn -B -ntp dependency:go-offline
COPY src ./src
RUN mvn -B -ntp package -DskipTests \
    && mv target/*.jar target/app.jar

# ---------- runtime (distroless, non-root) ----------
FROM gcr.io/distroless/java${JAVA_VERSION}-debian12 AS runtime
WORKDIR /app
COPY --from=builder /build/target/app.jar ./app.jar

ENV PORT=8080 \
    JAVA_TOOL_OPTIONS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
EXPOSE 8080
USER nonroot

# distroless has no shell — liveness/readiness handled by Kubernetes probes hitting the app's
# own actuator/health endpoint (see k8s/app/base/deployment.yaml).

ENTRYPOINT ["java", "-jar", "app.jar"]
