"""
Recorridos que NO son una espiral monótona.

Todo el resto del proyecto asume lo mismo: una sola subida continua, un punto
por (vuelta, fracción), z creciente, y cada vuelta apoyada sobre la anterior.
Esa suposición es la que hace que un aleta de 40 mm sea imposible — y no lo es.

Una aleta no se apoya en la vuelta de abajo: es un **disco plano**, varias
pasadas concéntricas a la MISMA altura, y se sostiene lateralmente igual que el
piso macizo de un bol. Para imprimirla hay que poder salir del eje, dar vueltas
sin subir, y volver. Eso no se puede pedir cambiando la función del radio: es
otra topología de recorrido, y por eso vive acá y no en `estructura.py`.

El recorrido de una lámpara de aletas es, en orden:

    tramo de pared (espiral normal) -> aleta (disco, ida y vuelta) -> pared ...

La aleta se emite en dos pasadas a distinta altura: la de ida abre de la pared
hacia afuera, la de vuelta cierra de afuera hacia la pared una capa más arriba.
Así queda de dos cordones de espesor —como las piezas de referencia, que no son
membranas de una pasada— y el recorrido termina donde tiene que seguir la pared,
sin viajes en el aire.
"""

import math
from dataclasses import dataclass
from typing import Callable, List, Optional

import fullcontrol as fc

from .comun import Perfil, _verificar_cama, pasos_iniciales

TAU = 2 * math.pi


def _punto(perfil: Perfil, r: float, a: float, z: float) -> fc.Point:
    cx, cy = perfil.centro
    return fc.Point(x=cx + r * math.cos(a), y=cy + r * math.sin(a), z=z)


def _anillo(perfil: Perfil, r_de, r_a, z_de: float, z_a: float, a0: float,
            vueltas: float, paso_arco: float = 1.0) -> tuple:
    """
    Espiral plana de `r_de` a `r_a` en `vueltas` vueltas, subiendo de `z_de` a
    `z_a`. `r_de`/`r_a` pueden ser números o `f(angulo) -> radio`, que es de
    donde sale que el borde de la aleta tenga lóbulos y no sea un disco.
    """
    f_de = r_de if callable(r_de) else (lambda a: r_de)
    f_a = r_a if callable(r_a) else (lambda a: r_a)
    pts: List[fc.Point] = []
    total = max(1e-6, vueltas) * TAU
    a = 0.0
    while a <= total:
        s = a / total
        ang = a0 + a
        r = f_de(ang) + (f_a(ang) - f_de(ang)) * s
        pts.append(_punto(perfil, r, ang, z_de + (z_a - z_de) * s))
        a += paso_arco / max(r, 0.6)
    return pts, a0 + total


def pasos_lampara_aletas(
    perfil: Perfil,
    altura: float = 150.0,
    radio: Callable[[float], float] = None,
    vuelo: float = 34.0,
    cuantas: int = 8,
    desde: float = 0.14,
    hasta: float = 0.94,
    lobulos: int = 5,
    irregular: float = 0.30,
    capas_aleta: int = 4,
    punta: float = 0.45,
    semilla: int = 0,
) -> list:
    """
    Lámpara de aletas suspendidas.

    Args:
        radio: `radio(t)` del núcleo. Por defecto, un cilindro suave.
        vuelo: cuánto sale cada aleta más allá del núcleo, en mm.
        cuantas: cuántas aletas.
        capas_aleta: cuántas pasadas de ida y vuelta tiene cada aleta. 2 = una
            ida y una vuelta, o sea dos cordones de espesor.
        lobulos, irregular: el contorno de la aleta. `irregular` alto ondula el
            borde y la placa deja de leerse como hoja; 0.10-0.15 alcanza.
        punta: hasta dónde llega la última pasada respecto de la primera. 1 =
            repisa de espesor constante; 0.45 = filo.
    """
    if radio is None:
        radio = lambda t: 40.0 - 4.0 * t  # noqa: E731

    paso = perfil.altura_capa
    ancho = perfil.ancho
    pasos = pasos_iniciales(perfil)
    pts: List[fc.Point] = []

    alturas = [desde + (hasta - desde) * (k + 0.5) / cuantas for k in range(max(1, cuantas))]
    z = paso
    a = 0.0
    t = 0.0

    def pared_hasta(t_fin, z, a):
        """Espiral normal del núcleo, de `t` a `t_fin`."""
        out = []
        tt = t
        while tt < t_fin:
            aa = 0.0
            while aa < TAU:
                r = radio(min(1.0, tt))
                out.append(_punto(perfil, r, a + aa, z + paso * aa / TAU))
                aa += 1.0 / max(r, 0.6)
            a += TAU
            z += paso
            tt += paso / max(altura, 1e-9)
        return out, z, a, tt

    for k, t_aleta in enumerate(alturas):
        tramo, z, a, t = pared_hasta(t_aleta, z, a)
        pts.extend(tramo)

        # --- la aleta ---
        r_nucleo = radio(min(1.0, t))
        fase = k * 1.7
        borde = (lambda ang, rn=r_nucleo, f=fase:
                 rn + vuelo * (1 + irregular * math.sin(lobulos * ang + f)))
        # Vueltas necesarias para que las pasadas se toquen: una por cordón.
        n_v = max(1.0, vuelo * (1 + irregular) / ancho)
        # La aleta se AFINA hacia el borde: las pasadas de más alto no llegan
        # tan lejos. En las piezas de referencia la placa es gruesa en la raíz y
        # termina en filo; con espesor constante queda una repisa de cartón.
        n_cap = max(1, int(capas_aleta))
        for capa in range(n_cap):
            # 1.0 en la primera pasada, `punta` en la última
            frac = 1.0 if n_cap == 1 else 1 - (1 - punta) * capa / (n_cap - 1)
            hasta_r = (lambda ang, f=frac, rn=r_nucleo, b=borde: rn + (b(ang) - rn) * f)
            n_i = max(1.0, n_v * frac)
            if capa % 2 == 0:
                tramo, a = _anillo(perfil, r_nucleo, hasta_r, z, z, a, n_i)
            else:
                tramo, a = _anillo(perfil, hasta_r, r_nucleo, z, z, a, n_i)
            pts.extend(tramo)
            z += paso            # la pasada siguiente va una capa más arriba
        t += (capas_aleta * paso) / max(altura, 1e-9)

    tramo, z, a, t = pared_hasta(1.0, z, a)
    pts.extend(tramo)

    pasos.append(fc.Extruder(on=False))
    pasos.append(pts[0])
    pasos.append(fc.Extruder(on=True))
    pasos.extend(pts[1:])
    return pasos


