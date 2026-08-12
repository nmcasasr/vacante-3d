"""
Deformaciones de la ESTRUCTURA: los bultos grandes que doblan el cuerpo entero.

Es otra escala que los patrones de `bowls/`. Un patrón es textura —décimas de
milímetro, muchos ciclos por vuelta, se ve de cerca. Una deformación de
estructura son varios milímetros y uno o dos ciclos en toda la pieza: cambia la
silueta, y las líneas de capa la revelan al curvarse alrededor.

Y por eso mismo se COMBINAN en vez de competir: la estructura mueve el cuerpo,
el patrón raya la superficie de ese cuerpo. Una deformación se suma encima del
radio que devuelva el patrón que sea, sin que el patrón se entere:

    radio_final(a, t) = patron(a, t) + deformacion(a, t)

Ver `bowls/__init__.pasos_bowl(deformacion=...)`.

## Por qué se anula arriba y abajo

Todos los modos van con `sin(k·π·t)`, que vale 0 en `t=0` y en `t=1`. O sea que
la deformación nace y muere sola: la base queda plana y redonda para apoyar en
la cama, y la boca también. Sin eso, un bulto en la primera capa levanta la
pieza de un lado, y un bulto en la boca deja un borde ondulado que se ve
descuidado en vez de intencional.
"""

import math
from typing import Callable

# (angulo_rad, t) -> cuánto se corre el radio en mm, positivo hacia afuera
Deformacion = Callable[[float, float], float]

TAU = 2 * math.pi


def _fases(semilla: int, n: int):
    """
    Fases y frecuencias reproducibles a partir de una semilla.

    Generador propio y no `random`: así la misma semilla da la misma pieza en
    cualquier máquina y en cualquier versión de Python, que es lo que uno
    quiere cuando encontró un bulto que le gusta y lo quiere volver a imprimir.
    """
    x = (semilla * 2654435761 + 1013904223) & 0xFFFFFFFF
    for _ in range(n):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        yield x / 0xFFFFFFFF


def _valor(ix: int, iy: int, nu: int, semilla: int) -> float:
    """
    Ruido de valor en un punto de la grilla, en [-1, 1].

    `ix` se toma módulo `nu` — o sea que la grilla es PERIÓDICA alrededor del
    eje. Sin eso el ruido no cierra en 0°/360° y queda una costura vertical
    visible en toda la altura de la pieza, que es el error clásico al mapear
    ruido sobre un sólido de revolución.
    """
    x = (ix % nu) * 374761393 + iy * 668265263 + semilla * 2147483647
    x = (x ^ (x >> 13)) & 0xFFFFFFFF
    x = (x * 1274126177) & 0xFFFFFFFF
    x = (x ^ (x >> 16)) & 0xFFFFFFFF
    return (x / 0x7FFFFFFF) - 1.0


def _suave(a: float, b: float, t: float) -> float:
    """Interpolación con smoothstep: derivada 0 en los extremos, sin aristas."""
    s = t * t * (3 - 2 * t)
    return a + (b - a) * s


def _ruido(u: float, v: float, nu: int, nv: int, semilla: int) -> float:
    """Ruido de valor 2D, periódico en `u` (el ángulo) y no en `v` (la altura)."""
    fu, fv = u * nu, v * nv
    iu, iv = math.floor(fu), math.floor(fv)
    du, dv = fu - iu, fv - iv
    a = _suave(_valor(iu, iv, nu, semilla), _valor(iu + 1, iv, nu, semilla), du)
    b = _suave(_valor(iu, iv + 1, nu, semilla), _valor(iu + 1, iv + 1, nu, semilla), du)
    return _suave(a, b, dv)


