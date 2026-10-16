#!/usr/bin/env python3
"""
Mide el TRESBOLILLO en un g-code con grumos (`puas intercalar=1`): dónde cae
cada grumo respecto de los dos de la fila de abajo. 0.5 es justo en el medio;
0 o 1, encima de uno.

    python3 verificar_intercalado.py output/arbol/1-cupones/intercalado/largos_1.2a9mm.gcode [-q]

"En el medio" es a menos de 0.2 púa del centro; "apilado", a menos de 0.15 de
uno de los dos de abajo.

Las vueltas se cortan en el ángulo donde ARRANCA la pared, que no es 0°: sale de
donde termina la espiral del piso (en el árbol, ~32°). Cortando en 0° cada fila
queda partida entre dos vueltas y el medidor inventa un grumo apilado por fila
en la costura —le pasó a la primera versión de este script—. Como ese ángulo no
está escrito en el archivo, se prueban cortes cada 2° y se elige el que deja
menos filas y, a igual cantidad, las filas más enteras.

Supone la pieza centrada en (128, 128), como las emite `comun.py`.
"""
import re, math, sys, bisect
ruta = sys.argv[1]; cx = cy = 128.0
pts = []; z = 0.0
for l in open(ruta):
    if not l.startswith('G1') or 'E' not in l: continue
    m = re.search(r'Z([\d.]+)', l)
    if m: z = float(m.group(1))
    mx = re.search(r'X([-\d.]+)', l); my = re.search(r'Y([-\d.]+)', l)
    if not (mx and my): continue
    x, y = float(mx.group(1)) - cx, float(my.group(1)) - cy
    pts.append((math.atan2(y, x) % (2 * math.pi), math.hypot(x, y), z))

def filas_con(a0):
    vueltas = []; cur = []; prev = None
    for a, r, zz in pts:
        a = (a - a0) % (2 * math.pi)
        if prev is not None and a < prev - math.pi:
            vueltas.append(cur); cur = []
        cur.append((a, r, zz)); prev = a
    vueltas.append(cur)
    filas = []
    for i, v in enumerate(vueltas):
        if len(v) < 50: continue
        base = sorted(p[1] for p in v)[len(v) // 10]
        puntas = []; run = []
        for a, r, zz in v:
            if r - base > 0.7: run.append(a)
            elif run: puntas.append(sum(run) / len(run)); run = []
        if run: puntas.append(sum(run) / len(run))
        if len(puntas) > 10:
            filas.append((i, v[0][2], sorted(p % (2 * math.pi) for p in puntas)))
    return filas

def nota(g):
    f = filas_con(math.radians(g))
    # menos filas, y a igual cantidad, filas más ENTERAS (más grumos cada una)
    return (len(f), -sum(len(x[2]) for x in f) / max(1, len(f)), g)
mejor = min(nota(g) for g in range(0, 360, 2))
filas = filas_con(math.radians(mejor[2]))
print(f"{len(filas)} filas con grumos (corte de vuelta en {mejor[2]}°)")
total = bien_t = apil_t = 0
for (i0, z0, p0), (i1, z1, p1) in zip(filas, filas[1:]):
    ds = []
    for a in p1:
        k = bisect.bisect_left(p0, a)
        lo = p0[k - 1] if k > 0 else p0[-1] - 2 * math.pi
        hi = p0[k] if k < len(p0) else p0[0] + 2 * math.pi
        ds.append((a - lo) / ((hi - lo) or 1e-9))
    bien = sum(1 for d in ds if abs(d - 0.5) < 0.2)
    apil = sum(1 for d in ds if abs(d - 0.5) > 0.35)
    total += len(ds); bien_t += bien; apil_t += apil
    if '-q' not in sys.argv:
        print(f"z {z0:5.1f}->{z1:5.1f}  grumos {len(p0):3d}->{len(p1):3d}"
              f"  en el medio {100*bien/len(ds):5.1f} %  apilados {100*apil/len(ds):5.1f} %")
print(f"TOTAL  en el medio {100*bien_t/total:.1f} %   apilados {100*apil_t/total:.1f} %")
