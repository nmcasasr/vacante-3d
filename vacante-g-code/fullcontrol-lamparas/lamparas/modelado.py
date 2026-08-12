"""
Esculpir la pieza a punta de toques: jalar, empujar, texturizar, suavizar.

Cada toque es un dato, no una edición del gcode. Eso no es un detalle de
implementación: un gcode editado ya no tiene parámetros, así que la siguiente
corrida del generador tira el cambio, y además habría que recalcular la
extrusión de cada punto movido. Un toque, en cambio, sobrevive a que después
muevas el slider de altura o cambies la silueta.

Un toque es un pincel (ver `formas.py`) puesto en un punto de la superficie
desenrollada:

    {"tipo": "jalar", "forma": "circulo", "angulo": 70, "t": 0.62,
     "radio_grados": 26, "radio_t": 0.07, "fuerza": 2.5}

- `angulo` en GRADOS y `t` en altura relativa (0 base, 1 boca). En `t` y no en
  milímetros a propósito: si después subís la altura de la pieza, los toques se
  estiran con ella en vez de quedarse clavados a una cota que ya no significa
  nada.
- `fuerza` en mm de pared. Positiva saca, negativa mete.

Todo lo que hacen es mover el RADIO. Por eso la pared sigue siendo una espiral
cerrada: el modo vaso sobrevive, no hay nada que reparar y es imposible abrir un
agujero por accidente. Limitarse a deformar no es una concesión, es lo que hace
que esto funcione sin un motor de mallas.

## Lo que hay que mirar antes de imprimir

`revisar()` calcula lo único que de verdad rompe una pieza en modo vaso: cuánto
se corre el radio **de una vuelta a la siguiente**. Si eso supera el ancho del
cordón, la vuelta nueva no apoya sobre la anterior y la pared se abre. Un toque
fuerte y angosto en `t` lo consigue con una facilidad que sorprende, así que el
chequeo corre solo y avisa con números, no con un "cuidado".

    python -m lamparas.modelado toques.json --altura 150 --ancho-linea 1.2
"""

import json
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from . import formas
from .estructura import Deformacion, _ruido

TAU = 2 * math.pi

TIPOS = ("jalar", "empujar", "textura", "suavizar", "aplanar", "pintar")

# Los nombres que van en la raíz del JSON, no dentro de un toque.
_RAIZ = ("version", "simetria", "toques")
# Campos propios del toque; lo que sobre se le pasa a la forma.
_CAMPOS = ("tipo", "forma", "caida", "rotacion", "angulo", "t", "radio_grados",
           "radio_t", "fuerza", "simetria", "escala", "semilla", "nota")


@dataclass
class Toque:
    tipo: str = "jalar"
    forma: str = "circulo"
    caida: str = "gauss"
    rotacion: float = 0.0
    angulo: float = 0.0          # grados
    t: float = 0.5               # altura relativa
    radio_grados: float = 30.0
    radio_t: float = 0.10
    fuerza: float = 2.0          # mm
    simetria: int = 1            # repeticiones alrededor del eje
    escala: int = 12             # solo 'textura': celdas de ruido por vuelta
    semilla: int = 0             # solo 'textura'
    nota: str = ""
    parametros: dict = field(default_factory=dict)   # los de la forma

    def pincel(self) -> Callable[[float, float], float]:
        return formas.resolver(self.forma, caida=self.caida,
                               rotacion=self.rotacion, **self.parametros)


def _envolver(delta: float) -> float:
    """Diferencia de ángulos llevada a [-pi, pi]."""
    return (delta + math.pi) % TAU - math.pi


def leer(ruta: str) -> List[Toque]:
    """
    Lee un archivo de toques.

    Archivo y no banderas de línea de comando: cuarenta toques en un `--toque`
    repetido es inmanejable, y así el archivo se versiona junto a la receta.
    """
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    if isinstance(datos, list):          # lista pelada, sin envoltorio
        datos = {"toques": datos}
    sobra = [k for k in datos if k not in _RAIZ]
    if sobra:
        raise ValueError(f"claves desconocidas en la raíz: {', '.join(sorted(sobra))}. "
                         f"Se aceptan: {', '.join(_RAIZ)}")

    simetria_global = int(datos.get("simetria", 1))
    salida: List[Toque] = []
    for i, crudo in enumerate(datos.get("toques", [])):
        if not isinstance(crudo, dict):
            raise ValueError(f"toque #{i + 1}: se esperaba un objeto")
        propios = {k: v for k, v in crudo.items() if k in _CAMPOS}
        extra = {k: v for k, v in crudo.items() if k not in _CAMPOS}
        propios.setdefault("simetria", simetria_global)
        t = Toque(**propios, parametros=extra)
        if t.tipo not in TIPOS:
            raise ValueError(f"toque #{i + 1}: tipo {t.tipo!r} desconocido. "
                             f"Opciones: {', '.join(TIPOS)}")
        if t.radio_grados <= 0 or t.radio_t <= 0:
            raise ValueError(f"toque #{i + 1}: los radios tienen que ser > 0")
        t.pincel()   # valida forma, caída y parámetros acá y no a media impresión
        salida.append(t)
    return salida


