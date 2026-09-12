"""
El dibujo lo hacen los TURUPES: la pared da vueltas normales y la boquilla
sale y entra sólo donde va la figura.

La pieza se imprime en modo vaso como cualquier otra —una espiral, una vuelta
por capa— y el patrón no cambia la Z ni el recorrido: cambia el RADIO dentro
de la vuelta. Donde la máscara dice que no hay dibujo, el radio es la silueta
y la boquilla va derecha. Donde dice que sí, el radio pulsa `puas` veces por
vuelta y cada pulso deposita un grumo que sobresale. Vista en planta, la
vuelta es un círculo liso con las púas asomando en el sector dibujado, que es
el croquis que describe la técnica.

Que las púas se APILEN es lo que convierte los grumos sueltos en dibujo: todas
las vueltas pulsan en la misma fase, así que cada púa cae encima de la de la
vuelta anterior y arma una columna continua. Es el mismo truco de
`bowls/zigzag.py` —la figura se dibuja cambiando la PIEL y no el color— pero
con el relieve concentrado en la figura en vez de repartido por la pared. Ver
`lamparas/superficie.py`.

## La perilla es `amplitud`, y no es lineal

Cuánto se ve el dibujo es cuánto sale la boquilla. Pero lo que se ve no es lo
que se pide: la boquilla deposita una cinta de un cordón de ancho, y esa cinta
no entra en un valle más angosto que ella, así que parte del vuelo se rellena
sola. `construir()` lo calcula antes de generar nada con el modelo de
`lamparas/cordon.py`. Con 150 púas sobre Ø68 y cordón de 1.0:

    amplitud pedida   0.60   0.80   1.00   1.30   1.60   2.00
    relieve impreso   0.60   0.76   0.86   1.02   1.18   1.39

Salir más se ve más, pero cada décima extra rinde menos. Y a `puas` fijas hay
un techo: lo que falta a partir de ahí es VALLE, no altura.

## Las dos lecturas de la misma máscara

`invertir=0` —lo de arriba, y el valor por defecto— pone el relieve en la
figura. `invertir=1` lo pone en el fondo y deja la figura lisa, que es como se
lee la lámpara de referencia: la pared entera es un cepillo y las flores son
los claros. El dibujo es el complemento, pero la pieza no: con 0 la boquilla
oscila sólo en la fracción de la vuelta que ocupa la figura.

## Qué hace distinto a `zigzag`

`zigzag` ondula el radio con un triángulo y alterna una vuelta con dientes y
otra lisa: el cordón liso de arriba marca el borde de los de abajo y se lee
como una raya. Acá se busca lo contrario, una púa que se APILE:

- La onda va **solo hacia afuera**. El valle vale exactamente la silueta, así
  que la superficie interior queda limpia y todo el relieve se va para afuera:
  por dentro el tubo es liso, y por eso sigue sirviendo para agua.
- **Todas las vueltas llevan púa y en la misma fase** (`deriva` en 0). Cada púa
  cae encima de la de la vuelta anterior y se apilan en una columna continua.
  Alternando, no habría columna: habría raya.
- El perfil es un **pulso trapecial**, no un triángulo. `ocupacion` dice qué
  fracción de cada paso ocupa la púa: con 0.5 la mitad del recorrido va afuera
  y la otra mitad pegada a la pared, que es lo que separa una púa de la
  siguiente. Un triángulo no separa nada — es una pared ondulada.

## La trampa que hay que respetar: el borde de la figura

En modo vaso el paso vertical es UNO SOLO por vuelta, y `comun.marcha_vertical`
lo achica hasta que la separación real vuelva a valer un cordón, mirando el
PEOR ángulo de la vuelta (ver `.agents/MAPA.md`). El borde de una flor es el
sitio donde la púa deja de existir: si ese borde es duro, dos vueltas vecinas
se llevan la amplitud entera de diferencia en ese ángulo, `marcha_vertical` lo
lee como una pared acostada y desploma el paso de LA PIEZA ENTERA al mínimo.

Por eso la máscara `flores` desvanece su borde en milímetros de superficie y
`construir()` mide el salto por vuelta antes de generar nada y avisa. No es
una precaución teórica: es el mismo mecanismo que en `glitch2` dejó el 26 % de
los cordones irrealizables.

Y por eso `deriva` viene en 0. Torcer las columnas significa que la púa de una
vuelta ya no cae sobre la de la vuelta anterior, o sea el salto entero de
amplitud en cada vuelta, en todos los ángulos a la vez. El módulo lo mide y lo
dice.
"""

