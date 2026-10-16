# Árbol dos: la copa en pisos

Es el árbol (`output/arbol/`) con la misma técnica de grumos, pero la bola ya no
es una esfera lisa. Está partida en **5 pisos que se inflan hacia afuera**, como
una copa de árbol en nubes. Entre piso y piso hay un pliegue que cae justo
sobre la esfera de antes. Sigue el dibujo, pero menos exagerado: allá los pisos
salen ~30 % y acá 12 o 18 %.

Lo demás es igual que el gajo 1 del cupón de velocidades del árbol, la
referencia:

- bola del hongo a escala 0.45, alta 59 mm, hueco Ø20;
- 72 púas fijas, 3 lisas + 1 con patrón, al tresbolillo;
- grumos de 9 mm en toda la bola;
- lo liso a 16 mm/s, el grumo a 8 y la punta a 3;
- PETG 240 °C, cordón 1.2, capa 0.8.

## Los cupones (`1-cupones/`)

| cupón | se infla | panza | tiempo* |
|---|---|---|---|
| `pisos5_infla12` | 12 % | Ø89 | ~2.2 h |
| `pisos5_infla18` | 18 % | Ø94 | ~2.5 h |
| (el árbol liso, de comparación) | — | Ø80 | ~1.9 h |

\* Calculado sobre el recorrido x1.4; el que da Orca es el bueno.

Ø en el eje del cordón, a cada altura. Los pliegues caen en z 12, 24, 36 y 47:

| z | 6 | **12** | 18 | **24** | 30 | **36** | 42 | **47** | 53 |
|---|---|---|---|---|---|---|---|---|---|
| liso | 52 | 65 | 73 | 78 | 80 | 78 | 73 | 64 | 50 |
| 12 % | 59 | 65 | 82 | 78 | 89 | 78 | 81 | 64 | 56 |
| 18 % | 62 | 65 | 87 | 78 | 94 | 78 | 86 | 64 | 59 |

Cada piso se infla en proporción al radio que tiene a esa altura. Por eso los
de arriba y abajo, donde la copa cierra, salen menos solos. El piso (t=0) y la
boca (t=1) no se mueven.

Verificador, los dos: línea fina 0.00 %, peor puente 9.8–10.2 mm, contacto
~17 %. Ese contacto es el mismo que en el cupón de velocidades: es el grumo
colgando, que se busca. Intercalado 99.2–99.3 %. Sin pausas.

## La forma del pliegue

Cada piso es `|sen|^P`. Con P = 1 la panza es redonda y el pliegue en V, como
en el dibujo, pero **no sale**:

- al 12 % ya queda un puente de 15 mm;
- al 18 % queda una vuelta entera al aire (58 mm, z 36.8).

Justo encima del pliegue la pared sale hacia afuera de golpe y la vuelta lisa no
tiene dónde apoyar. Con **P = 1.5** el fondo del pliegue se redondea, la panza
sigue llena, y pasa limpio hasta el 22 %. P = 2 es una onda suave y pierde el
pliegue. Los cupones van con 1.5.

Barrido (peor puente):

| P | 8 % | 12 % | 15 % | 18 % | 22 % |
|---|---|---|---|---|---|
| 1 | 9.8 | 15.2 ✗ | | 58 ✗ | |
| 1.5 | | 10.2 | 9.8 | 9.8 | 10.5 |
| 2 | | 10.2 | 9.8 | 9.8 | 9.8 |

**Qué mirar al imprimirlo:**

- si los pisos se leen desde lejos, o el grumo los tapa;
- si el pliegue se ve como pliegue o se pierde;
- cómo cuelgan los grumos debajo de cada panza, donde la pared vuelve a meterse.

## En el código

Opción nueva en `lamparas.bowls`. Apagada por defecto, así que las recetas
viejas salen idénticas: el cupón intercalado del árbol regenerado sólo cambia en
el nombre de la cabecera.

    --perfil-lobulos N          cuántos pisos (0 = apagado)
    --perfil-lobulos-amp FRAC   cuánto se infla cada uno (0.10 por defecto)
    --perfil-lobulos-forma P    exponente de la panza (1 por defecto; acá 1.5)

Se aplica sobre la silueta lisa, después de escalar. Así la marcha adaptativa,
`--pendiente-silueta` y el aviso de voladizo ven los pisos como forma, y los
grumos van encima.
