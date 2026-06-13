"""Keyword dictionaries, extension maps and taxonomy constants."""

from __future__ import annotations


# ── Taxonomy ──────────────────────────────────────────────────────────────────

TRABAJO = "Trabajo"
PERSONAL = "Personal"

# Leaf subcategories inside a project
PROYECTO_SUBDIRS = [
    "Propuestas",
    "Contratos",
    "Entregables",
    "Facturas",
    "Comunicaciones",
    "Recursos",
]

# Top-level Personal categories and their canonical aliases
# Keys are the EXACT folder names as they exist in ~/Dropbox/Personal
PERSONAL_CATEGORIES: dict[str, list[str]] = {
    "Coches":       ["coches", "coche", "vehiculos", "vehiculo", "carro", "car", "moto",
                     "bmw", "toyota", "porsche", "volvo", "jeep", "rav4", "corolla", "chr"],
    "Colegios":     ["colegios", "colegio", "escuela", "school", "universidad", "college",
                     "aldovea", "san patricio", "ceu", "trinity", "septima ars", "maria virgen"],
    "Compra-Venta": ["compra", "venta", "compraventa", "compra-venta", "compra venta"],
    "Documentos":   ["documentos", "docs", "document", "papeles"],
    "Familiar":     ["familiar", "familia", "family", "familiares"],
    "Gastos":       ["gastos", "gasto", "expenses", "expense", "presupuesto personal"],
    "Salud":        ["salud", "health", "medico", "medica", "medicina", "doctor"],
    "Viajes":       ["viajes", "travel", "viaje", "trip", "vacaciones", "vuelo", "flight"],
    "Vivienda":     ["vivienda", "casa", "hogar", "home", "piso", "apartamento",
                     "hipoteca", "alquiler", "arrendamiento"],
}

# Personal sub-categories (keyword → exact subfolder path inside Personal/)
PERSONAL_SUBCATEGORIES: dict[str, list[str]] = {
    # Documentos
    "Documentos/DNI":                   ["dni", "documento nacional de identidad"],
    "Documentos/Pasaportes":            ["pasaporte", "passport"],
    "Documentos/Certificados":          ["certificado", "certificate", "diploma"],
    "Documentos/Empadronamiento":       ["empadronamiento", "padron municipal"],
    "Documentos/Migración":             ["migracion", "migración", "visado", "visa",
                                         "esta usa", "green card", "residencia"],
    "Documentos/Actas de Nacimiento":   ["acta de nacimiento", "partida de nacimiento",
                                         "birth certificate"],
    "Documentos/Acta de Matrimonio":    ["acta de matrimonio", "marriage certificate", "boda"],
    "Documentos/Seguridad Social":      ["seguridad social", "numero ss", "ss number"],
    "Documentos/Carnet de conducir":    ["carnet de conducir", "permiso de conducir",
                                         "driver license", "driving license"],
    "Documentos/Libro de Familia":      ["libro de familia", "family book"],
    "Documentos/Familia Numerosa":      ["familia numerosa", "carnet familia numerosa"],
    "Documentos/CURP":                  ["curp"],
    "Documentos/RFC":                   ["rfc"],
    "Documentos/Score de crédito":      ["score de credito", "credit score", "buro de credito"],
    # Salud
    "Salud/Análisis":                   ["analisis", "análisis", "sangre", "orina",
                                         "laboratorio", "blood test"],
    "Salud/Médicos":                    ["informe medico", "consulta", "historial medico",
                                         "historia clinica", "medico", "doctor"],
    "Salud/Pruebas":                    ["radiografia", "ecografia", "resonancia", "prueba",
                                         "scanner", "tac", "rx ", "rayos x"],
    "Salud/Seguros":                    ["seguro medico", "seguro salud", "adeslas", "asisa",
                                         "caser", "gnp", "sanitas", "poliza medica"],
    "Salud/Vacunas":                    ["vacuna", "vacunacion", "vaccine", "cartilla vacunacion"],
    "Salud/Gimnasio":                   ["gimnasio", "gym", "deporte", "fitness"],
    # Coches
    "Coches":                           ["itv", "seguro coche", "seguro auto", "matricula",
                                         "permiso circulacion", "ficha tecnica"],
    # Vivienda
    "Vivienda":                         ["escritura", "catastro", "comunidad propietarios",
                                         "ibi", "suministro", "luz", "electricidad",
                                         "agua", "gas", "internet", "reforma", "obra"],
    # Viajes
    "Viajes":                           ["boarding pass", "tarjeta embarque", "vuelo",
                                         "hotel", "reserva", "itinerario", "visado", "visa"],
    # Gastos
    "Gastos":                           ["extracto", "nomina", "transferencia", "iban",
                                         "irpf", "declaracion", "hacienda", "aeat",
                                         "impuesto", "renta", "iva", "recibo",
                                         "factura personal", "gasto"],
    # Familiar (genérico cuando no hay persona concreta)
    "Familiar":                         ["libro carlos", "herencia", "testamento",
                                         "poder notarial"],
}