def pasos_lampara_glitch(
    perfil: Perfil,
    altura: float = 140.0,
    radio: Callable[[float], float] = None,
    centro: float = 0.5,
    alto: float = 0.34,
    salto: float = 26.0,
    sectores: int = 6,
    congelado: int = 5,
    escapes: int = 7,
    escape_vuelo: float = 45.0,
    escape_arco: float = 0.35,
    desvio: float = 12.0,
    direccion: float = 0.0,
    semilla: int = 0,
) -> list:
    """
    Pantalla clásica con una banda que se rompe.

    Dos mecanismos, y ninguno es una suma de senos — que fue el error de las
    cinco versiones anteriores: un seno es suave en todas partes y no puede
    hacer un corte, por eso salían lámparas derretidas.

    1. **Sectores duros.** Dentro de la banda, la vuelta se parte en tramos y
       cada uno corre a un radio fijo, con borde vertical. El salto ocurre
       DENTRO de la vuelta: el recorrido lo cruza con un tramo casi radial —el
       corte recto— y no cuesta apoyo, porque la vuelta de arriba repite el
       mismo escalón en el mismo ángulo. El patrón se congela varias vueltas
       (`congelado`) y cambia de golpe, como un cuadro trabado.

    2. **Escapes.** Cada tanto el recorrido se sale del todo: dispara hacia
       afuera, corre un arco a Z CONSTANTE muy lejos de la pared, y vuelve.
       Esas son las líneas que salen y entran. Se sostienen porque son planas
       —cada pasada al lado de la anterior, como el piso de un bol— y no porque
       se apoyen en la vuelta de abajo. Es lo que la espiral monótona no podía
       expresar por más que se le cambiara la función del radio.

    Args:
        salto: cuánto salta un sector, en mm.
        sectores: en cuántos tramos se parte la vuelta.
        congelado: cuántas vueltas repiten el mismo patrón antes de cambiar.
        escapes: cuántas excursiones planas hay en la banda.
        escape_vuelo: cuánto se aleja un escape, en mm.
        escape_arco: qué fracción de vuelta dura el escape.
        desvio, direccion: corrimiento del centro de la banda.
    """
    from .estructura import _valor

    if radio is None:
        radio = lambda t: 95 - 40 * t  # noqa: E731
    sem = int(semilla)
    n_sec = max(2, int(sectores))
    rad_dir = math.radians(direccion)
    paso = perfil.altura_capa
    ancho = perfil.ancho
    n_vueltas = max(1, int(altura / paso))
    t0, t1 = centro - alto / 2, centro + alto / 2

    def patron(bloque):
        offs = [_valor(bloque * 97 + k, 11, 9973, sem + 3) for k in range(n_sec)]
        cortes = sorted((_valor(bloque * 89 + k, 13, 9973, sem + 19) + 1) / 2
                        for k in range(n_sec))
        return offs, cortes

    def offset(bloque, ang, t):
        if not (t0 <= t <= t1):
            return 0.0
        env = 1 - (abs(t - centro) / max(alto / 2, 1e-6)) ** 2
        offs, cortes = patron(bloque)
        u = (ang % TAU) / TAU
        i = 0
        while i < len(cortes) and cortes[i] <= u:
            i += 1
        corr = desvio * (math.cos(rad_dir) * math.cos(ang) + math.sin(rad_dir) * math.sin(ang))
        return env * (salto * offs[(i - 1) % len(offs)] + corr)

    # En qué vueltas ocurre un escape, y con qué ángulo de arranque.
    v0, v1 = int(t0 * n_vueltas), int(t1 * n_vueltas)
    cuando = {}
    for k in range(max(0, int(escapes))):
        v = v0 + int((_valor(k, 41, 9973, sem + 61) + 1) / 2 * max(1, v1 - v0))
        cuando[v] = (_valor(k, 43, 9973, sem + 79) + 1) * math.pi

    pasos = pasos_iniciales(perfil)
    pts: List[fc.Point] = []
    z = paso
    a = 0.0
    for v in range(n_vueltas):
        t = v / n_vueltas
        bloque = v // max(1, int(congelado))
        aa = 0.0
        while aa < TAU:
            ang = a + aa
            r = radio(t) + offset(bloque, ang, t + aa / TAU / n_vueltas)
            pts.append(_punto(perfil, r, ang, z + paso * aa / TAU))
            aa += 1.0 / max(r, 0.6)
        a += TAU
        z += paso

        # El escape: sale, corre lejos a Z constante, y vuelve. Las idas y
        # vueltas se apilan de a un cordón para que se toquen de costado.
        if v in cuando:
            ang0 = cuando[v]
            r_base = radio(t) + offset(bloque, ang0, t)
            n_p = max(2, int(escape_vuelo / ancho))
            for i in range(n_p):
                s = (i + 1) / n_p
                r = r_base + escape_vuelo * s
                arco = escape_arco * TAU
                paso_ang = 1.0 / max(r, 0.6)
                b = 0.0
                while b < arco:
                    pts.append(_punto(perfil, r, ang0 + (b if i % 2 == 0 else arco - b), z))
                    b += paso_ang
            # volver a la pared para retomar la espiral
            pts.append(_punto(perfil, r_base, ang0, z))

    pasos.append(fc.Extruder(on=False))
    pasos.append(pts[0])
    pasos.append(fc.Extruder(on=True))
    pasos.extend(pts[1:])
    return pasos