def arrugas(
    amplitud: float = 1.6,
    escala: int = 5,
    octavas: int = 4,
    persistencia: float = 0.55,
    semilla: int = 0,
    borde: float = 0.10,
) -> Deformacion:
    """
    Pliegues finos por toda la superficie, tipo papel arrugado o tela apretada.

    Es otra cosa que `hoyuelos()`, y la diferencia se ve enseguida: un hoyuelo
    es UN hundido con un centro y un borde, y se leen como puntos sueltos. Una
    arruga no tiene centro — es una cresta que corre, se bifurca y se apaga.
    Eso no sale de sumar gaussianas: sale de ruido fractal, varias octavas de
    ruido suave, cada una del doble de frecuencia y con menos amplitud.

    La octava gruesa da las ondulaciones grandes y las finas les agregan los
    quiebres. Bajar `persistencia` deja la superficie más suave; subirla la
    vuelve áspera.

    El ruido es **periódico en el ángulo**: si no, no cierra en la costura y
    queda una línea vertical marcada a lo largo de toda la pieza.

    Args:
        amplitud: cuánto se mete o sale la pared, en mm. 1.5-2 es la referencia.
        escala: cuántas celdas de ruido entran en una vuelta, en la octava más
            gruesa. Más = arrugas más chicas.
        octavas: cuántos niveles de detalle se suman. 4 alcanza; más no se ve.
        persistencia: cuánta amplitud conserva cada octava respecto de la
            anterior. 0.5 = suave, 0.7 = áspero.
        semilla: cambiala para otra pieza con el mismo carácter.
        borde: fracción de la altura, arriba y abajo, donde las arrugas se
            apagan. Deja la base plana para apoyar y la boca limpia.

    Returns:
        Una `Deformacion`.
    """
    if octavas < 1:
        raise ValueError("`octavas` tiene que ser >= 1")

    capas = []
    amp, nu, nv = 1.0, max(2, escala), max(2, escala)
    total = 0.0
    for o in range(octavas):
        capas.append((amp, nu, nv, semilla + o * 101))
        total += amp
        amp *= persistencia
        nu *= 2
        nv *= 2

    def deformacion(angulo: float, t: float) -> float:
        u = (angulo % (2 * math.pi)) / (2 * math.pi)
        n = 0.0
        for a, nu_, nv_, sem in capas:
            n += a * _ruido(u, min(max(t, 0.0), 1.0), nu_, nv_, sem)
        n /= total
        # Apagado suave en la base y en la boca.
        env = 1.0
        if t < borde:
            env = t / borde
        elif t > 1 - borde:
            env = (1 - t) / borde
        env = env * env * (3 - 2 * env)
        return amplitud * n * env

    return deformacion


def hoyuelos(
    cantidad: int = 9,
    amplitud: float = 3.0,
    ancho_grados: float = 55.0,
    alto: float = 0.12,
    semilla: int = 0,
    hacia_adentro: float = 0.6,
) -> Deformacion:
    """
    Bultos y hundidos LOCALIZADOS, como dedos apretando la pieza en puntos sueltos.

    La diferencia con `bultos()` importa y es la que me costó ver: `bultos()`
    suma senoidales GLOBALES, o sea `sin(n·ángulo)`, y una senoidal ocupa toda
    la vuelta — da unos pocos lóbulos amplios y simétricos, una pieza que
    "respira" pareja. Un hundido de verdad es LOCAL: hay un punto donde la
    pared se mete y a 40° de ahí ya no pasa nada. Eso no se puede escribir como
    una senoidal de baja frecuencia, hay que ponerlo donde va.

    Cada hoyuelo es una gaussiana en (ángulo, altura), así que decae suave y no
    deja borde. La envolvente `sin(π·t)` los apaga en la base y en la boca, por
    lo mismo que en `bultos()`.

    Args:
        cantidad: cuántos hoyuelos se reparten por la pieza.
        amplitud: cuánto mete o saca cada uno, en mm.
        ancho_grados: qué tan ancho es cada uno alrededor. 55° da hundidos que
            se leen sueltos; con 120° se pisan entre sí y vuelve a parecer
            `bultos()`.
        alto: qué fracción de la altura ocupa cada uno.
        semilla: cambiala para otra distribución con el mismo carácter.
        hacia_adentro: fracción de hoyuelos que hunden en vez de sobresalir.
            0.6 = mayoría hundidos, que es lo que da el aspecto de tela
            apretada en vez de globo inflado.

    Returns:
        Una `Deformacion`.
    """
    if cantidad < 1:
        raise ValueError("`cantidad` tiene que ser >= 1")

    r = _fases(semilla, cantidad * 4)
    puntos = []
    for _ in range(cantidad):
        centro_a = next(r) * 2 * math.pi
        centro_t = 0.12 + next(r) * 0.76      # nunca pegados a la base ni a la boca
        signo = -1.0 if next(r) < hacia_adentro else 1.0
        escala = 0.6 + next(r) * 0.8          # que no salgan todos del mismo tamaño
        puntos.append((centro_a, centro_t, signo, escala))

    sigma_a = math.radians(ancho_grados) / 2
    sigma_t = alto / 2

    def deformacion(angulo: float, t: float) -> float:
        total = 0.0
        for centro_a, centro_t, signo, escala in puntos:
            da = (angulo - centro_a + math.pi) % (2 * math.pi) - math.pi
            dt = t - centro_t
            e = (da / sigma_a) ** 2 + (dt / sigma_t) ** 2
            if e > 12:            # más allá de ~3.5 sigmas no aporta nada
                continue
            total += signo * escala * amplitud * math.exp(-e / 2)
        return total * math.sin(math.pi * t)

    return deformacion


