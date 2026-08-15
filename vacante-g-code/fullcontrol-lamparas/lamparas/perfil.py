"""
Silueta tomada de un DXF exportado de Fusion.

La idea: modelás el perfil donde te resulta cómodo y acá lo único que hace
falta es `radio(t)`. Todo lo demás —estructura, patrón, toques, color— sigue
funcionando encima sin enterarse, porque todos hablan el mismo idioma.

## Lo que un DXF de Fusion trae de verdad

No un perfil limpio: el documento entero. En `hongis.dxf` hay 19 capas de
sketch, 5 sólidos, ejes de construcción, cotas y secciones. Por eso esto no
pide "el archivo del perfil" sino que **lista lo que hay y elige**, con una
regla explicable: la curva más larga que recorra el mayor rango de altura. Lo
elegido se puede ver en ASCII antes de generar nada, y forzar con `--capa`.

Los sketches verticales quedan en el plano XZ: `Y = 0` y la altura viaja en Z.
Un perfil de revolución está de un solo lado del eje, pero un contorno completo
está de los dos; se dobla con `|x|` y las dos mitades caen una sobre otra, así
que sirve igual y no hay que preguntar cuál es.

## Las splines son splines

Un SPLINE de DXF es un NURBS: puntos de control, nudos y grado. El polígono de
control NO es la curva —en grado 5 se aleja varios milímetros— así que se
evalúa con De Boor. Con 40 puntos de control y grado 5, usar el polígono daba
un sombrero 4 mm más angosto de lo que es.
"""

import collections
import math
from typing import Callable, Dict, List, Optional, Tuple

# (angulo, t) no: una silueta es radio(t). El ángulo lo agrega el patrón.
Silueta = Callable[[float], float]


def _pares(ruta: str):
    """Un DXF es una lista de pares (código, valor), una línea cada uno."""
    with open(ruta, errors="ignore") as f:
        it = iter(f)
        for c in it:
            v = next(it, "")
            try:
                yield int(c.strip()), v.rstrip("\n").rstrip("\r")
            except ValueError:
                continue


def _entidades(ruta: str) -> List[dict]:
    P = list(_pares(ruta))
    try:
        i0 = next(i for i, (c, v) in enumerate(P) if c == 2 and v == "ENTITIES")
        i1 = next(i for i, (c, v) in enumerate(P[i0:], i0) if c == 0 and v == "ENDSEC")
    except StopIteration:
        raise ValueError(f"{ruta}: no encontré la sección ENTITIES")
    ent: List[dict] = []
    cur = None
    for c, v in P[i0 + 1:i1]:
        if c == 0:
            cur = {"tipo": v, "g": collections.defaultdict(list)}
            ent.append(cur)
        elif cur is not None:
            cur["g"][c].append(v)
    return ent


def _de_boor(grado: int, nudos: List[float], ctrl: List[Tuple[float, float]], u: float):
    """Un punto de la NURBS. Sin esto, el polígono de control miente."""
    n = len(ctrl) - 1
    k = grado
    while k < n and nudos[k + 1] <= u:
        k += 1
    d = [list(ctrl[j + k - grado]) for j in range(grado + 1)]
    for r in range(1, grado + 1):
        for j in range(grado, r - 1, -1):
            i = j + k - grado
            den = nudos[i + grado + 1 - r] - nudos[i]
            a = 0.0 if den == 0 else (u - nudos[i]) / den
            d[j] = [(1 - a) * d[j - 1][m] + a * d[j][m] for m in range(2)]
    return d[grado]


def _muestrear(e: dict, n: int = 400) -> List[Tuple[float, float]]:
    """La entidad como lista de puntos (x, z). Vacía si no es una curva."""
    g = e["g"]
    try:
        if e["tipo"] == "LINE":
            p = (float(g[10][0]), float(g[30][0]))
            q = (float(g[11][0]), float(g[31][0]))
            return [(p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n)
                    for i in range(n + 1)]
        if e["tipo"] == "SPLINE":
            grado = int(g[71][0])
            nudos = [float(v) for v in g[40]]
            ctrl = list(zip([float(v) for v in g[10]], [float(v) for v in g[30]]))
            if len(ctrl) < grado + 1 or len(nudos) < len(ctrl) + grado + 1:
                return []
            u0, u1 = nudos[grado], nudos[len(ctrl)]
            return [_de_boor(grado, nudos, ctrl, u0 + (u1 - u0) * i / n * 0.999999)
                    for i in range(n + 1)]
    except (KeyError, IndexError, ValueError):
        pass
    return []


