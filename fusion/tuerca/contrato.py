"""
Contrato hembra->macho de la lampara tornillo.

La hembra NO cambia nunca: riel helicoidal continuo de seccion circular.
Todo macho valido se define sobre la MISMA helice y se valida aqui,
sin booleanos temporales en Fusion.

Regla de oro
------------
Todo rasgo del macho es una union de bolas. Una bola de radio rho cuyo centro
esta a distancia (d, e) de la helice (d = perpendicular dentro de la superficie,
o sea axial-ish; e = radial) cumple:

    sqrt(d^2 + e^2) + rho <= A_MAESTRO      -> nunca interfiere
    d == 0 and rho >= A_MAESTRO - t         -> apoya en AMBOS flancos

Corolario util (restriccion caligrafica): si dibujas siempre con e = 0 y
|d| + rho = A_MAESTRO, cada trazo es tangente interior al maestro. El ancho
maximo de pincel a la altura d es 2*(A_MAESTRO - |d|): gordo en el centro de
la banda, fino en los bordes. Dibujar dentro de esa regla == geometria valida.
"""
import math

# ---------------------------------------------------------------- invariantes
R_HELICE   = 50.75   # radio del eje del riel (mm)
PASO       = 13.5    # paso axial (mm), rosca derecha, 1 entrada
A_HEMBRA   = 5.50    # radio de la seccion del riel (D11)
R_BARRENO  = 52.20   # barreno liso de las caperuzas
HOLGURA    = 0.20    # holgura radial/axial objetivo por lado

A_MAESTRO  = A_HEMBRA - HOLGURA      # 5.30  radio de la seccion del solido maestro
R_NUCLEO_MAX = R_BARRENO - HOLGURA   # 52.00 radio maximo del nucleo cilindrico
R_NUCLEO   = 50.00                   # nucleo real del tubo actual
R_INT      = 49.00                   # pared interna actual

K          = PASO / (2 * math.pi)               # avance axial por radian
ARCO_RAD   = math.hypot(R_HELICE, K)            # mm de arco de helice por radian
ARCO_VUELTA= 2 * math.pi * ARCO_RAD             # longitud de una vuelta
ANG_HELICE = math.degrees(math.atan2(K, R_HELICE))
PASO_PERP  = PASO * math.cos(math.radians(ANG_HELICE))  # separacion entre vueltas

TOL_APOYO  = 0.25    # cuanto juego axial por lado aceptamos y seguimos llamandolo apoyo


def semiancho_hembra(r):
    """Semiancho del riel de la hembra al radio r (0 si no existe alli)."""
    q = A_HEMBRA**2 - (r - R_HELICE)**2
    return math.sqrt(q) if q > 0 else 0.0


def semiancho_maestro(r):
    """Semiancho del solido maestro (envolvente del macho) al radio r."""
    q = A_MAESTRO**2 - (r - R_HELICE)**2
    return math.sqrt(q) if q > 0 else 0.0


def frac_axial(r):
    """Componente axial de la normal de contacto al radio r. 1 = apoyo puro axial."""
    return semiancho_maestro(r) / A_MAESTRO if r < R_HELICE + A_MAESTRO else 0.0


# ------------------------------------------------------------------- primitiva
class Bola:
    """Bola en coordenadas de helice: s a lo largo, d perpendicular-en-superficie, e radial."""
    __slots__ = ("s", "d", "e", "rho", "tag")

    def __init__(self, s, d, e, rho, tag=""):
        self.s, self.d, self.e, self.rho, self.tag = s, d, e, rho, tag

    @property
    def off(self):
        return math.hypot(self.d, self.e)

    @property
    def margen(self):
        """Cuanto sobra hasta el maestro. <0 = interferencia con la hembra."""
        return A_MAESTRO - (self.off + self.rho)

    @property
    def r_max(self):
        return R_HELICE + self.e + self.rho

    @property
    def r_min(self):
        return R_HELICE + self.e - self.rho

    def apoya(self):
        """Toca ambos flancos: centrada en d=0 y casi tan gorda como el maestro."""
        return abs(self.d) <= 1e-6 and self.rho >= A_MAESTRO - TOL_APOYO

    def toca_flanco(self):
        """Toca UN flanco (tangente interior al maestro): sirve de tope en un sentido."""
        return self.margen <= 1e-6 + TOL_APOYO and abs(self.d) > 1e-6

    def juego_axial(self, r=R_BARRENO):
        """Juego total (mm) que le queda a esta bola dentro del riel, al radio r."""
        wh = semiancho_hembra(r)
        q = self.rho**2 - (r - R_HELICE - self.e)**2
        if q <= 0:
            return float("nan")   # no llega a ese radio
        return 2 * (wh - math.sqrt(q))

    def punto(self, phi0=0.0):
        """Posicion 3D absoluta (mm), con la helice arrancando en phi0."""
        phi = phi0 + self.s / ARCO_RAD
        c, sn = math.cos(phi), math.sin(phi)
        P = (R_HELICE * c, R_HELICE * sn, K * phi)
        er = (c, sn, 0.0)
        n = (K * sn / ARCO_RAD, -K * c / ARCO_RAD, R_HELICE / ARCO_RAD)
        return tuple(P[i] + self.d * n[i] + self.e * er[i] for i in range(3))


def valida(celula, nombre=""):
    """Devuelve (ok, lineas de reporte) para una celula."""
    out, ok = [], True
    for b in celula:
        if b.margen < -1e-9:
            ok = False
            out.append(f"    INTERFIERE  {b.tag:12s} off={b.off:5.2f} rho={b.rho:5.2f} margen={b.margen:+6.3f}")
        elif b.r_min < R_INT - 1e-9:
            out.append(f"    aviso       {b.tag:12s} entra al hueco (r_min={b.r_min:.2f} < {R_INT})")
    return ok, out
