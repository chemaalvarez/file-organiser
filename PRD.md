# PRD — Organizador Inteligente de Archivos

**Estado:** Borrador  
**Fecha:** Junio 2026  
**Autor:** Chema Álvarez  

---

## 1. Resumen ejecutivo

Herramienta CLI + motor de clasificación inteligente que analiza una carpeta raíz (por defecto `~/Downloads`) con todos sus archivos y subcarpetas, y la reorganiza **in-place** siguiendo una taxonomía predefinida de dos ramas principales: **Trabajo** y **Personal**. La carpeta raíz ya puede contener una estructura `Trabajo/` y `Personal/` parcialmente construida; el sistema la detecta, la extiende y clasifica dentro de ella todo lo que quede suelto. El sistema debe poder ejecutarse repetidamente sobre cualquier carpeta y producir siempre la misma estructura coherente.

---

## 2. Problema

Los archivos personales y laborales se acumulan en carpetas de descargas, escritorios y directorios raíz sin estructura. Hay subcarpetas históricas que dan pistas sobre el contenido, pero no hay una jerarquía uniforme. El resultado es:

- Archivos duplicados o huérfanos difíciles de localizar.
- Mezcla de contextos (trabajo, personal, finanzas, salud) en el mismo nivel.
- Tiempo perdido buscando documentos.
- Imposibilidad de delegar la organización a terceros o automatizarla.

---

## 3. Objetivo

Construir un sistema que:

1. **Analice** cualquier carpeta origen recursivamente.
2. **Clasifique** cada archivo en la taxonomía correcta usando nombre, extensión, contenido y metadatos.
3. **Mueva o copie** los archivos a la estructura destino, preservando la integridad (sin borrar ni sobreescribir sin confirmación).
4. **Sea reutilizable**: al apuntar a una nueva carpeta origen, produce el mismo árbol destino.
5. **Sea auditable**: genera un log/reporte de cada decisión tomada.

---

## 4. Taxonomía destino

### 4.1 Rama Trabajo

```
Trabajo/
└── {Empresa}/
    └── {Cliente}/
        └── {Proyecto}/
            ├── Propuestas/
            ├── Contratos/
            ├── Entregables/
            ├── Facturas/
            ├── Comunicaciones/
            └── Recursos/
```

**Reglas de clasificación:**
- Si existe una subcarpeta origen con nombre de empresa conocido → se mapea directamente.
- Documentos con palabras clave como "factura", "contrato", "propuesta", "invoice", "NDA" → categoría por tipo dentro del proyecto correspondiente.
- El nombre del cliente puede inferirse del path origen o del contenido del documento.
- Si no se puede determinar empresa/cliente → va a `Trabajo/_SinClasificar/`.

### 4.2 Rama Personal

Estructura basada en la carpeta real `~/Dropbox/Personal` existente:

```
Personal/
├── Coches/
│   └── {Año Marca Modelo}/       # Ej: "2024 Toyota Corolla"
├── Colegios/
│   └── {Colegio}/
│       └── {Hijo}/
├── Compra-Venta/
├── Documentos/
│   ├── DNI/
│   ├── Pasaportes/
│   ├── Certificados/
│   │   ├── España/
│   │   ├── México/
│   │   └── USA/
│   ├── Empadronamiento/
│   ├── Migración/
│   ├── Actas de Nacimiento/
│   ├── Acta de Matrimonio/
│   ├── Carnet de conducir/
│   ├── Libro de Familia/
│   ├── Familia Numerosa/
│   ├── Seguridad Social/
│   ├── CURP/
│   ├── RFC/
│   └── Score de crédito/
├── Familiar/
│   └── {persona}/                # chema, susan, martina, alejo…
│       └── (carpetas propias de cada persona)
├── Gastos/
├── Salud/
│   ├── Análisis/
│   ├── Gimnasio/
│   ├── Médicos/
│   ├── Pruebas/
│   ├── Seguros/
│   │   └── {Año Aseguradora}/
│   └── Vacunas/
├── Viajes/
│   └── {YYYY MM Destino}/        # Ej: "2021 08 Guardamar"
├── Vivienda/
│   └── {Ciudad}/                 # Madrid | Miami | México DF | Guadalajara
│       └── {Dirección}/
└── _SinClasificar/
```

---

## 5. Estructura preexistente en la carpeta raíz

La carpeta raíz a organizar **puede contener ya** una estructura parcial creada manualmente. El sistema debe detectarla, respetarla y usarla como contexto prioritario antes de aplicar cualquier otra regla.

