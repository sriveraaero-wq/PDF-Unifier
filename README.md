# PDF Unifier

Aplicación web para unificar múltiples archivos en un solo PDF.

## Formatos soportados

| Tipo | Extensiones |
|------|-------------|
| PDF | `.pdf` |
| Imágenes | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp` |
| Word | `.doc`, `.docx` |
| Excel | `.xls`, `.xlsx` |
| PowerPoint | `.ppt`, `.pptx` |

## Requisitos previos

- **Python 3.9+**
- Para convertir archivos Office (Word/Excel/PowerPoint): necesitas **Microsoft Office** instalado (Windows) o **LibreOffice** (Linux/Mac).

## Instalación y ejecución

```bash
# 1. Ir a la carpeta del proyecto
cd pdf-unifier

# 2. Crear entorno virtual (recomendado)
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Mac/Linux:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar la aplicación
python app.py
```

Luego abre el navegador en: **http://localhost:5000**

## Despliegue público en Render

El proyecto incluye `Dockerfile` y `render.yaml` para instalar LibreOffice y
mantener la conversión de Word, Excel y PowerPoint en el servidor.

1. Sube el proyecto a un repositorio de GitHub (sin `venv`).
2. En Render selecciona **New > Blueprint**.
3. Conecta el repositorio y confirma la creación del servicio.

Render construirá la imagen y publicará una dirección HTTPS. El límite público
predeterminado es 50 MB y 20 archivos por solicitud; ambos se pueden cambiar
con las variables `MAX_UPLOAD_MB` y `MAX_FILES`.

## Características

- 🖱️ **Drag & Drop** — arrastra archivos directamente a la zona de carga
- 🔀 **Reordenar** — arrastra los archivos en la lista para cambiar el orden en el PDF final
- 📛 **Nombre personalizado** — elige el nombre del PDF resultante
- 🗑️ **Quitar archivos** — elimina archivos individuales o limpia todo
- 🧹 **Auto-limpieza** — los archivos temporales se eliminan automáticamente

## Estructura del proyecto

```
pdf-unifier/
├── app.py              # Servidor Flask (backend)
├── requirements.txt    # Dependencias Python
├── templates/
│   └── index.html      # Interfaz web (frontend)
└── README.md           # Este archivo
```