def bultos(
    modos: int = 3,
    amplitud: float = 4.0,
    semilla: int = 0,
    n_max: int = 3,
    k_max: int = 3,
) -> Deformacion:
    """
    Bultos suaves y orgánicos: suma de unos pocos modos de baja frecuencia.

    Cada modo es `sin(n·ángulo + φ) · sin(k·π·t)` con `n` y `k` chicos, así que
    lo que sale son unas pocas panzas y hundidos amplios, no una superficie
    rugosa. Subir `modos` no hace bultos más chicos sino más irregulares.

    Args:
        modos: cuántos modos se suman. 1 da una pieza que solo se inclina; 3-4
            es el "tela colgando" de la referencia; más de 6 se emparejan entre
            sí y la pieza vuelve a parecer redonda.
        amplitud: cuánto se corre el radio como máximo, en mm. Es el total, se
            reparte entre los modos.
        semilla: cambiala para obtener otra pieza con el mismo carácter.
        n_max: frecuencia angular máxima. 3 = a lo sumo tres panzas alrededor.
        k_max: frecuencia vertical máxima. 3 = a lo sumo tres a lo alto.

    Returns:
        Una `Deformacion`.
    """
    if modos < 1:
        raise ValueError("`modos` tiene que ser >= 1")

    r = _fases(semilla, modos * 3)
    partes = []
    for _ in range(modos):
        n = 1 + int(next(r) * n_max)          # 1..n_max panzas alrededor
        k = 1 + int(next(r) * k_max)          # 1..k_max a lo alto
        fase = next(r) * 2 * math.pi
        partes.append((n, k, fase))

    peso = amplitud / modos

    def deformacion(angulo: float, t: float) -> float:
        total = 0.0
        for n, k, fase in partes:
            total += peso * math.sin(n * angulo + fase) * math.sin(k * math.pi * t)
        return total

    return deformacion


