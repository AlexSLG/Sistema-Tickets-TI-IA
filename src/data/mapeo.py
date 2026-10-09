"""Reglas de etiquetado (paso 4): categoría, relevancia de TI, prioridad, impacto, urgencia y usuarios afectados.

Todas las reglas están documentadas en reports/reglas_etiquetado.md. Los textos se comparan en
minúsculas y sin acentos. Las semillas son fijas (42).
"""
import random
import re
import unicodedata

CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"]
IMPACTOS = ["Bajo", "Medio", "Alto"]
URGENCIAS = ["Baja", "Media", "Alta"]
SEMILLA = 42


def normalizar(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


# ------------------------------------------------------------------ categoría
# (patrón, peso). Los patrones se aplican sobre texto normalizado.
REGLAS_CATEGORIA = {
    "Seguridad": [
        (r"phishing|malware|ransomware|troyano|spyware|virus\b|antivirus|antimalware", 3),
        (r"brecha|vulnerabilidad|ciberataque|ciberseguridad|hackeo|hackeado|intrusion|filtracion de datos|fuga de datos", 3),
        (r"acceso no autorizado|accesos no autorizados|intentos de acceso no autorizado|infraccion de (la )?(seguridad|proteccion)", 4),
        (r"cortafuegos|firewall|cifrad|encriptad|amenaza|incidente de seguridad|riesgo de seguridad|violacion de datos", 2),
        (r"seguridad de(l| los| las)? (dato|sistema|red|informacion|infraestructura)|proteccion de (los )?datos|proteger (los )?datos", 2),
        (r"medidas de seguridad|protocolos de seguridad|ataque", 1.5),
        (r"seguridad", 1),
    ],
    "Accesos": [
        (r"contrasena|restablec\w+ (de )?(la |mi )?(clave|contrasena)|\bclave de acceso", 3),
        (r"inicio de sesion|iniciar sesion|login|credenciales|autenticacion|doble factor|\b2fa\b|\bmfa\b|\bsso\b", 3),
        (r"cuenta (esta )?(bloquead|suspendid|desactivad)|bloqueo de (la )?cuenta|usuario bloqueado", 3),
        (r"permiso|autorizacion|autorizarme|privilegio|concede\w* acceso|dar(me)? acceso|tener acceso|obtener acceso|solicit\w+ acceso", 2.5),
        (r"acceso (denegado|restringido)|no puedo (entrar|acceder|ingresar)|sin acceso|control de acceso|controles de acceso", 2.5),
        (r"cuenta de usuario|nueva cuenta|crear (una )?cuenta|alta de usuario|nombre de usuario|rol(es)? de usuario|perfil de usuario", 2),
        (r"\bacceso\b", 0.75),
    ],
    "Correo": [
        (r"outlook|buzon|bandeja de entrada|smtp|imap|pop3|\bspam\b|gmail|exchange (online|server)|cliente de correo|servidor de correo|cuenta de correo", 3.5),
        (r"(enviar|recibir|sincroniz\w+) (los |mis )?(correos|emails|mensajes de correo)|correos? (no )?(llegan|se envian|rebotan|rechazad)", 3),
        (r"adjunto|lista de distribucion|firma de correo|reglas de correo|filtro de (correo|email)", 2),
        (r"casilla|carpeta de (elementos )?(enviados|recibidos|entrada|salida)|libreta de direcciones|mensajes (recibidos|enviados)|notificacion de nuevos correos", 2.5),
        (r"correo electronico|correos electronicos|e-?mails?|\bcorreos?\b", 1),
    ],
    "Red": [
        (r"\bvpn\b|wi-?fi|wifi|wlan|inalambric|\bdns\b|dhcp|direccion(es)? ip|\bip\b|ancho de banda|latencia|ethernet|\blan\b|\bwan\b|proxy|punto de acceso", 3),
        (r"\bred(es)?\b|router|modem|conectividad|internet|cortes de red|desconexion|switch\b|\bpaquetes\b|puerta de enlace|pasarela", 2),
        (r"conexion|conectarse|conectar", 1),
    ],
    "Hardware": [
        (r"impresora|portatil|laptop|disco duro|\bssd\b|\bhdd\b|monitor|teclado|raton\b|\bmouse\b|\bram\b|\bcpu\b|procesador|ventilador|bateria|placa base|fuente de alimentacion|tarjeta grafica|\bgpu\b", 3),
        (r"sobrecalent|altavoz|webcam|camara web|proyector|escaner|auricular|microfono|cable\b|\busb\b|pantalla|hardware|ordenador|computadora|\bpc\b|equipo informatico|sala de servidores|servidor fisico", 2),
        (r"no (se )?enciende|se apaga|encender|apagar|memoria|dispositivo|periferico|disco\b|equipo\b", 1),
    ],
    "Software": [
        (r"aplicacion|software|programa\b|actualizacion|parche|\bbug\b|sistema operativo|windows|linux|macos|instalacion|instalar|licencia|base de datos|\bsql\b|oracle|\bapi\b|integracion|plataforma|saas|navegador", 1.5),
        (r"guardar|exportar|importar|editor|\bcrm\b|\berp\b|ventanas? emergentes?|emergentes|\bpdf\b|documento|archivo|cuelga|no funciona|no responde|se congela", 1.5),
        (r"error|fallo|falla|se cierra|se bloquea|se cuelga|colapso|lento|rendimiento|configuracion|configurar|compatibilidad|caida|interrupcion|incidencia|funcionalidad", 1),
    ],
}
REGLAS_CATEGORIA = {c: [(re.compile(p), w) for p, w in rs] for c, rs in REGLAS_CATEGORIA.items()}

# Votos de las etiquetas de la fuente principal (tag_1..tag_8, ya en inglés)
VOTOS_ETIQUETA = {
    "security": ("Seguridad", 1), "data breach": ("Seguridad", 2), "virus": ("Seguridad", 2), "malware": ("Seguridad", 2),
    "data protection": ("Seguridad", 1), "login": ("Accesos", 2), "account": ("Accesos", 1),
    "network": ("Red", 1.5), "hardware": ("Hardware", 1.5), "software": ("Software", 1), "bug": ("Software", 0.75),
    "crash": ("Software", 0.75), "performance": ("Software", 0.5),
}
DESEMPATE = ["Seguridad", "Accesos", "Correo", "Red", "Hardware", "Software"]


# Menciones incidentales del correo ("envíe la información en un correo detallado") no indican la categoría Correo
INCIDENTAL_CORREO = re.compile(r"(por|mediante|a traves de|via) (un |el |su )?(detallado )?(correo|e-?mail)( electronico)?( detallado)?|"
                               r"en un (correo|e-?mail)( electronico)?( detallado)?|"
                               r"(envie|envienos|enviarme|enviarnos|responda|conteste|contacte)\w* .{0,40}(correo|e-?mail)")


def _puntaje_texto(texto):
    t = INCIDENTAL_CORREO.sub(" ", normalizar(texto))
    return {c: sum(w for rx, w in rs if rx.search(t)) for c, rs in REGLAS_CATEGORIA.items()}


def puntajes_categoria(titulo, descripcion, etiquetas=()):
    """El título pesa el doble que la descripción (dice de qué trata el ticket)."""
    pt, pd_ = _puntaje_texto(titulo), _puntaje_texto(descripcion)
    p = {c: 2 * pt[c] + pd_[c] for c in pt}
    for e in etiquetas:
        if e in VOTOS_ETIQUETA:
            c, w = VOTOS_ETIQUETA[e]
            p[c] += w
    return p


def categoria_por_reglas(titulo, descripcion="", etiquetas=()):
    """Devuelve (categoria, puntajes) o (None, puntajes) si no hay ninguna señal."""
    p = puntajes_categoria(titulo, descripcion, etiquetas)
    mejor = max(p.values())
    if mejor < 1:
        return None, p
    candidatas = [c for c in DESEMPATE if p[c] == mejor]
    return candidatas[0], p


# ------------------------------------------------------------------ relevancia de TI
NO_TI = re.compile(
    r"campanas? (publicitari|de marketing|digitales?)|rendimiento de (las |la )?campanas?|estrategias? (digital|de marca|de marketing|de crecimiento)|"
    r"metricas (de|del) (marketing|participacion|campana)|participacion en linea|medios sociales|redes sociales|\bseo\b|"
    r"trafico (del |de(l)? )?(sitio|web)|crecimiento de (la )?marca|desarrollo de la marca|audiencia objetivo|posicionamiento|"
    r"facturacion|reembolso|devolucion|\bfactura|precio|descuento|garantia|"
    r"estrategias? de inversion|politica de (privacidad|devoluciones)|"
    r"acuerdo de nivel de servicio|linea de tiempo de liberacion|comentarios (sobre|generales)|cuenta demo|caracteristica(s)? del producto|documentacion del producto")
# Si el texto menciona algo técnico, es de TI aunque el relato sea comercial (p. ej. "la plataforma de campañas se cayó")
PROBLEMA = re.compile(r"servidor|plataforma|sistema|software|aplicacion|herramienta|sitio web|base de datos|\bapi\b|integracion|error|fallo|falla|"
                      r"caida|\bvpn\b|\bred\b|acceso|contrasena|correo|dispositivo|conexion|actualizacion|instalacion|configuracion|"
                      r"sincroniz|cuelga|bloque|inactividad|lento|colaps|interrupcion|no funciona|no responde|desconect")

SENAL_TI = re.compile(
    r"error|fallo|falla|caida|servidor|sistema|aplicacion|software|conexion|acceso|contrasena|correo|dispositivo|actualizacion|"
    r"integracion|plataforma|base de datos|\bapi\b|red\b|virus|seguridad|impresora|equipo|datos|configuracion|instalacion|hardware|cuenta|usuario")


def es_ti(titulo, descripcion, categoria_fuerte=False):
    """False si el texto es claramente comercial/administrativo y no describe un problema o petición de TI."""
    t = normalizar(f"{titulo} {descripcion}")
    if categoria_fuerte:
        return True
    if NO_TI.search(t) and not PROBLEMA.search(t):
        return False
    return True


# ------------------------------------------------------------------ prioridad
PRIORIDAD_FUENTE = {"low": "Baja", "medium": "Media", "high": "Alta", "urgent": "Crítica"}
CRITICA = re.compile(
    r"caida total|caido por completo|totalmente caid|completamente caid|fuera de servicio|interrupcion (total|completa)|corte total|"
    r"servicio de produccion|entorno de produccion|sistemas? de produccion|sistema critico|critic[oa]s?\b|"
    r"toda la (empresa|organizacion|oficina|compania)|todos los (usuarios|empleados|departamentos|sistemas)|miles de usuarios|"
    r"no (se )?(puede|pueden) (trabajar|operar)|paralizad|operaciones detenidas|perdida (total )?de datos|brecha de datos|ransomware|"
    r"fallo (total|critico|generalizado)|apagon")
ETIQUETAS_CRITICAS = {"outage", "data breach"}
CRITICA_DEBIL = re.compile(r"interrupcion|caida|caido|fallo (?:del|de) sistema|colaps|multiples|varios (?:productos|sistemas|dispositivos)|"
                           r"inoperativ|no (?:esta )?disponible|degradacion|apagon|indisponib")


def prioridad_critica(texto, etiquetas, prioridad_base):
    """Alta + señales de caída total / producción / muchos usuarios -> Crítica."""
    if prioridad_base != "Alta":
        return prioridad_base
    t = normalizar(texto)
    fuerte = bool(CRITICA.search(t))
    etiqueta = bool(set(etiquetas) & ETIQUETAS_CRITICAS)
    return "Crítica" if fuerte or (etiqueta and CRITICA_DEBIL.search(t)) else prioridad_base


# ------------------------------------------------------------------ impacto, urgencia, usuarios afectados
IMPACTO_ALTO = re.compile(r"toda la (empresa|organizacion|oficina|compania)|todos los (usuarios|empleados|departamentos|clientes|sistemas)|"
                          r"miles de|cientos de|multiples (productos|sistemas|dispositivos|servicios)|varios (productos|sistemas|departamentos)|"
                          r"caida total|fuera de servicio|entorno de produccion|servicio de produccion|servidor(es)? (principal|de produccion|central)|"
                          r"toda la red|red corporativa|sistema critico|brecha|ransomware|perdida de datos")
IMPACTO_MEDIO = re.compile(r"\bequipo\b|departamento|varios (usuarios|empleados|dispositivos|equipos)|usuarios|empleados|clientes|servidor|"
                           r"sistema|plataforma|multiples|oficina|sucursal|nuestra (empresa|organizacion)|integracion")
IMPACTO_BAJO = re.compile(r"mi (portatil|ordenador|computadora|pc|equipo|teclado|raton|monitor|pantalla|cuenta|correo|impresora|telefono|dispositivo)|"
                          r"\bmi\b|\byo\b|estoy (teniendo|experimentando|intentando)|no puedo|me gustaria|puedo (tener|solicitar|obtener)")
URGENCIA_ALTA = re.compile(r"urgente|inmediat|cuanto antes|lo antes posible|critic[oa]|de inmediato|no puedo trabajar|no se puede trabajar|"
                           r"bloquead|paralizad|caid[oa]|fuera de servicio|sin servicio|no funciona (nada|nadie)|apagon|todo el dia|plazo|"
                           r"requiere atencion|atencion (urgente|inmediata)|inoperativ|se ha estrellado|ha colapsado|no responde")
URGENCIA_BAJA = re.compile(r"cuando (sea )?posible|sin prisa|consulta|pregunta|informacion|orientacion|asesoramiento|recomendacion|"
                           r"documentacion|me gustaria saber|podria (proporcionar|explicar|indicar)|como puedo|cual es|mejores practicas|guia|"
                           r"sugerencia|comentarios|interesado en|quisiera saber|buscando")

# Combinaciones (impacto, urgencia) por prioridad: suma de niveles 2-3 Baja, 4 Media, 5 Alta, 6 Crítica
def prioridad_matriz(i, u):
    s = IMPACTOS.index(i) + URGENCIAS.index(u) + 2
    return "Baja" if s <= 3 else "Media" if s == 4 else "Alta" if s == 5 else "Crítica"


COMBOS = {p: [(i, u) for i in IMPACTOS for u in URGENCIAS if prioridad_matriz(i, u) == p] for p in PRIORIDADES}
PORCENTAJE_EXCEPCIONES = 0.07
USUARIOS = {"Bajo": [1, 1, 1, 1, 2, 3], "Medio": [5, 8, 10, 15, 20, 30], "Alto": [50, 100, 100, 200, 500]}


def puntaje_impacto(texto):
    t = normalizar(texto)
    p = 0.5
    if IMPACTO_ALTO.search(t):
        p += 1.5
    elif IMPACTO_MEDIO.search(t):
        p += 0.8
    if IMPACTO_BAJO.search(t):
        p -= 0.4
    return p  # ~ 0.1 a 2.0 (0 = Bajo, 1 = Medio, 2 = Alto)


def puntaje_urgencia(texto):
    t = normalizar(texto)
    p = 0.8
    if URGENCIA_ALTA.search(t):
        p += 1.0
    if URGENCIA_BAJA.search(t):
        p -= 0.8
    return p


def asignar_impacto_urgencia(texto, prioridad, rng):
    """Elige la combinación (impacto, urgencia) coherente con la prioridad que mejor encaja con el texto.
    Con probabilidad PORCENTAJE_EXCEPCIONES se elige una combinación cuya matriz da la prioridad contigua
    (para que el MLP no aprenda solo la matriz). Devuelve (impacto, urgencia, es_excepcion)."""
    pi, pu = puntaje_impacto(texto), puntaje_urgencia(texto)
    destino = prioridad
    excepcion = False
    if rng.random() < PORCENTAJE_EXCEPCIONES:
        idx = PRIORIDADES.index(prioridad)
        vecinas = [PRIORIDADES[j] for j in (idx - 1, idx + 1) if 0 <= j < 4]
        destino = rng.choice(vecinas)
        excepcion = True
    combos = COMBOS[destino]
    mejor = min(combos, key=lambda c: abs(IMPACTOS.index(c[0]) - pi) + abs(URGENCIAS.index(c[1]) - pu) + rng.random() * 0.01)
    return mejor[0], mejor[1], excepcion


def usuarios_afectados(texto, impacto, rng):
    t = normalizar(texto)
    if impacto == "Alto" and re.search(r"toda la (empresa|organizacion|compania)|todos los (usuarios|empleados)|miles", t):
        return rng.choice([200, 500, 1000])
    if impacto == "Medio" and re.search(r"departamento|equipo", t):
        return rng.choice([5, 10, 15, 20])
    return rng.choice(USUARIOS[impacto])


def nuevo_rng():
    return random.Random(SEMILLA)
