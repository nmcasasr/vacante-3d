"""
Genera el tornillo macho de la lámpara, en `output/rosca/`.

El perfil de la rosca no es inventado: sale medido de `tuerca.stl` y vive en
`lamparas/envolvente_hembra.py`. `rosca.perfil_clasico` reproduce la pieza que
ya imprimís; los patrones sólo le quitan material, así que cualquiera de ellos
enrosca en la misma hembra sin verificar interferencia.

    python gen_rosca.py                                  # todas las velocidades
    python gen_rosca.py caritas --velocidad 2400
    python gen_rosca.py clasico --altura 40 --nombre cupon

La velocidad NO entra en la geometría: `generar_pieza` sólo la usa para el paso
`fc.Printer`. Por eso los puntos se calculan UNA vez y se reemiten con cada
velocidad, en lugar de rehacer la pieza entera cinco veces.
"""
import argparse
import math
import sys
sys.path.insert(0, '.')
import fullcontrol as fc
from lamparas.comun import (Perfil, a_gcode, conviene_paso_fijo, generar_pieza,
                            guardar_gcode, guardar_receta, peor_salto_radial)
from lamparas import rosca
from lamparas.velocidad import (modular_por_voladizo, SQUEEZY_VOLADIZO,
                                CAUDAL_MAX, MATERIALES, caudal, caudal_pico, velocidad_para)

ALTURA = 230.0
SEGMENTOS = 360          # el perfil del hilo se recorre entero en cada vuelta

PATRONES = {
    "clasico":      lambda: None,
    "perlas":       lambda: rosca.p_perlas(20),
    "interrumpida": lambda: rosca.p_interrumpida(6),
    "caritas":      lambda: rosca.p_caritas(16),
    "ondas":        lambda: rosca.p_ondas(24),
    "chevron":      lambda: rosca.p_chevron(12),
    "moleteado":    lambda: rosca.p_moleteado(30),
    "corazones":    lambda: rosca.p_sello("corazon", 16),
    "estrellas":    lambda: rosca.p_sello("estrella", 16),
    "circulos":     lambda: rosca.p_lienzo(rosca.imagen_circulos(52.0, 5, 54.0)),
    "cuadros":      lambda: rosca.p_lienzo(rosca.imagen_cuadros(42.0, 5, 54.0)),
    "caritas_lienzo": lambda: rosca.p_lienzo(
        rosca.imagen_caritas(int(__import__("os").environ.get("NCARAS","6"))), portadora_n=0),
    "corazones_lienzo": lambda: rosca.p_lienzo(
        rosca.imagen_forma("corazon", 72, 78, 4, 94.5)),
    "estrellas_lienzo": lambda: rosca.p_lienzo(
        rosca.imagen_forma("estrella", 72, 72, 4, 94.5)),
}

# `caritas_relieve` no es un patrón: los rasgos no rebajan un hilo previo, SON
# el hilo. Devuelve la FuncionRadio entera, así que se trata aparte.
RELIEVES = {
    "caritas_relieve":   rosca.caritas_relieve,
    # Ojos de LÍNEA VERTICAL y caras en damero. Los números, medidos:
    #   alto_ojo 1.8   3.6 mm de arco, o sea 3.6 cordones de 1.0: más angosto
    #                  se lo come la línea, que es la causa candidata de que los
    #                  rasgos no salieran en la tanda anterior. Ensancharlo es
    #                  GRATIS —el salto radial se queda en 0.413 mm hasta 4.8 mm
    #                  de ojo— así que el único límite es que se siga leyendo
    #                  como línea: a 3.6 x 9.2 mm la proporción es 2.6 a 1.
    #   ojo_v 4.6      9.2 mm de alto contra 6.7 del ojo redondo, y sin llegar
    #                  a PASO/2 = 6.75, que es donde el ojo invadiría la fila
    #                  de al lado. La pendiente en `d` BAJA de 0.92 a 0.67.
    #   n 10           par, así que la alternancia cierra sin costura (con 9 las
    #                  caras 8 y 0 son vecinas y salen iguales). De paso el
    #                  hueco sin apoyo baja de 27.5 a 23.9 mm.
    "caritas_intercalada": lambda **kw: rosca.caritas_relieve(
        n_por_vuelta=10, alto_ojo=1.8, ojo_v=4.6, intercalar=True, **kw),
    # Discos que sobresalen con una figura hundida en la cara: `perlas` y
    # `sellos_relieve` cruzados. 32 por vuelta deja 9.97 mm de paso para una
    # pastilla de Ø8.40, o sea 1.6 mm de hueco entre vecinas.
    "pastillas": rosca.pastillas,
    # El disco más grande que la envolvente admite, Ø9.25. Se lee mejor pero
    # deja el juego axial en 0.16 mm (1 % del paso), más apretado que el diente
    # más gordo posible: sin margen para la variación del plástico. El de
    # `pastillas` es Ø8.40 y conserva 0.94 mm.
    "pastillas_max": lambda **kw: rosca.pastillas(n_por_vuelta=30, radio=None, **kw),
    "corazones_relieve": lambda **kw: rosca.sellos_relieve("corazon", **kw),
    "estrellas_relieve": lambda **kw: rosca.sellos_relieve("estrella", **kw),
}

