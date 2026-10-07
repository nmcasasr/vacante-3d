# Gusanito chico para LEDs — qué es cada archivo

Esferas unidas, 3½ lóbulos contando el cortado de la base. **Sin piso**: el
fondo queda completamente abierto en el diámetro máximo, así que la tira de LEDs
entra por abajo sin tener que dejarle un agujero aparte.

PETG, cordón 1.2, capa 0.8, modo vaso, 480 mm/min (lo calibrado contra Squeezy).

| | Ø | alto | tiempo | material | contacto | peor puente |
|---|---|---|---|---|---|---|
| **led_D34_70mm** | 34 | 70 mm | **32 min** | 9.6 cm³ | 0.00 % | 0.00 mm |
| **led_D40_83mm** | 40 | 83 mm | **44 min** | 13.4 cm³ | 0.01 % | 0.09 mm |
| **led_D46_95mm** | 46 | 95 mm | **58 min** | 17.6 cm³ | 0.10 % | 0.84 mm |

Las tres IMPRIMIBLE y trazo continuo. Los tiempos son un cálculo sobre el
recorrido, no lo que diga el laminador.

    D34   34 33 28 31 34 34 34 31 28 33 34 34 32 28 31 34 34 34 31 24 0
    D40   40 38 33 36 40 40 40 36 33 39 40 40 38 33 37 40 40 39 36 28 0
    D46   46 44 38 42 46 46 46 42 38 44 46 46 44 38 42 46 46 45 41 32 0

## La regla de la forma

    altura = radio_max x 4.125        (4 lóbulos, apoyo 0)

El paso entre lóbulos tiene que ser igual al radio máximo — es la proporción del
gusanito original (Ø60 con un lóbulo cada 30 mm) y es lo único que hace que se
lea como esferas unidas. El 4.125 son 3.859 de esa proporción más un 7 % que
necesita el ápice para cerrar sin aplanarse.

**Para chequear una variante nueva**: mirar el diámetro subiendo por la pieza.
Tiene que ondular. Un perfil que baja monótono es un cono, no un gusanito.

## El tiempo va con el radio al cuadrado

    Ø34 -> 32 min    Ø40 -> 44 min    Ø46 -> 58 min
    Ø52 -> 1.2 h     Ø58 -> 1.5 h     Ø89.5 -> 3.5 h

La palanca es el DIÁMETRO. Achatar los lóbulos para bajar la altura no sirve:
rompe la figura y además aplana el ápice, que es lo que lo hace descolgarse.

## Si la luz sigue quedando corta

El cordón de 1.2 mm es bastante pared para un LED chico. Bajar a
`--ancho-linea 0.8` deja pasar más luz y además acorta el tiempo, pero cambia la
calibración de extrusión que viene de Squeezy, así que conviene sacar una de
prueba antes de hacer la tanda.

Las versiones grandes —de cuando la base tenía que recibir una lámpara
comprada— quedaron en `output/gusanito-85/`.

## Generar de nuevo

Los comandos exactos están en el `.params.json` de cada archivo.
