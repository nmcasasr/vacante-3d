"""
Lámpara en modo vaso (spiral) con pared ondulada y twist progresivo.

Idea: en vez de un cilindro liso, el radio de cada capa varía con una onda
seno (`n_ondas` lóbulos). Además la fase de esa onda rota progresivamente con
la altura (`vueltas_twist`), dando un efecto de torsión tipo "candy twist".

Uso desde la línea de comandos:

    python -m lamparas.twist --radio-base 40 --altura 150 --n-ondas 6

Uso como librería:

    from lamparas.twist import generar_lampara_twist
    gcode = generar_lampara_twist(radio_base=50, n_ondas=8, amplitud=6)
"""

import argparse
import math
from typing import Optional

from .comun import Perfil, a_gcode, generar_lampara, guardar_gcode
from .impresoras import cargar_gcode
from .preview import guardar_html, previsualizar


def pasos_lampara_twist(
    radio_base: float = 40.0,
    altura: float = 150.0,
    n_ondas: int = 6,
    amplitud: float = 4.0,
    vueltas_twist: float = 1.5,
    segmentos_por_capa: int = 120,
    perfil: Optional[Perfil] = None,
    espiral: bool = True,
    base_solida: bool = False,
    capas_transicion: int = 0,
) -> list:
    """Devuelve los pasos de FullControl de la lámpara (útil para previsualizar)."""

    def radio(angulo: float, t: float) -> float:
        # La fase rota con la altura -> torsión
        fase = t * vueltas_twist * 2 * math.pi
        return radio_base + amplitud * math.sin(n_ondas * angulo + fase)

    return generar_lampara(
        radio,
        altura=altura,
        perfil=perfil,
        segmentos_por_capa=segmentos_por_capa,
        espiral=espiral,
        base_solida=base_solida,
        capas_transicion=capas_transicion,
    )


def generar_lampara_twist(
    radio_base: float = 40.0,
    altura: float = 150.0,
    n_ondas: int = 6,
    amplitud: float = 4.0,
    vueltas_twist: float = 1.5,
    segmentos_por_capa: int = 120,
    perfil: Optional[Perfil] = None,
    espiral: bool = True,
    nombre: str = "lampara_twist",
    guardar: bool = True,
) -> str:
    """
    Genera el gcode de la lámpara con pared ondulada y twist.

    Args:
        radio_base: radio medio de la lámpara, en mm.
        altura: altura total, en mm.
        n_ondas: cantidad de lóbulos alrededor de la circunferencia.
        amplitud: cuánto sobresale/hunde cada lóbulo respecto al radio base, en mm.
        vueltas_twist: vueltas completas que gira la onda a lo largo de la altura.
        segmentos_por_capa: resolución angular de cada vuelta.
        perfil: parámetros de impresión (`Perfil()` por defecto).
        espiral: modo vaso con Z continua.
        nombre: nombre del archivo (sin extensión) dentro de `output/`.
        guardar: si es False, solo devuelve el gcode sin escribir el archivo.

    Returns:
        El gcode como cadena de texto.
    """
    pasos = pasos_lampara_twist(
        radio_base=radio_base,
        altura=altura,
        n_ondas=n_ondas,
        amplitud=amplitud,
        vueltas_twist=vueltas_twist,
        segmentos_por_capa=segmentos_por_capa,
        perfil=perfil,
        espiral=espiral,
    )
    gcode = a_gcode(pasos, perfil)
    if guardar:
        ruta = guardar_gcode(gcode, nombre)
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas de gcode)")
    return gcode