# mm/min. Con cordón 1.2 x ~0.31 el caudal va de 7.3 a 22 mm3/s; para PETG con
# boquilla de 0.8, de 2400 para arriba ya es zona de exigirle al extrusor.
VELOCIDADES = [1200, 1800, 2400, 3000, 3600]

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("patron", nargs="?", default="clasico",
                choices=list(PATRONES) + list(RELIEVES))
ap.add_argument("--velocidad", type=int, action="append",
                help="mm/min. Repetible. Sin esto salen todas.")
ap.add_argument("--altura", type=float, default=ALTURA,
                help="mm. 40 da un cupón de tres vueltas de rosca.")
ap.add_argument("--ventilador", type=int, default=None,
                help="%%. Por defecto, el del material (PLA 75, PETG 50).")
ap.add_argument("--nombre", default=None, help="base del archivo; por defecto, el patrón")
ap.add_argument("--diente", type=float, default=0.0,
                help="0 = perfil clásico (el que ya imprimís, 3.75 mm de juego "
                     "axial). 1 = la envolvente entera (0.28 mm). Intermedios "
                     "engordan el diente sin tocar la holgura radial. No aplica "
                     "a los relieves, que construyen su propio perfil.")
ap.add_argument("--caudal-max", type=float, default=None,
                help="mm3/s. Si la velocidad pedida se pasa, se BAJA hasta "
                     "respetarlo, que es lo que hace Orca. Por defecto, el del "
                     "material: PLA %.0f, PETG %.0f." % (CAUDAL_MAX["PLA"], CAUDAL_MAX["PETG"]))
ap.add_argument("--segmentos", type=int, default=SEGMENTOS,
                help="puntos por vuelta. A Ø103 los 360 por defecto son 0.86 mm "
                     "por segmento, y un ojo de carita mide 3.4 mm de arco: le "
                     "tocan CUATRO puntos, y a algunos rasgos uno solo. Para un "
                     "dibujo con detalle hacen falta 1440 o más.")
ap.add_argument("--ancho", type=float, default=1.2,
                help="mm de cordón. En modo vaso ES el espesor de pared. "
                     "El par que ya se imprimió y encaja usa 0.82 con boquilla "
                     "de 0.8; 1.2 es lo que veníamos generando.")
ap.add_argument("--velocidad-voladizo", type=float, default=None,
                help="mm/min en los tramos donde el cordón sale al aire. "
                     "Squeezy usa %d (la mitad de su velocidad normal). "
                     "Sin esto la velocidad es constante." % SQUEEZY_VOLADIZO)
ap.add_argument("--material", choices=sorted(MATERIALES), default="PETG",
                help="fija temperaturas, ventilador y tope de caudal. Los "
                     "valores salen de los .3mf que ya se imprimieron.")
ap.add_argument("--carpeta", default="rosca",
                help="subcarpeta de output/. 'prueba' para una tanda de impresión.")
