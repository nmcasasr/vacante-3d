# Florero Kadzi — qué es cada archivo

**La carpeta dice CÓMO está hecho. El nombre del archivo dice CON QUÉ NÚMEROS.**

    hoja_fondo5_pico9mm      ->  el pico del fondo mide 5 mm, el de la figura 9

Todo es cordón **1.2 mm**, capa 0.4, modo vaso, Ø50 salvo donde diga.
Las recetas están en `recetas/florero-kadzi/`, con el mismo árbol.

---

## Las tres maneras de hacer el grumo

Es la decisión que separa las carpetas, y sale de una sola regla física: **en
modo vaso cada vuelta se apoya en la de abajo, y la boquilla deja un cordón de
1.2 mm.** Si la vuelta nueva sale más de eso hacia afuera, esa punta queda al
aire.

### `grumo-crece` — el grumo sale de a poco

Después de las vueltas lisas, el grumo crece un escalón por vuelta hasta salir
entero. Todo apoya siempre.

- **Techo:** `pico <= con_patron x 1.2 mm`. Un pico de 9 mm necesita 8 vueltas.
- **Costo:** esas vueltas separan una fila de grumos de la siguiente, y esa
  separación es el alto del "punto" con el que se dibuja la figura. Más pico,
  dibujo más borroso.
- Todas dan **IMPRIMIBLE**.

### `grumo-puentea` — el grumo sale de una y se cuelga

Sale entero en la primera vuelta después de las lisas, tendiéndose al aire, y
el cabezal frena sólo en la punta (`puente_lento`) para pararse y dejar
material. Es lo que hace la pieza de referencia: los grumos se descuelgan un
poco y eso es parte de cómo se ve.

- **Sin techo de pico** y con la mejor resolución de dibujo.
- `verificar_pieza.py` lo da **NO IMPRIMIBLE**: 12 % de muestras sin apoyo
  contra 1.88 % de la referencia. Eso no es un error del archivo — es que el
  criterio supone que no querés puentes, y acá sí los querés. El peor puente
  mide 11.2 mm, por debajo de los 12 que la referencia aguanta.
- **Bajar la velocidad no adelgaza la línea**: la sección la fija la geometría
  y no el `F`, así que deposita lo mismo en más tiempo.

**Hay que imprimir el cupón antes de comprometer un florero acá.**

### `sin-cadencia` — sin vueltas lisas

Todas las vueltas pulsan en la misma fase, así que el pico se apila sobre el
pico: no hay salto, el largo sale gratis y el dibujo queda nítido. Pero los
picos dejan de ser grumos apilados y pasan a ser **crestas verticales
continuas**, que no es el aspecto del video.

---

## 1-cupones — imprimí estos primero

Cilindros cortos sin dibujo: son para leer el grumo, no la figura. Cinco bandas
de abajo hacia arriba.

| archivo | alto | bandas |
|---|---|---|
| `grumo-crece/largos_1.2a3.6mm` | 36 mm | 1.2 · 1.8 · 2.4 · 3.0 · 3.6 mm |
| `grumo-crece/largos_5a13mm` | 40 mm | 5 · 7 · 9 · 11 · 13 mm |
| `grumo-crece/extrusion_1.0a1.8x` | 36 mm | 1.0 · 1.2 · 1.4 · 1.6 · 1.8 x de material |
| **`grumo-puentea/largos_3a9mm`** | 40 mm | 3 · 4.5 · 6 · 7.5 · 9 mm |

`grumo-crece/largos_1.2a3.6mm` ya se imprimió: **la técnica salió bien pero los
picos son cortos**. Los otros dos de largos son la continuación.

El que decide el estilo es **`grumo-puentea/largos_3a9mm`**: dice a partir de
qué largo el grumo se descuelga más de lo que te gusta.

En `extrusion_*` el preview va a pintar el cordón de ancho uniforme — la
anotación `; LINE_WIDTH:` lleva el ancho nominal por contrato con Orca (ver
`.agents/MAPA.md`). Lo que cambia es la E, y eso sí se imprime.

## 2-floreros — Ø50 x 75 mm, 4 hojas con la K inscrita

| archivo | fondo | figura | punto del dibujo |
|---|---|---|---|
| `grumo-crece/hoja_fondo0.6_pico2.4mm` | 0.6 | 2.4 mm | 1.64 x 2.40 mm |
| `grumo-crece/hoja_fondo1.25_pico5mm` | 1.25 | 5.0 mm | 1.64 x 3.60 mm |
| `grumo-crece/hoja_fondo2.5_pico6mm` | 2.5 | 6.0 mm | 1.64 x 4.00 mm |
| `grumo-crece/hoja_fondo5_pico7mm` | 5.0 | 7.0 mm | 1.64 x 4.00 mm |
| `grumo-puentea/hoja_fondo5_pico9mm` | 5.0 | 9.0 mm | **1.64 x 2.00 mm** |
| `sin-cadencia/hoja_crestas_fondo5_pico9mm` | 5.0 | 9.0 mm | **1.64 x 0.40 mm** |

`grumo-crece/hoja_fondo5_pico7mm` tiene el fondo que pediste (5 mm) pero **el
dibujo casi no se ve**: el contraste es 2 mm sobre un relieve de 7, así que
todo se lee igual de alto. Es el que muestra el problema, no la solución.

`grumo-crece/flores_fondo0.6_pico2.4mm` es el otro florero, Ø68 x 200 mm, con
la máscara de flores en vez de hojas.

## 3-hueco-abierto — la variante descartada

Lo mismo pero con `ocupacion=0.5`: el hueco del pico mide 1.12 mm contra un
cordón de 1.2, o sea que se abre y el grumo sale hueco. Con 0.30 mide 0.67 y
las dos patas se funden desde la base, que es la bolita de la referencia.

## 0-3mf-viejos — NO IMPRIMIR

Injertos hechos antes de dos arreglos (el muestreo de la meseta y el borde
entre bandas). Hay que volver a injertar desde el g-code de arriba.

---

## Lo que todavía no está medido

1. **Ninguna está impresa** salvo `grumo-crece/largos_1.2a3.6mm`.
2. **El largo de pico no está calibrado**, ni el estilo. Los dos salen de los
   cupones.
3. **Que la pared de un cordón aguante agua no está medido.**
