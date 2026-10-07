# `pastillas` — espaciados y tamaños

Discos que sobresalen con una figura HUNDIDA: corazón, estrella, carita y raya,
en damero. Todo lo de acá es la versión **v2**, corregida contra la primera
pieza impresa (`pastillas_control`, disco Ø8.40, n=16).

## Los cinco espaciados

Mismo disco Ø8.40; lo único que cambia es cuántos entran por vuelta.

| archivo | por vuelta | paso | hueco |
|---|---|---|---|
| `macho_pastillas_n32_v1326` | 32 | 9.97 mm | 1.6 mm |
| `macho_pastillas_n28_v1326` | 28 | 11.40 | 3.0 |
| `macho_pastillas_n24_v1325` | 24 | 13.30 | **4.9** |
| `macho_pastillas_n20_v1330` | 20 | 15.96 | 7.6 |
| `macho_pastillas_n16_v1331` | 16 | 19.95 | 11.6 |

El hueco VERTICAL no se elige: son 5.1 mm y los fija el paso de rosca. Por eso
`n24` es el que se lee como retícula pareja — su hueco horizontal, 4.9, es casi
el mismo.

Las cinco: salto radial 0.452..0.455 -> **55 % de solape, paso FIJO**; holgura
radial **+0.197 ENTRA**; juego axial 1.06 mm; IMPRIMIBLE.

OJO con `verificar_encastre`: su `--ancho` vale 1.2 por defecto y estas piezas
llevan cordón 1.0. Sin pasárselo reporta la holgura 0.1 mm más ajustada de lo
que es y el apoyo muy alto. La señal de que está bien puesto es la primera
línea: `núcleo del recorrido + medio cordón = R50.000 contra R50.00  OK`.

## Y el disco grande

`macho_pastillas_MAXdisco_v1329` — Ø9.25, el máximo que admite la envolvente,
30 por vuelta.

    disco            cara plana   figura     juego axial
    Ø8.40 (defecto)    Ø5.80      r 2.76      0.96 mm
    Ø9.25 (MAXdisco)   Ø6.65      r 3.16      0.16 mm

La figura es un 15 % mayor y se lee bastante mejor. Lo que cuesta es el juego
axial: 0.16 mm es MÁS APRETADO que el diente más gordo que admite la geometría
(0.28), o sea que no deja margen para la variación del plástico. El par que ya
enrosca mide 4.08 mm de juego. Imprimí las dos y decide el plástico.

## LA VIGENTE

    macho_pastillas_n16_MAX_capa025_v1330.gcode

Disco Ø9.25, 16 por vuelta, **capa 0.25 mm**. Es la `n16_MAXdisco` que enroscó
bien, con la capa bajada de 0.30 a 0.25: 20 % más de resolución vertical, que es
donde se gana nitidez —el borde de un grabado se cuantiza al paso de capa, así
que las curvas dejan de escalonarse—. 40 min contra 34.

Confirmada impresa y mejor que la anterior.

    capa 0.250 (31 % de la boquilla)   velocidad 22 mm/s   radial 19.8 mm/s
    solape 55 %, con el 0.00 % de los pares por debajo
    núcleo + medio cordón = R50.000 exacto · holgura +0.196 · ENTRA

### Lo que se probó y NO sirvió: capa 0.20

Se intentó capa 0.20 con grabado 0.65, y salió con errores de impresión que no
tenía la de 0.30. Tres causas apiladas, todas introducidas a la vez:

1. **0.20 sobre una boquilla de 0.8 es el 25 %**, el borde inferior del rango
   sano, y nada en este proyecto se imprimió nunca por debajo de 0.30. Un cordón
   de 1.0 x 0.20 es un aplastado de 5:1: la punta plancha, arrastra y pega peor.

2. **La velocidad subió sola.** El freno de caudal mantiene los mm3/s, así que
   al bajar la capa baja la sección por milímetro y el freno DEJA CORRER MÁS
   RÁPIDO: 22 -> 30 mm/s. Sobre las mismas figuras el movimiento radial pasó de
   19.8 a 28.4 mm/s, un 44 % más. Eso es lo que produce fantasmas y grumos.

3. **Hubo que forzar `--paso-fijo si`** para el grabado de 0.65, saltando el
   criterio que rechaza solapes bajo 50 %. Dejaba el 0.2 % del recorrido al 35 %.

**Regla:** bajar la capa NO es gratis aunque los verificadores digan IMPRIMIBLE —
sube la velocidad por el costado del freno de caudal, y hay un piso de
capa/boquilla que ningún script de acá comprueba.

## Qué cambió respecto de la primera impresión

1. **Los discos ya no se deslizan.** `v` mide la altura desde la CINTA, y la
   cinta sube: sobre los 8.4 mm de una pastilla el hilo gana 0.355 mm, así que
   un círculo en (u, v) sale corrido sobre la pieza. Medido en la pieza
   impresa: +2.81°. Ahora: **+0.05°**.

2. **Las puntas ya no se recortan.** Las figuras se normalizaban contra su CAJA,
   y la caja de una estrella sobresale del círculo un 17 %: las puntas se
   cortaban contra la cara plana del disco. Por eso la estrella se leía
   redondeada. Ahora `rel_figura` es margen de verdad.

3. **Los trazos superan el cordón.** La carita usaba el 73 % del círculo y sus
   ojos medían 0.77 mm, o sea 0.8 cordones — por debajo de uno no se dibuja.

        medida             impreso   ahora
        ojo: ancho          0.77      1.38
        hueco entre ojos      --      1.38
        boca: grosor        1.32      1.46
        hueco ojo-boca        --      1.01
        raya                1.19      1.82

   El HUECO entre rasgos cuenta tanto como el rasgo: con 0.78 mm de separación
   los dos ojos se funden en una barra.

