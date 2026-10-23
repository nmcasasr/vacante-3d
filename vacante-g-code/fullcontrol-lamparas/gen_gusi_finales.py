"""
Las 12 piezas finales de Gusi —las que ofrece el creador de la web— en
`output/gusano-modular/finales/`, con su verificación, su tiempo y su
material, para sacar costos:

    2 tamaños (Ø150, Ø244) x 3 patrones (lisa, árbol, zigzag) x (módulo, tapa)

    python gen_gusi_finales.py                      # las 12, verif/, costos.csv
    python gen_gusi_finales.py 150 --patron arbol   # sólo esas
    python gen_gusi_finales.py --solo-costos        # rehace costos.csv sin generar

Todas son el gusano UNIVERSAL (`vacante-3d-gusanito`, rama `gusanito-grande`,
`gen_gusano_universal.py`): misma boca abajo (r 48.04) y mismo labio arriba
(r 46.24, 6 mm), hombro de 70°, holgura 0.6. El cuello es el del módulo Ø150
original del gusano modular (Ø96.1, labio Ø92.5): con el Ø60 fuera de la
línea, el cuello común ya no tiene que ser el del chiquito (Ø38.4), que en
los grandes quedaba como un cuello de botella. Así encastran en cualquier
orden. La silueta está COPIADA acá abajo (`gusano_universal`) porque en esta
rama `siluetas.gusano_modulo` todavía no tiene `cuello` ni `hombro`, y no se
toca: se registra con otro nombre al correr.

Los patrones salen de `bowls/puas.py` (el de esta rama, el más nuevo):

  - árbol: los grumos que cuelgan, al tresbolillo (`output/arbol/`): 3 lisas +
    1 con patrón, cantidad fija por fila, lisa a 16 mm/s, grumo a 8, punta a 3.
  - zigzag: los turupes del florero Kadzi (`output/florero-kadzi/`): 3 lisas +
    3 con patrón, ocupación 0.30, filo 0.34, el turupe crece en sus 3 vueltas,
    filas corridas media púa (el zigzag).

En los dos el patrón se apaga donde el radio baja de 48.3 mm (el cuello y el
labio, que quedan metidos en el módulo vecino) y donde el paso entre púas
baja de 1.5 mm (la cúpula de la tapa). Es la misma regla que dibuja la web
(`gusi-geometria.ts`, `RADIO_MIN` y `PASO_MIN`). Ver `finales/LEEME.md`.

Modo interno: `python gen_gusi_finales.py --bowls <args de lamparas.bowls>`
corre `python -m lamparas.bowls` con la silueta `gusano_universal`
registrada. Es lo que queda escrito en cada `.params.json` y en la cabecera de
cada g-code, así que cualquier pieza se rehace sola con ese comando.
"""
import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

# `verificar_tumbado.py` está sólo en la rama del gusano universal. Se usa de
# ahí, tal cual, sin copiarlo.
TUMBADO = os.path.normpath(os.path.join(
    AQUI, "..", "..", "..", "vacante-3d-gusanito", "vacante-g-code",
    "fullcontrol-lamparas", "verificar_tumbado.py"))

CARPETA = "gusano-modular/finales"


# --- la silueta ---------------------------------------------------------------

