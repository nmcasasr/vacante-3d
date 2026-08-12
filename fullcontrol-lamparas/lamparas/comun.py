"""
Infraestructura compartida por todos los diseños de lámparas.

La idea es que cada script de `lamparas/` solo tenga que describir *la forma*
(una función que devuelve el radio en función del ángulo y de la altura) y que
todo lo demás -- estado inicial de la impresora, generación de la espiral,
exportación del .gcode -- viva acá y no se duplique.
"""

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

import fullcontrol as fc

# Carpeta donde se dejan los .gcode generados (está en .gitignore)
DIR_OUTPUT = Path(__file__).resolve().parent.parent / "output"

# Una función de radio recibe (angulo_rad, t) y devuelve el radio en mm.
# `t` va de 0.0 (base) a 1.0 (tope), así la forma puede evolucionar en altura.
FuncionRadio = Callable[[float, float], float]


@dataclass
class Perfil:
    """
    Parámetros de impresión (no de forma).

    Los valores por defecto corresponden a una Bambu Lab A1 con boquilla de
    0.8 mm imprimiendo PLA en modo vaso con capas gruesas.
    """

    diametro_boquilla: float = 0.8      # mm - la boquilla física
    altura_capa: float = 0.4            # mm - capa gruesa, líneas marcadas

    # Ancho del cordón. Si queda en None se usa el diámetro de boquilla, que es
    # lo habitual. Se puede pedir más (hasta ~2x la boquilla) para una pared más
    # gruesa y opaca, o menos para una más fina: no es una orden a la impresora
    # sino cuánto plástico se empuja, y el cordón se aplasta hasta ese ancho.
    ancho_linea: Optional[float] = None
    diametro_filamento: float = 1.75    # mm
    velocidad_impresion: int = 1200     # mm/min
    velocidad_viaje: int = 6000         # mm/min
    temp_boquilla: int = 200            # °C (PLA)
    temp_cama: int = 55                 # °C
    ventilador: int = 100               # % (modo vaso quiere refrigeración alta)

    # La A1 tiene el origen en la esquina frontal-izquierda de la cama, así que
    # una lámpara centrada en (0, 0) quedaría fuera. Todo se traslada a `centro`.
    centro: Tuple[float, float] = (128.0, 128.0)
    tamano_cama: Tuple[float, float] = (256.0, 256.0)

    # Incluir G29 (nivelación de cama) en el start gcode.
    nivelar: bool = True

    # Start/end gcode. Si quedan en None se usan las secuencias para A1 de
    # `impresoras.py`. Para usar las de Bambu Studio:
    #     Perfil(start_gcode=cargar_gcode("mi_start.gcode"))
    start_gcode: Optional[str] = None
    end_gcode: Optional[str] = None

    # Perfil de impresora de FullControl. 'generic' es solo el vehículo: no
    # aporta start gcode propio, lo aporta `start_gcode` de acá.
    nombre_impresora: str = "generic"

    @property
    def ancho(self) -> float:
        """Ancho efectivo del cordón: el pedido, o el de la boquilla."""
        return self.ancho_linea if self.ancho_linea is not None else self.diametro_boquilla

    @property
    def area_extrusion(self) -> float:
        """mm² de sección de cada línea extruida (modelo rectangular)."""
        return self.ancho * self.altura_capa

    def start(self) -> str:
        from .impresoras import start_a1

        return self.start_gcode if self.start_gcode is not None else start_a1(self)

    def end(self) -> str:
        from .impresoras import end_a1

        return self.end_gcode if self.end_gcode is not None else end_a1(self)


def pasos_iniciales(perfil: Perfil) -> list:
    """
    Estado inicial de la impresora: geometría de extrusión y velocidades.

    Las temperaturas y el ventilador NO se ponen acá: se pasan por
    `initialization_data` en `a_gcode()` y el perfil de impresora de FullControl
    ya emite los M104/M140/M106 correspondientes. Si se hiciera en los dos
    lados, el gcode quedaría con los comandos duplicados.
    """
    return [
        fc.ExtrusionGeometry(
            area_model="rectangle",
            width=perfil.ancho,
            height=perfil.altura_capa,
        ),
        fc.Printer(
            print_speed=perfil.velocidad_impresion,
            travel_speed=perfil.velocidad_viaje,
        ),
    ]


def _verificar_cama(radio_max: float, perfil: Perfil) -> None:
    """Avisa (sin abortar) si la pieza se sale de la cama."""
    cx, cy = perfil.centro
    ancho, largo = perfil.tamano_cama
    margen = perfil.ancho / 2
    if (
        cx - radio_max - margen < 0
        or cy - radio_max - margen < 0
        or cx + radio_max + margen > ancho
        or cy + radio_max + margen > largo
    ):
        print(
            f"AVISO: con radio máximo {radio_max:.1f} mm y centro {perfil.centro} "
            f"la pieza se sale de una cama de {ancho:.0f}x{largo:.0f} mm."
        )


PASO_MINIMO = 0.05   # mm: por debajo de esto la vuelta no aporta nada y son miles
# Cuánto tiene que saltar el radio entre dos puntos para que el tramo cuente
# como puente al aire y no como pared. Tres milímetros son varias veces un
# cordón: nada que sea pared se corre tanto de un punto al siguiente.
SALTO_PUENTE = 3.0   # mm


def marcha_vertical(radio_medio, altura: float, paso: float,
                    minimo: float = PASO_MINIMO, pendiente=None):
    """
    Cuánto sube cada vuelta, para que la separación SOBRE LA SUPERFICIE sea
    constante. Devuelve (ts, zs), el `t` y la altura de cada vuelta.

    Con un paso vertical fijo la separación real es `paso/cos(theta)`, con theta
    el ángulo de la pared. En un cilindro theta=0 y da igual; en una cúpula la
    pared se tumba y la separación se dispara —medido en la cabeza del hongo,
    0.400 mm en el ecuador y 1.264 arriba, más que el cordón— y ahí las vueltas
    dejan de tocarse. Así que `dz = paso * cos(theta)`.

    El ángulo NO depende de dz, que es lo que evita resolverlo iterativamente:
    si R(t) es el radio medio, `tan(theta) = |dR/dz| = |dR/dt| / altura`, porque
    `dt = dz/altura`. Queda fórmula cerrada y se marcha acumulando, porque ni el
    número de vueltas ni el `t` de cada una se saben de antemano.

    Vive acá y no en quien la use porque la usan DOS: el generador, para emitir
    las vueltas, y `perfil.voladizo`, para avisar cuáles no van a pegar. Con una
    copia en cada lado, el aviso describía un recorrido que no era el que se
    imprimía: subestimaba la peor separación casi a la mitad.
    """
    def paso_en(t: float) -> float:
        # La ventana de la derivada tiene que ser MÁS ANCHA que el detalle más
        # fino de la silueta, o se mide la discretización en vez de la forma.
        if pendiente is not None:
            dR = pendiente(t)
        else:
            h = 5e-3
            a, b = min(1.0, t + h), max(0.0, t - h)
            dR = (radio_medio(a) - radio_medio(b)) / ((a - b) or 1e-9)
        tan = abs(dR) / max(altura, 1e-9)
        return paso / math.sqrt(1 + tan * tan)

    ts, zs = [0.0], [0.0]
    t = z = 0.0
    while t < 1.0 and len(ts) < 20000:
        dz = max(minimo, paso_en(t))
        t = min(1.0, t + dz / max(altura, 1e-9))
        z += dz
        ts.append(t)
        zs.append(z)
    return ts, zs


def radio_de_hueco(diametro: float, ancho: float, holgura: float = 0.3) -> float:
    """
    Radio del recorrido para que quede libre `diametro`.

    El cordón se deposita centrado en la trayectoria, así que el agujero sale
    un cordón más chico de lo que dice el radio. Un Ø33 recorrido con cordón de
    1.2 queda en Ø31.8 y la pieza que iba ahí no entra. Se suma además una
    holgura de ajuste, que para un encastre impreso es del orden de 0.3 mm.

    Args:
        diametro: el que tiene que quedar libre al final, en mm.
        ancho: ancho del cordón.
        holgura: juego para que entre sin forzar.
    """
    return (diametro + ancho + holgura) / 2


