# Árbol — la copa

La bola del hongo (`hongis.dxf`, espejada en la panza, paso adaptativo) cubierta
con los grumos del florero-kadzi que salen de una y se cuelgan
(`grumo-puentea`). Sólo la copa: el tronco es el palo de la lámpara, que entra
por el hueco de abajo.

Todo es cordón **1.2 mm**, capa **0.8**, PETG a 240 °C, cama 70, ventilador 100,
8 mm/s con `puente_lento=0.35` en la punta.

## Los cupones

**La carpeta dice CÓMO está hecho. El nombre del archivo dice CON QUÉ NÚMEROS.**

Los dos son la misma bola **Ø80 x 59 mm** (`--perfil-escala 0.45`), hueco abajo
Ø20, boca arriba Ø12, con los mismos cinco largos. Cambia cómo se ordenan los
grumos:

- **`1-cupones/intercalado/largos_1.2a9mm`** — EL QUE VA. **3 vueltas lisas + 1
  con patrón**, como la matera, y cada fila de grumos corrida media púa
  respecto de la anterior: cada grumo cae entre los dos de abajo, al
  tresbolillo, como las hojas de la copa. Filas cada ~3.2 mm. ~2 h.
- `1-cupones/columnas/largos_1.2a9mm` — el primer intento: 2 + 1, grumos
  apilados en columnas como el florero. Queda de comparación.

**Los largos van en GAJOS alrededor de la bola, no en bandas a lo alto.** En una
bola cada altura es otra situación —abajo voladizo, en el medio pared parada,
arriba cierre—, y con bandas cada largo caería en una sola. En gajos cada largo
recorre las tres.

    gajo 1  (0–72°)     1.2 mm   sólo el fondo: la referencia
    gajo 2  (72–144°)   3.2 mm
    gajo 3  (144–216°)  5.1 mm
    gajo 4  (216–288°)  7.1 mm
    gajo 5  (288–360°)  9.0 mm

El ángulo 0 es +X de la cama y crece antihorario visto desde arriba. El corte
entre gajos es duro a propósito: tiene que poder leerse "el tercero sirve y el
cuarto no".

**La cantidad de púas sigue al radio**, en 12 bandas a lo alto
(`barrido_puas=45,68,83,90,97,99,98,93,83,70,50,35`): ~2.5 mm entre grumos de la
base a la boca. Con una cantidad fija quedaban a 3.5 mm en el ecuador y
fundidas cerca de la boca.

Verificador, los dos: línea fina 0.00 % · peor puente 11.9 mm (el tope es 12) ·
contacto ~12 % — el mismo número que `florero-kadzi/1-cupones/grumo-puentea`:
es el grumo colgando, buscado. Dan NO IMPRIMIBLE por eso y sólo por eso.

Los tiempos son por recorrido x1.4 y salen cortos; el de Orca al laminar es el
bueno.

**Qué mirar al imprimirlo:** qué largo se lee como follaje y no como púa; si en
la mitad de abajo (voladizo) los grumos cuelgan como cordones o se caen; y si
arriba, donde la copa cierra casi plana, los grumos se ven o se aplastan.

## Lo que hizo falta en el código

`--pendiente-silueta` ahora gobierna también la MARCHA adaptativa, no sólo la
extrusión. Sin eso la marcha leía cada grumo como pared acostada y achicaba la
subida hasta el piso: el primer intento salió con cordón de 1.2 x 0.223, 19 %
de línea fina y puentes de 130 mm. Ninguna receta vieja cambia: las 114 que
usaban la opción son de paso fijo y no pasan por la marcha (comprobado con
`matriz`; el hongo sale byte a byte igual).

`puas.py`, todo apagado por defecto (las recetas viejas salen byte a byte
iguales: matriz, largos_3a9mm, velocidad, matera60_romo_piso_kadzi, hongo):

- `intercalar=1` corre media púa los grumos de una fila con patrón sí y otra no.
- Con `banda_por_vuelta=1` la cadencia cuenta VUELTAS de verdad y las bandas
  de `barrido_puas`/`barrido` se leen en el `t` real donde arranca el ciclo.
  En la bola hace falta: con paso adaptativo las vueltas no suben lo mismo, y
  `vuelta x dt_capa` no es la altura.
