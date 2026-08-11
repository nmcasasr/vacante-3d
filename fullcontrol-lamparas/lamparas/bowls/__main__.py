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

from ..comun import Perfil, descripciones_de, encabezado_receta, guardar_receta
from ..colores import (
    cambio_ams,
    degradado,
    manchas,
    cambios_desde_specs,
    parsear_filamento,
    pausa_manual,
    verificar_slots,
)
from ..estructura import resolver as resolver_estructura
from .. import modelado
from ..superficie import resolver as resolver_mascara
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
    p.add_argument("--ps", dest="par_silueta", action="append", type=_kv, default=[],
                   metavar="CLAVE=VALOR",
                   help="parametro de la silueta que no sea un radio, repetible. Para 'cilindro': "
                        "vuelo (cuanto se abre el borde de arriba, en mm) y vuelo_alto (en que "
                        "fraccion final de la altura). Para 'huevo': t_panza.")
    p.add_argument("--estructura", metavar="NOMBRE",
                   help="deformar el CUERPO con bultos grandes: 'bultos'. Es otra escala que el "
                        "patron: varios mm y uno o dos ciclos en toda la pieza, contra decimas de "
                        "mm y muchos ciclos por vuelta. Se combinan: la estructura mueve el cuerpo, "
                        "el patron raya la superficie de ese cuerpo.")
    p.add_argument("--pe", dest="par_estructura", action="append", type=_kv, default=[],
                   metavar="CLAVE=VALOR",
                   help="parametro de la estructura, repetible. Para 'bultos': modos, amplitud, "
                        "semilla, n_max, k_max. Ver lamparas/estructura.py")
    p.add_argument("--toques", metavar="ARCHIVO.json",
                   help="esculpir la pieza con toques locales: jalar, empujar, texturizar o "
                        "suavizar un punto de la superficie con un pincel de forma elegible "
                        "(circulo, cuadrado, estrella, banda, anillo...). Cada toque es un dato, "
                        "no una edicion del gcode, asi que sobrevive a mover los demas "
                        "parametros. Ver lamparas/modelado.py; para probar un archivo sin generar "
                        "nada: python -m lamparas.modelado archivo.json")
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
    p.add_argument("--cambio-ams", action="append", default=[], metavar="ALTURA:SLOT[:MATERIAL]",
                   help="cambio de slot del AMS a esa altura, repetible. El SLOT va 1..4, como lo "
                        "rotula el AMS (en el gcode sale como T0..T3). El MATERIAL sale de la tabla "
                        "de colores.py y define las temperaturas y el caudal del cambio; si no se "
                        "pone, PLA. Ej: --cambio-ams 20:2 --cambio-ams 40:3:PETG")
    p.add_argument("--slot-inicial", default="1", metavar="SLOT[:MATERIAL]",
                   help="con qué filamento arranca la pieza (por defecto 1, o sea A1 con PLA). "
                        "Hace falta porque la DESCARGA de cada cambio se hace a la temperatura y "
                        "al caudal del filamento que sale, no del que entra.")
    p.add_argument("--purga", type=float, default=0.0, metavar="MM",
                   help="mm de filamento a purgar en cada cambio de AMS (por defecto 0). Con 0 el "
                        "color viejo sale mezclado con el nuevo durante las primeras vueltas, que es "
                        "el efecto que estos disenos buscan. El .3mf de referencia tambien emite L0.")
    p.add_argument("--degradado", action="append", default=[], metavar="Z0:Z1:SLOT[:MATERIAL]",
                   help="degradado entre el filamento actual y SLOT, entre esas dos alturas. "
                        "Repetible, se encadenan. Ej: --degradado 0:45:2 --degradado 45:90:3. "
                        "Es el unico caso donde el sangrado ayuda: la mezcla ES el degradado. "
                        "Ojo: un rollo de filamento degradado hace esto mejor y gratis.")
    p.add_argument("--degradado-pasos", type=int, default=12, metavar="N",
                   help="en cuantas franjas se parte cada degradado (por defecto 12). "
                        "Mas pasos = mas suave y mas caro: son 2N-1 cambios de ~56 s.")
    p.add_argument("--manchas", metavar="Z0:Z1:SLOT[:MATERIAL]",
                   help="cambia de color a intervalos ALEATORIOS entre esas alturas, alternando "
                        "con --slot-inicial. Usa el sangrado como largo MINIMO, asi ningun cambio "
                        "sale a perdida: 1 cambio por tramo en vez de 2 por capa. Ver --manchas-vueltas.")
    p.add_argument("--manchas-vueltas", default="2:9", metavar="MIN:MAX",
                   help="largo de cada tramo en vueltas (por defecto 2:9). El MIN tiene que cubrir "
                        "la transicion del par de colores: ~1.4 para dos PLA parecidos, ~1.9 para "
                        "PLA->PETG, ~7 para PETG->PLA. La diferencia MAX-MIN es de donde sale la variedad.")
    p.add_argument("--pintar", metavar="MASCARA",
                   help="pintar una figura CON COLOR: 'caritas', 'feliz', 'triste'. Cambia de "
                        "filamento al entrar y al salir del dibujo, DENTRO de cada vuelta. "
                        "Necesita --pintar-con. Leé el aviso que imprime: son ~56 s por cambio y "
                        "el color tarda ~2 vueltas en salir limpio, asi que un dibujo con detalle "
                        "sale carisimo y borroneado. La alternativa sin costo es --p mascara=..., "
                        "que dibuja la misma figura con textura.")
    p.add_argument("--pp", dest="par_pintura", action="append", type=_kv, default=[],
                   metavar="CLAVE=VALOR",
                   help="parametro de la mascara que se pinta, repetible. Para 'parches': "
                        "cantidad, alto_t, ancho_grados, semilla, borde. El costo en cambios es "
                        "2 x cantidad x alto_t x n_capas, o sea que 'cantidad' y 'alto_t' son las "
                        "dos perillas que lo mueven; 'ancho_grados' no cuesta nada.")
    p.add_argument("--pintar-con", metavar="SLOT[:MATERIAL]",
                   help="el filamento del dibujo, p.ej. 3:PETG. El fondo es --slot-inicial.")
    p.add_argument("--plantilla-3mf", metavar="RUTA",
                   help="plantilla .gcode.3mf con la que se va a empaquetar, solo para avisar si no "
                        "declara todos los slots del AMS que usa la pieza.")
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
    p.add_argument("--sin-receta", action="store_true",
                   help="no escribir el <nombre>.params.json. Lo usa el preview en las corridas "
                        "de BORRADOR: esas llevan un --segmentos bajo para ir rapido, y si se "
                        "guardaran en la receta la baja resolucion quedaria pegada para siempre.")
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
    for k, v in args.par_silueta:
        if k not in acepta:
            p.error(f"la silueta '{args.silueta}' no acepta '{k}'. Acepta: {', '.join(acepta)}")
        parametros_silueta[k] = v
    ignorados = [k for k, v in pedidos.items() if v is not None and k not in acepta]
    if ignorados:
        print(f"AVISO: la silueta '{args.silueta}' no usa {', '.join(ignorados)}; se ignora.")

    cambios = {h: pausa_manual(f"a {h:.1f} mm") for h in args.cambio}
    if args.cambio_ams:
        # Un slot inválido es un error de uso, no un bug: sale por argparse en
        # vez de por un traceback.
        try:
            inicial = parsear_filamento(args.slot_inicial)
            cambios.update(cambios_desde_specs(args.cambio_ams, inicial, args.purga, perfil))
            slots = [inicial.slot] + [parsear_filamento(s.split(":", 1)[1]).slot
                                      for s in args.cambio_ams]
        except ValueError as e:
            p.error(str(e))
        if args.plantilla_3mf:
            verificar_slots(slots, args.plantilla_3mf)
    if args.manchas:
        try:
            z0, z1, resto = args.manchas.split(":", 2)
            mn, mx = (float(v) for v in args.manchas_vueltas.split(":"))
            radio = args.radio_max or args.radio_base or args.radio_boca or 45.0
            cambios.update(manchas(
                [parsear_filamento(args.slot_inicial), parsear_filamento(resto)],
                float(z0), float(z1), radio, mn, mx, perfil=perfil, purga=args.purga))
        except ValueError as e:
            p.error(str(e))

    if args.degradado:
        try:
            actual = parsear_filamento(args.slot_inicial)
            for spec in args.degradado:
                z0, z1, resto = spec.split(":", 2)
                destino = parsear_filamento(resto)
                cambios.update(degradado(actual, destino, float(z0), float(z1),
                                         args.degradado_pasos, args.purga, perfil))
                actual = destino
        except ValueError as e:
            p.error(str(e))

    for spec in args.velocidad_en:
        altura, mm_min = spec.split(":")
        cambios[float(altura)] = fc.Printer(print_speed=int(mm_min))
    for spec in args.ventilador_en:
        altura, pct = spec.split(":")
        cambios[float(altura)] = fc.Fan(speed_percent=int(pct))

    # Los toques se leen acá arriba porque algunos pintan, y la pintura se arma
    # más abajo: si se leyeran después, un archivo con toques de tipo 'pintar'
    # llegaría tarde a la única parte que sabe cambiar de filamento.
    toques = []
    if args.toques:
        try:
            toques = modelado.leer(args.toques)
        except (ValueError, TypeError, OSError) as e:
            p.error(f"--toques: {e}")
    mascara_toques = modelado.mascara(toques)

    # --- pintura por color: entrar y salir del dibujo dentro de la vuelta ---
    pintura = None
    if args.pintar or args.pintar_con or mascara_toques is not None:
        if not args.pintar_con:
            p.error("falta --pintar-con: hay un dibujo pero no con qué pintarlo")
        if args.pintar and mascara_toques is not None:
            p.error("--pintar y los toques de tipo 'pintar' definen los dos el mismo "
                    "dibujo; elegí uno")
        try:
            fondo = parsear_filamento(args.slot_inicial)
            dibujo = parsear_filamento(args.pintar_con)
            mascara = (resolver_mascara(args.pintar, **dict(args.par_pintura))
                       if args.pintar else mascara_toques)
        except ValueError as e:
            p.error(str(e))
        pintura = {
            "mascara": mascara,
            # entrar al dibujo = cargar el filamento del dibujo; salir = volver al fondo
            "entrar": cambio_ams(dibujo, fondo, perfil=perfil, nota="entra al dibujo"),
            "salir": cambio_ams(fondo, dibujo, perfil=perfil, nota="sale del dibujo"),
        }
        print(f"Pintura '{args.pintar or 'toques'}': fondo A{fondo.slot} ({fondo.tipo}), "
              f"dibujo A{dibujo.slot} ({dibujo.tipo}).")

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

    deformacion = None
    if args.estructura:
        try:
            deformacion = resolver_estructura(args.estructura, **dict(args.par_estructura))
        except (ValueError, TypeError) as e:
            p.error(str(e))

    # --- toques: esculpido local, encima de todo lo anterior ---
    if toques:
        # `suavizar` apaga la estructura, asi que necesita verla; por eso se
        # arma DESPUES de resolverla y no antes.
        esculpido = modelado.deformacion(toques, estructura=deformacion)
        if deformacion is None:
            deformacion = esculpido
        else:
            base = deformacion
            deformacion = lambda a, t: base(a, t) + esculpido(a, t)  # noqa: E731

        # El chequeo corre siempre. Lo unico que rompe una pieza en modo vaso es
        # que el radio se corra mas de un cordon entre dos vueltas, y un toque
        # fuerte y angosto lo consigue sin que se note al mirarlo.
        for aviso in modelado.revisar(
            toques,
            altura=args.altura,
            altura_capa=perfil.altura_capa,
            ancho_linea=args.ancho_linea or args.boquilla,
            segmentos=args.segmentos or 360,
        ):
            print(aviso)
        print(f"Toques: {len(toques)} desde {args.toques}.")

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
        pintura=pintura,
        deformacion=deformacion,
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
        import sys as _sys
        gcode = encabezado_receta(_sys.argv, "lamparas.bowls") + a_gcode(pasos, perfil)
        ruta = guardar_gcode(gcode, nombre)
        if not args.sin_receta:
            # Cada grupo de parámetros se documenta en la función que los
            # recibe, así que las descripciones se sacan de ahí.
            from ..estructura import ESTRUCTURAS
            from ..superficie import MASCARAS
            desc = {
                "--p": descripciones_de(DISENOS[args.diseno].construir),
                "--ps": descripciones_de(_SILUETAS[args.silueta]),
                "--pe": descripciones_de(ESTRUCTURAS[args.estructura]) if args.estructura else {},
                "--pp": descripciones_de(MASCARAS[args.pintar]) if args.pintar else {},
                # Los flags sueltos ya tienen su texto en argparse.
                "": {("--" + a.dest.replace("_", "-")): (a.help or "").split(".")[0]
                     for a in p._actions if a.dest != "help"},
            }
            from ..comun import ULTIMO_MAPEO
            guardar_receta(nombre, _sys.argv, "lamparas.bowls", desc,
                           extra={"mapeo": dict(ULTIMO_MAPEO),
                                  "toques": args.toques or None})
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas)")


if __name__ == "__main__":
    _cli()