def glitch(
    desvio: float = 16.0,
    direccion: float = 0.0,
    amplitud: float = 7.0,
    centro: float = 0.5,
    alto: float = 0.30,
    lineas: int = 26,
    desgarros: int = 7,
    caos: float = 0.55,
    semilla: int = 0,
) -> Deformacion:
    """
    Una banda de la pieza que parece una señal rota: la pared se desgarra hacia
    afuera en líneas de barrido desplazadas, y vuelve a componerse arriba y
    abajo.

    El problema de un glitch impreso es que un glitch de verdad tiene SALTOS, y
    un salto radial entre dos vueltas deja la vuelta nueva sin apoyo: la pared
    se abre. Así que el desorden no va por vuelta sino por **línea de barrido**
    —un bloque de varias vueltas que se desplazan juntas— que es además como se
    ve un glitch real: bandas corridas, no puntos sueltos. Dentro de una línea
    todas las vueltas comparten desplazamiento; el único salto queda en el borde
    entre líneas, y ahí la transición se suaviza.

    Encima van los DESGARROS: sectores de ángulo que se van hacia afuera mucho
    más que el resto, con bordes duros. Como son un fenómeno angular, no
    comprometen el apoyo entre vueltas — dos vueltas consecutivas se desgarran
    casi igual — y son los que dan la lectura de "se rompió".

    Lo que de verdad lee como glitch es que el CENTRO de esas vueltas se corra
    hacia un lado, no que la pared se deforme. Y sale gratis en apoyo: un anillo
    que se traslada entero sigue siendo un anillo, y la vuelta de arriba lo pisa
    igual mientras el corrimiento por vuelta no pase de un cordón. Un
    desplazamiento radial, en cambio, gasta apoyo en cada milímetro.

    En coordenadas de radio eso es un primer armónico: correr el centro (dx, dy)
    equivale a sumarle `dx·cos(a) + dy·sin(a)` al radio. Por eso entra en la
    misma firma que todas las demás deformaciones, sin plomería nueva.

    Args:
        desvio: cuántos mm se corre el centro de la banda. Es el efecto
            principal; `amplitud` es el temblor que va encima.
        direccion: hacia qué lado se corre, en grados.
        amplitud: cuánto se deforma la pared además de correrse, en mm.
        centro: a qué altura relativa está el centro de la banda (0 abajo, 1
            arriba). Este es el control para subir y bajar la sección rota.
        alto: qué fracción de la pieza ocupa la banda.
        lineas: cuántas líneas de barrido entran en la banda. Pocas = bloques
            grandes y limpios; muchas = ruido fino, y a partir de cierto punto
            deja de imprimirse porque cada línea dura menos de una vuelta.
        desgarros: cuántos sectores se van hacia afuera.
        caos: 0 = solo líneas ordenadas, 1 = todo desplazado y desgarrado.
        semilla: otra pieza con el mismo carácter.

    Returns:
        Una `Deformacion`.
    """
    sem = int(semilla)
    n_lin = max(2, int(lineas))
    # Desplazamiento de cada línea de barrido, y de cada desgarro. Deterministas:
    # la misma semilla tiene que dar la misma pieza, o el slider no sirve.
    despl = [_valor(i, 17, n_lin * 4, sem) for i in range(n_lin + 2)]
    # Corrimiento lateral de cada línea: sesgado hacia `direccion` para que la
    # banda entera se vaya para un lado, con la dispersión encima. Sin el sesgo
    # queda un temblor simétrico que se lee como ruido y no como desplazamiento.
    rad_dir = math.radians(direccion)
    ex, ey = [], []
    for i in range(n_lin + 2):
        # `desvio` tiene que ser los milímetros que uno ve, no un tope teórico:
        # con un factor de 0..1 el corrimiento medio salía la cuarta parte de lo
        # pedido. Va de 0.55 a 1, así que ninguna línea se queda quieta y la
        # banda entera se corre de verdad. Y la componente lateral se recorta,
        # porque si compite con la principal el resultado es una diagonal y deja
        # de leerse como "todo se fue para ese lado".
        s_ = 0.55 + 0.45 * (_valor(i, 29, n_lin * 4, sem + 71) + 1) / 2
        lat = _valor(i, 31, n_lin * 4, sem + 89) * 0.22
        ex.append(s_ * math.cos(rad_dir) - lat * math.sin(rad_dir))
        ey.append(s_ * math.sin(rad_dir) + lat * math.cos(rad_dir))
    tears = []
    for k in range(max(0, int(desgarros))):
        a0 = (_valor(k, 3, 9973, sem + 11) + 1) / 2 * TAU
        anc = 0.05 + 0.25 * (_valor(k, 5, 9973, sem + 23) + 1) / 2
        fuerza = (_valor(k, 7, 9973, sem + 37) + 1) / 2
        t0 = (_valor(k, 9, 9973, sem + 53) + 1) / 2
        tears.append((a0, anc, fuerza, t0))

    def deformacion(angulo: float, t: float) -> float:
        # Envolvente de la banda: fuera de ella la pieza es la lámpara limpia.
        d = abs(t - centro) / max(alto / 2, 1e-6)
        if d >= 1.0:
            return 0.0
        env = 1 - d * d
        env = env * env

        # Dentro de la banda, en qué línea de barrido caemos. La interpolación
        # entre líneas vecinas es lo que evita el escalón que rompería la pared.
        u = (t - (centro - alto / 2)) / max(alto, 1e-9) * n_lin
        i = int(u)
        f = u - i
        f = f * f * (3 - 2 * f)
        base = despl[i] + (despl[i + 1] - despl[i]) * f
        # El corrimiento del centro, como primer armónico.
        cx = ex[i] + (ex[i + 1] - ex[i]) * f
        cy = ey[i] + (ey[i + 1] - ey[i]) * f
        corrimiento = desvio * env * (cx * math.cos(angulo) + cy * math.sin(angulo))

        # Los desgarros: sectores de ángulo que se van hacia afuera.
        extra = 0.0
        for a0, anc, fuerza, t0 in tears:
            da = abs(((angulo - a0 + math.pi) % TAU) - math.pi)
            if da > anc * math.pi:
                continue
            # borde duro a propósito: un desgarro no se desvanece
            k = 1 - (da / (anc * math.pi)) ** 4
            dt = abs(t - (centro - alto / 2 + t0 * alto)) / max(alto * 0.35, 1e-6)
            if dt < 1.0:
                extra += fuerza * k * (1 - dt * dt)

        return corrimiento + amplitud * env * (base * (1 - caos * 0.5) + extra * caos)

    return deformacion