def _cli() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--radio-base", type=float, default=40.0, help="radio medio en mm")
    p.add_argument("--altura", type=float, default=150.0, help="altura total en mm")
    p.add_argument("--n-ondas", type=int, default=6, help="cantidad de lóbulos")
    p.add_argument("--amplitud", type=float, default=4.0, help="profundidad de la onda en mm")
    p.add_argument("--vueltas-twist", type=float, default=1.5, help="vueltas de torsión en toda la altura")
    p.add_argument("--segmentos", type=int, default=120, help="resolución angular por vuelta")
    p.add_argument("--velocidad", type=int, metavar="MM_MIN",
                   help="velocidad de impresión en mm/min (por defecto 1200 = 20 mm/s)")
    p.add_argument("--ventilador", type=int, metavar="PCT",
                   help="ventilador de capa en %%. PLA en modo vaso quiere 100; PETG mucho menos "
                        "(su perfil lo limita a ~60) porque pierde adhesión entre capas y transparencia.")
    p.add_argument("--temperatura", type=int, metavar="GRADOS",
                   help="temperatura de boquilla DURANTE la pieza. Se inyecta en el cuerpo, así que "
                        "sobrevive al empaquetado del .3mf y pisa la del template.")
    p.add_argument("--boquilla", type=float, default=0.8, help="diámetro de boquilla en mm")
    p.add_argument("--altura-capa", type=float, default=0.4, help="altura de capa en mm")
    p.add_argument("--ancho-linea", type=float, help="ancho del cordón en mm (por defecto, el de la boquilla)")
    p.add_argument("--capas-transicion", type=int, default=0, metavar="N",
                   help="vueltas en las que la onda nace desde un circulo liso (por defecto 0). "
                        "Con base maciza conviene 0: la base sigue el contorno ondulado, asi que si "
                        "la pared arrancara como circulo no le calzaria.")
    p.add_argument("--con-base", action="store_true",
                   help="rellenar el fondo con una espiral maciza, como los bowls. Por defecto la "
                        "lampara sale abierta abajo (es una pantalla). La base se rellena hasta el "
                        "radio MAXIMO de la onda, no el medio, o los lobulos quedarian al aire.")
    p.add_argument("--sin-espiral", action="store_true", help="capas planas en vez de modo vaso")
    p.add_argument("--nombre", default="lampara_twist", help="nombre del .gcode en output/")
    p.add_argument("--sin-nivelacion", action="store_true", help="no incluir G29 en el start gcode")
    p.add_argument("--start-gcode", help="archivo con el start gcode a usar (p.ej. el de Bambu Studio)")
    p.add_argument("--end-gcode", help="archivo con el end gcode a usar")
    p.add_argument("--preview", action="store_true", help="además del gcode, generar un HTML 3D en output/")
    p.add_argument("--solo-preview", action="store_true", help="generar solo el HTML, sin exportar gcode")
    p.add_argument("--plot", action="store_true", help="abrir el visor interactivo de FullControl")
    args = p.parse_args()

    ajustes = dict(
        diametro_boquilla=args.boquilla,
        altura_capa=args.altura_capa,
        ancho_linea=args.ancho_linea,
        nivelar=not args.sin_nivelacion,
        start_gcode=cargar_gcode(args.start_gcode) if args.start_gcode else None,
        end_gcode=cargar_gcode(args.end_gcode) if args.end_gcode else None,
    )
    if args.velocidad:
        ajustes["velocidad_impresion"] = args.velocidad
    if args.ventilador is not None:
        ajustes["ventilador"] = args.ventilador
    perfil = Perfil(**ajustes)
    comunes = dict(
        base_solida=args.con_base,
        capas_transicion=args.capas_transicion,
        radio_base=args.radio_base,
        altura=args.altura,
        n_ondas=args.n_ondas,
        amplitud=args.amplitud,
        vueltas_twist=args.vueltas_twist,
        segmentos_por_capa=args.segmentos,
        perfil=perfil,
        espiral=not args.sin_espiral,
    )

    pasos = pasos_lampara_twist(**comunes)

    if args.plot:
        previsualizar(pasos)
        return

    if args.preview or args.solo_preview:
        print(f"Preview: {guardar_html(pasos, nombre=args.nombre, perfil=perfil)}")

    if not args.solo_preview:
        # Después del marcador FIN DEL START GCODE, así el empaquetador del .3mf
        # lo deja pasar verbatim en vez de borrarlo con el calentado.
        if args.temperatura:
            import fullcontrol as fc
            pasos.insert(0, fc.ManualGcode(text=f"M104 S{args.temperatura} ; temperatura de impresion"))
        gcode = a_gcode(pasos, perfil)
        ruta = guardar_gcode(gcode, args.nombre)
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas de gcode)")


if __name__ == "__main__":
    _cli()