def pasos_lampara_glitch2(
    perfil: Perfil,
    altura: float = 140.0,
    radio: Callable[[float], float] = None,
    centro: float = 0.5,
    alto: float = 0.34,
    onda: float = 5.0,
    desvio: float = 9.0,
    direccion: float = 0.0,
    lenguas: int = 26,
    vuelo: float = 30.0,
    arco: float = 0.22,
    capas: int = 2,
    semilla: int = 0,
) -> list:
    """
    La pantalla glitch, con las dos técnicas a la vez.

    Son capas distintas, no alternativas — que es lo que tardé seis intentos en
    entender:

    - **La pared** sigue siendo una espiral continua y SUAVE. Se ondula y se
      corre de lado, pero poco: cada vuelta apoya sobre la anterior y es la que
      sostiene la pieza. Todo lo que hice con cortes duros en la pared dejaba
      vueltas al aire, porque un corte entre vueltas es exactamente lo que no
      se puede.
    - **Las lenguas** son lo violento: salen de la pared, corren a Z CONSTANTE
      y vuelven. No piden apoyo vertical — cada pasada se acuesta al lado de la
      anterior, como el piso de un bol— así que pueden salir 30 mm sin deberle
      nada a la vuelta de abajo.

    Cada lengua se emite como arcos concéntricos ANCLADOS EN LA PARED por los
    dos extremos, creciendo hacia afuera. Solo el arco más externo tiene un
    tramo al aire, y llega apoyado sobre el anterior. Emitirlas como idas y
    vueltas radiales, en cambio, deja la primera pasada como un puente suelto.

    Args:
        onda: cuánto ondula la pared dentro de la banda, en mm. Es lo suave.
        desvio, direccion: corrimiento del centro de la banda.
        lenguas: cuántas salen.
        vuelo: cuánto sale cada una, en mm.
        arco: qué fracción de vuelta ocupa cada lengua.
        capas: cuántas alturas apila cada lengua.
    """
    from .estructura import _valor

    if radio is None:
        radio = lambda t: 95 - 40 * t  # noqa: E731
    sem = int(semilla)
    rad_dir = math.radians(direccion)
    paso = perfil.altura_capa
    ancho = perfil.ancho
    n_v = max(1, int(altura / paso))
    t0, t1 = centro - alto / 2, centro + alto / 2

    def suave(ang, t):
        """Lo que se le suma a la PARED: suave, para no romper el apoyo."""
        if not (t0 <= t <= t1):
            return 0.0
        env = 1 - (abs(t - centro) / max(alto / 2, 1e-6)) ** 2
        u = (t - centro) / max(alto, 1e-9)
        w = (math.sin(3 * ang + 7 * u) + 0.6 * math.sin(7 * ang - 4 * u)
             + 0.4 * math.sin(11 * ang + 9 * u)) / 2.0
        corr = math.cos(rad_dir) * math.cos(ang) + math.sin(rad_dir) * math.sin(ang)
        return env * (onda * w + desvio * corr)

    # Dónde sale cada lengua: vuelta y ángulo.
    v0, v1 = int(t0 * n_v), int(t1 * n_v)
    donde = {}
    for k in range(max(0, int(lenguas))):
        v = v0 + int((_valor(k, 41, 9973, sem + 61) + 1) / 2 * max(1, v1 - v0))
        donde.setdefault(v, []).append((
            (_valor(k, 43, 9973, sem + 79) + 1) * math.pi,          # ángulo
            0.45 + 0.55 * (_valor(k, 47, 9973, sem + 97) + 1) / 2,  # largo relativo
        ))

    pasos = pasos_iniciales(perfil)
    pts: List[fc.Point] = []
    z = paso
    a = 0.0
    for v in range(n_v):
        t = v / n_v
        aa = 0.0
        while aa < TAU:
            ang = a + aa
            tt = t + aa / TAU / n_v
            r = radio(tt) + suave(ang, tt)
            pts.append(_punto(perfil, r, ang, z + paso * aa / TAU))
            aa += 1.0 / max(r, 0.6)
        a += TAU
        z += paso

        for ang0, largo in donde.get(v, ()):
            arco_l = arco * TAU * largo
            r_pared = radio(t) + suave(ang0, t)
            n_p = max(2, int(vuelo * largo / ancho))
            for capa in range(max(1, int(capas))):
                zc = z + capa * paso
                for i in range(n_p):
                    # Arcos concéntricos, cada uno un poco más afuera y un poco
                    # más corto: el borde de la lengua se afina en punta.
                    s = (i + 1) / n_p
                    r = r_pared + vuelo * largo * s
                    med = arco_l * (1 - 0.55 * s) / 2
                    b, paso_ang = -med, 1.0 / max(r, 0.6)
                    tramo = []
                    while b <= med:
                        tramo.append(_punto(perfil, r, ang0 + b, zc))
                        b += paso_ang
                    pts.extend(tramo if i % 2 == 0 else tramo[::-1])
            # La lengua NO consume altura de la pared. Avanzar `z` acá dejaba
            # a la pared salteándose una capa en cada lengua —50 vueltas sin
            # apoyo en 36 lenguas— por una razón puramente contable: la lengua
            # se apoya de costado, no ocupa el turno de nadie.

    pasos.append(fc.Extruder(on=False))
    pasos.append(pts[0])
    pasos.append(fc.Extruder(on=True))
    pasos.extend(pts[1:])
    return pasos