def _pesos(toque: Toque) -> Callable[[float, float], float]:
    """
    `(angulo_rad, t) -> peso 0..1`, ya con la simetría radial resuelta.

    El ángulo ENVUELVE. Sin eso un toque puesto en 0° sale partido en dos
    mitades, una en cada borde del desenrollado.
    """
    pincel = toque.pincel()
    ra = math.radians(toque.radio_grados)
    rt = toque.radio_t
    n = max(1, int(toque.simetria))
    centros = [math.radians(toque.angulo) + k * TAU / n for k in range(n)]

    def peso(angulo: float, t: float) -> float:
        v = (t - toque.t) / rt
        if abs(v) > 1.5:                 # fuera de la huella en altura: cortar ya
            return 0.0
        mejor = 0.0
        for c in centros:
            u = _envolver(angulo - c) / ra
            if abs(u) > 1.5:
                continue
            w = pincel(u, v)
            if w > mejor:
                mejor = w
        return mejor

    return peso


def deformacion(toques: List[Toque],
                estructura: Optional[Deformacion] = None) -> Deformacion:
    """
    Suma todos los toques en una sola `Deformacion` `(angulo, t) -> mm`.

    Args:
        toques: lo que devuelve `leer()`.
        estructura: la deformación de fondo (`--estructura`). Solo la necesitan
            los toques de tipo 'suavizar', que lo que hacen es cancelarla
            localmente; sin ella no tienen nada que apagar.
    """
    partes: List[Callable[[float, float], float]] = []

    for toque in toques:
        if toque.tipo == "pintar":
            continue                     # ese va por la máscara, no por el radio
        peso = _pesos(toque)
        # El signo lo lleva la fuerza; el tipo solo dice para qué lado cuenta.
        # Antes iba con `abs()`, y eso hacía imposible expresar un 'jalar' que
        # en realidad mete —que es exactamente el estado en el que está un
        # trazo mientras se arrastra hacia abajo, antes de renombrarse.
        f = -toque.fuerza if toque.tipo == "empujar" else toque.fuerza

        if toque.tipo in ("jalar", "empujar"):
            partes.append(lambda a, t, p=peso, f=f: f * p(a, t))

        elif toque.tipo == "textura":
            nu = max(2, int(toque.escala))
            sem = int(toque.semilla)

            def textura(a, t, p=peso, f=f, nu=nu, sem=sem):
                w = p(a, t)
                if w <= 0.0:
                    return 0.0
                u = (a % TAU) / TAU
                return f * w * _ruido(u, min(max(t, 0.0), 1.0), nu, nu, sem)

            partes.append(textura)

        elif toque.tipo == "aplanar":
            # Lleva la zona al radio que la pieza tiene EN EL CENTRO del toque.
            # Necesita ver el radio de abajo, y quien lo tiene es `pasos_bowl`,
            # que lo enchufa en `.patron` (ver `necesita_patron`). Aplana la
            # forma de abajo, no los otros toques: se componen después.
            a0, t0 = math.radians(toque.angulo), toque.t
            k = min(1.0, abs(toque.fuerza))

            def aplanar(a, t, p=peso, a0=a0, t0=t0, k=k):
                base = getattr(total, "patron", None)
                if base is None:
                    return 0.0
                w = p(a, t)
                return 0.0 if w <= 0.0 else k * w * (base(a0, t0) - base(a, t))

            partes.append(aplanar)

        elif toque.tipo == "suavizar":
            if estructura is None:
                continue
            frac = min(1.0, abs(toque.fuerza))
            partes.append(
                lambda a, t, p=peso, e=estructura, k=frac: -k * p(a, t) * e(a, t)
            )

    if not partes:
        return lambda a, t: 0.0

    def total(angulo: float, t: float) -> float:
        return sum(p(angulo, t) for p in partes)

    # `aplanar` es el único que necesita ver la forma que hay debajo. En vez de
    # cambiarle la firma a todas las deformaciones, se marca la que lo pide y
    # `pasos_bowl` le enchufa el patrón antes de generar.
    total.necesita_patron = any(t.tipo == "aplanar" for t in toques)
    total.patron = None
    return total


