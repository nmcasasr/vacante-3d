"""
Infraestructura compartida por todos los diseños de lámparas.

La idea es que cada script de `lamparas/` solo tenga que describir *la forma*
(una función que devuelve el radio en función del ángulo y de la altura) y que
todo lo demás -- estado inicial de la impresora, generación de la espiral,
exportación del .gcode -- viva acá y no se duplique.
"""

import math
from dataclasses import dataclass, field
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

    diametro_boquilla: float = 0.8      # mm - ancho de extrusión
    altura_capa: float = 0.4            # mm - capa gruesa, líneas marcadas
    velocidad_impresion: int = 1200     # mm/min
    velocidad_viaje: int = 6000         # mm/min
    temp_boquilla: int = 200            # °C (PLA)
    temp_cama: int = 55                 # °C
    ventilador: int = 100               # % (modo vaso quiere refrigeración alta)

    # La A1 tiene el origen en la esquina frontal-izquierda de la cama, así que
    # una lámpara centrada en (0, 0) quedaría fuera. Todo se traslada a `centro`.
    centro: Tuple[float, float] = (128.0, 128.0)
    tamano_cama: Tuple[float, float] = (256.0, 256.0)

    # Perfil de impresora de FullControl. 'generic' NO emite homing ni start
    # gcode de Bambu: ver el aviso del README.
    nombre_impresora: str = "generic"

    @property
    def area_extrusion(self) -> float:
        """mm² de sección de cada línea extruida (modelo rectangular)."""
        return self.diametro_boquilla * self.altura_capa


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
            width=perfil.diametro_boquilla,
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
    margen = perfil.diametro_boquilla / 2
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


def generar_lampara(
    funcion_radio: FuncionRadio,
    altura: float,
    perfil: Optional[Perfil] = None,
    segmentos_por_capa: int = 120,
    espiral: bool = True,
    capas_base: int = 1,
) -> list:
    """
    Construye la lista de pasos de FullControl para un sólido de revolución
    cuyo radio lo define `funcion_radio(angulo, t)`.

    Args:
        funcion_radio: radio en mm para un ángulo (rad) y una altura relativa t (0..1).
        altura: altura total de la lámpara en mm.
        perfil: parámetros de impresión. Si es None se usa `Perfil()`.
        segmentos_por_capa: resolución angular (más = más suave, más pesado el gcode).
        espiral: True para modo vaso real -- la Z sube de forma continua a lo
            largo de cada vuelta, sin escalón de cambio de capa.
        capas_base: cuántas primeras vueltas se imprimen planas (sin rampa de Z)
            antes de empezar a espiralar. Ayuda a la adherencia.

    Returns:
        La lista de pasos lista para `fc.transform(...)`.
    """
    perfil = perfil or Perfil()
    cx, cy = perfil.centro
    n_capas = max(1, int(round(altura / perfil.altura_capa)))

    pasos = pasos_iniciales(perfil)
    radio_max = 0.0
    puntos: list = []

    for capa in range(n_capas):
        # La primera capa se imprime a z = altura_capa, no a z = 0: a z = 0 la
        # boquilla estaría apoyada contra la cama.
        z_base = (capa + 1) * perfil.altura_capa
        rampa = espiral and capa >= capas_base

        for seg in range(segmentos_por_capa + 1):  # +1 para cerrar la vuelta
            fraccion = seg / segmentos_por_capa
            angulo = fraccion * 2 * math.pi
            # `t` avanza dentro de la capa para que la forma no dé saltos
            t = (capa + fraccion) / n_capas
            radio = funcion_radio(angulo, t)
            radio_max = max(radio_max, radio)

            z = z_base + fraccion * perfil.altura_capa if rampa else z_base
            puntos.append(
                fc.Point(
                    x=cx + radio * math.cos(angulo),
                    y=cy + radio * math.sin(angulo),
                    z=z,
                )
            )

    # Viaje sin extruir hasta el primer punto y recién ahí se abre el extrusor.
    # Con primer='no_primer' esto es necesario: FullControl necesita un punto
    # previo para poder calcular la longitud de la primera línea extruida.
    pasos.append(fc.Extruder(on=False))
    pasos.append(puntos[0])
    pasos.append(fc.Extruder(on=True))
    pasos.extend(puntos[1:])

    _verificar_cama(radio_max, perfil)
    return pasos


def a_gcode(pasos: list, perfil: Optional[Perfil] = None) -> str:
    """Convierte los pasos en una cadena de gcode (sin escribir ningún archivo)."""
    perfil = perfil or Perfil()
    return fc.transform(
        pasos,
        "gcode",
        fc.GcodeControls(
            printer_name=perfil.nombre_impresora,
            initialization_data={
                # El A1 ya tiene su propia rutina de purga en el start gcode que
                # vas a pegar a mano, así que acá no generamos ninguna.
                "primer": "no_primer",
                "print_speed": perfil.velocidad_impresion,
                "travel_speed": perfil.velocidad_viaje,
                "extrusion_width": perfil.diametro_boquilla,
                "extrusion_height": perfil.altura_capa,
                "nozzle_temp": perfil.temp_boquilla,
                "bed_temp": perfil.temp_cama,
                "fan_percent": perfil.ventilador,
            },
        ),
        show_tips=False,
    )


def guardar_gcode(gcode: str, nombre: str) -> Path:
    """Escribe el gcode en `output/<nombre>.gcode` y devuelve la ruta."""
    DIR_OUTPUT.mkdir(parents=True, exist_ok=True)
    ruta = DIR_OUTPUT / f"{nombre}.gcode"
    ruta.write_text(gcode)
    return ruta


def previsualizar(pasos: list) -> None:
    """Abre el plot interactivo de FullControl (requiere plotly)."""
    fc.transform(
        pasos,
        "plot",
        fc.PlotControls(style="line", color_type="z_gradient"),
        show_tips=False,
    )