def _radios_pasada(r_de: float, r_a: float, d_max: float, primero: float,
                   ancho: float = 1.8, alto: float = 0.4) -> List[float]:
    """
    Los radios de las pasadas que llevan la pared de `r_de` a `r_a` en una capa.

    Las dos pasadas de un mismo salto NO se apoyan igual, y ahí estaba el error:

    - La **primera** es la única que sube una capa, así que paga `dh` y `dv` a
      la vez. Repartiendo el salto en partes iguales le tocaba un cordón entero
      de corrimiento sobre 0.4 de altura, o sea un voladizo del 70 % en una
      capa: 11.8 % del recorrido sin contacto, todo en las primeras pasadas.
      Por eso arranca con un escalón chico, que sí se sostiene.
    - Las **siguientes** corren a la misma altura y se apoyan de costado en la
      vecina. Esas sí pueden ir a `d_max`, que es lo que cuesta un cordón menos
      su solape.
    """
    d = r_a - r_de
    if abs(d) <= d_max:
        return [r_a]                       # pared normal: una sola pasada
    signo = 1.0 if d > 0 else -1.0
    s1 = min(abs(d), primero)
    resto = abs(d) - s1
    n = max(1, int(math.ceil(resto / d_max)))
    # Redondear para arriba puede dejar las pasadas MUY juntas: con `resto`
    # apenas por encima de un múltiplo, `resto/n` se desploma y dos cordones
    # caen casi en el mismo eje. Eso no es apoyo de más, es material de más.
    # Si el reparto queda demasiado apretado, se usa una pasada menos.
    #
    # Pero SOLO si al quitarla las pasadas siguen tocándose. Sin esa condición
    # la separación se iba hasta 2.14 mm con cordón de 1.8: no se tocan, y
    # quedaban pasadas de relleno de 195 mm enteras al aire —los puentes que
    # mantenían la pieza en NO IMPRIMIBLE—. La ventana es estrecha y hay que
    # respetar los dos bordes, no uno.
    #
    # El techo sale de la geometría del cordón: dos vecinos se tocan mientras
    # los ejes no se separen más que el núcleo plano `(ancho - alto)` más el
    # alto. Se deja un margen para que se monten de verdad y no se rocen.
    tope = (ancho - alto) + alto * 0.9
    if n > 1 and resto / n < 0.78 * d_max and resto / (n - 1) <= tope:
        n -= 1
    return [r_de + signo * s1] + [
        r_de + signo * (s1 + resto * j / n) for j in range(1, n + 1)]


