"""
Rosca macho de la lámpara tornillo, como función de radio.

La hembra no cambia nunca: es el riel helicoidal continuo que ya tienen las
caperuzas. Su perfil no se supone, se midió sobre `tuerca.stl` y vive en
`envolvente_hembra.py`. Todo macho válido queda por debajo de esa envolvente.

Por qué esto es una `FuncionRadio` y no un sólido
-------------------------------------------------
El radio de un tornillo depende del ángulo y de la altura sólo a través de una
variable: la distancia axial al eje del hilo,

    d = z - paso * angulo / (2*pi)     (módulo paso)

así que `radio(angulo, z) = perfil(d)` y entra tal cual en `comun.generar_pieza`.
Los patrones son deformaciones de `perfil`: composición de funciones, no resta
de sólidos. No hay barrido, así que tampoco hay marco de Frenet que tuerza el
perfil, ni una hélice que se pueda desfasar por escribir mal una distancia.

Las dos reglas
--------------
1. CONTENCIÓN  `perfil(d) <= envolvente(d)`. Si se cumple, enrosca. Y como los
   patrones sólo pueden REBAJAR, se cumple por construcción.

2. APOYO       el perfil tiene que tocar la envolvente cada tanto, o la pieza
   se hunde dentro del riel antes de hacer tope.

Medido sobre el STL, el macho actual (`MACHO_ACTUAL`) ya está clavado sobre la
envolvente: le quedan 0.19 mm de holgura radial y 0.45 mm de juego axial, o sea
un 3% del paso. No es que sobre margen para hacerlo más profundo: no sobra nada.
Por eso el perfil clásico es el máximo posible, y todo patrón le quita material.

Voladizo
--------
El perfil clásico sube a 43° desde la vertical: 0.375 mm de radio por cada 0.4
de altura. `generar_pieza` ya lo maneja solo, porque le pasa a `marcha_vertical`
un `delta_radio` medido en el PEOR ÁNGULO de la vuelta y no sobre el radio
medio. Eso importa acá más que en ninguna otra pieza: en una rosca el radio
medio de la vuelta es EXACTAMENTE constante —cada vuelta recorre el perfil
entero, así que el promedio nunca se mueve— y con el promedio el generador
creería que está imprimiendo un cilindro liso.

La consecuencia práctica es que el paso se acorta en toda la altura, no en una
zona: a diferencia de una cúpula, la rosca tiene su punto más tumbado en todas
las vueltas. Con el perfil clásico eso da unos 0.29 mm de subida por vuelta en
lugar de 0.40, o sea ~1.4x más vueltas. Un patrón que grabe con pendientes más
bravas lo acorta todavía más, y ahí es donde deja de convenir.
"""

import math
from typing import Callable, Optional

from .envolvente_hembra import PASO, N, ENVOLVENTE, MACHO_ACTUAL, envolvente

R_NUCLEO = 50.00          # fondo del hilo = pared del tubo
R_HELICE = 50.75          # eje del riel, sólo para convertir arco <-> ángulo

ARCO_RAD = math.hypot(R_HELICE, PASO / (2 * math.pi))
ARCO_VUELTA = 2 * math.pi * ARCO_RAD

# Cuánto arco seguido puede quedar sin rosca sin que la pieza deje de agarrar.
# Es un criterio de diseño, no una medición: con el collarín de 30 mm engranando
# 2.22 vueltas, un hueco de este orden siempre deja rosca a ambos lados.
PASO_APOYO_MAX = 40.0


def coordenada_hilo(angulo: float, z: float) -> float:
    """Fase de hélice en [0, PASO): la posición dentro del perfil del hilo."""
    return (z - PASO * angulo / (2 * math.pi)) % PASO


def _tabla(tab, d):
    x = (d % PASO) / PASO * N
    i = int(x) % N
    f = x - int(x)
    return tab[i] * (1 - f) + tab[(i + 1) % N] * f


def perfil_clasico(d: float) -> float:
    """El perfil que ya imprimís: medido del STL, 2.0 mm de hilo, 43°."""
    return _tabla(MACHO_ACTUAL, d)


def perfil_envolvente(d: float) -> float:
    """El máximo teórico: la hembra menos la holgura."""
    return _tabla(ENVOLVENTE, d)


def rosca(patron: Optional[Callable[..., float]] = None,
          altura: float = 230.0,
          perfil: Callable[[float], float] = perfil_clasico,
          ancho_cordon: float = 0.0) -> Callable[[float, float], float]:
    """
    Devuelve una `FuncionRadio` lista para `comun.generar_pieza`.

    `patron(d, angulo, z, s, r_pleno)` devuelve un factor 0..1 sobre cuánto
    sobresale el hilo (1 = hilo entero, 0 = pared lisa). Como sólo rebaja, la
    contención está garantizada.

    `ancho_cordon` compensa que `generar_pieza` recibe la TRAYECTORIA y no la
    superficie: el cordón va centrado en el recorrido, así que la pared queda
    medio cordón por fuera. Pasale el ancho de línea y el perfil impreso sale
    donde lo pediste. Con 0 no compensa (útil para comparar contra el STL).
    """
    media = ancho_cordon / 2.0

    def funcion_radio(angulo: float, t: float) -> float:
        z = t * altura
        d = coordenada_hilo(angulo, z)
        r = perfil(d)
        if patron is not None and r > R_NUCLEO:
            s = ARCO_RAD * 2 * math.pi * (z - d) / PASO
            k = max(0.0, min(1.0, patron(d, angulo, z, s, r)))
            r = R_NUCLEO + (r - R_NUCLEO) * k
        return r - media

    return funcion_radio


