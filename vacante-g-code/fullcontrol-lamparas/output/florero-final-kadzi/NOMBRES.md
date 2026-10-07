# Cómo se llaman las cosas

Tres ejes independientes. El nombre del archivo es
`matera_<perfil>_<flanco>_<velocidad>.gcode`.

## PERFIL — de costado, cómo crece el grumo dentro de la banda

| nombre     | qué hace                                        | parámetros |
|------------|-------------------------------------------------|------------|
| `escalera` | crece vuelta a vuelta hasta arriba y corta      | `crecer_pico=1.0` (defecto) |
| `rombo`    | crece hasta la mitad y vuelve a bajar            | `crecer_pico=0.5`, `con_patron` impar |
| `romo`     | rombo con DOS vueltas en el máximo, punta ancha  | `crecer_pico=0.5`, `con_patron` par |

La escalera reparte el vuelo entre TODAS las vueltas de la banda; el rombo entre
la mitad. Por eso el rombo gasta el doble de salto por vuelta: 60 % de solape
contra 80 %. A cambio el rombo no termina en voladizo (contacto 0.00 % contra
0.49 %).

## FLANCO — de arriba, la forma del pico en planta

| nombre | qué hace                                  | parámetro   |
|--------|-------------------------------------------|-------------|
| `pico` | flanco en rampa, se afina hacia la punta  | `filo=0.50` |
| `dedo` | flanco recto, lados paralelos             | `filo=1.00` |

Con paso de púa de 2.80 mm: el `pico` mide 1.68 mm de base y 0.84 en la punta;
el `dedo` mide 1.68 en las dos. No cambia el solape ni el caudal — el flanco es
radial, y lo que manda el solape es cuánto avanza el radio por vuelta.

## VELOCIDAD

| nombre    | qué hace                               |
|-----------|----------------------------------------|
| (nada)    | todo a 8 mm/s                          |
| `rapida`  | piso a 8 mm/s y pared a 16             |

El piso NO se acelera: es capa de 0.8 mm y al doble se va a 13.1 mm³/s, donde el
PETG empieza a subextruir, y ahí se juega la adherencia de toda la pieza. Cuesta
3 minutos.

## Otras palabras que ya venimos usando

- **púa / turupe** — cada protuberancia. 56 por vuelta en esta pieza.
- **banda / fila** — un ciclo `lisas + con_patron`. Es la altura de un "pixel"
  del dibujo: 4.8 mm con 2 + 10 vueltas.
- **vuelo** — cuánto sale la púa de la pared (`amplitud`), 2.4 mm.
- **solape** — cuánto pisa una vuelta a la de abajo. Por debajo de 50 % avisa.
- **celda** — un punto del dibujo: una púa de ancho por una banda de alto.

## Lo que hay hoy en la carpeta

| archivo                                | perfil   | flanco | velocidad | vuelo | min |
|----------------------------------------|----------|--------|-----------|-------|-----|
| matera_escalera_dedo_rapida.gcode      | escalera | dedo   | rapida    | 2.4   |  36 |
| matera_kadzi_pico_recto_rapida.gcode   | romo     | dedo   | rapida    | 2.4   |  37 |
| matera_kadzi_prueba1.gcode             | escalera | pico   | lenta     | 3.0   |  66 |
| matera_kadzi_prueba2.gcode             | escalera | pico   | lenta     | 3.0   |  65 |
| matera_kadzi_prueba3.gcode             | escalera | pico   | lenta     | 3.0   |  65 |
| matera_kadzi_punta_roma.gcode          | romo     | pico   | lenta     | 2.4   |  64 |
| matera_kadzi_punta_roma_16mms.gcode    | romo     | pico   | 16mms     | 2.4   |  32 |
| matera_kadzi_punta_roma_rapida.gcode   | romo     | pico   | rapida    | 2.4   |  35 |
| matera_kadzi_rombo.gcode               | rombo    | pico   | lenta     | 2.4   |  62 |

## ANCHO — cuánto del paso ocupa el dedo (`ocupacion`)

| nombre    | `ocupacion` | dedo | hueco | |
|-----------|-------------|------|-------|--|
| `ancho`   | 0.60        | 1.68 | 1.12  | el hueco es MÁS ANGOSTO que el cordón de 1.2 |
| `angosto` | 0.35        | 0.98 | 1.82  | igual que la referencia `hojas_50x50mm` (1.83) |

Esto es lo que hacía que los dedos salieran como bloques pegados con una muesca:
**con hueco de 1.12 la boquilla no puede tallar el valle, lo rellena.** El hueco
tiene que medir más que el cordón. Con el flanco recto (`dedo`) angostar no
cuesta nada: 100 % de supervivencia y 80 % de solape en las dos.

## PISO calado con el isotipo

```
--hueco-isotipo 34          cala el piso con el logo, 34 mm
--hueco-isotipo-giro 90     triangulo grande hacia arriba, igual que la pared
--hueco-retraccion 0.8      retrae en cada cruce
```

`matera60_*_piso_kadzi.gcode`. Sirve de drenaje y marca la pieza por abajo.

**El piso deja de ser trazo continuo, y es inevitable.** El isotipo son CUATRO
polígonos sueltos, así que la espiral tiene que cruzarlos: 56 cruces, 752 mm de
viaje. La espiral NO cambia de recorrido —deformarla para esquivar cuatro islas
es otro problema—; lo que hace es apagar el extrusor encima de los huecos.

La PARED sigue siendo trazo continuo: el verificador la sigue dando como tal
porque mide el cuerpo, que ahora arranca donde termina el piso.

Los viajes salen como G0 a F6000 y **con retracción de 0.8 mm**, que hubo que
agregar: sin ella son 56 cruces de PETG sin retraer justo encima del dibujo, o
sea una telaraña sobre lo único que se quiere ver.

Tres de las cuatro piezas del isotipo son *estrelladas* respecto de su centro
(todo rayo lo cruza una vez) y el rombo no. Eso importa si alguna vez se quiere
el hueco hecho con la espiral morfando en vez de calado: ahí sólo sirven las
estrelladas, y de a una.
