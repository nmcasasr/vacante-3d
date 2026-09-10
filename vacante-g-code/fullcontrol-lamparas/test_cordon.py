#!/usr/bin/env python3
"""
Banco de pruebas del modelo del cordón (`lamparas/cordon.py`).

Existe por dos motivos concretos, los dos errores que ya se cometieron acá:

1. **La envolvente daba MÁS relieve que el recorrido.** Es imposible: pasarle
   un cordón encima a un perfil sólo puede rellenar, nunca ahondar. El bug era
   que el modelo apoya un disco en cada punto y los puntos del g-code crudo van
   uno cada 0.3 mm, así que entre disco y disco quedaba un hueco que ningún
   rayo tocaba. El caso `monotonía` de acá abajo lo caza en cuatro líneas.

2. **`lineas_que_entran` busca por bisección**, y una bisección sobre algo que
   no es monótono devuelve cualquier cosa con toda seriedad. El caso
   `sin repunte` barre el rango entero y verifica que sobrevivir de verdad baje
   con la cantidad de líneas, que es la suposición que la bisección usa.

    python3 test_cordon.py
"""

import math
import sys

import numpy as np

from lamparas.bowls.peine import _bulto
from lamparas.cordon import envolvente, lineas_que_entran, pico_a_valle, sobrevive

RADIO, CORDON, AMPLITUD = 32.0, 0.8, 0.55


def _diente(ancho=0.55, meseta=0.45):
    return lambda f: _bulto(f, ancho, meseta)


def main() -> int:
    fallos = 0

    def caso(bien: bool, texto: str, detalle: str = "") -> None:
        nonlocal fallos
        fallos += not bien
        print(f"  {'ok  ' if bien else 'FALLA'}  {texto}")
        if not bien and detalle:
            print(f"          {detalle}")

    print("modelo del cordón")

    # --- el cordón nunca agranda el relieve ---------------------------------
    peor = 0.0
    for n in (40, 80, 120, 160, 200, 260, 340):
        crudo, impreso = sobrevive(_diente(), RADIO, CORDON, n, AMPLITUD)
        peor = max(peor, impreso / crudo)
    # 2 % de tolerancia: la grilla de medición es discreta y puede no caer justo
    # en la cresta ni en el fondo. El bug que este caso caza no daba 1.01: daba
    # 1.10, y el de al lado daba infinito.
    caso(peor <= 1.02,
         "la superficie nunca tiene MÁS relieve que el recorrido",
         f"la peor razón dio {peor:.3f}; con más de 1 el modelo está mordido "
         f"(puntos demasiado separados para el diámetro del cordón)")

    # --- un cordón de cero no cambia nada -----------------------------------
    crudo, impreso = sobrevive(_diente(), RADIO, 0.02, 160, AMPLITUD)
    caso(abs(impreso - crudo) < 0.02 * crudo,
         "con un cordón de espesor ~0 la superficie ES el recorrido",
         f"recorrido {crudo:.3f}, superficie {impreso:.3f}")

    # --- un modelo mordido levanta en vez de devolver un número -------------
    esparcidos = np.linspace(0, 2 * math.pi, 300, endpoint=False)
    try:
        envolvente(np.full_like(esparcidos, RADIO), esparcidos, 0.05,
                   np.linspace(0, 2 * math.pi, 600, endpoint=False))
        bien, detalle = False, "devolvió un número con los discos separados"
    except ValueError as e:
        bien, detalle = "no cubre" in str(e), str(e)
    caso(bien, "con los puntos demasiado separados, el modelo levanta y no inventa", detalle)

    # --- un cordón enorme aplana todo ---------------------------------------
    crudo, impreso = sobrevive(_diente(), RADIO, 8.0, 160, AMPLITUD)
    caso(impreso < 0.15 * crudo,
         "un cordón mucho más ancho que el paso borra el peine",
         f"quedó el {100 * impreso / crudo:.0f} % con cordón de 8 mm")

    # --- sobrevivir baja con la cantidad de líneas (lo que la bisección supone)
    valores = []
    for n in range(40, 401, 20):
        crudo, impreso = sobrevive(_diente(), RADIO, CORDON, n, AMPLITUD)
        valores.append((n, impreso / crudo))
    # Tolerancia: la grilla de medición es discreta y puede mover un punto un
    # par de por ciento sin que la tendencia cambie.
    repuntes = [(a, b) for (a, va), (b, vb) in zip(valores, valores[1:]) if vb > va + 0.05]
    caso(not repuntes,
         "sobrevivir baja con la cantidad de líneas (la bisección es válida)",
         f"repunta entre {repuntes}" if repuntes else "")

    # --- la bisección cae en el escalón real --------------------------------
    n = lineas_que_entran(_diente(), RADIO, CORDON, AMPLITUD, 0.85)
    c1, i1 = sobrevive(_diente(), RADIO, CORDON, n, AMPLITUD)
    c2, i2 = sobrevive(_diente(), RADIO, CORDON, n + 12, AMPLITUD)
    caso(i1 / c1 >= 0.85 > i2 / c2,
         "lineas_que_entran devuelve el borde: pasa con n y no con n+12",
         f"n={n} deja {100 * i1 / c1:.0f} %, n+12 deja {100 * i2 / c2:.0f} %")

    # --- un diente más angosto deja pasar más líneas -------------------------
    ancho_55 = lineas_que_entran(_diente(0.55), RADIO, CORDON, AMPLITUD, 0.85)
    ancho_30 = lineas_que_entran(_diente(0.30), RADIO, CORDON, AMPLITUD, 0.85)
    caso(ancho_30 > ancho_55,
         "con el diente más angosto entran más líneas (no lo decide el paso solo)",
         f"diente 0.55 -> {ancho_55} lineas, diente 0.30 -> {ancho_30}")

    # --- la envolvente de un círculo es el círculo más medio cordón ----------
    th = np.linspace(0, 2 * math.pi, 4000, endpoint=False)
    r = np.full_like(th, RADIO)
    grilla = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    env = envolvente(r, th, CORDON, grilla)
    caso(abs(float(np.median(env)) - (RADIO + CORDON / 2)) < 1e-3,
         "sobre una pared lisa la superficie queda a medio cordón del recorrido",
         f"dio {float(np.median(env)):.4f}, se esperaba {RADIO + CORDON / 2:.4f}")

    # --- pico_a_valle mide POR LÍNEA, no el rango del anillo ----------------
    # Un anillo con la mitad de las líneas altas y la otra mitad bajas: el
    # rango del anillo es la diferencia entre las dos alturas, el pico a valle
    # por línea es el de la línea baja.
    n = 100
    x = th * n / (2 * math.pi)
    fase = x - np.floor(x)
    alto = (np.floor(x).astype(int) % n) < n // 2
    perfil = RADIO + np.where(alto, 1.0, 0.3) * np.array([_bulto(f, 0.55, 0.45) for f in fase])
    pv = pico_a_valle(np.interp(grilla, th, perfil), n)
    caso(0.25 < pv < 1.05,
         "pico_a_valle es el relieve de una línea, no el rango del anillo",
         f"dio {pv:.3f}; el rango del anillo entero es 1.0 y el de la línea baja 0.3")

    print(f"\n9 casos · {fallos} fallando")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