class Curva:
    def __init__(self, idx: int, capa: str, tipo: str, pts: List[Tuple[float, float]]):
        self.idx, self.capa, self.tipo, self.pts = idx, capa, tipo, pts
        self.r = [abs(p[0]) for p in pts]
        self.z = [p[1] for p in pts]
        self.largo = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        self.alto = max(self.z) - min(self.z)

    @property
    def es_eje(self) -> bool:
        """Una línea pegada al eje es construcción, no silueta."""
        return max(self.r) < 1.0

    def __repr__(self):
        return (f"#{self.idx} {self.tipo} capa={self.capa!r} z {min(self.z):.1f}..{max(self.z):.1f} "
                f"r {min(self.r):.1f}..{max(self.r):.1f} largo {self.largo:.0f}")


def curvas(ruta: str) -> List[Curva]:
    out = []
    for i, e in enumerate(_entidades(ruta)):
        pts = _muestrear(e)
        if len(pts) < 3:
            continue
        capa = e["g"][8][0] if e["g"][8] else "?"
        c = Curva(i, capa, e["tipo"], pts)
        if not c.es_eje:
            out.append(c)
    return out


def curva_de_stl(ruta: str, muestras: int = 400) -> Curva:
    """
    La silueta de un STL de revolución, como si fuera una curva del DXF.

    Existe porque las formas nuevas llegan modeladas en 3D, no como sección 2D
    de Fusion, y `curvas()` sobre un STL devuelve cero: no hay entidades DXF que
    leer. Sin esto, `--perfil caperusa.stl` no tenía forma de entrar al
    generador.

    Toma el radio MÁXIMO de cada franja de altura, que es la envolvente
    exterior: si la malla es una cáscara con espesor, el contorno interior es el
    que modelaste y acá lo reemplaza un cordón — el mismo criterio que
    `radio_de` aplica a los DXF.

    Solo tiene sentido con formas de revolución. Si el modelo varía con el
    ángulo, esto lo promedia a su envolvente y se pierde el relieve; el aviso
    lo da `_cli`, que mide cuánto varía.
    """
    import struct
    d = open(ruta, "rb").read()
    if d[:5] == b"solid" and b"facet" in d[:2048]:
        raise ValueError(f"{ruta}: STL ASCII, solo se leen binarios")
    n = (len(d) - 84) // 50
    if n <= 0:
        raise ValueError(f"{ruta}: no parece un STL binario")
    zs, xs, ys = [], [], []
    tris = []
    for i in range(n):
        o = 84 + i * 50 + 12
        t = []
        for k in range(3):
            x, y, z = struct.unpack_from("<fff", d, o + k * 12)
            t.append((x, y, z))
            xs.append(x); ys.append(y); zs.append(z)
        tris.append(t)
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    z0, z1 = min(zs), max(zs)
    alto = (z1 - z0) or 1.0

    # Radio máximo por franja, midiendo sobre las ARISTAS y no sobre los
    # vértices.
    #
    # Con los vértices solos el perfil sale como un serrucho, y no por poco: la
    # caperuza daba 42 cambios de signo de pendiente en una campana que debería
    # tener uno, con escalones de hasta 2.3 mm de radio. En la pieza eso se ve
    # como anillos: la pared sube a los tirones y la celosía se comprime y se
    # abre en bandas.
    #
    # El motivo es que un triángulo que cruza diez franjas solo aporta dato en
    # las tres donde caen sus vértices. Las siete del medio se quedan con lo que
    # les deje otro triángulo, que en general es un radio menor — y como después
    # se toma el MÁXIMO, el resultado alterna entre "cayó un vértice ancho acá"
    # y "no cayó ninguno". Es un artefacto del muestreo, no la forma del modelo.
    #
    # Interpolando a lo largo de cada arista, toda franja que la arista cruza
    # recibe su radio real, y la envolvente sale continua.
    cajas: Dict[int, float] = {}

    def _marcar(k, r):
        if 0 <= k <= muestras and r > cajas.get(k, 0.0):
            cajas[k] = r

    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            ka = int((a[2] - z0) / alto * muestras)
            kb = int((b[2] - z0) / alto * muestras)
            _marcar(ka, math.hypot(a[0] - cx, a[1] - cy))
            _marcar(kb, math.hypot(b[0] - cx, b[1] - cy))
            if ka == kb:
                continue
            lo, hi = (ka, kb) if ka < kb else (kb, ka)
            for k in range(lo + 1, hi):
                z = z0 + alto * k / muestras
                f = (z - a[2]) / ((b[2] - a[2]) or 1.0)
                _marcar(k, math.hypot(a[0] + (b[0] - a[0]) * f - cx,
                                      a[1] + (b[1] - a[1]) * f - cy))

    ks = sorted(cajas)
    pts = [(cajas[k], z0 + alto * k / muestras) for k in ks]
    return Curva(0, f"stl:{ruta.split('/')[-1]}", "STL", pts)


