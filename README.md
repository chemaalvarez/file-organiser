# ordenar

Organizador inteligente de archivos que clasifica `~/Downloads` (o cualquier carpeta) en una taxonomía jerárquica de **Trabajo** y **Personal**, usando un motor de reglas top-down que mueve carpetas enteras en bloque cuando tiene suficiente confianza, y desciende archivo a archivo solo cuando la carpeta es mixta o ambigua.

---

## Instalación

Requiere [uv](https://github.com/astral-sh/uv) y Python 3.11+.

```bash
git clone https://github.com/chemaalvarez/file-organiser.git
cd file-organiser

# Crear tu configuración personal (nunca sube al repo)
cp config.example.yaml config.yaml

# Instalar dependencias
uv sync

# Ejecutar directamente
uv run ordenar --help

# O instalar globalmente como herramienta
uv tool install .
ordenar --help
```

---

## Uso rápido

```bash
# Ver qué haría sin mover nada (recomendado la primera vez)
uv run ordenar run --dry-run

# Organizar ~/Downloads (confirma el plan antes de ejecutar)
uv run ordenar run

# Organizar otra carpeta
uv run ordenar run --root ~/Desktop

# Organizar sin pedir confirmación
uv run ordenar run --yes

# Ver el log del último run
uv run ordenar log --last

# Deshacer el último run
uv run ordenar undo --last
```

---

## Estructura resultante

### Trabajo

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

### Personal

```
Personal/
├── Coches/
│   └── {Año Marca Modelo}/        # "2024 Toyota Corolla", "2020 Toyota C-HR"…
├── Colegios/
│   └── {Colegio}/
│       └── {Hijo}/
├── Compra-Venta/
├── Documentos/
│   ├── DNI/
│   ├── Pasaportes/
│   ├── Certificados/
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
│   └── {persona}/                 # chema, susan, martina, alejo…
├── Gastos/
├── Salud/
│   ├── Análisis/
│   ├── Gimnasio/
│   ├── Médicos/
│   ├── Pruebas/
│   ├── Seguros/
│   └── Vacunas/
├── Viajes/
│   └── {YYYY MM Destino}/
├── Vivienda/
│   └── {Ciudad}/                  # Madrid | Miami | México DF | Guadalajara
│       └── {Dirección}/
└── _SinClasificar/
```

---

## Configuración (`config.yaml`)

El fichero `config.yaml` en la raíz del proyecto controla el comportamiento. Las opciones más importantes:

```yaml
# Carpeta raíz por defecto
root: "~/Downloads"

# Umbral de confianza para mover una carpeta entera en bloque (0.0–1.0)
# Una carpeta con el 85%+ de sus archivos apuntando al mismo destino se mueve sin descender
confidence_threshold: 0.85

# Qué hacer cuando el archivo destino ya existe: skip | rename | overwrite
on_duplicate: "rename"

# Tamaño máximo de archivo que se lee para clasificación por contenido (MB)
max_content_scan_mb: 100

# Empresas de trabajo (se usan para clasificar a Trabajo/{Empresa}/)
companies:
  - ARMS
  - MiEmpresa

# Miembros de la familia (clasifican a Personal/Familiar/{persona}/)
family_members:
  - chema
  - susan
  - martina

# Coches conocidos (clasifican a Personal/Coches/{modelo}/)
known_cars:
  - "2024 Toyota Corolla"
  - "2020 Toyota C-HR"

# Viviendas por ciudad (clasifican a Personal/Vivienda/{ciudad}/)
known_homes:
  Madrid:
    - "Dalia 66"
    - "Pensamiento 23"
  Miami:
    - "12535 NE Miami PL"
```

---

## Cómo clasifica cada archivo

El motor aplica estas señales en orden de prioridad, parando en la primera que resuelve el destino:

| # | Señal | Ejemplo |
|---|-------|---------|
| 1 | **Contexto de ruta** — el archivo ya está dentro de `Trabajo/ARMS/ClienteX/` | → va a `Facturas/` dentro del mismo proyecto |
| 2 | **Nombre del archivo** — empresa, familiar, coche, vivienda, keywords | `factura_ARMS_2024.pdf` → `Trabajo/ARMS/` |
| 3 | **Extensión** | `.gpx` → `Personal/Viajes`, `.dcm` → `Personal/Salud/Pruebas` |
| 4 | **Contenido** — primeras 500 palabras del texto (PDF, DOCX, TXT) | Encuentra "IRPF" → `Personal/Gastos/` |
| 5 | **IA local (Ollama)** — solo si los pasos 1–4 fallan y `ai.enabled: true` | Clasifica por semántica |
| — | Si nada resuelve | → `_SinClasificar/` |

### Carpetas en bloque

Antes de procesar archivo a archivo, el sistema evalúa si una carpeta completa puede moverse de una sola vez:

```
Confianza = archivos con destino unánime / total archivos de la carpeta

≥ 0.85  →  mover toda la carpeta en bloque  (eficiente, una sola operación)
< 0.85  →  carpeta mixta → descender y clasificar cada archivo
```

---

## Log de operaciones

Cada run genera un fichero JSONL inmutable en `.ordenar/runs/`:

```
~/Downloads/.ordenar/
├── runs/
│   ├── 2026-06-13_01-23-45.log.jsonl   ← un archivo por ejecución
│   └── 2026-06-14_09-10-11.log.jsonl
└── latest.log.jsonl                     ← symlink al último run
```

Cada línea del log registra un movimiento:

```json
{
  "ts": "2026-06-13T01:23:45.123Z",
  "run_id": "a3f2b1c4",
  "action": "move",
  "item_type": "file",
  "src": "/Users/chema/Downloads/factura_ARMS_2024.pdf",
  "dst": "/Users/chema/Downloads/Trabajo/ARMS/_SinCliente/Facturas/factura_ARMS_2024.pdf",
  "category": "Trabajo/Facturas",
  "rule": "keyword:company:ARMS",
  "confidence": 0.85,
  "sha256": "e3b0c44298fc1c149afb...",
  "size_bytes": 204800,
  "duplicate_of": null
}
```

### Comandos de log

```bash
# Ver el último run en tabla
uv run ordenar log --last

# Ver solo los errores
uv run ordenar log --last --filter error

# Ver solo lo que no se clasificó
uv run ordenar log --last --filter skip

# Exportar a CSV
uv run ordenar log --last --format csv > movimientos.csv

# Exportar a Markdown
uv run ordenar log --last --format md > movimientos.md

# Ver en JSON crudo
uv run ordenar log --last --format json
```

---

## Deshacer un run

El log contiene toda la información necesaria para revertir exactamente lo que se movió:

```bash
# Deshacer el último run (pide confirmación)
uv run ordenar undo --last

# Deshacer sin confirmación
uv run ordenar undo --last --yes
```

---

## Comportamiento con estructura preexistente

Si `~/Downloads` ya tiene carpetas `Trabajo/` y `Personal/` parcialmente construidas, el sistema las detecta automáticamente en la **fase de bootstrap** antes de clasificar nada:

- Las carpetas de empresa encontradas en `Trabajo/` se añaden al catálogo de empresas conocidas.
- Los clientes dentro de cada empresa se registran como contexto.
- Las subcarpetas de `Personal/` se mapean a las categorías canónicas.
- Los archivos sueltos dentro de `Trabajo/ARMS/` se intentan clasificar al cliente/proyecto correcto; si no se puede, van a `Trabajo/ARMS/_SinClasificar/`.

---

## Casos especiales

| Situación | Comportamiento |
|-----------|----------------|
| Archivo duplicado exacto (mismo SHA-256) | Según `on_duplicate`: `rename` añade sufijo `_1`, `_2`…; `skip` lo ignora; `overwrite` reemplaza |
| Archivo sin extensión | Se intenta detectar el tipo por magic bytes |
| Carpeta vacía | Se clasifica solo por nombre |
| `.DS_Store`, archivos ocultos, `.tmp` | Se ignoran siempre |
| Archivos > `max_content_scan_mb` | No se lee su contenido; se clasifica solo por nombre y extensión |
| Error de permisos en un archivo | Se registra en el log con `"action": "error"` y se continúa |

---

## Estructura del código

```
src/ordenar/
├── main.py        — CLI (Typer + Rich): comandos run, log, undo
├── config.py      — Carga config.yaml con Pydantic; defaults seguros
├── taxonomy.py    — Diccionarios de keywords, extensiones y categorías
├── models.py      — Tipos de datos: Decision, ClassificationResult, RunSummary…
├── bootstrap.py   — Fase 0: lee Trabajo/ y Personal/ existentes → KnownContext
├── classifier.py  — Motor de reglas (señales 1–4 + preparado para IA)
├── hierarchy.py   — Procesamiento top-down nivel a nivel; genera el plan
├── executor.py    — Ejecuta el plan: mueve archivos/carpetas, maneja duplicados
└── logger.py      — JSONL append-only, SHA-256, symlink latest
```

---

## Añadir empresas y personalizaciones

Para adaptar la herramienta a tu caso, edita `config.yaml`:

```yaml
# Tus empresas de trabajo
companies:
  - ARMS
  - NombreOtraEmpresa

# Tus familiares (se clasifican a Personal/Familiar/{nombre}/)
family_members:
  - chema
  - susan

# Tus coches actuales
known_cars:
  - "2024 Toyota Corolla"

# Tus viviendas (para clasificar documentos de cada piso al lugar correcto)
known_homes:
  Madrid:
    - "Dalia 66"
  Miami:
    - "12535 NE Miami PL"
```

---

## Activar IA local (Ollama)

Para clasificar archivos ambiguos que no resuelven las reglas deterministas:

1. Instala [Ollama](https://ollama.com) y un modelo: `ollama pull llama3.2`
2. En `config.yaml`:

```yaml
ai:
  enabled: true
  provider: "ollama"
  model: "llama3.2"
```

El contenido del archivo nunca sale del equipo.
