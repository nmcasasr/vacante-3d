#!/usr/bin/env python3
"""
Vista frontal y planta de un g-code, a PNG, sin dependencias.

Existe porque los números solos no alcanzan: la pieza puede medir bien en los
tres criterios y no parecerse al dibujo. Las lenguas salen en rojo y la pared en
gris, que es la separación que el generador deja escrita con `;TIPO:`.

    python3 vista_gcode.py output/glitch5.gcode vista.png [--ancho 1.8]
"""
import sys, math, zlib, struct
sys.path.insert(0, '.')
from verificar_pieza import leer

ancho = float(sys.argv[3]) if len(sys.argv) > 3 else 1.8
segs = leer(sys.argv[1], ancho)
W, H = 1100, 620
buf = bytearray(b'\xff' * (W * H * 3))

def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i:i+3] = bytes(c)

def linea(x0, y0, x1, y1, c):
    n = int(max(abs(x1-x0), abs(y1-y0))) + 1
    for k in range(n + 1):
        t = k / n
        px(int(x0 + (x1-x0)*t), int(y0 + (y1-y0)*t), c)

xs = [s[0] for s in segs]; ys = [s[1] for s in segs]; zs = [s[2] for s in segs]
zmax = max(zs)
GRIS, ROJO = (150,150,155), (200,40,40)

# frontal: (x, z) en el panel izquierdo · planta: (x, y) en el derecho
esc_f = min(520 / (max(xs)-min(xs)), 580 / zmax)
esc_p = 520 / max(max(xs)-min(xs), max(ys)-min(ys))
cx, cy = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
for x1, y1, z1, x2, y2, z2, area, tipo, arco in segs:
    c = ROJO if tipo == 'lengua' else GRIS
    linea(275 + (x1-cx)*esc_f, 600 - z1*esc_f, 275 + (x2-cx)*esc_f, 600 - z2*esc_f, c)
    linea(825 + (x1-cx)*esc_p, 310 - (y1-cy)*esc_p, 825 + (x2-cx)*esc_p, 310 - (y2-cy)*esc_p, c)

filas = b''.join(b'\x00' + bytes(buf[y*W*3:(y+1)*W*3]) for y in range(H))
def chunk(t, d):
    c = t + d
    return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))
open(sys.argv[2], 'wb').write(
    b'\x89PNG\r\n\x1a\n'
    + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    + chunk(b'IDAT', zlib.compress(filas, 6)) + chunk(b'IEND', b''))
print("frontal (izq) y planta (der) · lenguas en rojo")
