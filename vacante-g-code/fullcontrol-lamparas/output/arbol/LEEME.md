# Árbol — la copa

La bola del hongo (`hongis.dxf`, espejada en la panza, paso adaptativo) cubierta
con los grumos del florero-kadzi que salen de una y se cuelgan
(`grumo-puentea`). Sólo la copa: el tronco es el palo de la lámpara, que entra
por el hueco de abajo.

Todo es cordón **1.2 mm**, capa **0.8**, PETG a 240 °C, cama 70, ventilador 100,
8 mm/s con `puente_lento=0.35` en la punta.

## `1-cupones/largos_1.2a9mm`

Bola **Ø80 x 59 mm** (`--perfil-escala 0.45`), hueco abajo Ø20, boca arriba Ø12.

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

Verificador: línea fina 0.00 % · peor puente 11.9 mm (el tope es 12) ·
contacto 12 % — el mismo número que `florero-kadzi/1-cupones/grumo-puentea`:
es el grumo colgando, buscado. Da NO IMPRIMIBLE por eso y sólo por eso.

Tiempo: ~2.4 h estimadas por recorrido x1.4. El estimador sale corto; el de
Orca al laminar es el bueno.

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
