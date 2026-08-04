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

### Cómo se lo pasás a la impresora

Por **microSD**: archivo en la raíz de la tarjeta (no en subcarpetas), nombre
alfanumérico sin acentos, y desde la pantalla de la A1 *File* → seleccionarlo →
*Print*.

No sirve mandarlo desde Bambu Studio ni desde Orca Slicer: los dos son slicers,
esperan una malla y para Bambu usan el mismo plugin de red que exige un `.3mf`
laminado por ellos. Un `.gcode` crudo lo rechazan. Donde Orca sí sirve es como
**visor**: abrí el archivo generado y revisá capa por capa antes de imprimir.

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

**Para entender cómo se escribe un diseño en FullControl** hay un tutorial
corto en [`docs/fullcontrol.md`](docs/fullcontrol.md): el modelo de la lista de
pasos, cómo se calcula la extrusión, los helpers de geometría y los errores
típicos.

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

### Loop en vivo con gcode-preview (VS Code)

La extensión que está en `../../gcode-preview` puede quedarse mirando `output/`
y previsualizar siempre el gcode más nuevo. Sirve para iterar parámetros sin
regenerar un HTML de 4 MB por vuelta, y trae dos cosas que el preview de acá no
tiene: **slider de capas** y **mapa de calor de voladizo** medido sobre el
recorrido real.

1. En VS Code, click derecho sobre `output/` → **"G-code: Watch Folder
   (preview newest)"**. La carpeta puede no existir todavía.
2. `python -m lamparas.bowls celosia --altura 70` — el panel se actualiza solo.
3. Cambiás parámetros, volvés a correr. Cada corrida reemplaza la vista.

Por eso `guardar_gcode()` escribe de forma atómica (`.gcode.tmp` + rename): el
watcher se despierta con el primer byte y si no, leería un archivo a medio
escribir.

**Ojo con el mapa de calor en los calados.** Su métrica es "¿hay pared una capa
más abajo, a menos de 3 mm?", así que una `celosia` le va a salir roja entera —
y es exactamente lo que el diseño busca. Para el calado el chequeo que vale es
el `_verificar_apoyo()` de `comun.py`, que pide contacto en *algún* punto de la
vuelta y no en todos. En las siluetas lisas y en `cesta`/`malla`/`tramado` sí
coinciden las dos mediciones.

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
  bowls/         # bowls con patrones tejidos
    siluetas.py  # formas de la pared: bol, copa, platillo, campana
    cesta.py     # trenzado de cestería
    malla.py     # malla fina de rombos
    celosia.py   # calado real, con agujeros pasantes
    tramado.py   # entramado diagonal
output/          # .gcode y .html generados (gitignored)
requirements.txt
```

---

## Bowls con patrones tejidos

Cuatro patrones, cuatro siluetas, se combinan entre sí. Ninguno se puede hacer
con un slicer: el patrón cambia dentro de cada vuelta y de una vuelta a la otra.

```bash
python -m lamparas.bowls malla --preview
python -m lamparas.bowls cesta --altura 70 --radio-boca 85 --p n_tiras=20
python -m lamparas.bowls celosia --silueta platillo --radio-max 90 --solo-preview
python -m lamparas.bowls tramado --p torsion=14 --p amplitud=2.5 --nombre bowl_diagonal
python -m lamparas.bowls --help
```

| patrón | qué hace | cómo |
|---|---|---|
| `cesta` | tejas horizontales alternadas, tipo cestería | onda radial cuya fase se invierte entre bandas de capas, con envolvente seno |
| `malla` | malla fina de rombos | onda radial con **medio lóbulo de más por vuelta**: las crestas de una vuelta caen en los valles de la anterior |
| `celosia` | calado real, con agujeros pasantes | la **Z** ondula dentro de la vuelta; las vueltas se tocan solo en los nodos |
| `tramado` | entramado diagonal trenzado | dos familias de hélices opuestas combinadas con `max()`, así una tira pasa por encima de la otra |
| `rizos` | bucles que sobresalen, tipo candelero "Dream of Glow" | trocoide: el trazo **retrocede** en ángulo y cierra un bucle, en vez de solo ondular |

Los parámetros propios de cada patrón van con `--p clave=valor` (repetible) y
están documentados en el `construir()` de cada módulo.

**Siluetas** (`--silueta`): `bol` (por defecto), `copa` (cónica), `platillo`
(panza y boca cerrada), `campana`, `candelero` (acampanado con cuello). Se
ajustan con `--radio-base`, `--radio-boca` y `--radio-max`.

El candelero de las referencias sale así:

```bash
python -m lamparas.bowls rizos --silueta candelero --altura 90 \
       --radio-base 45 --radio-boca 14 --preview