def gusano_universal(
    radio_max: float = 39.0,
    cintura: float = 0.6405,
    achatado: float = 0.7355,
    labio: float = 6.0,
    holgura: float = 0.6,
    pared: float = 1.2,
    tapa: int = 0,
    boca: float = 0.0,
    cuello: float = 0.0,
    hombro: float = 0.0,
):
    """
    `siluetas.gusano_modulo` de la rama `gusanito-grande`, copiada sin cambios
    (con `cuello` y `hombro`): UN lóbulo del gusanito que arranca en la cama
    abierto en el CUELLO, se abre hasta el ecuador y cierra hasta un LABIO
    vertical. `tapa=1` es el mismo lóbulo sin labio, cerrado en cúpula o
    abierto en `boca` (fracción de `radio_max`). Ver la original para el
    detalle de cada parámetro.

    Args:
        radio_max: radio del ecuador del lóbulo.
        cintura: radio del cuello como fracción de `radio_max` (si no hay `cuello`).
        achatado: semieje vertical del lóbulo como fracción de `radio_max`.
        labio: alto en mm del tramo vertical de arriba.
        holgura: juego radial entre la cara de afuera del labio y la de adentro de la boca.
        pared: ancho del cordón.
        tapa: 1 = cerrada en cúpula y sin labio.
        boca: con `tapa=1`, la cúpula queda abierta donde su radio baja a esta fracción.
        cuello: radio del cuello en mm (el común del gusano universal: 48.04).
        hombro: ángulo máximo de la pared desde la vertical; de ahí al cuello, un cono.
    """
    if not 0.0 < cintura < 1.0:
        raise ValueError("gusano_universal: 'cintura' va entre 0 y 1")
    R = radio_max
    b = achatado * R
    c = cuello / R if cuello else cintura
    if not 0.0 < c < 1.0:
        raise ValueError("gusano_universal: 'cuello' tiene que ser menor que 'radio_max'")
    rc = c * R
    rl = rc - pared - holgura
    if rl <= 0:
        raise ValueError("gusano_universal: el labio no entra")

    if hombro > 0:
        tg = math.tan(math.radians(hombro))
        k = b / R * tg
        us = k / math.sqrt(1.0 + k * k)
        rs = R / math.sqrt(1.0 + k * k)
    else:
        tg, us, rs = 1.0, 1.0, 0.0
    cono_abajo = rs > rc
    if cono_abajo:
        zc = (rs - rc) / tg + us * b
    else:
        zc = math.sqrt(1.0 - c * c) * b
    zt = zc + us * b

    def z_arriba(r: float) -> float:
        if r >= rs:
            return zc + math.sqrt(1.0 - (r / R) ** 2) * b
        return zt + (rs - r) / tg

    if tapa:
        altura = zc + math.sqrt(1.0 - boca * boca) * b
        paso = None
    else:
        zl = z_arriba(rl)
        altura = zl + labio
        paso = z_arriba(rc)

    def silueta(t: float) -> float:
        z = t * altura
        if not tapa and z >= zl:
            return rl
        if cono_abajo and z < zc - us * b:
            return rc + z * tg
        if not tapa and z > zt:
            return rs - (z - zt) * tg
        u = (z - zc) / b
        return R * math.sqrt(max(0.0, 1.0 - u * u))

    silueta.altura = altura
    silueta.paso = paso
    silueta.cuello = rc
    silueta.labio = None if tapa else rl
    silueta.boca = boca * R if tapa else 0.0
    silueta.quiebres = ([zc - us * b] if cono_abajo else []) + (
        [] if tapa else ([zt] if zt < zl else []) + [zl])
    return silueta


# --- la familia (igual que gen_gusano_universal.py) ---------------------------

TAMANOS = {150: 75.0, 244: 122.0}
_MEDIO = math.sqrt(1.0 - 0.6405 ** 2)
ACHATADO = round(150.0 / (0.12 + 1.0 + 2.0 * _MEDIO * 4) / 30.0, 4)   # 0.6884
# El cuello del Ø150 original (`gusano-modular/modulo_D150_92mm_labio6`):
# cintura 0.6405 de su radio. Antes era el del Ø60 (0.6405 x 30 = 19.215).
CUELLO = 0.6405 * 75.0                                                 # 48.04
HOMBRO = 70.0
HOLGURA = 0.6
LABIO = 6.0
TAPAS = {150: 0.2, 244: 0.2}

# La receta del gusano universal, sin la velocidad, las temperaturas ni los
# segmentos por vuelta, que dependen del patrón. La lisa va con 240 segmentos;
# las de patrón, con los que pida `puas` (10 muestras por púa, para que alguna
# caiga en la meseta): con 240 fijos un Ø60 con 54 grumos quedaba con 4.4
# puntos por grumo y el grumo salía según dónde cayera la rejilla.
RECETA = [
    "--sin-base", "--altura-capa", "0.8", "--ancho-linea", "1.2",
    "--material", "PETG", "--temp-cama", "70", "--segundos-vuelta", "25",
    "--ventilador", "0", "--ventilador-desde", "0.89", "--ventilador-desde-pct", "100",
    "--separacion", "marcha",
]

# --- los patrones -------------------------------------------------------------

# Donde no va patrón: radio < 48.3 (cuello y labio, metidos en el módulo
# vecino) y paso entre púas < 1.5 mm (se funden). La misma regla que la web.
RADIO_MIN = 48.3
PASO_MIN = 1.5

# Grumos (árbol) o turupes (zigzag) por vuelta, fijos en toda la pieza, y el
# largo del grumo del árbol. Arrancan en los números de la web
# (`gusi-geometria.ts`: CUENTA, ALTO_ARBOL, ALTO_KADZI; en la web el patrón
# se llamaba "kadzi" y ahora "zigzag"); lo que se cambió y
# por qué está en `finales/LEEME.md`.
CUENTA = {
    "arbol": {150: 135, 244: 144},
    "zigzag": {150: 192, 244: 192},
}
LARGO_ARBOL = {150: 7.0, 244: 9.0}