def variacion_angular_stl(ruta: str, franjas: int = 20) -> float:
    """Cuánto varía el radio con el ángulo. Grande = NO es de revolución."""
    import struct
    d = open(ruta, "rb").read()
    n = (len(d) - 84) // 50
    verts = []
    for i in range(n):
        o = 84 + i * 50 + 12
        for k in range(3):
            verts.append(struct.unpack_from("<fff", d, o + k * 12))
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
    z0, z1 = min(zs), max(zs)
    peor = 0.0
    from collections import defaultdict
    b = defaultdict(list)
    for x, y, z in verts:
        b[int((z - z0) / (z1 - z0 or 1) * franjas)].append(math.hypot(x - cx, y - cy))
    for k, rr in b.items():
        if len(rr) > 10:
            peor = max(peor, max(rr) - min(rr))
    return peor


def circulos(ruta: str) -> List[Tuple[str, float, float]]:
    """(capa, z, radio) de cada CIRCLE. De acá salen los huecos."""
    out = []
    for e in _entidades(ruta):
        if e["tipo"] != "CIRCLE":
            continue
        g = e["g"]
        try:
            out.append((g[8][0] if g[8] else "?", float(g[30][0]), float(g[40][0])))
        except (KeyError, IndexError, ValueError):
            continue
    return sorted(out, key=lambda c: (c[1], c[2]))


def elegir(cs: List[Curva]) -> Curva:
    """
    La silueta es la curva más larga que recorra más altura.

    Regla explicable a propósito, y no un puntaje con pesos: cuando elige mal
    uno entiende por qué y pasa `--capa`. Las líneas horizontales de sección
    —que en `hongis.dxf` son quince— pueden ser largas pero no suben nada.
    """
    if not cs:
        raise ValueError("el DXF no tiene ninguna curva utilizable")
    return max(cs, key=lambda c: (c.alto, c.largo))