ap.add_argument("--capas-base", type=int, default=1,
                help="anillos planos antes de que arranque la espiral")
ap.add_argument("--paso-z", type=float, default=None,
                help="mm de altura por vuelta cuando el paso es FIJO. Por "
                     "defecto 0.30. Bajarlo a 0.20 sube la resolución VERTICAL "
                     "del dibujo un 50 %% —el borde de un grabado se cuantiza a "
                     "este paso— y de paso deja lugar para grabar más hondo. "
                     "Cuesta 50 %% más de tiempo.")
ap.add_argument("--pastillas-prof", type=float, default=None,
                help="mm de hondo del grabado; sólo para `pastillas`. 0.45 por "
                     "defecto. Más hondo da más sombra y se lee mejor, y lo "
                     "que cuesta es un filo alrededor de cada figura donde dos "
                     "vueltas solapan menos.")
ap.add_argument("--pastillas-radio", type=float, default=None,
                help="radio del disco en mm; sólo para `pastillas`. Con 1.30 de "
                     "chaflán, la cara donde entra el dibujo mide 2*(radio-1.30). "
                     "4.2 es el defecto y 4.625 el máximo que admite la "
                     "envolvente. OJO: agrandar el disco se come el JUEGO AXIAL, "
                     "que es lo que absorbe la variación del plástico.")
ap.add_argument("--pastillas-achatado", type=float, default=None,
                help="achica el disco sólo en el eje axial; sólo para "
                     "`pastillas`. 1.0 es redondo. Devuelve juego axial sin "
                     "tocar el ancho de la figura, pero empina el chaflán: "
                     "mirá el solape que reporta el generador.")
ap.add_argument("--receta", action="store_true",
                help="deja un .params.json al lado del g-code para que el "
                     "preview ofrezca los sliders. Pide UNA sola --velocidad, y "
                     "el archivo sale sin el sufijo _vNNNN: la extensión relee "
                     "SIEMPRE la misma ruta, y con el sufijo el freno de caudal "
                     "la renombra sola en cuanto un slider mueve la sección.")
ap.add_argument("--sin-receta", action="store_true",
                help="no escribe la receta. Es lo que usa el preview mientras "
                     "arrastrás un slider, para que el borrador de baja "
                     "resolución no quede pegado como receta buena.")
ap.add_argument("--pastillas-n", type=int, default=None,
                help="pastillas por vuelta; sólo para los patrones `pastillas`. "
                     "Menos pastillas = más hueco entre ellas. Con Ø8.40 de "
                     "disco: 32 deja 1.6 mm de hueco, 24 deja 4.9 (igual que el "
                     "vertical, que lo fija el paso de rosca), 16 deja 11.6. "
                     "El salto radial no se mueve con esto, así que el paso "
                     "sigue fijo en todos; lo que baja es el apoyo.")
ap.add_argument("--separacion-por-angulo", action="store_true",
                help="calcula la sección extruida en CADA ÁNGULO en vez de una "
                     "por vuelta tomada del peor ángulo. En una rosca sólo los "
                     "flancos están a 43%%: con una sola separación toda la "
                     "vuelta recibe la sección del flanco y la pared sale un "
                     "32%% más gruesa de lo pedido (1.32 mm midiendo 1.0).")
ap.add_argument("--paso-fijo", choices=["auto", "si", "no"], default="auto",
                help="altura de capa constante en vez de marcha adaptativa. "
                     "'auto' la usa solo si las vueltas siguen solapando.")
args = ap.parse_args()

cual = args.patron
velocidades = args.velocidad or VELOCIDADES
altura = args.altura
nombre = args.nombre or cual

# Con receta, el nombre NO lleva el sufijo de velocidad.
#
# La extensión relee siempre la misma ruta después de regenerar. Con el sufijo
# puesto, cualquier slider que mueva la sección —`--ancho`, `--pastillas-n`—
# hace actuar el freno de caudal, sale otra velocidad, y el generador escribe un
# archivo con OTRO nombre: el preview se queda mirando el viejo.
if args.receta and len(velocidades) != 1:
    ap.error("--receta necesita una sola --velocidad: la receta describe UN "
             "archivo, y sin eso no se sabe cuál de los cinco es.")