def _espiral_base(forma: Callable[[float], float], perfil: Perfil, paso_arco: float = 1.0,
                  radio_interior: float = 0.0, refuerzo: int = 0):
    """
    Espiral que rellena el fondo de la pieza, del centro hacia afuera. Es lo que
    le da piso a un bowl sin romper el trazo continuo del modo vaso: se imprime
    toda la base y se sigue de largo con la pared.

    `forma(angulo) -> radio` es el contorno de la pared. La espiral MORFA con
    él: cada vuelta es una copia a escala de la silueta, no un círculo. En una
    pieza cuyo radio ondula (el twist va de 36 a 44 mm) una base circular
    sobresale donde la pared se mete, y se ve un anillo que no pertenece a la
    figura.

    El avance se calcula contra el radio MÁXIMO del contorno. Así la separación
    entre vueltas nunca supera `perfil.ancho` — en la parte ancha da justo, y en
    la angosta quedan más juntas, o sea con más solape. Al revés (avanzar contra
    el mínimo) la parte ancha quedaría con huecos y la base saldría calada.

    `refuerzo` son vueltas CIRCULARES pegadas al borde del hueco antes de que
    empiece la espiral. El borde de un agujero hecho de un solo cordón es lo más
    frágil de la pieza, y justo ahí es donde encastra otra: son las vueltas que
    reciben el esfuerzo. Van circulares y no morfando hacia el contorno, porque
    lo que hay que reforzar es el círculo, no la silueta.

    Con `radio_interior` la base deja un hueco: la espiral arranca en una
    CIRCUNFERENCIA exacta de ese radio y de ahí morfa hacia el contorno. Que la
    primera vuelta sea un círculo y no una copia a escala del contorno no es un
    detalle: el hueco existe para que encaje otra pieza, y una pieza no encaja
    en un agujero con forma de silueta.

    Devuelve (puntos, angulo_final) para que la pared arranque justo donde
    termina la base y no quede un salto.
    """
    cx, cy = perfil.centro
    z = perfil.altura_capa
    r_max = max(forma(k / 180 * math.pi) for k in range(360)) or 1.0
    ri = max(0.0, radio_interior)
    if ri >= r_max:
        raise ValueError(f"el hueco (r={ri:.1f}) no cabe en la base (r_max={r_max:.1f})")
    # El avance se mide contra el ANCHO del anillo, no contra el radio: con un
    # hueco grande el anillo puede ser una franja angosta, y usar r_max daría
    # dos o tres vueltas para algo que necesita diez.
    avance = perfil.ancho / (r_max - ri)
    puntos = []
    angulo = 0.0

    # El collar: vueltas apiladas HACIA ARRIBA en el borde del hueco, antes del
    # piso. Va primero para que su primera vuelta se pegue a la cama, y termina
    # con un viaje —sin extruir— de vuelta al radio del hueco a la altura del
    # piso, que es donde arranca la espiral.
    #
    # La primera versión de esto avanzaba un cordón por VUELTA, igual que la
    # espiral del piso, así que agregaba un tramo idéntico al que ya había: un
    # no-op que no se notó hasta medir el g-code. Un refuerzo que vale es el que
    # sube, no el que se repite en el plano.
    n_ref = max(0, int(refuerzo))
    if n_ref and ri > 0:
        vueltas = 0.0
        while vueltas < n_ref:
            zc = z + vueltas * perfil.altura_capa
            puntos.append(fc.Point(x=cx + ri * math.cos(angulo),
                                   y=cy + ri * math.sin(angulo), z=zc))
            angulo += paso_arco / max(ri, 0.6)
            vueltas = angulo / (2 * math.pi)
        # bajar sin extruir hasta el arranque del piso
        puntos.append(fc.Extruder(on=False))
        puntos.append(fc.Point(x=cx + ri * math.cos(angulo),
                               y=cy + ri * math.sin(angulo), z=z))
        puntos.append(fc.Extruder(on=True))

    # El ángulo del collar NO cuenta para la espiral del piso. `s` se calcula
    # como `avance * angulo / 2pi`, así que arrastrar los 8 giros del collar
    # hacía arrancar el piso al 23% del anillo: quedaba un agujero enorme
    # alrededor del hueco, justo lo que el collar venía a reforzar.
    ang0 = angulo
    s = 0.0
    while s <= 1.0:
        r = ri + s * (forma(angulo) - ri)
        puntos.append(fc.Point(x=cx + r * math.cos(angulo), y=cy + r * math.sin(angulo), z=z))
        # paso angular adaptativo: segmentos de largo ~constante en toda la espiral
        angulo += paso_arco / max(r, 0.6)
        s = avance * (angulo - ang0) / (2 * math.pi)
    # cierre exacto sobre el contorno, para empalmar con la pared
    puntos.append(fc.Point(x=cx + forma(angulo) * math.cos(angulo),
                           y=cy + forma(angulo) * math.sin(angulo), z=z))
    return puntos, angulo


# Lo que el preview necesita para traducir un click en la pantalla a las
# coordenadas en las que están escritos los toques. `t` no es "altura sobre la
# cama dividido la altura de la pieza": la base sólida ocupa unas capas abajo y
# las capas de transición suben menos que las demás, así que el mapeo no es la
# regla de tres que uno supondría. Adivinarlo desde el gcode significa poner los
# toques unos milímetros más arriba de donde se los pintó, y eso se ve.
# Lo llena `generar_pieza`, que es la única que lo sabe de verdad.
ULTIMO_MAPEO: dict = {}


