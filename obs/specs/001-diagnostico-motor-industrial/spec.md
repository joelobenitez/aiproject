# Especificacion de Feature: Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude

**Feature Branch**: `001-diagnostico-motor-industrial`

**Created**: 2026-08-29

**Status**: Draft

**Input**: Caso de uso Fase 1 (`definicion/caso_de_uso_fase1.md`): monitoreo de un motor
industrial simulado (temperatura, corriente, vibracion, horas de operacion) donde, ante una
anomalia, el sistema no solo alerta sino que genera un diagnostico en lenguaje natural con
causa probable, urgencia, accion recomendada y nivel de confianza.

> **Nota post-implementacion (2026-08-30, D9):** esta spec se escribio antes de D9 (MVP
> simplificado). El correo (Email/SMTP) se postergo a una fase posterior junto con Web
> Report — no se implemento en el MVP. Afecta: la mitad de Historia 2 que depende de
> correo, Historia 3 completa, FR-007, FR-008 y SC-006, marcados abajo como **diferido
> (D9)**. El resto de la spec (Historias 1, 2-Telegram, 4 y el resto de los FR/SC) esta
> implementado y validado en Docker con credenciales reales (ver `memory/progress.md`).
> Este divergencia ya estaba documentada en `plan.md`/`tasks.md`; esta nota la deja tambien
> en la spec para que no diverja del alcance real. Ver `memory/decisions.md` D9.

## Escenarios de Usuario y Pruebas *(mandatory)*

### Historia de Usuario 1 - Diagnostico accionable ante una anomalia (Priority: P1)

Un operador de planta recibe una alerta de anomalia en un motor. En lugar de un mensaje
generico ("TEMPERATURA ALTA — 87°C"), recibe un diagnostico en lenguaje natural: que esta
pasando, por que probablemente esta pasando, que tan urgente es, y que accion concreta
tomar. Esto le permite decidir sin tener que investigar el historial del equipo el mismo.