# Cómo se llama cada control en el slider. Corto a propósito: el help de
# argparse son cinco líneas y acá entra un renglón.
QUE = {
    "--ancho": "mm de cordón. En modo vaso ES el espesor de pared.",
    "--altura": "mm de pieza. 40 da un cupón de tres vueltas de rosca.",
    "--velocidad": "mm/min. El freno de caudal la baja sola si se pasa.",
    "--diente": "0 = perfil clásico, 1 = envolvente entera. Llena el canal.",
    "--pastillas-n": "pastillas por vuelta. Menos = más hueco entre ellas.",
    "--pastillas-radio": "radio del disco en mm. Más grande = menos juego axial.",
    "--pastillas-achatado": "achata el disco en el eje axial. Menos = más juego.",
    "--pastillas-prof": "mm de hondo del grabado. Más hondo = más sombra.",
    "--paso-z": "mm por vuelta. Menos = más resolución vertical y más tiempo.",
}

def perfil_de(velocidad):
    # PETG, boquilla 0.8. El cordón va a 1.2 para que el lomo del hilo salga
    # macizo: con 0.8 el hilo queda hueco y es justo la parte que carga.
    #
    # El caudal es lo que pone el techo, no la velocidad: el PETG de referencia
    # declara `filament_max_volumetric_speed = 16`, y con este cordón
    # (1.2 x ~0.31 = 0.367 mm2/mm) eso son 2616 mm/min. Por encima subextruye,
    # y subextruir acá no se ve como un defecto: se ve como una rosca floja.
    m = MATERIALES[args.material]
    return Perfil(diametro_boquilla=0.8, altura_capa=0.4, ancho_linea=args.ancho,
                  velocidad_impresion=velocidad, temp_boquilla=m["boquilla"],
                  temp_cama=m["cama"],
                  ventilador=args.ventilador if args.ventilador is not None
                             else m["ventilador"])

base = perfil_de(velocidades[0])

# `ancho_cordon` compensa que generar_pieza recibe la TRAYECTORIA: el cordón va
# centrado en ella, así que sin esto la pared sale medio cordón más afuera y el
# hilo no entra en la hembra.
if cual in RELIEVES:
    extra = {}
    if cual.startswith("pastillas"):
        if args.pastillas_n:
            extra["n_por_vuelta"] = args.pastillas_n
        if args.pastillas_radio:
            extra["radio"] = args.pastillas_radio
        if args.pastillas_achatado:
            extra["achatado"] = args.pastillas_achatado
        if args.pastillas_prof:
            extra["prof"] = args.pastillas_prof
    funcion_radio = RELIEVES[cual](altura=altura, ancho_cordon=base.ancho, **extra)
else:
    funcion_radio = rosca.rosca(PATRONES[cual](), altura=altura,
                                perfil=rosca.perfil_mezcla(args.diente),
                                ancho_cordon=base.ancho)

# --- paso vertical: fijo o adaptativo ---------------------------------------
#
# La marcha adaptativa de `generar_pieza` está pensada para CÚPULAS: acorta el
# paso donde la pared se tumba para que la vuelta siguiente no quede colgando.
# Una rosca no es una cúpula — su pared es vertical y lo que se corre entre
# vueltas es el RADIO, no la inclinación. Aplicarle el mismo criterio produce
# una altura de capa que se bandea entre 0.230 y 0.383 mm en franjas que no
# coinciden con ningún rasgo de la pieza, y con ella se bandea el caudal.
#
# Pero no vale para todos los patrones. Los sellos (corazón, estrella) tienen
# cantos vivos en `d`, o sea en el eje vertical, y ahí el radio SÍ pega saltos
# que ninguna vuelta de paso fijo alcanza a solapar. Así que no se decide por
# gusto: se mide el peor salto radial entre dos vueltas consecutivas y se usa
# paso fijo solo si queda cordón solapado de sobra.
PASO_FIJO_Z = 0.30       # mm; es la media que venía dando la marcha adaptativa
# El criterio de si conviene el paso fijo vive en `lamparas/comun.py`: lo usa
# también la CLI de los bowls, y dos copias de una regla calibrada se separan.
PASO_Z = args.paso_z or PASO_FIJO_Z
paso_fijo = args.paso_fijo == "si"
paso_z = PASO_Z if args.paso_fijo != "no" else None
if args.paso_fijo == "auto":
    salto = peor_salto_radial(funcion_radio, altura, PASO_Z)
    paso_fijo, solape = conviene_paso_fijo(funcion_radio, altura, PASO_Z, base.ancho)
    print(f"  paso fijo {PASO_Z:.2f} mm -> peor salto radial {salto:.3f} mm, "
          f"solape {solape*100:.0f}% -> {'FIJO' if paso_fijo else 'ADAPTATIVO'}",
          flush=True)