def pasos_pantalla_glitch(
    perfil: Perfil,
    altura: float = 140.0,
    silueta: Callable[[float], float] = None,
    deformacion: Callable[[float, float], float] = None,
    segmentos: int = 400,
    base_solida: bool = False,
    solape: float = 0.92,
    primer_escalon: float = 0.50,
) -> list:
    """
    Pantalla con banda glitch, resuelta con pasadas planas en vez de paso corto.

    El problema que resuelve: donde la pared se tumba, la espiral adaptativa
    comprime `dz` hasta 0.05 mm para que las vueltas se toquen, y la extrusión
    lo sigue. Pero un cordón de 1.8 mm de ancho por 0.05 de alto **no existe** —
    una boquilla de 0.8 no tiende una cinta así, sale un hilo.

    Los viajes entre pasadas van CON RETRACCIÓN. Sin ella, los 537 saltos de
    esta pieza —81 de los cuales cruzan el hueco de la lámpara— dejan un hilo
    cada uno colgando justo en la parte que se ve desde adentro.

    Acá el paso vertical queda FIJO en la altura de capa, y el hueco radial se
    rellena con pasadas concéntricas a la MISMA altura, separadas un cordón. O
    sea, la técnica de las aletas flotantes aplicada vuelta por vuelta: cada
    pasada lleva su cordón completo y se apoya de costado en la vecina, no
    debajo. Donde la pared es vertical el hueco es de un cordón, sale una sola
    pasada, y el recorrido es la espiral de siempre.
    """
    if silueta is None:
        silueta = lambda t: 95 - 40 * t  # noqa: E731
    if deformacion is None:
        deformacion = lambda a, t: 0.0   # noqa: E731

    paso = perfil.altura_capa
    ancho = perfil.ancho
    n_v = max(1, int(altura / paso))

    # Cada pasada es un lazo cerrado: donde arranca queda una COSTURA. Con todas
    # las capas arrancando en el mismo ángulo, las 352 costuras de esta pieza se
    # apilan y sale una raya vertical de arriba abajo — que es exactamente lo
    # que Orca lista como "Costuras: 352, 414 mm".
    #
    # Se corre el arranque de cada capa por el ángulo áureo: no repite nunca y
    # las costuras quedan repartidas.
    #
    # Esto SOLO se puede hacer junto con el orden en serpentina de más abajo.
    # Girando el arranque sin encadenar las pasadas, cada una tiene que volver y
    # ese viaje de vuelta cae en un ángulo distinto cada vez: medido, el viaje
    # pasaba de 32.4 a 78.4 m y los cruces por el hueco de la lámpara de 122
    # a 454. Las dos cosas juntas sí funcionan.
    # El giro es PEQUEÑO a propósito: la costura se corre unos pocos grados por
    # capa y describe una espiral lenta, como hace un slicer. Saltando medio
    # giro (se probó con el ángulo áureo) la costura queda mejor repartida —7 %
    # en el peor sector contra 46 %— pero cuesta un viaje largo POR CAPA: medido,
    # 866 viajes y 69.6 m contra 537 y 22.1 m, con 413 cruces por el hueco de la
    # lámpara contra 81. No compensa.
    GIRO_COSTURA = 5.0 / 360.0      # vuelta completa cada 72 capas

    def angulos_de(v):
        off = (v * GIRO_COSTURA) % 1.0
        return [(k / segmentos + off) * TAU for k in range(segmentos + 1)]

    def perfil_en(t, angs):
        return [silueta(t) + deformacion(a, t) for a in angs]

    pasos = pasos_iniciales(perfil)
    pts: list = []
    z = paso
    for v in range(n_v):
        t = (v + 1) / n_v
        angs = angulos_de(v)
        r_prev = perfil_en(v / n_v, angs)
        r_now = perfil_en(t, angs)

        # Cuántas pasadas hacen falta EN CADA ÁNGULO. Antes se calculaba una
        # sola cifra para toda la vuelta —el peor corrimiento— y se aplicaba a
        # todos los ángulos: donde la pared se movió 68 mm quedaban a un cordón,
        # y donde se movió 3 mm las mismas 38 pasadas se apretaban en 3 mm, o
        # sea 0.08 mm entre cordones de 1.8. Medido sobre la pieza entera, el
        # 89% del recorrido quedaba pisado. El número tiene que ser local.
        # Los radios de cada pasada, ángulo por ángulo, de adentro hacia afuera.
        # `solape` es un margen de seguridad sobre la separación de fusión, no
        # una fracción del ancho: por debajo de ella los cordones se pisan y por
        # encima no se tocan, y la ventana entre las dos cosas es estrecha.
        d_paso = (ancho - 0.215 * paso) * solape
        radios = [_radios_pasada(a, b, d_paso, primer_escalon, ancho, paso)
                  for a, b in zip(r_prev, r_now)]
        m = [len(rr) for rr in radios]
        n_sub = max(m)

        # El relleno se emite POR REGIONES CONTIGUAS, no barriendo los 360° en
        # cada pasada.
        #
        # Barriendo entero, si hacen falta pasadas en tres zonas sueltas de la
        # vuelta el recorrido salta de una a otra, y esos saltos cruzan el hueco
        # de la lámpara. Medido: 864 viajes, 174 de ellos de más de 50 mm que
        # suman 16.9 de los 26.2 m totales, y una sola capa —la del cambio de
        # bloque— con 202 viajes. Agrupando, los saltos se quedan dentro de su
        # zona y son cortos.
        #
        # La pasada 1 sí barre entero: existe en todos los ángulos (m >= 1
        # siempre) y es un lazo cerrado sin un solo viaje.
        regiones = []
        k = 0
        while k < len(m):
            if m[k] >= 2:
                j = k
                while j < len(m) and m[j] >= 2:
                    j += 1
                regiones.append((k, j - 1))
                k = j
            else:
                k += 1

        def emitir(i, k0, k1, al_derecho):
            """Una pasada `i` sobre el tramo de ángulos [k0, k1]."""
            nonlocal_extruyendo = [False]
            pts.append(fc.ManualGcode(
                text=";TIPO:base" if i == 1 else ";TIPO:relleno"))
            rango = range(k0, k1 + 1) if al_derecho else range(k1, k0 - 1, -1)
            for k in rango:
                if i > m[k]:
                    if nonlocal_extruyendo[0]:
                        pts.append(fc.Extruder(on=False))
                        pts.append(fc.ManualGcode(text=RETRAER))
                        nonlocal_extruyendo[0] = False
                    continue
                pts.append(_punto(perfil, radios[k][i - 1], angs[k], z))
                if not nonlocal_extruyendo[0]:
                    # el primer punto de un tramo es un viaje; se abre después
                    pts.append(fc.ManualGcode(text=CEBAR))
                    pts.append(fc.Extruder(on=True))
                    nonlocal_extruyendo[0] = True
            if nonlocal_extruyendo[0]:
                pts.append(fc.Extruder(on=False))
                pts.append(fc.ManualGcode(text=RETRAER))

        # La pasada 1 barre la vuelta entera: existe en todos los ángulos y es
        # un lazo cerrado sin un solo viaje. Es la que apoya en la capa de abajo.
        emitir(1, 0, len(angs) - 1, True)

        # El relleno, REGIÓN POR REGIÓN: se terminan todas las pasadas de una
        # zona antes de pasar a la siguiente.
        #
        # El orden importa mucho y no es obvio. Emitiendo pasada por pasada
        # sobre toda la vuelta, el recorrido salta de una zona a otra en CADA
        # pasada, y esos saltos cruzan el hueco de la lámpara: 864 viajes con
        # 97 cruces. Agrupando por región pero dejando la pasada afuera del
        # bucle, salen menos viajes pero MÁS cruces (695 y 149), porque al
        # terminar la última región de una pasada hay que volver a la primera.
        # Con la región afuera hay un solo viaje de entrada y otro de salida
        # por zona, y la serpentina se encadena dentro.
        # Y en orden de CERCANÍA, no en el orden en que aparecen. Dos regiones en
        # lados opuestos de la vuelta obligan a un salto que pasa por el centro
        # de la pieza, que es justo el que se ve cruzando el hueco de la lámpara.
        # Se arranca por la que quedó más cerca de donde terminó la pasada 1 y se
        # sigue por la más cercana cada vez.
        pendientes = list(regiones)
        aqui = len(angs) - 1          # la pasada 1 terminó en el último ángulo
        t_i = 0
        while pendientes:
            def dist(reg):
                # distancia angular al extremo más cercano de la región
                return min(abs(reg[0] - aqui), abs(reg[1] - aqui),
                           len(angs) - abs(reg[0] - aqui),
                           len(angs) - abs(reg[1] - aqui))
            reg = min(pendientes, key=dist)
            pendientes.remove(reg)
            k0, k1 = reg
            # entrar por el extremo más cercano
            al_derecho = min(abs(k0 - aqui), len(angs) - abs(k0 - aqui)) <= \
                         min(abs(k1 - aqui), len(angs) - abs(k1 - aqui))
            m_max = max(m[k0:k1 + 1])
            for i in range(2, m_max + 1):
                emitir(i, k0, k1, al_derecho)
                al_derecho = not al_derecho
            aqui = k0 if al_derecho else k1
            t_i += 1
        z += paso

    primero = next(i for i, q in enumerate(pts) if isinstance(q, fc.Point))
    pasos.extend(pts[:primero])
    pasos.append(fc.Extruder(on=False))
    pasos.append(pts[primero])
    pasos.append(fc.Extruder(on=True))
    pasos.extend(pts[primero + 1:])
    return pasos


