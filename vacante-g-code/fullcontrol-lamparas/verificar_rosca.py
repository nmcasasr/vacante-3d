"""
Valida una rosca macho contra el riel hembra invariante, sin CAD.

Comprueba las tres cosas que importan:
  1. CONTENCIÓN  -- que enrosque (nunca supera la envolvente del riel).
  2. APOYO       -- que cargue (el flanco de arriba toca, y cada cuánto).
  3. VOLADIZO    -- que se imprima (mismo criterio que comun._verificar_voladizo).
"""
import math, sys, types, importlib.util, pathlib

# se importa por ruta: `lamparas/__init__` arrastra fullcontrol y acá sólo
# hacemos aritmética, así que la validación corre sin la impresora encima.
#
# Hace falta registrar un paquete `lamparas` VACÍO antes, y no es un detalle:
# `rosca.py` importa `from .envolvente_hembra import ...`, y un módulo cargado
# por ruta suelta no tiene paquete padre, así que el import relativo revienta.
# El paquete de mentira sólo aporta el `__path__`; su `__init__` real —el que
# arrastra fullcontrol— no se ejecuta nunca.
_dir = pathlib.Path(__file__).resolve().parent / 'lamparas'
if 'lamparas' not in sys.modules:
    _pkg = types.ModuleType('lamparas')
    _pkg.__path__ = [str(_dir)]
    sys.modules['lamparas'] = _pkg
_spec = importlib.util.spec_from_file_location('lamparas.rosca', _dir / 'rosca.py')
R = importlib.util.module_from_spec(_spec)
sys.modules['lamparas.rosca'] = R
_spec.loader.exec_module(R)


def verificar(nombre, func_radio, altura=230.0, paso_z=0.4, ancho=0.8,
              n_ang=720, n_z=None, carga='arriba'):
    """
    `carga='abajo'` significa que la pieza se imprime DADA VUELTA, así que el
    voladizo hay que medirlo sobre la geometría invertida. La contención y el
    apoyo, en cambio, se miden siempre en coordenadas de uso: son propiedades
    del encastre, no de cómo salió de la impresora.
    """
    n_z = n_z or int(altura / paso_z)
    r_impresion = ((lambda a, t: func_radio(a, 1.0 - t)) if carga == 'abajo'
                   else func_radio)
    peor_exceso = -9e9
    salto_max = 0.0
    apoyo_por_vuelta = 0
    radios = {}
    for i in range(n_ang):
        ang = 2 * math.pi * i / n_ang
        col = []
        for j in range(n_z):
            z = j * paso_z
            r = func_radio(ang, z / altura)
            d = R.coordenada_hilo(ang, z)
            peor_exceso = max(peor_exceso, r - R.perfil_envolvente(d))
            col.append(r_impresion(ang, z / altura))
        radios[i] = col
        for j in range(len(col) - 1):
            salto_max = max(salto_max, col[j + 1] - col[j])

    # Apoyo: ¿el hilo llega al techo del riel?
    #
    # El criterio se mide contra la ENVOLVENTE medida —el interior de la
    # caperuza menos la holgura— y no contra el barreno redondo de Ø11 del
    # primer modelo, que ya no existe: la hembra real se sacó de `tuerca.stl`.
    # Se mira la fase de la CRESTA, que es donde el hilo llega más lejos, y se
    # da por apoyado lo que queda a menos de 0.15 mm del techo.
    techo = max(R.ENVOLVENTE)
    d_apoyo = R.D_CRESTA
    if carga == 'abajo':
        d_apoyo = -d_apoyo
    toca = []
    for i in range(n_ang):
        ang = 2 * math.pi * i / n_ang
        z = d_apoyo + R.PASO * ang / (2 * math.pi) + R.PASO * 6
        toca.append(func_radio(ang, z / altura) >= techo - 0.15)
    frac = sum(toca) / n_ang
    paso_arco = R.ARCO_VUELTA / n_ang
    hueco = corrido = 0
    for k in range(2 * n_ang):            # dos vueltas: el hueco puede cruzar el 0
        corrido = 0 if toca[k % n_ang] else corrido + 1
        hueco = max(hueco, corrido)
    hueco_mm = min(hueco, n_ang) * paso_arco

    solape = ancho - salto_max
    ang_vol = math.degrees(math.atan2(salto_max, paso_z))
    # Tolerancia de una centésima, no cero.
    #
    # La envolvente y el perfil clásico son DOS tablas de 270 muestras cada una,
    # interpoladas linealmente, y se evalúan en 720 ángulos: entre muestra y
    # muestra las dos curvas no se interpolan igual y aparecen picos de unas
    # micras que no son geometría. Medido sobre el perfil clásico —la pieza que
    # ya enrosca— el exceso da +0.0088 mm. Con el corte en cero, el propio STL
    # de referencia salía INTERFIERE.
    #
    # 0.01 mm es dos órdenes por debajo de la holgura de montaje (0.20) y por
    # debajo de lo que una boquilla de 0.8 puede colocar.
    ok_cont = peor_exceso <= 0.01
    ok_vol = solape >= ancho * 0.5
    ok_apo = frac > 0 and hueco_mm < R.PASO_APOYO_MAX

    print(f"--- {nombre}")
    print(f"    contención : exceso máx sobre la envolvente {peor_exceso:+.4f} mm  "
          f"{'OK (enrosca)' if ok_cont else 'INTERFIERE'}")
    print(f"    apoyo      : {100*frac:5.1f}% del recorrido toca el flanco portante; "
          f"tramo contiguo sin apoyo más largo {hueco_mm:.1f} mm  "
          f"{'OK' if ok_apo else 'INSUFICIENTE'}")
    print(f"    voladizo   : ({'impresa dada vuelta' if carga=='abajo' else 'impresa derecha'}) "
          f"el radio crece {salto_max:.3f} mm/vuelta sobre cordón {ancho} "
          f"({100*solape/ancho:.0f}% de solape, {ang_vol:.0f}° desde vertical)  "
          f"{'OK' if ok_vol else ('JUSTO' if solape>0 else 'SE CAE')}")
    return ok_cont and ok_vol


