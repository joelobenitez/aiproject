# Caso de Uso — Fase 1

> Definido en Session 02 — 2026-06-04
> Estado: DEFINIDO — listo para spec SDD

---

## Nombre

**Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude**

---

## El Problema que Resolvemos

Los sistemas de monitoreo industriales tradicionales detectan cuando una variable supera un umbral
y emiten una alerta generica ("TEMPERATURA ALTA — 87°C"). El operador recibe la alerta pero no
sabe si es urgente, cual es la causa probable ni que debe hacer.

Deloitte cuantifica el costo del problema: el downtime no planificado le cuesta a la industria
manufacturera $50 mil millones por ano. Las estrategias tradicionales (reactiva y preventiva)
desperdician entre el 5% y 20% de la capacidad productiva de una planta.

**El gap que cubrimos:** la brecha entre "deteccion de anomalia" y "diagnostico accionable".

---

## Solucion

Cuando el sistema detecta una anomalia en los datos de un motor, Claude recibe el contexto
completo (valores actuales, tendencia de las ultimas 24hs, metadata del equipo) y genera
un diagnostico en lenguaje natural con:

- Causa probable (con razonamiento explicito)
- Nivel de urgencia (ALTA / MEDIA / BAJA)
- Accion recomendada concreta
- Nivel de confianza del diagnostico

Esto reemplaza el requisito de Deloitte de 20-30 fallas historicas registradas por tipo
para arrancar el analisis de causa raiz — Claude razona sin necesitar ese historial previo.

---

## Activo Simulado

**Motor industrial de induccion** — presente en casi cualquier industria
(bombas, compresores, ventiladores, transportadores, maquinas-herramienta)

Elegido porque:
- Variables bien definidas y comprensibles
- Tipos de falla conocidos y documentados
- Aplica a manufactura, agua, energia, HVAC, agro
- Facilmente escalable a otros activos (mismo patron, distintas variables)

---

## Variables del Emulador

| Variable | Unidad | Rango Normal | Trigger Alerta | Trigger Critico |
|----------|--------|-------------|----------------|-----------------|
| Temperatura | °C | 20 - 75 | > 75 | > 90 |
| Corriente | A | 10 - 20 | > 22 | > 26 |
| Vibracion | mm/s | 0 - 4.5 | > 4.5 | > 7.1 |
| Horas operacion | h | — | — | — |

Referencias de vibracion: ISO 10816 (clase II: maquinas medianas)
- <= 2.3 mm/s: BUENO
- 2.3 - 4.5 mm/s: ACEPTABLE
- 4.5 - 7.1 mm/s: ALERTA
- > 7.1 mm/s: CRITICO

---

## Escenarios de Falla que el Emulador Simula

### Escenario A — Degradacion del sistema de refrigeracion
- Temperatura sube gradualmente (+12°C en 3 horas)
- Corriente se mantiene estable
- Vibracion normal
- **Diagnostico esperado:** filtro obstruido o ventilador con caudal reducido

### Escenario B — Sobrecarga mecanica
- Temperatura sube moderadamente
- Corriente aumenta por encima del nominal
- Vibracion levemente elevada
- **Diagnostico esperado:** carga mecanica excesiva, posible obstruccion o desalineamiento

### Escenario C — Falla de rodamiento (incipiente)
- Temperatura sube lentamente
- Corriente levemente elevada
- Vibracion aumenta progresivamente (pasar de zona ACEPTABLE a ALERTA)
- **Diagnostico esperado:** desgaste de rodamiento, planificar reemplazo preventivo

### Escenario D — Operacion normal con variacion
- Fluctuaciones dentro de rangos normales
- El sistema NO debe generar alertas innecesarias (reducir falsos positivos)

---

## Flujo del Caso de Uso

```
1. Script Python emula motor y publica cada 30 segundos via MQTT
   → topico: demo/planta1/linea_a/motor_001/{variable}

2. Node-RED suscribe, normaliza y escribe en InfluxDB + MySQL

3. Node-RED (o n8n) evalua regla: ¿algun valor fuera de umbral?
   SI → dispara workflow en n8n

4. n8n consulta:
   - Ultimas 24hs del motor en InfluxDB
   - Metadata del equipo en MySQL (horas_op, alertas previas)
   - Umbrales configurados

5. n8n invoca Claude Agent con todo el contexto

6. Claude genera diagnostico estructurado

7. n8n:
   a. Guarda diagnostico en MySQL
   b. Envia alerta por Telegram (con diagnostico resumido)
   c. Si es CRITICO: envia email inmediato

8. Grafana muestra la serie de tiempo con anotacion de la alerta

9. Claude Agent (cron 7:00 AM):
   - Resume las alertas y diagnosticos del dia anterior
   - Genera reporte diario HTML
   - Envia por email
```

---

## Formato de Diagnostico Claude (Output Esperado)

```json
{
  "equipo": "Motor M-01 | Linea A | Planta 1",
  "timestamp_alerta": "2026-06-05T03:45:00Z",
  "variable_trigger": "temperatura",
  "valor_trigger": 87.3,
  "unidad": "C",
  "umbral_normal": 75,
  "tendencia_24h": "incremento de 12°C en las ultimas 3 horas",
  "causa_probable": "degradacion del sistema de refrigeracion (filtro obstruido o ventilador con caudal reducido)",
  "razonamiento": "El incremento de temperatura sin aumento de corriente descarta sobrecarga mecanica. La curva gradual y sostenida es tipica de restriccion de flujo de aire, no de falla electrica.",
  "urgencia": "MEDIA",
  "accion_recomendada": "Inspeccionar circuito de enfriamiento antes de las proximas 8 horas de operacion. Revisar filtros y verificar caudal del ventilador.",
  "confianza": "ALTA",
  "proxima_revision_recomendada": "8 horas"
}
```

---

## Criterios de Exito — Fase 1

| Criterio | Metrica |
|---------|---------|
| Datos fluyen end-to-end | Script → MQTT → InfluxDB en < 5 segundos |
| Anomalia detectada | Alerta generada en < 60 segundos desde evento |
| Diagnostico generado | Claude responde en < 10 segundos |
| Diagnostico coherente | Causa probable alineada con escenario simulado |
| Sin falsos positivos | Operacion normal no genera alertas |
| Telegram funciona | Alerta llega al bot en < 90 segundos del evento |
| Grafana muestra datos | Dashboard actualizado en tiempo real |

---

## Lo que Este Caso de Uso NO Incluye (Fases Posteriores)

- Conexion a hardware real (RUT956 + sensores RS485)
- Modelos ML entrenados (Isolation Forest, LSTM)
- Multi-equipo / multi-planta
- Interfaz de configuracion de umbrales (UI)
- Feedback loop para reentrenamiento de modelos
- Integracion con ERP/CMMS para ordenes de trabajo automaticas