# Qué fracción del paso ocupa el grumo del árbol. En el cupón (72 púas en
# Ø80) el paso es 3.49 mm y 0.30 deja un grumo de 1.05 mm de ancho. Con los
# conteos de la web el Ø60 y el Ø150 quedan en ese mismo paso, pero el Ø244
# (144 grumos) queda en 5.32 mm, y a 0.30 el grumo mide 1.6: sus dos patas se
# separan y cada una vuela sola. Medido en el módulo Ø244:
#   144 grumos, ocupación 0.30   contacto 24.6 %   15.98 h  470 g
#   216 grumos, ocupación 0.30   contacto 19.9 %   19.46 h  541 g
#   144 grumos, ocupación 0.20   contacto 16.5 %   15.64 h  469 g   <- éste
# 0.20 x 5.32 = 1.06 mm: el mismo grumo que el cupón, sólo que más espaciado.
OCUPACION_ARBOL = {150: 0.30, 244: 0.20}
# El turupe del zigzag, en mm. La web dibuja 1.2 en los tres tamaños. Con 1.2
# el Ø60 da 1.44 % de contacto (IMPRIMIBLE, la referencia es 1.88), pero el
# Ø150 da 1.94 y el Ø244 2.4–2.5: NO IMPRIMIBLE. El turupe crece 0.4 mm por
# vuelta en sus tres vueltas; con paso de 2.5–4 mm las dos patas del turupe
# quedan separadas y cada una vuela sola. Medido en el módulo Ø150:
#   alto 1.2, 3 vueltas   1.94 %   NO IMPRIMIBLE
#   alto 0.9, 3 vueltas   0.94 %   IMPRIMIBLE   <- éste (la cadencia 3+3 queda)
#   alto 1.2, 4 vueltas   1.00 %   IMPRIMIBLE   (pero cambia la cadencia a 3+4)
ALTO_ZIGZAG = {150: 0.9, 244: 0.9}

# La rampa con que se prende y se apaga el patrón, en mm de alto. 0.8 como la
# lámpara puck del árbol: con los 5 mm por defecto las primeras y últimas filas
# salen cortas sin ninguna razón física.
SUAVE_MM = 0.8

# Desde qué altura (mm) va el ventilador en las piezas con patrón. Las dos
# primeras capas sin aire, como el arranque del gusano liso.
VENTILADOR_DESDE = 1.6


def silueta_de(d: int, tapa: int):
    return gusano_universal(radio_max=TAMANOS[d], achatado=ACHATADO, labio=LABIO,
                            holgura=HOLGURA, cuello=CUELLO, hombro=HOMBRO,
                            tapa=tapa, boca=TAPAS[d] if tapa else 0.0)


def radio_corte(patron: str, d: int) -> float:
    """El radio por debajo del cual no hay patrón: el mayor de los dos topes."""
    return max(RADIO_MIN, CUENTA[patron][d] * PASO_MIN / (2 * math.pi))


def ventana(s, r_corte: float):
    """
    El tramo [t0, t1] de la pieza donde el radio de la silueta es >= r_corte.

    La silueta sube desde el cuello hasta el ecuador y baja hasta el labio o la
    cúpula, así que ese tramo es uno solo.
    """
    n = 20000
    dentro = [i / n for i in range(n + 1) if s(i / n) >= r_corte]
    if not dentro:
        return None
    return dentro[0], dentro[-1]


