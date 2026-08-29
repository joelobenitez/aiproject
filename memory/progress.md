# Progress — aiproject

> **Ultima actualizacion:** 2026-08-29
> **Donde estamos:** fase de definicion CERRADA (D1-D4 resueltas). Spec Kit instalado
> (Session 05) pero sin usar — `constitution.md` sigue siendo el template vacio. Recien se
> adopto el metodo de memoria multisesion (D6): esta es la primera foto de `progress.md`,
> armada por migracion desde `CHECKPOINT.md`, no por trabajo nuevo de esta sesion.

---

## Estado por frente

| Frente | Estado |
|---|---|
| Definicion (arquitectura + caso de uso) | CERRADO — D1, D2, D3, D4 resueltas. Ver `memory/decisions.md` |
| Ubicacion de la carpeta de trabajo (Windows vs WSL2) | ABIERTO — sin resolver. Ver `memory/risks.md` |
| Repo git local (esta carpeta) | NO EXISTE — nunca se corrio `git init` aca |
| Spec Kit | INSTALADO (Session 05), no inicializado en contenido — falta `/speckit-constitution` |
| Contratos de datos (MQTT payload, schema InfluxDB, schema MySQL, contrato HTTP del Agent) | NO INICIADO |
| Docker Compose real | NO INICIADO — solo tabla de referencia en `definicion/arquitectura_sistema.md` |
| Memoria multi-sesion (este metodo) | RECIEN INSTALADO — 2026-08-29 |

---

## Problemas abiertos

- **Duplicacion de carpeta de trabajo:** esta carpeta (Windows/OneDrive) tiene todo el
  contenido pero no es repo git; `/home/joelo/aiproject` (WSL2) es repo git con remote pero
  esta desactualizada. Sin resolver desde Session 05. Bloquea cualquier `git init`/push y,
  con eso, `/speckit-taskstoissues` mas adelante. Detalle: `memory/risks.md`.

---

## Proximos pasos

**Foco de la proxima sesion (default):** resolver la ubicacion de la carpeta de trabajo
(punto 0) antes de tocar git o seguir con Spec Kit — es lo que bloquea el resto.

0. Resolver ubicacion de carpeta: Windows (esta) vs WSL2 `/home/joelo/aiproject`. Opciones
   sobre la mesa (sin decidir): (a) `git init` aca + remote + force-push, (b) copiar el
   contenido de aca a WSL2 y seguir ahi, (c) seguir sin decidir un tiempo mas.
1. Si se va a usar `/speckit-taskstoissues` mas adelante, inicializar git en la carpeta que
   se elija y configurar el remoto.
2. Agregar `.claude/` a `.gitignore` (recomendado por Spec Kit).
3. `/speckit-constitution` — alimentar con las convenciones de `CLAUDE.md` (idioma sin
   tildes, arquitectura por capas Node-RED=datos / n8n=orquestacion / Python=inteligencia,
   disciplina git).
4. `/speckit-specify` — usar `definicion/caso_de_uso_fase1.md` como base del "que/por que".
5. `/speckit-plan` — usar `definicion/arquitectura_sistema.md` + `memory/decisions.md`
   (D1-D4).
6. `/speckit-tasks` — derivar los contratos de datos: topicos MQTT (UNS) + payload JSON,
   schema InfluxDB, schema MySQL, contrato HTTP del Claude Agent (`/diagnose`, `/report`,
   `/health`) + prompt base + salida estructurada, Docker Compose inicial con todos los
   servicios (incluido `claude-agent`).

---

## Pendientes sueltos

- Confirmar con Joelo el "por que" completo de D5 (adoptar Spec Kit) — no quedo registrado
  mas alla de "arrancar SDD". Ver nota en `memory/decisions.md` D5.
- Definir manejo de secretos del Claude Agent (`ANTHROPIC_API_KEY` y credenciales de
  InfluxDB/MySQL) antes de escribir el `docker-compose.yml` real. Ver `memory/risks.md`.