**Why this priority**: es el diferencial central del proyecto (ver CLAUDE.md: "la brecha
entre alerta de anomalia y diagnostico accionable"). Sin esto, el sistema es un SCADA mas.
Es el unico requisito sin el cual no hay MVP.

**Independent Test**: se puede probar de punta a punta simulando cada uno de los 4
escenarios de falla del emulador (degradacion de refrigeracion, sobrecarga mecanica, falla
de rodamiento incipiente, operacion normal) y verificando que el diagnostico generado sea
coherente con la causa simulada, sin depender de que Telegram, email o Grafana esten
funcionando.

**Acceptance Scenarios**:

1. **Given** el motor viene operando en rango normal, **When** la temperatura sube
   gradualmente +12°C en 3 horas sin que la corriente aumente, **Then** el sistema genera un
   diagnostico cuya causa probable apunta a degradacion del sistema de refrigeracion (no a
   sobrecarga mecanica), con urgencia MEDIA.
2. **Given** el motor viene operando en rango normal, **When** la corriente sube por encima
   del nominal junto con temperatura y vibracion levemente elevadas, **Then** el diagnostico
   apunta a sobrecarga mecanica (carga excesiva, obstruccion o desalineamiento).
3. **Given** el motor viene operando en rango normal, **When** la vibracion pasa
   progresivamente de la zona ACEPTABLE (2.3-4.5 mm/s) a la zona ALERTA (4.5-7.1 mm/s) con
   temperatura y corriente subiendo solo levemente, **Then** el diagnostico apunta a desgaste
   de rodamiento y recomienda planificar un reemplazo preventivo (no una intervencion de
   emergencia).
4. **Given** el motor viene operando en rango normal, **When** las variables fluctuan dentro
   de sus rangos normales (sin cruzar ningun umbral), **Then** el sistema NO genera ninguna
   alerta ni diagnostico.

---

### Historia de Usuario 2 - Notificacion inmediata por el canal operativo (Priority: P1)

Cuando se genera un diagnostico, el operador lo recibe en su telefono (no tiene que estar
frente a una pantalla de Grafana) con un resumen del diagnostico. Si la urgencia es
CRITICA, ademas llega un correo inmediato para asegurar que alguien lo vea aunque no este
mirando el telefono en ese momento.

**Why this priority**: sin notificacion activa, el diagnostico existe pero nadie actua sobre
el a tiempo — el valor del diagnostico depende de que llegue a alguien rapido. Es P1 junto
con la Historia 1 porque ambas son necesarias para que el "diagnostico accionable" sea
accionable en la practica.

**Independent Test**: se puede probar generando un diagnostico de prueba con urgencia MEDIA
y otro con urgencia CRITICA, y verificando que el primero solo llega por el canal
operativo inmediato y el segundo llega ademas por el canal de respaldo, sin depender de que
el emulador este corriendo en ese momento.

**Acceptance Scenarios**:

1. **Given** se genero un diagnostico con urgencia MEDIA o BAJA, **When** el diagnostico
   queda listo, **Then** el operador lo recibe en el canal operativo inmediato (mensajeria)
   dentro de los 90 segundos desde el evento que disparo la anomalia.
2. **Given** se genero un diagnostico con urgencia ALTA (critico), **When** el diagnostico
   queda listo, **Then** ademas del canal operativo inmediato, se envia un correo
   inmediato como respaldo. *(Diferido — D9: sin canal de correo en el MVP)*

---

### Historia de Usuario 3 - Reporte ejecutivo diario (Priority: P2) — *Diferido (D9)*

> Fuera de alcance del MVP: postergada a una fase posterior junto con Email/Web Report
> (D9). No tiene tareas en `tasks.md`. Se mantiene documentada aca como backlog, sin
> cambios al contenido original de la historia.

Un responsable de planta que no sigue las alertas en tiempo real quiere, cada manana, un
resumen de que paso el dia anterior: cuantas alertas hubo, de que equipos, cuales eran
criticas y cual fue el diagnostico de cada una.

**Why this priority**: agrega valor de gestion (visibilidad ejecutiva) pero no es
indispensable para que el sistema cumpla su promesa central de diagnostico en el momento —
por eso es P2 y no P1. Puede implementarse despues de que las Historias 1 y 2 esten
funcionando.

**Independent Test**: se puede probar generando un lote de alertas y diagnosticos de
prueba con fecha del dia anterior, y verificando que el reporte generado a la manana
siguiente los resuma correctamente, sin depender de que haya trafico de sensores en vivo
en ese momento.

**Acceptance Scenarios**:

1. **Given** hubo una o mas alertas con diagnostico el dia anterior, **When** llega la hora
   programada del reporte diario, **Then** se genera un reporte que lista cada alerta con su
   diagnostico resumido y se envia por correo.
2. **Given** no hubo ninguna alerta el dia anterior, **When** llega la hora programada del
   reporte diario, **Then** se genera igualmente un reporte indicando "sin novedades" (no se
   omite el envio).

---

### Historia de Usuario 4 - Visualizacion en tiempo real (Priority: P3)

Un operador que si esta frente a una pantalla quiere ver la serie de tiempo del motor
(temperatura, corriente, vibracion) en vivo, con las alertas marcadas sobre el grafico para
poder correlacionar visualmente el momento del evento con la lectura.

**Why this priority**: es un canal complementario (D4: Grafana ya cubre "el vivo") — no
reemplaza ni bloquea el diagnostico de Claude ni la notificacion. Es la historia de menor
prioridad porque el sistema entrega su valor central (Historias 1-2) sin necesidad de un
dashboard visual.

**Independent Test**: se puede verificar de forma aislada apuntando el dashboard a datos
historicos ya cargados, sin depender de que las demas historias esten operativas en ese
momento.

**Acceptance Scenarios**:

1. **Given** el motor esta publicando lecturas, **When** el operador abre el dashboard,
   **Then** ve la serie de tiempo actualizarse en vivo para temperatura, corriente y
   vibracion.
2. **Given** se genero una alerta para el motor, **When** el operador mira el grafico del
   periodo correspondiente, **Then** ve una marca/anotacion en el punto donde ocurrio la
   alerta.

---

### Casos Limite

- ¿Que pasa si el motor emulado deja de publicar datos (el script se detiene o pierde
  conectividad)? El sistema debe poder distinguir "no hay datos" de "todo esta normal" y no
  debe generar un diagnostico de anomalia de variable a partir de datos ausentes.
- ¿Que pasa si el servicio de diagnostico (Claude Agent) no responde a tiempo o falla la
  llamada? La alerta original (deteccion de umbral cruzado) no debe perderse aunque el
  diagnostico narrativo no se pueda generar en ese momento.
- ¿Que pasa si el mismo motor cruza el mismo umbral repetidas veces en un lapso corto (la
  lectura oscila justo alrededor del umbral)? El sistema no debe generar un diagnostico
  nuevo por cada lectura individual — debe evitar notificaciones duplicadas para el mismo
  evento de anomalia en curso.
- ¿Que pasa si dos variables distintas del mismo motor cruzan su umbral casi al mismo
  tiempo (ej. temperatura y corriente)? El diagnostico debe considerar el contexto conjunto
  de todas las variables relevantes, no solo la que disparo la deteccion.

## Requisitos *(mandatory)*

### Requisitos Funcionales

- **FR-001**: El sistema MUST recibir lecturas periodicas del motor simulado (temperatura,
  corriente, vibracion, horas de operacion acumuladas) y conservarlas para poder consultar
  su historial reciente (al menos las ultimas 24 horas).
- **FR-002**: El sistema MUST evaluar cada lectura contra los umbrales de alerta y critico
  definidos por variable (temperatura, corriente, vibracion segun ISO 10816) y detectar
  cuando una lectura los cruza.
- **FR-003**: Cuando se detecta un cruce de umbral, el sistema MUST componer el contexto de
  la anomalia (valor actual, tendencia de las ultimas 24 horas, metadata del equipo:
  horas de operacion y alertas previas) antes de pedir un diagnostico.
- **FR-004**: El sistema MUST generar, para cada anomalia detectada, un diagnostico en
  lenguaje natural que incluya: causa probable con razonamiento explicito, nivel de
  urgencia (ALTA/MEDIA/BAJA), accion recomendada concreta, y nivel de confianza del
  diagnostico.
- **FR-005**: El sistema MUST guardar cada diagnostico generado de forma persistente,
  asociado al equipo y al evento que lo origino.
- **FR-006**: El sistema MUST notificar el diagnostico por un canal operativo inmediato
  (mensajeria) dentro de los 90 segundos desde el evento que disparo la deteccion.
- **FR-007** *(Diferido — D9)*: El sistema MUST enviar ademas una notificacion por correo
  cuando la urgencia del diagnostico sea ALTA (critica), sin depender de que el operador
  este viendo el canal de mensajeria en ese momento.
- **FR-008** *(Diferido — D9)*: El sistema MUST generar, con periodicidad diaria, un
  reporte que resuma las alertas y diagnosticos del periodo anterior y enviarlo por correo,
  incluso cuando no hubo alertas en ese periodo.
- **FR-009**: El sistema MUST mostrar la serie de tiempo de las variables del motor en un
  dashboard que se actualiza en vivo, con marcas visuales en los puntos donde ocurrieron
  alertas.
- **FR-010**: El sistema MUST evitar generar diagnosticos duplicados para una misma anomalia
  en curso cuando la variable sigue oscilando alrededor del umbral en un lapso corto.
- **FR-011**: El sistema MUST NOT generar alertas ni diagnosticos cuando las variables se
  mantienen dentro de sus rangos normales (operacion normal con fluctuacion, sin falsos
  positivos).
- **FR-012**: El sistema MUST distinguir la ausencia de datos (equipo que dejo de publicar)
  de una lectura dentro de rango, y no debe generar un diagnostico de anomalia de variable a
  partir de datos ausentes.
- **FR-013**: El sistema MUST conservar la deteccion de umbral cruzado (la alerta cruda)
  incluso si la generacion del diagnostico narrativo falla o no responde a tiempo.

### Entidades Clave

- **Equipo (Motor)**: el activo monitoreado. Atributos relevantes: identificador, ubicacion
  (planta/linea), horas de operacion acumuladas, historial de alertas previas.
- **Lectura**: un valor de una variable (temperatura, corriente, vibracion) del equipo en un
  momento dado. Se acumulan en el tiempo para poder calcular tendencias.
- **Umbral**: el valor de referencia por variable que separa rango normal / alerta /
  critico. Esta definido por tipo de equipo, no por instancia individual en Fase 1.
- **Alerta**: el evento generado cuando una lectura cruza un umbral. Tiene una variable
  disparadora, un valor, y un timestamp.
- **Diagnostico**: el resultado generado para una alerta. Incluye causa probable,
  razonamiento, urgencia, accion recomendada y confianza. Se asocia 1 a 1 con la alerta que
  lo origino.
- **Reporte diario**: un resumen periodico que agrupa las alertas y diagnosticos de un
  periodo (un dia) para un consumo ejecutivo.

## Criterios de Exito *(mandatory)*

### Resultados Medibles

- **SC-001**: una lectura nueva del motor esta disponible para consulta (y por lo tanto
  para deteccion de anomalia) dentro de los 5 segundos de haber sido emitida.
- **SC-002**: ante una anomalia real, el operador recibe la notificacion con el diagnostico
  dentro de los 90 segundos desde el evento que la origino.
- **SC-003**: el diagnostico completo (causa probable, urgencia, accion, confianza) se
  genera dentro de los 10 segundos desde que se detecto la anomalia.
- **SC-004**: en el 100% de los 3 escenarios de falla simulados (degradacion de
  refrigeracion, sobrecarga mecanica, falla de rodamiento incipiente), la causa probable del
  diagnostico generado coincide con la causa simulada por el emulador.
- **SC-005**: durante operacion normal simulada (fluctuacion dentro de rango), la tasa de
  alertas generadas es cero (sin falsos positivos).
- **SC-006** *(Diferido — D9)*: el reporte ejecutivo diario esta disponible todos los dias,
  incluidos los dias sin alertas.
- **SC-007**: el dashboard en vivo refleja una lectura nueva del motor sin que el operador
  tenga que refrescar la pagina manualmente.

## Supuestos

- Fase 1 monitorea un unico motor (una planta, una linea, un equipo). Multi-equipo y
  multi-planta quedan fuera de alcance (ver `definicion/caso_de_uso_fase1.md`, seccion "Lo
  que este caso de uso NO incluye").
- Las lecturas del motor provienen de un emulador (script) y no de hardware real en esta
  fase; el sistema no distingue entre origen simulado y real a nivel de datos.
- Los umbrales de alerta y critico por variable son los ya definidos en el caso de uso
  (temperatura, corriente segun rango nominal, vibracion segun ISO 10816 clase II) y se
  configuran por tipo de equipo, no a traves de una interfaz de usuario en esta fase.
- No hay gestion de usuarios ni permisos diferenciados en Fase 1: la notificacion es
  unidireccional (solo push) hacia un canal operativo compartido.
- El idioma de los diagnosticos y reportes generados es espanol, consistente con la
  convencion de documentacion del proyecto.
- La ventana de "lapso corto" para evitar diagnosticos duplicados de una misma anomalia en
  curso se resuelve con un mecanismo de enfriamiento entre notificaciones para el mismo
  equipo y variable; el valor exacto de esa ventana se ajusta durante la implementacion sin
  impacto en el alcance de esta especificacion.
