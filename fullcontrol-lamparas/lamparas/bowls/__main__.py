"""
CLI de los bowls.

    python -m lamparas.bowls malla --preview
    python -m lamparas.bowls cesta --altura 70 --radio-boca 85 --p n_tiras=20
    python -m lamparas.bowls celosia --silueta platillo --radio-max 90 --solo-preview
    python -m lamparas.bowls tramado --p torsion=14 --p amplitud=2.5 --nombre bowl_diagonal

Los parámetros propios de cada patrón van con `--p clave=valor` (se puede
repetir). Están documentados en el `construir()` de cada módulo:
`lamparas/bowls/cesta.py`, `malla.py`, `celosia.py`, `tramado.py`.
"""

import argparse
import inspect

from ..comun import Perfil
from ..impresoras import cargar_gcode
from ..preview import guardar_html, previsualizar
from . import DISENOS, SILUETAS, a_gcode, guardar_gcode, pasos_bowl
from .siluetas import SILUETAS as _SILUETAS


def _kv(texto: str):
    """Convierte 'clave=valor' en (clave, valor) con el tipo adecuado."""
    if "=" not in texto:
        raise argparse.ArgumentTypeError(f"se esperaba clave=valor, llegó {texto!r}")
    clave, valor = texto.split("=", 1)
    for conversor in (int, float):
        try:
            return clave.strip(), conversor(valor)
        except ValueError:
            continue
    return clave.strip(), valor


def _cli() -> None:
    p = argparse.ArgumentParser(prog="lamparas.bowls", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("diseno", choices=sorted(DISENOS), help="patrón del bowl")
    p.add_argument("--silueta", choices=sorted(SILUETAS), default="bol")
    p.add_argument("--altura", type=float, default=60.0, help="altura de la pared en mm")
    p.add_argument("--radio-base", type=float, help="radio del fondo en mm")
    p.add_argument("--radio-boca", type=float, help="radio de la boca en mm")
    p.add_argument("--radio-max", type=float, help="radio de la panza (solo silueta platillo)")
    p.add_argument("--p", dest="parametros", action="append", type=_kv, default=[],
                   metavar="CLAVE=VALOR", help="parámetro del patrón, repetible")
    p.add_argument("--segmentos", type=int, help="resolución angular (por defecto, la del patrón)")
    p.add_argument("--sin-base", action="store_true", help="no rellenar el fondo")
    p.add_argument("--boquilla", type=float, default=0.8)
    p.add_argument("--altura-capa", type=float, default=0.4)
    p.add_argument("--sin-nivelacion", action="store_true", help="no incluir G29 en el start gcode")
    p.add_argument("--start-gcode", help="archivo con el start gcode a usar")
    p.add_argument("--end-gcode", help="archivo con el end gcode a usar")
    p.add_argument("--nombre", help="nombre del archivo en output/ (por defecto bowl_<diseño>)")
    p.add_argument("--preview", action="store_true", help="además del gcode, generar el HTML 3D")
    p.add_argument("--solo-preview", action="store_true", help="solo el HTML, sin gcode")
    p.add_argument("--plot", action="store_true", help="visor interactivo de FullControl")
    args = p.parse_args()

    perfil = Perfil(
        diametro_boquilla=args.boquilla,
        altura_capa=args.altura_capa,
        nivelar=not args.sin_nivelacion,
        start_gcode=cargar_gcode(args.start_gcode) if args.start_gcode else None,
        end_gcode=cargar_gcode(args.end_gcode) if args.end_gcode else None,
    )

    # solo se le pasan a la silueta los radios que esa silueta acepta
    pedidos = {
        "radio_base": args.radio_base,
        "radio_boca": args.radio_boca,
        "radio_max": args.radio_max,
    }
    acepta = inspect.signature(_SILUETAS[args.silueta]).parameters
    parametros_silueta = {k: v for k, v in pedidos.items() if v is not None and k in acepta}
    ignorados = [k for k, v in pedidos.items() if v is not None and k not in acepta]
    if ignorados:
        print(f"AVISO: la silueta '{args.silueta}' no usa {', '.join(ignorados)}; se ignora.")

    nombre = args.nombre or f"bowl_{args.diseno}"
    pasos = pasos_bowl(
        diseno=args.diseno,
        silueta=args.silueta,
        altura=args.altura,
        perfil=perfil,
        parametros=dict(args.parametros),
        parametros_silueta=parametros_silueta,
        segmentos_por_capa=args.segmentos,
        base_solida=not args.sin_base,
    )

    if args.plot:
        previsualizar(pasos)
        return

    if args.preview or args.solo_preview:
        print(f"Preview: {guardar_html(pasos, nombre=nombre, perfil=perfil)}")

    if not args.solo_preview:
        gcode = a_gcode(pasos, perfil)
        ruta = guardar_gcode(gcode, nombre)
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas)")


if __name__ == "__main__":
    _cli()
