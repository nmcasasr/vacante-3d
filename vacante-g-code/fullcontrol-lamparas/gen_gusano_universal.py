"""
Genera el gusano UNIVERSAL en `output/gusano-universal/`: módulos de tres
tamaños —Ø60, Ø150 y Ø244— que se apilan en cualquier orden, porque todos
comparten la MISMA boca abajo y el MISMO labio arriba. Por tamaño, un módulo y
una tapa, con su verificación en `verif/`, y `perfiles.json`: los perfiles
exactos que dibuja el visor 3D de Vacante.

    python gen_gusano_universal.py                  # los tres tamaños
    python gen_gusano_universal.py 60 --holgura 0.4
    python gen_gusano_universal.py --solo-perfiles  # sólo perfiles.json

La geometría vive en `siluetas.gusano_modulo` (`cuello` y `hombro`). Lo que
decide este script es la familia:

  - el CUELLO común es el del Ø60, que es el más chico y manda: su cuello
    propio es `0.6405 x 30 = 19.2` (Ø38.4) y no puede ser más ancho sin
    cambiarle la cintura al gusanito;
  - la proporción del lóbulo es la del gusanito ORIGINAL de la Kadzi (5
    lóbulos en 150 mm, Ø60, `apoyo` 0.12), así que apilados los Ø60 dan
    exactamente ese gusanito, con su mismo paso de 31.7 mm;
  - el HOMBRO de 70°: el elipsoide de los grandes sigue igual hasta que su
    pared se tumba a 70° de la vertical, y de ahí baja recto al cuello. Ver
    `output/gusano-universal/LEEME.md` para lo que se midió antes de elegirlo.

Mismo encastre que el gusano modular: el labio del de abajo entra por la boca
del de arriba, y esa boca se apoya donde el hombro de abajo vuelve a pasar por
el radio del cuello. Como el cuello es el mismo para los tres, eso vale para
cualquier par.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
sys.path.insert(0, '.')
from lamparas.bowls.siluetas import gusano_modulo

# Radio del ecuador de cada tamaño, por su nombre (el diámetro).
TAMANOS = {60: 30.0, 150: 75.0, 244: 122.0}

# El gusanito de la Kadzi (`output/gusanito/gusanito.params.json`): Ø60,
# 5 lóbulos en 150 mm, cintura 0.6405, apoyo 0.12. Se recalcula con la misma
# cuenta que `siluetas.gusanito` en vez de copiar el número, para que si se
# cambia uno de esos cuatro valores no quede un 0.688 huérfano.
_MEDIO = math.sqrt(1.0 - 0.6405 ** 2)
# Redondeado a 4 decimales porque es lo que viaja por `--ps`: si el generador
# recibe 0.6884 y la altura se calculó con 0.68836, el lóbulo del g-code y el
# de `perfiles.json` difieren (poco: 5 centésimas en el Ø244, pero difieren).
ACHATADO = round(150.0 / (0.12 + 1.0 + 2.0 * _MEDIO * 4) / 30.0, 4)   # 0.6884
CUELLO = 0.6405 * 30.0                                                 # 19.215 mm

# El elipsoide se sigue hasta que su pared se tumba a 70° de la vertical; de
# ahí al cuello, recto. Medido sobre el g-code del Ø244 (ver el LEEME):
#   sin hombro   peor 84.0°, 21 mm de radio a más de 76° en la panza de abajo
#   hombro 76°   peor 76.0°, 175.5 mm de alto
#   hombro 70°   peor 70.0°, 182.7 mm               <- éste
#   hombro 60°   peor 60.0°, 204.1 mm, y los pisados del verificador de 6 a 19 %
#   hombro 45°   272 mm: no entra en la A1 (256)
# Al Ø60 no lo toca (su pared no pasa de 64°) y al Ø95 apenas: 3 mm de cono.
HOMBRO = 70.0

# La boca de cada tapa, como fracción de radio_max (0 = cerrada). Las tres
# llevan la proporción del módulo.
#   - Ø60: cerrada, 1.1 mm al aire en el ápice.
#   - Ø95: cerrada NO es confiable. Con la proporción del cuerpo da 12.1 mm al
#     aire (se descuelga a los 12) y estirándola baila sin orden: 0.77 da 8.2,
#     0.775 da 11.5, 0.78 da 8.4, 0.785 da 10.5 —depende de dónde cae la
#     última vuelta contra el ápice—. Abierta al 20 % (Ø19) no tiene nada al
#     aire y conserva la proporción del módulo.
#   - Ø244: abierta al 20 % (Ø49), como las grandes del gusano modular.
TAPAS = {60: 0.0, 150: 0.2, 244: 0.2}

RECETA = [
    "--p", "mascara=ninguna", "--p", "amplitud=0", "--p", "dientes=0",
    "--sin-base", "--altura-capa", "0.8", "--ancho-linea", "1.2",
    "--material", "PETG", "--temp-primera-capa", "250", "--temperatura", "245",
    "--temp-cama", "70", "--velocidad", "480", "--segundos-vuelta", "25",
    "--ventilador", "0", "--ventilador-desde", "0.89", "--ventilador-desde-pct", "100",
    "--separacion", "marcha", "--segmentos", "240",
]

# Cuántas muestras lleva cada perfil de `perfiles.json`.
MUESTRAS = 160

MOV = re.compile(r'([XYZEF])(-?\d*\.?\d+)')
PETG = 1.27                                   # g/cm³
AREA_FILAMENTO = math.pi * (1.75 / 2) ** 2    # mm²


def perfil(s, n: int = MUESTRAS) -> list:
    """
    El perfil `[z, r]` del eje del cordón, con `n` puntos repartidos por
    LONGITUD DE ARCO y no por altura.

    Por altura, el Ø244 sin hombro dejaba el arranque —donde el radio pasa de
    19 a 40 mm en los primeros 5 mm de z— con cuatro muestras: el visor lo
    habría dibujado como un escalón. Por arco cada muestra cubre el mismo
    trecho de pared, sea vertical u horizontal. Los quiebres (el arranque del
    labio, los extremos del cono) se agregan exactos, para que el dibujo no
    los redondee.
    """
    H = s.altura
    fina = 20000
    zs = [H * i / fina for i in range(fina + 1)]
    rs = [s(z / H) for z in zs]
    arco = [0.0]
    for i in range(fina):
        arco.append(arco[-1] + math.hypot(zs[i + 1] - zs[i], rs[i + 1] - rs[i]))
    total = arco[-1]
    out, j = [], 0
    for k in range(n):
        objetivo = total * k / (n - 1)
        while j < fina and arco[j + 1] < objetivo:
            j += 1
        tramo = arco[j + 1] - arco[j] if j < fina else 0.0
        f = 0.0 if tramo <= 0 else (objetivo - arco[j]) / tramo
        z = zs[j] + f * (zs[min(j + 1, fina)] - zs[j])
        out.append([round(z, 3), round(s(z / H), 3)])
    for zq in getattr(s, "quiebres", []):
        out.append([round(zq, 3), round(s(zq / H), 3)])
    out.sort()
    return out


def medir_gcode(ruta: str) -> dict:
    """Tiempo sobre el recorrido (largo / velocidad pedida) y material."""
    x = y = 0.0
    f = 1000.0
    seg = 0.0
    e_total = 0.0
    en_cuerpo = False
    for ln in open(ruta):
        if not ln.startswith("G1"):
            continue
        d = dict(MOV.findall(ln.split(";")[0]))
        if "F" in d:
            f = float(d["F"])
        nx, ny = float(d.get("X", x)), float(d.get("Y", y))
        e = float(d["E"]) if "E" in d else 0.0
        # La purga va a F1000 sobre 180 mm y no es la pieza; el cuerpo empieza
        # en la primera vuelta a la velocidad de la receta y no se interrumpe.
        if "F" in d and "X" in d and e > 0 and not ln.rstrip().endswith("purga"):
            en_cuerpo = True
        if en_cuerpo and e > 0:
            seg += math.hypot(nx - x, ny - y) / (f / 60.0)
            e_total += e
        x, y = nx, ny
    return {"horas": seg / 3600.0,
            "gramos": e_total * AREA_FILAMENTO / 1000.0 * PETG}


def verificar(gcode: str, carpeta: str) -> str:
    """Corre los dos verificadores y deja el texto en `verif/`. Devuelve el veredicto."""
    os.makedirs(os.path.join(carpeta, "verif"), exist_ok=True)
    # sin `check`: `verificar_pieza` sale con código distinto de 0 cuando la
    # pieza NO es imprimible, y eso es justamente lo que hay que dejar escrito.
    pieza = subprocess.run([sys.executable, "verificar_pieza.py", gcode],
                           capture_output=True, text=True).stdout
    cont = subprocess.run([sys.executable, "verificar_continuidad.py", gcode],
                          capture_output=True, text=True, check=True).stdout
    # El tumbado va aparte porque `verificar_pieza` da 0.00 % sin apoyo tanto
    # a 60° como a 84°: es el número con el que se eligió el hombro.
    tumbado = subprocess.run([sys.executable, "verificar_tumbado.py", gcode],
                             capture_output=True, text=True, check=True).stdout
    base = os.path.basename(gcode).replace(".gcode", "")
    with open(os.path.join(carpeta, "verif", base + ".verif.txt"), "w") as fh:
        fh.write(pieza + "\n" + cont + "\n" + tumbado)
    m = re.findall(r"^\s*-> (\S+)", pieza, re.M)
    return m[-1] if m else "?"


def juego_entre(abajo, arriba, pared: float = 1.2) -> float:
    """
    El juego más chico entre el labio de `abajo` y la boca de `arriba`, en mm
    radiales y de cara a cara, a lo largo de todo el tramo en que el labio
    queda adentro.

    Es la cuenta que dice si "cualquier orden" es cierto: el labio sube
    `altura - paso` por encima del apoyo, y en todo ese tramo la pared de
    adentro de la pieza de arriba tiene que quedar afuera de la de afuera del
    labio. Como todas arrancan en el mismo cuello y se abren hacia arriba, el
    mínimo cae en la boca y vale la holgura; si algún día una pieza arrancara
    cerrándose, acá se vería negativo.
    """
    sube = abajo.altura - abajo.paso
    peor = float("inf")
    for i in range(201):
        z = sube * i / 200
        peor = min(peor, (arriba(z / arriba.altura) - pared / 2)
                   - (abajo.labio + pared / 2))
    return peor


def dibujar_armado(perfiles: dict, ruta: str, pilas: list) -> None:
    """
    Corte de las piezas y de un par de pilas mezcladas, a escala, con los
    perfiles de `perfiles.json` —los mismos que dibuja el visor— y el detalle
    del encastre de los dos pares más dispares (Ø60 sobre Ø244 y al revés).
    """
    from PIL import Image, ImageDraw, ImageFont
    W, H, M = 2400, 1150, 30
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    # La fuente por defecto de PIL no trae la Ø ni los acentos: salen cajitas.
    try:
        fuente = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    except OSError:
        fuente = ImageFont.load_default(size=22)
    COLORES = {"60": (40, 40, 40), "150": (205, 85, 30), "244": (40, 110, 200)}

    def trazo(pts, x0, y0, esc, color, grosor=2, solo_derecha=False):
        for lado in ((1,) if solo_derecha else (-1, 1)):
            xy = [(x0 + lado * r * esc, y0 - z * esc) for z, r in pts]
            dr.line(xy, fill=color, width=grosor)

    # 1. las piezas sueltas, módulo arriba y tapa abajo, todas a la misma escala
    ancho_p = 760
    esc = (ancho_p - 2 * M) / sum(perfiles[k]["diametro"] + 20 for k in perfiles)
    x = M
    for k in sorted(perfiles, key=int):
        p = perfiles[k]
        cx = x + p["diametro"] / 2 * esc
        trazo(p["modulo"], cx, 80 + 190 * esc, esc, COLORES[k])
        trazo(p["tapa"], cx, H - M, esc, COLORES[k])
        dr.text((x, 40), f"Ø{k}", fill=COLORES[k], font=fuente)
        x += (p["diametro"] + 20) * esc
    dr.text((M, 8), "módulos (arriba) y tapas (abajo), misma escala", fill="black", font=fuente)

    # 2. las pilas
    x = ancho_p + M
    ancho_pila = (W - ancho_p - 600 - 2 * M) / len(pilas)
    for pila in pilas:
        alto = sum(perfiles[k]["paso"] for k in pila[:-1])
        alto += perfiles[pila[-1]]["altura_tapa"]
        e = min((H - 2 * M - 60) / alto, (ancho_pila - 40) / max(perfiles[k]["diametro"] for k in pila))
        cx = x + ancho_pila / 2
        z0 = 0.0
        for i, k in enumerate(pila):
            pts = perfiles[k]["tapa" if i == len(pila) - 1 else "modulo"]
            trazo([(z + z0, r) for z, r in pts], cx, H - M, e, COLORES[k])
            z0 += perfiles[k]["paso"]
        nombre = " + ".join(f"Ø{k}" for k in pila[:-1]) + f" + tapa Ø{pila[-1]}"
        dr.text((x, 8), nombre, fill="black", font=fuente)
        dr.text((x, 36), f"{alto:.0f} mm", fill="black", font=fuente)
        x += ancho_pila

    # 3. el encastre en detalle: el cordón con su ancho, 12 mm a cada lado del apoyo
    x0 = W - 600 + M
    e = 14.0
    for j, (abajo, arriba) in enumerate((("60", "244"), ("244", "60"))):
        pa, pb = perfiles[abajo], perfiles[arriba]
        cx = x0 + j * 290 - 230
        cy = H / 2 + 120
        ventana = lambda pts, dz: [(z + dz - pa["paso"], r) for z, r in pts
                                   if abs(z + dz - pa["paso"]) < 14 and r < 34]
        trazo(ventana(pa["modulo"], 0.0), cx, cy, e, COLORES[abajo], grosor=int(1.2 * e), solo_derecha=True)
        trazo(ventana(pb["modulo"], pa["paso"]), cx, cy, e, COLORES[arriba], grosor=int(1.2 * e), solo_derecha=True)
        dr.text((cx + 200, cy - 230), f"Ø{arriba}", fill=COLORES[arriba], font=fuente)
        dr.text((cx + 200, cy + 200), f"Ø{abajo}", fill=COLORES[abajo], font=fuente)
    dr.text((x0, 8), "encastre, cordón a escala (x14)", fill="black", font=fuente)
    im.save(ruta)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tamanos", nargs="*", type=int, default=sorted(TAMANOS),
                   help="por nombre: " + ", ".join(str(k) for k in sorted(TAMANOS)))
    p.add_argument("--cuello", type=float, default=CUELLO)
    p.add_argument("--hombro", type=float, default=HOMBRO)
    p.add_argument("--achatado", type=float, default=ACHATADO)
    p.add_argument("--holgura", type=float, default=0.6)
    p.add_argument("--labio", type=float, default=6.0)
    p.add_argument("--carpeta", default="gusano-universal",
                   help="dentro de output/; para probar alternativas sin pisar la buena")
    p.add_argument("--solo-perfiles", action="store_true")
    p.add_argument("--sin-verificar", action="store_true")
    a = p.parse_args()

    carpeta = os.path.join("output", a.carpeta)
    os.makedirs(carpeta, exist_ok=True)
    ruta_perfiles = os.path.join(carpeta, "perfiles.json")
    try:
        perfiles = json.load(open(ruta_perfiles))
    except (OSError, ValueError):
        perfiles = {}
    # Sólo los tamaños vigentes: si uno sale de TAMANOS (pasó con el Ø95,
    # reemplazado por el Ø150) no tiene que quedar colgado en el contrato.
    perfiles = {k: v for k, v in perfiles.items() if int(k) in TAMANOS}

    filas = []
    for d in a.tamanos:
        R = TAMANOS[d]
        boca = TAPAS[d]
        comun = dict(radio_max=R, labio=a.labio, holgura=a.holgura,
                     cuello=a.cuello, hombro=a.hombro)
        mod = gusano_modulo(achatado=a.achatado, tapa=0, **comun)
        tap = gusano_modulo(achatado=a.achatado, tapa=1, boca=boca, **comun)
        perfiles[str(d)] = {
            "diametro": d,
            "paso": round(mod.paso, 3),
            "cuello": round(mod.cuello, 3),
            "labio": round(mod.labio, 3),
            "altura_modulo": round(mod.altura, 3),
            "altura_tapa": round(tap.altura, 3),
            "boca_tapa": round(tap.boca, 3),
            "modulo": perfil(mod),
            "tapa": perfil(tap),
        }
        if a.solo_perfiles:
            continue
        for nombre, s, tapa, ach, bo in (("modulo", mod, 0, a.achatado, 0.0),
                                         ("tapa", tap, 1, a.achatado, boca)):
            archivo = (f"{nombre}_D{d}_{s.altura:.0f}mm"
                       + (f"_boca{2 * R * bo:.0f}" if bo else ""))
            cmd = [sys.executable, "-m", "lamparas.bowls", "zigzag",
                   "--silueta", "gusano_modulo",
                   "--ps", f"tapa={tapa}", "--ps", f"labio={a.labio:g}",
                   "--ps", f"holgura={a.holgura:g}", "--ps", f"achatado={ach:.4f}",
                   "--ps", f"boca={bo:g}", "--ps", f"cuello={a.cuello:.3f}",
                   "--ps", f"hombro={a.hombro:g}",
                   *RECETA,
                   "--radio-max", f"{R:g}", "--altura", f"{s.altura:.3f}",
                   "--nombre", f"{a.carpeta}/{archivo}"]
            subprocess.run(cmd, check=True, capture_output=True)
            gcode = os.path.join(carpeta, archivo + ".gcode")
            m = medir_gcode(gcode)
            v = "—" if a.sin_verificar else verificar(gcode, carpeta)
            filas.append((archivo, s.altura, m["horas"], m["gramos"], v))

    with open(ruta_perfiles, "w") as fh:
        json.dump(perfiles, fh, indent=1)
    print(f"{ruta_perfiles}: {', '.join(sorted(perfiles, key=int))}")

    # Cada par posible, con las piezas recién calculadas (no las del json, que
    # pueden traer tamaños de otra corrida).
    todas = {d: (gusano_modulo(radio_max=TAMANOS[d], achatado=a.achatado, labio=a.labio,
                               holgura=a.holgura, cuello=a.cuello, hombro=a.hombro),
                 gusano_modulo(radio_max=TAMANOS[d], achatado=a.achatado, tapa=1,
                               boca=TAPAS[d], labio=a.labio, holgura=a.holgura,
                               cuello=a.cuello, hombro=a.hombro))
             for d in sorted(TAMANOS)}
    print("juego labio-boca, de cara a cara (filas: el de abajo; columnas: el de arriba)")
    print("        " + "".join(f"  Ø{d:<5}tapa  " for d in todas))
    for d, (mod, _) in todas.items():
        celdas = "".join(f"{juego_entre(mod, m):6.2f}{juego_entre(mod, t):6.2f}  "
                         for m, t in todas.values())
        print(f"  Ø{d:<4} {celdas}")

    if set(perfiles) >= {str(d) for d in TAMANOS}:
        dibujar_armado(perfiles, os.path.join(carpeta, "armado.png"),
                       [["244", "150", "60", "60"], ["60", "150", "244"]])
    for archivo, h, horas, gramos, v in filas:
        print(f"  {archivo:28s} {h:6.1f} mm  {horas:4.1f} h  {gramos:5.0f} g  {v}")


if __name__ == "__main__":
    main()
