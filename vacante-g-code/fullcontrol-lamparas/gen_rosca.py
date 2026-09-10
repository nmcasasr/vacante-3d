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
                            guardar_gcode, peor_salto_radial)
from lamparas import rosca

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
ap.add_argument("--ventilador", type=int, default=50,
                help="%%. El PETG de referencia corre al 50, no apagado.")
ap.add_argument("--nombre", default=None, help="base del archivo; por defecto, el patrón")
ap.add_argument("--capas-base", type=int, default=1,
                help="anillos planos antes de que arranque la espiral")
ap.add_argument("--paso-fijo", choices=["auto", "si", "no"], default="auto",
                help="altura de capa constante en vez de marcha adaptativa. "
                     "'auto' la usa solo si las vueltas siguen solapando.")
args = ap.parse_args()

cual = args.patron
velocidades = args.velocidad or VELOCIDADES
altura = args.altura
nombre = args.nombre or cual

def perfil_de(velocidad):
    # PETG, boquilla 0.8. El cordón va a 1.2 para que el lomo del hilo salga
    # macizo: con 0.8 el hilo queda hueco y es justo la parte que carga.
    #
    # El caudal es lo que pone el techo, no la velocidad: el PETG de referencia
    # declara `filament_max_volumetric_speed = 16`, y con este cordón
    # (1.2 x ~0.31 = 0.367 mm2/mm) eso son 2616 mm/min. Por encima subextruye,
    # y subextruir acá no se ve como un defecto: se ve como una rosca floja.
    return Perfil(diametro_boquilla=0.8, altura_capa=0.4, ancho_linea=1.2,
                  velocidad_impresion=velocidad, temp_boquilla=245,
                  temp_cama=80, ventilador=args.ventilador)

base = perfil_de(velocidades[0])

# `ancho_cordon` compensa que generar_pieza recibe la TRAYECTORIA: el cordón va
# centrado en ella, así que sin esto la pared sale medio cordón más afuera y el
# hilo no entra en la hembra.
if cual in RELIEVES:
    funcion_radio = RELIEVES[cual](altura=altura, ancho_cordon=base.ancho)
else:
    funcion_radio = rosca.rosca(PATRONES[cual](), altura=altura, ancho_cordon=base.ancho)

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
paso_fijo = args.paso_fijo == "si"
paso_z = PASO_FIJO_Z if args.paso_fijo != "no" else None
if args.paso_fijo == "auto":
    salto = peor_salto_radial(funcion_radio, altura, PASO_FIJO_Z)
    paso_fijo, solape = conviene_paso_fijo(funcion_radio, altura, PASO_FIJO_Z, base.ancho)
    print(f"  paso fijo {PASO_FIJO_Z:.2f} mm -> peor salto radial {salto:.3f} mm, "
          f"solape {solape*100:.0f}% -> {'FIJO' if paso_fijo else 'ADAPTATIVO'}",
          flush=True)
if not paso_fijo:
    paso_z = None

print(f"calculando '{cual}', {altura:.0f} mm ({altura/rosca.PASO:.1f} vueltas de rosca), "
      f"ventilador {args.ventilador}%...", flush=True)
pasos = generar_pieza(funcion_radio, altura=altura, perfil=base,
                      segmentos_por_capa=SEGMENTOS, capas_base=args.capas_base,
                      paso_z=paso_z, paso_fijo=paso_fijo)
print(f"  {len(pasos)} pasos", flush=True)

for v in velocidades:
    p = perfil_de(v)
    # se reemplaza el paso de velocidad; el resto de la lista son los puntos
    emitir = [fc.Printer(print_speed=p.velocidad_impresion,
                         travel_speed=p.velocidad_viaje)
              if isinstance(x, fc.Printer) else x for x in pasos]
    ruta = guardar_gcode(a_gcode(emitir, p), f"rosca/{nombre}_v{v}")
    caudal = p.ancho * 0.306 * v / 60
    print(f"  {ruta.name:28s} {v:5d} mm/min = {v/60:4.0f} mm/s  ~{caudal:4.1f} mm3/s", flush=True)