### 5.1 Escenario real de partida

La carpeta raíz por defecto es **`~/Downloads`**. Puede ser cualquier otra carpeta si se indica con `--root`.

```
~/Downloads/                     ← carpeta raíz (se organiza in-place)
├── Trabajo/                     ← ya existe
│   ├── ARMS/                    ← empresa conocida
│   │   ├── ClienteX/            ← cliente ya catalogado
│   │   └── (archivos sueltos)   ← hay que moverlos al nivel correcto
│   ├── OtraEmpresa/             ← empresa sin clientes definidos aún
│   └── (archivos sueltos)       ← hay que clasificarlos
├── Personal/                    ← ya existe (puede estar vacía o no)
├── factura_marzo.pdf            ← archivo suelto en raíz → hay que clasificarlo
├── contrato NDA empresa X.docx  ← ídem
└── Descargas varias/            ← carpeta sin estructura → hay que procesarla
```

### 5.2 Fase 0 — Lectura del estado actual (bootstrap)

Antes del escaneo general, el sistema realiza una **fase de bootstrap**:

```
┌──────────────────────────────────────────────────────┐
│  FASE 0: Bootstrap (lectura de estructura existente) │
│                                                      │
│  1. Detecta si existe Trabajo/ en la raíz            │
│     → Extrae lista de nombres de empresa (nivel 1)   │
│     → Por cada empresa, extrae clientes (nivel 2)    │
│     → Por cada cliente, extrae proyectos (nivel 3)   │
│                                                      │
│  2. Detecta si existe Personal/ en la raíz           │
│     → Mapea subcarpetas a categorías conocidas       │
│                                                      │
│  3. Construye un "mapa de contexto" dinámico:        │
│     { empresas: [...], clientes: {...}, proyectos: {...} }
│                                                      │
│  4. Este mapa se combina con config.yaml             │
│     (config.yaml tiene prioridad en caso de conflicto)
└──────────────────────────────────────────────────────┘
```

### 5.3 Comportamiento según el estado encontrado

| Situación en raíz | Comportamiento del sistema |
|---|---|
| `Trabajo/` existe con empresas | Usa esas empresas como catálogo base; añade las de `config.yaml` |
| `Trabajo/Empresa/Cliente/` existe | Mueve archivos relacionados directamente a ese cliente |
| `Trabajo/Empresa/` existe sin clientes | Crea `_SinCliente/` dentro de la empresa para los archivos ambiguos |
| `Trabajo/` no existe | La crea según taxonomía completa |
| `Personal/` existe con subcarpetas | Respeta las subcarpetas existentes; las mapea a la taxonomía |
| `Personal/` no existe | La crea según taxonomía completa |
| Archivos sueltos en raíz | Se clasifican con el motor de reglas y se mueven al lugar correcto |
| Carpetas sin nombre estructurado en raíz | Se procesan recursivamente como si fueran carpetas origen independientes |

### 5.4 Archivos sueltos dentro de carpetas ya estructuradas

Si dentro de `Trabajo/ARMS/` hay archivos directamente (sin pasar por cliente/proyecto), el sistema:

1. Intenta inferir a qué cliente/proyecto pertenecen por nombre o contenido.
2. Si puede, los mueve al nivel correcto dentro de `ARMS/`.
3. Si no puede, los deja en `Trabajo/ARMS/_SinClasificar/` y los marca en el log.

---

## 6. Flujo de trabajo del sistema

```
~/Downloads/
      │
      ▼
┌─────────────────────────────────────────────────┐
│  FASE 0: Bootstrap                              │
│  Lee Trabajo/ y Personal/ si ya existen.        │
│  Construye catálogo: empresas, clientes,        │
│  proyectos, categorías personales conocidas.    │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  FASE 1: Clasificación por niveles (top-down)   │
│  Procesa nivel a nivel, de lo más general a     │
│  lo más específico. Ver sección 6.2.            │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  FASE 2: Plan (dry-run)                         │
│  Lista completa de movimientos propuestos:      │
│  carpeta/archivo → destino, regla, confianza.   │
│  Agrupa por decisión para revisión rápida.      │
└────────────────────┬────────────────────────────┘
                     │  (confirmación del usuario)
                     ▼
┌─────────────────────────────────────────────────┐
│  FASE 3: Ejecución                              │
│  Mueve en bloque las carpetas clasificadas.     │
│  Mueve individualmente solo los archivos        │
│  sueltos o los de carpetas mixtas.              │
│  Crea estructura destino si no existe.          │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│  FASE 4: Log                                    │
│  JSONL append-only en .ordenar/runs/            │
│  Una entrada por carpeta o archivo movido.      │
│  Resumen final con totales y pendientes.        │
└─────────────────────────────────────────────────┘
```