import math
from typing import Optional, Tuple

from ..cordon import sobrevive
from ..superficie import Mascara, resolver
from .siluetas import Silueta

TAU = 2 * math.pi


def _pulso(u: float, ocupacion: float, filo: float) -> float:
    """
    Perfil de una púa. `u` es la fase dentro del paso, en [0, 1).

    Vale 0 pegado a la pared y 1 en la punta. `ocupacion` es qué fracción del
    paso ocupa la púa y `filo` qué parte de esa fracción va en la meseta: con
    `filo=1` el flanco es vertical —la boquilla sale de golpe— y con `filo=0`
    la púa es un triangulito.
    """
    if u >= ocupacion:
        return 0.0
    meseta = ocupacion * filo
    rampa = (ocupacion - meseta) / 2
    if rampa <= 1e-9:
        return 1.0
    if u < rampa:
        return u / rampa
    if u < rampa + meseta:
        return 1.0
    return (ocupacion - u) / rampa


def _ventana(t: float, desde: float, hasta: float, suave: float) -> float:
    """
    0 fuera de la banda [desde, hasta], 1 adentro, con rampas suaves.

    `suave` viene en unidades de `t`, pero quien lo llama lo calcula desde
    MILÍMETROS y por un motivo físico, no estético: la rampa es una zona donde
    la púa crece de vuelta en vuelta, o sea exactamente el salto de radio que
    `marcha_vertical` mira para decidir el paso. Un "3 % de la altura" mide
    6 mm en un tubo de 200 y 0.7 mm en una prueba de 24 — dos vueltas— y ahí es
    un escalón duro que aplasta el paso de la prueba entera. Con la rampa en
    mm, la prueba chica se comporta como la pieza grande, que es justo para lo
    que sirve una prueba.
    """
    if t <= desde or t >= hasta:
        return 0.0
    subida = min(1.0, (t - desde) / suave) if suave > 0 else 1.0
    bajada = min(1.0, (hasta - t) / suave) if suave > 0 else 1.0
    u = min(subida, bajada)
    return u * u * (3 - 2 * u)


def _lista(texto: str):
    """Los valores de un barrido, o () si no hay barrido."""
    if not str(texto).strip():
        return ()
    return tuple(float(v) for v in str(texto).replace(" ", "").split(",") if v)


def _bandas(texto: str, por_defecto: float):
    """
    `"0.6,0.9,1.2"` -> una función de t que devuelve el valor de su banda.

    Las bandas parten la altura en tramos IGUALES y el corte es duro: la gracia
    de un cupón es poder decir "la tercera banda se ve bien y la cuarta no", y
    con un degradé entre bandas no hay una tercera banda, hay un continuo del
    que no se puede leer un número.

    Que el corte sea duro cuesta apoyo en la juntura —el radio salta la
    diferencia entre dos bandas de una vuelta a la otra— y por eso `construir()`
    mide el salto sobre la función de radio ya armada, que es la que ve las
    junturas. Con las bandas ordenadas de menor a mayor, cada salto es una sola
    diferencia entre vecinas y no el rango entero.
    """
    if not str(texto).strip():
        return lambda t: por_defecto
    vals = list(_lista(texto))
    if not vals:
        return lambda t: por_defecto
    n = len(vals)
    return lambda t: vals[min(n - 1, max(0, int(t * n)))]


