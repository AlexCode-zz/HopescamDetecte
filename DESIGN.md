# HopeScan — Plan de diseño (frontend-design skill)

## Sujeto, audiencia y trabajo principal

- **Sujeto:** HopeScan, herramienta de apoyo a la detección temprana de cáncer de mama por ultrasonido mamario (B-mode). El contexto es El Salvador (DUI, hospitales locales, español).
- **Audiencia:** personal de clínicas/consultorios y pacientes que acuden a una valoración de mama. No son radiólogos: necesitan lenguaje claro, no jerga de modelo de ML.
- **Trabajo principal:** guiar a una persona por un flujo de 3 pasos (datos del paciente → imagen de ecografía → resultado seguro) y, cuando el estado lo permite, entregar un reporte imprimible. **Regla de seguridad innegociable:** nunca se muestra una clase, un porcentaje ni un Grad-CAM a menos que el estado sea `valida_confiable`.

## Pase 1 — Plan de diseño

### Color

Base neutra cálida pero distinta del cliché "crema #F4F1EA + terracotta #D97757" (tell de IA). El ultrasonido es una imagen en escala de grises; la UI debe acompañarla sin competir.

| Token | Hex | Uso |
|-------|-----|-----|
| `paper` | `#FDF9F5` | fondo de página (blanco papel cálido muy sutil) |
| `surface` | `#FFFFFF` | tarjetas y contenedores |
| `ink` | `#1A181A` | texto principal (casi negro, no #0B0B0B) |
| `muted` | `#6E6670` | texto secundario, leyendas |
| `border` | `#E7E4E0` | divisores estructurales |
| `primary` | `#7C3AED` | violeta profundo: acciones de marca, estado confiable (médico, autoritario, no el rosa cliché del cáncer de mama) |
| `primary-hover` | `#6D28D9` | estado pulsado del primario |
| `attention` | `#D97706` | ámbar: no concluyente, pendiente de revisión |
| `success` | `#047857` | verde esmeralda: benigno / sin hallazgos |
| `danger` | `#B91C1C` | rojo: hallazgo sospechoso (solo cuando `valida_confiable`) |

**Gasto de boldness:** un solo elemento colorido con fuerza (el violeta de marca en botones primarios y badges de estado). Todo lo alrededor queda quieto: neutros, bordes finos, sombra casi nula.

### Tipografía

Dos familias, claramente distintas, ninguna por defecto genérica:

- **Display / encabezados:** `Source Serif 4` (serif). Autoridad médica, lectura serena en español. Se usa solo para títulos de página y secciones, nunca para cuerpo.
- **Cuerpo / UI:** `Inter` (sans). Muy legible en pantallas, buena cobertura de acentos españoles (á, é, í, ó, ú, ü, ñ). Se usa para todo el cuerpo, etiquetas, botones, tablas.

Escala tipográfica (Elementos del Estilo Tipográfico, intencional):

- H1 página: 2.5rem / 2.8, peso 700, tracking normal
- H2 sección: 1.5rem / 2, peso 600
- H3 tarjeta: 1.125rem / 1.6, peso 600
- Cuerpo: 1rem / 1.7, peso 400
- Pequeño / leyenda: 0.875rem / 1.5, peso 400, color `muted`

Longitud de línea: cuerpo < 75 caracteres; serif ligeramente más amplio. Alineación: siempre a la izquierda (español LTR), nunca centrado en bloques de texto largo. No hay "eyebrow" en mayúsculas con tracking, ni "WORD — fragment", ni punto medio entre metas.

### Layout

Concepto: "una página, un flujo". Todo ocurre en una sola columna principal con un héroe centrado solo en la entrada; el análisis se despliega en dos columnas (imagen | resultado) solo en desktop, apilado en móvil. No hay "SaaS-card kit": nada tiene el mismo border-radius ni la misma sombra genérica; los contenedores se distinguen por borde, fondo y padding según su jerarquía.

ASCII — entrada (héroe centrado, una sola pieza memorable):

```
        [ HopeScan — ecografía mamaria ]
              apoyo a la detección temprana

    [ Datos del paciente ]   [ Imagen ]   [ Resultado ]   ← progreso lineal (1 → 2 → 3)
```

ASCII — resultado confiable (dos columnas en desktop):

```
┌─────────────────────┬──────────────────────────────────┐
│  Imagen analizada   │  Resultado                       │
│  (escala de grises) │                                    │
│                     │  [badge: BENIGNO / MALIGNO /      │
│  [Grad-CAM opcional │   NORMAL, solo si confiable]      │
│   debajo de la img] │                                    │
│                     │  Confianza calibrada · margen      │
│                     │  Distribución de probabilidades    │
│                     │  ¿Por qué esta decisión?           │
│                     │  [Descargar reporte HTML]          │
└─────────────────────┴──────────────────────────────────┐
                    Aviso médico (ancho completo)          │
└──────────────────────────────────────────────────────────┘
```

### Principios (qué hace única esta página)

1. **Seguridad primero:** la clase, la confianza y el Grad-CAM solo aparecen si `status == valida_confiable`. Los estados no concluyente e inválido ocupan el mismo visual peso que el confiable, sin empujar a un diagnóstico.
2. **Autoridad serena:** violeta de marca como único color fuerte; fondos neutros, bordes finos, sin sombras blandas genéricas en cada tarjeta.
3. **Imagen médica protagonista:** la ecografía en escala de grises tiene el espacio más grande y el borde más limpio; el Grad-CAM se presenta como explicación, nunca como lesión.
4. **Progreso lineal real:** los marcadores 1 → 2 → 3 son una secuencia genuina (paciente, imagen, resultado), por eso tienen sentido.
5. **Español claro:** nombres de campos por lo que el usuario entiende ("Nombres", "DUI", "Edad"), no por cómo está construido el sistema ("user_input", "record_id").
6. **Sin decoration por decoration:** bordes, reglas y numeración solo cuando codifican información (paso del flujo, estado de seguridad).

## Pase 2 — Revisión contra el brief

| Riesgo por defecto | ¿Aparece en el plan? | Decisión |
|---|---|---|
| Fondo crema #F4F1EA + terracotta #D97757 | No | Fondo `#FDF9F5` + violeta `#7C3AED`; evito la combinación cliché de Claude/IA |
| Fondo negro + accent verde ácido | No | Fondo cálido claro, acento violeta y ámbar |
| Broadsheet con reglas de pelo y columnas densas | No | Una columna principal, dos columnas solo en resultado, reglas estructurales escasas |
| SaaS-card kit (mismo radio, misma sombra en todo) | No | Cada contenedor se distingue por función; sombra casi nula, bordes finos |
| Eyebrow en MAYÚSCULAS con tracking | No | Ninguna |
| Metas unidas con punto medio | No | Ninguna |
| "WORD — fragment" con guion espaciado | No | Ninguna |
| Monospace para datos pequeños | No | Inter en todo el cuerpo |
| "→" al final de botones | No | Botones con verbo exacto ("Guardar y continuar", "Analizar con IA") |
| Fade-and-slide en cada sección + hover en cada tarjeta | No | Una sola transición de entrada al cargar la página; hover sutil solo en botones |
| Mostrar confianza aunque el estado no sea confiable | No | Prohibido por contrato del proyecto; respetado en el diseño |

El plan pasa la revisión: ninguna parte lee como el genérico que yo produciría para cualquier página similar. Cada elección se justifica por el sujeto (ultrasonido en grises, entorno médico de El Salvador, regla de seguridad OOD).

## Pase 3 — Build (siguiente paso)

- Backend: FastAPI en `api/` que expone la lógica pura de `src/hopescan/` (análisis OOD, paciente, búsqueda, chat RAG, estado del modelo).
- Frontend: React + Vite + Tailwind CSS en `frontend/` siguiendo este plan.
- Se conserva `app.py` (Streamlit) sin tocar para no romper los tests existentes; el frontend React es la nueva UI principal.