---

## 7. Motor de clasificación jerárquico (top-down)

El corazón del sistema. En lugar de procesar archivo a archivo, razona primero a nivel de **carpeta**. Solo desciende al nivel de archivo cuando la carpeta es mixta o ambigua. Esto reduce drásticamente el número de decisiones y el tiempo de proceso.

### 7.1 Principio general

```
Para cada elemento en el nivel actual:
  1. ¿Es una carpeta?
     a. Evaluar si toda la carpeta pertenece a un único destino
        → SI (confianza alta): mover la carpeta entera en bloque ✓
        → NO (carpeta mixta o ambigua): descender al nivel siguiente
  2. ¿Es un archivo suelto?
     → Clasificar individualmente con el motor de reglas
     → Si hay duda: escanear contenido del archivo
```

### 7.2 Procesamiento nivel a nivel

#### Nivel 1 — Raíz de Downloads

Elementos a clasificar: todo lo que está directamente en `~/Downloads/` (excepto `.ordenar/`, `Trabajo/`, `Personal/`).

```
Para cada carpeta en raíz:
  → ¿Pertenece claramente a Trabajo? (nombre de empresa conocida, palabras clave)
      SÍ → moverla en bloque a Trabajo/
      NO → ¿Pertenece claramente a Personal?
           SÍ → moverla en bloque a Personal/
           NO → marcar como mixta → procesar en Nivel 2

Para cada archivo suelto en raíz:
  → Clasificar individualmente → mover al destino correcto
```

#### Nivel 2 — Dentro de Trabajo/

Elementos a clasificar: carpetas y archivos sueltos que ya están o acaban de llegar a `Trabajo/`.

```
Para cada carpeta en Trabajo/:
  → ¿Coincide con una empresa del catálogo?
      SÍ → ya está en el lugar correcto → procesar Nivel 3
      NO → ¿El nombre o contenido sugiere una empresa?
           SÍ → mover a Trabajo/{Empresa}/
           NO → mover a Trabajo/_SinClasificar/

Para cada archivo suelto en Trabajo/:
  → Inferir empresa por nombre/contenido
  → Si se puede → mover a Trabajo/{Empresa}/
  → Si no → Trabajo/_SinClasificar/
```

#### Nivel 2 — Dentro de Personal/

```
Para cada carpeta en Personal/:
  → ¿Coincide con una categoría conocida? (Salud, Casa, Dinero…)
      SÍ → ya está en el lugar correcto → procesar Nivel 3
      NO → clasificar por nombre/contenido → mover a la categoría correcta

Para cada archivo suelto en Personal/:
  → Clasificar por nombre, extensión, contenido → mover a subcategoría correcta
```

#### Nivel 3 — Dentro de Trabajo/{Empresa}/

```
Para cada carpeta en Empresa/:
  → ¿Coincide con un cliente del catálogo para esa empresa?
      SÍ → ya está en el lugar correcto → procesar Nivel 4
      NO → ¿El nombre/contenido sugiere un cliente?
           SÍ → mover a Empresa/{Cliente}/
           NO → mover a Empresa/_SinCliente/
```

#### Nivel 4 — Dentro de Trabajo/{Empresa}/{Cliente}/

```
Para cada carpeta en Cliente/:
  → ¿Es un proyecto identificable?
      SÍ → ya está en el lugar correcto → procesar Nivel 5
      NO → mover a Cliente/_SinProyecto/

Para cada archivo suelto en Cliente/:
  → Clasificar por tipo de documento (Factura, Contrato, Entregable…)
  → Mover a Cliente/{Proyecto}/{TipoDoc}/
```

#### Nivel 5 — Dentro de Proyecto/ (nivel hoja)

```
Para cada archivo:
  → Clasificar en: Propuestas / Contratos / Entregables /
                   Facturas / Comunicaciones / Recursos
  → Si es ambiguo: escanear contenido para decidir
  → Si sigue siendo ambiguo: mover a Proyecto/_SinClasificar/
```

### 7.3 Cuándo escanear el contenido de un archivo

El contenido solo se lee cuando hay duda tras aplicar nombre + extensión. Se aplica por orden de coste:

| Paso | Técnica | Coste |
|------|---------|-------|
| 1 | Nombre + extensión + ruta | Gratuito |
| 2 | Magic bytes (tipo real del archivo) | Muy bajo |
| 3 | Primeras 20 líneas / 500 palabras del texto | Bajo |
| 4 | Metadatos embebidos (EXIF, PDF metadata) | Bajo |
| 5 | LLM local (Ollama) con resumen del contenido | Alto — solo si los pasos 1–4 no resuelven |

Los archivos > 100 MB omiten el paso 3 y 5 por defecto (configurable).

### 7.4 Clasificación de carpetas: criterio de confianza

Una carpeta se mueve **en bloque** solo si supera el umbral de confianza (configurable, por defecto 0.85).

```
Confianza de una carpeta =
  (archivos que apuntan al mismo destino) / (total archivos en la carpeta)

Ejemplo:
  Carpeta "ARMS_Q4_2024/" tiene 48 archivos:
  - 45 → Trabajo/ARMS/  (confianza individual alta)
  -  3 → ambiguos
  Confianza de carpeta = 45/48 = 0.9375 → ✓ mover en bloque

  Carpeta "Varios/" tiene 30 archivos:
  - 12 → Trabajo
  - 11 → Personal/Dinero
  -  7 → ambiguos
  Confianza = 12/30 = 0.4 → ✗ carpeta mixta → descender a nivel de archivo
```

---

## 8. Reglas de clasificación (motor de reglas)

### 8.1 Prioridad de señales (archivos individuales)

| Prioridad | Señal | Ejemplo |
|-----------|-------|---------|
| 1 (mayor) | Subcarpeta origen con nombre estructurado | `/ARMS/ClienteX/...` |
| 2 | Nombre del archivo contiene entidad reconocida | `Factura_ARMS_2024.pdf` |
| 3 | Palabras clave en el nombre | `contrato`, `invoice`, `IRPF`, `seguro` |
| 4 | Extensión del archivo | `.dcm` → Salud, `.gpx` → Viajes |
| 5 | Metadatos del archivo | Fecha GPS en foto → Viajes |
| 6 (menor) | Inferencia IA sobre contenido | LLM analiza primeras líneas |

### 8.2 Diccionario de palabras clave (extracto inicial)

**Trabajo:**
- `factura`, `invoice`, `presupuesto`, `quote`, `propuesta`, `proposal`
- `contrato`, `contract`, `NDA`, `acuerdo`, `SLA`
- `entregable`, `deliverable`, `informe`, `report`
- `reunión`, `meeting`, `minuta`, `acta`

**Personal > Dinero:**
- `irpf`, `declaracion`, `hacienda`, `aeat`
- `extracto`, `nomina`, `recibo`, `transferencia`

**Personal > Salud:**
- `receta`, `analisis`, `informe medico`, `seguro medico`

**Personal > Casa:**
- `hipoteca`, `alquiler`, `escritura`, `catastro`, `luz`, `agua`, `gas`

**Personal > Documentos:**
- `dni`, `pasaporte`, `nie`, `titulo`, `certificado`, `diploma`

### 8.3 Extensiones por categoría

| Extensión | Categoría sugerida |
|-----------|-------------------|
| `.pdf`, `.docx`, `.xlsx` | Según nombre/contenido |
| `.jpg`, `.png`, `.heic` | Fotos (Personal/Fotos o Viajes) |
| `.mp4`, `.mov` | Vídeos (según contexto) |
| `.dwg`, `.sketch`, `.fig` | Trabajo/Recursos |
| `.csv`, `.json`, `.xml` | Trabajo (datos) |
| `.dcm`, `.dicom` | Personal/Salud/Historial |
| `.gpx`, `.kml` | Personal/Viajes |

---

## 9. Requisitos técnicos

### 9.1 CLI (interfaz de usuario mínima)

```bash
# Ejecutar sobre ~/Downloads (carpeta por defecto)
ordenar run

# Ejecutar sobre otra carpeta raíz
ordenar run --root ~/Documents/Archivo

# Ver el plan sin ejecutar nada (dry-run)
ordenar run --dry-run

# Dry-run sobre otra carpeta
ordenar run --root ~/Desktop --dry-run

# Modo interactivo: pregunta antes de mover cada archivo ambiguo
ordenar run --interactive

# Ver el log del último run
ordenar log --last

# Deshacer el último run
ordenar undo --last
```

### 9.2 Configuración

