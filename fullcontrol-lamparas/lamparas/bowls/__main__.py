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
import fullcontrol as fc
import inspect

from ..comun import Perfil
from ..colores import cambio_ams, pausa_manual
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
    p.add_argument("--capas-transicion", type=int, default=6, metavar="N",
                   help="vueltas en las que el patrón nace desde un círculo liso (por defecto 6). "
                        "Subirlo hace que el calado entre más despacio: en las primeras vueltas los "
                        "picos quedan al aire sin nada debajo, y con pocas capas de transición "
                        "arrancan demasiado alto para agarrarse de la base.")
    p.add_argument("--capas-base", type=int, default=1, metavar="N",
                   help="primeras vueltas sin rampa de Z (anillos cerrados apilados, por defecto 1). "
                        "Le da al calado algo macizo de donde arrancar en vez de un solo cordón.")
    p.add_argument("--boquilla", type=float, default=0.8)
    p.add_argument("--altura-capa", type=float, default=0.4)
    p.add_argument("--ancho-linea", type=float, help="ancho del cordón en mm (por defecto, el de la boquilla)")
    p.add_argument("--velocidad", type=int, metavar="MM_MIN",
                   help="velocidad de impresión en mm/min (por defecto 1200 = 20 mm/s). "
                        "Los patrones que puentean al aire (celosia, malla) necesitan menos: "
                        "el cordón tiene que cuajar antes de que la vuelta siguiente pase por encima.")
    p.add_argument("--ventilador", type=int, metavar="PCT",
                   help="ventilador de capa en %% (por defecto 100). PLA en modo vaso quiere 100; "
                        "PETG no tolera tanto (el perfil de Orca lo limita a ~60) y con mas se despega "
                        "entre capas. Ojo: el template del .3mf NO lo define, sale de aca.")
    # --- modulacion dentro de la vuelta ---
    p.add_argument("--velocidad-pico", type=int, metavar="MM_MIN",
                   help="velocidad en la CRESTA de la onda (maximo voladizo, el cordon va al aire). "
                        "--velocidad pasa a ser la del cruce. Ej: --velocidad 600 --velocidad-pico 120.")
    p.add_argument("--ventilador-pico", type=int, metavar="PCT",
                   help="ventilador en la cresta. --ventilador pasa a ser el del cruce, donde "
                        "conviene MENOS aire para que las vueltas suelden.")
    p.add_argument("--espera", type=int, metavar="MS",
                   help="parar la boquilla N ms en cada CRUCE para que la soldadura cuaje antes "
                        "de salir al aire otra vez (retrae, G4, ceba). Tecnica del gcode de "
                        "Squeezy Fidget Toy, que usa 1500 ms. Cuesta tiempo: 430 cruces x 1.5 s = 11 min.")
    p.add_argument("--espera-cada", type=int, default=1, metavar="N",
                   help="esperar solo cada N cruces, para no pagar el tiempo en todos.")
    p.add_argument("--retraccion", type=float, default=1.5, metavar="MM",
                   help="retraccion durante la espera (por defecto 1.5). Sin esto la boquilla "
                        "queda presurizada y deja un grumo.")
    p.add_argument("--ancho-nodo", type=float, metavar="MM",
                   help="ancho de cordon en el CRUCE con la vuelta de abajo: mas material justo "
                        "donde tiene que soldar. --ancho-linea queda como el del resto.")
    p.add_argument("--temperatura", type=int, metavar="GRADOS",
                   help="temperatura de boquilla DURANTE la pieza. Se inyecta en el cuerpo, asi que "
                        "sobrevive al empaquetado del .3mf y pisa la del template (que solo sirve para "
                        "el calentado inicial). PETG en patrones calados quiere ~240: mas caliente no "
                        "solidifica y se descuelga en los vanos.")
    p.add_argument("--cambio", type=float, action="append", default=[], metavar="ALTURA",
                   help="pausa para cambiar el filamento a mano a esa altura en mm (repetible)")
    p.add_argument("--cambio-ams", action="append", default=[], metavar="ALTURA:SLOT",
                   help="cambio de slot del AMS sin purga (SIN VERIFICAR, ver colores.py)")
    p.add_argument("--velocidad-en", action="append", default=[], metavar="ALTURA:MM_MIN",
                   help="cambiar la velocidad a esa altura, repetible. Sirve para hacer una torre "
                        "de calibración: bandas de altura a velocidades crecientes, para ver a "
                        "partir de qué velocidad el patrón deja de cuajar.")
    p.add_argument("--ventilador-en", action="append", default=[], metavar="ALTURA:PCT",
                   help="cambiar el ventilador a esa altura, repetible. El gcode de Squeezy Fidget Toy "
                        "lo usa asi: 0%% en toda la seccion maciza y 100%% en cuanto empieza el calado. "
                        "Las zonas macizas sin aire quedan mas fuertes y transparentes; los puentes con "
                        "aire no se descuelgan.")
    p.add_argument("--sin-nivelacion", action="store_true", help="no incluir G29 en el start gcode")
    p.add_argument("--start-gcode", help="archivo con el start gcode a usar")
    p.add_argument("--end-gcode", help="archivo con el end gcode a usar")
    p.add_argument("--nombre", help="nombre del archivo en output/ (por defecto bowl_<diseño>)")
    p.add_argument("--preview", action="store_true", help="además del gcode, generar el HTML 3D")
    p.add_argument("--solo-preview", action="store_true", help="solo el HTML, sin gcode")
    p.add_argument("--plot", action="store_true", help="visor interactivo de FullControl")
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

    cambios = {h: pausa_manual(f"a {h:.1f} mm") for h in args.cambio}
    for spec in args.cambio_ams:
        altura, slot = spec.split(":")
        cambios[float(altura)] = cambio_ams(int(slot), f"a {float(altura):.1f} mm")
    for spec in args.velocidad_en:
        altura, mm_min = spec.split(":")
        cambios[float(altura)] = fc.Printer(print_speed=int(mm_min))
    for spec in args.ventilador_en:
        altura, pct = spec.split(":")
        cambios[float(altura)] = fc.Fan(speed_percent=int(pct))

    # nodo = valle de la onda (cruce con la vuelta de abajo), pico = cresta.
    v_nodo = args.velocidad or 1200
    f_nodo = args.ventilador if args.ventilador is not None else 100
    w_base = args.ancho_linea or args.boquilla
    modulacion = {}
    if args.velocidad_pico:
        modulacion["velocidad"] = (v_nodo, args.velocidad_pico)
    if args.ventilador_pico is not None:
        modulacion["ventilador"] = (f_nodo, args.ventilador_pico)
    if args.ancho_nodo:
        modulacion["ancho"] = (args.ancho_nodo, w_base)
    if args.espera:
        modulacion["espera"] = (args.espera, args.retraccion, args.espera_cada)

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
        capas_transicion=args.capas_transicion,
        capas_base=args.capas_base,
        cambios=cambios or None,
        modulacion=modulacion or None,
    )

    # Va al principio de los pasos, o sea DESPUES del marcador FIN DEL START
    # GCODE. Ahi el empaquetador lo deja pasar verbatim; arriba del marcador lo
    # borraria junto con el calentado de FullControl.
    if args.temperatura:
        pasos.insert(0, fc.ManualGcode(text=f"M104 S{args.temperatura} ; temperatura de impresion"))

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
