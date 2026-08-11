#!/usr/bin/env python3
"""
El campo de deformación del preview tiene que dar lo MISMO que el de Python.

Hay dos implementaciones del mismo cálculo —una en `lamparas/modelado.py`, que
es la que genera el gcode, y otra en `media/main.js`, que es la que deforma la
pieza en pantalla mientras arrastrás— y si se separan, el preview miente: la
pared se mueve en un lado y sale impresa en otro.

No es hipotético. La primera versión de `envolver()` en JS usaba `3π` donde iba
`2π`, y eso corría CADA toque media vuelta. Era invisible mientras el preview
dibujaba una cáscara translúcida; con la pieza real deformándose no lo sería,
pero para entonces ya habría salido un gcode equivocado. Esto lo agarra antes.

    python3 verificar_campo.py        (desde ext-gcode/gcode-preview)

Se relanza solo con el intérprete del venv de lamparas, que es el único que
tiene fullcontrol instalado.

Extrae el JS del archivo de verdad, no de una copia: si alguien toca main.js,
esto prueba lo que se toc��.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LAMPARAS = AQUI.parent.parent / "vacante-g-code" / "fullcontrol-lamparas"
sys.path.insert(0, str(LAMPARAS))

# `lamparas` importa fullcontrol, que vive en el venv del generador y no en el
# python del sistema. En vez de pedirle a quien corra esto que se acuerde de
# activar el entorno, el script se relanza solo con el intérprete correcto.
_VENV = LAMPARAS / "venv" / "bin" / "python"
if _VENV.exists() and Path(sys.executable).resolve() != _VENV.resolve():
    import os
    os.execv(str(_VENV), [str(_VENV), str(Path(__file__).resolve()), *sys.argv[1:]])

CASOS = [
    {"tipo": "jalar", "forma": "circulo", "caida": "gauss", "rotacion": 0,
     "angulo": 40, "t": 0.55, "radio_grados": 34, "radio_t": 0.09, "simetria": 1, "fuerza": 2.4},
    {"tipo": "empujar", "forma": "estrella", "caida": "suave", "rotacion": 15,
     "angulo": 200, "t": 0.30, "radio_grados": 48, "radio_t": 0.22, "simetria": 3,
     "fuerza": 1.8, "puntas": 5, "hundido": 0.5},
    {"tipo": "jalar", "forma": "cuadrado", "caida": "meseta", "rotacion": 45,
     "angulo": 0, "t": 0.5, "radio_grados": 60, "radio_t": 0.3, "simetria": 2, "fuerza": 3.0},
    {"tipo": "jalar", "forma": "anillo", "caida": "pico", "rotacion": 0,
     "angulo": 120, "t": 0.7, "radio_grados": 70, "radio_t": 0.25, "simetria": 1,
     "fuerza": 1.2, "grosor": 0.4},
    {"tipo": "textura", "forma": "circulo", "caida": "gauss", "rotacion": 0,
     "angulo": 180, "t": 0.8, "radio_grados": 90, "radio_t": 0.4, "simetria": 1,
     "fuerza": 0.8, "escala": 18, "semilla": 4},
    {"tipo": "jalar", "forma": "banda", "caida": "gauss", "rotacion": 0,
     "angulo": 0, "t": 0.2, "radio_grados": 180, "radio_t": 0.35, "simetria": 1, "fuerza": 1.4},
    {"tipo": "jalar", "forma": "poligono", "caida": "suave", "rotacion": 30,
     "angulo": 300, "t": 0.45, "radio_grados": 55, "radio_t": 0.3, "simetria": 4,
     "fuerza": 2.0, "lados": 6},
    {"tipo": "empujar", "forma": "cruz", "caida": "plano", "rotacion": 0,
     "angulo": 90, "t": 0.6, "radio_grados": 45, "radio_t": 0.28, "simetria": 1,
     "fuerza": 1.1, "grosor": 0.35},
    # Fuerza NEGATIVA con tipo 'jalar': es el estado de un trazo mientras se
    # arrastra hacia abajo, antes de que al soltar se renombre a 'empujar'. Si
    # las dos implementaciones no coinciden acá, el preview muestra un bulto
    # donde el gcode va a hacer un hundido.
    {"tipo": "jalar", "forma": "circulo", "caida": "gauss", "rotacion": 0,
     "angulo": 210, "t": 0.4, "radio_grados": 40, "radio_t": 0.2, "simetria": 1,
     "fuerza": -1.85},
]

# Dónde empieza y termina cada trozo de main.js que hace falta. Son marcas de
# comentario y no números de línea: mover código no rompe esto, borrarlo sí, que
# es exactamente cuando uno quiere enterarse.
TROZOS = [
    ("  const ESC_FORMAS = {", "  // --- la cáscara"),
    ("  function _valorJS(", "  // Un toque como campo"),
    ("  function campoDeToque(", "  // La diferencia entre lo que se quiere ver"),
]

ARNES = r"""
const casos = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = [];
for (const t of casos) {
  const f = campoDeToque(t, 1);
  for (let i = 0; i < 9; i++) {
    for (let j = 0; j < 5; j++) {
      out.push((f ? f(i / 9 * 2 * Math.PI, j / 4) : 0).toFixed(9));
    }
  }
}
console.log(out.join('\n'));
"""


def js() -> list:
    fuente = (AQUI / "media" / "main.js").read_text(encoding="utf-8")
    partes = []
    for desde, hasta in TROZOS:
        if desde not in fuente:
            sys.exit(f"no encontré {desde!r} en media/main.js — ¿le cambiaron el nombre?")
        i = fuente.index(desde)
        partes.append(fuente[i:fuente.index(hasta, i)])
    tmp = AQUI / ".campo_arnes.js"
    casos = AQUI / ".campo_casos.json"
    tmp.write_text("\n".join(partes) + ARNES, encoding="utf-8")
    casos.write_text(json.dumps(CASOS), encoding="utf-8")
    try:
        salida = subprocess.run(["node", str(tmp), str(casos)],
                                capture_output=True, text=True, check=True).stdout
    finally:
        tmp.unlink(missing_ok=True)
        casos.unlink(missing_ok=True)
    return salida.split()


def py() -> list:
    from lamparas import modelado
    out = []
    for crudo in CASOS:
        propios = {k: v for k, v in crudo.items() if k in modelado._CAMPOS}
        extra = {k: v for k, v in crudo.items() if k not in modelado._CAMPOS}
        d = modelado.deformacion([modelado.Toque(**propios, parametros=extra)])
        for i in range(9):
            for j in range(5):
                out.append("%.9f" % d(i / 9 * 2 * math.pi, j / 4))
    return out


def main() -> int:
    a, b = js(), py()
    if a == b:
        print(f"Idénticos: {len(a)} muestras, {len(CASOS)} pinceles "
              f"(círculo, estrella, cuadrado, anillo, textura, banda, polígono, cruz), "
              f"5 caídas, con rotación y simetría.")
        return 0
    print(f"DIFIEREN. {sum(1 for x, y in zip(a, b) if x != y)} de {len(a)} muestras.\n")
    caso = 0
    for k, (x, y) in enumerate(zip(a, b)):
        if x != y:
            caso = k // 45
            print(f"  muestra {k} (pincel #{caso + 1}, forma {CASOS[caso]['forma']}): "
                  f"js {x}  vs  python {y}")
            if k > 400:
                break
    return 1


if __name__ == "__main__":
    sys.exit(main())