def construir(
    silueta: Silueta,
    altura: float,
    puas: int = 150,
    amplitud: float = 0.9,
    amplitud_fondo: float = 0.35,
    barrido: str = "",
    barrido_puas: str = "",
    flujo: float = 1.0,
    flujo_barrido: str = "",
    ocupacion: float = 0.5,
    filo: float = 0.34,
    lisas: int = 3,
    con_patron: int = 2,
    crecer: int = 1,
    puente_lento: float = 0.35,
    muestras: int = 6,
    mascara="flores",
    invertir: int = 0,
    suave_borde: float = 5.0,
    tomas: int = 5,
    deriva: float = 0.0,
    desde: float = 0.03,
    hasta: float = 0.99,
    suave_mm: float = 5.0,
    altura_capa: float = 0.4,
    ancho_cordon: float = 0.8,
    **par_mascara,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura de la pared en mm.
        puas: cuántas púas entran en una vuelta. Lo que importa de verdad es el
            PASO que resulta, `2·pi·radio / puas`: por debajo de un cordón las
            púas vecinas se funden y vuelve a ser una pared ondulada. El módulo
            imprime el paso en mm para que no haya que hacer la cuenta.
        amplitud: cuánto sale la boquilla en la FIGURA, en mm. Es la perilla
            de "cuánto se ve el dibujo".
        amplitud_fondo: cuánto sale en el resto de la pared, en mm. **No es 0**
            a propósito: el pulso está en toda la pieza y lo que dibuja es la
            DIFERENCIA de intensidad entre el fondo y la figura. Con 0 el
            dibujo queda flotando sobre una pared lisa y se ve el recuadro, que
            es otra pieza. Lo que se lee es `amplitud - amplitud_fondo`.
        barrido: bandas de AMPLITUD a lo alto, para calibrar contra la pieza
            impresa: `"0.6,0.9,1.2,1.5"` parte la altura en cuatro tramos
            iguales y le da a cada uno su vuelo. Vacío = `amplitud` en toda la
            pieza. Es lo que convierte una prueba en un cupón: en vez de
            imprimir cuatro piezas para saber qué largo se ve bien, se imprime
            una y se mira.
        barrido_puas: bandas de CANTIDAD DE PÚAS a lo alto, para comparar
            separaciones en una sola pieza: `"48,60,72"` parte la altura en tres
            tramos y le da a cada uno su paso. Vacío = `puas` en toda la pieza.

            Cada banda tiene que ser un ENTERO o sus columnas salen en hélice
            en vez de apiladas (ver el encabezado). Dentro de una banda las
            columnas se apilan normal; en la juntura entre bandas se corren, y
            eso es justo lo que deja ver dónde empieza cada una.
        flujo: cuánto material se deposita EN EL TURUPE, como factor del ancho
            de cordón. 1.0 es el nominal. Sube la sección sin mover la
            boquilla, que es la otra forma de que el turupe se vea más: más
            lleno en vez de más largo. El fondo siempre va a 1.0.
        flujo_barrido: bandas de `flujo` a lo alto, igual que `barrido`:
            `"1.0,1.2,1.4,1.6"`. Vacío = `flujo` en toda la pieza.

            Los dos barridos son independientes y se pueden usar juntos, pero
            conviene no hacerlo: con los dos a la vez, una banda que sale mal
            no dice cuál de las dos cosas la arruinó.
        crecer: 1 hace que el grumo CREZCA a lo largo de su banda, repartiendo
            el salto; 0 lo saca entero en la primera vuelta con patrón y deja
            que PUENTEE sobre la vuelta lisa de abajo.

            Con 1, el largo del grumo está limitado por
            `con_patron x ancho_de_cordon`, y cada vuelta de crecimiento separa
            una fila de grumos de la siguiente: se paga en resolución del
            dibujo. Con 0 no hay techo y la resolución es la mejor posible, pero
            la punta del grumo se tiende al aire y se descuelga un poco. En la
            pieza de referencia se descuelga, y es parte de cómo se ve.

            Con 0, `puente_lento` es lo que hace que ese puente salga bien.
        puente_lento: qué fracción de la velocidad se usa donde el grumo está
            al aire. **No adelgaza la línea**: la sección la fija la geometría y
            no el `F`, así que bajar la velocidad deposita lo mismo en más
            tiempo.

            Frena sólo en la PUNTA, no en todo el vuelo, y eso está medido en
            la referencia (`Squeezy Fidget Toy.gcode`, ver el bloque de
            `modulacion` en `comun.generar_pieza`): de los 14 segmentos de un
            nodo, 11 van a velocidad plena y 3 a la mitad. Tiende el puente
            rápido —cuanto menos tiempo al aire, menos se descuelga— y frena
            únicamente para pararse y dejar material en el vértice. Frenar todo
            el vuelo hace lo contrario de lo que hay que hacer.
        lisas: cuántas vueltas seguidas van DERECHAS, sin pulsar.
        con_patron: cuántas vueltas seguidas pulsan, después de las lisas. El
            ciclo `lisas + con_patron` se repite hasta arriba. Con `lisas=0` el
            patrón está en todas las vueltas.

            Las vueltas lisas son las costillas continuas que se ven en la
            pieza de referencia entre fila y fila de grumos, y son las que
            atan las columnas entre sí: sin ellas cada columna se sostiene
            sola. Cuesta apoyo —el radio salta la amplitud entera al pasar de
            una vuelta lisa a una con patrón— así que `construir()` lo mide y
            lo dice antes de generar.
        ocupacion: qué fracción del paso ocupa la púa (0..1). 1 no deja valle:
            las púas se tocan y la textura desaparece. Se llama así y no
            "ancho" porque `--ancho-linea` ya es un ancho en mm y son cosas
            distintas: esto es una fracción del paso entre púas.
        filo: qué parte de la púa es meseta. 1 = flancos verticales.
        muestras: puntos de recorrido por púa. **Es un mínimo, no un valor
            fijo**: el módulo lo sube si hace falta para que caiga al menos una
            muestra en la meseta de la púa, porque si no el turupe no llega a
            la altura pedida y cuánto le falta depende de un ángulo que nadie
            eligió. Ver el bloque de arriba. Es lo que fija la resolución
            angular, así que también es lo que fija el tamaño del archivo.
        mascara: dónde va la figura. Por defecto 'flores'. Para mirar la
            textura sola, sin figura: `mascara=ninguna invertir=0`.

            **El dibujo se cuantiza a la rejilla del patrón**, y esa rejilla es
            gruesa: un "punto" mide `2·pi·radio / puas` de ancho por
            `(lisas + con_patron) · altura_capa` de alto. En un Ø50 con 70 púas
            y cadencia 3+3 son 2.24 x 2.40 mm, o sea que la pieza entera son
            70 x 31 puntos. Cualquier rasgo más fino que eso no se dibuja: se
            promedia con lo de al lado y desaparece. Antes de elegir el tamaño
            de una figura conviene dividir sus rasgos por esos dos números —una
            vena de 2 mm es menos de UN punto— y mirarla a esa resolución, no a
            resolución libre con `python -m lamparas.superficie`.
        invertir: **0 (por defecto) = la figura son los TURUPES**: la pared da
            vueltas normales y la boquilla sale y entra sólo donde va el
            dibujo. Es la técnica tal como se pidió, y es lo que se ve en el
            croquis de planta: un círculo liso con las púas asomando en el
            sector dibujado. 1 = al revés, la figura queda lisa y la púa es el
            fondo, que es como se lee la lámpara de referencia.

            El costo de imprimir NO es el mismo en los dos sentidos aunque el
            dibujo sea el complemento: con 0 la boquilla oscila sólo en la
            fracción de la vuelta que ocupa la figura, y el resto del tiempo
            va derecha.
        suave_borde: en cuántos mm de ALTURA se desvanece el borde de la figura,
            y `tomas` con cuántas muestras. No es un parámetro estético: es lo
            que acota el salto de radio por vuelta. Ver abajo.
        deriva: vueltas que rota la textura a lo largo de la altura. **Dejalo en
            0**; ver el docstring del módulo.
        desde, hasta: en qué tramo de la altura (0..1) hay púas. El zócalo liso
            de abajo no es decorativo: es donde la pieza se agarra a la cama.
        suave_mm: en cuántos MILÍMETROS de altura encienden y apagan esas dos
            rampas. En mm y no en fracción a propósito: ver `_ventana`.
        altura_capa: solo para el aviso — cuánto sube una vuelta. No cambia la
            pieza, la altura real la fija `--altura-capa`.
        ancho_cordon: el ancho del cordón, para predecir cuánto del turupe
            sobrevive. Lo pone `bowls.pasos_bowl` desde el perfil de impresión;
            no se pide por `--p`. No cambia la pieza: sólo el aviso.
        **par_mascara: se le pasan a la máscara (para 'flores': cantidad,
            petalos, tamano, corazon, borde_mm, semilla...).

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `funcion_dz` y `paso_z` son None: la Z no se toca, así que la pared sube
    como una capa normal y el tubo queda estanco.
    """
    radio_medio = sum(silueta(k / 8) for k in range(9)) / 9
    fn: Mascara = resolver(mascara, radio_mm=radio_medio, altura_mm=altura,
                           **par_mascara)

    ocupacion = min(1.0, max(0.02, ocupacion))
    filo = min(1.0, max(0.0, filo))

    # --- cuántas muestras por púa: al menos UNA en la meseta ----------------
    #
    # La rejilla angular es pareja y no arranca en la fase de la púa —arranca
    # donde terminó la espiral del piso, que es cualquier ángulo—. Si la meseta
    # de la púa es más angosta que el paso de muestreo, las muestras pueden
    # ESQUIVARLA entera y el turupe no llega nunca a la altura pedida.
    #
    # No es teórico: con `ocupacion=0.30` y `filo=0.34` la meseta mide 0.102
    # del paso contra un muestreo de 1/6 = 0.167, y el g-code depositaba
    # 1.78 mm de los 2.40 pedidos. Y era LOTERÍA: con 95 púas la fase caía bien
    # y salían los 2.40, con 70 caía mal y salían 1.78. La misma pieza, dos
    # alturas, según un ángulo que nadie eligió.
    #
    # Es la misma cuenta que hace `bowls/peine.py` con `muestras_diente`, y por
    # el mismo motivo. Con la meseta por defecto (ocupacion 0.5, filo 0.34) da
    # 6, que es lo que ya se venía usando: ninguna pieza anterior se mueve.
    meseta = ocupacion * filo
    minimo = math.ceil(1.0 / max(meseta, 1e-9))
    m = max(int(muestras) or 0, minimo, 3)
    if m > max(int(muestras) or 0, 3):
        print(f"  muestras {m} por púa (pediste {muestras}): con ocupacion="
              f"{ocupacion:g} y filo={filo:g} la meseta mide {meseta:.3f} del paso "
              f"y un muestreo más grueso la esquiva, así que el turupe no llegaría "
              f"a los {amplitud:.2f} mm.")

    # --- el borde de la figura, promediado EN VERTICAL --------------------
    #
    # El problema, medido: con la máscara evaluada punto a punto, el borde de
    # una flor movía el radio 0.550 mm de una vuelta a la siguiente, y eso hace
    # que `marcha_vertical` achique el paso de la pieza ENTERA (el paso es uno
    # solo por vuelta). El culpable no era el desvanecido de la máscara sino la
    # muesca entre dos pétalos: ahí el contorno corre casi horizontal, así que
    # subir 0.4 mm lo corre 1.7 mm de costado y se come cualquier borde suave
    # que la máscara declare en el plano.
    #
    # Suavizar más la máscara no lo arregla —la cuenta da que harían falta
    # ~11 mm de desvanecido, o sea una flor sin contorno— y depende de la forma
    # de cada figura, así que el próximo dibujo volvería a romperlo.
    #
    # Lo que se hace en cambio es promediar la máscara a lo largo de `tomas`
    # alturas repartidas en `suave_borde` milímetros. Eso ACOTA POR
    # CONSTRUCCIÓN cuánto puede cambiar el peso al subir una vuelta —como mucho
    # lo que aporte una toma— sea cual sea la figura, y deja intactos los bordes
    # VERTICALES, que no cuestan nada porque el ángulo no cambia entre vueltas.
    # Es, además, lo que se ve en la pieza de referencia: las púas se van
    # acortando al acercarse a la flor en vez de cortarse de golpe.
    n = max(1, int(tomas))
    dt_borde = (suave_borde / max(altura, 1e-9)) / n if n > 1 else 0.0
    desplazamientos = [(k - (n - 1) / 2) * dt_borde for k in range(n)]

    def peso(angulo: float, t: float) -> float:
        """Cuánto de FIGURA hay en ese punto: 0 = fondo, 1 = dibujo."""
        m = 0.0
        for d in desplazamientos:
            m += fn(angulo, min(1.0, max(0.0, t + d)))
        m /= n
        if invertir:
            m = 1.0 - m
        return m * _ventana(t, desde, hasta, suave_mm / max(altura, 1e-9))

    # --- la cadencia vertical: vueltas lisas y vueltas con patrón ---------
    #
    # No todas las vueltas pulsan. El ciclo es `lisas` vueltas derechas y
    # después `con_patron` vueltas pulsando, y se repite hasta arriba. Es lo
    # que se ve en la pieza de referencia y no es decorativo: la columna de
    # púas necesita algo de dónde agarrarse. Las vueltas lisas son una pared
    # continua que ata las columnas entre sí; sin ellas cada columna es un
    # hilo suelto sostenido sólo por sí mismo.
    #
    # Cuesta apoyo y por eso hay que medirlo: entre una vuelta lisa y la
    # siguiente con patrón el radio salta la amplitud entera EN ESE ÁNGULO.
    # El grumo apoya sobre la vuelta lisa de abajo y vuela hacia afuera, que
    # es exactamente lo que se ve en la foto — el grumo asomando por encima
    # de las costillas lisas.
    dt_capa = altura_capa / max(altura, 1e-9)
    ciclo = max(0, int(lisas)) + max(1, int(con_patron))

    def pulsa(capa: int) -> bool:
        """True si a esa vuelta le toca patrón."""
        if lisas <= 0:
            return True
        return (capa % ciclo) >= int(lisas)

    def crecida(capa: int) -> float:
        """
        Qué fracción de la amplitud le toca a esa vuelta DENTRO de su banda.

        El grumo no sale entero de una vez: crece a lo largo de las
        `con_patron` vueltas de la banda, así que con 2 vueltas la primera sale
        a la mitad y la segunda entera.

        No es estético, es lo único que hace que la banda se apoye. Saliendo
        entero de golpe, la primera vuelta con patrón se corre la amplitud
        COMPLETA respecto de la vuelta lisa de abajo, y con 1.30 mm contra un
        cordón de 1.0 la punta del grumo queda al aire: medido, 5.90 % de
        muestras sin apoyo contra el 1.88 % de la referencia, o sea NO
        IMPRIMIBLE. Repartido en dos vueltas el salto es la mitad y cada una
        apoya sobre la anterior.

        La bajada de vuelta a la pared lisa no necesita rampa: correrse hacia
        ADENTRO no deja nada al aire — la vuelta lisa se apoya en el valle,
        que vale la silueta en todas las vueltas.
        """
        if lisas <= 0 or not crecer:
            return 1.0
        k = (capa % ciclo) - int(lisas)          # 0 .. con_patron-1
        return (k + 1) / max(1, int(con_patron))

    lista_puas = [max(4, int(round(v))) for v in _lista(barrido_puas)] or [puas]
    puas_de = _bandas(",".join(str(v) for v in lista_puas), puas)
    amp_de = _bandas(barrido, amplitud)
    flujo_de = _bandas(flujo_barrido, flujo)

    def funcion_flujo(angulo: float, t: float) -> float:
        """El factor de sección en ese punto: nominal en el fondo, `flujo` en el turupe."""
        f = flujo_de(t)
        if f == 1.0:
            return 1.0
        capa = math.floor(t / dt_capa)
        if not pulsa(capa):
            return 1.0
        # Sigue la forma del pulso, no un escalón: el turupe se engorda donde
        # está y el valle queda con la sección nominal. Con un escalón, el
        # cambio de sección cae en mitad del flanco y se lee como un anillo.
        n = int(puas_de((capa // ciclo) * ciclo * dt_capa))
        fase = angulo * n / TAU + deriva * t * n
        return 1.0 + (f - 1.0) * _pulso(fase % 1.0, ocupacion, filo)

    def funcion_velocidad(angulo: float, t: float) -> float:
        """Velocidad en ese punto: plena salvo en la punta de un grumo al aire."""
        if crecer or lisas <= 0 or puente_lento >= 1.0:
            return 1.0
        capa = math.floor(t / dt_capa)
        # Sólo la PRIMERA vuelta de la banda tiene la vuelta lisa debajo; de la
        # segunda en adelante cada grumo apoya sobre el de la vuelta anterior.
        if not pulsa(capa) or (capa % ciclo) != int(lisas):
            return 1.0
        # la meseta, o sea el vértice donde la boquilla se para y vuelve
        meseta_ini = (ocupacion - ocupacion * filo) / 2
        if meseta_ini <= fase <= meseta_ini + ocupacion * filo:
            return max(0.05, puente_lento)
        return 1.0

    def radio(angulo: float, t: float) -> float:
        base = silueta(t)
        # `floor` y no `round`: la banda tiene que empezar donde la espiral
        # cierra la vuelta, no a media vuelta de ahí. Con `round` el cambio de
        # lisa a patrón caía en t = (k+0.5)·dt_capa, o sea medio giro corrido
        # del punto donde el recorrido ya tiene su costura, y eso agrega un
        # SEGUNDO escalón helicoidal en vez de esconder el cambio en el que ya
        # existe. Con `floor` los dos coinciden.
        capa = math.floor(t / dt_capa)
        if not pulsa(capa):
            return base
        # El pulso está en TODA la vuelta; lo que cambia es cuánto sale. En el
        # fondo sale `amplitud_fondo` y en la figura `amplitud`, y la máscara
        # interpola entre las dos. Que el fondo también pulse es lo que hace
        # que la pieza se lea como una piel con el dibujo más marcado, y no
        # como un sello pegado sobre una pared lisa.
        # La banda del barrido se lee al ARRANQUE DEL CICLO, no en `t`. Si
        # cambiara a media banda de patrón, el grumo empezaría a crecer con una
        # amplitud y terminaría con otra: el salto de esa vuelta sería el paso
        # del crecimiento MÁS la diferencia entre bandas, y eso no lo tapa
        # ningún cordón (medido: 2.28 mm contra 1.2 en un cupón de 4.8 a 12).
        # Leyéndola al arranque, cada grumo crece entero con una sola amplitud y
        # el cambio de banda cae donde ya hay vueltas lisas.
        amp = amplitud_fondo + (amp_de((capa // ciclo) * ciclo * dt_capa)
                                - amplitud_fondo) * peso(angulo, t)
        amp *= crecida(capa)
        if amp <= 0.0:
            return base
        n = int(puas_de((capa // ciclo) * ciclo * dt_capa))
        fase = angulo * n / TAU + deriva * t * n
        return base + amp * _pulso(fase % 1.0, ocupacion, filo)

    _avisar(silueta, altura, radio_medio, radio, pulsa, lisas, con_patron,
            lista_puas, amplitud, deriva, altura_capa, ocupacion, filo,
            ancho_cordon, _lista(barrido))

    return (radio, None, max(120, max(lista_puas) * m), None, None, funcion_flujo,
            funcion_velocidad)


def _avisar(silueta, altura, radio_medio, radio, pulsa, lisas, con_patron,
            lista_puas, amplitud, deriva, altura_capa, ocupacion, filo,
            ancho_cordon, bandas=()) -> None:
    """
    Los dos números que deciden si esto se imprime, medidos antes de generar.

    Están acá y no en un verificador aparte porque los dos se contestan con la
    función de radio y sin gcode: esperar al gcode para enterarse cuesta
    minutos, y el veredicto sería el mismo.
    """
    diente = lambda f: _pulso(f, ocupacion, filo)  # noqa: E731
    if len(lista_puas) > 1:
        # con barrido de púas cada banda tiene su paso, su hueco y su
        # supervivencia: un solo número sería el de una banda que no existe.
        print(f"Púas: {len(lista_puas)} bandas sobre radio ~{radio_medio:.1f} mm")
        for k, n in enumerate(lista_puas):
            pm = TAU * radio_medio / max(n, 1)
            c, i = sobrevive(diente, radio_medio, ancho_cordon, n, amplitud)
            print(f"    banda {k + 1}: {n:3d} púas · paso {pm:.2f} mm · "
                  f"hueco entre grumos {pm - ancho_cordon:.2f} mm · "
                  f"sobrevive {100 * i / c if c > 1e-9 else 0:.0f} %")
    puas = lista_puas[0]
    paso_mm = TAU * radio_medio / max(puas, 1)
    if len(lista_puas) == 1:
        print(f"Púas: {puas} por vuelta sobre radio ~{radio_medio:.1f} mm -> "
              f"paso {paso_mm:.2f} mm, {amplitud:.2f} mm de vuelo.")

    # Cuánto del vuelo llega a la SUPERFICIE, que es lo único que se ve y se
    # toca. La boquilla no deposita una línea sin espesor sino una cinta de
    # `ancho_cordon`, y esa cinta no entra en un valle más angosto que ella: el
    # g-code puede tener un turupe de 1.0 mm y la pieza salir con una
    # ondulación insinuada. Lo calcula `lamparas/cordon.py` modelando la
    # superficie como la unión de los discos del cordón.
    #
    # Reemplaza al aviso viejo, que era `paso < 1.0 mm`. Esa regla —"el paso
    # tiene que medir un cordón"— es de las que suenan bien y son falsas en las
    # dos direcciones; la tabla del encabezado de `cordon.py` la desmiente con
    # números. Acá no hay regla: hay una cuenta, y cuesta milisegundos contra
    # los minutos que tarda generar el g-code para descubrir que salió liso.
    # Con barrido se informa BANDA POR BANDA: el cupón existe para leer un
    # número por banda contra la pieza impresa, y un promedio de las cinco no
    # se puede comparar con nada.
    if bandas:
        print(f"  cada banda, del turupe al cordón de {ancho_cordon:g} mm:")
        queda = 1.0
        for k, a in enumerate(bandas):
            c, i = sobrevive(diente, radio_medio, ancho_cordon, puas, a)
            q = i / c if c > 1e-9 else 0.0
            queda = min(queda, q)
            print(f"      banda {k + 1}: pide {a:.2f} mm -> quedan {i:.2f} mm "
                  f"({100 * q:.0f} %)")
    else:
        crudo, impreso = sobrevive(diente, radio_medio, ancho_cordon, puas, amplitud)
        queda = impreso / crudo if crudo > 1e-9 else 0.0
        print(f"  del turupe sobrevive el {100 * queda:.0f} % al cordón de "
              f"{ancho_cordon:g} mm: {impreso:.2f} mm de los {crudo:.2f} pedidos.")
    if queda < 0.60:
        print(f"  AVISO: el cordón se come el {100 * (1 - queda):.0f} % del turupe. "
              f"Subir `amplitud` NO lo arregla — lo que falta es VALLE, no altura: "
              f"la cinta no llega al fondo entre dos púas. Bajá `puas`, bajá "
              f"`ocupacion` o poné una boquilla más fina.")

    # Cuánto se corre el radio de una vuelta a la siguiente, en el peor punto
    # de la pieza. Es lo que `comun.marcha_vertical` va a mirar para decidir el
    # paso, y es la regla que gobierna todas las piezas del proyecto:
    #
    #     Δ radio HACIA AFUERA por vuelta < ancho de cordón
    #
    # **Hacia afuera, con signo, y no en valor absoluto.** Los dos sentidos no
    # son lo mismo y confundirlos daba un aviso que gritaba sobre una pieza
    # sana: cuando la banda de patrón termina, la vuelta lisa de arriba se
    # corre 1.3 mm hacia ADENTRO, y eso no deja nada al aire —se apoya en el
    # valle, que vale la silueta en todas las vueltas— mientras que los mismos
    # 1.3 mm hacia afuera son la punta del grumo colgando. Con `abs()` los dos
    # daban 1.30 y el aviso salía igual con la pieza ya arreglada.
    N_A, N_T = 240, 300
    dt = altura_capa / max(altura, 1e-9)
    afuera = 0.0
    for i in range(N_T):
        t = i / (N_T - 1)
        t2 = min(1.0, t + dt)
        for k in range(N_A):
            a = k / N_A * TAU
            afuera = max(afuera, radio(a, t2) - radio(a, t))
    # la silueta también se corre; se informa junta, que es como la ve el paso
    salto_silueta = max(abs(silueta(min(1.0, i / 200 + dt)) - silueta(i / 200))
                        for i in range(201))
    print(f"  salto de radio HACIA AFUERA por vuelta de {altura_capa:.2f} mm: "
          f"{afuera:.3f} mm contra un cordón de {ancho_cordon:g} "
          f"({100 * max(0.0, ancho_cordon - afuera) / max(ancho_cordon, 1e-9):.0f} % "
          f"de solape; la silueta aporta {salto_silueta:.3f}).")
    if lisas > 0:
        print(f"  cadencia: {lisas} vueltas lisas + {con_patron} con patrón, y el "
              f"grumo crece {1 / max(1, int(con_patron)):.0%} de la amplitud por "
              f"vuelta hasta salir entero.")
    # El tamaño del "punto" con el que este patrón puede dibujar. Se imprime
    # SIEMPRE porque es el número que decide si una figura se va a leer, y no
    # se puede deducir mirando la máscara: `lamparas.superficie` dibuja la
    # máscara ideal, no lo que la pieza puede. Una hoja con venas de 2 mm sobre
    # puntos de 2.24 x 2.40 no dibuja venas: dibuja una mancha.
    ancho_punto = TAU * radio_medio / max(puas, 1)
    alto_punto = (max(0, int(lisas)) + max(1, int(con_patron))) * altura_capa
    print(f"  el dibujo se cuantiza a puntos de {ancho_punto:.2f} x {alto_punto:.2f} mm "
          f"-> la pieza son {puas} x {int(altura / max(alto_punto, 1e-9))} puntos. "
          f"Un rasgo más fino que eso no se dibuja.")
    if deriva:
        print(f"  AVISO: `deriva={deriva:g}` desalinea las púas entre vueltas. "
              f"Eso mete un salto de hasta {amplitud:.2f} mm en TODOS los ángulos, "
              f"no solo en el borde de la figura, y el paso vertical se desploma.")
    if afuera > ancho_cordon:
        print(f"  AVISO: {afuera:.2f} mm hacia afuera contra un cordón de "
              f"{ancho_cordon:g}: la vuelta nueva NO solapa con la de abajo y esa "
              f"punta queda al aire. Subí `con_patron` —el grumo crece en más "
              f"vueltas y cada salto es menor—, bajá `amplitud`, o subí "
              f"`suave_borde` si el que salta es el borde de la figura.")
