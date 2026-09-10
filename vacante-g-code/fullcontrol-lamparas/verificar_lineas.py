#!/usr/bin/env python3
"""
¿El peine se ve, o se lo come el cordón?

El g-code de una pieza tipo `bowls/peine.py` tiene una onda radial con un
diente por línea vertical. Que la onda esté EN EL ARCHIVO no dice nada sobre la
pieza: lo que queda impreso es el cordón, y un cordón de 0.8 mm rellena
cualquier valle más angosto que él. La pieza sale con una ondulación insinuada
y el archivo, mientras tanto, muestra un peine perfecto.

Así que acá no se mide el recorrido: se mide la SUPERFICIE que ese recorrido
deja. El modelo del cordón —la unión de discos de radio `ancho/2` apoyados a lo
largo de la trayectoria— vive en `lamparas/cordon.py` y es EL MISMO que usa el
generador para elegir cuántas líneas entran.

Que sea el mismo modelo no lo vuelve un espejo: el generador lo corre sobre un
diente ideal repetido, y acá se corre sobre el g-code que salió de verdad, con
su rejilla de muestreo y su máscara ya aplicadas. Si los dos números no
coinciden, lo que se emitió no es lo que el patrón cree que emitió — que es
exactamente el error que este archivo existe para cazar.

De ahí salen los números que deciden la pieza:

- **Relieve que sobrevive**: pico a valle de `env` contra pico a valle del
  recorrido. Es la fracción del peine que de verdad se ve. Por debajo de ~40 %
  la pieza sale casi lisa por más amplitud que diga el gcode: lo que hay que
  bajar es la CANTIDAD de líneas, no subir la amplitud.
- **Apoyo**: cuánto se corre el radio entre una vuelta y la siguiente EN EL
  MISMO ÁNGULO. Es la regla que gobierna todas las piezas de este proyecto
  (`Δ radio por vuelta < ancho de cordón`), y en un peine no la mueve la
  silueta —la pared es vertical— sino la rampa con la que una línea pasa de la
  altura de fondo a la del dibujo.

- **Lo que la máquina puede seguir**. Los dos anteriores son geometría; este es
  el que la geometría no ve. Un peine fino recorrido rápido le pide al cabezal
  una oscilación radial de decenas de hercios, y el eje tiene una aceleración
  máxima: por encima de ella la máquina redondea la onda y la pieza sale más
  lisa que el archivo, sin que ningún verificador geométrico se entere. Se
  reporta la frecuencia y la aceleración de pico que pide el g-code —con la
  velocidad que el propio g-code declara— para poder compararlas contra el
  límite del perfil de impresión. Es una ESTIMACIÓN: sale de tratar el diente
  como una senoidal, y un diente con meseta pide más, no menos.

Uso:
    python3 verificar_lineas.py output/peine.gcode
    python3 verificar_lineas.py output/peine.gcode --ancho 0.8 --vueltas 40
"""

import argparse
import math
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lamparas.cordon import envolvente, pico_a_valle   # noqa: E402

MARCADOR = "FIN DEL START GCODE"
# Fracción del relieve del recorrido que tiene que sobrevivir al cordón para
# que el peine se lea. No es un número inventado: por debajo de acá el valle
# entre dientes mide menos que el cordón y la superficie queda ondulada en vez
# de rayada. Ver el aviso de `bowls/peine.py`, que trabaja sobre el mismo
# criterio pero ANTES de generar (paso de línea contra cordón).
RELIEVE_MINIMO = 0.40


