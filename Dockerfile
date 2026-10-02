FROM registry.access.redhat.com/ubi9/openjdk-21-runtime:latest
COPY --chown=185 target/quarkus-app/ /deployments/
USER 185
ENV JAVA_APP_JAR=/deployments/quarkus-run.jar