# ---------------------------------------------------------------------- patrones
# Todos reciben (d, angulo, z, s, r_pleno) y devuelven 0..1.
# `r_pleno` viene dado y no se recalcula adentro: si el patrón se arma su propia
# copia del perfil, usa otros parámetros que los de esta rosca y el dibujo sale
# montado sobre una referencia que no existe.

def p_continua(d, angulo, z, s, r_pleno):
    return 1.0


def p_perlas(n_por_vuelta: int = 20, calado: float = 0.55, dureza: float = 3.0):
    """Cuentas: el hilo se estrangula n veces por vuelta y quedan perlas."""
    def f(d, angulo, z, s, r_pleno):
        fase = math.cos(n_por_vuelta * angulo)
        return 1.0 - calado * 4 * (0.5 - 0.5 * fase) ** dureza
    return f


def p_interrumpida(n_sectores: int = 6, hueco: float = 0.35):
    """Bayoneta: n tramos de hilo por vuelta con huecos lisos entre medio."""
    def f(d, angulo, z, s, r_pleno):
        return 0.0 if (angulo * n_sectores / (2 * math.pi)) % 1.0 < hueco else 1.0
    return f


def p_caritas(n_por_vuelta: int = 16, prof_ojo: float = 0.60,
              prof_boca: float = 0.55, r_grabado: float = 51.30,
              grad_max: float = 0.50):
    """
    Caritas felices y tristes alternadas, GRABADAS en la cresta del hilo.

    Sólo hunde material por encima de `r_grabado`. Ahí la superficie del macho
    mira al fondo del riel, o sea que el contacto es radial y no aporta apoyo
    axial: quitarlo sale gratis y el flanco que carga queda intacto.

    `grad_max` es la pendiente del grabado medida EN d, y es lo que decide si se
    imprime: se suma a la del perfil. En el ángulo puede ser todo lo brusco que
    quiera, porque ese cambio pasa dentro de una misma vuelta. Por eso los
    rasgos son elipses finas en ángulo y estiradas en d.
    """
    paso_ang = 2 * math.pi / n_por_vuelta
    ojo_d = max(0.8, prof_ojo * math.pi / (2 * grad_max))
    boca_d = max(0.6, prof_boca * math.pi / (2 * grad_max))
    ojo_u = 1.25
    ancho_cara = ARCO_VUELTA / n_por_vuelta

    def _bulto(dist2, prof):
        return 0.0 if dist2 >= 1.0 else prof * 0.5 * (1 + math.cos(math.pi * math.sqrt(dist2)))

    def f(d, angulo, z, s, r_pleno):
        if r_pleno <= r_grabado:
            return 1.0
        feliz = int(math.floor(angulo / paso_ang)) % 2 == 0
        u = ((angulo / paso_ang) % 1.0 - 0.5) * ancho_cara
        v = d - PASO / 2                      # centro del lomo, no del paso
        corte = 0.0
        for lado in (-1.0, 1.0):
            corte = max(corte, _bulto(((u - lado * 2.9) / ojo_u) ** 2
                                      + ((v - 1.1) / ojo_d) ** 2, prof_ojo))
        if abs(u) < 4.6:
            comba = -1.0 if feliz else 1.0
            v_boca = -0.9 + comba * 0.8 * (1 - (u / 4.6) ** 2)
            corte = max(corte, _bulto(((v - v_boca) / boca_d) ** 2, prof_boca))
        if corte <= 0.0:
            return 1.0
        r_obj = max(r_grabado, r_pleno - corte)
        return (r_obj - R_NUCLEO) / (r_pleno - R_NUCLEO)
    return f


def p_ondas(n_por_vuelta: int = 24, amplitud: float = 0.45):
    """
    El hilo respira: se hace más y menos profundo a lo largo de la vuelta.

    A diferencia de los grabados, esto SÍ toca el apoyo — donde el hilo se
    encoge deja de tocar la envolvente. Por eso `amplitud` no debería pasar de
    ~0.5: con 1.0 el hilo desaparece y la pieza se queda sin rosca en el valle.
    """
    def f(d, angulo, z, s, r_pleno):
        return 1.0 - amplitud * (0.5 - 0.5 * math.cos(n_por_vuelta * angulo))
    return f


def p_chevron(n_por_vuelta: int = 12, ancho: float = 1.6, prof: float = 0.7,
              r_grabado: float = 51.30):
    """
    Muescas en V grabadas en la cresta, apuntando alternadamente arriba y abajo.

    Es el patrón más barato de todos: la V es una discontinuidad en el ÁNGULO,
    y eso pasa dentro de una misma vuelta, así que no cuesta nada de voladizo.
    Lo único que hay que cuidar es el ancho de la muesca EN d.
    """
    paso_ang = 2 * math.pi / n_por_vuelta

    def f(d, angulo, z, s, r_pleno):
        if r_pleno <= r_grabado:
            return 1.0
        u = (angulo / paso_ang) % 1.0
        v = d - PASO / 2
        # la V: el centro de la muesca sube y baja en zigzag con el ángulo
        centro = (abs(u - 0.5) * 4 - 1) * 2.0
        dist = abs(v - centro)
        if dist >= ancho:
            return 1.0
        corte = prof * 0.5 * (1 + math.cos(math.pi * dist / ancho))
        r_obj = max(r_grabado, r_pleno - corte)
        return (r_obj - R_NUCLEO) / (r_pleno - R_NUCLEO)
    return f