def generar_pieza(
    funcion_radio: FuncionRadio,
    altura: float,
    perfil: Optional[Perfil] = None,
    segmentos_por_capa: int = 200,
    espiral: bool = True,
    capas_base: int = 1,
    funcion_dz: Optional[FuncionRadio] = None,
    funcion_dangulo: Optional[FuncionRadio] = None,
    base_solida: bool = False,
    hueco: float = 0.0,   # diámetro FINAL del agujero del piso, en mm
    refuerzo_hueco: int = 0,
    capas_transicion: int = 6,
    paso_z: Optional[float] = None,
    silueta_referencia: Optional[Callable[[float], float]] = None,
    cambios: Optional[dict] = None,
    modulacion: Optional[dict] = None,
    pintura: Optional[dict] = None,
) -> list:
    """
    Construye los pasos de FullControl para un sólido de revolución cuyo radio
    lo define `funcion_radio(angulo, t)`.

    Args:
        funcion_radio: radio en mm para un ángulo (rad) y una altura relativa t (0..1).
        altura: altura total de la pared en mm.
        perfil: parámetros de impresión. Si es None se usa `Perfil()`.
        segmentos_por_capa: resolución angular. Los patrones finos necesitan
            bastante: como mínimo unos 6 segmentos por lóbulo.
        espiral: modo vaso, con la Z subiendo de forma continua en cada vuelta.
        capas_base: primeras vueltas planas (sin rampa de Z), para adherencia.
        funcion_dz: desplazamiento de Z en mm, `(angulo, t) -> dz`. Es lo que
            permite las celosías: si la Z ondula dentro de la vuelta y la fase
            se invierte capa a capa, las capas se tocan solo en los cruces y
            entre medio queda el calado.
        funcion_dangulo: corrimiento angular en radianes, `(angulo, t) -> dang`.
            Sin esto el ángulo solo avanza y el recorrido nunca puede volver
            sobre sí mismo. Con esto sí, y ahí aparecen los rizos: si el
            corrimiento retrocede más rápido de lo que avanza el ángulo, el
            trazo cierra un bucle en vez de ondular.
        base_solida: rellena el fondo con una espiral antes de empezar la pared
        hueco: diámetro que tiene que QUEDAR libre en el piso, en mm. No es el
            del recorrido: el cordón va centrado en la trayectoria, así que se
            come medio cordón por lado. Acá se compensa (ver `radio_de_hueco`),
            porque pedir el diámetro del recorrido es pedirle al usuario que
            haga una cuenta que la máquina ya sabe hacer.
            (necesario para un bowl que tenga que contener algo).
        capas_transicion: en las primeras capas el patrón se mezcla desde un
            círculo liso hasta su forma completa. Evita el escalón contra la
            base y mejora el agarre.
        paso_z: cuánto sube la pieza por vuelta, en mm. Por defecto la altura de
            capa, que es lo normal. Las celosías necesitan un paso MAYOR que su
            oscilación de Z: si la vuelta de arriba ondula ±A y solo sube 0.4,
            en las crestas termina 1 mm por debajo de la vuelta anterior y la
            boquilla vuelve a meterse en material ya impreso. Con paso_z >= 2*A
            las vueltas se tocan en los nodos y nunca se pisan.
        silueta_referencia: silueta lisa `t -> radio`, solo para medir el
            voladizo. Sin esto la medición usa el radio medio de cada vuelta,
            que en los patrones con relieve variable da falsos positivos.
        modulacion: cambia velocidad, ventilador y ancho DENTRO de cada vuelta,
            según en qué punto de la onda de `funcion_dz` esté el recorrido.
            `{'velocidad': (nodo, pico), 'ventilador': (nodo, pico), 'ancho': (nodo, pico)}`,
            interpolando entre los dos valores.

            El valle de `funcion_dz` es el CRUCE con la vuelta de abajo (ahí las
            dos se muerden y hay que soldar); la cresta es el PICO, el punto de
            máximo voladizo, donde el cordón está puenteando al aire. O sea que
            la propia onda del patrón dice dónde estamos, sin que el diseño
            tenga que exponer nada.

            Sirve para lo que el patrón pide a gritos: más material y menos aire
            en los cruces, y máximo aire y mínima velocidad en los picos.

        pintura: pintar una figura CON COLOR, cambiando de filamento al entrar y
            al salir del dibujo. `{'mascara': fn, 'entrar': bloque, 'salir': bloque}`,
            donde `mascara(angulo, t) -> 0..1` dice dónde va el dibujo y los
            bloques son los que devuelve `colores.cambio_ams()`.

            A diferencia de `cambios`, que va por altura, esto dispara **dentro
            de la vuelta**, en el punto exacto donde el recorrido entra o sale
            de la figura. Es lo único que permite pintar una forma que no sea
            una banda horizontal.

            Leé el aviso que imprime: cada cambio son ~56 s de máquina y el
            color nuevo tarda un par de vueltas en salir limpio, así que un
            dibujo con detalle sale carísimo y borroneado. Ver el docstring de
            `lamparas/superficie.py`.

        cambios: `{altura_mm: bloque}`. El bloque se inserta en el punto donde
            el recorrido cruza esa altura. Sirve para cambiar de color: ver
            `lamparas/colores.py`. El bloque puede ser una cadena de gcode, un
            paso de FullControl ya armado, o un **callable** que recibe el
            último punto impreso y devuelve el gcode — que es lo que usa el
            cambio por AMS, porque necesita saber adónde volver.

    Returns:
        La lista de pasos lista para `fc.transform(...)`.
    """
    perfil = perfil or Perfil()
    cx, cy = perfil.centro
    paso = paso_z or perfil.altura_capa

    # La pendiente que gobierna el paso es la del PEOR ÁNGULO, no la del radio
    # medio. Con el medio, una deformación angular —que saca por un lado y mete
    # por el otro— no lo mueve, el generador cree que la pared sigue vertical y
    # no frena: las vueltas quedan separadas varios milímetros en radio mientras
    # la Z sube igual, y entre ellas quedan huecos. Con el peor ángulo, el paso
    # se desploma justo donde la pared se tumba y las vueltas se acuestan una
    # contra otra, que es lo que hace imprimible una repisa.
    N_ANG = 32

    def _pendiente(t: float, h: float = 5e-3) -> float:
        a, b = min(1.0, t + h), max(0.0, t - h)
        dt = (a - b) or 1e-9
        peor = 0.0
        for k in range(N_ANG):
            ang = k / N_ANG * 2 * math.pi
            peor = max(peor, abs(funcion_radio(ang, a) - funcion_radio(ang, b)) / dt)
        return peor

    ts, zs = marcha_vertical(None, altura, paso, pendiente=_pendiente)
    n_capas = max(1, len(ts) - 1)
    angulos = [seg / segmentos_por_capa * 2 * math.pi for seg in range(segmentos_por_capa + 1)]

    # radio medio de la primera capa: define el tamaño de la base y el punto de
    # partida de la transición
    radios_capa0 = [funcion_radio(a, 0.0) for a in angulos[:-1]]
    radio_medio_0 = sum(radios_capa0) / len(radios_capa0)

    pasos = pasos_iniciales(perfil)
    puntos: list = []
    angulo_inicio = 0.0

    if base_solida:
        # La base sigue el CONTORNO de la pared, no un círculo. Ver _espiral_base.
        # El piso también declara su cordón. Sale antes que la pared y sin esto
        # queda sin anotar: el injerto tiene que inventarle una capa semilla,
        # que después no cierra contra la primera capa de la pared.
        puntos.append(fc.ManualGcode(text=f";Z:{perfil.altura_capa:.3f}"))
        puntos.append(fc.ManualGcode(text=f";WIDTH:{perfil.ancho:.3f}"))
        puntos.append(fc.ManualGcode(text=f"; LINE_WIDTH: {perfil.ancho:.3f}"))
        puntos.append(fc.ManualGcode(text=f";HEIGHT:{perfil.altura_capa:.3f}"))
        puntos_base, angulo_inicio = _espiral_base(
            lambda a: funcion_radio(a, 0.0), perfil,
            radio_interior=radio_de_hueco(hueco, perfil.ancho) if hueco else 0.0,
            refuerzo=refuerzo_hueco)
        puntos.extend(puntos_base)

    # con base sólida la pared arranca una capa más arriba, encima del fondo
    z_offset = perfil.altura_capa if base_solida else 0.0

    radio_max = 0.0
    radios_medios = []
    # La altura de extrusión vigente. En lista para poder tocarla desde adentro
    # del bucle sin declarar `nonlocal` en cada función anidada.
    ultimo_alto = [perfil.altura_capa]
    # Radio del punto anterior, para detectar los saltos que son puentes.
    radio_previo = [None]

    def _mezcla(capa: int) -> float:
        """Cuánto del patrón está activo en esta vuelta: 0 en la primera, 1 al final."""
        return min(1.0, capa / capas_transicion) if capas_transicion > 0 else 1.0

    # El paso vertical tiene que crecer JUNTO con la amplitud del patrón, nunca
    # antes. Si se sube el paso completo mientras la onda todavía está atenuada,
    # la vuelta no llega a tocar la de abajo y quedan anillos sueltos en el aire.
    # El piso de altura_capa es para que la parte maciza suba como una capa normal.
    # La subida de cada vuelta sale de la marcha de arriba, pero atenuada igual
    # que el patrón durante la transición: subir el paso completo mientras la
    # onda todavía está apagada deja la vuelta sin tocar la de abajo.
    # ¿La pieza tiene patrón angular? Si el radio no varía con el ángulo, no hay
    # ninguna amplitud que ir levantando y la transición no tiene sentido.
    variacion_angular = max(
        (max(funcion_radio(a, t) for a in angulos[:-1])
         - min(funcion_radio(a, t) for a in angulos[:-1]))
        for t in (0.0, 0.25, 0.5, 0.75, 1.0)
    )

    # La subida de cada vuelta. La atenuación por transición se aplica SOLO si
    # hay patrón angular que levantar.
    #
    # Sin esa condición, las primeras cinco vueltas de una pieza lisa subían
    # 0.067, 0.133, 0.200, 0.267 y 0.333 mm, y como la extrusión sigue a la
    # separación, salían cordones de 1.2 x 0.067 —18:1— justo en la base. Se
    # veía como un anillo azul oscuro en el mapa de ancho de línea de Orca.
    #
    # El razonamiento original era que el paso debía crecer junto con la
    # amplitud del patrón, "porque si no la vuelta no llega a tocar la de
    # abajo". Está al revés: `zs` ya sale de `marcha_vertical` calculada con el
    # patrón a amplitud COMPLETA, así que durante la transición —cuando la pared
    # todavía está lisa— ese paso ya es conservador.
    #
    # NO va ningún piso propio acá, y esto es importante: `marcha_vertical`
    # avanza `t` junto con `dz`, así que la altura de cada vuelta y el `t` con
    # el que se evalúa la silueta son la misma cuenta. Subir un paso por debajo
    # estira la silueta en esa zona y cambia la FORMA de la pieza: un piso de
    # media capa dejó la cabeza del hongo 10 mm más alta y abombada.
    def _paso_capa(c: int) -> float:
        crudo = zs[c] - zs[c - 1]
        if variacion_angular > 0.02:
            crudo = max(PASO_MINIMO, crudo * _mezcla(c))
        return crudo

    pasos_capa = [perfil.altura_capa] + [_paso_capa(c) for c in range(1, n_capas + 1)]

    # --- modulación dentro de la vuelta -------------------------------------
    # La amplitud de la onda se mide muestreándola, en vez de pedírsela al
    # patrón: así esto funciona con cualquier `funcion_dz` sin que el diseño
    # tenga que exponer su amplitud.
    amplitud_onda = 0.0
    if modulacion and funcion_dz is not None:
        amplitud_onda = max(
            abs(funcion_dz(s / 400 * 2 * math.pi, 0.5)) for s in range(401)
        )
    modular = bool(modulacion) and amplitud_onda > 1e-9
    ultimo = {"velocidad": None, "ventilador": None, "ancho": None, "k": None, "nodo": 0}

    def _pasos_modulacion(dz_crudo: float) -> list:
        """
        Pasos a insertar antes del punto, según dónde caiga en la onda.

        k = 0 en el valle (el CRUCE con la vuelta de abajo: hay que soldar) y
        k = 1 en la cresta (el PICO: el cordón está puenteando al aire).
        Se emite solo cuando el valor cuantizado cambia, si no el gcode se
        llenaría de comandos redundantes: son cientos de segmentos por vuelta.
        """
        k = min(1.0, max(0.0, (dz_crudo / amplitud_onda + 1) / 2))
        salida = []

        # Espera en el CRUCE: parar con la boquilla quieta deja que la soldadura
        # con la vuelta de abajo cuaje antes de salir al aire otra vez, así el
        # puente siguiente arranca de un anclaje sólido en vez de tirar de
        # material blando. Es la técnica del gcode de "Squeezy Fidget Toy":
        # retraer, G4, volver a cebar.
        #
        # La retracción NO es opcional: parar con la boquilla presurizada deja
        # un grumo. En extrusión relativa (M83) el -R y el +R se cancelan, así
        # que la contabilidad de E de FullControl no se entera y queda intacta.
        #
        # Se dispara en el FLANCO de bajada: k cruza el umbral una vez por nodo,
        # no en cada uno de los cientos de puntos que hay cerca del valle.
        espera = modulacion.get("espera")
        if espera:
            ms, retraccion, cada = espera
            previo = ultimo["k"]
            if previo is not None and previo >= 0.15 > k:
                ultimo["nodo"] += 1
                if ultimo["nodo"] % max(1, cada) == 0:
                    salida.append(fc.ManualGcode(
                        text=f"G1 E-{retraccion} F1800\nG4 P{ms} ; esperar a que suelde el cruce\n"
                             f"G1 E{retraccion} F1800"
                    ))
        ultimo["k"] = k

        rango = modulacion.get("velocidad")
        if rango:
            v = int(round((rango[0] + (rango[1] - rango[0]) * k) / 30.0) * 30)
            if v != ultimo["velocidad"]:
                salida.append(fc.Printer(print_speed=v))
                ultimo["velocidad"] = v

        rango = modulacion.get("ventilador")
        if rango:
            f = int(round((rango[0] + (rango[1] - rango[0]) * k) / 5.0) * 5)
            if f != ultimo["ventilador"]:
                salida.append(fc.Fan(speed_percent=f))
                ultimo["ventilador"] = f

        rango = modulacion.get("ancho")
        if rango:
            # ESCALÓN, no rampa. Copiado del gcode de "Squeezy Fidget Toy":
            # cordón fino en todo el vano y un blob gordo justo en el cruce, en
            # vez de un degradé. Medido ahí: 0.950 mm² en los tramos horizontales
            # contra 0.501 mm² en los que tienen pendiente — 53 %, un escalón
            # limpio. Se ve a ojo en el visor de flujo de Orca: puntos verdes
            # sobre malla azul.
            #
            # Gana en los dos frentes al mismo tiempo: menos masa colgando en el
            # puente (descuelga menos y cuaja antes) y más material justo donde
            # tiene que soldar. Una rampa lineal reparte mal las dos cosas.
            w = rango[0] if k < 0.15 else rango[1]
            w = round(w / 0.05) * 0.05
            if w != ultimo["ancho"]:
                salida.append(
                    fc.ExtrusionGeometry(area_model="rectangle", width=w, height=perfil.altura_capa)
                )
                ultimo["ancho"] = w

        return salida

    # --- pintura: cambios de color DENTRO de la vuelta -----------------------
    # Se dispara en el flanco: la máscara cambia de 0 a 1 (o al revés) entre un
    # punto y el siguiente, y ahí va el bloque. El bloque necesita saber dónde
    # está la boquilla, y eso es el ÚLTIMO punto ya emitido — el mismo criterio
    # que usa `_insertar_cambios`, y por el mismo motivo: volver al punto que
    # todavía no se imprimió se saltearía ese tramo de pared.
    pintando = {"estado": None, "n": 0}

    def _pintar(angulo_p: float, t_p: float) -> None:
        if not pintura:
            return
        dentro = pintura["mascara"](angulo_p, t_p) > 0.5
        if pintando["estado"] is None:
            pintando["estado"] = dentro
            return
        if dentro == pintando["estado"]:
            return
        anterior = next((q for q in reversed(puntos) if isinstance(q, fc.Point)), None)
        if anterior is None:
            pintando["estado"] = dentro
            return
        bloque = pintura["entrar"] if dentro else pintura["salir"]
        puntos.append(fc.ManualGcode(text=bloque(anterior, perfil.velocidad_impresion)))
        pintando["estado"] = dentro
        pintando["n"] += 1

    # Con base sólida la pared arranca A LA ALTURA del piso y sube rampando en
    # su primera vuelta, en vez de saltar una capa de golpe. El salto dejaba un
    # movimiento que extruía subiendo 0.400 mm con 0.03 mm de avance en XY: un
    # cordón vertical en el aire, que además el mapa de solape marcaba en rojo
    # porque no tiene vecino debajo. Rampando, la pared nace del piso.
    z_vuelta = z_offset if base_solida else z_offset + pasos_capa[0]

    # z de t=0 (arranque de la pared) y de t=1 (última vuelta), más las alturas
    # exactas de cada vuelta: con eso el preview invierte z -> t sin suponer que
    # la espiral sube parejo, que es justo lo que no hace abajo.
    ULTIMO_MAPEO.clear()
    ULTIMO_MAPEO.update({
        "z0": z_vuelta,
        "z1": z_vuelta + sum(pasos_capa[1:n_capas + 1]),
        "capas": n_capas,
        "z_capa": [z_vuelta + sum(pasos_capa[1:c + 1]) for c in range(n_capas + 1)],
    })

    for capa in range(n_capas):
        # La primera capa va a z = altura_capa, no a z = 0: a z = 0 la boquilla
        # estaría apoyada contra la cama.
        z_capa = z_vuelta
        subida = pasos_capa[capa + 1]  # lo que sube esta vuelta hasta la siguiente
        z_vuelta += subida
        rampa = espiral and (capa >= capas_base or (base_solida and capa == 0))
        mezcla = _mezcla(capa)

        # Cuánto material lleva ESTA vuelta.
        #
        # NO es `subida`. Ese fue el defecto que dejó la cabeza del hongo con
        # 0.157 mm de pared arriba —papel de seda, azul oscuro en el mapa de
        # ancho de línea de Orca— y el 4.07 % del recorrido con el cordón por
        # debajo de 0.10 mm, contra el 0.26 % de `Squeezy Fidget Toy.gcode`.
        #
        # El razonamiento que lo puso ahí era que con altura fija "se empujaba
        # plástico para 0.40 mm en un hueco de 0.20". Pero ese hueco no es
        # `subida`: donde la pared se tumba, la vuelta siguiente no se apoya
        # encima sino AL LADO, y el hueco real es la separación medida SOBRE LA
        # SUPERFICIE, `hypot(subida, Δradio)`. Y esa separación es justamente lo
        # que `marcha_vertical` mantiene constante en `altura_capa`: para eso
        # divide por sqrt(1+tan²). Escalar la extrusión con la componente
        # vertical descuenta dos veces el mismo coseno.
        #
        # Medido sobre la cúpula de las dos piezas, vuelta por vuelta:
        #
        #     Squeezy   separación 0.800 constante · área 0.960 CONSTANTE
        #     hongo     separación 0.400 constante · área 0.330 -> 0.063
        #
        # Las dos mantienen bien la separación. La diferencia era solo esto.
        # Anotación de cordón para el visor, SIN crear capas.
        #
        # No se emite `; CHANGE_LAYER` / `; Z_HEIGHT:` / `; LAYER_HEIGHT:`, y el
        # motivo es concreto: de eso ya se encarga el injerto
        # (`ext-gcode/gcode-preview/src/bambu.ts`), que emite las capas por Z
        # REAL y avisa en su propio comentario que `; Z_HEIGHT:` es autoritativo
        # y que emitirlo mal destruye la vista previa. Además usa la PRIMERA
        # línea `; CHANGE_LAYER` como marca para saber dónde termina el
        # start-gcode de la plantilla (`HEAD_END`), así que meter 425 más deja
        # la pieza cortada por la mitad en Orca. Ya pasó.
        #
        # Lo que sí hace falta declarar es el ancho del cordón: el injerto lo
        # deduce anclándose en el ancho nominal de la PLANTILLA, que no es el
        # nuestro, y de ahí sale un mapa de ancho que no corresponde a la pieza.
        # `;WIDTH:` y `;HEIGHT:` son anotaciones puras: no arman capas y no
        # pueden romper nada.
        # El ancho en los DOS dialectos. Orca es un fork de BambuStudio y Bambu
        # escribe sus etiquetas con espacio (`; FEATURE:`, `; LAYER_HEIGHT:`);
        # el estilo Prusa va pegado (`;WIDTH:`). Emitiendo solo el de Prusa,
        # Orca lo ignoraba y deducía el ancho como area/altura, que es de donde
        # salía el color cambiando a lo largo de la pieza.
        puntos.append(fc.ManualGcode(text=f";WIDTH:{perfil.ancho:.3f}"))
        # `; LINE_WIDTH:` es el nombre que Orca lee. NO es `;WIDTH:` (Prusa) ni
        # `; WIDTH:`. Se sacó abriendo un g-code hecho por el propio Orca:
        #
        #     ; CHANGE_LAYER
        #     ; Z_HEIGHT: 0.2
        #     ; LAYER_HEIGHT: 0.2
        #     ; LINE_WIDTH: 0.42
        #
        # Con el nombre equivocado Orca ignoraba el ancho y lo deducía como
        # area/altura, y ahí no había forma de ganar: la altura que hace que
        # apile bien los cordones (la subida real) es la que hace que deduzca un
        # ancho disparatado. Con el nombre correcto son dos cosas independientes.
        puntos.append(fc.ManualGcode(text=f"; LINE_WIDTH: {perfil.ancho:.3f}"))

        tan_v = _pendiente(ts[capa]) / max(altura, 1e-9)
        # `subida` ya viene atenuada por `_mezcla` y con piso en PASO_MINIMO,
        # así que la separación se reconstruye desde ella y no desde `paso`.
        separacion = subida * math.sqrt(1 + tan_v * tan_v)
        # Donde el paso choca contra el piso, la separación se dispara y un
        # cordón solo no llena el hueco. Se extruye lo que se pueda y el
        # voladizo lo denuncia `_verificar_voladizo`; seguir subiendo la sección
        # solo pondría una soga colgando.
        separacion = min(separacion, 1.5 * perfil.altura_capa)
        # `;HEIGHT:` es la altura del CORDÓN para el visor, o sea cuánto ocupa en
        # vertical. Eso es `subida`, no `separacion`.
        #
        # Va variando —0.400 abajo, 0.050 donde el ala se acuesta— y ahí está la
        # gracia: el injerto solo puede declarar UNA altura para toda la pieza,
        # y donde la vuelta sube menos que ese número el visor apila varias
        # pasadas dibujadas más altas de lo que son. Se ve como un aro en la
        # cúpula. Bajando la constante del injerto de 0.400 a 0.274 el aro se
        # corrió hacia arriba y se achicó, que es lo que confirmó el mecanismo.
        # Con la altura real por capa no hay ninguna constante que desajustar.
        # La altura del cordón NO es la separación vertical: es cuánto ocupa el
        # cordón en vertical, y el cordón ROTA con la superficie.
        #
        # La sección es un rectángulo `separacion x ancho` apoyado sobre la
        # pared. Con la pared vertical queda 1.2 de ancho por 0.4 de alto; con
        # la pared acostada queda 0.4 de ancho por 1.2 de alto. Girado un ángulo
        # theta, su extensión vertical es `separacion*cos(theta) + ancho*sin(theta)`,
        # y `separacion*cos(theta)` es justamente `subida`.
        #
        # Importa porque el visor deduce el ancho como area/altura y NO lee el
        # `;WIDTH:` que emitimos — comprobado: declarando `subida` (0.050 arriba)
        # Orca pintaba 0.48/0.05 = 9.6 y saturaba la escala en 2.00. Con la
        # altura real da 0.48/1.24 = 0.39, que es el ancho que de verdad tiene
        # el cordón ahí: la pared acostada avanza 0.4 por vuelta en radio.
        # La z del TECHO de esta vuelta, aparte de la altura del cordón. Son dos
        # cosas distintas y el visor necesita las dos: con la pared acostada el
        # cordón mide 1.2 de alto mientras la vuelta sube 0.05, así que los
        # cordones se solapan y la altura NO sirve para apilar capas.
        puntos.append(fc.ManualGcode(text=f";Z:{z_capa + subida:.3f}"))
        # Y la altura del cordón, CONSTANTE, porque el cordón es constante: la
        # sección que se deposita vale `ancho x separacion` en toda la pieza.
        #
        # No se declara ni la subida vertical ni la altura del cordón rotado.
        # Las dos varían y las dos hacen que el visor pinte un ancho que cambia
        # a lo largo de la pieza —dedujo 9.6 mm con una y 0.38 con la otra—
        # cuando lo que de verdad se extruye no cambia nunca. El visor calcula
        # ancho = area/altura y no lee `;WIDTH:`, así que declarar la altura
        # nominal es lo único que le hace pintar el cordón que realmente hay.
        #
        # Se puede hacer porque el apilado ya no depende de esto: la z de cada
        # capa la lleva `;Z:` por separado.
        # La altura vuelve a ser la SUBIDA REAL: es la que hace que el visor
        # apile los cordones donde van y la que elimina el aro. Comprobado en
        # los dos sentidos: con altura constante el aro aparece, con la subida
        # real desaparece. El ancho ya no depende de esto si Orca lee `; WIDTH:`.
        puntos.append(fc.ManualGcode(text=f";HEIGHT:{subida:.3f}"))
        if abs(separacion - ultimo_alto[0]) > 0.005:
            puntos.append(fc.ExtrusionGeometry(area_model="rectangle",
                                               width=perfil.ancho, height=separacion))
            ultimo_alto[0] = separacion

        # se calcula la vuelta entera primero para poder mezclarla con su propio
        # radio medio durante la transición
        crudos = []
        for seg in range(segmentos_por_capa + 1):  # +1 para cerrar la vuelta
            fraccion = seg / segmentos_por_capa
            # Ángulo ACUMULADO a lo largo de toda la espiral, no reiniciado en
            # cada vuelta. Para un patrón de n lóbulos enteros da igual, pero
            # permite usar frecuencias de medio lóbulo (n + 0.5): así el patrón
            # se invierte solo de una vuelta a la otra, que es lo que teje la
            # malla, y sin ningún salto en la costura.
            angulo = angulo_inicio + (capa + fraccion) * 2 * math.pi
            # `t` avanza dentro de la capa y sale de la marcha, no de una regla de
            # tres: las vueltas ya no suben todas lo mismo.
            t = ts[capa] + (ts[capa + 1] - ts[capa]) * fraccion
            crudos.append((fraccion, angulo, t, funcion_radio(angulo, t)))

        medio = sum(r for _, _, _, r in crudos[:-1]) / segmentos_por_capa
        radios_medios.append(medio)

        for fraccion, angulo, t, radio_crudo in crudos:
            radio = medio + (radio_crudo - medio) * mezcla
            radio_max = max(radio_max, radio)
            z = z_capa + fraccion * subida if rampa else z_capa
            dz_crudo = funcion_dz(angulo, t) if funcion_dz is not None else 0.0
            z += dz_crudo * mezcla
            if modular:
                puntos.extend(_pasos_modulacion(dz_crudo))
            _pintar(angulo, t)
            # el corrimiento angular solo afecta la POSICIÓN; el `angulo` que
            # ven las funciones de forma sigue siendo el que avanza parejo
            angulo_pos = angulo
            if funcion_dangulo is not None:
                angulo_pos += funcion_dangulo(angulo, t) * mezcla

            # Un salto radial grande no es pared: es un puente al aire de punta
            # a punta. La altura de extrusión de la vuelta —que con paso
            # adaptativo puede ser 0.05 mm— lo convierte en un hilo de la tercera
            # parte del grosor, que es lo que se veía como una reja de hilos
            # finos cruzando el vacío. Un puente tiene que salir con el grosor
            # del cordón normal: es lo único que le da material para llegar al
            # otro lado. Después se vuelve a la altura de la vuelta.
            salto = abs(radio - radio_previo[0]) if radio_previo[0] is not None else 0.0
            puentea = salto > SALTO_PUENTE
            if puentea:
                puntos.append(fc.ExtrusionGeometry(
                    area_model="rectangle", width=perfil.ancho, height=perfil.altura_capa))
            puntos.append(
                fc.Point(
                    x=cx + radio * math.cos(angulo_pos),
                    y=cy + radio * math.sin(angulo_pos),
                    z=z,
                )
            )
            if puentea:
                puntos.append(fc.ExtrusionGeometry(
                    area_model="rectangle", width=perfil.ancho, height=ultimo_alto[0]))
            radio_previo[0] = radio

    # Viaje sin extruir hasta el primer punto y recién ahí se abre el extrusor.
    # Con primer='no_primer' esto es necesario: FullControl necesita un punto
    # previo para poder calcular la longitud de la primera línea extruida.
    # `puntos` puede traer pasos de modulación intercalados, así que el viaje
    # inicial tiene que apuntar al primer PUNTO, no al primer elemento.
    primero = next(i for i, p in enumerate(puntos) if isinstance(p, fc.Point))
    pasos.extend(puntos[:primero])
    pasos.append(fc.Extruder(on=False))
    pasos.append(puntos[primero])
    pasos.append(fc.Extruder(on=True))
    resto = puntos[primero + 1:]
    pasos.extend(
        _insertar_cambios(resto, cambios, puntos[primero], perfil.velocidad_impresion)
        if cambios else resto
    )

    if pintura and pintando["n"]:
        _avisar_pintura(pintando["n"])
    _verificar_cama(radio_max, perfil)
    solo_puntos = [p for p in puntos if isinstance(p, fc.Point)]
    _verificar_apoyo(solo_puntos[len(solo_puntos) - n_capas * (segmentos_por_capa + 1):],
                     segmentos_por_capa + 1, perfil)
    if silueta_referencia is not None:
        radios_medios = [silueta_referencia(capa / n_capas) for capa in range(n_capas + 1)]
    _verificar_voladizo(radios_medios, paso, perfil.ancho)
    return pasos


