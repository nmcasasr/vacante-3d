# Cómo funciona FullControl

Tutorial corto para entender el modelo de scripting, con las cosas que hay que
saber para tocar este repo sin romper nada.

---

## 1. Un diseño es una lista. Nada más.

No hay clases que heredar ni un motor que resolver. Un diseño de FullControl es
una lista de Python con objetos adentro, y esa lista **se recorre en orden**.
Cada objeto se traduce a gcode en el momento en que le toca.

```python
import fullcontrol as fc

pasos = []
pasos.append(fc.Printer(print_speed=1200))
pasos.append(fc.Point(x=10, y=10, z=0.4))
pasos.append(fc.Point(x=50, y=10, z=0.4))
```

Eso es todo el modelo mental. Si entendés que es una lista ordenada, entendiste
FullControl.

---

## 2. Hay dos tipos de paso: geometría y estado

**Geometría** es un solo objeto: `fc.Point`. Es a dónde va la boquilla.

**Estado** es todo lo demás, y no mueve nada: cambia cómo se van a interpretar
los `Point` que vengan *después*.

| paso de estado | qué cambia |
|---|---|
| `fc.Printer(print_speed=, travel_speed=)` | velocidades |
| `fc.Extruder(on=True/False)` | si los movimientos extruyen o son viajes |
| `fc.ExtrusionGeometry(area_model=, width=, height=)` | cuánto plástico por mm |
| `fc.Hotend(temp=, wait=)` / `fc.Buildplate(temp=, wait=)` | temperaturas |
| `fc.Fan(speed_percent=)` | ventilador |
| `fc.ManualGcode(text=)` | escupe texto crudo, para lo que no está modelado |
| `fc.StationaryExtrusion(volume=, speed=)` | extruir sin moverse (purgas) |
| `fc.PrinterCommand(id='home')` | comandos con nombre (`home`, `retract`, ...) |

---

## 3. El estado es pegajoso

Un paso de estado vale **desde que aparece hasta que otro lo cambie**. No hay
que repetirlo en cada punto.

```python
pasos.append(fc.Printer(print_speed=600))   # lento
pasos.append(fc.Point(x=10, y=10, z=0.4))   # va a 600
pasos.append(fc.Point(x=50, y=10, z=0.4))   # sigue a 600
pasos.append(fc.Printer(print_speed=2400))  # rápido de acá en adelante
pasos.append(fc.Point(x=50, y=50, z=0.4))   # va a 2400
```

Esto es lo que permite variar velocidad, ventilador o ancho de línea **dentro**
de una pieza: se meten pasos de estado en el medio de los puntos. Es
exactamente lo que un slicer hace, y lo que en este repo todavía no hacemos
(ver "Lo que este repo no hace todavía", al final).

---

## 4. La E no se escribe: se calcula

Esta es la parte que más confunde y la que más consecuencias tiene.

Vos nunca ponés cuánto extruir. FullControl mide la distancia entre el punto
anterior y el actual, la multiplica por el área de sección que fijó el último
`ExtrusionGeometry`, y de ahí saca los milímetros de filamento:

```
E = distancia × área_de_sección / área_del_filamento
```

Tres consecuencias prácticas:

**a) El área depende del `area_model` que elijas**, y no da lo mismo:

| modelo | fórmula | con 0.8 × 0.4 |
|---|---|---|
| `rectangle` | `w × h` | 0.3200 mm² |
| `stadium` | `(w−h)×h + π(h/2)²` | 0.2857 mm² |
| `circle` | `π(d/2)²` | — |

`rectangle` extruye **12% más** que `stadium` para la misma línea. `stadium`
modela la forma real de un cordón aplastado (rectángulo con los costados
redondeados); `rectangle` sobrestima. Este repo usa `rectangle`, o sea que va
levemente sobre-extruido — a propósito, porque en pared simple ayuda a que las
vueltas suelden y a que no queden poros. Si te queda muy gordo, cambiá a
`stadium` en `pasos_iniciales()` de `comun.py`.

**b) El primer punto necesita un punto anterior.** Si no hay ninguno, no hay
distancia que medir y revienta. Por eso todos los diseños de acá arrancan con
un viaje con el extrusor apagado:

```python
pasos.append(fc.Extruder(on=False))
pasos.append(primer_punto)     # viaje, no extruye
pasos.append(fc.Extruder(on=True))
```

**c) Más puntos no es más plástico.** Podés subdividir una curva en 500 puntos
en vez de 100: cada tramo extruye menos y el total es el mismo. La resolución
solo cambia cuán suave queda la curva y cuánto pesa el archivo.

---

## 5. `transform()`: la lista se convierte en algo

```python
gcode = fc.transform(pasos, 'gcode', fc.GcodeControls(printer_name='generic'))
fc.transform(pasos, 'plot', fc.PlotControls(style='line'))
```

Mismo diseño, dos salidas. `'gcode'` devuelve el texto (y lo guarda si le pasás
`save_as`); `'plot'` abre un visor 3D.

---

## 6. El perfil de impresora envuelve tu diseño

`printer_name` no es cosmético. FullControl importa un módulo de
`fullcontrol/devices/community/singletool/` y ese módulo arma la lista final:

```
starting_procedure_steps  +  primer  +  TU DISEÑO  +  ending_procedure_steps
```

- `generic` casi no aporta nada (un comentario y `M83`). Es el que usamos, y el
  start/end real lo inyectamos nosotros como `ManualGcode` desde
  `lamparas/impresoras.py`.
