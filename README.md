# GENERA-VS
Genera imágenes para enfrentamientos deportivos
Descripción
---
Esta carpeta contiene la app Streamlit `app_generadora_streamlit.py` para generar imágenes "VS" a partir de un fondo y dos logos. El despliegue en Streamlit Cloud usa `requirements.txt` para instalar dependencias.

Requisitos
---
- Python 3.10 / 3.11 recomendado
- `requirements.txt` presente en la raíz del repo (ya incluido)

Probar localmente
---
1) Crear y activar un virtualenv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Instalar dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3) Ejecutar la app:

```bash
streamlit run app_generadora_streamlit.py
```

Desplegar en Streamlit Community Cloud
---
1) Crea un repositorio en GitHub y sube todo el contenido de esta carpeta (`git init`, `git add .`, `git commit -m "init"`, `git push`).

2) Entra a https://streamlit.io/cloud, conecta tu cuenta de GitHub y crea una nueva app:
   - Selecciona el repositorio recién subido.
   - En "Main file" elige `app_generadora_streamlit.py`.
   - Streamlit Cloud instalará dependencias desde `requirements.txt` automáticamente.

3) Opcional: en la UI de Streamlit Cloud puedes configurar variables de entorno o secretos.

Notas y buenas prácticas
---
- Si tienes problemas con SVG complejos, añade librerías o preprocesa los SVG en el repo.
- Para estabilidad en producción, limita número máximo de enfrentamientos y tamaño de archivo por upload.
- Recomiendo elegir Python 3.11 en tu entorno local; Streamlit Cloud usa la versión que el sistema soporte.

Soporte
---
Si quieres, puedo:
- Crear un archivo `Dockerfile` para despliegue alternativo.
- Añadir límites y validaciones (tamaño por archivo, número máximo de items en cola).
- Automatizar el push a GitHub desde tu máquina con pasos listos.