if not paso_fijo:
    paso_z = None

print(f"calculando '{cual}', {altura:.0f} mm ({altura/rosca.PASO:.1f} vueltas de rosca), "
      f"{args.material}, ventilador {base.ventilador}%...", flush=True)
pasos = generar_pieza(funcion_radio, altura=altura, perfil=base,
                      segmentos_por_capa=args.segmentos, capas_base=args.capas_base,
                      paso_z=paso_z, paso_fijo=paso_fijo,
                      separacion_por_angulo=args.separacion_por_angulo)
print(f"  {len(pasos)} pasos", flush=True)

for v in velocidades:
    tope = args.caudal_max if args.caudal_max else MATERIALES[args.material]["caudal"]
    # El freno mira el TRAMO GORDO, no el típico. Con la mediana los picos se
    # escapan y salen como línea fina justo en los rasgos. Ver `velocidad.py`.
    pico = caudal_pico(pasos, v)
    if tope and pico and pico > tope:
        v_ok = velocidad_para(pasos, tope)
        print(f"  {v} mm/min daria {pico:.1f} mm3/s en el tramo gordo, por encima "
              f"de {tope:.0f} ({args.material}): se baja a {v_ok:.0f} mm/min", flush=True)
        v = int(v_ok)
    q = caudal(pasos, v)
    pico = caudal_pico(pasos, v)
    p = perfil_de(v)
    # se reemplaza el paso de velocidad; el resto de la lista son los puntos
    emitir = [fc.Printer(print_speed=p.velocidad_impresion,
                         travel_speed=p.velocidad_viaje)
              if isinstance(x, fc.Printer) else x for x in pasos]
    # La modulación va DESPUÉS del reemplazo: si fuera antes, esa lista por
    # comprensión le pisaría cada `Printer` con la velocidad base.
    if args.velocidad_voladizo:
        emitir, est = modular_por_voladizo(emitir, p.centro, p.ancho,
                                           v, args.velocidad_voladizo)
        if est:
            print(f"    voladizo: peor {100*est['peor_frac']:.0f}% del cordón colgando; "
                  f"{100*est['frac_lentos']:.0f}% de los puntos frenados, mínimo "
                  f"{est['v_min']:.0f} mm/min; "
                  f"{est['cambios']} cambios de F; "
                  f"x{est['minutos_con']/est['minutos_sin']:.2f} de tiempo")
    base = f"{args.carpeta}/{nombre}" if args.receta else f"{args.carpeta}/{nombre}_v{v}"
    ruta = guardar_gcode(a_gcode(emitir, p), base)
    print(f"  {ruta.name:28s} {v:5d} mm/min = {v/60:4.0f} mm/s  "
          f"{q:5.1f} mm3/s tipico, {pico:5.1f} en el tramo gordo", flush=True)
    if args.receta and not args.sin_receta:
        # `gen_rosca.py` es un script suelto, no un paquete: `python -m
        # gen_rosca` lo importaría en vez de correrlo.
        r = guardar_receta(base, sys.argv, "gen_rosca.py",
                           descripciones={"": QUE})
        print(f"  receta -> {r.name}", flush=True)
