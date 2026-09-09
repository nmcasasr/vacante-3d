"""
G-code de la TUERCA a partir de un STL de tuerca. Sólo la tuerca: paredes de
lado a lado, sin relleno, sin soportes, sin faldón.

    ./venv/bin/python gen_tuerca.py ../../gcodes/reference/tuerca/mariposa_v3_hembra.stl
    ./venv/bin/python gen_tuerca.py TUERCA.stl --carpeta rosca/prueba --nombre prueba_hembra

Por qué esto se puede emitir sin escribir un laminador
-----------------------------------------------------
Una tuerca cualquiera no se puede: hay que recortar las vueltas entre dos
contornos y la cantidad que entra cambia con el ángulo. Ésta sí, porque su
sección es un anillo entre DOS superficies que se conocen exactamente:

  - por fuera, un cilindro de radio constante (57.20 en la mariposa);
  - por dentro, el barreno helicoidal, que depende sólo de la fase de hélice.

Entonces cada capa son vueltas cerradas y no hay nada que recortar. Lo único
que varía es el espesor del anillo —de 5.03 mm en el fondo del hilo a 6.95 en
la cresta— y eso se absorbe repartiendo la banda del medio entre un número FIJO
de vueltas de ancho variable, en vez de meter más vueltas donde entra una más.

    vuelta 0        barreno + cordón/2        ancho fijo   <- la superficie que mide
    vueltas 1..k    reparten la banda         ancho variable
    vuelta última   exterior - cordón/2       ancho fijo   <- el cilindro

Con k = 3 el ancho de las del medio va de 0.88 a 1.52 mm, que para una boquilla
de 0.8 está dentro de lo que se puede depositar. Si el STL diera una banda muy
distinta, `--medias` lo ajusta.

**El intento anterior hacía las 4 paredes como offsets del mismo barreno**, para
no tener que repartir nada. Salía una tuerca correcta por dentro y un tornillo
por fuera: el exterior copiaba la rosca y ondulaba 1.9 mm. Con el exterior
tomado del STL eso no pasa.

De dónde sale la geometría
--------------------------
El barreno NO se lee capa por capa del STL: se mide una vez como función de la
fase de hélice (`medir_hembra.riel_de_stl`, la misma que usa el verificador) y
se evalúa. Es más fiel, no menos: la tabla promedia el ruido del teselado en
vez de arrastrarlo a cada capa. Y como es la misma función que valida los
machos, el g-code y el veredicto no pueden discrepar.

La fase absoluta se conserva, así que la pieza emitida es intercambiable con la
del STL: enrosca en el mismo sitio.

Se imprime de AFUERA HACIA ADENTRO: el barreno va último y no lo empuja ninguna
vuelta posterior.
"""
import argparse
import math
import sys

sys.path.insert(0, '.')
import fullcontrol as fc

from lamparas.comun import (Perfil, a_gcode, generar_pieza, guardar_gcode,
                            guardar_receta)
from lamparas import rosca
from lamparas.velocidad import (modular_por_voladizo, SQUEEZY_VOLADIZO,
                                MATERIALES, caudal, caudal_pico, velocidad_para)
import medir_hembra as MH

VELOCIDADES = [2400]
MEDIAS = 3               # vueltas de ancho variable entre las dos fijas

# Arranque de capa corrido con la razón áurea: con todas las costuras en el
# mismo ángulo se apilan en una línea y dejan una junta débil de punta a punta,
# justo en la pieza que tiene que aguantar el tirón.
GIRO_COSTURA = 0.6180339887


def medir(ruta):
    """Barreno como tabla de fase, radio exterior y altura, sacados del STL."""
    riel, cobertura, rms, e0, e1 = MH.riel_de_stl(ruta)
    c, cx, cy, z0, z1 = MH.barrenos(ruta)[0]
    r_ext = max(math.hypot(q[0], q[1]) for t in c for q in t)
    return riel, cobertura, rms, r_ext, z1 - z0


