"""
PDF Unifier - Aplicación web Flask para unificar archivos en un solo PDF.
Soporta: PDF, imágenes (JPG, PNG, GIF, BMP, TIFF, WEBP), Word, Excel, PowerPoint.
"""
import os
import uuid
import shutil
import logging
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import pypdf
from PIL import Image
from docx2pdf import convert as docx_convert
import tempfile

app = Flask(__name__)
MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', '50'))
MAX_FILES = int(os.environ.get('MAX_FILES', '20'))
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024
logging.basicConfig(level=logging.INFO)

# Carpeta temporal para uploads
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "pdf_unifier_uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'
}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_pdf(image_path: Path, output_path: Path) -> None:
    """Convierte una imagen a PDF."""
    img = Image.open(image_path)
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    img.save(str(output_path), 'PDF', resolution=150)

def office_to_pdf(office_path: Path, output_dir: Path) -> Path:
    """Convierte archivos Office (Word/Excel/PPT) a PDF usando docx2pdf / LibreOffice."""
    try:
        # Intenta con docx2pdf (requiere Word en Windows o LibreOffice en Linux/Mac)
        output_pdf = output_dir / (office_path.stem + '.pdf')
        docx_convert(str(office_path), str(output_pdf))
        if output_pdf.exists():
            return output_pdf
    except Exception:
        pass

    # Fallback: LibreOffice headless. Cada solicitud usa un perfil aislado para
    # evitar bloqueos cuando hay conversiones simultáneas.
    profile_dir = output_dir / f"lo_profile_{uuid.uuid4().hex}"
    profile_dir.mkdir(exist_ok=True)
    result = subprocess.run(
        ['libreoffice', f'-env:UserInstallation={profile_dir.as_uri()}',
         '--headless', '--convert-to', 'pdf',
         '--outdir', str(output_dir), str(office_path)],
        capture_output=True, text=True, timeout=60
    )
    output_pdf = output_dir / (office_path.stem + '.pdf')
    if output_pdf.exists():
        return output_pdf
    app.logger.warning("LibreOffice no pudo convertir %s: %s", office_path.name, result.stderr)
    raise RuntimeError(f"No se pudo convertir {office_path.name} a PDF.")

@app.route('/')
def index():
    return render_template('index.html', max_upload_mb=MAX_UPLOAD_MB, max_files=MAX_FILES)


@app.errorhandler(413)
def request_too_large(error):
    return jsonify({'error': f'La carga supera el límite de {MAX_UPLOAD_MB} MB'}), 413

@app.route('/merge', methods=['POST'])
def merge_files():
    """Recibe los archivos y genera el PDF unificado."""
    if 'files' not in request.files:
        return jsonify({'error': 'No se recibieron archivos'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No se seleccionaron archivos'}), 400
    if len(files) > MAX_FILES:
        return jsonify({'error': f'Se permiten como máximo {MAX_FILES} archivos'}), 400

    # Crear carpeta de sesión temporal
    session_id = uuid.uuid4().hex
    session_dir = UPLOAD_FOLDER / session_id
    session_dir.mkdir(exist_ok=True)

    try:
        pdf_paths = []
        # Guardar archivos subidos
        uploaded = []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                save_path = session_dir / filename
                # Evitar colisiones de nombre
                counter = 1
                while save_path.exists():
                    stem = Path(filename).stem
                    suffix = Path(filename).suffix
                    save_path = session_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                f.save(str(save_path))
                uploaded.append(save_path)
            else:
                return jsonify({'error': f'Tipo de archivo no soportado: {f.filename}'}), 400

        # Convertir cada archivo a PDF
        # El navegador ya envía las partes en el orden elegido por el usuario.
        for file_path in uploaded:
            ext = file_path.suffix.lower().lstrip('.')
            if ext == 'pdf':
                pdf_paths.append(file_path)
            elif ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp'):
                out_pdf = session_dir / (file_path.stem + '_converted.pdf')
                image_to_pdf(file_path, out_pdf)
                pdf_paths.append(out_pdf)
            elif ext in ('doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'):
                out_pdf = office_to_pdf(file_path, session_dir)
                pdf_paths.append(out_pdf)

        if not pdf_paths:
            return jsonify({'error': 'No se pudo procesar ningún archivo'}), 400

        # Unir todos los PDFs
        merger = pypdf.PdfWriter()
        for pdf_path in pdf_paths:
            merger.append(str(pdf_path))

        output_name = request.form.get('output_name', 'documento_unificado').strip() or 'documento_unificado'
        output_name = secure_filename(output_name)
        if not output_name.endswith('.pdf'):
            output_name += '.pdf'

        output_path = session_dir / output_name
        with open(output_path, 'wb') as f:
            merger.write(f)
        merger.close()

        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=output_name,
            mimetype='application/pdf'
        )

    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500
    except Exception:
        app.logger.exception("Error al procesar una solicitud")
        return jsonify({'error': 'No se pudieron procesar los archivos'}), 500
    finally:
        # Limpiar archivos temporales en segundo plano (después de enviar la respuesta)
        # Para simplificar, se limpia al siguiente request o manualmente
        pass


@app.teardown_request
def cleanup_old_sessions(exception=None):
    """Limpia sesiones con más de 1 hora de antigüedad."""
    import time
    try:
        now = time.time()
        for session_dir in UPLOAD_FOLDER.iterdir():
            if session_dir.is_dir():
                age = now - session_dir.stat().st_mtime
                if age > 3600:  # 1 hora
                    shutil.rmtree(session_dir, ignore_errors=True)
    except Exception:
        pass


if __name__ == '__main__':
    print("🚀 PDF Unifier iniciado en http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
