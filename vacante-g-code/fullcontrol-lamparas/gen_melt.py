#!/usr/bin/env python3
"""
La pantalla clásica JALADA: el mismo cuerpo de siempre, tirado de costado.

Dos cosas que se combinan, y cada una entra por su lado:

- la SILUETA es la de una pantalla de sobremesa de toda la vida —tronco de cono
  o campana, ancha abajo, aro arriba—, sacada de las proporciones de las fotos
  de referencia: la boca mide ~0.55 del pie y la altura ~0.70 del diámetro.
- la DEFORMACIÓN es `estructura.jalada`: el eje se corre y la sección no cambia.

**Lo que hace que se parezca a la referencia no es la ondulación, es que el
ancho no cambia.** Midiendo el jarrón del reel a la altura de cada
"estrangulamiento" y de cada "panza", el ancho da casi el mismo número: no hay
panzas. Es un cuerpo de sección constante al que se le corrió el centro, y el
bulto de un lado con la muesca del otro son la misma sección vista de perfil.
Por eso el objeto se sigue entendiendo y las proporciones se mantienen.

Las primeras versiones de este archivo modulaban el RADIO. Se ven al lado en
`output/melt/interpretaciones.png` y el defecto es doble: la pieza engorda y
adelgaza —±7.4 mm de ancho contra ±0.0 del modelo de ahora, medido con
`--solo-informe`— y, al agregarle al pliegue torsión y serpenteo propios para
compensar, la superficie se vuelve ruido en vez de la sincronía de la
referencia. El plisado no lleva movimiento propio: se mueve porque se mueve el
cuerpo abajo.

La pantalla se imprime **como se usa**, con el pie apoyado en la cama: al ser
más ancha abajo que arriba, la pared se cierra hacia adentro y no hay un solo
voladizo estructural. El tirón sí corre la pared, pero lo que decide es el
corrimiento POR CAPA contra el ancho del cordón, y `--solo-informe` lo mide:
con 0.4 de capa y 1.0 de cordón las tres variantes quedan por debajo de dos
tercios de un cordón, así que salen de una sola pasada, sin relleno.

Sale todo a `output/melt/`, aparte de `output/glitch/`: son dos familias
distintas —una corta la pared, la otra la dobla— y mezclarlas en una carpeta ya
hizo perder de vista cuál era cuál.

    python3 gen_melt.py                       # las tres variantes
    python3 gen_melt.py melt_b
    python3 gen_melt.py melt_b --p tiro=18 --p tirones=3
"""
import argparse
import math
import sys

sys.path.insert(0, ".")
from lamparas.comun import Perfil, a_gcode, guardar_gcode
from lamparas.estructura import jalada
from lamparas.recorrido import pasos_pantalla_glitch

# Proporciones medidas sobre las fotos de referencia (`image.png`,
# `image copy.png`): boca / pie = 0.55, alto / diámetro del pie = 0.70.
PIE, BOCA, ALTURA = 95.0, 52.0, 140.0


def cono(pie=PIE, boca=BOCA):
    """Tronco de cono recto: la pantalla `imperio`, la de la primera foto."""
    return lambda t: pie + (boca - pie) * t


def campana(pie=PIE, boca=BOCA, curva=1.6):
    """
    Perfil cóncavo: sube casi vertical del pie y se cierra arriba.

    `curva > 1` deja el vuelo abajo —la falda de la segunda foto—; `curva < 1`
    lo tira arriba y la pantalla se lee como una copa.
    """
    return lambda t: boca + (pie - boca) * (1.0 - t) ** curva


# El tirón de la referencia, medido sobre la foto: el centro se corre ~1/6 del
# radio. Es el único parámetro de la deformación grande, porque no hay panza —
# ver `estructura.jalada`. Lo que cambia entre variantes es la SILUETA y cuántas
# veces se va de un lado al otro, no la intensidad.
MELT = dict(tiro=12.0, nervios=70, nervio=1.8)

VARIANTES = {
    # Pantalla de sobremesa clásica, 190 de pie y 140 de alto. A esa proporción
    # el tirón alcanza a irse una vez y media de un lado al otro.
    "melt_a": dict(silueta=cono(95, 52), altura=140.0, tirones=1.5, **MELT),
    # Pantalla alta (164 de pie, 190 de alto). Al ser más esbelta entran dos
    # tirones y medio, que es la cadencia del jarrón: de las tres, la que más se
    # parece a la referencia.
    "melt_b": dict(silueta=cono(82, 50), altura=190.0, tirones=2.5, **MELT),
    # Campana: la silueta cóncava de la segunda foto, con el mismo tirón.
    "melt_c": dict(silueta=campana(95, 52), altura=160.0, tirones=2.0, **MELT),
}