Archivo `config.yaml` para:
- Definir empresas conocidas (lista de nombres).
- Añadir/quitar palabras clave por categoría.
- Especificar extensiones y su mapeo.
- Configurar si se usa IA (modelo local o API).
- Definir acción sobre duplicados: `skip`, `rename`, `overwrite`.
- Definir profundidad máxima de escaneo.

### 9.3 Log de operaciones (requisito obligatorio)

Cada ejecución genera un archivo de log inmutable con la huella completa de todo lo movido. El log es **la única fuente de verdad** para auditar, revertir o reproducir cualquier operación.

#### Ubicación

El log vive dentro de la misma carpeta raíz que se organiza (por defecto `~/Downloads`):

```
~/Downloads/.ordenar/            ← carpeta oculta, nunca se mueve ni clasifica
├── runs/
│   ├── 2026-06-13_01-23-45.log.jsonl   ← un archivo por ejecución
│   └── 2026-06-14_09-10-11.log.jsonl
├── latest.log.jsonl                     ← symlink al último run
└── ordenar.db                           ← SQLite (historial acumulado)
```

La carpeta `.ordenar/` está excluida automáticamente del escaneo y nunca se toca.

#### Formato de cada entrada (JSONL — una línea por archivo)

```jsonc
{
  "ts": "2026-06-13T01:23:45.123Z",      // timestamp ISO 8601
  "run_id": "a3f2b1c4",                  // ID único del run
  "action": "move",                      // "move" | "copy" | "skip" | "error"
  "src": "/Users/chema/Descargas/Factura_ARMS_2024.pdf",
  "dst": "Trabajo/ARMS/ClienteX/Proyecto1/Facturas/Factura_ARMS_2024.pdf",
  "category": "Trabajo/Facturas",
  "rule": "keyword:factura",             // señal que disparó la clasificación
  "confidence": 0.95,                    // 1.0 si fue por regla determinista
  "sha256": "e3b0c44298fc1c149afb...",   // hash del archivo antes de mover
  "size_bytes": 204800,
  "duplicate_of": null                   // path si era duplicado exacto
}
```

#### Comportamiento del log

- **Append-only**: nunca se modifica ni borra una entrada existente.
- **Se escribe antes de mover**: si el proceso falla a mitad, el log refleja exactamente qué se hizo y qué no.
- **Errores también se registran** con `"action": "error"` y un campo `"error_msg"`.
- **Resumen al final del run**: última línea del archivo con totales.

```jsonc
{
  "ts": "2026-06-13T01:24:10.000Z",
  "run_id": "a3f2b1c4",
  "action": "summary",
  "total_files": 342,
  "moved": 318,
  "skipped": 12,
  "errors": 4,
  "unclassified": 8,
  "duration_seconds": 5.4
}
```

#### Comandos relacionados con el log

```bash
# Ver el log del último run formateado
ordenar log --last

# Ver log de un run específico
ordenar log --run a3f2b1c4

# Ver solo los errores del último run
ordenar log --last --filter action=error

# Ver solo los no clasificados
ordenar log --last --filter action=skip

# Revertir (undo) un run completo usando el log
ordenar undo --run a3f2b1c4

# Exportar el log a CSV o Markdown
ordenar log --last --format csv > movimientos.csv
ordenar log --last --format md > movimientos.md
```

### 9.4 Persistencia (SQLite)

- **Base de datos ligera** (SQLite) para almacenar el historial acumulado de todos los runs.
- Indexa por `sha256` para detección de duplicados entre runs distintos.
- Permite "deshacer" un run completo usando el log correspondiente.
- Permite aprender de correcciones manuales del usuario.

### 9.5 Motor de IA (opcional pero recomendado)

- Fallback para archivos ambiguos.
- Modelo local (Ollama / llama.cpp) para privacidad.
- Alternativa: API de OpenAI/Anthropic con modo opt-in.
- Input al modelo: nombre del archivo + primeras 500 palabras del contenido (si es texto) + path origen.
- Output esperado: categoría destino + nivel de confianza (0–1).

---

## 10. Requisitos no funcionales

| Requisito | Criterio de aceptación |
|-----------|----------------------|
| **Seguridad** | Nunca elimina archivos sin confirmación explícita |
| **Integridad** | En caso de error a mitad del proceso, el estado queda reversible |
| **Privacidad** | El contenido de los archivos no sale del equipo salvo opt-in explícito |
| **Rendimiento** | Procesa 10.000 archivos en < 60 segundos (sin IA) |
| **Idempotencia** | Ejecutar dos veces sobre la misma carpeta no genera duplicados |
| **Portabilidad** | Funciona en macOS, Linux y Windows |