def glitch2(
    desvio: float = 22.0,
    direccion: float = 0.0,
    caos: float = 14.0,
    armonicos: int = 9,
    deriva: float = 6.0,
    centro: float = 0.5,
    alto: float = 0.34,
    vueltas: int = 350,
    cordon: float = 1.2,
    margen: float = 3.0,
    reparto: float = 0.5,
    semilla: int = 0,
) -> Deformacion:
    """
    Glitch caótico que NO rompe el apoyo, por construcción.

    La versión anterior desordenaba por líneas de barrido: bloques de vueltas
    que saltan unos respecto de otros. Se ve bien y deja vueltas al aire, porque
    el salto ocurre justo en la dirección que cuesta —de una vuelta a la
    siguiente—. Acá el desorden va al revés:

        MUCHO en el ángulo, POCO en la altura.

    Cada vuelta es una curva complicadísima —una suma de armónicos con fases
    propias— pero la vuelta de arriba es casi la misma curva, apenas girada y
    morfada. Consecutivas se pisan; a lo largo de veinte vueltas la forma deriva
    tanto que en proyección las líneas se cruzan y se enredan, que es
    exactamente la maraña del dibujo. El caos es real y es gratis: no se paga en
    apoyo porque no ocurre entre vueltas.

    Y no se confía en que salga bien: la función se AUTOESCALA. Muestrea su
    propia derivada respecto de la altura, calcula cuánto se correría el radio
    entre dos vueltas y, si pasa del presupuesto (`margen` del cordón), baja
    todo proporcionalmente. Por eso el efecto puede pedirse exagerado sin
    riesgo: lo que no entra, no entra.

    Args:
        desvio: cuántos mm se corre el centro de la banda.
        direccion: hacia qué lado, en grados.
        caos: amplitud de la maraña, en mm.
        armonicos: cuántos lóbulos distintos se superponen. Más = más enredo.
        deriva: cuántas veces cambia de forma a lo largo de la banda. Es lo que
            hace que las líneas se crucen en vez de quedar paralelas.
        centro, alto: dónde y cuánto ocupa la banda.
        vueltas: cuántas vueltas da la pieza entera. De acá sale el presupuesto.
        cordon: ancho del cordón, el presupuesto de solape.
        margen: cuántos cordones puede correrse el radio por vuelta. Suena
            imposible que sea > 1 y no lo es: cuando la pared se tumba, el paso
            vertical adaptativo frena la Z y la vuelta nueva se apoya AL LADO de
            la anterior, no encima — como el piso macizo, que es una espiral
            plana y se sostiene sola. Con 0.55 el efecto salía estrangulado por
            una regla que el generador ya resolvía: 36 mm de excursión contra
            65 con el mismo cero de vueltas sueltas.
        reparto: qué parte del presupuesto se lleva el corrimiento; el resto es
            para la maraña. 0.5 es mitad y mitad.
    """
    sem = int(semilla)
    n_arm = max(1, int(armonicos))
    rad_dir = math.radians(direccion)
    # Cada armónico: su número de lóbulos, su fase inicial y a qué velocidad
    # gira. Las velocidades son distintas entre sí — si fueran iguales la figura
    # rotaría rígida y no se enredaría nunca.
    arms = []
    for k in range(n_arm):
        lob = 2 + int((_valor(k, 2, 9973, sem + 5) + 1) / 2 * 9)
        fase = (_valor(k, 4, 9973, sem + 13) + 1) * math.pi
        vel = (_valor(k, 6, 9973, sem + 29)) * deriva
        peso = 0.35 + 0.65 * (_valor(k, 8, 9973, sem + 41) + 1) / 2
        arms.append((lob, fase, vel, peso))
    total = sum(a[3] for a in arms) or 1.0

    # Las dos partes se calculan por separado porque gastan apoyo de forma muy
    # distinta: el corrimiento del centro varía despacio con la altura y casi no
    # cuesta, la maraña varía rápido y es la que se come el presupuesto.
    # Escalarlas juntas —como hacía la primera versión— dejaba el corrimiento en
    # 0.3 mm de 26 pedidos: pagaba por los pecados de la otra.
    def _env(t):
        d = abs(t - centro) / max(alto / 2, 1e-6)
        return 0.0 if d >= 1.0 else (1 - d * d) ** 2

    def _corr(angulo, t):
        e = _env(t)
        if e <= 0:
            return 0.0
        u = (t - centro) / max(alto, 1e-9)
        cx = desvio * math.cos(rad_dir) * (0.75 + 0.25 * math.sin(3.1 * u * TAU))
        cy = desvio * math.sin(rad_dir) * (0.75 + 0.25 * math.cos(2.7 * u * TAU))
        return e * (cx * math.cos(angulo) + cy * math.sin(angulo))

    def _marana(angulo, t):
        e = _env(t)
        if e <= 0:
            return 0.0
        u = (t - centro) / max(alto, 1e-9)
        m = 0.0
        for lob, fase, vel, peso in arms:
            m += peso * math.sin(lob * angulo + fase + vel * u * TAU)
        return e * caos * m / total

    dt = 1.0 / max(1, int(vueltas))
    peor_c = peor_m = 0.0
    for i in range(140):
        t = centro - alto / 2 + alto * i / 139
        for j in range(72):
            a = j / 72 * TAU
            peor_c = max(peor_c, abs(_corr(a, t + dt) - _corr(a, t)))
            peor_m = max(peor_m, abs(_marana(a, t + dt) - _marana(a, t)))
    presupuesto = margen * cordon
    # El presupuesto se REPARTE, no se asigna por orden de llegada. Dar
    # prioridad al corrimiento dejaba la maraña en cero —y con ella `caos`,
    # `armonicos` y `deriva` sin ningún efecto— sin que nada lo dijera: tres
    # configuraciones distintas producían el mismo archivo.
    #
    # Y acá está el límite duro del asunto: con cordón de 1.2 el presupuesto son
    # 0.66 mm por vuelta, y un corrimiento grande ya se lo gasta. Se puede tener
    # el desplazamiento o el enredo a fondo, no los dos — salvo que se ensanche
    # el cordón o se reparta la banda en más vueltas (`alto`).
    parte = presupuesto * reparto
    esc_c = 1.0 if peor_c <= parte else parte / max(peor_c, 1e-9)
    otra = presupuesto - peor_c * esc_c
    esc_m = 1.0 if peor_m <= otra else max(0.0, otra) / max(peor_m, 1e-9)

    def deformacion(angulo: float, t: float) -> float:
        return esc_c * _corr(angulo, t) + esc_m * _marana(angulo, t)

    deformacion.escala = (esc_c, esc_m)
    return deformacion