- `bambulab_x1` sí trae una rutina completa, pero es de X1 y no de A1.
- El **primer** es la rutina de purga: `'no_primer'`, `'travel'`,
  `'front_lines_then_xy'`, etc. Usamos `no_primer` porque purgamos en nuestro
  propio start gcode.

---

## 7. Los helpers de geometría

No hace falta escribir senos y cosenos a mano para las formas comunes.
Devuelven listas de `Point`, así que se concatenan con `extend()`:

```python
fc.circleXY(centro, radio, angulo_inicial, segments=100, cw=False)
fc.helixZ(centro, radio_ini, radio_fin, angulo_ini, n_turns, pitch_z, segments)
fc.rectangleXY(...)   fc.ellipseXY(...)   fc.polygonXY(...)   fc.spiralXY(...)
fc.arcXY(...)         fc.elliptical_arcXY(...)
fc.squarewaveXY(...)  fc.sinewaveXYpolar(...)  fc.trianglewaveXYpolar(...)
fc.segmented_line(p1, p2, segments)
fc.travel_to(punto)          # atajo de extruder off / punto / extruder on
fc.move(geometria, fc.Vector(z=0.4), copy=True, copy_quantity=50)
fc.reflectXY(...)   fc.ramp_xyz(...)   fc.distance(p1, p2)   fc.path_length(...)
```

`fc.move(..., copy=True)` es el atajo clásico para apilar capas: hacés una
vuelta y la copiás 50 veces subiendo 0.4 mm.

**Este repo casi no los usa** y es a propósito: nuestras formas necesitan que
el radio y la Z sean función del ángulo *y* de la altura al mismo tiempo, y eso
no lo cubre ningún helper. Por eso `comun.py` calcula punto por punto.

---

## 8. Ejemplo mínimo completo

Un vaso cilíndrico en modo espiral, de punta a punta:

```python
import math
import fullcontrol as fc

ALTURA_CAPA, N_CAPAS, SEGMENTOS, RADIO = 0.4, 50, 64, 20
CX, CY = 128, 128

# 1. estado inicial
pasos = [
    fc.ExtrusionGeometry(area_model='stadium', width=0.8, height=ALTURA_CAPA),
    fc.Printer(print_speed=1200, travel_speed=6000),
    fc.Fan(speed_percent=100),
]

# 2. geometría: un círculo por vuelta, con la Z subiendo dentro de la vuelta
puntos = []
for capa in range(N_CAPAS):
    for seg in range(SEGMENTOS + 1):          # +1 para cerrar la vuelta
        fraccion = seg / SEGMENTOS
        angulo = fraccion * 2 * math.pi
        z = (capa + 1 + fraccion) * ALTURA_CAPA
        puntos.append(fc.Point(x=CX + RADIO * math.cos(angulo),
                               y=CY + RADIO * math.sin(angulo),
                               z=z))

# 3. viaje inicial sin extruir: hace falta un punto previo antes de la primera
#    extrusión, si no FullControl no puede medir la distancia
pasos += [fc.Extruder(on=False), puntos[0], fc.Extruder(on=True)] + puntos[1:]

# 4. a gcode
gcode = fc.transform(pasos, 'gcode', fc.GcodeControls(
    printer_name='generic',
    initialization_data={'primer': 'no_primer'},
), show_tips=False)
open('vaso.gcode', 'w').write(gcode)
```

Fijate que el modo vaso no es un ajuste: es que la Z sube un poquito en cada
segmento en vez de saltar al final de la vuelta.

---

## 9. Cómo se mapea a este repo

| concepto de FullControl | dónde está acá |
|---|---|
| pasos de estado iniciales | `pasos_iniciales()` en `comun.py` |
| generación de los `Point` | `generar_pieza()` en `comun.py` |
| forma de la pieza | `funcion_radio(angulo, t)` de cada diseño |
| `ManualGcode` de start/end | `lamparas/impresoras.py` |
| `transform(..., 'gcode')` | `a_gcode()` en `comun.py` |
| `transform(..., 'plot')` | `previsualizar()` en `preview.py` |

El `angulo` que reciben las funciones de forma es **acumulado** a lo largo de
toda la espiral, no reiniciado en cada vuelta. Eso permite frecuencias de medio
lóbulo (`n + 0.5`), que invierten el patrón solo de una vuelta a la otra sin
dejar salto en la costura. Es el truco que teje la malla y la celosía.

---

## 10. Tres errores típicos

1. **Primera capa en `z = 0`.** La boquilla queda apoyada contra la cama. Va en
   `z = altura_capa`.
2. **Pieza centrada en `(0, 0)`.** El origen de la A1 es la esquina frontal
   izquierda; media pieza cae en coordenadas negativas. Centrala en `(128, 128)`.
3. **Cambiar la Z sin cambiar el paso vertical.** Si hacés que la Z ondule
   dentro de la vuelta con amplitud A, la pieza tiene que subir más de 2A por
   vuelta o la vuelta nueva termina *por debajo* de la anterior y la boquilla
   vuelve a bajar sobre material ya impreso. Es exactamente el bug que tuvo la
   celosía de este repo.

---

## Lo que este repo no hace todavía

El estado es pegajoso y se puede cambiar en cualquier punto del recorrido, pero
hoy fijamos velocidad y ventilador **una sola vez** y no los tocamos más: un
`.gcode` de 35.000 líneas tiene exactamente 2 `M106` (encender y apagar) y una
sola `F` de impresión. Un slicer, en cambio, apaga el ventilador en las
primeras capas para que la pieza agarre, lo sube después, y lo dispara al
máximo en puentes y voladizos.

Se arregla metiendo `fc.Fan(...)` y `fc.Printer(...)` entre los puntos, en las
capas donde corresponda.