def args_patron(patron: str, d: int, s) -> list:
    """Los `--p` y la velocidad de cada patrón, con la ventana de la pieza."""
    if patron == "lisa":
        return ["zigzag", "--p", "mascara=ninguna", "--p", "amplitud=0", "--p", "dientes=0",
                "--temp-primera-capa", "250", "--temperatura", "245", "--velocidad", "480",
                "--segmentos", "240"]
    v = ventana(s, radio_corte(patron, d))
    t0, t1 = v
    # El ventilador: el gusano liso va sin aire hasta el 89 % (la primera vuelta
    # es un solo cordón sobre la cama y tiene que agarrar). Los grumos y los
    # turupes se calibraron al 100 %, y `puas` sólo emite el ventilador cuando
    # CAMBIA: con el perfil en 100 lo emite una vez al arrancar, el
    # `--ventilador-en 0:0` lo apaga en la primera vuelta y el de 1.6 lo prende
    # para el resto. Con el perfil en 0 lo prendía y apagaba en cada punta.
    comun = ["puas", "--temp-primera-capa", "250", "--temperatura", "240",
             "--ventilador", "100", "--ventilador-en", "0:0",
             "--ventilador-en", f"{VENTILADOR_DESDE:g}:100",
             "--pendiente-silueta",
             # Sin la mezcla de las primeras capas, como la mini lámpara y la
             # puck del árbol: con la mezcla, la tapa Ø60 árbol dejaba un puente
             # de 33.7 mm en z 1.9 (allá era uno de 67 mm en z 2.1).
             "--capas-transicion", "0",
             "--p", f"puas={CUENTA[patron][d]}",
             "--p", f"desde={t0:.4f}", "--p", f"hasta={t1:.4f}",
             "--p", f"suave_mm={SUAVE_MM:g}",
             "--p", "mascara=ninguna",
             "--p", f"ocupacion={OCUPACION_ARBOL[d] if patron == 'arbol' else 0.30:.2f}",
             "--p", "banda_por_vuelta=1", "--p", "intercalar=1"]
    if patron == "arbol":
        # El cupón de velocidades del árbol, gajo 1 (la referencia), y la mini
        # lámpara y la puck: lo liso a 16 mm/s, el grumo a 8, la punta a 3, la
        # subida entera frenada. El grumo sale de una y se cuelga.
        return comun + ["--velocidad", "960",
                        "--p", f"amplitud={LARGO_ARBOL[d]:g}", "--p", "amplitud_fondo=0",
                        "--p", "crecer=0", "--p", "lisas=3", "--p", "con_patron=1",
                        "--p", "grumo_lento=0.5", "--p", "puente_lento=0.1875",
                        "--p", "lento_alcance=subida"]
    # zigzag: el florero Kadzi de grumo-crece (el cupón impreso, `largos_1.2a3.6mm`):
    # 3 + 3, el turupe crece en sus tres vueltas y apoya siempre, a 8 mm/s.
    return comun + ["--velocidad", "480",
                    "--p", f"amplitud={ALTO_ZIGZAG[d]:g}", "--p", "amplitud_fondo=0",
                    "--p", "filo=0.34", "--p", "crecer=1",
                    "--p", "lisas=3", "--p", "con_patron=3"]


def comando(patron: str, d: int, tipo: str) -> tuple:
    """(nombre, argumentos para `--bowls`) de una pieza."""
    tapa = 1 if tipo == "tapa" else 0
    s = silueta_de(d, tapa)
    nombre = f"{tipo}_D{d}_{patron}"
    a = args_patron(patron, d, s)
    # La receta va ANTES que lo del patrón: `--ventilador` y `--velocidad` del
    # patrón tienen que pisar los de la receta (argparse se queda con el último).
    args = [a[0], "--silueta", "gusano_universal",
            "--ps", f"tapa={tapa}", "--ps", f"labio={LABIO:g}",
            "--ps", f"holgura={HOLGURA:g}", "--ps", f"achatado={ACHATADO:.4f}",
            "--ps", f"boca={TAPAS[d] if tapa else 0:g}", "--ps", f"cuello={CUELLO:.3f}",
            "--ps", f"hombro={HOMBRO:g}",
            *RECETA, *a[1:],
            "--radio-max", f"{TAMANOS[d]:g}", "--altura", f"{s.altura:.3f}",
            "--nombre", f"{CARPETA}/{nombre}"]
    return nombre, args


# --- el modo interno: lamparas.bowls con la silueta registrada -----------------

def correr_bowls(argv: list) -> None:
    from lamparas.bowls import siluetas
    siluetas.SILUETAS["gusano_universal"] = gusano_universal
    from lamparas.bowls import __main__ as M
    from lamparas import comun

    propio = [os.path.basename(__file__), "--bowls", *argv]
    M.encabezado_receta = lambda _argv, _mod: comun.encabezado_receta(
        ["", *propio], "X").replace("; python -m X ", "; python ", 1)
    M.guardar_receta = (lambda nombre, _argv, _mod, *a, **k:
                        comun.guardar_receta(nombre, propio, os.path.basename(__file__), *a, **k))
    sys.argv = ["lamparas.bowls", *argv]
    M._cli()


# --- medir ---------------------------------------------------------------------

MOV = re.compile(r'([XYZEF])(-?\d*\.?\d+)')
PETG = 1.27                                   # g/cm³
AREA_FILAMENTO = math.pi * (1.75 / 2) ** 2    # mm²