def glitch3(
    salto: float = 40.0,
    sectores: int = 7,
    bloques: int = 9,
    rampa: float = 0.18,
    solo_afuera: bool = False,
    desvio: float = 0.0,
    direccion: float = 0.0,
    centro: float = 0.5,
    alto: float = 0.42,
    semilla: int = 0,
) -> Deformacion:
    """
    Glitch de verdad: escalones, no ondas.

    Las versiones anteriores sumaban armónicos, y una suma de senos es suave en
    todas partes por definición — no puede producir un corte. Por eso salían
    lámparas derretidas y no lámparas rotas. Acá la primitiva es otra:

    - **En el ángulo, constante a tramos.** La vuelta se parte en sectores y
      cada uno se va a un radio fijo, con borde vertical. El salto ocurre
      DENTRO de la vuelta, así que el recorrido lo cruza con un tramo casi
      radial —el corte recto que se ve en las piezas de referencia— y no cuesta
      apoyo: la vuelta de arriba tiene el mismo escalón en el mismo ángulo.
    - **En la altura, congelado a bloques.** Varias vueltas repiten el mismo
      patrón exacto, como un cuadro trabado, y de golpe cambia. Entre bloques el
      cambio se reparte en `rampa` para que la vuelta nueva no quede en el aire:
      el ojo lee el bloque como constante y la rampa no se ve.

    Esa asimetría es todo el truco. El desorden vive donde es gratis —dentro de
    la vuelta— y donde cuesta —entre vueltas— la pieza es casi periódica.

    Args:
        salto: cuántos mm salta un sector hacia afuera o adentro.
        sectores: en cuántos tramos se parte la vuelta.
        bloques: cuántos bloques congelados entran en la banda.
        solo_afuera: los sectores solo salen, nunca se meten. Sin esto la mitad
            del glitch queda por DENTRO de la pieza: no se ve y no apoya.
        rampa: qué fracción de un bloque se usa para pasar al siguiente.
            Chico = corte más brusco y menos apoyo; 0.18 es un buen término.
        desvio, direccion: corrimiento del centro, en mm y grados.
        centro, alto: dónde y cuánto ocupa la banda.
    """
    sem = int(semilla)
    n_sec = max(2, int(sectores))
    n_blq = max(1, int(bloques))
    rad_dir = math.radians(direccion)
    r_ram = min(0.49, max(0.01, rampa))

    # Un patrón por bloque: qué offset tiene cada sector, y dónde empiezan los
    # cortes. Los bordes también se mueven entre bloques — si fueran fijos se
    # vería una rejilla regular y no un glitch.
    patrones = []
    for b in range(n_blq + 2):
        crudo = [_valor(b * 97 + k, 11, 9973, sem + 3) for k in range(n_sec)]
        # Solo hacia AFUERA. Con offsets de -1 a 1 la mitad de los sectores se
        # mete hacia adentro, y esas pasadas quedan por dentro de la pieza: no
        # aportan superficie, cruzan el interior y en el vaso son cordones al
        # aire que no apoyan en nada. El glitch se lee igual —lo que se ve es el
        # contorno— y el recorrido deja de invadirse a sí mismo.
        offs = [(v + 1) / 2 for v in crudo] if solo_afuera else crudo
        cortes = sorted((_valor(b * 89 + k, 13, 9973, sem + 19) + 1) / 2 for k in range(n_sec))
        patrones.append((offs, cortes))

    def _sector(offs, cortes, angulo: float) -> float:
        u = (angulo % TAU) / TAU
        i = 0
        while i < len(cortes) and cortes[i] <= u:
            i += 1
        return offs[(i - 1) % len(offs)]

    def deformacion(angulo: float, t: float) -> float:
        d = abs(t - centro) / max(alto / 2, 1e-6)
        if d >= 1.0:
            return 0.0
        env = 1 - d * d              # sin suavizar: la banda también empieza de golpe

        x = (t - (centro - alto / 2)) / max(alto, 1e-9) * n_blq
        b = int(x)
        f = x - b                    # 0..1 dentro del bloque

        offs_b, cortes_b = patrones[b]
        offs_n, cortes_n = patrones[b + 1]
        if f > 1 - r_ram:
            # Durante la rampa, los CORTES ya son los del bloque siguiente y solo
            # se interpolan las alturas. Deslizar el corte de a poco era peor que
            # saltarlo: mientras se mueve, cada vuelta lo pone en otro ángulo y
            # ninguna se apila con la de abajo — 661 puentes al aire en vez de
            # uno por bloque. Un corte quieto se sostiene sobre el de la vuelta
            # anterior; uno que se desliza no se sostiene sobre nada.
            k = (f - (1 - r_ram)) / r_ram
            k = k * k * (3 - 2 * k)
            a0 = _sector(offs_b, cortes_n, angulo)
            a = a0 + (_sector(offs_n, cortes_n, angulo) - a0) * k
        else:
            a = _sector(offs_b, cortes_b, angulo)

        corr = desvio * (math.cos(rad_dir) * math.cos(angulo)
                         + math.sin(rad_dir) * math.sin(angulo))
        return env * (salto * a + corr)

    return deformacion


