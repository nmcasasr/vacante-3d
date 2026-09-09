"""
¿Entra el macho IMPRESO en la tuerca? Se mide sobre el g-code, no sobre la
función de radio.

    ./venv/bin/python verificar_encastre.py output/rosca/cupon_v2400.gcode
    ./venv/bin/python verificar_encastre.py output/rosca/*_v2400.gcode

`verificar_rosca.py` valida la `FuncionRadio`, que es la intención. Entre esa
función y el plástico se meten tres cosas que sólo existen en el g-code:

  - el medio cordón de compensación (`ancho_cordon`), que puede estar mal puesto
    o puesto dos veces;
  - el redondeo del paso fijo, que corre las vueltas respecto de las que se
    verificaron;
  - los anillos de base, que no tienen rosca y sin embargo son pared.

Así que esto lee los puntos que realmente se van a imprimir, les suma medio
cordón para llegar a la CARA exterior del hilo, y busca si existe alguna
posición axial en la que esa cara entre entera dentro del barreno.

El juego axial es el resultado, no un parámetro
-----------------------------------------------
Enroscar es elegir una fase: el macho se puede subir o bajar dentro del riel.
Por eso no se compara `macho(d)` contra `hembra(d)` a fase fija —eso mide el
dibujo, no el encastre— sino que se barre el corrimiento axial δ y se busca el
que deja más holgura. El ANCHO del intervalo de δ que sigue entrando es el juego
axial de la unión: cuánto cabecea la lámpara una vez enroscada.

Un macho que entra con mucha holgura no es mejor: es una rosca floja. Los dos
números se leen juntos.
"""
import argparse
import glob
import math
import pathlib
import re
import sys
import types
import importlib.util

_dir = pathlib.Path(__file__).resolve().parent / "lamparas"
if "lamparas" not in sys.modules:
    _pkg = types.ModuleType("lamparas")
    _pkg.__path__ = [str(_dir)]
    sys.modules["lamparas"] = _pkg
_spec = importlib.util.spec_from_file_location("lamparas.rosca", _dir / "rosca.py")
R = importlib.util.module_from_spec(_spec)
sys.modules["lamparas.rosca"] = R
_spec.loader.exec_module(R)

AREA_FILAMENTO = math.pi * (1.75 / 2) ** 2

_G1 = re.compile(r"^G[01](?=\s)", re.I)
_EJE = {c: re.compile(rf"\b{c}(-?\d*\.?\d+)") for c in "XYZE"}


def leer_extrusiones(ruta):
    """Puntos (x, y, z) con extrusión positiva, y el largo y área de cada tramo."""
    x = y = z = 0.0
    pts, largos, areas = [], [], []
    with open(ruta, errors="replace") as f:
        for linea in f:
            if not _G1.match(linea):
                continue
            linea = linea.split(";")[0]
            v = {}
            for c, rx in _EJE.items():
                m = rx.search(linea)
                if m:
                    v[c] = float(m.group(1))
            nx, ny, nz = v.get("X", x), v.get("Y", y), v.get("Z", z)
            e = v.get("E", 0.0)
            largo = math.dist((x, y, z), (nx, ny, nz))
            if e > 0 and largo > 1e-9:
                pts.append((nx, ny, nz))
                largos.append(largo)
                areas.append(e * AREA_FILAMENTO / largo)
            x, y, z = nx, ny, nz
    return pts, largos, areas


def _circulo(P):
    """Ajuste algebraico de círculo (Kåsa). Devuelve (cx, cy, radio)."""
    n = len(P)
    sx = sy = sxx = syy = sxy = sz = szx = szy = 0.0
    for x, y in P:
        z = x * x + y * y
        sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y
        sz += z; szx += z * x; szy += z * y
    A = [[2 * sxx, 2 * sxy, sx], [2 * sxy, 2 * syy, sy], [2 * sx, 2 * sy, n]]
    b = [szx, szy, sz]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(3):
            if r == i:
                continue
            f = A[r][i] / A[i][i]
            for c in range(i, 3):
                A[r][c] -= f * A[i][c]
            b[r] -= f * b[i]
    cx, cy, c = b[0] / A[0][0], b[1] / A[1][1], b[2] / A[2][2]
    return cx, cy, math.sqrt(max(0.0, c + cx * cx + cy * cy))