---

## 11. Manejo de casos especiales

| Caso | Comportamiento |
|------|---------------|
| Archivo duplicado exacto (mismo hash) | Mueve uno, registra el duplicado en el log |
| Archivo con nombre ambiguo | Va a `_SinClasificar/` + aparece en reporte para revisión manual |
| Subcarpeta origen ya tiene estructura parcial | Se respeta como señal de contexto (prioridad 1) |
| Archivo sin extensión | Se intenta detectar tipo por magic bytes |
| `.DS_Store`, `Thumbs.db`, archivos ocultos | Se omiten por defecto (configurable) |
| Archivos > 100 MB | No se leen para clasificación por IA, solo nombre/path |

---

## 12. Stack tecnológico propuesto

| Componente | Tecnología |
|-----------|-----------|
| Lenguaje principal | Python 3.11+ |
| CLI | `Typer` + `Rich` (output bonito) |
| Clasificación reglas | Motor propio (dict + regex) |
| Clasificación IA | `ollama` / `openai` SDK |
| Base de datos | SQLite via `SQLModel` |
| Lectura de metadatos | `python-magic`, `Pillow`, `pymupdf` |
| Tests | `pytest` |
| Configuración | `PyYAML` + `Pydantic` |
| Packaging | `uv` |

---

## 13. Fases de entrega

### Fase 1 — MVP (semana 1–2)
- [ ] Bootstrap: detectar estructura `Trabajo/` y `Personal/` existente.
- [ ] Clasificación jerárquica nivel a nivel (top-down).
- [ ] Motor de reglas con palabras clave y extensiones.
- [ ] Movimiento en bloque de carpetas con confianza ≥ 0.85.
- [ ] Creación de estructura destino si no existe.
- [ ] Modo `--dry-run`.
- [ ] **Log JSONL obligatorio**: cada movimiento registrado con origen, destino, regla, confianza y hash SHA-256.
- [ ] Carpeta `.ordenar/runs/` creada automáticamente.
- [ ] Resumen al final de cada run (totales por nivel, errores, no clasificados).

### Fase 2 — Robustez (semana 3)
- [ ] Escaneo de contenido para archivos ambiguos (magic bytes + primeras líneas).
- [ ] Manejo de duplicados con hash SHA-256.
- [ ] Deshacer (undo) con base de datos SQLite.
- [ ] Configuración por `config.yaml` (empresas, umbral de confianza, palabras clave).
- [ ] Modo `--interactive` para carpetas mixtas y archivos ambiguos.

### Fase 3 — Inteligencia (semana 4)
- [ ] Integración con Ollama (LLM local) para clasificación de archivos que superan los pasos 1–4.
- [ ] Aprendizaje de correcciones manuales del usuario.
- [ ] Reporte visual con estadísticas por nivel y categoría.
- [ ] Exportación del reporte a HTML / Markdown.

### Fase 4 — Pulido (semana 5+)
- [ ] Tests unitarios e integración por nivel.
- [ ] Documentación de usuario.
- [ ] Packaging como herramienta instalable (`uv tool install`).
- [ ] Soporte multi-carpeta origen (varios `--root` en un solo run).

---

## 14. Métricas de éxito

| Métrica | Objetivo |
|---------|---------|
| Tasa de clasificación correcta | > 85% sin IA, > 95% con IA |
| Archivos en `_SinClasificar` | < 5% del total |
| Tiempo de proceso (10k archivos) | < 60 segundos |
| Satisfacción usuario (revisión manual del plan) | > 90% de decisiones aceptadas sin cambio |

---

## 15. Preguntas abiertas

1. ~~**¿Carpeta destino = misma carpeta origen?**~~ → Resuelto: in-place dentro de `~/Downloads`.
2. ~~**¿Las empresas son conocidas de antemano?**~~ → Resuelto: lista en `config.yaml` + bootstrap detecta las existentes.
3. ~~**¿Mover o copiar?**~~ → Resuelto: mover por defecto.
4. ~~**¿IA local o API?**~~ → Resuelto: Ollama local.
5. **¿Qué hacer con emails exportados** (`.eml`, `.msg`)? ¿Siguen la misma taxonomía?
6. **¿La taxonomía Personal es completamente fija** o el usuario puede añadir/quitar categorías?
7. **¿Umbral de confianza para mover en bloque** configurable por el usuario, o fijo en 0.85?
8. **¿Hay integración futura con cloud** (iCloud, Google Drive, OneDrive)?