def medir_gcode(ruta: str) -> dict:
    """
    Tiempo sobre el recorrido (largo / F de cada movimiento) y material. Es la
    misma cuenta que `gen_gusano_universal.medir_gcode`, que da 2.8 h para el
    módulo Ø180 del gusano modular; ahí se lee que lo real sale ~35 % más.
    """
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
        if "F" in d and "X" in d and e > 0 and not ln.rstrip().endswith("purga"):
            en_cuerpo = True
        if en_cuerpo and e > 0:
            seg += math.hypot(nx - x, ny - y) / (f / 60.0)
            e_total += e
        x, y = nx, ny
    return {"horas": seg / 3600.0, "mm_filamento": e_total,
            "gramos": e_total * AREA_FILAMENTO / 1000.0 * PETG}


def puntos(ruta: str) -> list:
    """
    (r, z) de cada punto extruido del cuerpo, con la pieza centrada en
    (128, 128). Arranca en la primera vuelta (z 0.8): lo de antes es la purga y
    el acercamiento.
    """
    x = y = z = 0.0
    out = []
    for ln in open(ruta):
        if not ln.startswith("G1"):
            continue
        d = dict(MOV.findall(ln.split(";")[0]))
        x, y, z = float(d.get("X", x)), float(d.get("Y", y)), float(d.get("Z", z))
        if "E" in d and float(d["E"]) > 0 and not ln.rstrip().endswith("purga"):
            if out or z <= Z0 + 0.01:
                out.append((math.hypot(x - 128.0, y - 128.0), z))
    return out


Z0 = 0.8          # la primera vuelta va a z 0.8 en el g-code; la silueta, en 0


def relieve(ruta: str, ruta_lisa: str) -> list:
    """
    (z de la silueta, r de la lisa, cuánto sale el punto por fuera de la lisa),
    punto por punto.

    Se compara contra el g-code de la LISA del mismo tamaño y no contra la
    silueta: en una pared a 70° un error de 0.1 mm en z son 0.27 mm de radio, y
    la marcha y el arranque corren la z de cada vuelta unas décimas respecto de
    la silueta. Con `--pendiente-silueta` la marcha mira la silueta lisa, así
    que la pieza con patrón sube EXACTAMENTE igual que la lisa (mismas z) y la
    lisa, que es una hélice, da su radio como función de z.
    """
    import bisect
    lisa = puntos(ruta_lisa)
    zs = [z for _, z in lisa]
    rs = [r for r, _ in lisa]

    def r_lisa(z):
        i = bisect.bisect_left(zs, z)
        if i <= 0:
            return rs[0]
        if i >= len(zs):
            return rs[-1]
        f = (z - zs[i - 1]) / (zs[i] - zs[i - 1]) if zs[i] > zs[i - 1] else 0.0
        return rs[i - 1] + f * (rs[i] - rs[i - 1])

    out = []
    for r, z in puntos(ruta):
        rl = r_lisa(z)
        out.append((z - Z0, rl, r - rl))
    return out


def encastre(ruta: str, ruta_lisa: str, s) -> dict:
    """
    Lo que se mide del encastre sobre el g-code, contra la lisa:

    - `relieve_boca`: cuánto sale el punto más afuera en los primeros 2 mm de
      la pieza (lo que se apoya sobre el hombro del de abajo);
    - `relieve_hombro`: ídem desde 2 mm por debajo del asiento hasta arriba
      (el hombro donde se apoya el de arriba, y el labio que entra en él);
    - `adentro`: el punto más metido respecto de la lisa en TODA la pieza
      (la cara de adentro, la que toca el labio, no tiene que cambiar);
    - dónde arranca y termina de verdad el patrón (relieve > 0.3 mm), en z y r,
      y cuánto queda entre el último grumo y el asiento.
    """
    rel = relieve(ruta, ruta_lisa)
    fuera = [p for p in rel if p[2] > 0.3]
    out = {
        "relieve_boca": max(p[2] for p in rel if p[0] <= 2.0),
        "adentro": min(p[2] for p in rel),
        "relieve_max": max(p[2] for p in rel),
    }
    if s.paso is not None:
        out["relieve_hombro"] = max(p[2] for p in rel if p[0] >= s.paso - 2.0)
    if fuera:
        out["patron_z"] = (min(p[0] for p in fuera), max(p[0] for p in fuera))
        out["patron_r_min"] = min(p[1] for p in fuera)
        if s.paso is not None:
            out["grumo_a_asiento"] = s.paso - out["patron_z"][1]
    return out


