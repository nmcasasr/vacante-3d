"""
Mide el barreno roscado de la caperuza sobre `tuerca.stl` y lo contrasta con
`rosca.perfil_hembra`, que es `ENVOLVENTE + HOLGURA`.

Existe porque la tabla `ENVOLVENTE` estaba en el repo pero el script que la
midió no, y `SKILL.md` dice que cuando se mide algo nuevo se escribe el
verificador. Sin esto, dos cosas quedaban como suposición:

  - que la holgura de 0.20 mm se descontó en RADIO y no normal a la superficie;
  - que el barreno real es un helicoide de paso 13.5 y una entrada.

Las dos se comprueban acá: se trazan rayos desde el eje contra la malla, se
lleva cada impacto a fase de hélice y se busca el par (signo, origen de fase)
que minimiza el error contra la tabla. Si el modelo fuera falso, ningún origen
de fase daría un residuo chico.

    ./venv/bin/python medir_hembra.py
    ./venv/bin/python medir_hembra.py --listar     # qué cuerpos hay en el STL

Cómo se lee el rayo
-------------------
La caperuza es MACIZA (5–6.7 mm de pared en el cubo roscado), así que el primer
impacto de un rayo que sale del eje es la pared del barreno y no hace falta
ninguna heurística de normales. La altura de cada rayo se corre una fracción
irracional de milímetro para no caer nunca sobre un vértice de la malla: con z
justo sobre una cara horizontal, el conteo de cruces se vuelve arbitrario.
"""
import argparse
import collections
import math
import pathlib
import struct
import sys
import types
import importlib.util
import statistics

STL = pathlib.Path(__file__).resolve().parents[2] / "gcodes/reference/tuerca/tuerca.stl"

# Igual que `verificar_rosca.py`: un paquete `lamparas` de mentira con sólo
# `__path__`, para que el import relativo de rosca.py funcione sin ejecutar el
# `__init__` real (que arrastra fullcontrol).
_dir = pathlib.Path(__file__).resolve().parent / "lamparas"
if "lamparas" not in sys.modules:
    _pkg = types.ModuleType("lamparas")
    _pkg.__path__ = [str(_dir)]
    sys.modules["lamparas"] = _pkg
_spec = importlib.util.spec_from_file_location("lamparas.rosca", _dir / "rosca.py")
R = importlib.util.module_from_spec(_spec)
sys.modules["lamparas.rosca"] = R
_spec.loader.exec_module(R)


