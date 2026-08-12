# Plan: esculpir la pieza desde el preview

Objetivo: jalar, empujar y texturizar la superficie con el mouse sobre el
preview, y que eso salga en el G-code. Sin cortar, sin agujeros, sin mallas.

## La decisión que sostiene todo lo demás

**El G-code no se edita nunca.** Un G-code editado ya no tiene parámetros: la
siguiente corrida del generador tira el cambio, y habría que recalcular la
extrusión de cada punto movido a mano. Los sliders ya funcionan así — mueven un
parámetro y **regeneran** — y las herramientas de modelado son lo mismo: cada
pincelada es un dato, no una edición.

El gancho ya existe. `bowls/pasos_bowl` acepta `deformacion=(angulo, t) -> mm` y
la suma al radio del patrón (`bowls/__init__.py:93`). Todo el plan consiste en
alimentar esa función desde el mouse.

Como la deformación es **radial**, la pared sigue siendo una espiral cerrada:
el modo vaso sobrevive, no hay nada que reparar y no existe la posibilidad de
abrir un hueco. Es exactamente el motivo de limitarse a deformar.

## Modelo de datos: la pincelada

Un archivo `nombre.toques.json` al lado del `.gcode` y del `.params.json`:

```json
{ "version": 1,
  "simetria": 1,
  "toques": [
    { "tipo": "jalar", "angulo": 1.24, "t": 0.62,
      "radio_ang": 0.45, "radio_t": 0.07,
      "fuerza": 2.5, "caida": "gauss" },
    { "tipo": "textura", "angulo": 3.9, "t": 0.30,
      "radio_ang": 0.8, "radio_t": 0.15,
      "fuerza": 0.6, "escala": 14, "semilla": 3 }
  ] }
```

Archivo y no flags: cuarenta pinceladas en una línea de comando son
inmanejables. Se pasa con `--toques archivo.json`, que sí entra en el `args` de
la receta y por lo tanto se versiona con ella.

**Coordenadas `(angulo, t)`, no `(x, y, z)`.** `t` es altura relativa, así que
si después mueves el slider de `altura` las pinceladas se estiran con la pieza
en vez de quedarse pegadas a una cota que ya no significa nada. Es una decisión
de intención de diseño, no de conveniencia.

## Lado Python: `lamparas/modelado.py`

```python
cargar(ruta) -> Deformacion        # suma de todas las pinceladas
_peso(toque, angulo, t) -> 0..1    # caída
```

- El ángulo **envuelve**: `Δa = (a - a0 + π) mod 2π - π`. Sin eso, una pincelada
  en 0° sale partida a la mitad.
- Caída gaussiana normalizada al radio: `w = exp(-2.3·((Δa/ra)² + (Δt/rt)²))`,
  cero fuera del elipsoide.
- Simetría radial N: se evalúa la misma pincelada en `a0 + 2πk/N`. Barato, y es
  lo que hace que una pieza decorativa se vea intencional en tres brochazos.

Tipos, en orden de valor:

| tipo | qué hace | cómo |
|---|---|---|
| `jalar` / `empujar` | el 80% del uso | `+fuerza·w` / `-fuerza·w` |
| `textura` | ruido local | reusa `estructura._ruido`, enmascarado por `w` |
| `suavizar` | apaga la estructura ahí | `-w·estructura(a,t)` |
| `aplanar` | lleva a un radio objetivo | `w·(objetivo - r(a,t))` |

`textura` y `suavizar` no traen código de ruido nuevo: `estructura.py` ya tiene
el fBm periódico en ángulo.

## Lado preview: pintar sobre la pieza

**Picking.** No contra las líneas — contra una **cáscara de revolución
invisible** construida con el radio medio por capa. Ese radio ya se calcula:
`computeRelief` ajusta un círculo por mínimos cuadrados a cada capa
(`media/main.js`), con 0.006 mm de error. La cáscara es de ~375×64 vértices,
existe siempre (aunque el modo sólido esté apagado) y da `(angulo, t)` directo
desde el punto de impacto.

**Dos niveles de respuesta, a propósito:**

1. **Fantasma, instantáneo.** Mientras arrastras, JS deforma *la cáscara* — no
   el recorrido real — y la muestra translúcida. Es un display de intención a
   60 fps.