## Los renders

`banda_*_altura.png` es el que hay que mirar para juzgar el dibujo (gris =
radio); `banda_*.png` es el sombreado, donde el lado en sombra parece vacío.
Los dos salen de `ver_banda.py --impreso`, que filtra con el diámetro de
boquilla para mostrar lo que la máquina puede colocar de verdad.

## OJO

`macho_pastillas_n20_v1330.gcode.3mf` es un injerto del **31 de agosto**, o sea
de la versión vieja: mismo nombre de archivo, geometría anterior. Hay que
volver a injertarlo si se quiere imprimir esa variante.

## v3 — el disco achatado (por qué la de 240 mm enroscaba dura)

El usuario imprimió los 240 mm con el disco máximo (Ø9.25) y **enrosca duro**.
No es la holgura radial: da +0.20 mm, igual que en todas. Es el **juego axial**,
que es lo que absorbe la variación del plástico:

    macho_clasico_v1823                3.74 mm  (28 % del paso)   enrosca bien
    macho_perlas_v1846                 3.74 mm  (28 %)            enrosca bien
    macho_caritas_intercalada_v1774    3.20 mm  (24 %)            enrosca bien
    pastillas Ø9.25 (lo impreso)       0.28 mm  ( 2 %)            DURO

Diez veces menos margen que todo lo que ya funcionaba, y menos que la variación
del propio plástico. Que el cupón de 40 mm pasara y la pieza entera no es
coherente, no contradictorio: el cupón cruza 48 pastillas y los 240 mm cruzan
284; con 0.28 mm basta una para que agarre.

**La salida no es achicar el disco.** Lo que aprieta es cuánto llena el CANAL
del hilo, y el canal sólo tiene ancho en el eje axial. En el ángulo el disco no
le pide nada a nadie: la vuelta de arriba está al mismo ángulo. Bajar el radio
paga en las dos direcciones y sólo cobra en una.

`--pastillas-achatado 0.88` achica el disco **sólo en axial**:

    opción                      juego    disco (ancho x alto)   figura
    radio 4.625, achatado 1.00   0.28 mm   9.25 x 9.25 mm        r 3.16   <- duro
    radio 4.20,  achatado 1.00   1.06      8.40 x 8.40           r 2.76
    radio 4.625, achatado 0.88   1.01      9.25 x 8.14           r 3.16

Las dos últimas dan el mismo milímetro de juego. La tercera lo consigue sin
perder nada de ancho de figura — que es justo donde se había ganado la
legibilidad, vía `fig_ancho_rel`.

Y no cuesta solape: el peor salto radial sigue en 0.450 (55 %) hasta achatado
0.85, porque ese salto lo pone la rampa del grabado, no el chaflán del disco.
Desde 0.80 sí empieza a cobrar (0.473).

### Cuánto se nota el óvalo

0.88 SE VE. El juego no lo fija el radio ni el achatado por separado sino el
**semieje axial** (`radio * achatado`), así que hay toda una familia con el
mismo ajuste y distinta forma:

    radio  achat  disco (ancho x alto)  ovalidad  figura  juego
    4.625  0.88     9.25 x 8.14          12 %     r 3.16  1.01 mm
    4.50   0.92     9.00 x 8.28           8 %     r 3.04  0.97
    4.45   0.94     8.90 x 8.37           6 %     r 2.99  0.94   <- la vigente
    4.40   0.95     8.80 x 8.36           5 %     r 2.95  0.97
    4.35   0.97     8.70 x 8.44           3 %     r 2.89  0.94
    4.30   1.00     8.60 x 8.60           0 %     r 2.85  0.86

El ALTO de la figura casi no se mueve en toda la tabla (5.56 a 5.70 mm). Lo
único que se compra con la ovalidad es ANCHO de dibujo: 6.32 contra 5.70. Pasar
de 0.88 a 4.45/0.94 cuesta 5 % de ancho y parte la ovalidad al medio.

### Lo elegido: REDONDA

`radio 4.30, achatado 1.0` — Ø8.60 redondo de verdad, juego axial **0.86 mm**,
tres veces lo que enroscaba duro. Cuesta un 10 % de figura contra el disco
máximo, y se recupera de sobra con el centrado de abajo.

## v4 — el centrado de las figuras

Las cuatro tenían la CAJA centrada y la TINTA a cuatro alturas distintas:

    corazón   +0.598 mm      estrella  -0.256 mm
    carita    -0.406 mm      raya      -0.002 mm

Dos causas, las dos en `_marca_polar`:

  - **centrar la caja no centra la figura**: la caja de una estrella llega a
    +1.00 arriba y a -0.809 abajo, así que centrarla la baja 0.096 de radio;
  - **escalar por `hx` y `hy` por separado la ESTIRA**: cada forma se deformaba
    hasta llenar un cuadrado, la estrella 5.1 % más alta y el corazón 4.0 % más
    baja de lo que son.

Ahora las polares se centran en el **centro de área** y se escalan con un solo
factor. La carita no es polar: se mide su tinta y se corre, con tope en 0.97 del
radio para no meterle los ojos en el chaflán (centrarla a secas la sube 0.62 mm
y los deja a 0.11 del borde).

Los cuatro centroides quedan dentro de **±0.03 mm** del centro del disco.

    macho_pastillas_n16_redonda_v1330.gcode   cupón de 40 mm, ~40 min
    ../../control/pastillas_240.gcode         la pieza entera, ~4 h

El barrido que lo midió quedó en `output/rosca/prueba/holgura/`.
