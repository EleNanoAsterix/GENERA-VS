import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
try:
    import cairosvg
    HAVE_CAIROSVG = True
except Exception:
    cairosvg = None
    HAVE_CAIROSVG = False
import io
import numpy as np
from io import BytesIO
import zipfile
import os

st.set_page_config(page_title='Generador VS - Web', layout='wide')

# --- helper functions (adapted from the original tkinter app) ---

def load_and_convert_logo_file(file_obj):
    # Accept file-like objects or BytesIO containing image or SVG data.
    name = getattr(file_obj, 'name', None)
    # Read raw bytes from the object (reset pointer afterwards)
    try:
        file_obj.seek(0)
    except Exception:
        pass
    try:
        data = file_obj.read()
    except Exception as e:
        raise Exception(f"No se pudo leer el archivo: {e}")
    # Ensure we have bytes
    if not isinstance(data, (bytes, bytearray)):
        raise Exception("Contenido de archivo no es binario")

    ext = os.path.splitext(name)[1].lower() if name else ''

    # Heurística para detectar SVG cuando no hay extensión (BytesIO sin .name)
    is_svg = False
    if ext == '.svg':
        is_svg = True
    else:
        head = data[:512].lower()
        if b'<svg' in head or b'<?xml' in head or b'xmlns="http://www.w3.org/2000/svg"' in head:
            is_svg = True

    if is_svg:
        if not HAVE_CAIROSVG:
            # Give a helpful error for deployment environments where cairosvg isn't installed
            raise Exception(
                "SVG upload detected but cairosvg is not available in the runtime. "
                "Streamlit Cloud may not have installed the native cairo dependencies. "
                "Two options: (1) upload PNG versions of your logos, or (2) add cairosvg to requirements and ensure the build logs show it installed successfully. "
                "See Streamlit Cloud build logs for pip install failures."
            )
        try:
            png_bytes = cairosvg.svg2png(bytestring=data)
            img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
            return img
        except Exception as e:
            raise Exception(f"No se pudo procesar el SVG: {e}")
    else:
        try:
            return Image.open(io.BytesIO(data)).convert('RGBA')
        except Exception as e:
            raise Exception(f"No se pudo cargar la imagen: {e}")