# Segundos de máquina por cambio de filamento del AMS. 29 s de descarga + 25 s
# de carga, del `project_settings.config` de Bambu, más el viaje. Verificado
# aparte contra los marcadores M73 de un gcode laminado de 64 cambios: mediana
# de 60 s, y 55 % del tiempo total de esa pieza. No incluye torre de purga —
# nuestro bloque no construye ninguna.
SEGUNDOS_POR_CAMBIO = 56


def _avisar_pintura(n: int) -> None:
    """
    Avisa cuánto cuesta pintar con cambios de filamento. No aborta: es una
    decisión de quien imprime, pero tiene que verla antes y no después.
    """
    horas = n * SEGUNDOS_POR_CAMBIO / 3600
    print(
        f"AVISO: la pintura mete {n} cambios de filamento. A ~{SEGUNDOS_POR_CAMBIO} s "
        f"cada uno son {horas:.1f} h SOLO en cambiar, aparte del tiempo de impresión."
    )
    print(
        "       Y el color no va a salir limpio: a radio 40 una vuelta consume 33 mm "
        "de filamento y un blanco->negro tarda ~70 mm en limpiarse, o sea 2 vueltas. "
        "Cada tramo pintado que dure menos que eso sale mezclado con el anterior."
    )


def _insertar_cambios(puntos: list, cambios: dict, punto_previo=None, velocidad=None) -> list:
    """
    Mete cada bloque de gcode en el punto donde el recorrido cruza su altura.

    En los diseños donde la Z ondula dentro de la vuelta (celosía) el cruce
    puede caer en una cresta y adelantar el cambio media vuelta. A la escala de
    un cambio de color da igual.

    `punto_previo` es el punto anterior al primero de `puntos`: hace falta
    porque un cambio que caiga en el primer punto tiene que poder decir dónde
    estaba la boquilla antes.

    `velocidad` es la de impresión vigente, en mm/min. Se va siguiendo a lo
    largo del recorrido —la cambian tanto la modulación por nodo como un
    `--velocidad-en`— porque el bloque del AMS tiene que reponerla al terminar:
    emite `F` para sus propios movimientos y FullControl no la vuelve a emitir,
    ya que para él nunca cambió.
    """
    pendientes = sorted(cambios.items(), key=lambda kv: kv[0])
    salida, i = [], 0
    ultimo = punto_previo
    for punto in puntos:
        if isinstance(punto, fc.Printer) and punto.print_speed is not None:
            velocidad = punto.print_speed
        # La lista puede traer pasos que no son puntos (cambios de velocidad,
        # ventilador o ancho que inyecta la modulación por nodo). Esos no tienen
        # altura: se copian tal cual sin mirarlos.
        if not isinstance(punto, fc.Point):
            salida.append(punto)
            continue
        while i < len(pendientes) and punto.z >= pendientes[i][0]:
            bloque = pendientes[i][1]
            # Un callable es un bloque que necesita saber DÓNDE se lo inserta:
            # el cambio por AMS se lleva la boquilla fuera de la cama y tiene
            # que volver sola. Se lo llama con el último punto YA IMPRESO, que
            # es donde está la boquilla de verdad — no con `punto`, que todavía
            # no se imprimió: volver ahí se saltearía ese tramo de pared.
            if callable(bloque):
                bloque = bloque(ultimo if ultimo is not None else punto, velocidad)
            # Un cambio de velocidad insertado por altura (`--velocidad-en`)
            # también corre el estado, y puede caer justo antes de un cambio.
            if isinstance(bloque, fc.Printer) and bloque.print_speed is not None:
                velocidad = bloque.print_speed
            # Un str es gcode crudo (los cambios de color). Cualquier otra cosa
            # es un paso de FullControl ya armado — `fc.Printer(print_speed=...)`
            # para cambiar de velocidad, por ejemplo. Va tal cual, para que
            # FullControl siga el estado en vez de que le pisemos la F a mano.
            salida.append(fc.ManualGcode(text=bloque) if isinstance(bloque, str) else bloque)
            i += 1
        salida.append(punto)
        ultimo = punto
    if i < len(pendientes):
        faltan = [f"{a:.1f}" for a, _ in pendientes[i:]]
        print(
            f"AVISO: {len(pendientes) - i} cambio(s) quedan por encima de la pieza "
            f"y no se insertaron (alturas: {', '.join(faltan)} mm)."
        )
    return salida