def aletas(
    vuelo: float = 38.0,
    cuantas: int = 8,
    grosor: float = 0.25,
    ceja: float = 0.32,
    lobulos: int = 5,
    irregular: float = 0.35,
    desde: float = 0.12,
    hasta: float = 0.95,
    semilla: int = 0,
) -> Deformacion:
    """
    Repisas horizontales apiladas, como las lámparas de aletas.

    Una aleta sale 40 mm de la pared y aun así se imprime, y el motivo es el que
    me costó ver: **no se apoya encima de la vuelta anterior sino AL LADO**.
    Cuando la pared se pone horizontal, el paso vertical adaptativo desploma la
    Z —`dz = paso·cos(θ)` con θ→90°— y las vueltas quedan tendidas una junto a
    otra, igual que la espiral de un piso macizo, que se sostiene sola.

    Por eso la aleta tiene que ser **axisimétrica**: si sale por todos los
    ángulos a la vez, `marcha_vertical` la ve al medir el radio medio y frena.
    Un desplazamiento angular —lo que yo venía haciendo— no mueve el radio medio,
    el generador no frena, y las vueltas quedan en el aire. Ahí estaba el error.

    La irregularidad va aparte, en el contorno de cada aleta, que es de donde
    sale que se vean como hojas y no como discos.

    Args:
        vuelo: cuánto sale la aleta, en mm.
        cuantas: cuántas aletas se apilan.
        ceja: qué fracción de la aleta se usa para entrar y salir. Es el
            voladizo curvo del borde; por debajo de ~0.2 el flanco se vuelve un
            acantilado y deja vueltas en el aire.
        grosor: qué fracción del ciclo ocupa la aleta. Chico = repisa fina y
            bien separada; grande = la pieza se vuelve un cono ondulado.
        lobulos: cuántos lóbulos tiene el contorno de cada aleta.
        irregular: 0 = discos perfectos, 1 = hojas muy asimétricas.
        desde, hasta: entre qué alturas relativas se apilan.
    """
    sem = int(semilla)
    n = max(1, int(cuantas))
    g = min(0.9, max(0.05, grosor))
    lob = max(2, int(lobulos))
    fases = [(_valor(k, 7, 9973, sem + 3) + 1) * math.pi for k in range(n + 1)]
    pesos = [0.6 + 0.4 * (_valor(k, 9, 9973, sem + 17) + 1) / 2 for k in range(n + 1)]

    def deformacion(angulo: float, t: float) -> float:
        if t < desde or t > hasta:
            return 0.0
        u = (t - desde) / max(hasta - desde, 1e-9) * n
        k = min(n, int(u))
        f = u - k
        # Perfil de la aleta: sube de golpe, se mantiene, y baja. El borde
        # exterior queda casi horizontal, que es lo que hace que se imprima.
        if f > g:
            return 0.0
        x = f / g                       # 0..1 dentro de la aleta
        # Subida y bajada SUAVES con meseta en el medio. El primer intento usaba
        # sin(pi·x)^0.35, que parecía una meseta ancha y en realidad sube el 32%
        # del vuelo en el primer 1% de la aleta: un acantilado que ni el paso
        # mínimo alcanza a seguir, y de ahí 94 vueltas al aire. El voladizo tiene
        # que entrar y salir como una curva, como en las piezas de referencia;
        # lo que es abrupto es el CICLO, no el flanco.
        c = min(0.45, max(0.05, ceja))
        if x < c:
            k = x / c
        elif x > 1 - c:
            k = (1 - x) / c
        else:
            k = 1.0
        perfil = k * k * (3 - 2 * k)
        contorno = 1 + irregular * math.sin(lob * angulo + fases[k])
        return vuelo * pesos[k] * perfil * contorno

    return deformacion


def ninguna() -> Deformacion:
    """Sin deformación. Para poder pedir 'nada' desde la línea de comandos."""
    return lambda angulo, t: 0.0


ESTRUCTURAS = {
    "glitch": glitch,
    "glitch2": glitch2,
    "glitch3": glitch3,
    "aletas": aletas,
    "bultos": bultos,
    "hoyuelos": hoyuelos,
    "arrugas": arrugas,
    "ninguna": lambda **kw: ninguna(),
}


def resolver(nombre, **kwargs) -> Deformacion:
    """Convierte el nombre que llega por `--estructura` en una `Deformacion`."""
    if callable(nombre):
        return nombre
    if nombre not in ESTRUCTURAS:
        raise ValueError(
            f"estructura desconocida: {nombre!r}. Opciones: {', '.join(sorted(ESTRUCTURAS))}"
        )
    return ESTRUCTURAS[nombre](**kwargs)
