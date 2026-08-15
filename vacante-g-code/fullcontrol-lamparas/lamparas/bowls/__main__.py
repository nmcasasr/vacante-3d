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
import sys as _sys
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
    p.add_argument("--perfil", metavar="ARCHIVO.dxf",
                   help="tomar la silueta de un DXF de Fusion en vez del catalogo. Elige sola la "
                        "curva mas larga que mas altura recorre; para ver que hay y forzar otra: "
                        "python -m lamparas.perfil ARCHIVO.dxf")
    p.add_argument("--perfil-capa", metavar="CAPA", help="forzar una capa del DXF")
    p.add_argument("--perfil-idx", type=int, metavar="N", help="forzar una curva del DXF por su numero")
    p.add_argument("--perfil-desde", type=float, metavar="Z",
                   help="recortar el perfil por abajo, en las coordenadas del modelo. Para imprimir "
                        "solo la cabeza de una lampara: --perfil-desde 124.4")
    p.add_argument("--perfil-hasta", type=float, metavar="Z", help="recortar el perfil por arriba")
    p.add_argument("--perfil-escala", type=float, default=1.0, metavar="K",
                   help="achicar o agrandar el perfil, radio y altura por igual. Para sacar una "
                        "prueba chica de una pieza que tarda horas: --perfil-escala 0.35. "
                        "Uniforme a proposito: el voladizo es un ANGULO y los angulos no cambian "
                        "con la escala, asi que la version chica pone a prueba la misma geometria. "
                        "Lo que NO escala es el cordon: con la misma boquilla, la pared de la "
                        "chica pesa mas en proporcion.")
    p.add_argument("--perfil-invertir", action="store_true",
                   help="dar vuelta el perfil de arriba abajo. Un modelo suele venir en la "
                        "orientacion de la FIGURA, no en la de impresion: la caperuza tiene el "
                        "encastre arriba en el ensamblaje y tiene que ir contra la cama para poder "
                        "imprimirse. Sin esto sale al reves y no encastra ni se sostiene.")
    p.add_argument("--perfil-limitar", action="store_true",
                   help="recortar la pendiente del perfil para que ninguna vuelta se corra mas que "
                        "un cordon. Una cupula siempre tiene tangente horizontal en el apice y ahi "
                        "las lineas quedan sueltas en el aire; esto la reemplaza por el cono mas "
                        "cerrado que si pega, y avisa cuanto queda abierta la punta.")
    p.add_argument("--piso", type=float, metavar="DIAMETRO",
                   help="diametro que tiene que QUEDAR libre en el piso, en mm. No es el del "
                        "recorrido: el cordon va centrado en la trayectoria y se come medio cordon "
                        "por lado, asi que se compensa. Sin esto el agujero sale chico y no encaja.")
    p.add_argument("--piso-refuerzo", type=int, default=3, metavar="N",
                   help="vueltas de COLLAR: una pared corta que sube desde el borde del hueco "
                        "(3 por defecto, o sea ~1.2 mm de alto con capa 0.4). Le da al encastre una "
                        "superficie de agarre en vez de un canto de un solo cordon. 0 lo apaga.")
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
    p.add_argument("--temp-cama", type=int, metavar="GRADOS",
                   help="temperatura de cama. El g-code de referencia usa 70 para PETG, no los 80 "
                        "que pone --material: diez grados de mas dejan la pieza blanda mas tiempo.")
    p.add_argument("--temp-primera-capa", type=int, metavar="GRADOS",
                   help="boquilla SOLO para la primera capa. La referencia arranca a 250 para que "
                        "agarre y baja a 240 para el cuerpo; el truco es que la de adherencia y la "
                        "de impresion no tienen por que ser la misma.")
    p.add_argument("--espera-desde", type=float, default=0.0, metavar="FRACCION",
                   help="poner las esperas SOLO por encima de esa fraccion de la altura. La "
                        "referencia las pone unicamente en la zona calada (z28-69.7 de 97), no en "
                        "la base maciza: abajo no hay puente que cuajar y cada espera lleva una "
                        "retraccion, o sea una oportunidad de hilo.")
    p.add_argument("--material", choices=["PLA", "PETG"], default="PLA",
                   help="fija boquilla y cama. PETG: 245/80 y ventilador al 40%%, que es lo que "
                        "usan los dos gcodes de referencia; a 100%% el PETG no suelda entre capas "
                        "y una pieza en modo vaso, que es todo pared, se abre.")
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
    p.add_argument("--ventilador-desde", type=float, default=0.0, metavar="FRACCION",
                   help="prender el ventilador a partir de esa FRACCION de la altura (0.89 = el "
                        "ultimo 11%%). Es lo mismo que --ventilador-en pero relativo, asi que "
                        "sigue cayendo donde corresponde cuando se mueve --perfil-escala: con la "
                        "altura absoluta, una pieza escalada a 1.38 prendia el aire al 65%% en vez "
                        "del 89%% y soplaba sobre un tercio de pieza que no lo necesita. "
                        "El porcentaje lo fija --ventilador-desde-pct.")
    p.add_argument("--ventilador-desde-pct", type=int, default=100, metavar="PCT",
                   help="a que potencia prende --ventilador-desde (por defecto 100). El g-code de "
                        "referencia pasa de 0 a 100 de una: el blower tarda 500-1000 ms en cambiar "
                        "de regimen y no sigue una rampa fina.")
    p.add_argument("--segundos-vuelta", type=float, default=25.0, metavar="SEG",
                   help="mantener ESE tiempo por vuelta en toda la pieza, calculando la velocidad "
                        "sola a partir del perimetro. Es lo que gobierna si el cordon cuaja antes "
                        "de que le apoyen el siguiente encima: donde la pieza se angosta la vuelta "
                        "se acorta, y a velocidad fija el cabezal vuelve al mismo punto mucho antes. "
                        "Medido en la cabeza del hongo: 35 s por vuelta en el ecuador y 3.5 s en el "
                        "apice. Reemplaza a escribir --velocidad-en a mano, que ademas queda mal "
                        "en cuanto se cambia --perfil-escala porque son alturas absolutas. "
                        "La velocidad nunca baja del piso de caudal ni sube de --velocidad. "
                        "El defecto de 25 s NO es un criterio propio: es lo que mide el g-code de "
                        "referencia (`Squeezy Fidget Toy.gcode`), 25 s de mediana en sus DOS "
                        "cupulas, que es una pieza impresa y viable. 0 lo apaga y vuelve a la "
                        "velocidad fija de --velocidad.")
    p.add_argument("--caudal-minimo", type=float, default=3.8, metavar="MM3_S",
                   help="piso de caudal para --segundos-vuelta, en mm3/s (por defecto 3.8). Por "
                        "debajo de esto la boquilla babea y el material se acumula en vez de "
                        "correrse: es lo que hizo grumos en el apice de una prueba a 1.2 mm3/s. "
                        "El 3.8 sale del g-code de referencia, que nunca baja de ahi.")
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
    if args.material == "PETG":
        ajustes.setdefault("temp_boquilla", 245)
        ajustes.setdefault("temp_cama", 80)
        ajustes.setdefault("ventilador", 40)
    if args.temp_cama is not None:
        ajustes["temp_cama"] = args.temp_cama
    # La del PERFIL es la del calentado inicial, o sea con la que se imprime la
    # primera capa: el `M104` del cuerpo recién baja a la de impresión cuando la
    # espiral empieza a subir. Por eso `--temp-primera-capa` va acá y no en el
    # cuerpo. El empaquetador la copia al start g-code de la plantilla.
    if args.temp_primera_capa is not None:
        ajustes["temp_boquilla"] = args.temp_primera_capa
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
        # El piso automático —hasta que el patrón llega a amplitud completa— lo
        # pone `generar_pieza`; esto solo lo sube más.
        if args.espera_desde:
            modulacion["espera_desde"] = args.espera_desde

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

    # --- silueta desde un DXF ---
    silueta = args.silueta
    altura = args.altura
    if args.perfil:
        from .. import perfil as _perfil
        try:
            # Un STL de revolución entra por el mismo camino que un DXF: se le
            # saca la envolvente exterior y de ahí sale la misma `radio(t)`.
            if args.perfil.lower().endswith(".stl"):
                var = _perfil.variacion_angular_stl(args.perfil)
                print(f"Perfil desde STL: variacion angular {var:.2f} mm"
                      + ("" if var < 3.0 else "  <- OJO: no parece de revolucion,"
                         " se pierde el relieve angular"))
                cs = [_perfil.curva_de_stl(args.perfil)]
            else:
                cs = _perfil.curvas(args.perfil)
            if args.perfil_capa:
                cs = [c for c in cs if c.capa == args.perfil_capa]
            if args.perfil_idx is not None:
                cs = [c for c in cs if c.idx == args.perfil_idx]
            if not cs:
                p.error("--perfil: ninguna curva coincide con --perfil-capa/--perfil-idx")
            curva = _perfil.elegir(cs)
            silueta, info = _perfil.radio_de(curva, args.perfil_desde, args.perfil_hasta)
            if args.perfil_invertir:
                _cruda = silueta
                silueta = lambda t, _f=_cruda: _f(1.0 - t)   # noqa: E731
                info = {**info, "r_base": info["r_boca"], "r_boca": info["r_base"]}
        except (ValueError, OSError) as e:
            p.error(f"--perfil: {e}")
        if args.perfil_escala != 1.0:
            # Se escala DESPUES de recortar y antes de todo lo que mide, para
            # que el aviso de voladizo y la altura que se le pasa al generador
            # hablen de la pieza que se va a imprimir y no del modelo.
            k = args.perfil_escala
            _crudo = silueta
            silueta = lambda t, _f=_crudo, _k=k: _f(t) * _k  # noqa: E731
            info = {**info, "alto": info["alto"] * k,
                    "r_min": info["r_min"] * k, "r_max": info["r_max"] * k,
                    "r_base": info["r_base"] * k, "r_boca": info["r_boca"] * k}
        # La altura sale del modelo salvo que la pidas distinta: el DXF ya la
        # dice, y repetirla a mano es la forma más fácil de que no coincidan.
        if not any(a == "--altura" for a in _sys.argv):
            altura = info["alto"]
        print(f"Perfil de {args.perfil}: {info['curva']}")
        print(f"  z {info['z0']:.1f}..{info['z1']:.1f} -> {info['alto']:.1f} mm de alto, "
              f"radio {info['r_min']:.1f}..{info['r_max']:.1f} mm "
              f"(base {info['r_base']:.1f}, boca {info['r_boca']:.1f})")
        if args.perfil_escala != 1.0:
            print(f"  escalado x{args.perfil_escala:g}: los radios y la altura de arriba YA son "
                  f"los de la pieza chica (el z del modelo no, es donde se recorto).")
        if args.perfil_limitar:
            silueta, rec = _perfil.limitar(silueta, info["alto"], perfil.altura_capa, perfil.ancho)
            print(f"  perfil limitado: {rec['tocados']} de {rec['muestras']} muestras recortadas. "
                  f"La boca pasa de Ø{2*rec['r_boca_antes']:.1f} a Ø{2*rec['r_boca_despues']:.1f} mm "
                  f"— esa punta queda ABIERTA.")
        malos = _perfil.voladizo(silueta, info["alto"], perfil.altura_capa, perfil.ancho)
        if malos:
            peor = max(malos, key=lambda m: m[2])
            print(f"AVISO: {len(malos)} vueltas quedan separadas mas que el cordon "
                  f"({perfil.ancho:g} mm): ahi la pared no apoya sobre la anterior. La peor, "
                  f"{peor[2]:.2f} mm de separacion ({peor[1]:.0f} grados desde la vertical) "
                  f"en z={info['z0'] + peor[0]*info['alto']:.1f}.")

    # --- velocidad calculada para mantener los segundos por vuelta ----------
    #
    # Va acá y no arriba con los otros `--velocidad-en` porque necesita la
    # silueta ya resuelta: la velocidad de cada altura sale del PERÍMETRO que
    # tiene la pieza ahí.
    #
    # El problema que resuelve: a velocidad fija, el tiempo por vuelta sigue al
    # perímetro. Medido en la cabeza del hongo, 35 s en el ecuador y 3.5 s en el
    # ápice — y es justo arriba, donde la pared se acuesta, donde el cordón más
    # necesita cuajar antes de que le apoyen el siguiente encima.
    #
    # Escribirlo a mano con `--velocidad-en` funciona para UN tamaño y queda mal
    # en cuanto se mueve `--perfil-escala`: son alturas absolutas, así que en una
    # pieza más grande la rampa arranca a mitad de camino. Medido a escala 1.38:
    # frenaba al 63 % de la altura, se agotaba con 40 mm por delante y terminaba
    # igual en 9 s por vuelta.
    # El ventilador, relativo a la altura por el mismo motivo que la velocidad.
    if args.ventilador_desde > 0:
        z_aire = round(altura * min(1.0, args.ventilador_desde), 2)
        cambios[z_aire] = fc.Fan(speed_percent=args.ventilador_desde_pct)
        print(f"  ventilador {args.ventilador_desde_pct}% desde z{z_aire:.1f} "
              f"({100*args.ventilador_desde:.0f}% de los {altura:.1f} mm)")

    if args.segundos_vuelta > 0:
        import math as _math
        # SOLO desde donde la pared se acuesta, no en toda la pieza.
        #
        # Mantener los segundos por vuelta abajo no sirve: ahí la pared es
        # vertical, la vuelta apoya entera sobre la anterior y el tiempo de
        # enfriado no decide nada — sólo se pierde tiempo. Medido: sin este
        # recorte, la pieza a escala 1.0 frenaba desde el 2 % de la altura
        # (radio 58 mm, perímetro 366 mm, 366/25 = 14.6 mm/s por debajo del
        # techo) mientras la de escala 1.38 no frenaba hasta el 94 %. El mismo
        # criterio daba comportamientos opuestos según el tamaño.
        #
        # La referencia lo confirma: `Squeezy` tiene 25 s de MEDIANA pero p10 de
        # 14 s. No sostiene 25 en todas partes.
        #
        # Arranca donde entra el aire, que es el mismo sitio por el mismo
        # motivo: donde la cúpula empieza a cerrar.
        desde_t = args.ventilador_desde if args.ventilador_desde > 0 else 0.0
        area = perfil.ancho * perfil.altura_capa
        piso_mm_min = args.caudal_minimo / max(area, 1e-9) * 60.0
        techo_mm_min = float(perfil.velocidad_impresion)
        PASO_MUESTREO = 2.0     # mm de altura entre escalones
        n = max(2, int(altura / PASO_MUESTREO))
        ultimo = None
        for i in range(n + 1):
            z = altura * i / n
            if z < altura * desde_t:
                continue
            r = silueta(min(1.0, z / max(altura, 1e-9)))
            mm_min = 2 * _math.pi * r / args.segundos_vuelta * 60.0
            mm_min = min(techo_mm_min, max(piso_mm_min, mm_min))
            mm_min = int(round(mm_min / 20) * 20)     # escalones de 20 mm/min
            if mm_min != ultimo and z > 0:
                cambios[round(z, 2)] = fc.Printer(print_speed=mm_min)
                ultimo = mm_min
        print(f"  velocidad por perímetro desde {100*desde_t:.0f}% de la altura: "
              f"{args.segundos_vuelta:g} s por vuelta · "
              f"piso {piso_mm_min/60:.1f} mm/s ({args.caudal_minimo:g} mm³/s) · "
              f"techo {techo_mm_min/60:.1f} mm/s · {len(cambios)} escalones")

    nombre = args.nombre or f"bowl_{args.diseno}"
    pasos = pasos_bowl(
        diseno=args.diseno,
        silueta=silueta,
        altura=altura,
        perfil=perfil,
        parametros=dict(args.parametros),
        parametros_silueta=parametros_silueta,
        segmentos_por_capa=args.segmentos,
        base_solida=not args.sin_base,
        hueco=args.piso or 0.0,
        refuerzo_hueco=args.piso_refuerzo,
        capas_transicion=args.capas_transicion,
        capas_base=args.capas_base,
        cambios=cambios or None,
        modulacion=modulacion or None,
        pintura=pintura,
        deformacion=deformacion,
    )

    # Va DESPUES del marcador FIN DEL START GCODE. Ahi el empaquetador lo deja
    # pasar verbatim; arriba del marcador lo borraria junto con el calentado de
    # FullControl.
    #
    # Con --temp-primera-capa no va al principio sino en cuanto la espiral
    # EMPIEZA A SUBIR, o sea con la primera capa ya puesta: asi la adherencia se
    # hace caliente y el resto de la pieza a la temperatura de impresion. Es lo
    # que hace el g-code de referencia, medido: M104 S250 en z0.0 (dos veces,
    # calentado y espera) y M104 S240 en z0.4, o sea al terminar su primera capa.
    if args.temperatura:
        linea = fc.ManualGcode(text=f"M104 S{args.temperatura} ; temperatura de impresion")
        donde = 0
        if args.temp_primera_capa is not None:
            z0 = next((s.z for s in pasos if isinstance(s, fc.Point) and s.z is not None), None)
            if z0 is not None:
                donde = next(
                    (i for i, s in enumerate(pasos)
                     if isinstance(s, fc.Point) and s.z is not None and s.z > z0 + 1e-6),
                    0)
        pasos.insert(donde, linea)

    if args.plot:
        previsualizar(pasos)
        return

    if args.preview or args.solo_preview:
        print(f"Preview: {guardar_html(pasos, nombre=nombre, perfil=perfil)}")

    if not args.solo_preview:
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
            # El tope del slider de escala sale de la CAMA, no de un número
            # fijo: depende de cuánto mide esta pieza. Se calcula contra el
            # volumen de la A1 (256 x 256 x 256) dejando 6 mm de margen en
            # planta — la boquilla necesita lugar para el cordón y el arranque
            # de la espiral, y las líneas de purga viven en Y 5-6.
            rangos = None
            if args.perfil:
                CAMA_XY, CAMA_Z, MARGEN = 256.0, 256.0, 6.0
                ancho_actual = 2 * info["r_max"]
                alto_actual = altura
                if ancho_actual > 0 and alto_actual > 0:
                    tope_xy = (CAMA_XY - 2 * MARGEN) / ancho_actual
                    tope_z = CAMA_Z / alto_actual
                    tope = round(min(tope_xy, tope_z) * args.perfil_escala, 2)
                    rangos = {"--perfil-escala": (0.05, max(0.1, tope))}
            guardar_receta(nombre, _sys.argv, "lamparas.bowls", desc,
                           extra={"mapeo": dict(ULTIMO_MAPEO),
                                  "toques": args.toques or None},
                           rangos=rangos)
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas)")


if __name__ == "__main__":
    _cli()