2. **Verdad, al soltar.** Se escribe el `.toques.json` y se regenera con
   Python, igual que los sliders (borrador `--segmentos 120`, ~1.8 s + ~1 s de
   parseo).

El fantasma nunca finge ser el recorrido real, así que si la caída en JS se
desvía un pelo de la de Python no importa: desaparece en cuanto llega el
G-code de verdad. Eso ahorra tener que mantener dos implementaciones idénticas
del mismo campo.

**Panel de pinceladas.** Lista con cada toque, su fuerza editable y un botón de
borrar; deshacer es `pop()` sobre el arreglo. Poder retocar la fuerza *después*
vale más que acertar durante el arrastre.

## Lo que hay que vigilar

1. **Δradio por vuelta < ancho de cordón**, o las paredes no pegan. Es el mismo
   límite que ya verifica `comun._verificar_voladizo`, pero ahí es global y una
   pincelada lo rompe localmente: 5 mm de fuerza en `radio_t=0.02` de una pieza
   de 150 mm son 3 mm de alto ≈ 7 vueltas ≈ 0.7 mm por vuelta, al borde con
   cordón de 1.2. **El pincel tiene que calcular la pendiente en vivo y avisar
   o topar la fuerza**, no dejar que salga un G-code que no se puede imprimir.
2. **El borrador miente con pinceladas finas.** `--segmentos 120` son 3° por
   muestra; una pincelada más angosta que eso aparece y desaparece. Hay que
   topar `radio_ang` por debajo a unos pocos pasos del borrador, o subir los
   segmentos cuando hay toques.
3. **Voladizo.** Jalar hacia afuera rápido lo genera. El modo `overhang` del
   preview ya lo mide; conviene saltar a él solo cuando una pincelada lo empuje
   sobre 45°.

## Etapas

Todas hechas.

1. **`modelado.py` + `--toques`** — más `formas.py`, la librería de pinceles:
   nueve formas × cinco caídas, compartidas por máscara y deformación. Se puede
   iterar sin abrir VS Code: `python -m lamparas.modelado toques.json` dibuja el
   desenrollado en ASCII y corre los chequeos.
2. **Cáscara de picking** — `ajusteDeCapas()` se sacó de `computeRelief` y ahora
   la usan los dos. La cáscara es un sólido de revolución con el radio medio de
   cada vuelta, con `material.visible = false`: no se dibuja pero sí se
   raycastea, porque `THREE.Mesh.raycast` mira la geometría y no si el material
   pinta.
3. **Jalar y empujar** — clic y arrastrar: arriba jala, abajo empuja. El signo
   sale del gesto, no de un selector. Fantasma a 60 fps mientras se arrastra,
   Python al soltar.
4. **Panel de toques** — lista con ±0.25 mm por click, borrar, deshacer,
   limpiar. Al seleccionar un toque, los controles del pincel pasan a editarlo.
5. **Resto de herramientas** — `textura`, `suavizar`, `aplanar` y simetría
   radial. `aplanar` necesita ver el radio de abajo; se marca con
   `necesita_patron` y `pasos_bowl` se lo enchufa, que es el único punto donde
   el patrón ya está armado y todavía no se generó nada.
6. **Aviso de pendiente en vivo** — mm por vuelta contra el ancho del cordón,
   mientras se arrastra.

## Dos cosas que salieron distinto de lo planeado

**`aplanar` con caída gaussiana no aplana.** La corrección en el centro es cero
por definición (ahí está el radio objetivo) y la gaussiana solo pesa fuerte en
el centro: el resultado medido era una corrección de 0.44 mm donde tenía que ser
2 mm. Por eso existe la caída **`meseta`** —plana hasta 0.6 del radio y suave
en el borde—, que es la que esa herramienta quiere. Con ella el radio queda
clavado en 42.79 mm de t=0.42 a t=0.58 mientras el lado intacto va de 44.6 a
40.2: una cara plana en un huevo.

**`t` no es "z sobre altura".** La base sólida ocupa unas capas abajo y las de
transición suben menos que las demás. Adivinarlo desde el gcode pone los toques
unos milímetros más arriba de donde se los pintó. Ahora `generar_pieza` deja la
tabla exacta (`ULTIMO_MAPEO`) y la receta la lleva en `mapeo.z_capa`; el preview
invierte por búsqueda binaria.