# ---------------------------------------------------------------------------
# La pantalla glitch, séptimo intento: pared intacta + lenguas a mano
# ---------------------------------------------------------------------------

# Etiquetas que se emiten como comentario en el g-code. No son decorativas: son
# la única forma honesta de medir después. Las seis versiones anteriores se
# midieron separando pared de lengua POR GEOMETRÍA (un filtro por radio), los
# primeros arcos de cada lengua caían del lado equivocado, y el número que salía
# de ahí hizo abandonar el enfoque correcto. Se etiqueta al emitir.
MARCA_PARED = ";TIPO:pared"
MARCA_LENGUA = ";TIPO:lengua"

# El g-code sale en extrusión relativa (M83), así que retraer y cebar la misma
# cantidad no corre el contador: lo que emite FullControl después sigue valiendo.
RETRAER = "G1 E-0.8 F2100 ; retraer para el salto a la lengua"
CEBAR = "G1 E0.8 F2100 ; cebar de nuevo"


@dataclass
class Lengua:
    """
    Una lengua, colocada a mano.

    A mano y no al azar por dos razones concretas: se verifica lengua por lengua
    en vez de en promedio, y el resultado se parece al dibujo —que tiene las
    lenguas en lugares determinados—, cosa que veintiséis al azar nunca dieron.

    Args:
        t: altura relativa donde nace, 0 en la base y 1 en la boca.
        angulo: en grados. 0 es +X.
        vuelo: cuánto sale de la pared, en mm.
        arco: cuántos grados abarca en la raíz.
        capas: cuántas alturas apila. 2 = ida hacia afuera y vuelta hacia
            adentro una capa más arriba, o sea dos cordones de espesor.
        afinado: cuánto se acorta el arco al llegar a la punta. 0 = repisa de
            ancho constante; 0.6 = lengua en punta.
    """

    t: float
    angulo: float
    vuelo: float
    arco: float
    capas: int = 2
    afinado: float = 0.5


# La banda del dibujo: rota, corrida hacia un lado, con las lenguas más largas
# agrupadas y algunas sueltas más arriba y más abajo. El centro de la banda está
# en t≈0.52 y la masa de lenguas mira hacia +X.
LENGUAS_GLITCH = [
    Lengua(t=0.42, angulo=-38, vuelo=14, arco=26, afinado=0.55),
    Lengua(t=0.45, angulo=12, vuelo=26, arco=40, afinado=0.45),
    Lengua(t=0.47, angulo=58, vuelo=18, arco=30, afinado=0.55),
    Lengua(t=0.50, angulo=-14, vuelo=32, arco=46, afinado=0.40),
    Lengua(t=0.52, angulo=96, vuelo=12, arco=22, afinado=0.60),
    Lengua(t=0.54, angulo=34, vuelo=30, arco=44, afinado=0.45),
    Lengua(t=0.56, angulo=-72, vuelo=16, arco=28, afinado=0.55),
    Lengua(t=0.58, angulo=2, vuelo=24, arco=38, afinado=0.50),
    Lengua(t=0.61, angulo=-110, vuelo=11, arco=20, afinado=0.60),
    Lengua(t=0.63, angulo=52, vuelo=20, arco=32, afinado=0.50),
]


