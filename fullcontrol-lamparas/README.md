# fullcontrol-lamparas

Lámparas paramétricas impresas en 3D, generadas escribiendo G-code directamente
con [FullControl](https://github.com/FullControlXYZ/fullcontrol).

Pensado para una **Bambu Lab A1 con boquilla de 0.8 mm**, imprimiendo en modo
vaso (spiral) con capas de 0.4 mm.

---

## ⚠️ AVISO IMPORTANTE ANTES DE IMPRIMIR

**El G-code que genera este repo NO es imprimible tal cual.**

FullControl emite únicamente los movimientos de la pieza. Con el perfil
`generic` que usamos, el archivo **no incluye**:

- homing (`G28`)
- nivelación de cama / mesh bed leveling
- carga de filamento ni purga (usamos `primer: 'no_primer'`)
- el resto del *start gcode* propio de la A1 (AMS, calibración de flujo, etc.)
- el *end gcode* (retracción final, bajar cama, apagar temperaturas y motores)

Lo único que sí emite son los `M104/M140/M109/M190` de temperatura, el `M106`
de ventilador y `M83` (extrusión relativa).

**Qué hacer antes de mandar a imprimir:**

1. Abrí Bambu Studio / Orca, poné el mismo filamento y boquilla, y copiá el
   *Machine start G-code* y el *Machine end G-code* del perfil de la A1.
2. Pegá el start gcode **al principio** del `.gcode` generado y el end gcode
   **al final**.
3. Revisá que no queden temperaturas duplicadas o en conflicto entre el start
   gcode de Bambu y las líneas que genera FullControl (si el start gcode de
   Bambu ya fija las temperaturas, borrá las de FullControl).
4. Previsualizá el resultado antes de imprimir (`--plot`, o un visor de gcode
   tipo [gcode.ws](https://gcode.ws)) y **quedate mirando la primera capa**.

Las coordenadas se centran por defecto en `(128, 128)`, el centro de la cama de
256×256 mm de la A1. Si cambiás de impresora, ajustá `Perfil.centro` y
`Perfil.tamano_cama` (el generador avisa por consola si la pieza no entra).

---

## Qué es FullControl

FullControl es una librería de Python que permite **diseñar la trayectoria de
impresión directamente**, sin pasar por un modelo 3D ni por un slicer.

El flujo normal es `CAD → STL → slicer → gcode`: el slicer decide cómo rellenar
el sólido y uno solo controla parámetros globales. Con FullControl uno describe
una lista de "pasos" (puntos, cambios de velocidad, temperaturas, extrusor
on/off) y esa lista *es* el recorrido de la boquilla, punto por punto.

Para lámparas en modo vaso esto es ideal: la pieza es literalmente una sola
espiral continua, así que definirla como una función matemática del ángulo y la
altura es mucho más directo (y más fácil de parametrizar) que modelarla en CAD.

La contrapartida es la del aviso de arriba: al no haber slicer, tampoco hay
start/end gcode de la impresora.

---

## Instalación

```bash
git clone <este-repo> fullcontrol-lamparas
cd fullcontrol-lamparas

python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Cómo correr un script

Cada diseño vive en `lamparas/` y se puede ejecutar como módulo:

```bash
# valores por defecto (radio 40, altura 150, 6 lóbulos, 1.5 vueltas de twist)
python -m lamparas.twist

# lámpara más ancha, más baja y con más torsión
python -m lamparas.twist --radio-base 55 --altura 120 --n-ondas 8 \
                         --amplitud 6 --vueltas-twist 3 --nombre lampara_alta

# ver todas las opciones
python -m lamparas.twist --help

# previsualización interactiva en el navegador (requiere plotly)
python -m lamparas.twist --plot
```

El `.gcode` queda en `output/` (esa carpeta está en `.gitignore`).

También se puede usar como librería:

```python
from lamparas import Perfil
from lamparas.twist import generar_lampara_twist

perfil = Perfil(diametro_boquilla=0.6, altura_capa=0.3, temp_boquilla=215)

gcode = generar_lampara_twist(
    radio_base=45,
    altura=180,
    n_ondas=10,
    amplitud=5,
    vueltas_twist=2.0,
    perfil=perfil,
    nombre="lampara_10_lobulos",
)
```

---

## Estructura del proyecto

```
lamparas/
  comun.py      # setup de impresora, generador de espiral, exportación de gcode
  twist.py      # lámpara ondulada con twist progresivo
output/         # .gcode generados (gitignored)
requirements.txt
```

## Cómo agregar una forma nueva

Todo lo compartido (estado inicial, construcción de la espiral, exportación)
está en `lamparas/comun.py`. Un diseño nuevo solo tiene que definir **una
función de radio** y delegar el resto:

```python
# lamparas/helicoidal.py
import math
from .comun import Perfil, a_gcode, generar_lampara, guardar_gcode

def generar_lampara_helicoidal(radio_base=40, altura=150, conicidad=0.3, nombre="helicoidal"):
    def radio(angulo, t):
        # `angulo` en radianes (0..2π dentro de cada vuelta)
        # `t` va de 0.0 en la base a 1.0 en el tope
        return radio_base * (1 - conicidad * t)

    pasos = generar_lampara(radio, altura=altura)
    gcode = a_gcode(pasos)
    guardar_gcode(gcode, nombre)
    return gcode
```

`generar_lampara()` se encarga de cerrar cada vuelta, de la rampa de Z del modo
vaso, de arrancar con la primera capa plana para adherencia y de hacer el viaje
inicial con el extrusor apagado.

## Notas de impresión (modo vaso)

- **Ancho de extrusión = diámetro de boquilla (0.8 mm)**: pared de una sola
  línea, translúcida, que es justo lo que se busca en una lámpara.
- **Capa de 0.4 mm** con boquilla de 0.8: relación 1:2, marca bien las líneas.
- `capas_base=1` deja la primera vuelta plana (sin rampa de Z) para mejorar la
  adherencia antes de empezar a espiralar.
- La primera capa se imprime a `z = altura_capa`, nunca a `z = 0`.
- Sin retracciones ni cambios de capa: el modo vaso es un único trazo continuo.
