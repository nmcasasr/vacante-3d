# Piezas con CONTROLES para el preview

Estas tres traen un `.params.json` al lado, que es lo que hace que la extensión
muestre sliders. Al mover uno, **no edita el g-code: vuelve a correr el
generador** con el valor nuevo y reescribe el archivo. Por eso la pieza y sus
parámetros no se pueden desincronizar.

    pastillas_control.gcode   sliders: pastillas-n, altura, ancho, velocidad
    clasico_control.gcode     sliders: diente, altura, ancho, velocidad
    hembra_control.gcode      sliders: ancho, velocidad

## Un control SÓLO aparece si el flag está en el comando

Es la trampa principal y no es un bug: `guardar_receta` arma los controles
recorriendo el `argv` con el que se generó la pieza. Si no pasaste `--diente`,
no hay slider de diente aunque el generador lo acepte.

    gen_rosca.py clasico ... --receta              -> altura, ancho, velocidad
    gen_rosca.py clasico ... --diente 0 --receta   -> + diente

O sea: **pasá explícitamente, con su valor por defecto, todo lo que quieras
poder tocar después.**

## `--receta` implica nombre estable

El archivo sale como `<nombre>.gcode`, sin el `_vNNNN` de siempre. No es
cosmético: la extensión relee SIEMPRE la misma ruta después de regenerar, y el
freno de caudal cambia la velocidad sola en cuanto un slider mueve la sección
—`--ancho` y `--pastillas-n` la mueven—, con lo que el archivo saldría con otro
nombre y el preview se quedaría mirando el viejo.

Por eso `--receta` exige una sola `--velocidad`: la receta describe UN archivo.

## Cómo se regeneran

    ./venv/bin/python gen_rosca.py pastillas --pastillas-n 24 --altura 40 \
        --material PLA --ancho 1.0 --segmentos 1440 --velocidad 2400 \
        --carpeta rosca/control --nombre pastillas_control \
        --separacion-por-angulo --receta

    ./venv/bin/python gen_rosca.py clasico --diente 0 --altura 40 \
        --material PLA --ancho 1.0 --segmentos 1440 --velocidad 2400 \
        --carpeta rosca/control --nombre clasico_control \
        --separacion-por-angulo --receta

    ./venv/bin/python gen_tuerca.py ../../gcodes/reference/tuerca/mariposa_v3_hembra.stl \
        --carpeta rosca/control --nombre hembra_control --material PLA \
        --ancho 1.0 --velocidad 2400 --separacion-por-angulo --receta

## El `borrador` de la receta NO lo usa la extensión

La receta trae un campo `borrador` con `--segmentos 120 --sin-receta`, y es
fácil suponer que la extensión lo aplica mientras arrastrás. **No lo hace**: los
tres puntos donde `media/main.js` llama a `pedirRegen` pasan `borrador = false`.
El comentario de ahí explica por qué lo sacaron — salía un borrador por cada
pausa del arrastre, la pieza parpadeaba entre versiones que nadie pidió y el
valor final llegaba detrás de una cola de corridas ya inútiles. Ahora el
arrastre sólo mueve el número y la corrida sale UNA vez, al soltar, a
resolución completa.

O sea que los sliders no bajan la resolución. Pero el mecanismo sigue en la
receta, y si se lo invoca a mano **deja el borrador pegado en el disco**:

    120 segmentos por vuelta  ->  2.60 mm por segmento
    una pastilla mide 8.4 mm  ->  le tocan TRES puntos

A esa resolución las pastillas desaparecen. Es la misma trampa que dejó las
caritas sin dibujo con `SEGMENTOS = 360`. Si el preview muestra la pieza lisa,
lo primero que hay que mirar es cuántos movimientos tiene el archivo:

    grep -c ' E' pastillas_control.gcode      # 191534 completo, ~16000 borrador

Comprobado el ida y vuelta: moviendo `--pastillas-n` de 24 a 16 la velocidad
pasó sola de 1325 a 1331 mm/min y el archivo siguió llamándose igual.

## Resolución de cada uno

    pastillas_control  1440 seg/vuelta   0.22 mm/segmento
    clasico_control    1440 seg/vuelta   0.22 mm/segmento
    hembra_control      360 seg/vuelta   0.91 mm/segmento

La hembra va con el defecto de `gen_tuerca.py` y está bien: no lleva patrón
angular, así que no hay detalle que resolver. Los machos con dibujo sí lo
necesitan.