# La misma banda, con la densidad del dibujo. Sigue siendo una lista explícita:
# cada lengua se verifica sola y se mueve sola. Veintiséis al azar nunca daban
# esto, porque el dibujo tiene la masa agrupada hacia un lado y huecos limpios
# entre los grupos, y el azar reparte parejo.
LENGUAS_DENSAS = [
    Lengua(t=0.38, angulo=-24, vuelo=10, arco=20, afinado=0.60),
    Lengua(t=0.40, angulo=20, vuelo=16, arco=28, afinado=0.55),
    Lengua(t=0.41, angulo=-56, vuelo=12, arco=22, afinado=0.60),
    Lengua(t=0.43, angulo=6, vuelo=22, arco=36, afinado=0.50),
    Lengua(t=0.44, angulo=64, vuelo=14, arco=26, afinado=0.55),
    Lengua(t=0.46, angulo=-32, vuelo=26, arco=40, afinado=0.45),
    Lengua(t=0.47, angulo=38, vuelo=20, arco=32, afinado=0.50),
    Lengua(t=0.49, angulo=-8, vuelo=32, arco=46, afinado=0.40),
    Lengua(t=0.50, angulo=104, vuelo=11, arco=20, afinado=0.60),
    Lengua(t=0.51, angulo=52, vuelo=28, arco=42, afinado=0.45),
    Lengua(t=0.53, angulo=-80, vuelo=15, arco=26, afinado=0.55),
    Lengua(t=0.54, angulo=14, vuelo=34, arco=48, afinado=0.40),
    Lengua(t=0.55, angulo=-44, vuelo=24, arco=38, afinado=0.50),
    Lengua(t=0.57, angulo=78, vuelo=18, arco=30, afinado=0.55),
    Lengua(t=0.58, angulo=-2, vuelo=30, arco=44, afinado=0.45),
    Lengua(t=0.59, angulo=132, vuelo=9, arco=18, afinado=0.60),
    Lengua(t=0.60, angulo=44, vuelo=25, arco=38, afinado=0.50),
    Lengua(t=0.62, angulo=-64, vuelo=13, arco=24, afinado=0.55),
    Lengua(t=0.63, angulo=24, vuelo=27, arco=40, afinado=0.45),
    Lengua(t=0.64, angulo=-20, vuelo=17, arco=30, afinado=0.55),
    Lengua(t=0.66, angulo=88, vuelo=12, arco=22, afinado=0.60),
    Lengua(t=0.67, angulo=34, vuelo=21, arco=34, afinado=0.50),
    Lengua(t=0.68, angulo=-100, vuelo=10, arco=20, afinado=0.60),
    Lengua(t=0.70, angulo=8, vuelo=16, arco=28, afinado=0.55),
]


def _pasos_lengua(perfil: Perfil, lengua: Lengua, r_pared: float, ang0: float,
                  z0: float, paso: float, sep: float) -> List[fc.Point]:
    """
    Una lengua: arcos concéntricos a Z CONSTANTE, hacia afuera y de vuelta.

    El arco más interno corre pegado a la pared —a un `sep` de ella, o sea
    solapado— y cada arco siguiente se acuesta al lado del anterior. Ninguno le
    pide apoyo a la vuelta de abajo: es el mecanismo del piso macizo de un bol,
    que es lo que permite volar 30 mm sin deberle nada al paso vertical.

    Los arcos se acortan hacia la punta (`afinado`), así que el extremo de cada
    uno cae DENTRO del arco anterior, que es más largo, y llega apoyado.

    El sentido se alterna arco por arco con un contador único que atraviesa las
    capas: así el final de un arco siempre queda donde arranca el siguiente,
    incluso en el salto de capa, y no hay viajes en el aire dentro de la lengua.
    """
    n = max(1, int(math.ceil(lengua.vuelo / sep)))
    med0 = math.radians(lengua.arco) / 2
    pts: List[fc.Point] = []
    nn = 0
    for capa in range(max(1, int(lengua.capas))):
        zc = z0 + capa * paso
        # La capa de ida abre de la pared hacia afuera; la de vuelta cierra de
        # afuera hacia la pared, y termina donde tiene que seguir la espiral.
        orden = range(n) if capa % 2 == 0 else range(n - 1, -1, -1)
        for k in orden:
            r = r_pared + sep * (k + 1)
            med = med0 * (1 - lengua.afinado * (k / max(1, n - 1)))
            paso_ang = 1.0 / max(r, 0.6)
            tramo = []
            b = -med
            while b <= med:
                tramo.append(_punto(perfil, r, ang0 + b, zc))
                b += paso_ang
            if not tramo:
                continue
            pts.extend(tramo if nn % 2 == 0 else tramo[::-1])
            nn += 1
    return pts


def _emitir(pts, perfil, lengua, r_pared, ang0, z0, paso, sep, p_pared) -> int:
    """
    Mete una lengua en el recorrido y vuelve a dejarlo sobre la pared.

    Se entra y se sale VIAJANDO. Extruyendo, el salto de la pared al arranque
    del arco es una cuerda de decenas de milímetros tendida en el aire.

    Y con retracción: el viaje mide hasta 35 mm y cruza el hueco entre la pared
    y la punta de la lengua, que es aire. Sin retraer, cada entrada y cada
    salida deja un hilo colgado justo en la parte de la pieza que se mira.
    Son veinte viajes en total, así que cuesta nada.
    """
    tramo = _pasos_lengua(perfil, lengua, r_pared, ang0, z0, paso, sep)
    if not tramo:
        return 0
    pts.append(fc.Extruder(on=False))
    pts.append(fc.ManualGcode(text=RETRAER))
    pts.append(tramo[0])
    pts.append(fc.ManualGcode(text=CEBAR))
    pts.append(fc.Extruder(on=True))
    pts.append(fc.ManualGcode(text=MARCA_LENGUA))
    pts.extend(tramo[1:])
    pts.append(fc.Extruder(on=False))
    pts.append(fc.ManualGcode(text=RETRAER))
    pts.append(p_pared)
    pts.append(fc.ManualGcode(text=CEBAR))
    pts.append(fc.Extruder(on=True))
    pts.append(fc.ManualGcode(text=MARCA_PARED))
    return 1