def resize_logo(logo_image: Image.Image, max_size=450, add_outline=False, outline_width=3):
    w, h = logo_image.size
    if w == 0 or h == 0:
        return logo_image
    if w > h:
        new_w = max_size
        new_h = int(h * (max_size / w))
    else:
        new_h = max_size
        new_w = int(w * (max_size / h))
    logo_resized = logo_image.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)

    if not add_outline:
        return logo_resized

    scale_factor = 4
    temp_logo = logo_resized.resize((logo_resized.width * scale_factor, logo_resized.height * scale_factor), Image.LANCZOS)
    alpha = temp_logo.split()[-1] if temp_logo.mode == 'RGBA' else Image.new('L', temp_logo.size, 255)

    blur_radius = outline_width * scale_factor
    extra_padding = blur_radius * 2
    padding = int(outline_width * scale_factor * 2.5) + extra_padding

    expanded_w = temp_logo.width + 2 * padding
    expanded_h = temp_logo.height + 2 * padding
    expanded_alpha = Image.new('L', (expanded_w, expanded_h), 0)
    alpha_pos = ((expanded_w - alpha.width) // 2, (expanded_h - alpha.height) // 2)
    expanded_alpha.paste(alpha, alpha_pos)

    dilated = expanded_alpha.filter(ImageFilter.MaxFilter(3))
    blurred = dilated.filter(ImageFilter.GaussianBlur(blur_radius))

    result = Image.new("RGBA", (expanded_w, expanded_h), (0, 0, 0, 0))
    result.paste((255, 255, 255), (0, 0), mask=blurred)

    logo_pos = ((expanded_w - temp_logo.width) // 2, (expanded_h - temp_logo.height) // 2)
    result.paste(temp_logo, logo_pos, temp_logo)

    final_size = (expanded_w // scale_factor, expanded_h // scale_factor)
    return result.resize(final_size, Image.LANCZOS)


def auto_enhance_background(img: Image.Image):
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img = ImageOps.equalize(img)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    img = ImageEnhance.Color(img).enhance(1.1)
    img = ImageEnhance.Sharpness(img).enhance(1.1)
    return img


def draw_vs_and_paste(bg_image: Image.Image, logo_a: Image.Image, logo_b: Image.Image, 
                      logo_a_pos, logo_b_pos, font_size):
    image = bg_image.copy()
    draw = ImageDraw.Draw(image)

    x_a = int(logo_a_pos[0] - logo_a.width // 2)
    y_a = int(logo_a_pos[1] - logo_a.height // 2)
    image.paste(logo_a, (x_a, y_a), logo_a)

    x_b = int(logo_b_pos[0] - logo_b.width // 2)
    y_b = int(logo_b_pos[1] - logo_b.height // 2)
    image.paste(logo_b, (x_b, y_b), logo_b)

    # load font with fallbacks
    try:
        font = ImageFont.truetype("Roboto-BlackItalic.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("Roboto-Black.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("Impact-Italic.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except Exception:
                    font = ImageFont.load_default()

    text = "VS."
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    center_x = (image.width - text_w) // 2
    center_y = (image.height - text_h) // 2
    offset_percent = int(image.height * (0.02 if image.width == 480 else 0.05))
    text_y = center_y + offset_percent
    draw.text((center_x, text_y), text, fill="white", font=font)
    return image


# --- app state ---
if 'enfrentamientos' not in st.session_state:
    st.session_state['enfrentamientos'] = []

st.title("Generador de imágenes VS - Web")
st.write("Sube fondo y dos logos, añade enfrentamientos a la cola y genera un ZIP con todas las resoluciones.")

col1, col2 = st.columns([1, 1])
with col1:
    background_file = st.file_uploader("Imagen de fondo (JPG/PNG)", type=['jpg', 'jpeg', 'png'], key='bg')
    auto_enhance = st.checkbox('Mejorar automáticamente la imagen de fondo', value=False)
with col2:
    logo_a_file = st.file_uploader("Logo Equipo A (PNG/SVG)", type=['png', 'jpg', 'jpeg', 'svg'], key='la')
    logo_b_file = st.file_uploader("Logo Equipo B (PNG/SVG)", type=['png', 'jpg', 'jpeg', 'svg'], key='lb')

add_outline = st.checkbox('Agregar contorno blanco a los logos', value=False)
outline_width = st.slider('Grosor del contorno', 1, 8, 3)

# Añadir enfrentamiento
if st.button('Añadir enfrentamiento a la lista'):
    if not background_file:
        st.error('Debes seleccionar una imagen de fondo')
    elif not logo_a_file or not logo_b_file:
        st.error('Debes seleccionar ambos logos')
    else:
        try:
            # store raw files in session_state (BytesIO copies)
            bg_bytes = background_file.read()
            logo_a_bytes = logo_a_file.read()
            logo_b_bytes = logo_b_file.read()
            st.session_state['enfrentamientos'].append({
                'background': bg_bytes,
                'logo_a': logo_a_bytes,
                'logo_b': logo_b_bytes,
                'equipo_a': os.path.splitext(logo_a_file.name)[0],
                'equipo_b': os.path.splitext(logo_b_file.name)[0],
                'add_outline': add_outline,
                'outline_width': outline_width,
                'auto_enhance': auto_enhance
            })
            st.success(f"Añadido: {os.path.splitext(logo_a_file.name)[0]} vs {os.path.splitext(logo_b_file.name)[0]}")
        except Exception as e:
            st.error(f"Error al añadir enfrentamiento: {e}")

# Mostrar cola
st.subheader('Enfrentamientos en cola')
for idx, ef in enumerate(st.session_state['enfrentamientos']):
    st.write(f"{idx+1}. {ef['equipo_a']} vs {ef['equipo_b']}")
    if st.button(f"Eliminar {idx+1}", key=f"del_{idx}"):
        st.session_state['enfrentamientos'].pop(idx)
        # Streamlit API changed in some versions; attempt to rerun, otherwise continue
        try:
            st.experimental_rerun()
        except Exception:
            pass

if st.session_state['enfrentamientos']:
    if st.button('Generar y descargar ZIP'):
        # process all enfrentamientos into zip
        with st.spinner('Generando imágenes...'):
            all_files = []
            # resolutions same as in original
            resolutions = [
                (1920, 1080, (476, 666), (1440, 666), int(450 * 1920 / 1920), int(130 * 1920 / 1920), "1920x1080"),
                (3840, 2160, (952, 1332), (2880, 1332), int(450 * 3840 / 1920), int(130 * 3840 / 1920), "3840x2160"),
                (480, 720, (120, 230), (360, 515), 177, 60, "480x720"),
            ]

            progress = st.progress(0)
            total = len(st.session_state['enfrentamientos']) * len(resolutions)
            done = 0

            for ef in st.session_state['enfrentamientos']:
                equipo_a = ef['equipo_a']
                equipo_b = ef['equipo_b']
                try:
                    bg_img = Image.open(io.BytesIO(ef['background'])).convert('RGB')
                except Exception as e:
                    st.error(f"No se pudo abrir fondo para {equipo_a} vs {equipo_b}: {e}")
                    continue

                for width, height, logo_a_pos, logo_b_pos, logo_size, font_size, res_str in resolutions:
                    # prepare background
                    bg_w, bg_h = bg_img.size
                    aspect_bg = bg_w / bg_h
                    aspect_out = width / height
                    if aspect_bg > aspect_out:
                        new_w = int(height * aspect_bg)
                        new_h = height
                    else:
                        new_w = width
                        new_h = int(width / aspect_bg)
                    bg_resized = bg_img.resize((new_w, new_h), Image.LANCZOS)
                    left = (new_w - width) // 2
                    top = (new_h - height) // 2
                    right = left + width
                    bottom = top + height
                    bg_cropped = bg_resized.crop((left, top, right, bottom))

                    blur_radius = {1920: 11.3, 3840: 20, 480: 8.1}.get(width, 10)
                    bg_blurred = bg_cropped.filter(ImageFilter.GaussianBlur(blur_radius))
                    if ef.get('auto_enhance'):
                        bg_blurred = auto_enhance_background(bg_blurred)

                    # load logos
                    try:
                        logo_a = load_and_convert_logo_file(io.BytesIO(ef['logo_a']))
                        logo_b = load_and_convert_logo_file(io.BytesIO(ef['logo_b']))
                    except Exception as e:
                        st.error(f"Error cargando logos para {equipo_a} vs {equipo_b}: {e}")
                        continue

                    logo_a = resize_logo(logo_a, max_size=logo_size, add_outline=ef['add_outline'], outline_width=ef['outline_width'])
                    logo_b = resize_logo(logo_b, max_size=logo_size, add_outline=ef['add_outline'], outline_width=ef['outline_width'])

                    final = draw_vs_and_paste(bg_blurred, logo_a, logo_b, logo_a_pos, logo_b_pos, font_size)
                    buf = BytesIO()
                    final.convert('RGB').save(buf, format='JPEG', quality=95)
                    fname = f"{equipo_a} vs {equipo_b} - {res_str}.jpg"
                    all_files.append((fname, buf.getvalue()))

                    done += 1
                    progress.progress(int(done / total * 100))

            # create zip
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, 'w') as z:
                for fname, data in all_files:
                    z.writestr(fname, data)
            zip_buf.seek(0)
            st.success('Generación completada')
            st.download_button('Descargar ZIP', data=zip_buf.getvalue(), file_name='generadas.zip', mime='application/zip')

else:
    st.info('No hay enfrentamientos en la lista. Añade uno para generar.')