def separacion_apilado(gcodes: dict) -> list:
    """
    Con cada par apilado (cualquier módulo abajo, cualquier pieza arriba), la
    menor distancia VERTICAL entre un grumo o turupe de una pieza y el eje del
    cordón de la otra, en el radio de ese grumo. Por debajo de 0.8 (un cordón)
    se tocarían. Ignora el ángulo, así que es el peor caso: cada fila de grumos
    cuenta como un anillo entero.
    """
    def z_subiendo(s, r):
        """La menor z donde la silueta pasa por r (el lado de abajo)."""
        H = s.altura
        n = 4000
        for i in range(n + 1):
            if s(i / n) >= r:
                return H * i / n
        return None

    def z_bajando(s, r):
        """La mayor z (antes del labio) donde la silueta pasa por r."""
        H = s.altura
        n = 4000
        for i in range(n, -1, -1):
            if s(i / n) >= r:
                return H * i / n
        return None

    grumos = {}
    for (d, tipo, patron), ruta in gcodes.items():
        if patron == "lisa":
            continue
        lisa = gcodes[(d, tipo, "lisa")]
        grumos[(d, tipo, patron)] = [(p[0], p[1] + p[2]) for p in relieve(ruta, lisa) if p[2] > 0.3]

    filas = []
    for (d_ab, t_ab, p_ab), g_ab in grumos.items():
        if t_ab != "modulo":
            continue
        ab = silueta_de(d_ab, 0)
        for d_ar in TAMANOS:
            for t_ar in ("modulo", "tapa"):
                ar = silueta_de(d_ar, 1 if t_ar == "tapa" else 0)
                # grumos del de abajo cerca del asiento contra la base del de arriba
                peor = None
                for z, r in g_ab:
                    if z < ab.paso - 15:
                        continue
                    zu = z_subiendo(ar, r)
                    if zu is None:
                        continue
                    dz = ab.paso + zu - z
                    peor = dz if peor is None else min(peor, dz)
                filas.append((f"Ø{d_ab} {p_ab} abajo", f"{t_ar} Ø{d_ar} arriba", peor))
    for (d_ar, t_ar, p_ar), g_ar in grumos.items():
        s_ar = silueta_de(d_ar, 1 if t_ar == "tapa" else 0)
        for d_ab in TAMANOS:
            ab = silueta_de(d_ab, 0)
            peor = None
            for z, r in g_ar:
                if z > 15:
                    continue
                zb = z_bajando(ab, r)
                if zb is None:
                    continue
                dz = (ab.paso + z) - zb
                peor = dz if peor is None else min(peor, dz)
            filas.append((f"módulo Ø{d_ab} abajo", f"{t_ar} Ø{d_ar} {p_ar} arriba", peor))
    return filas


def verificar(gcode: str, patron: str) -> tuple:
    """Corre los verificadores, deja el texto en `verif/` y devuelve (veredicto, resumen)."""
    carpeta = os.path.join(AQUI, "output", CARPETA, "verif")
    os.makedirs(carpeta, exist_ok=True)
    py = sys.executable
    pieza = subprocess.run([py, "-B", "verificar_pieza.py", gcode],
                           capture_output=True, text=True, cwd=AQUI).stdout
    cont = subprocess.run([py, "-B", "verificar_continuidad.py", gcode],
                          capture_output=True, text=True, cwd=AQUI).stdout
    textos = [pieza, cont]
    if os.path.exists(TUMBADO):
        textos.append(subprocess.run([py, "-B", TUMBADO, gcode],
                                     capture_output=True, text=True, cwd=AQUI).stdout)
    if patron != "lisa":
        textos.append(subprocess.run([py, "-B", "verificar_intercalado.py", gcode, "-q"],
                                     capture_output=True, text=True, cwd=AQUI).stdout)
    base = os.path.basename(gcode).replace(".gcode", "")
    with open(os.path.join(carpeta, base + ".verif.txt"), "w") as fh:
        fh.write("\n".join(textos))
    m = re.findall(r"^\s*-> (\S+(?: IMPRIMIBLE)?)", pieza, re.M)
    return (m[-1] if m else "?"), pieza


def resumen_pieza(texto: str) -> dict:
    """Los números de `verificar_pieza` que van a la tabla (los del VEREDICTO)."""
    out = {}
    for clave, patron in (("linea_fina", r"línea fina[^:]*:\s*([\d.]+) %"),
                          ("contacto", r"contacto:\s*([\d.]+) %"),
                          ("puente", r"peor puente:\s*([\d.]+) mm"),
                          ("pisados", r"muestras pisadas \(\s*([\d.]+) %")):
        m = re.search(patron, texto)
        if m:
            out[clave] = float(m.group(1))
    return out