def leer(ruta: str):
    """Puntos extruidos del cuerpo de la pieza: (x, y, z, mm/min), en orden."""
    x = y = z = None
    f = 0.0
    puntos = []
    empezo = False
    ancho = None
    with open(ruta, encoding="utf-8", errors="ignore") as f:
        for linea in f:
            if not empezo:
                empezo = MARCADOR in linea
                continue
            if ancho is None:
                m = re.search(r";WIDTH:([\d.]+)", linea)
                if m:
                    ancho = float(m.group(1))
            if not linea.startswith(("G0", "G1")):
                continue
            mf = re.search(r"F(-?[\d.]+)", linea)
            if mf:
                f = float(mf.group(1))
            campos = dict(re.findall(r"([XYZE])(-?[\d.]+)", linea))
            nx = float(campos.get("X", x)) if (campos.get("X") or x is not None) else None
            ny = float(campos.get("Y", y)) if (campos.get("Y") or y is not None) else None
            nz = float(campos.get("Z", z)) if (campos.get("Z") or z is not None) else None
            extruye = "E" in campos and float(campos["E"]) > 0
            x, y, z = nx, ny, nz
            if extruye and None not in (x, y, z):
                puntos.append((x, y, z, f))
    return puntos, ancho


def _pared(puntos):
    """
    Descarta el piso macizo y el anillo plano de arranque.

    El piso es la espiral del fondo y la primera vuelta de pared es un anillo
    a esa misma altura: las dos viven en la Z mínima. Todo lo que sube ya es
    pared.
    """
    if not puntos:
        return []
    z0 = min(p[2] for p in puntos)
    for i, p in enumerate(puntos):
        if p[2] > z0 + 1e-6:
            return puntos[i:]
    return []


def _polares(puntos):
    a = np.asarray(puntos, dtype=float)[:, :4]
    cx, cy = a[:, 0].mean(), a[:, 1].mean()
    r = np.hypot(a[:, 0] - cx, a[:, 1] - cy)
    th = np.unwrap(np.arctan2(a[:, 1] - cy, a[:, 0] - cx))
    return r, th, a[:, 2], a[:, 3]


def _remuestrear(r, th, rayos):
    """
    r en los ángulos `rayos`, interpolando sobre el desenrollado.

    Los ángulos son ABSOLUTOS. Anclarlos al primer punto de cada vuelta —que es
    lo que hacía antes— corre una vuelta respecto de la otra hasta un paso de
    muestreo, porque el corte por `searchsorted` no cae en el mismo sitio en
    todas. Con seis muestras por diente eso es media línea de desfasaje, y al
    comparar dos vueltas se terminaba restando la cresta de una contra el
    flanco de la otra: daba 0.898 mm de salto radial en una pieza cuyo patrón
    no se mueve más de 0.138 por vuelta. El número era del método, no de la
    pieza.
    """
    return np.interp(rayos, th, r)