PASO_FIJO_Z = 0.30       # el mismo que usa el macho
SOLAPE_MINIMO = 0.5


def peor_salto_radial(fr, dz, altura, n_ang=360):
    """Cuánto se corre el radio entre dos vueltas seguidas, en el peor ángulo."""
    angs = [k / n_ang * 2 * math.pi for k in range(n_ang)]
    peor = 0.0
    z = 0.0
    while z + dz <= altura:
        t, t2 = z / altura, (z + dz) / altura
        peor = max(peor, max(abs(fr(a, t2) - fr(a, t)) for a in angs))
        z += dz
    return peor


PEND_ENTRADA = 0.40      # mm de radio por mm de altura, ~22° desde la vertical


def como_vaso(riel, altura, perfil, segmentos, capas_base, entrada=3.0,
               separacion_por_angulo=False):
    """
    La tuerca en MODO VASO, igual que los machos.

    Con un solo cordón de pared, la tuerca es topológicamente idéntica al macho:
    un tubo cuyo radio depende de la fase de hélice. Lo único que cambia es la
    función de radio — el macho la toma de `perfil_clasico` y le RESTA medio
    cordón; la hembra la toma del barreno medido y le SUMA medio cordón, porque
    su pared queda del lado de afuera.

    Emitirla como capas planas fue un error: son 93 vueltas cerradas con un
    viaje entre cada una, y como la costura se escalona ese viaje cruza la pieza
    de lado a lado. Una espiral no tiene viajes ni costura, y de paso hereda
    todo lo que `generar_pieza` ya sabe hacer: paso fijo o adaptativo, primera
    vuelta apoyada en la cama, verificación de voladizo.
    """
    media = perfil.ancho / 2.0

    def funcion_radio(angulo, t):
        z = t * altura
        b = int(rosca.coordenada_hilo(angulo, z) / rosca.PASO * MH.N_FASE)
        r = riel[b % MH.N_FASE] + media
        # Chaflán de entrada, a 45°, y no es decoración.
        #
        # `generar_pieza` arranca la espiral con una RAMPA: los primeros
        # milímetros la z impresa todavía no es la del modelo, así que la fase
        # va corrida y el radio sale hasta 0.55 mm fuera de sitio. En un macho
        # da igual —el pie queda un poco gordo y no estorba— pero en una hembra
        # ese error AHOGA LA BOCA justo por donde tiene que entrar el tornillo.
        # Medido: 0.55 mm a z 1.0 y 0.24 a z 1.5, cero a partir de z 2.
        #
        # El chaflán abre la boca más de lo que la rampa la cierra (1.0 mm a
        # z 1.0), y como sólo QUITA material no puede interferir: lo único que
        # cuesta es que la primera media vuelta no engrane. Toda tuerca de
        # verdad lo tiene, por la misma razón práctica de poder empezar a
        # enroscar sin trabarse en el canto.
        #
        # La PENDIENTE importa tanto como la altura. A 45° el chaflán suma 0.30
        # al salto radial por vuelta, el total se va a 0.739 y `gen_rosca` se
        # pasa a marcha adaptativa. A 0.40 (unos 22° desde la vertical) suma
        # 0.12, el paso fijo se mantiene, y repartido en 3 mm abre 0.8 mm a
        # z 1.0: más que los 0.55 que cierra la rampa.
        return r + max(0.0, entrada - z) * PEND_ENTRADA

    salto = peor_salto_radial(funcion_radio, PASO_FIJO_Z, altura, segmentos)
    solape = (perfil.ancho - salto) / perfil.ancho
    fijo = solape >= SOLAPE_MINIMO
    print(f"  paso fijo {PASO_FIJO_Z:.2f} mm -> peor salto radial {salto:.3f} mm, "
          f"solape {solape*100:.0f}% -> {'FIJO' if fijo else 'ADAPTATIVO'}", flush=True)

    return generar_pieza(funcion_radio, altura=altura, perfil=perfil,
                         segmentos_por_capa=segmentos, capas_base=capas_base,
                         paso_z=PASO_FIJO_Z if fijo else None, paso_fijo=fijo,
                         separacion_por_angulo=separacion_por_angulo)


