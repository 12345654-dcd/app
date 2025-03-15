"""
Fecha: 3 marzo del 2025
Autor: Mical Anheli Cruz Rodriguez
Descripción: Esta aplicación web, desarrollada con Flask, permite a los usuarios consultar 
el clima actual de una ciudad en México utilizando la API de OpenWeatherMap. 
Basándose en las condiciones climáticas y los síntomas ingresados por el usuario, 
el sistema genera recomendaciones para mitigar posibles problemas de alergias. 
Además, se almacena un historial de consultas en una base de datos SQLite 
para su posterior revisión. También incluye un endpoint para consultar una IA 
usando la API de Cohere.
"""

from flask import Flask, render_template, request, jsonify
import requests
import datetime
import sqlite3
import cohere

app = Flask(__name__)

# Configuración de la API de OpenWeatherMap
API_KEY_WEATHER = '324039eadaafe607cbd9847c23b6b7d5'
API_URL_WEATHER = "http://api.openweathermap.org/data/2.5/weather"
UNITS = "metric"
LANG = "es"

# Configuración de la API de Cohere
COHERE_API_KEY = "ZEOP2SH22uTBcYvF45V8KxSrGOig9wqRBoGbIvqM"
co = cohere.Client(COHERE_API_KEY)

# Inicializar base de datos
def init_db():
    conn = sqlite3.connect('historial_consultas.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ciudad TEXT NOT NULL,
            sintomas TEXT NOT NULL,
            recomendaciones TEXT NOT NULL,
            fecha TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def obtener_clima(ciudad):
    """Obtiene el clima de la ciudad desde OpenWeatherMap."""
    try:
        params = {
            "q": f"{ciudad},Mexico",
            "appid": API_KEY_WEATHER,
            "units": UNITS,
            "lang": LANG
        }
        respuesta = requests.get(API_URL_WEATHER, params=params)
        datos = respuesta.json()

        if respuesta.status_code == 200:
            return {
                "temperatura": datos["main"]["temp"],
                "humedad": datos["main"]["humidity"],
                "descripcion": datos["weather"][0]["description"].capitalize(),
                "viento": datos["wind"]["speed"],
                "uv": datos["main"]["temp_max"],  # Asumido como indicador de UV
                "presion": datos["main"]["pressure"],
                "hora": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            print(f"Error en la API: {datos.get('message', 'Error desconocido')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API: {e}")
        return None

def guardar_historial(ciudad, sintomas, recomendaciones):
    """Guarda el historial de consultas del usuario en la base de datos."""
    conn = sqlite3.connect('historial_consultas.db')
    c = conn.cursor()

    c.execute("INSERT INTO historial (ciudad, sintomas, recomendaciones, fecha) VALUES (?, ?, ?, ?)",
              (ciudad, ', '.join(sintomas), ', '.join([r[0] for r in recomendaciones]), datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()

def obtener_historial():
    """Obtiene el historial de consultas almacenado en la base de datos."""
    conn = sqlite3.connect('historial_consultas.db')
    c = conn.cursor()

    c.execute("SELECT ciudad, sintomas, recomendaciones, fecha FROM historial ORDER BY fecha DESC")
    consultas = c.fetchall()

    conn.close()

    return consultas

def generar_recomendaciones(clima, sintomas):
    """Genera recomendaciones y posibles causas en función del clima y síntomas ingresados."""
    recomendaciones = []

    # Condiciones climáticas que pueden afectar alergias
    descripcion_clima = clima["descripcion"].lower()
    if clima["humedad"] > 70:
        recomendaciones.append(("La humedad alta puede favorecer la proliferación de moho y ácaros. Mantén los espacios ventilados.", "Causa: Humedad excesiva y condiciones de moho o ácaros."))
    if any(x in descripcion_clima for x in ["lluvia", "tormenta", "niebla"]):
        recomendaciones.append(("Evita salir en condiciones de lluvia o niebla si eres sensible a la humedad.", "Causa: Humedad y aire pesado que intensifican los síntomas alérgicos."))
    if any(x in descripcion_clima for x in ["viento", "polvo"]):
        recomendaciones.append(("Usa gafas y mascarilla si hay viento fuerte o polvo en el aire.", "Causa: El viento puede levantar polvo y polen, agravando los síntomas alérgicos."))

    # Recomendaciones para viento y UV
    if clima["viento"] > 15:
        recomendaciones.append(("El viento está muy fuerte. Considera no salir o usar protección para los ojos y vías respiratorias.", "Causa: El viento puede aumentar la dispersión de alérgenos en el aire."))
    if clima["uv"] > 7:
        recomendaciones.append(("El índice UV es alto. Usa protector solar y evita la exposición prolongada al sol.", "Causa: El sol fuerte puede causar irritación en la piel y ojos, especialmente si tienes alergias."))
    
    # Recomendaciones de presión atmosférica
    if clima["presion"] < 1010:
        recomendaciones.append(("La presión atmosférica es baja, lo que puede causar dolores de cabeza. Mantén tu hidratación adecuada.", "Causa: Presión baja que puede afectar la circulación y desencadenar dolores de cabeza."))
    elif clima["presion"] > 1025:
        recomendaciones.append(("La presión atmosférica es alta, lo que podría causar incomodidad. Relájate y mantén la calma.", "Causa: La presión alta puede generar incomodidad general y aumento de la tensión arterial."))

    # Sugerencias de estilo de vida
    recomendaciones.append(("Mantén un estilo de vida saludable. Come alimentos ricos en vitamina C y duerme lo suficiente para fortalecer tu sistema inmunológico.", 
                            "Causa: Un sistema inmunológico fuerte ayuda a prevenir el empeoramiento de los síntomas de alergias."))

    # Recomendaciones según los síntomas
    sintomas_recomendaciones = {
        "estornudos": ("Evita el contacto con el polvo y alérgenos. Usa un purificador de aire en casa.", "Causa: La exposición a polvo o alérgenos comunes como el polen puede desencadenar estornudos."),
        "congestión nasal": ("Mantén la hidratación y usa solución salina para limpiar las fosas nasales.", "Causa: La congestión nasal puede ser causada por alérgenos como polvo, polen, o incluso aire seco."),
        "ojos llorosos": ("Usa gafas de sol al salir para protegerte del polen y el viento.", "Causa: El polen y el viento pueden irritar los ojos y causar lagrimeo."),
        "picazón en la garganta": ("Evita cambios bruscos de temperatura y bebe líquidos tibios.", "Causa: La irritación en la garganta puede ser provocada por alergias o infecciones respiratorias."),
        "dolor de cabeza": ("Mantén la calma y usa analgésicos si es necesario.", "Causa: El dolor de cabeza puede estar relacionado con cambios de presión atmosférica o alergias."),
        "fatiga": ("Descansa y mantén tu hidratación adecuada.", "Causa: La fatiga puede ser un síntoma secundario de las alergias o la falta de descanso."),
        "fiebre leve": ("Consulta a un médico si los síntomas persisten.", "Causa: La fiebre podría estar relacionada con infecciones o reacciones alérgicas graves."),
        "dificultad para respirar": ("Busca atención médica inmediatamente si sientes dificultades graves.", "Causa: La dificultad para respirar puede ser un síntoma de una reacción alérgica severa o asma."),
        "erupciones en la piel": ("Evita el contacto con posibles alérgenos y utiliza cremas para calmar la piel.", "Causa: Las erupciones pueden ser causadas por reacciones alérgicas a ciertos alérgenos o irritantes."),
        "tos seca": ("Mantén la hidratación y evita ambientes secos.", "Causa: La tos seca puede ser un síntoma de alergias respiratorias o aire seco."),
        "mareos": ("Descansa y mantén la cabeza en una posición cómoda.", "Causa: Los mareos pueden ser causados por cambios de presión o desequilibrio en el sistema interno."),
        "picazón en la nariz": ("Evita tocarte la cara y usa un humidificador.", "Causa: La picazón en la nariz es comúnmente provocada por polen o polvo en el aire."),
        "secreción nasal": ("Mantén tus fosas nasales limpias y usa spray salino.", "Causa: La secreción nasal puede ser un síntoma de resfriados o alergias a los alérgenos del aire.")
    }

    for sintoma in sintomas:
        if sintoma in sintomas_recomendaciones:
            recomendaciones.append(sintomas_recomendaciones[sintoma])

    return recomendaciones

@app.route("/", methods=["GET", "POST"])
def index():
    clima = None
    recomendaciones = []
    error = None
    historial = obtener_historial()

    if request.method == "POST":
        ciudad = request.form.get("ciudad", "").strip()
        sintomas = request.form.getlist("sintomas")

        if ciudad:
            clima = obtener_clima(ciudad)
            if clima:
                recomendaciones = generar_recomendaciones(clima, sintomas)
                guardar_historial(ciudad, sintomas, recomendaciones)
            else:
                error = "Ciudad no encontrada o error en la API. Intenta de nuevo."
        else:
            error = "Por favor, ingresa una ciudad válida."

    return render_template("index.html", clima=clima, recomendaciones=recomendaciones, error=error, historial=historial)

@app.route('/consultar-ia', methods=['POST'])
def consultar_ia():
    data = request.json
    pregunta = data.get('pregunta')

    if not pregunta or not pregunta.strip():
        return jsonify({"error": "Por favor, ingresa una pregunta válida."}), 400

    try:
        respuesta = co.generate(
            model='command',
            prompt=pregunta,
            max_tokens=300
        )
        return jsonify({"respuesta": respuesta.generations[0].text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