# --- costos --------------------------------------------------------------------

PRESETS = {
    "Gusanito": [(150, "modulo", "lisa")] * 4 + [(150, "tapa", "lisa")],
    "Árbol": [(244, "modulo", "arbol"), (150, "modulo", "arbol"), (150, "tapa", "arbol")],
    "Torre": [(244, "modulo", "zigzag"), (150, "modulo", "zigzag"), (244, "modulo", "zigzag"),
              (150, "modulo", "zigzag"), (150, "tapa", "zigzag")],
}
EXTRA_REAL = 1.35


def generar(nombre: str, args: list, out: str) -> None:
    print(f"== {nombre}", flush=True)
    r = subprocess.run([sys.executable, "-B", __file__, "--bowls", *args],
                       cwd=AQUI, capture_output=True, text=True)
    log = os.path.join(out, "verif", nombre + ".gen.txt")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w") as fh:
        fh.write(r.stdout + "\n" + r.stderr)
    if r.returncode:
        print(r.stderr[-2000:])
        raise SystemExit(f"falló {nombre}")


def medir(d: int, patron: str, tipo: str, out: str, verificar_tambien: bool) -> dict:
    nombre = f"{tipo}_D{d}_{patron}"
    gcode = os.path.join(out, nombre + ".gcode")
    lisa = os.path.join(out, f"{tipo}_D{d}_lisa.gcode")
    s = silueta_de(d, 1 if tipo == "tapa" else 0)
    m = medir_gcode(gcode)
    fila = {"tamano": d, "patron": patron, "tipo": tipo,
            "alto_mm": round(s.altura + Z0, 1), **m}
    if patron != "lisa":
        fila["cuenta"] = CUENTA[patron][d]
        fila["r_corte"] = round(radio_corte(patron, d), 2)
        fila["paso_ecuador"] = round(2 * math.pi * TAMANOS[d] / CUENTA[patron][d], 2)
        fila["largo"] = LARGO_ARBOL[d] if patron == "arbol" else ALTO_ZIGZAG[d]
        fila["encastre"] = encastre(gcode, lisa, s)
    if verificar_tambien:
        v, texto = verificar(gcode, patron)
        fila["veredicto_verificador"] = v
        fila.update(resumen_pieza(texto))
    print(f"   {nombre}: {m['horas']:.2f} h  {m['gramos']:.0f} g  "
          f"{fila.get('veredicto_verificador', '')}", flush=True)
    return fila


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--bowls":
        correr_bowls(sys.argv[2:])
        return
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tamanos", nargs="*", type=int, default=sorted(TAMANOS))
    p.add_argument("--patron", action="append", choices=["lisa", "arbol", "zigzag"])
    p.add_argument("--tipo", action="append", choices=["modulo", "tapa"])
    p.add_argument("--sin-verificar", action="store_true")
    p.add_argument("--solo-costos", action="store_true",
                   help="no genera ni mide: rehace costos.csv desde verif/mediciones.json")
    a = p.parse_args()
    # La lisa primero: es la referencia contra la que se mide el relieve.
    patrones = [x for x in ("lisa", "arbol", "zigzag") if x in (a.patron or ["lisa", "arbol", "zigzag"])]
    tipos = a.tipo or ["modulo", "tapa"]

    out = os.path.join(AQUI, "output", CARPETA)
    os.makedirs(os.path.join(out, "verif"), exist_ok=True)
    # Una medición por pieza (`verif/<pieza>.med.json`), para poder correr los
    # tamaños en paralelo sin que uno pise lo que escribió el otro.
    if not a.solo_costos:
        for d in a.tamanos:
            for patron in patrones:
                for tipo in tipos:
                    nombre, args = comando(patron, d, tipo)
                    generar(nombre, args, out)
                    fila = medir(d, patron, tipo, out, not a.sin_verificar)
                    with open(os.path.join(out, "verif", nombre + ".med.json"), "w") as fh:
                        json.dump(fila, fh, indent=1, ensure_ascii=False)
    med = {}
    for f in sorted(os.listdir(os.path.join(out, "verif"))):
        if f.endswith(".med.json"):
            med[f[:-len(".med.json")]] = json.load(open(os.path.join(out, "verif", f)))
    escribir_costos(med, out)