# ── Trabajo keywords ──────────────────────────────────────────────────────────

TRABAJO_KEYWORDS: list[str] = [
    "factura", "invoice", "presupuesto", "quote", "propuesta", "proposal",
    "contrato", "contract", "nda", "acuerdo", "sla", "convenio",
    "entregable", "deliverable", "informe", "report",
    "reunión", "reunion", "meeting", "minuta", "acta",
    "cliente", "client", "proveedor", "vendor",
    "proyecto", "project",
    "oferta", "licitacion", "pliego",
    "soporte", "incidencia", "ticket",
]

PROYECTO_KEYWORD_MAP: dict[str, str] = {
    "factura":      "Facturas",
    "invoice":      "Facturas",
    "recibo":       "Facturas",
    "propuesta":    "Propuestas",
    "proposal":     "Propuestas",
    "oferta":       "Propuestas",
    "presupuesto":  "Propuestas",
    "quote":        "Propuestas",
    "contrato":     "Contratos",
    "contract":     "Contratos",
    "nda":          "Contratos",
    "acuerdo":      "Contratos",
    "sla":          "Contratos",
    "entregable":   "Entregables",
    "deliverable":  "Entregables",
    "informe":      "Entregables",
    "report":       "Entregables",
    "reunion":      "Comunicaciones",
    "reunión":      "Comunicaciones",
    "meeting":      "Comunicaciones",
    "minuta":       "Comunicaciones",
    "acta":         "Comunicaciones",
    "email":        "Comunicaciones",
    "correo":       "Comunicaciones",
}

# ── Extension maps ────────────────────────────────────────────────────────────

# Extensions that strongly suggest a specific Personal subcategory
EXTENSION_PERSONAL_MAP: dict[str, str] = {
    ".dcm":   "Salud/Historial",
    ".dicom": "Salud/Historial",
    ".gpx":   "Viajes",
    ".kml":   "Viajes",
    ".kmz":   "Viajes",
    ".fit":   "Salud/Historial",
}

# Extensions that suggest Trabajo/Recursos
EXTENSION_TRABAJO_MAP: dict[str, str] = {
    ".dwg":    "Trabajo",
    ".dxf":    "Trabajo",
    ".sketch": "Trabajo",
    ".fig":    "Trabajo",
    ".xd":     "Trabajo",
    ".ai":     "Trabajo",
}

# Generic document extensions (need further keyword analysis)
DOCUMENT_EXTENSIONS: set[str] = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".txt", ".rtf", ".csv",
}

# Image extensions
IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
    ".heic", ".heif", ".webp", ".raw", ".cr2", ".nef", ".arw",
}

# Video extensions
VIDEO_EXTENSIONS: set[str] = {
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v", ".webm",
}

# Ignored filenames / patterns (exact match or glob)
IGNORE_NAMES: set[str] = {
    ".DS_Store", "Thumbs.db", ".localized", "desktop.ini",
    ".gitkeep", ".gitignore",
}

IGNORE_SUFFIXES: set[str] = {
    ".tmp", ".part", ".crdownload", ".download",
}
