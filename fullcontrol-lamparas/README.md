# fullcontrol-lamparas

Lámparas paramétricas impresas en 3D, generadas escribiendo G-code directamente
con [FullControl](https://github.com/FullControlXYZ/fullcontrol).

Pensado para una **Bambu Lab A1 con boquilla de 0.8 mm**, imprimiendo en modo
vaso (spiral) con capas de 0.4 mm.

---

## ⚠️ AVISO IMPORTANTE ANTES DE IMPRIMIR

El G-code que sale de acá **ya incluye start y end gcode para la A1**
(`lamparas/impresoras.py`), así que es imprimible tal cual. Pero esa secuencia
**la escribí a mano con comandos estándar, NO es el start gcode de fábrica de
Bambu Studio.**

Qué **sí** hace:

- calentar cama y boquilla, y esperar
- homing (`G28`)
- nivelación de cama (`G29`) — se puede desactivar con `--sin-nivelacion`
- dos líneas de purga en el borde frontal de la cama, con retracción y salto de Z
- ventilador de capa
- al terminar: retraer, separar la boquilla, adelantar la cama, apagar todo

Qué **no** hace (y sí hace Bambu Studio):

- nada de AMS / cambio de filamento
- calibración de flujo, de linear advance ni compensación de vibraciones
- la rutina de limpieza de boquilla propia de la A1

**Lo más seguro es usar el start/end gcode real de tu A1.** Se saca de Bambu
Studio (*Ajustes de impresora → Machine G-code → Machine start/end G-code*), se
guarda en un archivo y se pasa así:

```bash
python -m lamparas.twist --start-gcode a1_start.gcode --end-gcode a1_end.gcode
```

En ese caso las temperaturas las fija tu start gcode, no el nuestro.

**Siempre**, uses el bloque que uses: previsualizá el `.gcode` antes de
imprimir (ver más abajo, o un visor tipo [gcode.ws](https://gcode.ws)) y
**quedate mirando la primera capa**.

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
```

El `.gcode` queda en `output/` (esa carpeta está en `.gitignore`).

---

## Cómo ver cómo quedaría

```bash
# genera el .gcode Y un HTML 3D interactivo en output/
python -m lamparas.twist --preview

# solo la previsualización, sin exportar gcode (para iterar rápido)
python -m lamparas.twist --solo-preview --n-ondas 12 --amplitud 8 --vueltas-twist 4

# visor propio de FullControl: simula el ancho y alto real de cada línea
python -m lamparas.twist --plot
```

`--preview` deja un `output/<nombre>.html` autocontenido (plotly embebido, no
necesita internet) que se abre con doble clic en cualquier navegador y se puede
rotar y hacer zoom. Dibuja también el contorno de la cama, así se ve de una si
la pieza entra. Funciona sin entorno gráfico, así que sirve por SSH o en un
contenedor.

`--plot` abre el visor de FullControl, que es más fiel (simula el grosor real
de la línea extruida) pero mucho más pesado y necesita un navegador en la misma
máquina.

Desde código:

```python
from lamparas.preview import guardar_html
from lamparas.twist import pasos_lampara_twist

pasos = pasos_lampara_twist(n_ondas=12, amplitud=8)
print(guardar_html(pasos, "prueba_12_lobulos"))
```

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
  comun.py       # Perfil de impresión, generador de espiral, exportación de gcode
  impresoras.py  # start/end gcode de la A1 (o el tuyo, desde un archivo)
  preview.py     # previsualización HTML 3D
  twist.py       # lámpara ondulada con twist progresivo
output/          # .gcode y .html generados (gitignored)
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