def veredicto(f: dict) -> str:
    """
    El veredicto que va a costos.csv: el de `verificar_pieza`, salvo el caso
    que el árbol ya documentó —el grumo que sale de una y se cuelga da NO
    IMPRIMIBLE por CONTACTO y sólo por eso (`output/arbol/LEEME.md`)—. Ahí se
    compara contra las piezas de árbol laminadas (12–21 % de contacto, puente
    de hasta 11.9 mm) y se dice cuál es el caso.
    """
    v = f.get("veredicto_verificador", "?")
    if v == "IMPRIMIBLE":
        return "IMPRIMIBLE"
    fina, cont, puente = f.get("linea_fina", 99), f.get("contacto", 99), f.get("puente", 99)
    if f["patron"] == "arbol" and fina < 0.26 and puente <= 12.0:
        if cont <= CONTACTO_ARBOL_MAX:
            return f"IMPRIMIBLE* (grumo colgando: contacto {cont:.1f} %, puente {puente:.1f} mm)"
        return (f"A PROBAR (contacto {cont:.1f} %, más que el árbol más colgado "
                f"laminado, {CONTACTO_ARBOL_MAX:.0f} %)")
    return f"NO IMPRIMIBLE (línea fina {fina:.2f} %, contacto {cont:.1f} %, puente {puente:.1f} mm)"


# El contacto más alto de las piezas de árbol laminadas (`3-mini-lampara/`,
# 18–21 %): el grumo de 9 mm colgando. Por encima de eso no hay referencia.
CONTACTO_ARBOL_MAX = 21.0


def escribir_costos(med: dict, out: str) -> None:
    filas = []
    for d in sorted(TAMANOS):
        for patron in ("lisa", "arbol", "zigzag"):
            for tipo in ("modulo", "tapa"):
                f = med.get(f"{tipo}_D{d}_{patron}")
                if f:
                    filas.append(f)
    with open(os.path.join(out, "costos.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["archivo", "tamano", "patron", "tipo", "alto_mm", "tiempo_h",
                    "tiempo_h_mas35", "gramos", "metros_filamento", "cuenta_por_vuelta",
                    "largo_mm", "veredicto"])
        for f in filas:
            w.writerow([f"{f['tipo']}_D{f['tamano']}_{f['patron']}.gcode", f["tamano"],
                        f["patron"], f["tipo"], f["alto_mm"], round(f["horas"], 2),
                        round(f["horas"] * EXTRA_REAL, 2), round(f["gramos"], 1),
                        round(f["mm_filamento"] / 1000.0, 2), f.get("cuenta", ""),
                        f.get("largo", ""), veredicto(f)])
    with open(os.path.join(out, "costos_presets.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["preset", "piezas", "tiempo_h", "tiempo_h_mas35", "gramos",
                    "metros_filamento", "alto_pila_mm"])
        for nombre, piezas in PRESETS.items():
            fs = [med.get(f"{t}_D{d}_{p}") for d, t, p in piezas]
            if not all(fs):
                continue
            h = sum(f["horas"] for f in fs)
            alto = sum(silueta_de(d, 0).paso for d, t, p in piezas[:-1]) + silueta_de(
                piezas[-1][0], 1).altura
            w.writerow([nombre, " + ".join(f"{t} Ø{d} {p}" for d, t, p in piezas),
                        round(h, 2), round(h * EXTRA_REAL, 2),
                        round(sum(f["gramos"] for f in fs), 1),
                        round(sum(f["mm_filamento"] for f in fs) / 1000.0, 2), round(alto)])
    # El apilado, si están las 12.
    rutas = {(d, t, p): os.path.join(out, f"{t}_D{d}_{p}.gcode")
             for d in TAMANOS for t in ("modulo", "tapa") for p in ("lisa", "arbol", "zigzag")}
    if all(os.path.exists(r) for r in rutas.values()):
        with open(os.path.join(out, "verif", "apilado.txt"), "w") as fh:
            fh.write("Menor distancia vertical entre un grumo/turupe y el eje del cordón de la\n"
                     "otra pieza, en el radio del grumo, con las dos apiladas. Peor caso: sin\n"
                     "ángulo (cada fila cuenta como anillo). Menos de 0.8 mm = se tocan.\n\n")
            for ab, ar, dz in separacion_apilado(rutas):
                fh.write(f"{ab:28s} {ar:30s} {'—' if dz is None else f'{dz:6.2f} mm'}\n")
    print(f"{out}/costos.csv")


if __name__ == "__main__":
    main()