def _densificar(puntos, ancho=0.8):
    """
    El recorrido con puntos bien juntos, interpolando SOBRE LOS SEGMENTOS.

    Hace falta para que las dos mediciones se puedan comparar. La envolvente
    modela el cordón como discos apoyados en los puntos del recorrido, y con
    los puntos crudos —uno cada 0.3 mm— entre disco y disco queda un hueco que
    ningún rayo toca: la envolvente salía MAYOR que el recorrido, o sea "el
    cordón agranda el relieve", que es imposible. Con los puntos a 0.05 mm los
    discos se pisan y la unión es la cinta que de verdad deja la boquilla.

    Y de paso el recorrido de referencia se mide sobre la MISMA poligonal, así
    que la fracción que se reporta compara dos cosas iguales y no un estimador
    contra otro.
    """
    paso = min(0.05, ancho / 8)
    a = np.asarray(puntos, dtype=float)[:, :2]
    d = np.hypot(np.diff(a[:, 0]), np.diff(a[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(d)])
    if s[-1] <= 0:
        return a[:, 0], a[:, 1]
    fino = np.arange(0.0, s[-1], paso)
    return np.interp(fino, s, a[:, 0]), np.interp(fino, s, a[:, 1])


def _lineas(perfil: np.ndarray) -> int:
    """Cuántas líneas hay alrededor: el armónico dominante del perfil."""
    espectro = np.abs(np.fft.rfft(perfil - perfil.mean()))
    if len(espectro) < 5:
        return 0
    return int(np.argmax(espectro[4:]) + 4)


def _desenrollar(perfiles, n, filas=32, columnas=96) -> str:
    """
    La pieza abierta y aplanada: qué líneas quedaron altas y cuáles bajas.

    La altura de cada línea sale del pico a valle DENTRO de esa línea, y el
    corte entre fondo y dibujo se pone en el medio de los dos modos que hay —
    la mediana entre el mínimo y el máximo de la pieza— y no en un número fijo:
    la amplitud del fondo y la del dibujo son parámetros y cambian de pieza en
    pieza.
    """
    validos = [p for p in perfiles if p is not None]
    if not validos:
        return "(no hay vueltas que dibujar)"
    alturas = []
    for perfil, _z in validos:
        m = len(perfil) // n * n
        trozos = perfil[:m].reshape(n, -1)
        alturas.append(trozos.max(axis=1) - trozos.min(axis=1))
    mapa = np.array(alturas)                       # (vueltas, lineas)
    corte = (mapa.min() + mapa.max()) / 2
    filas_txt = []
    for f in range(filas):
        v = int(round((filas - 1 - f) / (filas - 1) * (mapa.shape[0] - 1)))
        fila = "".join(
            "#" if mapa[v, int(c / columnas * n)] > corte else "\u00b7"
            for c in range(columnas))
        filas_txt.append(fila)
    return ("  el dibujo COMO QUEDO EN EL G-CODE, 0\u00b0..360\u00b0 de izquierda a derecha "
            f"(corte en {corte:.2f} mm)\n" + "\n".join("  " + f for f in filas_txt))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcode")
    ap.add_argument("--ancho", type=float, default=None,
                    help="ancho de cordón en mm. Por defecto, el que declara el propio g-code.")
    ap.add_argument("--vueltas", type=int, default=24,
                    help="cuántas vueltas medir, repartidas por toda la altura (por defecto 24)")
    ap.add_argument("--muestras", type=int, default=16,
                    help="puntos por línea en la grilla de medición (por defecto 16)")
    ap.add_argument("--dibujo", action="store_true",
                    help="desenrollar la pieza y mostrar en ASCII qué líneas quedaron altas. "
                         "Es el dibujo tal como QUEDÓ EN EL G-CODE, no la máscara: entre una "
                         "cosa y la otra están la cuantización a la rejilla, la rampa vertical "
                         "y las capas de transición, y cualquiera de las tres puede haberse "
                         "comido el dibujo sin que ninguna otra medición se entere.")
    args = ap.parse_args()

    puntos, ancho_declarado = leer(args.gcode)
    ancho = args.ancho or ancho_declarado or 0.8
    pared = _pared(puntos)
    if len(pared) < 1000:
        print(f"{args.gcode}: no hay pared que medir ({len(pared)} puntos extruidos).")
        return 1

    r, th, z, vel = _polares(pared)
    n_vueltas = int((th[-1] - th[0]) / (2 * math.pi))
    if n_vueltas < 3:
        print(f"{args.gcode}: {n_vueltas} vueltas, muy poco para medir.")
        return 1

    # Una vuelta de reconocimiento para saber cuántas líneas hay, y con eso
    # armar la grilla: hay que muestrear el diente, no la vuelta.
    medio = (th[0] + th[-1]) / 2
    corte = slice(*np.searchsorted(th, [medio, medio + 2 * math.pi]))
    gruesa = medio + np.linspace(0, 2 * math.pi, 2048, endpoint=False)
    n = _lineas(_remuestrear(r[corte], th[corte], gruesa))
    if n <= 0:
        print(f"{args.gcode}: no se detectó ninguna línea vertical.")
        return 1
    # Una sola grilla, en ángulos absolutos y anclada al arranque de la pared:
    # todas las vueltas se miden en los MISMOS ángulos, que es lo que permite
    # restarlas entre sí.
    grilla = np.linspace(0, 2 * math.pi, n * args.muestras, endpoint=False)

    # --- relieve: unas cuantas vueltas repartidas por la altura --------------
    #
    # Es la parte cara (la unión de discos), así que se muestrea. El apoyo, en
    # cambio, se mide en TODAS: es barato y el peor salto puede estar en
    # cualquier vuelta.
    elegidas = np.linspace(1, n_vueltas - 2, min(args.vueltas, n_vueltas - 2), dtype=int)
    relieves, envueltos = [], []
    todos = np.asarray(pared, dtype=float)
    cx, cy = todos[:, 0].mean(), todos[:, 1].mean()
    margen = 2 * math.pi / n          # una línea de más a cada lado
    for v in elegidas:
        a = th[0] + v * 2 * math.pi
        # La rebanada va un poco MÁS ANCHA que la vuelta: los rayos arrancan
        # exactamente en `a` y el recorrido densificado tiene que bracketearlos,
        # o el primero cae antes del primer punto y el modelo se queda sin
        # discos que apoyar justo en el borde.
        corte = slice(*np.searchsorted(th, [a - margen, a + 2 * math.pi + margen]))
        if corte.stop - corte.start < n:
            continue
        xd, yd = _densificar(pared[corte], ancho)
        rd = np.hypot(xd - cx, yd - cy)
        td = np.unwrap(np.arctan2(yd - cy, xd - cx))
        # `unwrap` arranca en la rama principal (-pi, pi], así que el ángulo
        # densificado NO está en el mismo marco que el acumulado de la espiral:
        # se lo lleva al de `th` sumando las vueltas enteras que le faltan. Sin
        # esto los rayos caen a decenas de vueltas de distancia del recorrido.
        td += 2 * math.pi * round((th[corte][0] - td[0]) / (2 * math.pi))
        rayos = a + grilla
        relieves.append(pico_a_valle(_remuestrear(rd, td, rayos), n))
        envueltos.append(pico_a_valle(envolvente(rd, td, ancho, rayos), n))

    recorrido = float(np.median(relieves))
    impreso = float(np.median(envueltos))
    fraccion = impreso / recorrido if recorrido > 1e-9 else 0.0
    radio_medio = float(np.median(r))
    paso_mm = 2 * math.pi * radio_medio / n

    # --- apoyo: el radio de una vuelta contra el de la de abajo, mismo ángulo -
    #
    # Vueltas CONSECUTIVAS, no las que se eligieron arriba. Repartir el salto
    # entre vueltas salteadas es una regla de tres sobre algo que no es lineal:
    # con una rampa de 4 vueltas medida cada 2, daba 0.375 mm donde el patrón
    # se corre 0.138. El techo que importa es entre vecinas.
    perfiles = []
    for v in range(n_vueltas - 1):
        a = th[0] + v * 2 * math.pi
        corte = slice(*np.searchsorted(th, [a - margen, a + 2 * math.pi + margen]))
        if corte.stop - corte.start < n:
            perfiles.append(None)
            continue
        perfiles.append((_remuestrear(r[corte], th[corte], a + grilla), float(z[corte].mean())))
    pares = [(float(np.abs(b[0] - a[0]).max()), b[1])
             for a, b in zip(perfiles, perfiles[1:]) if a is not None and b is not None]
    salto_vuelta, z_peor = max(pares) if pares else (0.0, 0.0)
    flojas = sum(1 for s_, _ in pares if s_ > ancho * 0.5)
    # Se reporta la DISTRIBUCIÓN y no sólo el peor. El peor de una pieza sana
    # queda por encima de lo que el patrón se mueve por vuelta, y no es un
    # error: el recorrido es una poligonal, así que entre dos vértices el radio
    # va por una recta, y dos vueltas cuyos vértices no caen sobre los mismos
    # rasgos se separan más en el medio del tramo que en las puntas. Medido en
    # el florero: mediana 0.136 y p99 0.138 contra los 0.1375 que declara el
    # patrón —o sea que el grueso coincide con el cálculo— y un único punto en
    # 0.185. Si la mediana no coincidiera con lo que el patrón declara, ahí sí
    # habría un problema de verdad.
    saltos = np.array([s_ for s_, _ in pares]) if pares else np.zeros(1)

    print(f"{args.gcode}")
    print(f"  {n_vueltas} vueltas · radio medio {radio_medio:.1f} mm · cordón {ancho:g} mm"
          + ("" if args.ancho else " (declarado por el g-code)"))
    print(f"  {n} líneas verticales · paso {paso_mm:.2f} mm = "
          f"{paso_mm / ancho:.1f} cordones")
    print(f"  relieve del RECORRIDO {recorrido:.3f} mm  ->  de la SUPERFICIE "
          f"{impreso:.3f} mm  ({100 * fraccion:.0f} % sobrevive al cordón)")
    # --- lo que la máquina tiene que poder seguir ---------------------------
    #
    # Geometría aparte: recorrer `n` dientes por vuelta a la velocidad que
    # declara el g-code es pedirle al cabezal una oscilación radial de `v/paso`
    # hercios. La aceleración de pico de una senoidal de media amplitud `A` a
    # esa frecuencia es `(2 pi f)^2 A`, y si el perfil de impresión no la
    # permite, la máquina redondea la onda: la pieza sale más lisa que el
    # archivo y ningún verificador geométrico se entera.
    #
    # Es una ESTIMACIÓN por lo bajo: el diente tiene meseta y flancos, o sea
    # más contenido armónico que una senoidal, y eso pide más aceleración.
    v_mm_s = float(np.median(vel[vel > 0])) / 60.0 if np.any(vel > 0) else 0.0
    hz = v_mm_s / paso_mm if paso_mm > 1e-9 else 0.0
    acel = (2 * math.pi * hz) ** 2 * (recorrido / 2)

    print(f"  apoyo: el radio se corre {float(np.median(saltos)):.3f} mm por vuelta "
          f"(mediana), peor {salto_vuelta:.3f} en z={z_peor:.1f} -> "
          f"{100 * max(0.0, ancho - salto_vuelta) / ancho:.0f} % de solape en el peor punto"
          + (f" · {flojas} de {len(pares)} vueltas por debajo del 50 %" if flojas else ""))

    print(f"  dinámica: a {v_mm_s:.0f} mm/s el cabezal oscila a {hz:.0f} Hz, "
          f"pico ~{acel:.0f} mm/s² de aceleración radial (estimado). "
          f"Comparalo con la aceleración de pared exterior de tu perfil: por debajo "
          f"de ese número la máquina redondea el peine y sale más liso que el archivo.")

    if args.dibujo:
        print(_desenrollar(perfiles, n, filas=32, columnas=96))

    problemas = 0
    if fraccion < RELIEVE_MINIMO:
        print(f"  AVISO: el cordón se come el {100 * (1 - fraccion):.0f} % del peine. "
              f"Bajá la cantidad de líneas (a ~{int(2 * math.pi * radio_medio / (2.5 * ancho))} "
              f"para este radio y esta boquilla) o poné una boquilla más fina. "
              f"Subir la amplitud no lo arregla: lo que falta es VALLE, no altura.")
        problemas += 1
    if salto_vuelta > ancho:
        print("  ERROR: entre dos vueltas el radio se corre más que un cordón entero: "
              "la vuelta nueva no toca la anterior. Subí 'rampa'.")
        problemas += 1
    elif salto_vuelta > ancho * 0.5:
        print("  AVISO: menos del 50 % de solape en el peor punto. Subí 'rampa'.")
        problemas += 1
    if not problemas:
        print("  OK: el peine se lee y cada vuelta apoya sobre la anterior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