if __name__ == '__main__':
    H = 230.0
    ANCHO = 1.2          # el cordón real de la rosca, no el 0.8 de la boquilla
    PASO_Z = 0.30        # el que usa `gen_rosca.py` cuando fija la capa
    # Las funciones se piden con `ancho_cordon=0`, o sea la SUPERFICIE y no la
    # trayectoria. `generar_pieza` recibe el recorrido y por eso `gen_rosca` le
    # descuenta medio cordón; acá lo que se mide es dónde queda la pared, y con
    # el descuento puesto todo daba medio cordón por debajo de la envolvente
    # —contención -0.59 mm y apoyo 0.0 % en las nueve variantes, que es el
    # síntoma de estar midiendo el eje del cordón contra el techo del riel.
    print(f"hembra medida de tuerca.stl: cresta R{max(R.ENVOLVENTE):.2f}, "
          f"núcleo R{R.R_NUCLEO:.2f}, paso {R.PASO} | arco/vuelta {R.ARCO_VUELTA:.1f} mm")
    print(f"apoyo: hueco contiguo máximo admitido {R.PASO_APOYO_MAX:.0f} mm\n")

    print("### referencia: el perfil que ya imprimís")
    verificar("clásico (medido del STL)",
              R.rosca(None, altura=H, ancho_cordon=0.0), H, paso_z=PASO_Z, ancho=ANCHO)
    print()

    print("### patrones que sólo REBAJAN el hilo clásico")
    for nombre, patron in [
        ("perlas 20/vuelta",        R.p_perlas(20)),
        ("interrumpida 6 sectores", R.p_interrumpida(6)),
        ("ondas 24/vuelta",         R.p_ondas(24)),
        ("chevron 12/vuelta",       R.p_chevron(12)),
        ("moleteado 30/vuelta",     R.p_moleteado(30)),
        ("caritas grabadas 16",     R.p_caritas(16)),
    ]:
        verificar(nombre, R.rosca(patron, altura=H, ancho_cordon=0.0), H, paso_z=PASO_Z, ancho=ANCHO)
    print()

    print("### relieves: los rasgos SON el hilo")
    # OJO con el voladizo de los sellos: se mide a paso FIJO de 0.30 mm, y para
    # ellos `gen_rosca.py` no usa paso fijo —mide el salto radial y se pasa al
    # adaptativo, que acorta la capa justo en el canto del sello—. El veredicto
    # de acá es el del paso fijo, no el del g-code que sale.
    verificar("caritas en relieve",
              R.caritas_relieve(altura=H, ancho_cordon=0.0), H, paso_z=PASO_Z, ancho=ANCHO)
    for forma in ("corazon", "estrella"):
        verificar(f"sellos de {forma}",
                  R.sellos_relieve(forma, altura=H, ancho_cordon=0.0), H, paso_z=PASO_Z, ancho=ANCHO)