```

### Rizos: qué hace falta para que sea un bucle y no una onda

Una onda entra y sale del radio pero el ángulo siempre avanza. Para que el
trazo se cierre sobre sí mismo tiene que **retroceder** en ángulo, y eso lo da
`funcion_dangulo` en `generar_pieza()`. La curva es una trocoide, y solo cierra
el bucle si la amplitud supera `radio / n_rizos`. Por debajo de eso queda una
pared ondulada; el módulo lo calcula y avisa.

### Ancho de línea

`--ancho-linea` está separado de `--boquilla`: la boquilla es el hardware, el
ancho es cuánto plástico se empuja. Se puede pedir hasta ~2x la boquilla para
una pared más gruesa y opaca. Si no se especifica, se usa el de la boquilla.

### Dos cosas que estos diseños resuelven y conviene entender

**Base sólida.** Un bowl necesita piso, y el modo vaso es un trazo continuo sin
saltos. `generar_pieza(base_solida=True)` rellena el fondo con una espiral de
Arquímedes desde el centro hacia afuera y sigue de largo con la pared, sin
cortar la extrusión. Con `--sin-base` queda abierto abajo (pantalla de lámpara).

**Paso vertical de la celosía.** Es el detalle no obvio del calado. Si la Z
ondula ±0.7 mm pero la pieza sube solo 0.4 mm por vuelta, la cresta de una
vuelta queda 1 mm *por debajo* del valle de la anterior: la boquilla vuelve a
bajar sobre material ya impreso. Por eso `celosia` sube `2 * amplitud_z` por
vuelta en vez de una altura de capa, y usa `solape` para dejar una mordida
controlada de ~0.2 mm en los nodos, que es lo que los suelda.

## Cambiar de color sin purgar

La idea: parar, meter el filamento nuevo y seguir. Lo que quedaba del color
viejo en la zona de fusión sale mezclado con el nuevo durante las primeras
vueltas, y esa mezcla es el efecto.

```bash
# pausa manual a 20 y a 40 mm: la impresora para, cambiás el rollo y reanudás
python -m lamparas.bowls cesta --altura 60 --cambio 20 --cambio 40

# cambio de slot del AMS (SIN VERIFICAR, leer abajo)
python -m lamparas.bowls cesta --altura 60 --cambio-ams 20:1
```

**`--cambio` usa `M400 U1`**, el comando nativo de pausa de Bambu (M600 no
existe en estas máquinas). No toca el AMS, no purga nada y no depende de ningún
comando propietario. Es la opción segura, y para dos o tres colores por zonas
es todo lo que hace falta.

**`--cambio-ams` no está verificado.** Bambu nunca documentó los comandos del
AMS; lo que emite es el patrón `M620 S{slot}A` / `T{slot}` / `M621 S{slot}A`
que reconstruyó la comunidad. Para tener los comandos que tu firmware espera de
verdad, sacá el bloque real de un gcode de dos colores laminado por tu Bambu
Studio y pasalo por `colores.quitar_purga()`, que le saca el `M620.10` (el que
lleva la longitud de flush) y los movimientos que extruyen de más.

### Cuánta altura dura la mezcla

El color viejo no desaparece de golpe: hay que empujarlo fuera del bloque
caliente. Milímetros de filamento hasta que sale limpio, según la comunidad:

| transición | filamento | en un bowl de radio 55 |
|---|---|---|
| blanco → negro | 60–80 mm | **0.6 mm de altura** |
| gris → azul | ~48 mm | 0.4 mm |
| negro → blanco | 250–300 mm | **2.4 mm de altura** |

Tapar claro con oscuro es rápido; al revés cuesta cuatro veces más.
`colores.altura_de_mezcla(mm, radio)` lo calcula para tu geometría.

La consecuencia: **un cambio solo da entre 0.6 y 2.4 mm de mezcla**, o sea una
transición de borde suave, no un ombre. Para un degradado a lo largo de 40 mm
harían falta decenas de cambios encadenados (`colores.alturas_regulares()` los
reparte), con su costo en tiempo de máquina. Si lo que querés es un ombre
limpio, filamento gradiente de un solo rollo lo resuelve sin ningún cambio: en
modo vaso el color se mapea solo a la altura, porque la pieza es un trazo
continuo de abajo hacia arriba.

---

### Chequeos automáticos

`generar_pieza()` verifica tres cosas y avisa por consola. Miralas antes de
mandar a imprimir: no abortan la generación, solo avisan.

- **Cabe en la cama.** Radio máximo contra `Perfil.tamano_cama`.
- **Voladizo.** En modo vaso cada vuelta se apoya sobre la de abajo; si el radio
  crece más rápido que el ancho de línea por vuelta, la pared se descuelga. Se
  mide sobre la silueta lisa y avisa a partir de 45°; por encima de ~55° no
  esperes que salga. La silueta `platillo` es la más propensa: bajá
  `--radio-max` o subí `--altura` hasta que el aviso desaparezca.
- **Apoyo.** Que cada vuelta toque a la de abajo en *algún* punto. Una vuelta
  puede estar despegada casi entera —eso es justamente el calado— pero si en
  toda su longitud no hay un solo punto de contacto, se imprime en el aire.
  Este control es el que separa una celosía de un montón de anillos sueltos.

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