def construir(nombre, **cambios):
    """(silueta, deformación, altura) de una variante, con los cambios pedidos."""
    if nombre not in VARIANTES:
        raise SystemExit(f"variante desconocida: {nombre!r}. Hay: {', '.join(VARIANTES)}")
    cfg = dict(VARIANTES[nombre]); cfg.update(cambios)
    silueta = cfg.pop("silueta"); altura = cfg.pop("altura")
    return silueta, jalada(silueta, **cfg), altura


def informe(silueta, deformacion, altura, perfil, n_a=720, n_t=None):
    """
    Lo que decide si la forma se puede imprimir, medido sobre el CAMPO.

    No reemplaza a `verificar_pieza.py` —ese mide el g-code ya emitido— pero
    contesta antes de generar 15 MB si la amplitud elegida se pasa de rosca.
    El número que importa es el corrimiento radial por capa contra el ancho del
    cordón: por encima de un cordón la vuelta no se apoya en la de abajo.
    """
    paso = perfil.altura_capa
    n_t = n_t or int(altura / paso)
    peor = 0.0
    r_max = 0.0
    desvio = 0.0
    r_ant = None
    for v in range(n_t + 1):
        t = v / n_t
        rs = [silueta(t) + deformacion(a * 2 * math.pi / n_a, t) for a in range(n_a)]
        r_max = max(r_max, max(rs))
        # El ANCHO de la pieza a esta altura: `r(θ) + r(θ+π)`, o sea de un
        # contorno al otro. Es la medición que separa un tirón de una panza: si
        # el centro se corre, el ancho no se entera; si el radio se modula, se
        # va con él. Lo que hay que comparar es contra el ancho de la silueta
        # lisa, no contra el de la vuelta anterior.
        n2 = n_a // 2
        ancho = max(rs[k] + rs[k + n2] for k in range(n2))
        desvio = max(desvio, abs(ancho - 2 * silueta(t)))
        if r_ant is not None:
            peor = max(peor, max(abs(b - a) for a, b in zip(r_ant, rs)))
        r_ant = rs
    return dict(radio_max=r_max, salto_capa=peor, cordon=perfil.ancho,
                fraccion=peor / perfil.ancho, desvio_ancho=desvio)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variante", nargs="?", default=None)
    ap.add_argument("--p", action="append", default=[], metavar="clave=valor",
                    help="cambia un parámetro de la deformación (repetible)")
    ap.add_argument("--segmentos", type=int, default=None,
                    help="puntos por vuelta. Por defecto, ~9 por pliegue")
    ap.add_argument("--solape", type=float, default=0.92)
    ap.add_argument("--nombre", default=None)
    ap.add_argument("--ancho", type=float, default=1.0,
                    help="ancho de cordón en mm. 1.0 es el de la familia melt: "
                         "es una PANTALLA y la pared tiene que dejar pasar luz. "
                         "1.8 —el de las piezas glitch— la deja opaca")
    ap.add_argument("--solo-informe", action="store_true")
    args = ap.parse_args()

    cambios = {}
    for kv in args.p:
        k, _, v = kv.partition("=")
        cambios[k] = float(v)

    perfil = Perfil(diametro_boquilla=0.8, altura_capa=0.4, ancho_linea=args.ancho,
                    velocidad_impresion=1200, temp_boquilla=245, temp_cama=80,
                    ventilador=0)

    for nombre in ([args.variante] if args.variante else list(VARIANTES)):
        silueta, deform, altura = construir(nombre, **cambios)
        cfg = dict(VARIANTES[nombre]); cfg.update(cambios)
        # ~9 puntos por pliegue: con menos, el triángulo del nervio sale
        # astillado y se ve como facetas y no como plisado.
        segs = args.segmentos or max(400, int(9 * cfg.get("nervios", 70)))
        inf = informe(silueta, deform, altura, perfil)
        print(f"{nombre}: radio max {inf['radio_max']:.1f} mm · "
              f"salto por capa {inf['salto_capa']:.2f} mm "
              f"({inf['fraccion']*100:.0f} % del cordón) · "
              f"ancho vs silueta lisa ±{inf['desvio_ancho']:.1f} mm · "
              f"{segs} segmentos")
        if args.solo_informe:
            continue
        pasos = pasos_pantalla_glitch(perfil, altura=altura, silueta=silueta,
                                      deformacion=deform, segmentos=segs,
                                      solape=args.solape)
        ruta = guardar_gcode(a_gcode(pasos, perfil), "melt/" + (args.nombre or nombre))
        print("  guardado:", ruta, f"({len(pasos)} pasos)")


if __name__ == "__main__":
    main()