def _verificar_apoyo(puntos_pared: list, por_vuelta: int, perfil: Perfil) -> None:
    """
    Avisa si alguna vuelta no llega a tocar la de abajo en NINGÚN punto.

    Es el control que separa una celosía de un montón de anillos sueltos. Una
    vuelta puede estar despegada en casi toda su longitud (eso es justamente el
    calado), pero si en toda la vuelta no hay un solo punto donde el hueco baje
    de la altura de capa, esa vuelta se imprime en el aire y la pieza se cae.
    """
    flotantes = []
    n_vueltas = len(puntos_pared) // por_vuelta
    for v in range(1, n_vueltas):
        anterior = puntos_pared[(v - 1) * por_vuelta : v * por_vuelta]
        actual = puntos_pared[v * por_vuelta : (v + 1) * por_vuelta]
        if len(actual) < por_vuelta:
            break
        hueco = min(a.z - b.z for a, b in zip(actual, anterior))
        if hueco > perfil.altura_capa + 1e-6:
            flotantes.append((v, hueco))
    if flotantes:
        v, hueco = flotantes[0]
        print(
            f"AVISO: {len(flotantes)} vuelta(s) no tocan la de abajo en ningún punto "
            f"(la primera es la {v}, con {hueco:.2f} mm de hueco mínimo). "
            "Se van a imprimir en el aire: bajá el paso vertical o subí la "
            "amplitud del patrón."
        )


