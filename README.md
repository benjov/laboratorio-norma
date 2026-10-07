# Laboratorio Norma+

App de Streamlit para la sesión del diplomado. Cada alumno abre un enlace, pega la API key que le dimos y recorre cinco estaciones del pipeline de Norma+ con tres resoluciones ficticias:

| Estación | Qué hace el alumno | Llama a Claude |
|---|---|---|
| 1 · Estructura | Ve el PDF, el ruido detectado, el router, el mapa de secciones y la zona argumentativa medida contra el gold | No |
| 2 · Extracción | Edita el prompt, extrae criterios de un apartado y ve cada cita verificada o no literal | Sí |
| 3 · Validación | Mide el validador contra 30 fragmentos etiquetados, mueve el umbral, prueba el gate de fidelidad y su filtro de riesgo | Sí |
| 4 · Deduplicación | Mueve el umbral de similitud, juzga candidatos con Claude, activa o desactiva las reglas duras | Sí |
| 5 · Evaluación y costos | P/R/F1 por etapa de su propia extracción y una calculadora de costos para el acervo de la SCJN | No |

Cada estación tiene retos y un panel **Ver el código** con las funciones reales que corren.

## Costo

Modelo `claude-haiku-4-5`. Un recorrido completo cuesta alrededor de USD 0.10 a 0.15 por alumno (estimación con un simulador; confirmar en la corrida de ensayo). Cada sesión se detiene al llegar a `LIMITE_SESION_USD` (1.5 por defecto).

La caché es **compartida**: si alguien ya hizo exactamente la misma llamada (mismo prompt y mismo texto), la respuesta sale de la caché y no se paga. Sin key, el alumno ve solo lo que ya está en caché.

## Desplegar en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio de GitHub (puede ser privado). `app.py` debe quedar en la raíz del repositorio o indica su ruta al crear la app.
2. Entra a share.streamlit.io con la cuenta de GitHub y elige **Create app** › desde un repositorio existente.
3. Selecciona el repositorio, la rama y `app.py` como archivo principal.
4. En **Advanced settings**, elige Python 3.11 o 3.12 y pega en **Secrets** el contenido de `.streamlit/secrets.toml.ejemplo` con una clave de instructor propia.
5. Despliega. La primera instalación tarda unos minutos.
6. Revisa en la configuración de compartir quién puede abrir la app. Comparte el enlace con los alumnos.

La app no guarda las keys en disco: viven solo en la sesión del navegador de cada alumno. Aun así, pasan por el servidor de la app; por eso se usan keys del curso, con tope de gasto, que se revocan al terminar.

## Respaldo para quien no tenga key

1. Después de la corrida de ensayo, abre **Inicio › Para el instructor**, escribe la clave de instructor y descarga la caché.
2. Reemplaza `datos/respaldo/cache.json` en el repositorio con ese archivo y vuelve a desplegar.

Con eso, cualquier alumno ve los resultados de la corrida de ensayo aunque su key falle. La caché en memoria se pierde cuando la app se reinicia o se duerme por inactividad; el respaldo no.

## Embeddings

Por defecto, la estación 4 mide similitud con TF-IDF de n-gramas de caracteres, que corre en cualquier servidor. Para usar embeddings reales (MiniLM multilingüe), descomenta `sentence-transformers` en `requirements.txt`. Pesa cerca de 1 GB y puede exceder los recursos gratuitos de Streamlit Cloud.

## Estructura

```
app.py                 Inicio
pages/                 Las cinco estaciones
nucleo/                La lógica del pipeline (lo que muestra «Ver el código»)
datos/                 Resoluciones ficticias, gold, negativos, pares de fidelidad, taxonomía y respaldo de caché
.streamlit/            Tema y ejemplo de secretos
```

Prueba local: `pip install -r requirements.txt` y `streamlit run app.py`.