def mascara(toques: List[Toque]):
    """
    Los toques de tipo 'pintar', juntos, como `Mascara` `(angulo, t) -> 0..1`.

    Devuelve None si no hay ninguno, para que quien llame pueda distinguir
    "no pediste pintar" de "pediste pintar nada".
    """
    pintar = [t for t in toques if t.tipo == "pintar"]
    if not pintar:
        return None
    pesos = [_pesos(t) for t in pintar]
    return lambda a, t: min(1.0, max(p(a, t) for p in pesos))


# --- lo que puede salir mal ------------------------------------------------


def _gradientes(toque: Toque, muestras: int = 121):
    """
    Máxima pendiente del pincel en cada eje, en unidades normalizadas.

    Se mide muestreando en vez de derivando a mano porque las formas son nueve y
    las caídas cuatro: una fórmula por combinación se desincroniza en cuanto se
    agrega la décima. Y la caída 'plano' no tiene derivada — muestrear la
    reporta como el escalón enorme que es, que es exactamente lo que se quiere.
    """
    pincel = toque.pincel()
    paso = 3.0 / (muestras - 1)
    du = dv = 0.0
    for i in range(muestras):
        u = -1.5 + i * paso
        for j in range(muestras):
            v = -1.5 + j * paso
            w = pincel(u, v)
            du = max(du, abs(pincel(u + paso, v) - w) / paso)
            dv = max(dv, abs(pincel(u, v + paso) - w) / paso)
    return du, dv


def revisar(toques: List[Toque], altura: float, altura_capa: float,
            ancho_linea: float, segmentos: int = 360,
            radio_tipico: float = 40.0) -> List[str]:
    """
    Avisos con números, antes de generar el gcode.

    Lo que se mide es el corrimiento del radio **de una vuelta a la siguiente**.
    En modo vaso cada vuelta apoya sobre la anterior; si el radio se corre más
    que el ancho del cordón, no hay superficie común y la pared se abre. Es el
    mismo límite que ya vigila `comun._verificar_voladizo` para la silueta, pero
    un toque lo rompe LOCAL: 3 mm de fuerza en `radio_t=0.02` de una pieza de
    150 mm son 3 mm repartidos en 7 vueltas, y ahí ya no pega.

    Args:
        altura: alto de la pared en mm (lo que hace que `t` sea milímetros).
        altura_capa: cuánto sube la espiral por vuelta.
        ancho_linea: ancho del cordón; es el presupuesto contra el que se compara.
        segmentos: puntos por vuelta, para el escalón dentro de la vuelta.
        radio_tipico: solo para pasar el arco angular a mm.
    """
    avisos: List[str] = []
    dt_por_vuelta = altura_capa / max(altura, 1e-6)

    for i, toque in enumerate(toques, 1):
        if toque.tipo == "pintar":
            continue
        du, dv = _gradientes(toque)
        f = abs(toque.fuerza)
        if toque.tipo in ("suavizar", "aplanar"):
            # No son milímetros sino una fracción de lo que ya hay. Para el
            # chequeo se acota con lo que esa fracción puede llegar a mover: la
            # estructura o el relieve del patrón, que rara vez pasan de 5 mm.
            f = min(1.0, f) * 5.0

        # De una vuelta a la siguiente. El tope en `f` no es cosmético: el peso
        # va de 0 a 1, así que el radio no puede correrse más que la fuerza
        # entera entre dos vueltas. Sin ese tope, una caída 'plano' —que no
        # tiene derivada— reporta lo que dé la resolución del muestreo, o sea un
        # número inventado que crece si uno muestrea más fino.
        dr_vuelta = min(f * dv / toque.radio_t * dt_por_vuelta, f)
        etiqueta = f"toque #{i} ({toque.tipo} {toque.forma}" \
                   f"{', ' + toque.nota if toque.nota else ''})"
        if dr_vuelta > ancho_linea:
            avisos.append(
                f"⚠ {etiqueta}: el radio se corre {dr_vuelta:.2f} mm por vuelta y el "
                f"cordón mide {ancho_linea:.2f} mm — la vuelta nueva no apoya sobre la "
                f"anterior y la pared se abre. Bajá la fuerza a "
                f"{f * ancho_linea / dr_vuelta:.2f} mm"
                + (" o cambiá la caída: con 'plano' el borde es un escalón y agrandar "
                   "el radio no lo suaviza."
                   if toque.caida == "plano" else
                   f" o subí radio_t a {toque.radio_t * dr_vuelta / ancho_linea:.3f}.")
            )
        elif dr_vuelta > 0.6 * ancho_linea:
            solape = 100 * (1 - dr_vuelta / ancho_linea)
            avisos.append(
                f"• {etiqueta}: {dr_vuelta:.2f} mm por vuelta, {solape:.0f}% de solape. "
                f"Imprime, pero justo."
            )

        # Dentro de la vuelta: no despega nada, pero se ve facetado.
        arco = TAU / max(segmentos, 1)
        dr_punto = min(f * du / math.radians(toque.radio_grados) * arco, f)
        if dr_punto > ancho_linea:
            avisos.append(
                f"• {etiqueta}: salta {dr_punto:.2f} mm entre puntos vecinos de la misma "
                f"vuelta. No despega, pero se va a ver facetado; subí --segmentos o usá "
                f"una caída que no sea 'plano'."
            )

        # Un toque más angosto que el paso angular se cae entre las muestras.
        if math.radians(toque.radio_grados) < 2 * arco:
            avisos.append(
                f"⚠ {etiqueta}: mide {toque.radio_grados:.1f}° de radio y el generador "
                f"muestrea cada {math.degrees(arco):.1f}° — el toque cae entre dos puntos "
                f"y aparece y desaparece. Subí --segmentos o agrandá el toque."
            )
    return avisos