# --------------------------------------------------------------------- malla
def leer_stl(ruta):
    with open(ruta, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        data = f.read(n * 50)
    return [struct.unpack_from("<12f", data, i * 50) for i in range(n)]


def a_puntos(tris):
    return [tuple((v[3 + 3 * k], v[4 + 3 * k], v[5 + 3 * k]) for k in range(3))
            for v in tris]


def centrar(cuerpo):
    """
    Lleva un cuerpo a su propio eje y devuelve (triángulos centrados, cx, cy).

    El eje NO es el origen del archivo. `mariposa_v3_hembra.stl` viene en
    (0, 340) y en z 200..228 porque conserva la posición que tenía en el
    conjunto; un medidor que trace rayos desde el origen no le acierta a nada.
    Y tampoco sirve el centro del archivo entero: `tuerca.stl` trae cuerpos en
    X≈0 y en X≈400, y su centro común no es el eje de ninguno.

    Por eso el eje se saca POR CUERPO, de su caja envolvente en XY: una pieza de
    revolución es simétrica, así que ahí su caja sí está centrada.
    """
    xs = [q[0] for t in cuerpo for q in t]
    ys = [q[1] for t in cuerpo for q in t]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return [tuple((q[0] - cx, q[1] - cy, q[2]) for q in t) for t in cuerpo], cx, cy


def barrenos(ruta, r_max=60.0):
    """
    Todos los barrenos roscados de un STL, ya centrados en su eje y recortados
    a la zona del barreno.

    Devuelve una lista de (triángulos, cx, cy, z0, z1). La usan `medir_hembra`,
    `verificar_encastre --hembra` y `gen_tuerca`: una sola implementación,
    porque si cada uno buscara el barreno a su manera podrían estar midiendo
    cuerpos distintos.

    `r_max` recorta lo que está lejos del eje, y NO es una optimización: el rayo
    se queda con su PRIMER cruce, así que si el cuerpo trae además la pantalla
    —`tuerca.stl` la trae, hasta R 130— el barrido entra en alturas donde no hay
    barreno y ese primer cruce es el faldón. Medido así, los cuatro barrenos de
    `tuerca.stl` daban RMS 18 a 30 mm en vez de 0.02.

    Y el recorte va DESPUÉS de centrar. Aplicado sobre las coordenadas del
    archivo se lleva puesta cualquier pieza que no esté en el origen, como
    `mariposa_v3_hembra.stl`, que vive en (0, 340).
    """
    cs = sorted(cuerpos(a_puntos(leer_stl(ruta))), key=len, reverse=True)
    cresta = min(R.ENVOLVENTE) + R.HOLGURA
    out = []
    for c in cs:
        cent, cx, cy = centrar(c)
        cerca = [t for t in cent
                 if max(math.hypot(q[0], q[1]) for q in t) <= r_max]
        if not cerca:
            continue
        zs = [q[2] for t in cerca for q in t]
        rs = [math.hypot(q[0], q[1]) for t in cerca for q in t]
        if abs(min(rs) - cresta) < 0.3 and max(zs) - min(zs) > 2 * R.PASO:
            out.append((cerca, cx, cy, min(zs), max(zs)))
    return out


def cuerpos(tris):
    """Componentes conexas por vértice compartido."""
    par = list(range(len(tris)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    visto = {}
    for i, t in enumerate(tris):
        for p in t:
            key = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
            j = visto.get(key)
            if j is None:
                visto[key] = i
            else:
                a, b = find(i), find(j)
                if a != b:
                    par[a] = b
    comp = collections.defaultdict(list)
    for i in range(len(tris)):
        comp[find(i)].append(tris[i])
    return list(comp.values())


def indexar(tris, h=0.5):
    idx = collections.defaultdict(list)
    for t in tris:
        z0 = min(p[2] for p in t)
        z1 = max(p[2] for p in t)
        for b in range(int(math.floor(z0 / h)), int(math.floor(z1 / h)) + 1):
            idx[b].append(t)
    return idx, h


def cruces(idx, h, th, z):
    """Radios donde el rayo (desde el eje, ángulo th, altura z) cruza la malla."""
    dx, dy = math.cos(th), math.sin(th)
    out = []
    for t in idx.get(int(math.floor(z / h)), ()):
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            A, B = t[a], t[b]
            if (A[2] - z) * (B[2] - z) >= 0:
                continue
            u = (z - A[2]) / (B[2] - A[2])
            pts.append((A[0] + u * (B[0] - A[0]), A[1] + u * (B[1] - A[1])))
        if len(pts) != 2:
            continue
        (x0, y0), (x1, y1) = pts
        ex, ey = x1 - x0, y1 - y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        # P0 + v*E = s*D, resuelto por el cruz con D. El signo importa: con el
        # v negado el rayo devuelve un cruce de cada dos y la pieza parece abierta.
        v = (x0 * dy - y0 * dx) / den
        if not 0.0 <= v <= 1.0:
            continue
        s = (x0 + v * ex) * dx + (y0 + v * ey) * dy
        if s > 0:
            out.append(s)
    out.sort()
    return out


# ------------------------------------------------------------------- medición
EPS_Z = 0.0137          # para no caer nunca sobre una cara horizontal


def barrer(idx, h, z0, z1, n_ang=48, dz=0.05):
    m = []
    for ia in range(n_ang):
        th = 2 * math.pi * ia / n_ang
        z = z0 + EPS_Z
        while z < z1:
            c = cruces(idx, h, th, z)
            if c:
                m.append((th, z, c[0]))
            z += dz
    return m


def ajustar(muestras, n_fases=270):
    """Mejor (signo de hélice, origen de fase) contra `rosca.perfil_hembra`."""
    mejor = None
    for signo in (+1, -1):
        for k in range(n_fases):
            off = k * R.PASO / n_fases
            e = [r - R.perfil_hembra((z + signo * R.PASO * th / (2 * math.pi) + off) % R.PASO)
                 for th, z, r in muestras]
            rms = (sum(x * x for x in e) / len(e)) ** 0.5
            if mejor is None or rms < mejor[0]:
                mejor = (rms, signo, off)
    return mejor


# --------------------------------------------------- el barreno como tabla
N_FASE = 2700           # rejilla de fase: 0.005 mm de paso


def riel_de_tabla():
    """El barreno según `rosca.perfil_hembra`: la intención."""
    return [R.perfil_hembra(k * R.PASO / N_FASE) for k in range(N_FASE)]


def _completar(riel):
    """
    Rellena las casillas de fase sin muestra interpolando entre las vecinas
    MEDIDAS, en círculo.

    Antes caían a la tabla, y eso es lo peor que se puede hacer: la tabla y la
    pieza medida no comparten el origen de fase —cada tuerca arranca donde le
    tocó— así que el riel quedaba mitad de una curva y mitad de la otra, corrida
    8 mm. Daba RMS 1.46 mm y NO ENTRA en las cuatro piezas, con el mismo archivo
    que `medir_hembra.py` aprueba con 0.027.

    Interpolando entre medidas no hace falta conocer el origen: el barrido de δ
    ya absorbe cualquier corrimiento.
    """
    n = len(riel)
    llenas = [b for b in range(n) if riel[b] is not None]
    if not llenas:
        raise SystemExit("no se midió ninguna fase del barreno")
    out = list(riel)
    for b in range(n):
        if out[b] is not None:
            continue
        i = j = b
        while riel[i % n] is None:
            i -= 1
        while riel[j % n] is None:
            j += 1
        d0, d1 = b - i, j - b
        a, c = riel[i % n], riel[j % n]
        out[b] = a + (c - a) * d0 / (d0 + d1)
    return out, len(llenas) / n


def _contra_tabla(riel):
    """RMS contra `perfil_hembra` al mejor origen de fase. Sólo informativo: el
    veredicto no lo usa, pero si diera grande el riel medido no es esta rosca."""
    n = len(riel)
    tabla = riel_de_tabla()
    mejor = None
    for k in range(n):
        e = [riel[b] - tabla[(b + k) % n] for b in range(n)]
        rms = (sum(x * x for x in e) / n) ** 0.5
        if mejor is None or rms < mejor[0]:
            mejor = (rms, min(e), max(e), k * R.PASO / n)
    return mejor


def riel_de_stl(ruta, n_ang=72, dz=0.05):
    """
    El barreno de una TUERCA REAL, trazando rayos contra su malla.

    Es la referencia más fuerte que hay: no es la tabla ni una tuerca que
    hayamos fabricado, es la pieza que se va a enroscar. `medir_hembra.py` pone
    la maquinaria; acá sólo se queda con el radio mínimo por fase, que es el
    material que estorba.
    """
    enc = barrenos(ruta)
    if not enc:
        raise SystemExit(f"{ruta}: no encontré un barreno roscado")
    # Un solo sitio decide qué cuerpo es el barreno y dónde está su eje: si cada
    # script lo buscara a su manera podrían medir cuerpos distintos y nadie se
    # enteraría. `mariposa_v3_hembra.stl` viene en (0, 340) y en z 200..228.
    c, cx, cy, z0, z1 = enc[0]
    idx, h = indexar(c)
    riel = [None] * N_FASE
    for ia in range(n_ang):
        th = 2 * math.pi * ia / n_ang
        z = z0 + R.PASO / 2 + EPS_Z
        while z < z1 - R.PASO / 2:
            cr = cruces(idx, h, th, z)
            if cr:
                b = int(R.coordenada_hilo(th, z) / R.PASO * N_FASE) % N_FASE
                if riel[b] is None or cr[0] < riel[b]:
                    riel[b] = cr[0]
            z += dz
    riel, cobertura = _completar(riel)
    rms, e0, e1, fase = _contra_tabla(riel)
    return riel, cobertura, rms, e0, e1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stl", default=str(STL))
    ap.add_argument("--listar", action="store_true",
                    help="enumera los cuerpos cerca del eje y sale")
    ap.add_argument("--n-ang", type=int, default=48)
    ap.add_argument("--dz", type=float, default=0.05)
    args = ap.parse_args()

    print(f"leyendo {args.stl} ...", flush=True)
    encontrados = barrenos(args.stl)
    if args.listar:
        for c in sorted(cuerpos(a_puntos(leer_stl(args.stl))), key=len, reverse=True):
            cent, cx, cy = centrar(c)
            zs = [q[2] for t in cent for q in t]
            rs = [math.hypot(q[0], q[1]) for t in cent for q in t]
            print(f"  tris {len(c):7d}   eje ({cx:8.2f},{cy:8.2f})   "
                  f"z {min(zs):8.2f}..{max(zs):8.2f}   r {min(rs):6.2f}..{max(rs):6.2f}")
        return
    if not encontrados:
        print("no encontré ningún cuerpo con barreno roscado; probá --listar")
        return

    cresta = min(R.ENVOLVENTE) + R.HOLGURA
    ok_global = True
    for c, cx, cy, z0, z1 in encontrados:
        idx, h = indexar(c)
        # un margen de una vuelta en cada punta deja fuera chaflanes y bordes
        m = barrer(idx, h, z0 + R.PASO, z1 - R.PASO, args.n_ang, args.dz)
        if not m:
            continue
        rms, signo, off = ajustar(m)
        e = [r - R.perfil_hembra((z + signo * R.PASO * th / (2 * math.pi) + off) % R.PASO)
             for th, z, r in m]
        vueltas = (z1 - z0) / R.PASO
        print(f"\n--- barreno en el eje ({cx:.2f},{cy:.2f}), z {z0:.1f}..{z1:.1f} "
              f"({vueltas:.1f} vueltas), {len(m)} muestras")
        print(f"    hélice     : paso {R.PASO} mm, sentido {'igual' if signo < 0 else 'OPUESTO'} "
              f"al del macho; origen de fase {off:.2f} mm")
        print(f"    cresta/fondo: medido {min(r[2] for r in m):.3f} / {max(r[2] for r in m):.3f}  "
              f"tabla {cresta:.3f} / {max(R.ENVOLVENTE) + R.HOLGURA:.3f}")
        print(f"    residuo    : RMS {rms:.4f} mm   media {statistics.mean(e):+.4f}   "
              f"peor {max(map(abs, e)):.4f}")
        # 0.10 mm es el orden del teselado del STL: el propio barreno liso, que
        # es un cilindro exacto, ya devuelve picos de esa magnitud entre muestras.
        veredicto = rms <= 0.05 and max(map(abs, e)) <= 0.15
        ok_global &= veredicto
        print(f"    {'OK: perfil_hembra reproduce el barreno medido' if veredicto else 'NO COINCIDE'}")

    print()
    if not ok_global:
        sys.exit(1)


if __name__ == "__main__":
    main()