def centro(pts):
    """
    Eje de la pieza, ajustado sobre el NÚCLEO del hilo. Devuelve (cx, cy, radio
    del núcleo en la trayectoria).

    La caja envolvente no sirve, y el error no es chico: un patrón que depende
    del ángulo no llega al radio máximo en todas las direcciones, así que la
    caja sale corrida. Sobre `cuadros` la corre 0.99 mm — y ese milímetro
    aparece después como un exceso de 0.99 mm sobre la envolvente, o sea la
    pieza da NO ENTRA por un defecto del medidor. Pasó con los cuatro patrones
    de lienzo.

    El ajuste de círculo sobre todos los puntos tampoco alcanza: el hilo mueve
    el radio 2 mm y deja 0.05 mm de sesgo, del orden del veredicto.

    Lo que sí es un círculo exacto es el núcleo. `perfil_clasico` vale
    `R_NUCLEO` en toda una franja de fase, y ahí `rosca()` ni siquiera aplica el
    patrón (`if r > R_NUCLEO`), así que ese tramo existe en TODOS los ángulos y
    en todas las variantes, con el mismo radio. Se filtran los puntos más
    cercanos al eje y se les ajusta el círculo.
    """
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    r = 0.0
    for _ in range(3):
        rs = sorted(math.hypot(x - cx, y - cy) for x, y, _ in pts)
        lim = rs[len(rs) // 20] + 0.08
        sel = [(x, y) for x, y, _ in pts if math.hypot(x - cx, y - cy) < lim]
        if len(sel) < 16:
            break
        cx, cy, r = _circulo(sel)
    return cx, cy, r


# La medición del barreno vive en `medir_hembra`: es el módulo que mide, y así
# el generador y el verificador no pueden leer la misma tuerca distinto.
from medir_hembra import (N_FASE, riel_de_tabla, riel_de_stl,
                          _completar, _contra_tabla)

# Tolerancia de contención, la misma que `verificar_rosca.py` y por el mismo
# motivo: el hilo y el riel salen de dos tablas de 270 muestras interpoladas y
# evaluadas en puntos distintos, y entre muestra y muestra aparecen picos de
# unas micras que no son geometría. Con el corte en cero, el propio perfil que
# ya enrosca da NO ENTRA por 3 milésimas.
TOL = 0.01


def _perfil_maximo(muestras):
    """El radio más grande de la cara por cada casilla de fase.

    Para la holgura mínima sólo manda el peor punto de cada fase, así que
    colapsar 46 000 muestras en 2700 casillas no cambia el resultado y baja el
    barrido de 62 millones de evaluaciones a 7. La casilla mide 0.005 mm y el
    riel sube como mucho 0.76 mm/mm: el error que introduce es de 0.004 mm.
    """
    top = [None] * N_FASE
    quien = [None] * N_FASE
    for d, r, z, th in muestras:
        b = int(d / R.PASO * N_FASE) % N_FASE
        if top[b] is None or r > top[b]:
            top[b] = r
            quien[b] = (d, r, z, th)
    return top, quien


def riel_de_gcode(ruta, ancho, desde=1.0):
    """
    El barreno según el g-code de la TUERCA: lo que se va a imprimir de verdad.

    Cada punto del recorrido deja pared hacia AFUERA, así que la cara del
    barreno es `radio - ancho/2`, y de todas las vueltas que pasan por una fase
    manda la más interior: es la que estorba.

    Devuelve (riel, cobertura, desvío contra la tabla). El desvío importa: si el
    g-code de la hembra no reproduce `perfil_hembra`, el veredicto del macho
    contra la tabla y contra el archivo dejan de ser lo mismo.
    """
    pts, _, _ = leer_extrusiones(ruta)
    cuerpo = [p for p in pts if p[2] >= desde]
    cx, cy, _ = centro(cuerpo)
    riel = [None] * N_FASE
    for p in cuerpo:
        th = math.atan2(p[1] - cy, p[0] - cx)
        cara = math.hypot(p[0] - cx, p[1] - cy) - ancho / 2
        b = int(R.coordenada_hilo(th, p[2]) / R.PASO * N_FASE) % N_FASE
        if riel[b] is None or cara < riel[b]:
            riel[b] = cara
    riel, cobertura = _completar(riel)
    rms, e0, e1, fase = _contra_tabla(riel)
    return riel, cobertura, rms, e0, e1


def encastre(muestras, riel):
    """
    Para cada corrimiento axial δ, la holgura radial mínima de toda la pieza.
    Devuelve (mejor_delta, holgura, tabla de (δ, holgura), la casilla más justa).
    """
    top, quien = _perfil_maximo(muestras)
    ocupadas = [b for b in range(N_FASE) if top[b] is not None]
    tabla = []
    for k in range(N_FASE):
        peor, peor_b = None, None
        for b in ocupadas:
            h = riel[(b + k) % N_FASE] - top[b]
            if peor is None or h < peor:
                peor, peor_b = h, b
        tabla.append((k * R.PASO / N_FASE, peor, peor_b))
    mejor = max(tabla, key=lambda t: t[1])
    return mejor[0], mejor[1], tabla, quien[mejor[2]]


def juego_axial(tabla):
    """Ancho total de los δ que siguen entrando. Es un conjunto en un círculo de
    período PASO, así que se mide por conteo y no por extremos: si el intervalo
    cruza el origen, mirar min y max daría el período entero."""
    return sum(1 for _, h, _ in tabla if h >= -TOL) * R.PASO / len(tabla)


def asiento(tabla):
    """
    El δ en el que la pieza queda APOYADA, que no es el de máxima holgura.

    Una rosca no carga sobre la cresta del hilo sino sobre los flancos: enroscada
    a fondo, el macho se corre hasta que un flanco toca. Ese es el borde del
    intervalo de δ que entra, no su centro. Midiendo el contacto en el δ de
    máxima holgura da 0 % en todas las piezas —incluida la que ya enrosca— y
    parece que ninguna apoya.
    """
    validos = [(h, d) for d, h, _ in tabla if h >= -TOL]
    return min(validos)[1] if validos else None


def por_vuelta(cuerpo, cx, cy, areas, altura_capa=0.4, ancho_ref=1.2):
    """
    Lo que separa una vuelta de la siguiente, medido sobre el archivo.

    Devuelve (subida, peor Δradio, qué fracción de pares se pasa del cordón,
    ancho de cordón implícito). Salen
    de comparar cada punto con el que cae UNA VUELTA más arriba, no con el
    siguiente: en modo vaso la espiral sube unas micras por segmento y cualquier
    cuenta sobre puntos consecutivos devuelve ruido.

    Y el ancho implícito se saca dividiendo el área por la SEPARACIÓN sobre la
    superficie —`hypot(subida, Δradio)`— y no por la subida. Es la distinción
    que MAPA.md llama "las tres alturas que NO son la misma": con el flanco del
    hilo a 43°, dividir por la subida devuelve 1.64 mm de cordón para uno de
    1.20 y hace pensar que el archivo sobre-extruye un 36 %.

    El Δradio es el PEOR de la vuelta, no el de cada punto, porque así lo escala
    el generador: `generar_pieza` saca una separación por capa a partir del peor
    ángulo. Punto a punto el Δradio mediano es casi cero —el hilo entra y sale— y
    la cuenta vuelve a dar la subida pelada.

    Y para el ancho se usa el percentil 99 del Δradio de la vuelta, no su máximo,
    más el tope de `1.5 * altura_capa` que aplica `comun.py:1139`. Un patrón que
    prende y apaga el hilo —`interrumpida`— tiene saltos de 1.98 mm en los bordes
    de sector, que son 123 pares de 44 824: ahí el hilo empieza y termina por
    diseño. Con el máximo pelado la cuenta devuelve 0.32 mm de cordón para uno de
    1.20 y el archivo parece roto.

    Por eso el peor Δradio se sigue reportando —es real y hay que verlo— pero
    acompañado de CUÁNTOS pares lo tienen. Un 0 % y un 0.3 % dicen cosas
    distintas con el mismo máximo: uno es una pared que se abre en toda la
    vuelta, el otro es el canto donde termina un tramo de rosca.

    Aun así el número no cierra al milímetro: el generador usa la pendiente
    analítica del perfil y acá se mide una diferencia finita sobre una vuelta
    entera, que sale un par de grados más parada. Sobre el clásico cierra en
    1.21 para un cordón de 1.20, pero no hay que pedirle esa puntería. Sirve para cazar un `--ancho` groseramente equivocado
    —0.8 donde van 1.2 corre la cara 0.2 mm— no para calibrar nada.
    """
    dths = []
    for a, b in zip(cuerpo, cuerpo[1:]):
        dth = math.atan2(b[1] - cy, b[0] - cx) - math.atan2(a[1] - cy, a[0] - cx)
        dth = (dth + math.pi) % (2 * math.pi) - math.pi
        if abs(dth) > 1e-9:
            dths.append(abs(dth))
    if not dths:
        return float("nan"), float("nan"), float("nan")
    n = max(1, round(2 * math.pi / (sorted(dths)[len(dths) // 2])))

    subidas, saltos, sobre = [], [], 0
    por_giro = {}
    for i in range(len(cuerpo) - n):
        a, b = cuerpo[i], cuerpo[i + n]
        dz = b[2] - a[2]
        dr = math.hypot(b[0] - cx, b[1] - cy) - math.hypot(a[0] - cx, a[1] - cy)
        if dz <= 0:
            continue
        subidas.append(dz)
        saltos.append(dr)
        if dr > 0.5 * ancho_ref:
            sobre += 1
        g = por_giro.setdefault(i // n, [0.0, [], []])
        g[0] = max(g[0], dz)
        g[1].append(dr)
        if i < len(areas):
            g[2].append(areas[i])

    med = lambda v: sorted(v)[len(v) // 2] if v else float("nan")
    anchos = []
    for dz, drs, ars in por_giro.values():
        p99 = sorted(drs)[min(len(drs) - 1, int(0.99 * len(drs)))] if drs else 0.0
        sep = min(math.hypot(dz, p99), 1.5 * altura_capa)
        if sep > 1e-6 and ars:
            anchos.append(med(ars) / sep)
    salto = max(saltos) if saltos else float("nan")
    return med(subidas), salto, sobre / max(1, len(saltos)), med(anchos)


def verificar(ruta, ancho, apoyo=0.15, desde=2.0, riel=None,
              altura_capa=0.4, n_muestras=60000):
    pts, largos, areas = leer_extrusiones(ruta)
    if not pts:
        print(f"--- {pathlib.Path(ruta).name}: sin movimientos de extrusión")
        return False

    # Lo de abajo de todo son las líneas de purga de la plantilla, que cruzan la
    # cama en recta, y los anillos de base, que son pared pero no son rosca.
    par = [(p, a) for p, a in zip(pts, areas) if p[2] >= desde]
    if not par:
        print(f"--- {pathlib.Path(ruta).name}: nada por encima de z {desde}")
        return False
    cuerpo, area_cuerpo = zip(*par)
    cx, cy, r_nucleo = centro(cuerpo)

    paso = max(1, len(cuerpo) // n_muestras)
    muestras = []
    for p in cuerpo[::paso]:
        th = math.atan2(p[1] - cy, p[0] - cx)
        r = math.hypot(p[0] - cx, p[1] - cy) + ancho / 2      # cara exterior del hilo
        muestras.append((R.coordenada_hilo(th, p[2]), r, p[2], th))

    subida, salto, frac_salto, ancho_impl = por_vuelta(
        cuerpo, cx, cy, area_cuerpo, altura_capa, ancho)

    riel = riel if riel is not None else riel_de_tabla()
    delta, holgura, tabla, peor = encastre(muestras, riel)
    juego = juego_axial(tabla)

    # ¿cuánto del recorrido apoya contra el flanco, con la pieza asentada?
    d_asiento = asiento(tabla)
    frac = 0.0
    if d_asiento is not None:
        k = int(d_asiento / R.PASO * N_FASE) % N_FASE
        frac = sum(1 for d, r, _, _ in muestras
                   if riel[(int(d / R.PASO * N_FASE) + k) % N_FASE] - r <= apoyo) / len(muestras)

    # Lo que se dejó afuera no se esconde: si el anillo de base es más gordo que
    # el hilo, la tuerca no llega hasta abajo, y eso hay que verlo. Las líneas de
    # purga viven a la misma altura y cruzan la cama entera, así que se sacan por
    # radio: a 100 mm del eje no hay pieza.
    base = [p for p in pts if 0.2 <= p[2] < desde
            and math.hypot(p[0] - cx, p[1] - cy) < 100.0]
    r_base = max((math.hypot(p[0] - cx, p[1] - cy) + ancho / 2 for p in base),
                 default=float("nan"))

    r_max = max(r for _, r, _, _ in muestras)
    print(f"--- {pathlib.Path(ruta).name}")
    print(f"    eje        : ({cx:.3f}, {cy:.3f})  núcleo del recorrido R{r_nucleo:.3f} "
          f"+ medio cordón = R{r_nucleo + ancho / 2:.3f} contra R{R.R_NUCLEO:.2f}  "
          f"{'OK' if abs(r_nucleo + ancho / 2 - R.R_NUCLEO) < 0.05 else 'la compensación no cierra'}")
    print(f"    cordón     : declarado {ancho:.2f} mm, implícito {ancho_impl:.2f} mm  "
          f"{'OK' if abs(ancho_impl - ancho) < 0.15 * ancho else 'NO COINCIDE: revisá --ancho'}")
    print(f"    vuelta     : sube {subida:.3f} mm; peor corrimiento radial {salto:.3f} mm "
          f"-> solape {100 * (ancho - salto) / ancho:.0f} %, y lo tiene el "
          f"{100 * frac_salto:.2f} % de los pares")
    print(f"    rosca      : z {desde:.1f}..{max(p[2] for p in cuerpo):.1f} mm, "
          f"{len(muestras)} muestras, cara máxima R{r_max:.3f}")
    print(f"    encastre   : holgura radial mínima {holgura:+.3f} mm con el macho "
          f"corrido {delta:.2f} mm  {'ENTRA' if holgura >= -TOL else 'NO ENTRA'}")
    print(f"    juego axial: {juego:.2f} mm de {R.PASO} de paso "
          f"({100 * juego / R.PASO:.0f} % del paso)")
    print(f"    apoyo      : asentado a δ {d_asiento if d_asiento is None else round(d_asiento, 2)} mm, "
          f"{100 * frac:5.1f} % del recorrido a menos de {apoyo} mm del flanco  "
          f"{'OK' if frac > 0 else 'NO TOCA: rosca floja'}")
    print(f"    más justo  : z {peor[2]:.1f} mm, ángulo {math.degrees(peor[3]) % 360:.0f}°, "
          f"fase {peor[0]:.2f} mm; cara R{peor[1]:.3f} contra riel "
          f"R{riel[(int(peor[0] / R.PASO * N_FASE) + int(delta / R.PASO * N_FASE)) % N_FASE]:.3f}")
    print(f"    base       : {len(base)} extrusiones bajo z {desde:.1f}, cara máxima "
          f"R{r_base:.3f}  {'no estorba' if r_base <= max(riel) else 'la tuerca frena ahí'}")
    return holgura >= -TOL and frac > 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcode", nargs="+")
    ap.add_argument("--ancho", type=float, default=1.2,
                    help="mm de cordón, el mismo que le pasaste al generador")
    ap.add_argument("--apoyo", type=float, default=0.15,
                    help="mm por debajo del riel que todavía cuentan como apoyo")
    ap.add_argument("--ancho-hembra", type=float, default=None,
                    help="mm de cordón de la TUERCA, si difiere del macho. El "
                         "barreno se lee como `radio - ancho/2`, así que usar el "
                         "ancho del macho para leer la hembra corre el riel medio "
                         "cordón: con macho 1.0 contra hembra 1.2 la holgura daba "
                         "+0.308 en vez de +0.208.")
    ap.add_argument("--altura-capa", type=float, default=0.4,
                    help="mm: la `altura_capa` del Perfil con que se generó, no "
                         "la subida real. Sólo se usa para acotar la separación "
                         "igual que lo hace el generador.")
    ap.add_argument("--hembra", default=None,
                    help="g-code o STL de la TUERCA. Sin esto el riel sale de la tabla "
                         "`rosca.perfil_hembra`; con esto, del archivo que se va "
                         "a imprimir de verdad.")
    ap.add_argument("--desde", type=float, default=2.0,
                    help="mm: por debajo de esto están la purga y los anillos de "
                         "base, que son pared pero no son rosca. Se reportan aparte.")
    args = ap.parse_args()

    rutas = [r for patron in args.gcode for r in sorted(glob.glob(patron))]
    if not rutas:
        print("ningún archivo")
        sys.exit(2)
    riel = None
    if args.hembra:
        if args.hembra.lower().endswith(".stl"):
            riel, cob, rms, e0, e1 = riel_de_stl(args.hembra)
        else:
            riel, cob, rms, e0, e1 = riel_de_gcode(
                args.hembra, args.ancho_hembra or args.ancho)
        print(f"hembra: {pathlib.Path(args.hembra).name}  cresta R{min(riel):.3f}  "
              f"fondo R{max(riel):.3f}  paso {R.PASO} mm")
        print(f"        {100 * cob:.0f} % de las fases medidas (el resto interpolado entre ellas); "
              f"contra la tabla "
              f"RMS {rms:.4f} mm (de {e0:+.3f} a {e1:+.3f})  "
              f"{'OK' if rms < 0.05 else 'el g-code de la hembra NO reproduce la tabla'}\n")
    else:
        print(f"hembra: tabla `rosca.perfil_hembra`  cresta R{min(R.ENVOLVENTE) + R.HOLGURA:.3f}  "
              f"fondo R{max(R.ENVOLVENTE) + R.HOLGURA:.3f}  paso {R.PASO} mm\n")
    ok = True
    for r in rutas:
        ok &= verificar(r, args.ancho, args.apoyo, args.desde, riel, args.altura_capa)
        print()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
