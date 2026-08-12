---
name: vacante-3d
description: Generador de piezas 3D en modo vaso (FullControl + extensión de VS Code). Usar al tocar lamparas/, ext-gcode/, o cualquier g-code de output/.
---

# Cómo se trabaja en este proyecto

## La regla que ordena todo lo demás

**El g-code no se edita nunca. Se regenera.** Un g-code editado ya no tiene
parámetros: la corrida siguiente tira el cambio, y habría que recalcular la
extrusión de cada punto movido. Todo —sliders, toques, esculpido— es un DATO que
vuelve a entrar al generador, nunca una edición del archivo.

## Verificar, no suponer

Esta es la lección más cara de la sesión anterior y no es retórica. Cada vez que
afirmé algo sin medirlo, estuve equivocado:

- Dije "es la costura" de unos escalones. En modo vaso no hay costura.
- Dije que el corrimiento lateral "sale gratis en apoyo". Dejaba 5 vueltas al aire.
- Entregué `glitch.gcode` reportando la excursión sin medir el solape: **85 de
  400 vueltas sin apoyo**, el peor archivo de la sesión.
- Reporté tres configuraciones "distintas" que eran el mismo archivo, porque un
  bug ponía a cero la parte que variaba.

Antes de afirmar que algo funciona, **medilo sobre el g-code generado**. Y si la
medición contradice el cálculo, sospechá primero de la medición: varias veces el
filtro que separaba una cosa de otra estaba mal y el número no significaba lo que
yo creía.

Herramientas que ya existen para eso:
- `python3 ext-gcode/gcode-preview/verificar_campo.py` — contrasta el campo de
  deformación de JS contra el de Python. Encontró un `envolver()` con `3π` donde
  iba `2π`, que corría cada toque media vuelta.
- `verificar_ams.py` — contrasta el bloque de cambio de filamento contra un 3mf
  real de Bambu.
- El modo **solape** del preview colorea segmento por segmento; es más confiable
  que un script que resume.

Cuando midas algo nuevo, escribí el verificador. No lo dejes en un script de /tmp.

## La física que gobierna las piezas

**Δ radio por vuelta < ancho de cordón.** En modo vaso cada vuelta apoya sobre la
anterior; si el radio se corre más que un cordón, no hay superficie común y la
pared se abre. Es el mismo criterio en `comun._verificar_voladizo`,
`modelado.revisar`, `perfil.voladizo` y el modo solape del preview — y tienen que
seguir coincidiendo, porque ya pasó que cada uno midiera distinto.

**Excepción, y es la que desbloquea las piezas interesantes:** una superficie
casi horizontal NO se apoya encima sino AL LADO, como el piso macizo de un bol.
Por eso una aleta puede salir 40 mm. Lo que hay que respetar ahí es la separación
lateral entre pasadas, no el apoyo vertical.

**El paso vertical es adaptativo**: `dz = paso · cos(θ)` para que la separación
sobre la superficie sea constante, y θ sale del **peor ángulo** de la vuelta, no
del radio medio. Esa distinción no es un detalle: con el medio, una deformación
angular no lo activa —saca por un lado y mete por el otro, el promedio no se
mueve— el generador cree que la pared sigue vertical y deja las vueltas
separadas con huecos entre ellas. Fue el defecto que hizo fracasar cinco
versiones del glitch.

Vale como principio general para este proyecto: **cuando algo se mide para
decidir si una pieza aguanta, se mide el peor caso, no el promedio.** El promedio
esconde exactamente los lugares donde la pieza falla.

**Color: solo por bandas.** Un cambio dentro de la vuelta cuesta 56 s y sangra
1.3–6.9 vueltas. La forma se hace con geometría; el color, con bandas de altura.

## Dónde vive cada cosa

- `lamparas/comun.py` — el motor: espiral, modo vaso, base, marcha vertical.
- `lamparas/bowls/` — composición y CLI. `--p` patrón, `--pe` estructura, `--ps`
  silueta, `--pp` pintura. Todo `--p*` aparece como slider en el preview.
- `lamparas/{siluetas,estructura,superficie,modelado,formas}.py` — los campos.
  Todos hablan `(ángulo, t) -> mm` y se suman sin conocerse.
- `lamparas/perfil.py` — silueta desde un DXF de Fusion.
- `lamparas/recorrido.py` — **recorridos que no son una espiral monótona**. Si
  algo necesita volver sobre la misma altura, va acá: no se puede expresar
  cambiando la función del radio.
- `ext-gcode/gcode-preview/` — el preview. `media/main.js` es el webview.

## Al agregar un mapa de color al preview

Ponele **piso absoluto a la escala**. Ya pasó dos veces: cuando la pieza no tiene
variación, una escala derivada de los datos amplifica el ruido de coma flotante
hasta saturar, y se ve un mapa lleno de color donde no hay nada. Ver
`RELIEVE_MINIMO` y `RANGO_MINIMO`.
