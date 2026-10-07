"""
Genera el gusano modular en `output/gusano-modular/`: por cada diámetro, un
MÓDULO (un lóbulo con labio, se imprimen los que hagan falta y se apilan) y
una TAPA (el mismo lóbulo cerrado en cúpula).

    python gen_gusano_modular.py                 # Ø58, Ø78 y Ø95
    python gen_gusano_modular.py 120 150 180     # los grandes
    python gen_gusano_modular.py 78 --holgura 0.4
    python gen_gusano_modular.py --labio 10 --solo-modulos

La geometría vive en `siluetas.gusano_modulo`. Este script sólo le pide al
generador la altura que la silueta dice que tiene —si no, la estira y el
encastre deja de coincidir— y usa la misma receta que el gusanito grande.
"""
import argparse
import subprocess
import sys
sys.path.insert(0, '.')
from lamparas.bowls.siluetas import gusano_modulo

RECETA = [
    "--p", "mascara=ninguna", "--p", "amplitud=0", "--p", "dientes=0",
    "--sin-base", "--altura-capa", "0.8", "--ancho-linea", "1.2",
    "--material", "PETG", "--temp-primera-capa", "250", "--temperatura", "245",
    "--temp-cama", "70", "--velocidad", "480", "--segundos-vuelta", "25",
    "--ventilador", "0", "--ventilador-desde", "0.89", "--ventilador-desde-pct", "100",
    "--separacion", "marcha", "--segmentos", "240",
]

# Las tapas de cada diámetro, como (achatado, boca). Sin entrada: una sola,
# con la proporción del cuerpo y cerrada.
#
# La cúpula cerrada deja un tramo al aire en el ápice que crece con el radio
# (se descuelga a los 12 mm):
#   - Ø95: 12.6 mm. Estirándola un 9 % (0.80) baja a 7.4. No es monótono
#     —0.76 da 11.6, 0.78 10.2, 0.84 9.8—: depende de dónde cae la última
#     vuelta contra el ápice.
#   - Ø120: cierra sólo si es una esfera redonda (1.0): 9.7 mm. La cabeza
#     queda más grande que los lóbulos, así que va también la que hace juego,
#     abierta.
#   - Ø150 y Ø180: no cierran ni redondas (17 y 23 mm). Abiertas con una boca
#     del 20 % del diámetro no tienen nada al aire, y con la proporción del
#     cuerpo.
TAPAS = {
    95: [(0.80, 0.0)],
    120: [(1.0, 0.0), (0.7355, 0.2)],
    150: [(0.7355, 0.2)],
    180: [(0.7355, 0.2)],
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("diametros", nargs="*", type=float, default=[58, 78, 95])
    p.add_argument("--holgura", type=float, default=0.6)
    p.add_argument("--labio", type=float, default=6.0)
    p.add_argument("--solo-modulos", action="store_true",
                   help="no rehacer las tapas: no llevan labio ni holgura")
    a = p.parse_args()

    for d in a.diametros:
        r = d / 2.0
        piezas = [("modulo", 0, 0.7355, 0.0)]
        if not a.solo_modulos:
            piezas += [("tapa", 1, ach, boca)
                       for ach, boca in TAPAS.get(d, [(0.7355, 0.0)])]
        for nombre, tapa, ach, boca in piezas:
            s = gusano_modulo(radio_max=r, labio=a.labio, holgura=a.holgura,
                              tapa=tapa, achatado=ach, boca=boca)
            cmd = [sys.executable, "-m", "lamparas.bowls", "zigzag",
                   "--silueta", "gusano_modulo",
                   "--ps", f"tapa={tapa}", "--ps", f"labio={a.labio:g}",
                   "--ps", f"holgura={a.holgura:g}", "--ps", f"achatado={ach:g}",
                   "--ps", f"boca={boca:g}",
                   *RECETA,
                   "--radio-max", f"{r:g}", "--altura", f"{s.altura:.2f}",
                   "--nombre", f"gusano-modular/{nombre}_D{d:g}_{s.altura:.0f}mm"
                               + (f"_boca{d * boca:.0f}" if boca else "")
                               + ("" if tapa else f"_labio{a.labio:g}")]
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