def radio_de(curva: Curva, desde_z: Optional[float] = None,
             hasta_z: Optional[float] = None, muestras: int = 2000, suavizado: int = 9) -> Tuple[Silueta, dict]:
    """
    Convierte una curva en `radio(t)`, con t=0 abajo y t=1 arriba del tramo.

    La tabla se SUAVIZA antes de devolverla, y no es cosmética: el paso vertical
    adaptativo la deriva, y la derivada de una escalera es ruido. Con el máximo
    por franja crudo, `dR/dt` saltaba 1740 entre muestras vecinas de una curva
    que es lisa, y el paso de cada vuelta salía entre 0.29 y 0.40 al azar — que
    es exactamente el "unas pegadas y otras separadas sin relación con la
    altura" que se ve en la pieza.

    Donde el contorno pasa dos veces por la misma altura —el envés de un
    sombrero, el interior de una cascarón— se queda con el radio MAYOR. En modo
    vaso la pared es la superficie: el contorno interior es el espesor que
    modelaste, y acá lo reemplaza un cordón.
    """
    z0 = min(curva.z) if desde_z is None else desde_z
    z1 = max(curva.z) if hasta_z is None else hasta_z
    if z1 - z0 < 1e-6:
        raise ValueError(f"el tramo z {z0}..{z1} no tiene altura")

    # Envolvente exterior: el radio máximo en cada franja de altura.
    cajas: Dict[int, float] = {}
    n = muestras
    for x, z in curva.pts:
        if z < z0 - 1e-9 or z > z1 + 1e-9:
            continue
        k = min(n, max(0, int((z - z0) / (z1 - z0) * n)))
        cajas[k] = max(cajas.get(k, 0.0), abs(x))
    if len(cajas) < 3:
        raise ValueError(f"la curva casi no pasa por z {z0:.1f}..{z1:.1f}")

    # Rellenar las franjas vacías por interpolación entre las vecinas con dato.
    ks = sorted(cajas)
    tabla = [0.0] * (n + 1)
    for i in range(n + 1):
        if i <= ks[0]:
            tabla[i] = cajas[ks[0]]
        elif i >= ks[-1]:
            tabla[i] = cajas[ks[-1]]
        else:
            import bisect
            j = bisect.bisect_left(ks, i)
            a, b = ks[j - 1], ks[j]
            f = (i - a) / (b - a)
            tabla[i] = cajas[a] + (cajas[b] - cajas[a]) * f

    # Suavizado por media móvil. Cada franja toma el MÁXIMO de los puntos que le
    # caen, y cuántos le caen depende de cómo quedó el muestreo de la spline:
    # unas reciben uno y otras tres, así que el máximo salta aunque la curva no.
    if suavizado > 1:
        h = suavizado // 2
        suave = []
        for i in range(n + 1):
            a, b = max(0, i - h), min(n, i + h)
            suave.append(sum(tabla[a:b + 1]) / (b - a + 1))
        tabla = suave

    def radio(t: float) -> float:
        x = min(1.0, max(0.0, t)) * n
        i = min(n - 1, int(x))
        return tabla[i] + (tabla[i + 1] - tabla[i]) * (x - i)

    info = {"z0": z0, "z1": z1, "alto": z1 - z0,
            "r_min": min(tabla), "r_max": max(tabla),
            "r_base": tabla[0], "r_boca": tabla[-1], "curva": repr(curva)}
    return radio, info


def voladizo(radio: Silueta, alto: float, altura_capa: float, ancho: float,
             muestras: int = 400) -> List[Tuple[float, float, float]]:
    """
    Dónde dos vueltas quedan separadas más que un cordón.

    Usa `comun.marcha_vertical`, la MISMA función que emite las vueltas, y mide
    la separación sobre la superficie `hypot(dz, dr)` — que es lo que decide si
    la vuelta nueva apoya sobre la anterior.

    Tener una marcha propia acá era la trampa: difería en el paso mínimo (0.02
    contra 0.05) y eso bastaba para que el aviso subestimara la peor separación
    casi a la mitad, justo en el ápice, que es donde importa.

    Devuelve (t, ángulo desde la vertical, separación en mm) de lo que no pega.
    """
    from .comun import marcha_vertical

    ts, zs = marcha_vertical(radio, alto, altura_capa)
    malos = []
    for i in range(len(ts) - 1):
        dz = zs[i + 1] - zs[i]
        dr = radio(ts[i + 1]) - radio(ts[i])
        sep = math.hypot(dz, dr)
        if sep > ancho:
            malos.append((ts[i], math.degrees(math.atan2(abs(dr), dz)), sep))
    return malos


def limitar(radio: Silueta, alto: float, altura_capa: float, ancho: float,
            muestras: int = 2000) -> Tuple[Silueta, dict]:
    """
    Recorta la pendiente del perfil para que ninguna vuelta se corra más que un
    cordón respecto de la anterior.

    Una cúpula SIEMPRE tiene una tangente horizontal en el ápice — es geometría,
    no un defecto del modelo. Ahí el radio se corre 8 mm por vuelta contra un
    cordón de 1.2, la vuelta nueva no apoya en nada y las líneas quedan sueltas
    en el aire. Esto reemplaza esos últimos milímetros por el cono más cerrado
    que sí pega, que es exactamente el mismo criterio que ya vigila todo lo demás.

    No inventa material: solo frena la velocidad a la que el radio puede cambiar.
    Por eso la punta queda abierta, y cuánto queda abierta lo dice el informe —
    es un dato para decidir, no algo para tapar en silencio.
    """
    dt = altura_capa / max(alto, 1e-9)
    n = muestras
    tabla = [radio(i / n) for i in range(n + 1)]
    paso_max = ancho * (1.0 / n) / dt          # cuánto puede cambiar por muestra
    tocados = 0
    for i in range(1, n + 1):
        d = tabla[i] - tabla[i - 1]
        if abs(d) > paso_max:
            tabla[i] = tabla[i - 1] + math.copysign(paso_max, d)
            tocados += 1

    def rec(t: float) -> float:
        x = min(1.0, max(0.0, t)) * n
        i = min(n - 1, int(x))
        return tabla[i] + (tabla[i + 1] - tabla[i]) * (x - i)

    return rec, {"tocados": tocados, "muestras": n,
                 "r_boca_antes": radio(1.0), "r_boca_despues": tabla[-1]}


