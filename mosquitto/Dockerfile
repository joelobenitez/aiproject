# Copia la config al build en vez de bind-mount (D20/T019): el bind-mount de `passwd` desde
# Windows/Docker Desktop no preserva el permiso 600 que mosquitto exige para ese archivo —
# el proceso (usuario no-root `mosquitto` dentro del contenedor) no podia abrirlo.
FROM eclipse-mosquitto:2

COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY acl.conf /mosquitto/config/acl.conf
COPY passwd /mosquitto/config/passwd

RUN chmod 644 /mosquitto/config/mosquitto.conf /mosquitto/config/acl.conf \
    && chmod 600 /mosquitto/config/passwd \
    && chown mosquitto:mosquitto /mosquitto/config/passwd
