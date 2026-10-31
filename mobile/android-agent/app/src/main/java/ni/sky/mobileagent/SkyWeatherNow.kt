package ni.sky.mobileagent

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

/**
 * Condiciones actuales estimadas por Open-Meteo, sin GPS y sin clave API.
 * La ciudad debe ser indicada por el usuario.
 */
object SkyWeatherNow {
    data class Result(val text: String, val sourceUrl: String)

    // Weather is a direct question/command, not the mere presence of a word.
    // "tiempo disponible", "clima emocional" or a 350-page thesis brief must
    // never hijack the academic/work/document intent.
    private val weatherOpening = Regex(
        """^(?:(?:como|que|cual es|cuanto es|cuantos grados hace)\s+""" +
            """(?:(?:esta|estara|sera|hace|va a estar|hay)\s+)?""" +
            """(?:(?:el|la|del)\s+)?)?""" +
            """(?:clima|pronostico|temperatura)\b"""
    )
    private val weatherTimeOpening = Regex(
        """^(?:que tiempo hace|como esta el tiempo|como estara el tiempo|""" +
            """tiempo (?:en|de|para)\s+|estado del tiempo\b)"""
    )
    private val named = Regex(
        """(?:clima|tiempo|temperatura|pron[oó]stico)(?:\s+(?:actual|de hoy|ahora))?\s+(?:en|de)\s+([\p{L}][\p{L} ,.'-]{1,78})[?.!]*$""",
        RegexOption.IGNORE_CASE
    )
    private val future = Regex(
        """\b(mañana|pasado mañana|próxima semana|proxima semana|fin de semana)\b""",
        RegexOption.IGNORE_CASE
    )

    fun isWeatherQuery(raw: String): Boolean {
        // Only a short, explicitly meteorological instruction can route here.
        // Never infer weather from research context or the word "tiempo".
        if (raw.length !in 3..260 || raw.contains('\n')) return false
        var clean = java.text.Normalizer.normalize(
            raw.lowercase(Locale.ROOT), java.text.Normalizer.Form.NFD)
            .replace(Regex("""\p{M}+"""), "")
            .replace(Regex("""[^a-z0-9 ]"""), " ")
            .replace(Regex("""\s+"""), " ").trim()
        clean = clean.replace(Regex("""^(?:(?:hola|hey)\s+)?(?:sky ia|sky|esky)\s+"""), "")
            .replace(Regex("""^(?:por favor\s+)?(?:dime|decime|consulta|dame|quiero saber|necesito saber)\s+"""), "")
            .replace(Regex("""^(?:el|la|del)\s+"""), "")
        return weatherOpening.containsMatchIn(clean) ||
            weatherTimeOpening.containsMatchIn(clean)
    }
    fun requestsFuture(raw: String): Boolean = future.containsMatchIn(raw)

    fun requestedCity(raw: String): String? = named.find(raw.trim())
        ?.groupValues?.get(1)?.trim()?.trimEnd('.', '?', '!', ',')
        ?.takeIf { it.length >= 2 }

    fun current(city: String): Result {
        require(city.length in 2..80) { "Indicá una ciudad válida para consultar el clima." }
        val geoUrl = "https://geocoding-api.open-meteo.com/v1/search?name=" +
            URLEncoder.encode(city, "UTF-8") + "&count=5&language=es&format=json"
        val places = getJson(geoUrl).optJSONArray("results")
            ?: throw IllegalStateException("No encontré la ciudad. Añadí el país.")
        require(places.length() > 0) { "No encontré esa ciudad." }
        val location = places.optJSONObject(0)
            ?: throw IllegalStateException("La ubicación meteorológica es inválida.")
        val name = location.optString("name")
        val country = location.optString("country")
        val sameName = (0 until places.length()).mapNotNull { places.optJSONObject(it) }
            .filter { it.optString("name").equals(name, ignoreCase = true) }
            .map { it.optString("country_code") }.distinct()
        if (sameName.size > 1 && !city.contains(",")) {
            throw IllegalArgumentException("Hay varias ciudades llamadas " + name +
                ". Decime también el país, por ejemplo «clima en " + name + ", Nicaragua».")
        }
        val latitude = location.getDouble("latitude")
        val longitude = location.getDouble("longitude")
        require(latitude in -90.0..90.0 && longitude in -180.0..180.0) {
            "Coordenadas meteorológicas inválidas."
        }
        val forecastUrl = "https://api.open-meteo.com/v1/forecast?latitude=" +
            latitude.toString() + "&longitude=" + longitude.toString() +
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature," +
            "precipitation,weather_code,wind_speed_10m&timezone=auto"
        val now = getJson(forecastUrl).optJSONObject("current")
            ?: throw IllegalStateException("Open-Meteo no devolvió condiciones actuales.")
        val temp = now.optDouble("temperature_2m", Double.NaN)
        val feels = now.optDouble("apparent_temperature", Double.NaN)
        val humidity = now.optDouble("relative_humidity_2m", Double.NaN)
        val wind = now.optDouble("wind_speed_10m", Double.NaN)
        val measuredAt = now.optString("time")
        require(temp.isFinite() && measuredAt.isNotBlank()) {
            "No hay condiciones actuales verificables."
        }
        fun value(number: Double) = String.format(Locale.US, "%.1f", number)
        val output = buildString {
            append("En ").append(name).append(", ").append(country)
            append(", Open-Meteo estima ").append(value(temp)).append(" °C y ")
            append(weatherDescription(now.optInt("weather_code", -1))).append(".")
            if (feels.isFinite()) append(" Sensación térmica: ").append(value(feels)).append(" °C.")
            if (humidity.isFinite()) append(" Humedad: ").append(humidity.toInt()).append(" %.")
            if (wind.isFinite()) append(" Viento: ").append(value(wind)).append(" km/h.")
            append("\nFecha y hora local del dato: ").append(measuredAt).append(".")
            append("\nFuente: Open-Meteo. Estimación meteorológica, no lectura del teléfono.")
        }
        return Result(output, forecastUrl)
    }

    private fun weatherDescription(code: Int): String = when(code) {
        0 -> "cielo despejado"
        1, 2, 3 -> "cielo parcialmente nublado"
        45, 48 -> "niebla"
        51, 53, 55, 56, 57 -> "llovizna"
        61, 63, 65, 66, 67 -> "lluvia"
        71, 73, 75, 77 -> "nieve"
        80, 81, 82 -> "chubascos"
        85, 86 -> "chubascos de nieve"
        95, 96, 99 -> "tormenta"
        else -> "condiciones no especificadas"
    }

    private fun getJson(address: String): JSONObject {
        val connection = URL(address).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 8_000
            connection.readTimeout = 13_000
            connection.setRequestProperty("Accept", "application/json")
            if (connection.responseCode !in 200..299) {
                throw IllegalStateException("El servicio meteorológico no respondió correctamente.")
            }
            val data = connection.inputStream.use { input ->
                val output = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(4096)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    require(output.size() + count <= 150_000) {
                        "La respuesta meteorológica fue demasiado grande."
                    }
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            }
            return JSONObject(data.toString(Charsets.UTF_8))
        } finally {
            connection.disconnect()
        }
    }
}