def p_moleteado(n_por_vuelta: int = 30, prof: float = 0.55,
                r_grabado: float = 51.30, sesgo: float = 1.4):
    """
    Moleteado: dos familias de surcos cruzados grabados en la cresta.

    `sesgo` es cuánto se inclinan los surcos respecto del hilo. Con 0 quedan
    paralelos al hilo y no se ve nada; cuanto más alto, más rombo.
    """
    def f(d, angulo, z, s, r_pleno):
        if r_pleno <= r_grabado:
            return 1.0
        v = d - PASO / 2
        a = n_por_vuelta * angulo
        onda = math.cos(a + sesgo * v) * math.cos(a - sesgo * v)
        corte = prof * max(0.0, onda)
        if corte <= 0.0:
            return 1.0
        r_obj = max(r_grabado, r_pleno - corte)
        return (r_obj - R_NUCLEO) / (r_pleno - R_NUCLEO)
    return f


# fase de hélice donde el hilo tiene su cresta: es donde hay que poner los
# rasgos para que engranen, y sale de la propia tabla en vez de a ojo
D_CRESTA = PASO * max(range(N), key=lambda i: MACHO_ACTUAL[i]) / N


def caritas_relieve(n_por_vuelta: int = 9, altura: float = 230.0,
                    alto_ojo: float = 3.4, sep_ojos: float = 7.5,
                    alto_boca: float = 2.9, largo_boca: float = 17.0,
                    comba: float = 2.6,
                    pend_max: float = 1.0, ancho_cordon: float = 0.0):
    """
    Caritas felices y tristes en RELIEVE, con los ojos en una fila de rosca y la
    boca en la siguiente.

    Por qué no se puede con `p_lienzo`
    ----------------------------------
    Aquél sólo prende y apaga el hilo a lo largo de su fila: no puede mover un
    rasgo dentro de la banda ni curvarlo. Y la curvatura de la boca no es
    decorativa — es lo que le da los dos apoyos. Los extremos de la sonrisa
    suben y tocan el flanco de arriba del riel, el medio baja y toca el de
    abajo. La cara resuelve sola la regla de apoyar en ambos flancos.

    Cada rasgo tiene una fila ENTERA para él, 13.5 mm de banda. Meter ojos y
    boca en la misma fila es lo que arruinó los intentos anteriores: había que
    repartir 6.3 mm de relieve completo entre los dos y los ojos terminaban
    aplastados a 1.05 mm.

        fila k+1    ●   ●          ojos
        fila k     ●         ●     boca: cadena de bultos sobre una parábola
                     ● ● ●

    Contención garantizada por recorte contra la envolvente medida:

        r = min(envolvente(d), núcleo + campana)

    Un bulto que se pase sale achatado contra el techo del riel en vez de
    interferir. Y ese recorte es justamente lo que produce el contacto: los
    extremos de la boca, al subir, quedan tocando el flanco.

    Los bultos son campanas de coseno y no casquetes esféricos. Una esfera llega
    a la pared con tangente vertical y un solo rasgo así le parte la capa a la
    pieza entera: medido con esferas D4, capa 0.152 mm en vez de 0.306 y 63.5 %
    de cordón pisado. `pend_max` acota la pendiente en `d`, que es el eje caro;
    en el ángulo se puede ser todo lo brusco que se quiera.
    """
    media = ancho_cordon / 2.0
    paso_ang = 2 * math.pi / n_por_vuelta
    ancho_cara = ARCO_VUELTA / n_por_vuelta
    techo = max(ENVOLVENTE) - R_NUCLEO

    # La banda útil del riel NO está centrada en la cresta del hilo.
    #
    # El techo plano de la envolvente va de v=-1.65 a v=+5.00, o sea que su
    # centro está en +1.67. Centrar los rasgos en la cresta (v=0) los deja
    # colgando hacia abajo: medido, tocaban el talud inferior a v=-1.70 y nunca
    # llegaban al superior, así que la pieza tenía tope en un solo sentido.
    #
    # Centrados en la banda y con el radio justo para cubrirla, cada rasgo toca
    # LOS DOS taludes, que es la regla de apoyo desde el principio.
    _vs = [k / 40 for k in range(-280, 281)]
    _plano = [v for v in _vs if envolvente(D_CRESTA + v) >= max(ENVOLVENTE) - 0.05]
    V_LO, V_HI = min(_plano), max(_plano)
    # v0 = 0: los rasgos van centrados en la CRESTA del hilo.
    #
    # Centrarlos en el medio de la meseta del riel (v0 = +1.68) es mejor en
    # todo lo que se puede medir: la pendiente máxima baja de 1.57 a 0.92
    # —mejor que el propio hilo liso, 1.25— y con eso la altura de capa deja de
    # bandearse (desvío 0.020 contra 0.041). Pero DESHACE EL DIBUJO: mirado en
    # el desenrollado del g-code, las caritas se convierten en bloques rayados.
    # Se probó con el cálculo unificado de fila/v, que es lo que evita que el
    # rasgo se parta al cruzar el borde del paso, y aun así.
    #
    # Queda como está hasta entender por qué. El bandeado de altura de capa es
    # el precio, y es visible en el mapa de Orca: 0.230 a 0.383 mm con período
    # de dos filas, o sea una carita.
    v0 = 0.0
    rv = (V_HI - V_LO) / 2 + 0.03

    rv_ojo = rv_boca = rv
    ru_ojo, ru_boca = alto_ojo, alto_boca


    # La grilla de caras se alinea con la COSTURA del redondeo de fila.
    #
    # `fila` sale de round((z-d+D_CRESTA)/PASO), y ese redondeo salta un entero
    # a un ángulo fijo —0.5 - D_CRESTA/PASO de vuelta, unos 307°—. La cara que
    # cae encima de ese salto queda partida: los ojos de una fila y la boca de
    # la siguiente. Con 9 caras por vuelta es una de cada nueve, y son las que
    # se ven raras en el preview.
    #
    # Corriendo la grilla para que un BORDE de cara caiga justo en la costura,
    # el salto pasa entre dos caras y ninguna se parte.
    desfase = ((0.5 - D_CRESTA / PASO) * n_por_vuelta) % 1.0

    def campana(du, dv, ru, rv):
        q = math.hypot(du / ru, dv / rv)
        return 0.0 if q >= 1.0 else techo * 0.5 * (1 + math.cos(math.pi * q))

    def campana_curva(u, v, signo):
        """
        La boca como una CURVA continua, no como una cadena de bultos.

        Se toma el punto más cercano de la parábola dentro del largo de la boca
        —recortando `u` a los extremos, que además da las puntas redondeadas— y
        se levanta la campana sobre esa distancia. El resultado es un cordón
        liso en vez de un rosario.

        La pendiente en `d` la sigue fijando `rv`, igual que en un bulto suelto:
        que la curva se incline en `u` no cuesta nada, porque el ángulo es el
        eje libre.
        """
        media_l = largo_boca / 2
        ue = max(-media_l, min(media_l, u))
        vb = signo * comba * ((ue / media_l) ** 2 - 0.5)
        return campana(u - ue, v - vb, ru_boca, rv_boca)

    def funcion_radio(angulo: float, t: float) -> float:
        z = t * altura
        # `fila` y `v` salen del MISMO cálculo, o el rasgo se parte.
        #
        # Antes `v` se medía respecto del centro de la banda y `fila` se
        # redondeaba a partir de la cresta: los dos bordes no coincidían, así
        # que un rasgo que cruzaba el final del paso quedaba con la mitad de
        # arriba asignada a la fila SIGUIENTE, donde no existe. Medido, un
        # escalón de 0.9 mm de radio con pendiente 44, que le pedía a
        # `marcha_vertical` pasos de 0.009 mm y dejaba el 10.7 % del recorrido
        # con el cordón por debajo de 0.10.
        #
        # Con una sola cuenta —posición en unidades de paso respecto del centro
        # de la banda— la parte entera es la fila y la fraccionaria es `v`, y el
        # corte cae siempre a media banda de distancia de cualquier rasgo.
        d = coordenada_hilo(angulo, z)
        v = (d - D_CRESTA + PASO / 2) % PASO - PASO / 2 - v0
        fila = int(round((z - (d - D_CRESTA)) / PASO))
        u = (((angulo / paso_ang) - desfase) % 1.0 - 0.5) * ancho_cara

        bulto = 0.0
        if fila % 2 == 1:                                  # fila de ojos
            for lado in (-1.0, 1.0):
                bulto = max(bulto, campana(u - lado * sep_ojos / 2, v,
                                           ru_ojo, rv_ojo))
        else:                                              # fila de boca
            feliz = (fila // 2) % 2 == 0
            bulto = campana_curva(u, v, 1.0 if feliz else -1.0)

        # El rasgo se RECORTA contra la envolvente, no se escala por ella.
        #
        # El recorte es lo que le da forma: la cima queda plana y el contorno
        # sigue la curva de la boca, que es lo que se lee como sonrisa. Escalado
        # se ve la cúpula suave entera y la cara se convierte en un borrón.
        #
        # Se probó escalar creyendo que el codo del recorte era el que hacía
        # que `marcha_vertical` achicara el paso hasta PASO_MINIMO. No era: eso
        # venía de que `fila` y `v` salían de dos cuentas distintas y partía los
        # rasgos en el borde del paso. Con eso arreglado el recorte no cuesta
        # nada, y además es el que produce el contacto con los flancos.
        return min(envolvente(d), R_NUCLEO + bulto) - media

    return funcion_radio

def _rho_estrella(fi, puntas=5, valle=0.45):
    """Estrella de `puntas` picos, con una punta mirando hacia arriba."""
    return valle + (1 - valle) * abs(math.cos(puntas * (fi - math.pi / 2) / 2))


def _rho_corazon(fi):
    """
    Curva de corazón clásica en polar: cúspide arriba, punta abajo.

    `fi` va SIN desfase, y eso no es un detalle. Con `fi + pi/2` el radio queda
    en función de `cos(fi)`, que es par, y la figura sale simétrica respecto del
    eje HORIZONTAL: una hoja apuntando al costado, no un corazón. La simetría
    tiene que ser respecto del eje vertical, o sea `rho(fi) == rho(pi - fi)`,
    que es lo que dan `sin(fi)` y `|cos(fi)|`.

    El piso de 0.05 evita que el radio valga exactamente cero en la cúspide sin
    rellenarla: con 0.30 la hendidura desaparecía y era justo lo que hace que un
    corazón se lea como corazón.
    """
    s, c = math.sin(fi), math.cos(fi)
    return max(0.05, 2 - 2 * s + s * math.sqrt(abs(c)) / (s + 1.4))


def _rho_circulo(fi):
    return 1.0


FORMAS = {"estrella": _rho_estrella, "corazon": _rho_corazon, "circulo": _rho_circulo}


def _encuadre(rho, n=1440):
    """
    Caja del contorno en el plano del sello: (cx, hx, cy, hy).

    Normalizar por el radio máximo no alcanza: en un corazón el máximo está en
    la punta de abajo, así que la figura queda chica y corrida hacia abajo
    (medido: 2.75 mm de los 6.75 de banda). Lo que hay que hacer es encuadrar la
    figura en su caja, no en su radio.
    """
    xs, ys = [], []
    for i in range(n):
        fi = 2 * math.pi * i / n
        r = rho(fi)
        xs.append(r * math.cos(fi)); ys.append(r * math.sin(fi))
    return ((max(xs) + min(xs)) / 2, (max(xs) - min(xs)) / 2,
            (max(ys) + min(ys)) / 2, (max(ys) - min(ys)) / 2)



def sellos_relieve(forma: str = "corazon", n_por_vuelta: int = 16,
                   altura: float = 230.0, pend_max: float = None,
                   ancho_rel: float = 1.35, girar_alternos: bool = True,
                   borde_mm: float = 1.75, ancho_cordon: float = 0.0):
    """
    Un sello repetido a lo largo de la hélice, en relieve, con la misma técnica
    que `caritas_relieve`: campana de coseno recortada contra la envolvente.

        r = min(envolvente(d), núcleo + campana(contorno))

    `ancho_rel` estira el sello en el ÁNGULO, que es el eje gratis: agrandarlo
    ahí no cuesta ni una capa. El tamaño en `d` NO se elige, sale de la banda
    que deja la hembra.

    El radio MÍNIMO del contorno —el valle de una estrella, la muesca de un
    corazón— es el que fija la pendiente, no el radio medio. Por eso se barre el
    contorno entero para medirlo, y si no entra en `pend_max` se baja el alto
    del relieve en vez de dejar que la capa se parta sola.

    `girar_alternos` da vuelta un sello de cada dos, el equivalente de las
    caritas felices y tristes: rompe las columnas verticales que aparecen cuando
    `n_por_vuelta` es par.
    """
    media = ancho_cordon / 2.0
    paso_ang = 2 * math.pi / n_por_vuelta
    ancho_cara = ARCO_VUELTA / n_por_vuelta
    rho = FORMAS[forma]
    cx, hx, cy, hy = _encuadre(rho)
    alto = max(ENVOLVENTE) - R_NUCLEO

    techo = max(ENVOLVENTE)
    vs = [k / 20 for k in range(-140, 141)]
    plano = [v for v in vs if envolvente(D_CRESTA + v) >= techo - 0.05]
    v_lo, v_hi = min(plano), max(plano)
    v0 = (v_lo + v_hi) / 2
    sv = (v_hi - v_lo) / 2

    su = sv * ancho_rel

    def _bulto(u, v, h):
        """
        Meseta: altura plena adentro del contorno, borde suave cerca de él.

        Una campana centrada en el origen polar no sirve para cualquier forma.
        En un corazón el origen polar no está en el medio de la figura, así que
        el domo queda descentrado y la punta de abajo se desvanece (medido: la
        mitad inferior del sello sin relieve). Con meseta la figura sale entera
        y el único parámetro que importa es cuánto dura el borde.
        """
        if abs(u) > su or abs(v) > sv:
            return 0.0
        a, b = cx + u / su * hx, cy + v / sv * hy
        q = math.hypot(a, b)
        if q == 0.0:
            return h
        lim = rho(math.atan2(b, a))
        if q >= lim:
            return 0.0
        # El borde se mide en MILÍMETROS de `d`, no en fracción del radio del
        # contorno. Con fracción, un valle de radio chico —los de una estrella—
        # sube el relieve entero en medio milímetro y la pendiente se dispara:
        # medido, capa 0.101 mm y 96 % de cordón pisado. En mm la pendiente
        # queda acotada por h*pi/(2*borde_mm) sea cual sea la forma.
        e = (lim - q) * sv / hy                # distancia al borde, en mm de d
        if e >= borde_mm:
            return h
        return h * 0.5 * (1 - math.cos(math.pi * e / borde_mm))

    # La pendiente se MIDE barriendo el sello, no se deduce. La fórmula cerrada
    # supone que el contorno manda por su radio, y en uno con picos y valles
    # —una estrella, la cúspide de un corazón— no manda: la pendiente peor
    # aparece cruzando un valle, no yendo al centro. Deducirla dejaba la
    # estrella en 46 % de solape creyendo que estaba en 67 %.
    paso = 0.02
    peor = 0.0
    for iu in range(-60, 61):
        u = iu * su / 60 * 1.4
        for iv in range(-60, 61):
            v = iv * sv / 60 * 1.4
            peor = max(peor, abs(_bulto(u, v + paso, alto) - _bulto(u, v, alto)) / paso)
    # `pend_max=None` deja el sello a la altura completa y con los bordes
    # afilados. No es lo mismo que ignorar el voladizo: acotar la pendiente EN
    # TODAS PARTES es demasiado conservador, porque lo que se descuelga no es la
    # pendiente sino el ARCO SEGUIDO que queda al aire. Un borde que cruza la
    # hélice en diagonal saca el cordón hacia afuera dentro de la misma vuelta y
    # no le pide apoyo a nadie; sólo duele donde el contorno corre paralelo a la
    # hélice. Con el guard puesto, corazón y estrella quedaban en 0.68 y 0.89 mm
    # de relieve contra los 1.97 que hacen falta para tocar el riel: no
    # enroscaban. Sin él quedan escalonados, y eso lo decide el verificador
    # sobre el g-code, no una fórmula acá.
    if pend_max is not None and peor > pend_max:
        alto *= pend_max / peor

    def funcion_radio(angulo: float, t: float) -> float:
        z = t * altura
        d = coordenada_hilo(angulo, z)
        v = (d - D_CRESTA + PASO / 2) % PASO - PASO / 2 - v0
        u = ((angulo / paso_ang) % 1.0 - 0.5) * ancho_cara
        if girar_alternos and int(math.floor(angulo / paso_ang)) % 2:
            v = -v
        return min(envolvente(d), R_NUCLEO + _bulto(u, v, alto)) - media

    return funcion_radio


def p_sello(forma: str = "corazon", n_por_vuelta: int = 16, prof: float = 0.60,
            r_grabado: float = 51.30, grad_max: float = 0.50,
            ancho_rel: float = 1.35, girar_alternos: bool = True,
            borde_mm: float = 1.0):
    """
    Sellos (corazón, estrella, círculo) GRABADOS en la cresta del hilo.

    Es la contracara de `sellos_relieve`, y existe porque aquello no funciona
    para formas con esquinas: un contorno con picos y valles no puede ser alto y
    manso a la vez en la banda de 6.75 mm que deja la hembra. Medido, el guard
    de pendiente les baja el relieve a 0.68 mm (corazón) y 0.89 (estrella)
    contra los 1.97 que hacen falta para tocar el techo del riel: no enroscan.

    Grabado no tiene ese problema. El hilo sigue siendo el hilo clásico, agarra
    al 100 %, y la forma se lee en hueco sobre la cresta. Como sólo quita
    material, la contención está garantizada.
    """
    paso_ang = 2 * math.pi / n_por_vuelta
    ancho_cara = ARCO_VUELTA / n_por_vuelta
    rho = FORMAS[forma]
    cx, hx, cy, hy = _encuadre(rho)
    sv = max(1.4, prof * math.pi / (2 * grad_max))
    su = sv * ancho_rel

    def f(d, angulo, z, s, r_pleno):
        if r_pleno <= r_grabado:
            return 1.0
        v = (d - D_CRESTA + PASO / 2) % PASO - PASO / 2
        if girar_alternos and int(math.floor(angulo / paso_ang)) % 2:
            v = -v
        u = ((angulo / paso_ang) % 1.0 - 0.5) * ancho_cara
        if abs(u) > su or abs(v) > sv:
            return 1.0
        a, b = cx + u / su * hx, cy + v / sv * hy
        q = math.hypot(a, b)
        lim = rho(math.atan2(b, a)) if q > 0 else 1.0
        if q >= lim:
            return 1.0
        e = (lim - q) * sv / hy
        corte = prof if e >= borde_mm else prof * 0.5 * (1 - math.cos(math.pi * e / borde_mm))
        r_obj = max(r_grabado, r_pleno - corte)
        return (r_obj - R_NUCLEO) / (r_pleno - R_NUCLEO)
    return f


# ------------------------------------------------------------------- lienzo
# La rosca como pantalla de puntos: cada vuelta es una FILA y encender o apagar
# tramos de hilo dibuja. Es `p_perlas` generalizado — aquél modula con un coseno
# del ángulo, esto modula con una imagen cualquiera.
#
# El lienzo es el cilindro desenrollado: 2*pi*R de ancho por la altura de alto.
# La resolución vertical NO se elige: es el paso, porque sólo hay una fila de
# hilo cada 13.5 mm. La horizontal es libre.
#
#     tubo de 230 mm -> 23 columnas x 17 filas con píxel cuadrado de 13.3 mm
#
# Las columnas salen verticales (una fila sube un paso entero al dar la vuelta,
# así que a ángulo fijo los píxeles se apilan a plomo). Lo que se inclina es la
# fila, 2.4°, y por eso hay costura: el último píxel de una fila toca al primero
# de la fila de ARRIBA, no al de la suya.

def imagen_circulos(diametro: float = 52.0, por_vuelta: int = 5,
                    alto_fila: float = 58.0, alternar: bool = True):
    """Rejilla de círculos grandes sobre el cilindro desenrollado."""
    ancho = 2 * math.pi * R_HELICE
    paso_u = ancho / por_vuelta
    rad = diametro / 2

    def f(u, v):
        fila = math.floor(v / alto_fila)
        vc = (fila + 0.5) * alto_fila
        corr = paso_u / 2 if (alternar and fila % 2) else 0.0
        mejor = 9e9
        for k in (-1, 0, 1):
            uc = (math.floor((u - corr) / paso_u) + k + 0.5) * paso_u + corr
            mejor = min(mejor, math.hypot(u - uc, v - vc))
        return max(0.0, min(1.0, (rad - mejor) / 3.0))
    return f


def p_lienzo(imagen, altura: float = 230.0, portadora_n: int = 9,
             portadora_frac: float = 0.34, suave: float = 0.10,
             invertir: bool = False):
    """
    Enciende y apaga el hilo según una imagen dibujada sobre el cilindro
    desenrollado. `imagen(u, v) -> 0..1`, con `u` la posición circunferencial en
    mm y `v` la altura en mm.

    La imagen se evalúa en la LÍNEA DEL HILO, no en la Z del punto. Es lo que
    hace que esto salga gratis en impresión: `z - (d - D_CRESTA)` es la altura
    de la cresta de esta vuelta de rosca, y vale lo mismo en todo el corte
    transversal del diente Y entre vueltas de impresión consecutivas —las dos
    suben lo mismo, así que la diferencia no cambia. El patrón entonces sólo
    varía con el ÁNGULO, que es el eje que no cuesta capa.

    Evaluar en `z` a secas cortaría el perfil del diente en horizontal y metería
    la pendiente que venimos esquivando todo el tiempo.

    LA PORTADORA
    ------------
    `portadora_n` tacos de rosca a profundidad plena por vuelta, garantizados en
    TODAS las filas, con el dibujo encima (se toma el máximo de los dos).

    No es decoración: sin ella el dibujo deja filas enteras sin rosca y la pieza
    deja de enroscar a esa altura. Medido sobre las primeras versiones, con
    17 filas en 230 mm:

        círculos y cuadros   4 filas vacías, huecos de 272-285 mm
        corazones            5 vacías, dos de ellas SEGUIDAS
        estrellas            7 vacías, tres SEGUIDAS -> 40 mm de tubo liso

    Y la peor posición de caperuza daba 0 de 2 filas con rosca: ahí no agarra
    nada. Un dibujo cualquiera no puede garantizar cobertura por fila, así que
    la cobertura la pone la portadora y el dibujo sólo agrega.

    `portadora_frac` es qué parte de cada período va con rosca. Con 9 tacos al
    34 % quedan huecos de ~23 mm, muy por debajo de los 40 que nos pusimos como
    tope.
    """
    # Qué filas necesitan portadora: se calcula UNA vez, muestreando la imagen.
    #
    # Aplicarla a TODAS convierte los tacos en columnas verticales que atraviesan
    # el dibujo y lo tapan: con la estrella no se veía nada. Sólo la llevan las
    # filas que el dibujo deja realmente sin agarre.
    #
    # Y el criterio es el HUECO CONTIGUO, no la cobertura. Con cobertura, la
    # fila de ojos de una carita —16 %, pero repartido en diez tramos con huecos
    # de 27 mm— salía marcada como flaca y la portadora le pasaba por encima.
    # Lo que hace que una fila no agarre no es tener poco material sino tenerlo
    # todo junto en un lado.
    flacas = set()
    _n = 180
    _paso_arco = ARCO_VUELTA / _n
    # La fila `m` es la que el patrón lee como v = PASO*m, y sus puntos NO
    # arrancan en ángulo 0: el redondeo la corre. Hay que barrerla desde su
    # propio arranque o se indexa mal — con `_k` en vez de `m` la portadora caía
    # una fila más abajo de donde hacía falta y el hueco de 285 mm seguía ahí.
    _a0_frac = -0.5 - D_CRESTA / PASO
    for _m in range(0, int(altura / PASO) + 2):
        _hay = []
        for _i in range(_n):
            _a = 2 * math.pi * (_m + _a0_frac + _i / _n)
            _z = D_CRESTA + PASO * _a / (2 * math.pi)
            _hay.append(0.0 <= _z <= altura and
                        imagen(R_HELICE * (_a % (2 * math.pi)), PASO * _m) >= 0.95)
        _h = _c = 0
        for _j in range(2 * _n):
            _c = 0 if _hay[_j % _n] else _c + 1
            _h = max(_h, _c)
        if min(_h, _n) * _paso_arco > PASO_APOYO_MAX:
            flacas.add(_m)

    def f(d, angulo, z, s, r_pleno):
        u = R_HELICE * angulo
        # Altura de la cresta de esta vuelta, CUANTIZADA a la fila.
        #
        # Sin cuantizar, `z - (d - D_CRESTA)` sube un paso entero a lo largo de
        # la vuelta, así que una misma fila de hilo cruza de una banda del
        # dibujo a la siguiente y la imagen sale rayada en diagonal y cortada a
        # la mitad. Redondeando al múltiplo del paso, toda la fila lee la misma
        # altura y el dibujo sale limpio.
        #
        # El precio es que la imagen queda inclinada 2.4° sobre el cilindro —el
        # ángulo de la hélice— porque las filas son helicoidales y no anillos.
        # A esa escala no se ve, y es mucho mejor que el rayado.
        v = PASO * round((z - (d - D_CRESTA)) / PASO)
        dib = imagen(u, v)
        if invertir:
            # El hilo va COMPLETO y el dibujo se hace con los huecos.
            #
            # Con el dibujo en positivo cada rasgo mide unos 8 mm de alto —lo
            # que mide el hilo— y las filas están a 13.5, así que entre marca y
            # marca hay 5.5 mm de nada. Una cara son tres marcas separadas por
            # huecos tan grandes como ellas, y a esa densidad no se lee como
            # cara: se lee como textura. Invertido hay una retícula continua
            # contra la cual leer los huecos, y además la rosca engarza en toda
            # su longitud, así que no hace falta portadora.
            return 1.0 - dib
        if portadora_n <= 0:
            return dib
        if invertir or round(v / PASO) not in flacas:
            return dib                      # esta fila se sostiene sola
        fase = (angulo * portadora_n / (2 * math.pi)) % 1.0
        borde = min(fase, portadora_frac - fase) / suave
        port = max(0.0, min(1.0, borde + 0.5)) if fase < portadora_frac else 0.0
        return max(dib, port)
    return f


def imagen_cuadros(lado: float = 40.0, por_vuelta: int = 5,
                   alto_fila: float = 54.0, alternar: bool = True,
                   suave: float = 3.0):
    """Rejilla de cuadros grandes sobre el cilindro desenrollado."""
    ancho = 2 * math.pi * R_HELICE
    paso_u = ancho / por_vuelta
    h = lado / 2

    def f(u, v):
        fila = math.floor(v / alto_fila)
        vc = (fila + 0.5) * alto_fila
        corr = paso_u / 2 if (alternar and fila % 2) else 0.0
        mejor = 9e9
        for k in (-1, 0, 1):
            uc = (math.floor((u - corr) / paso_u) + k + 0.5) * paso_u + corr
            mejor = min(mejor, max(abs(u - uc), abs(v - vc)))
        return max(0.0, min(1.0, (h - mejor) / suave))
    return f


def imagen_forma(forma: str = "corazon", ancho_sello: float = 46.0,
                 alto_sello: float = 46.0, por_vuelta: int = 5,
                 alto_fila: float = 54.0, alternar: bool = True,
                 suave: float = 3.0):
    """
    La misma forma polar de `FORMAS`, pero dibujada COMO IMAGEN en el lienzo en
    vez de levantada como sello en relieve.

    Es la salida al problema que tenían `sellos_relieve` con corazones y
    estrellas: un contorno con esquinas obliga a `marcha_vertical` a afinar la
    capa de la pieza entera, y de ahí salía el choque (64 % en el corazón, 10 %
    en la estrella). Acá la forma no modela el PERFIL del diente —que sigue
    siendo el clásico, manso— sino DÓNDE HAY diente. Y eso sólo varía con el
    ángulo, que es el eje que no cuesta nada.

    La contrapartida es la resolución: el dibujo se cuantiza a filas de 13.5 mm,
    así que un corazón de 46 mm sale en 3 o 4 filas. Es tramado grueso, no
    contorno fino.
    """
    ancho = 2 * math.pi * R_HELICE
    paso_u = ancho / por_vuelta
    rho = FORMAS[forma]
    cx, hx, cy, hy = _encuadre(rho)

    def dentro(du, dv):
        a, b = cx + du / (ancho_sello / 2) * hx, cy + dv / (alto_sello / 2) * hy
        q = math.hypot(a, b)
        if q == 0.0:
            return 1.0
        lim = rho(math.atan2(b, a))
        return max(0.0, min(1.0, (lim - q) / lim * (ancho_sello / 2) / suave))

    def f(u, v):
        fila = math.floor(v / alto_fila)
        vc = (fila + 0.5) * alto_fila
        corr = paso_u / 2 if (alternar and fila % 2) else 0.0
        mejor = 0.0
        for k in (-1, 0, 1):
            uc = (math.floor((u - corr) / paso_u) + k + 0.5) * paso_u + corr
            mejor = max(mejor, dentro(u - uc, v - vc))
        return mejor
    return f


def imagen_caritas(por_vuelta: int = 6, ancho_cara: float = 0.80,
                   ojo: float = 0.30, hueco_ojos: float = 0.14,
                   boca: float = 0.33, hueco_boca: float = 0.16,
                   suave: float = 2.5):
    """
    Caritas felices y tristes: TRES filas de rosca por cara, con bloques
    grandes. Las medidas van en FRACCIÓN del ancho de cara, no en mm, para que
    la proporción se mantenga al cambiar `por_vuelta`.

        fila 2   ████   ████     ojos: dos bloques
        fila 1  ██          ██   aire en el medio, hilo en los bordes
        fila 0   █████  █████    boca: dos bloques, partida al medio

    Dos cosas que salieron de mirar el g-code como imagen y no como función:

    LOS RASGOS SON BLOQUES, no barras finas. Un segmento de 7 mm sobre una cara
    de 40 se pierde entre el rayado del propio hilo; uno que ocupa un tercio de
    la cara se lee.

    LA FILA DE AIRE NO PUEDE ESTAR VACÍA DE PUNTA A PUNTA. Como todas las caras
    se alinean, una fila vacía da la vuelta entera y deja un anillo de tubo liso
    —medido, 27 mm a z 40 y a z 135, con el rango radial en 0.05 mm— que se ve
    como una banda rara y donde la rosca no engancha. Acá el aire es sólo el
    ancho de la cara: en los márgenes entre cara y cara el hilo sigue.

    La boca va PARTIDA AL MEDIO. Entera se lee como una raya recta, no como
    boca.
    """
    circunf = 2 * math.pi * R_HELICE
    paso_u = circunf / por_vuelta
    W = paso_u
    FILAS = 3
    alto_cara = FILAS * PASO

    def bloque(du, centro, largo):
        return max(0.0, min(1.0, (largo / 2 - abs(du - centro)) / suave + 0.5))

    def f(u, v):
        cara = math.floor(v / alto_cara)
        feliz = cara % 2 == 0
        fila = int(round((v - cara * alto_cara) / PASO))
        du = ((u / paso_u) % 1.0 - 0.5) * W
        media = ancho_cara * W / 2

        if fila == 2:                                     # ojos
            c = (hueco_ojos + ojo) * W / 2
            return max(bloque(du, -c, ojo * W), bloque(du, c, ojo * W))
        if fila == (1 if feliz else 0):                   # aire, sólo en la cara
            return 0.0 if abs(du) < media else 1.0
        c = (hueco_boca + boca) * W / 2                   # boca partida
        return max(bloque(du, -c, boca * W), bloque(du, c, boca * W))
    return f