def rasterizar(radio: Silueta, ancho: int = 60, alto: int = 26) -> str:
    """El perfil en ASCII, media sección: el eje a la izquierda."""
    rmax = max(radio(i / 200) for i in range(201)) or 1.0
    filas = []
    for f in range(alto):
        t = 1.0 - f / (alto - 1)
        c = int(radio(t) / rmax * (ancho - 1))
        filas.append("|" + " " * c + "#")
    return "\n".join(filas)


def _cli() -> None:
    """
    Mirar un DXF antes de generar nada:

        python -m lamparas.perfil hongis.dxf
        python -m lamparas.perfil hongis.dxf --desde-z 124.4
        python -m lamparas.perfil hongis.dxf --capa "hongis v8_general" --idx 13
    """
    import argparse

    p = argparse.ArgumentParser(prog="lamparas.perfil", description=_cli.__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo")
    p.add_argument("--capa", help="forzar una capa")
    p.add_argument("--idx", type=int, help="forzar una curva por su número")
    p.add_argument("--desde-z", type=float, help="recortar el perfil por abajo")
    p.add_argument("--hasta-z", type=float, help="recortar el perfil por arriba")
    p.add_argument("--altura-capa", type=float, default=0.4)
    p.add_argument("--ancho-linea", type=float, default=1.2)
    args = p.parse_args()

    cs = curvas(args.archivo)
    print(f"{len(cs)} curvas utilizables en {args.archivo}\n")
    print("las diez que más altura recorren:")
    for c in sorted(cs, key=lambda c: -c.alto)[:10]:
        print(f"  {c}")

    cand = cs
    if args.capa:
        cand = [c for c in cand if c.capa == args.capa]
    if args.idx is not None:
        cand = [c for c in cand if c.idx == args.idx]
    if not cand:
        p.error("ninguna curva coincide con --capa/--idx")
    c = elegir(cand)
    print(f"\nelegida: {c}")

    cir = [x for x in circulos(args.archivo)]
    if cir:
        print("\ncírculos (de acá salen los huecos):")
        alturas = collections.defaultdict(list)
        for capa, z, r in cir:
            alturas[round(z, 1)].append(r)
        for z in sorted(alturas):
            rs = sorted(set(round(r, 2) for r in alturas[z]))
            print(f"  z {z:8.1f}   Ø " + ", ".join(f"{2*r:.1f}" for r in rs))

    radio, info = radio_de(c, args.desde_z, args.hasta_z)
    print(f"\nperfil: z {info['z0']:.1f}..{info['z1']:.1f} ({info['alto']:.1f} mm de alto)")
    print(f"  radio {info['r_min']:.1f}..{info['r_max']:.1f} mm   "
          f"base {info['r_base']:.1f}   boca {info['r_boca']:.1f}")
    print(rasterizar(radio))
    malos = voladizo(radio, info["alto"], args.altura_capa, args.ancho_linea)
    print()
    if malos:
        peor = max(malos, key=lambda m: m[1])
        print(f"⚠ {len(malos)} de 400 tramos se corren más de {args.ancho_linea} mm por vuelta.")
        print(f"  el peor: {peor[1]:.0f}° desde la vertical en t={peor[0]:.2f} "
              f"(z={info['z0'] + peor[0]*info['alto']:.1f}), {abs(peor[2]):.2f} mm por vuelta")
    else:
        print(f"Sin voladizos: con capa {args.altura_capa} y cordón {args.ancho_linea}, "
              f"ninguna vuelta se corre más de un cordón.")


if __name__ == "__main__":
    _cli()