_RAMPA_FUERA = " ·-=+*#@"
_RAMPA_DENTRO = " ,:;coO0"


def rasterizar(deform: Deformacion, escala: float, ancho: int = 96,
               alto: int = 32) -> str:
    """
    Dibuja la deformación desenrollada, con SIGNO.

    Dos rampas y no una: lo que sale y lo que se mete son cosas distintas y un
    solo degradé las confunde justo en el caso que importa, que es un toque al
    lado de otro de signo contrario. La rampa va en raíz, no lineal: si no, un
    detalle diez veces más chico que el toque más grande no se ve nunca.
    """
    filas: List[str] = []
    for f in range(alto):
        t = 1.0 - f / (alto - 1)
        fila = []
        for c in range(ancho):
            v = deform(c / ancho * TAU, t)
            # Raíz y no lineal: en una misma pieza conviven un jalón de 3 mm y
            # una textura de 0.25 mm, y en escala lineal la textura cae entera
            # en el primer escalón de la rampa, o sea desaparece.
            n = min(1.0, abs(v) / escala) ** 0.5
            rampa = _RAMPA_FUERA if v >= 0 else _RAMPA_DENTRO
            fila.append(rampa[min(len(rampa) - 1, int(n * len(rampa)))])
        filas.append("".join(fila))
    return "\n".join(filas)


def _cli() -> None:
    """
    Ver y revisar un archivo de toques sin generar gcode:

        python -m lamparas.modelado toques.json
        python -m lamparas.modelado toques.json --altura 150 --ancho-linea 1.2
    """
    import argparse

    p = argparse.ArgumentParser(prog="lamparas.modelado", description=_cli.__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivo")
    p.add_argument("--altura", type=float, default=150.0)
    p.add_argument("--altura-capa", type=float, default=0.4)
    p.add_argument("--ancho-linea", type=float, default=1.2)
    p.add_argument("--segmentos", type=int, default=360)
    p.add_argument("--cols", type=int, default=96)
    p.add_argument("--filas", type=int, default=32)
    args = p.parse_args()

    try:
        toques = leer(args.archivo)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        p.error(str(e))

    print(f"{len(toques)} toque(s) en {args.archivo}")
    for i, t in enumerate(toques, 1):
        sim = f", x{t.simetria} alrededor del eje" if t.simetria > 1 else ""
        print(f"  #{i} {t.tipo:9s} {t.forma:9s} en {t.angulo:6.1f}° t={t.t:.2f}  "
              f"radio {t.radio_grados:.0f}°/{t.radio_t:.3f}  fuerza {t.fuerza:+.2f} mm{sim}"
              + (f"  — {t.nota}" if t.nota else ""))

    d = deformacion(toques)
    # La escala sale de lo que el campo REALMENTE vale, no del `fuerza` más
    # grande: una textura de 0.8 mm al lado de un jalón de 3 mm nunca llega a
    # su fuerza nominal (la modula el ruido) y con la otra escala no se ve.
    escala = max(
        (abs(d(c / args.cols * TAU, 1 - f / (args.filas - 1)))
         for f in range(args.filas) for c in range(args.cols)),
        default=1.0,
    )
    escala = max(escala, 0.001)
    print(f"\ndesenrollado (0°..360°), base abajo · '#' sale, 'O' se mete, "
          f"escala ±{escala:.2f} mm")
    print(rasterizar(d, escala, ancho=args.cols, alto=args.filas))

    avisos = revisar(toques, args.altura, args.altura_capa, args.ancho_linea,
                     args.segmentos)
    print()
    if avisos:
        for a in avisos:
            print(a)
    else:
        print(f"Sin avisos para {args.altura:g} mm de alto, capa {args.altura_capa:g} mm, "
              f"cordón {args.ancho_linea:g} mm.")


if __name__ == "__main__":
    _cli()