def recorrido(riel, r_ext, altura, perfil, medias, segmentos, paredes=0):
    """Capas planas de vueltas concéntricas. Devuelve (pasos, n_capas, avisos)."""
    cx, cy = perfil.centro
    w = perfil.ancho
    n_capas = max(1, int(round(altura / perfil.altura_capa)))
    dz = altura / n_capas

    pasos = [
        fc.ExtrusionGeometry(area_model="rectangle", width=w, height=dz),
        fc.Printer(print_speed=perfil.velocidad_impresion,
                   travel_speed=perfil.velocidad_viaje),
    ]

    def barreno(ang, z):
        b = int(rosca.coordenada_hilo(ang, z) / rosca.PASO * MH.N_FASE)
        return riel[b % MH.N_FASE]

    anchos_vistos = []
    ultimo_ancho = [w]

    def emitir_vuelta(z, a0, radio_de, ancho_de):
        puntos = []
        for i in range(segmentos + 1):          # +1 para cerrar la vuelta
            ang = a0 + 2 * math.pi * i / segmentos
            an = ancho_de(ang, z)
            if abs(an - ultimo_ancho[0]) > 0.01:
                puntos.append(fc.ExtrusionGeometry(area_model="rectangle",
                                                   width=an, height=dz))
                ultimo_ancho[0] = an
            r = radio_de(ang, z)
            puntos.append(fc.Point(x=cx + r * math.cos(ang),
                                   y=cy + r * math.sin(ang), z=z))
        # Viaje sin extruir hasta el arranque. FullControl necesita un punto
        # previo para medir la primera línea, así que el primero también va así.
        primero = next(i for i, p in enumerate(puntos) if isinstance(p, fc.Point))
        pasos.extend(puntos[:primero])
        pasos.append(fc.Extruder(on=False))
        pasos.append(puntos[primero])
        pasos.append(fc.Extruder(on=True))
        pasos.extend(puntos[primero + 1:])

    for capa in range(n_capas):
        z = (capa + 1) * dz
        a0 = 2 * math.pi * ((capa * GIRO_COSTURA) % 1.0)

        if paredes:
            # Pared de espesor constante: `paredes` cordones corridos del
            # barreno hacia afuera. El exterior del STL no se usa, así que la
            # cara de afuera copia la rosca — con un cordón no hay otra: una
            # sola pared no puede dar dos superficies distintas.
            for k in range(paredes - 1, -1, -1):
                emitir_vuelta(z, a0,
                              lambda ang, zz, k=k: barreno(ang, zz) + w / 2 + k * w,
                              lambda ang, zz: w)
                anchos_vistos.append(w)
            continue

        # de afuera hacia adentro: el barreno queda último
        emitir_vuelta(z, a0, lambda ang, zz: r_ext - w / 2, lambda ang, zz: w)
        for k in range(medias, 0, -1):
            def radio_de(ang, zz, k=k):
                b = barreno(ang, zz)
                banda = (r_ext - w) - (b + w)
                return b + w + banda * (k - 0.5) / medias
            def ancho_de(ang, zz):
                banda = (r_ext - w) - (barreno(ang, zz) + w)
                anchos_vistos.append(banda / medias)
                return banda / medias
            emitir_vuelta(z, a0, radio_de, ancho_de)
        emitir_vuelta(z, a0, lambda ang, zz: barreno(ang, zz) + w / 2,
                      lambda ang, zz: w)

    return pasos, n_capas, dz, (min(anchos_vistos), max(anchos_vistos))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stl", help="STL de la tuerca sola (anillo con barreno roscado)")
    ap.add_argument("--velocidad", type=int, action="append", help="mm/min. Repetible.")
    ap.add_argument("--altura-capa", type=float, default=0.4,
                    help="mm: el paso NOMINAL del perfil, no la subida real. "
                         "Igual que `gen_rosca.py`, queda en 0.4 mientras la "
                         "marcha va a %.2f. Ponerlo en 0.30 hace que "
                         "`_verificar_apoyo` marque todas las vueltas: compara "
                         "el hueco vertical contra este número, y el paso fijo "
                         "redondea a 0.30107." % PASO_FIJO_Z)
    ap.add_argument("--ancho", type=float, default=1.2, help="mm de cordón")
    ap.add_argument("--medias", type=int, default=MEDIAS,
                    help="vueltas de ancho variable entre el barreno y el exterior")
    ap.add_argument("--receta", action="store_true",
                    help="deja un .params.json al lado del g-code para que el "
                         "preview ofrezca los sliders. Pide UNA sola "
                         "--velocidad y el archivo sale sin el sufijo _vNNNN: "
                         "la extensión relee siempre la misma ruta.")
    ap.add_argument("--sin-receta", action="store_true",
                    help="no escribe la receta. Lo usa el preview mientras "
                         "arrastrás un slider.")
    ap.add_argument("--separacion-por-angulo", action="store_true",
                    help="calcula la sección extruida en CADA ÁNGULO en vez de "
                         "una por vuelta tomada del peor ángulo. Sin esto la "
                         "pared de la tuerca sale 1.75 mm pidiendo 1.0. Sólo "
                         "aplica al modo vaso.")
    ap.add_argument("--macizo", action="store_true",
                    help="pieza maciza de capas planas, con el exterior "
                         "cilíndrico del STL. Por defecto sale en MODO VASO, un "
                         "cordón de pared, igual que los machos.")
    ap.add_argument("--capas-base", type=int, default=1,
                    help="anillos planos antes de que arranque la espiral")
    ap.add_argument("--entrada", type=float, default=3.0,
                    help="mm de chaflán a 45° en la boca. Tapa el error de la "
                         "rampa de arranque, que ahoga el barreno hasta 0.55 mm "
                         "en los primeros 2 mm.")
    ap.add_argument("--segmentos", type=int, default=360)
    ap.add_argument("--ventilador", type=int, default=None,
                    help="%%. Por defecto, el del material (PLA 75, PETG 50).")
    ap.add_argument("--caudal-max", type=float, default=None,
                    help="mm3/s. Por defecto el del material. Si la velocidad "
                         "pedida se pasa, se baja, como hace Orca.")
    ap.add_argument("--velocidad-voladizo", type=float, default=None,
                    help="mm/min en los tramos donde el cordón sale al aire. "
                         "Squeezy usa %d (la mitad de su velocidad normal). "
                         "Sin esto la velocidad es constante." % SQUEEZY_VOLADIZO)
    ap.add_argument("--material", choices=sorted(MATERIALES), default="PETG",
                    help="fija temperaturas, ventilador y tope de caudal. Los "
                         "valores salen de los .3mf que ya se imprimieron.")
    ap.add_argument("--carpeta", default="rosca")
    ap.add_argument("--nombre", default="tuerca")
    args = ap.parse_args()

    print(f"midiendo {args.stl} ...", flush=True)
    riel, cobertura, rms, r_ext, altura = medir(args.stl)
    print(f"  barreno R{min(riel):.3f}..{max(riel):.3f}  exterior R{r_ext:.3f}  "
          f"alto {altura:.2f} mm ({altura / rosca.PASO:.2f} vueltas)")
    print(f"  {100 * cobertura:.0f} % de las fases medidas; contra `perfil_hembra` "
          f"RMS {rms:.4f} mm  {'OK' if rms < 0.05 else 'NO es esta rosca'}")
    if rms >= 0.05:
        sys.exit(1)
    if args.macizo:
        print(f"  MACIZO: pared {r_ext - max(riel):.2f}..{r_ext - min(riel):.2f} mm, "
              f"{args.medias + 2} vueltas por capa, sin relleno")
    else:
        print(f"  MODO VASO: un cordón de {args.ancho:.2f} mm, sin viajes ni "
              f"costura; la cara de afuera copia la rosca")
        print(f"  chaflán de entrada {args.entrada:.1f} mm: quedan "
              f"{(altura - args.entrada) / rosca.PASO:.2f} vueltas engranando")

    velocidades = args.velocidad or VELOCIDADES
    if args.receta and len(velocidades) != 1:
        ap.error("--receta necesita una sola --velocidad: la receta describe UN "
                 "archivo, y con el sufijo _vNNNN puesto el freno de caudal "
                 "renombra el archivo en cuanto un slider mueve la sección.")

    m = MATERIALES[args.material]

    def perfil_de(v):
        return Perfil(diametro_boquilla=0.8, altura_capa=args.altura_capa,
                      ancho_linea=args.ancho, velocidad_impresion=v,
                      temp_boquilla=m["boquilla"], temp_cama=m["cama"],
                      ventilador=args.ventilador if args.ventilador is not None
                                 else m["ventilador"])

    base = perfil_de(velocidades[0])
    if args.macizo:
        pasos, n_capas, dz, (an0, an1) = recorrido(
            riel, r_ext, altura, base, args.medias, args.segmentos, 0)
        print(f"  {n_capas} capas de {dz:.4f} mm; las {args.medias} vueltas del "
              f"medio van de {an0:.2f} a {an1:.2f} mm", flush=True)
        if an0 < 0.8 or an1 > 2 * 0.8:
            print(f"  AVISO: ese ancho se sale de lo que coloca una boquilla de "
                  f"0.8 (0.80..1.60). Probá otro --medias.")
    else:
        pasos = como_vaso(riel, altura, base, args.segmentos, args.capas_base,
                          args.entrada, args.separacion_por_angulo)
    print(f"  {len(pasos)} pasos", flush=True)

    for v in velocidades:
        p = perfil_de(v)
        tope = args.caudal_max if args.caudal_max else m["caudal"]
        # El freno mira el TRAMO GORDO, no el típico. Ver `velocidad.py`.
        pico = caudal_pico(pasos, v)
        if tope and pico and pico > tope:
            v_ok = velocidad_para(pasos, tope)
            print(f"    {v} mm/min daria {pico:.1f} mm3/s en el tramo gordo, por "
                  f"encima de {tope:.0f} ({args.material}): se baja a "
                  f"{v_ok:.0f} mm/min", flush=True)
            v = int(v_ok)
            p = perfil_de(v)
        q = caudal(pasos, v)
        emitir = [fc.Printer(print_speed=p.velocidad_impresion,
                             travel_speed=p.velocidad_viaje)
                  if isinstance(x, fc.Printer) else x for x in pasos]
        # Después del reemplazo, o la comprensión de arriba pisa cada `Printer`.
        if args.velocidad_voladizo:
            emitir, est = modular_por_voladizo(emitir, p.centro, p.ancho,
                                               v, args.velocidad_voladizo)
            if est:
                print(f"    voladizo: peor {100*est['peor_frac']:.0f}% del cordón colgando; "
                      f"{100*est['frac_lentos']:.0f}% de los puntos frenados, mínimo "
                  f"{est['v_min']:.0f} mm/min; "
                      f"{est['cambios']} cambios de F; "
                      f"x{est['minutos_con']/est['minutos_sin']:.2f} de tiempo")
        base = (f"{args.carpeta}/{args.nombre}" if args.receta
                else f"{args.carpeta}/{args.nombre}_v{v}")
        ruta = guardar_gcode(a_gcode(emitir, p), base)
        if args.receta and not args.sin_receta:
            guardar_receta(base, sys.argv, "gen_tuerca.py", descripciones={"": {
                "--ancho": "mm de cordón. En modo vaso ES el espesor de pared.",
                "--altura": "mm de tuerca.",
                "--velocidad": "mm/min. El freno de caudal la baja sola.",
            }})
        print(f"  {ruta.name:38s} {v:5d} mm/min  {q:5.1f} mm3/s")


if __name__ == "__main__":
    main()