def _verificar_voladizo(radios_medios: list, paso: float, ancho: float = 0.8) -> None:
    """
    Avisa si la silueta se abre demasiado rápido.

    En modo vaso cada vuelta se apoya sobre la de abajo. Si el radio crece más
    que el ancho de línea por vuelta, la vuelta queda colgando en el aire. El
    ángulo se mide desde la vertical: 45° es el límite cómodo, más de 55° suele
    descolgarse.
    """
    if len(radios_medios) < 2:
        return
    saltos = [radios_medios[i + 1] - radios_medios[i] for i in range(len(radios_medios) - 1)]
    salto_max = max(saltos, default=0.0)
    angulo = math.degrees(math.atan2(salto_max, paso))
    # El número que decide si se cae NO es el ángulo sino cuánto se corre el
    # radio entre dos vueltas contra el ancho del cordón: eso es el solape con
    # el que apoya la vuelta nueva. Bajar la velocidad ayuda a que el cordón
    # cuaje, pero no le devuelve apoyo a algo que quedó en el aire.
    solape = ancho - salto_max
    if solape < 0:
        print(
            f"ERROR de voladizo: el radio crece {salto_max:.2f} mm por vuelta y el cordón mide "
            f"{ancho:.2f} mm. La vuelta nueva NO TOCA la anterior: se cae seguro. "
            f"({angulo:.0f}° desde la vertical.)"
        )
    elif solape < ancho * 0.5:
        print(
            f"AVISO: el radio crece {salto_max:.2f} mm por vuelta y el cordón mide {ancho:.2f} mm, "
            f"o sea {100*solape/ancho:.0f}% de solape ({angulo:.0f}° desde la vertical). "
            "Por debajo del 50% conviene bajar la velocidad y subir el ventilador en esa zona; "
            "por debajo del 25% no esperes que salga."
        )
    elif angulo > 45:
        print(
            f"Voladizo máximo {angulo:.0f}° desde la vertical: {salto_max:.2f} mm de radio por "
            f"vuelta, {100*solape/ancho:.0f}% de solape sobre un cordón de {ancho:.2f} mm. Imprimible."
        )


