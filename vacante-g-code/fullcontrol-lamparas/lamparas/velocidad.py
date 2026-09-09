"""
Bajar la velocidad donde el cordón sale al aire, como hace `Squeezy Fidget Toy`.

Medido sobre esa pieza —la referencia impresa del repo— hay que separar DOS
cosas, y confundirlas lleva a aplicar la regla donde no va:

    zona                     sección     velocidad      caudal
    cúpulas (z<28, z>70)     0.961 mm2   480 siempre    7.7 mm3/s
    celosía (z 30..70)       0.501 mm2   480, y 240     4.0 mm3/s
                             (la mitad)  donde flota

1. **La sección cambia por ZONA, no por voladizo.** La celosía lleva la mitad de
   sección que las cúpulas, y con tres decimales de constancia: es un valor
   declarado. Dentro de cada zona no varía, esté el cordón apoyado o al aire.

2. **La velocidad baja a la mitad donde flota, pero SÓLO dentro de la celosía.**
   Ahí los segmentos a 240 están al aire el 71.5 % del tiempo contra el 37.7 %
   de los de 480. En las cúpulas no hay modulación ninguna: sus 653 segmentos al
   aire corren a 480 y caudal pleno, igual que el resto.

**Cuidado con la conclusión.** Una pared maciza —nuestras roscas, sus cúpulas—
Squeezy la imprime a velocidad y caudal CONSTANTES. Este módulo traduce lo que
hace en la celosía, que es otra cosa: una estructura de hilos que cruzan en el
aire por diseño. Usarlo en una pared maciza es ir más allá de lo que la
referencia respalda, no reproducirla.

La primera medición que hice acá daba "70.4 % al aire a 240 contra 12.3 % a 480"
sobre la pieza ENTERA, y de ahí saqué que la velocidad seguía al voladizo. Era
una correlación de zona: la celosía es a la vez la parte lenta y la parte al
aire. Separando por zona aparece el cuadro real.

Por qué dentro de la vuelta
---------------------------
En una cúpula el voladizo depende de la altura, así que alcanza con una rampa
por z (`gen_rosca --velocidad-en`). En una rosca no: el hilo sube y baja el
radio una vez por vuelta, así que en la MISMA altura hay ángulos donde la pared
se apoya en la vuelta de abajo y ángulos donde sale al aire. Una rampa por
altura no puede distinguirlos.

Acá el voladizo se mide punto contra punto: cuánto se corrió el radio respecto
del punto que está una vuelta más abajo, en el mismo ángulo. Si creció, ese
cordón está colgando esa fracción de su ancho.

    frac = max(0, r_i - r_(i-N)) / ancho

`N` no se pide: se mide del propio recorrido, contando cuántos puntos hay en
una vuelta de ángulo. Pedirlo sería confiar en que quien llama pasó el mismo
`segmentos_por_capa` que usó el generador, y ese es el tipo de dato duplicado
que en este repo ya rompió cosas.

El gradiente, y por qué no es un escalón
----------------------------------------
Squeezy conmuta entre dos valores. Acá se interpola, porque el voladizo de una
rosca cambia de forma continua a lo largo de la vuelta y un escalón metería un
cambio de velocidad brusco varias veces por vuelta. Es además lo que el artículo
de Claywoven identifica como la diferencia entre su intento fallido y el bueno:
el mínimo era el mismo, lo que cambió fue llegar con un gradiente.
"""
import math

import fullcontrol as fc

# mm/min. Los dos números medidos sobre `Squeezy Fidget Toy.gcode`.
SQUEEZY_NORMAL = 480
SQUEEZY_VOLADIZO = 240


def _puntos_y_radios(pasos, cx, cy):
    idx = [i for i, p in enumerate(pasos) if isinstance(p, fc.Point)]
    rad = [math.hypot(pasos[i].x - cx, pasos[i].y - cy) for i in idx]
    ang = [math.atan2(pasos[i].y - cy, pasos[i].x - cx) for i in idx]
    return idx, rad, ang


