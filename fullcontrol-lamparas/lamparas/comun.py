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


def _espiral_base(forma: Callable[[float], float], perfil: Perfil, paso_arco: float = 1.0):
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

    Devuelve (puntos, angulo_final) para que la pared arranque justo donde
    termina la base y no quede un salto.
    """
    cx, cy = perfil.centro
    z = perfil.altura_capa
    r_max = max(forma(k / 180 * math.pi) for k in range(360)) or 1.0
    avance = perfil.ancho / r_max  # fracción del contorno que se gana por vuelta
    puntos = []
    angulo = 0.0
    s = 0.0
    while s <= 1.0:
        r = s * forma(angulo)
        puntos.append(fc.Point(x=cx + r * math.cos(angulo), y=cy + r * math.sin(angulo), z=z))
        # paso angular adaptativo: segmentos de largo ~constante en toda la espiral
        angulo += paso_arco / max(r, 0.6)
        s = avance * angulo / (2 * math.pi)
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
    n_capas = max(1, int(round(altura / paso)))
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
        puntos_base, angulo_inicio = _espiral_base(lambda a: funcion_radio(a, 0.0), perfil)
        puntos.extend(puntos_base)

    # con base sólida la pared arranca una capa más arriba, encima del fondo
    z_offset = perfil.altura_capa if base_solida else 0.0

    radio_max = 0.0
    radios_medios = []

    def _mezcla(capa: int) -> float:
        """Cuánto del patrón está activo en esta vuelta: 0 en la primera, 1 al final."""
        return min(1.0, capa / capas_transicion) if capas_transicion > 0 else 1.0

    # El paso vertical tiene que crecer JUNTO con la amplitud del patrón, nunca
    # antes. Si se sube el paso completo mientras la onda todavía está atenuada,
    # la vuelta no llega a tocar la de abajo y quedan anillos sueltos en el aire.
    # El piso de altura_capa es para que la parte maciza suba como una capa normal.
    pasos_capa = [max(perfil.altura_capa, paso * _mezcla(c)) for c in range(n_capas + 1)]

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

    # la primera vuelta arranca exactamente una capa por encima de la base
    z_vuelta = z_offset + pasos_capa[0]

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
        rampa = espiral and capa >= capas_base
        mezcla = _mezcla(capa)

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
            t = (capa + fraccion) / n_capas  # `t` avanza dentro de la capa: sin saltos
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
            puntos.append(
                fc.Point(
                    x=cx + radio * math.cos(angulo_pos),
                    y=cy + radio * math.sin(angulo_pos),
                    z=z,
                )
            )

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
    DIR_OUTPUT.mkdir(parents=True, exist_ok=True)
    ruta = DIR_OUTPUT / f"{nombre}.params.json"
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
    DIR_OUTPUT.mkdir(parents=True, exist_ok=True)
    ruta = DIR_OUTPUT / f"{nombre}.gcode"
    temporal = ruta.parent / f"{ruta.name}.tmp"
    temporal.write_text(gcode)
    os.replace(temporal, ruta)
    return ruta