# nombre viejo, se mantiene para los diseños que ya lo usan
generar_lampara = generar_pieza


def a_gcode(pasos: list, perfil: Optional[Perfil] = None) -> str:
    """
    Convierte los pasos en una cadena de gcode lista para imprimir, con el
    start/end gcode de la impresora incluido. No escribe ningún archivo.
    """
    perfil = perfil or Perfil()
    # El start/end gcode se inyecta como texto crudo alrededor del diseño.
    # Las temperaturas y el ventilador viven ahí, no en initialization_data,
    # para que no queden comandos duplicados.
    completos = [fc.ManualGcode(text=perfil.start())] + pasos + [fc.ManualGcode(text=perfil.end())]
    return fc.transform(
        completos,
        "gcode",
        fc.GcodeControls(
            printer_name=perfil.nombre_impresora,
            initialization_data={
                # La purga ya la hace el start gcode de arriba.
                "primer": "no_primer",
                "print_speed": perfil.velocidad_impresion,
                "travel_speed": perfil.velocidad_viaje,
                "extrusion_width": perfil.ancho,
                "extrusion_height": perfil.altura_capa,
                "dia_feed": perfil.diametro_filamento,
            },
        ),
        show_tips=False,
    )


# Flags con clave=valor que se convierten en controles. Son los que llevan los
# parámetros de patrón, estructura, pintura y silueta.
_FLAGS_KV = ("--p", "--pe", "--pp", "--ps")

# Flags sueltos que también vale la pena exponer, con su rango.
_FLAGS_SUELTOS = {
    "--altura": (20.0, 300.0),
    "--radio-base": (5.0, 110.0),
    "--radio-boca": (5.0, 110.0),
    "--radio-max": (5.0, 110.0),
    "--ancho-linea": (0.3, 1.6),
    "--velocidad": (120.0, 6000.0),
}


def _rango(clave: str, valor: float):
    """
    Rango razonable para un control, a partir del nombre y del valor actual.

    Se adivina en vez de declararse en cada módulo a propósito: un parámetro
    nuevo aparece como control sin que haya que registrarlo en ningún lado, que
    es lo que hace que valga la pena mantenerlo. Los nombres que sabemos que son
    fracciones o cuentas enteras se tratan aparte; el resto sale del valor.
    """
    if clave.startswith("t_") or clave.endswith("_t") or clave in ("persistencia", "borde", "vuelo_alto"):
        return 0.0, 1.0, 0.01
    if clave in ("octavas", "modos", "cantidad", "dientes", "escala", "n_lados", "semilla", "alternar"):
        tope = max(4.0, valor * 4)
        return 0.0, tope, 1.0
    if "grados" in clave:
        return 0.0, 360.0, 5.0
    tope = max(1.0, abs(valor) * 3)
    return 0.0, tope, tope / 200