def _puntos_por_vuelta(ang):
    """Cuántos puntos entran en una vuelta de ángulo, medido del recorrido."""
    d = []
    for a, b in zip(ang, ang[1:]):
        x = (b - a + math.pi) % (2 * math.pi) - math.pi
        if abs(x) > 1e-9:
            d.append(abs(x))
    if not d:
        return None
    return max(1, round(2 * math.pi / sorted(d)[len(d) // 2]))


def modular_por_voladizo(pasos, centro, ancho, rapida, lenta,
                         umbral=None, salto_minimo=30.0):
    """
    Devuelve una copia de `pasos` con cambios de velocidad donde hay voladizo.

    `umbral` es qué fracción del cordón tiene que colgar para llegar a `lenta`.
    Con `None` se toma el PEOR voladizo de la propia pieza, y esa es la opción
    sana: una rosca nunca alcanza la condición de Squeezy —su peor punto cuelga
    0.276 mm, el 23 % del cordón, contra segmentos enteros al aire— así que un
    umbral fijo de 1.0 deja la velocidad casi sin tocar (mínimo 1810 de 2400) y
    la modulación no hace nada. Normalizando contra el máximo de la pieza, el
    punto más colgado recibe exactamente `lenta` y el resto interpola.

    `salto_minimo` evita escribir un `F` por cada punto: sólo se emite cuando el
    valor cambia más que eso.

    Devuelve `(pasos_nuevos, estadística)`, donde la estadística trae cuántos
    puntos quedaron a cada velocidad y cuánto se estima que alarga la pieza.
    """
    cx, cy = centro
    idx, rad, ang = _puntos_y_radios(pasos, cx, cy)
    n = _puntos_por_vuelta(ang)
    if not n or len(idx) <= n:
        return list(pasos), None

    fracs = [0.0] * n + [max(0.0, rad[k] - rad[k - n]) / ancho
                         for k in range(n, len(idx))]
    if umbral is None:
        # El PERCENTIL 99, no el máximo. Con el máximo, un patrón que prende y
        # apaga el hilo —`interrumpida`— tiene 123 puntos de 44 824 colgando el
        # 165 % del cordón, en los bordes de sector, y esos fijan la escala: el
        # resto de la pieza queda casi sin frenar. Es la misma trampa que
        # `verificar_encastre.por_vuelta`, y se resuelve igual.
        orden = sorted(fracs)
        umbral = orden[min(len(orden) - 1, int(0.99 * len(orden)))]
    vel = [rapida if umbral <= 0 else
           rapida + (lenta - rapida) * min(1.0, f / umbral) for f in fracs]

    nuevo = []
    ultima = [None]
    j = 0
    for i, p in enumerate(pasos):
        if isinstance(p, fc.Point) and j < len(vel):
            v = vel[j]
            if ultima[0] is None or abs(v - ultima[0]) >= salto_minimo:
                nuevo.append(fc.Printer(print_speed=round(v)))
                ultima[0] = v
            j += 1
        nuevo.append(p)

    # Cuánto alarga: el tiempo es largo/velocidad, y el largo de cada tramo sale
    # del propio recorrido. Sin esto uno no sabe si "más lento" son dos minutos
    # o dos horas.
    t_rapida = t_modulada = 0.0
    for k in range(1, len(idx)):
        a, b = pasos[idx[k - 1]], pasos[idx[k]]
        largo = math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
        t_rapida += largo / rapida
        t_modulada += largo / vel[k]
    lentos = sum(1 for v in vel if v < rapida - salto_minimo)
    return nuevo, {
        "umbral": umbral,
        "peor_frac": max(fracs),
        "puntos": len(vel),
        "lentos": lentos,
        "frac_lentos": lentos / len(vel),
        "v_min": min(vel),
        "cambios": sum(1 for x in nuevo if isinstance(x, fc.Printer)),
        "minutos_sin": t_rapida,
        "minutos_con": t_modulada,
    }


# Tope de caudal del filamento, mm3/s. Sacado de los `.gcode.3mf` que el usuario
# imprimió: `filament_max_volumetric_speed = 12,16,16,16` -> 12 el PLA, 16 el
# PETG. Su macho de PLA corre exactamente a 12.0: Orca le bajó la velocidad de
# 120 mm/s a 33.5 para no pasarse. Nosotros no teníamos ese freno.
CAUDAL_MAX = {"PLA": 12.0, "PETG": 16.0}

# Perfiles de material, sacados de los mismos `.gcode.3mf` impresos. Las cuatro
# ranuras del archivo son PLA;PETG;PETG;PETG y los valores van en ese orden, así
# que el PLA es siempre el primero.
#
#     nozzle_temperature = 220,245,245,245
#     hot_plate_temp     = 65,70,70,70
#     fan_min_speed      = 60,20,20,20      fan_max = 80,60,60,60
#
# El ventilador real medido en el archivo oscila entre 178 y 201 de 255, o sea
# 70 a 79 %: se toma 75.
MATERIALES = {
    "PLA":  {"boquilla": 220, "cama": 65, "ventilador": 75, "caudal": 12.0},
    "PETG": {"boquilla": 245, "cama": 80, "ventilador": 50, "caudal": 16.0},
}


def _secciones_por_largo(pasos):
    """
    `(sección, mm de recorrido)` de cada tramo, leído de los propios pasos.

    Pesa por LARGO y no por cantidad de `ExtrusionGeometry`, y la diferencia no
    es cosmética: `generar_pieza` sólo emite la marca cuando la sección CAMBIA
    más de 0.005, así que un tramo largo y parejo deja una sola marca y un tramo
    que varía deja cientos. Contando marcas, los tramos gordos —que son los que
    varían— pesan de más y cualquier percentil sale sesgado hacia ellos.
    """
    tramos = []
    area = None
    extruyendo = True
    ant = None
    for paso in pasos:
        if isinstance(paso, fc.ExtrusionGeometry):
            if paso.width and paso.height:
                area = paso.width * paso.height
        elif isinstance(paso, fc.Extruder):
            if paso.on is not None:
                extruyendo = bool(paso.on)
        elif isinstance(paso, fc.Point):
            xyz = (paso.x, paso.y, paso.z)
            if None in xyz and ant is not None:
                xyz = tuple(b if a is None else a for a, b in zip(xyz, ant))
            if None in xyz:
                continue
            if ant is not None and area is not None and extruyendo:
                d = math.dist(ant, xyz)
                if d > 1e-9:
                    tramos.append((area, d))
            ant = xyz
    return tramos


def _percentil_por_largo(tramos, q):
    """La sección que deja por debajo la fracción `q` del RECORRIDO."""
    if not tramos:
        return None
    tramos = sorted(tramos)
    objetivo = q * sum(d for _, d in tramos)
    acum = 0.0
    for a, d in tramos:
        acum += d
        if acum >= objetivo:
            return a
    return tramos[-1][0]


def area_emitida(pasos, q: float = 0.5):
    """
    Sección que el recorrido realmente deposita, leída de los propios
    `ExtrusionGeometry`. Por defecto la MEDIANA, o sea la sección típica.

    No se calcula como `ancho * altura_capa`: esa cuenta usa la SUBIDA y la
    sección va con la SEPARACIÓN sobre la superficie, que con el flanco del hilo
    a 43° es un 34 % mayor. `gen_rosca` anunciaba 14.7 mm3/s mientras emitía
    19.7 — la misma confusión de alturas que `MAPA.md` lista como causa de la
    mitad de los defectos de la pieza.
    """
    return _percentil_por_largo(_secciones_por_largo(pasos), q)


# Percentil con el que se frena. NO es la mediana, y no es el máximo.
#
# Con la mediana, en cuanto la sección varía los picos se escapan: el cupón de
# caritas medía 0.303 de mediana y 0.511 de máximo, así que frenando por la
# mediana el 10 % del recorrido corría por encima del tope de PLA y llegaba a
# 18.2 mm3/s contra 12. Pedirle al extrusor más de lo que funde no sale como
# plástico de más: sale como línea fina e irregular, que es justo el defecto que
# se está persiguiendo.
#
# Con el máximo tampoco. Los picos son RAROS —medido sobre ese mismo cupón, el
# 2.7 % del recorrido pasa de 0.40 y el 0.1 % de 0.45— así que frenar por el
# máximo cuesta un 41 % de tiempo en toda la pieza para cubrir el 0.1 % del
# recorrido.
PERCENTIL_FRENO = 0.99


def caudal(pasos, velocidad, q: float = 0.5):
    """mm3/s reales a esa velocidad (mm/min), o None si no se puede medir."""
    a = area_emitida(pasos, q)
    return None if a is None else a * velocidad / 60.0


def caudal_pico(pasos, velocidad):
    """El caudal del tramo gordo, que es el que decide si sub-extruye."""
    return caudal(pasos, velocidad, PERCENTIL_FRENO)


def velocidad_para(pasos, caudal_max):
    """
    La velocidad (mm/min) más alta a la que NINGÚN tramo pasa de `caudal_max`.

    Se mide sobre `PERCENTIL_FRENO`, no sobre la mediana: lo que hay que
    respetar es el tramo más gordo, no el típico.
    """
    a = area_emitida(pasos, PERCENTIL_FRENO)
    return None if a is None else caudal_max * 60.0 / a