def pasos_pantalla_lenguas(
    perfil: Perfil,
    altura: float = 140.0,
    radio: Callable[[float], float] = None,
    lenguas: Optional[List[Lengua]] = None,
    solape: float = 0.85,
    onda: float = 0.0,
) -> list:
    """
    La pantalla glitch con las dos técnicas en capas distintas, de verdad.

    El diagnóstico de la sesión anterior fue que nunca se combinaron: en un caso
    el glitch se metió DENTRO de la pared —que la obliga a acostarse, el paso
    adaptativo se comprime, y termina pidiendo un cordón de 1.8 x 0.05 que
    ninguna boquilla de 0.8 tiende—; en el otro se reemplazó la espiral entera
    por pasadas planas, y las vueltas dejaron de tocarse. Acá:

    - **La pared no se toca.** Espiral normal, paso fijo en la altura de capa,
      cordón entero, cada vuelta apoyada en la anterior. Es la misma espiral del
      hongo, que mide 1.22 % de cordones sueltos. Nunca entra en la zona
      imposible porque nada la obliga a tumbarse.
    - **El glitch va ENCIMA**, como estructura aparte: lenguas planas que salen
      de la pared, corren a Z constante y vuelven. Se apoyan de costado.

    Las lenguas arrancan a un cordón POR FUERA de la pared, no encima: así se
    sueldan de lado con la vuelta que se está imprimiendo, y la vuelta siguiente
    de la pared —que pasa a la misma altura que la segunda capa de la lengua—
    corre por dentro sin chocarla.

    Args:
        lenguas: la lista explícita. Por defecto `LENGUAS_GLITCH`.
        solape: separación entre arcos de una lengua, en fracción de cordón.
            0.85 deja 15 % de solape lateral. Por encima de 1 no se tocan.
        onda: ondulación de la pared, en mm. Va en 0 a propósito — la pared es
            lo que sostiene la pieza y el efecto vive en las lenguas.
    """
    if radio is None:
        radio = lambda t: 95 - 40 * t  # noqa: E731
    if lenguas is None:
        lenguas = LENGUAS_GLITCH

    paso = perfil.altura_capa
    sep = perfil.ancho * solape
    n_v = max(1, int(altura / paso))

    # En qué vuelta y en qué ángulo local sale cada lengua.
    #
    # La lengua NO se dispara al llegar a su ángulo central sino al TERMINAR de
    # recorrer su arco. Disparándola en el centro, la mitad de adelante del
    # primer arco se deposita antes que la pared con la que tiene que soldarse:
    # lo único que tiene debajo es la vuelta ANTERIOR, un cordón más abajo y
    # 1.5 mm hacia adentro, o sea un voladizo del 85 % por capa. Medido, eran
    # 207 segmentos sueltos y nueve puentes de hasta 29 mm.
    #
    # Disparándola al final del arco, toda la pared de abajo ya está puesta y a
    # la misma altura: la espiral sube `paso · arco/2π` en el tramo, que para un
    # arco de 46° son 0.05 mm.
    por_vuelta = {}
    for lg in lenguas:
        v = min(n_v - 1, max(0, int(lg.t * n_v)))
        med0 = math.radians(lg.arco) / 2
        u0 = math.radians(lg.angulo) % TAU
        # El arco tiene que caber entero antes de la costura de la vuelta; si el
        # ángulo pedido lo empuja afuera, se corre lo mínimo para que entre.
        disparo = u0 + med0
        if disparo >= TAU:
            # El arco cruza la costura de la vuelta: la lengua entera se pasa a
            # la vuelta siguiente, mismo ángulo y 0.4 mm más arriba. Recortar el
            # disparo contra TAU en vez de esto dejaba el disparo tan al final
            # de la vuelta que el barrido angular no llegaba a cruzarlo, y la
            # lengua no se emitía: se perdió la más grande de las diez y el
            # g-code salió con nueve sin avisar.
            v, disparo = min(n_v - 1, v + 1), disparo - TAU
        por_vuelta.setdefault(v, []).append((disparo, disparo - med0, lg))
    for v in por_vuelta:
        por_vuelta[v].sort(key=lambda p: p[0])

    r_max = max(radio(0.0), radio(1.0),
                *(radio(lg.t) + lg.vuelo + sep for lg in lenguas)) if lenguas else radio(0.0)
    _verificar_cama(r_max, perfil)

    pasos = pasos_iniciales(perfil)
    pts: list = [fc.ManualGcode(text=MARCA_PARED)]
    z = paso
    emitidas = 0
    for v in range(n_v):
        t0 = v / n_v
        cola = por_vuelta.get(v, ())
        i_cola = 0
        aa = 0.0
        while aa < TAU:
            tt = t0 + aa / TAU / n_v
            r = radio(tt) + (onda * math.sin(3 * (v * TAU + aa)) if onda else 0.0)
            zz = z + paso * aa / TAU
            p_pared = _punto(perfil, r, v * TAU + aa, zz)
            pts.append(p_pared)

            while i_cola < len(cola) and cola[i_cola][0] <= aa:
                _, centro, lg = cola[i_cola]
                i_cola += 1
                # El arco va centrado en `centro`, que quedó atrás; la altura es
                # la de acá, el punto más alto de la pared bajo la lengua.
                emitidas += _emitir(pts, perfil, lg, r, v * TAU + centro, zz,
                                    paso, sep, p_pared)

            aa += 1.0 / max(r, 0.6)

        # Lo que haya quedado sin disparar porque el barrido angular saltó por
        # encima del ángulo, sale acá. Ninguna lengua se pierde en silencio.
        while i_cola < len(cola):
            _, centro, lg = cola[i_cola]
            i_cola += 1
            emitidas += _emitir(pts, perfil, lg, r, v * TAU + centro, zz, paso, sep,
                                p_pared)
        z += paso

    if emitidas != len(lenguas):
        raise AssertionError(
            f"se pidieron {len(lenguas)} lenguas y se emitieron {emitidas}")

    primero = next(i for i, q in enumerate(pts) if isinstance(q, fc.Point))
    salida = pasos + pts[:primero]
    salida.append(fc.Extruder(on=False))
    salida.append(pts[primero])
    salida.append(fc.Extruder(on=True))
    salida.extend(pts[primero + 1:])
    return salida