def descripciones_de(func) -> dict:
    """
    Saca `{parámetro: descripción}` del bloque `Args:` del docstring de `func`.

    Se lee del docstring en vez de mantener una tabla aparte a propósito: la
    tabla se desincroniza en cuanto alguien agrega un parámetro y se olvida de
    registrarlo, y entonces el tooltip miente — que es peor que no tenerlo. El
    docstring en cambio se escribe igual porque es lo que uno lee en el código.

    Reconoce el formato de Google (`nombre: texto`, con continuaciones más
    indentadas), que es el que usa todo el repo.
    """
    import inspect
    import re

    doc = inspect.getdoc(func) or ""
    if "Args:" not in doc:
        return {}
    cuerpo = doc.split("Args:", 1)[1]
    # el bloque termina en la próxima sección de nivel cero
    for corte in ("\nReturns:", "\nRaises:", "\nNota:", "\n##"):
        if corte in cuerpo:
            cuerpo = cuerpo.split(corte, 1)[0]

    def claves_pendientes(clave, partes, salida):
        for k in clave or []:
            salida[k] = " ".join(partes)
        return ()

    # La sangría de las entradas se MIDE, no se asume. `textwrap.dedent` acá no
    # sirve: le alcanza una sola línea sin sangrar en el bloque para que el
    # prefijo común sea 0 y no saque nada — y entonces todas las entradas se
    # leen como continuaciones y el resultado es un solo parámetro fantasma con
    # todo el texto pegado.
    lineas = [l for l in cuerpo.splitlines() if l.strip()]
    if not lineas:
        return {}
    sangria = len(lineas[0]) - len(lineas[0].lstrip())

    salida, clave, partes = {}, None, []
    for linea in lineas:
        propia = len(linea) - len(linea.lstrip())
        # Acepta `nombre: texto` y también `a, b, c: texto` — varios docstrings
        # documentan juntos los parámetros que van juntos, y sin esto la
        # descripción del primero se comía la de todos los siguientes.
        m = (re.match(r"^([\w, ]+): (.*)$", linea.strip())
             if propia <= sangria else None)
        if m:
            for k in claves_pendientes(clave, partes, salida):
                pass
            clave, partes = [x.strip() for x in m.group(1).split(",")], [m.group(2)]
        elif clave:
            partes.append(linea.strip())
    claves_pendientes(clave, partes, salida)

    # Solo lo que puede ser un parámetro de verdad: una frase de prosa que
    # termina en dos puntos ("Es la silueta para una matera: pared vertical…")
    # calza con el patrón y entraría como un parámetro fantasma.
    salida = {k: v for k, v in salida.items() if k.isidentifier()}
    # Los docstrings de acá explican largo; el tooltip quiere lo esencial.
    return {k: (v if len(v) <= 260 else v[:257].rsplit(" ", 1)[0] + "…") for k, v in salida.items()}


def encabezado_receta(argv: list, modulo: str) -> str:
    """
    El comando que generó la pieza, como comentario para meter en el gcode.

    El `.params.json` vive en `output/`, que está en `.gitignore`: si se borra
    esa carpeta, los parámetros se van con ella y la pieza queda huérfana. El
    gcode en cambio es lo que uno guarda, manda o imprime, así que lleva el
    comando adentro y se describe solo.

    Va como comentario, o sea que la impresora lo ignora. Y va ANTES del start
    gcode, así que el empaquetador del .3mf —que corta en el marcador de fin de
    start gcode— lo descarta al empaquetar sin que estorbe.
    """
    partes = [f"python -m {modulo}"] + [str(a) for a in argv[1:]]
    linea = " ".join(partes)
    envuelto = []
    actual = ""
    for palabra in linea.split(" "):
        if len(actual) + len(palabra) + 1 > 88:
            envuelto.append(actual)
            actual = "    " + palabra
        else:
            actual = (actual + " " + palabra) if actual else palabra
    envuelto.append(actual)
    cuerpo = "\n".join(f"; {l}" for l in envuelto)
    return (
        ";===== RECETA ==================================================\n"
        "; Este archivo se generó con el comando de abajo. Volvé a correrlo\n"
        "; para reproducirlo, o cambiale un número para variarlo.\n"
        f"{cuerpo}\n"
        ";===============================================================\n"
    )


def guardar_receta(nombre: str, argv: list, modulo: str, descripciones: dict = None,
                   extra: dict = None) -> Path:
    """
    Deja un `<nombre>.params.json` al lado del gcode, con cómo se generó.

    Es lo que le permite al preview ofrecer controles: la extensión lee la
    receta, arma un slider por cada parámetro numérico y vuelve a invocar este
    mismo comando con el valor cambiado. El gcode nunca se edita — se regenera,
    así que no hay forma de que la pieza y sus parámetros se desincronicen, que
    es el problema que tiene editar el gcode a mano.

    Args:
        nombre: el mismo que se le pasó a `guardar_gcode`.
        argv: `sys.argv`, tal cual.
        modulo: cómo volver a invocar esto, p.ej. "lamparas.bowls". Hace falta
            porque `sys.argv[0]` de un `python -m paquete` es la ruta del
            `__main__.py`, y correr ESE archivo directo rompe los imports
            relativos del paquete. Lo que hay que reconstruir es `-m modulo`.
        extra: se mezcla tal cual en la receta. Por ahí va el mapeo z<->t, que
            el preview necesita para saber a qué `t` corresponde un click.
    """
    import json
    import sys

    controles = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in _FLAGS_KV and i + 1 < len(argv) and "=" in argv[i + 1]:
            clave, _, valor = argv[i + 1].partition("=")
            try:
                v = float(valor)
            except ValueError:
                i += 2
                continue
            mn, mx, paso = _rango(clave, v)
            controles.append({"flag": a, "clave": clave, "valor": v,
                              "min": mn, "max": mx, "paso": paso,
                              "que": (descripciones or {}).get(a, {}).get(clave, "")})
            i += 2
            continue
        if a in _FLAGS_SUELTOS and i + 1 < len(argv):
            try:
                v = float(argv[i + 1])
            except ValueError:
                i += 2
                continue
            mn, mx = _FLAGS_SUELTOS[a]
            controles.append({"flag": a, "clave": a.lstrip("-"), "valor": v,
                              "min": mn, "max": mx, "paso": (mx - mn) / 200,
                              "que": (descripciones or {}).get("", {}).get(a, "")})
            i += 2
            continue
        i += 1

    receta = {
        "python": sys.executable,
        "cwd": str(Path.cwd()),
        # Los argumentos con los que se vuelve a invocar, ya listos para
        # `spawn(python, args)`. No es `sys.argv`: ver el docstring.
        "args": ["-m", modulo] + list(argv[1:]),
        "nombre": nombre,
        # Con esto la extensión baja la resolución mientras arrastrás: 1.8 s en
        # vez de 8.6 s. Al soltar regenera completo.
        # Lo que la extensión agrega mientras arrastrás un slider: baja la
        # resolución para ir rápido, y NO deja receta — si la dejara, el
        # `--segmentos` del borrador quedaría pegado y todo lo que se genere
        # después saldría en baja resolución sin que nadie lo pida.
        "borrador": ["--segmentos", "120", "--sin-receta"],
        "controles": controles,
    }
    if extra:
        receta.update(extra)
    # `nombre` puede traer carpeta ("glitch/glitch15"), así que la que hay que
    # crear es la del archivo, no `output` a secas.
    ruta = DIR_OUTPUT / f"{nombre}.params.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(receta, indent=1))
    return ruta


def guardar_gcode(gcode: str, nombre: str) -> Path:
    """
    Escribe el gcode en `output/<nombre>.gcode` y devuelve la ruta.

    La escritura es atómica: primero un `.tmp` y después un rename. Un gcode de
    lámpara son varios MB, y cualquier cosa que esté mirando la carpeta -- el
    watcher de gcode-preview, un visor abierto -- se despierta con el primer
    byte. Escribiendo en el sitio leería un archivo a medio generar; con el
    rename, o ve el archivo viejo o ve el nuevo entero.

    El `.tmp` queda fuera del patrón `*.gcode`, así que el watcher lo ignora.
    """
    ruta = DIR_OUTPUT / f"{nombre}.gcode"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.parent / f"{ruta.name}.tmp"
    temporal.write_text(gcode)
    os.replace(temporal, ruta)
    return ruta
