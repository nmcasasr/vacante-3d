# Lámpara gusanito — qué es cada archivo

Esferas unidas, 3½ lóbulos contando el cortado de la base. **Sin piso**: la
pared arranca de una. El corte cae en el ecuador del lóbulo de abajo
(`apoyo=0`), así que **la base ES el punto más ancho**.

## Para imprimir ahora

| | Ø | alto | tiempo | contacto | peor puente |
|---|---|---|---|---|---|
| **lampara_3lob_y_medio_D58_120mm** | 58 | 120 mm | **1.5 h** | **0.00 %** | **0.00 mm** |
| lampara_3lob_y_medio_D52_107mm | 52 | 107 mm | 1.2 h | 0.37 % | 2.56 mm |

La de Ø58 es la pedida: hora y media y **cero puentes**. La de Ø52 está por si
el tiempo real se pasa del estimado — los tiempos de acá son un cálculo sobre el
recorrido, no una medición del laminador.

    Ø58   58 56 48 53 57 58 57 52 49 56 58 58 55 47 53 58 58 57 52 40 0
    Ø52   52 50 43 47 52 52 51 47 44 50 52 52 49 42 48 52 52 51 46 34 0

## La regla de la forma: el paso de lóbulo es igual al radio máximo

Es la proporción del gusanito original —Ø60 con un lóbulo cada 30 mm— y es lo
único que hace que se lea como esferas unidas. En la práctica:

    altura = radio_max x 4.125        (4 lóbulos, apoyo 0)

El 4.125 son dos cosas: 3.859 de la proporción del original, más un 7 % de
estirón que necesita el ápice (ver abajo). Romper esa regla es lo que produjo
la primera tanda, que salió como una bala en vez de un gusanito: lóbulos cada
100 mm en vez de cada 45.

**Cómo chequearlo rápido**: mirar el diámetro subiendo por la pieza. Tiene que
ondular. Un perfil que baja monótono —`104 103 100 96 90 83 72 58 34`— no es un
gusanito, es un cono.

## El ápice cierra, pero pide altura

La punta cierra apoyándose vuelta a vuelta: baja hasta Ø1.1 con pasos de radio
de 0.2 a 0.4 mm contra un cordón de 1.2. No hay nada colgando.

Lo que sí pasa es que si la pieza queda CORTA para su radio, el ápice se aplana
y aparece un tramo al aire arriba. Medido a Ø89.5 con 4 lóbulos:

| altura | peor puente | |
|---|---|---|
| 173 mm | 12.41 mm | NO IMPRIMIBLE |
| 185 mm | 9.51 mm | ok |
| 200 mm | 6.98 mm | ok |

Doce milímetros más de alto y pasa. Por eso el factor lleva el 7 % de estirón.

**El tamaño no impide cerrar**, y se comprobó al revés: la silueta del gusanito
original escalada a Ø89.5 cierra con puente 10.5 mm y da IMPRIMIBLE. Si algo no
cierra, es que está achatado, no que sea grande.

## El tiempo va con el radio al cuadrado

El recorrido crece con el perímetro Y con la cantidad de vueltas, y las dos van
con el radio. Medido:

    Ø52 -> 1.2 h      Ø58 -> 1.5 h      Ø64 -> 1.8 h      Ø89.5 -> 3.5 h

Así que la palanca del tiempo es el DIÁMETRO. Achatar los lóbulos para bajar la
altura no sirve: rompe la forma y además aplana el ápice.

Los 480 mm/min son los calibrados contra Squeezy, que está impreso y funciona;
no se tocan para ganar tiempo.

## Las viejas, de cuando la base tenía que medir 88

`PRUEBA_medio_lobulo_24mm`, `lampara_2lob_y_medio_134mm` y
`lampara_3lob_y_medio_185mm` son de Ø89.5, de cuando la apertura de la base
tenía que recibir la lámpara. Ya no hace falta ese diámetro. La de prueba sigue
sirviendo como cupón: es sólo el medio lóbulo de la base, media hora, y prueba
lo que importa —que agarre en la cama sin piso y que la pared aguante al
cerrarse.

## Generar de nuevo

Los comandos exactos están en el `.params.json` de cada archivo.
