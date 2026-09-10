"""Registra cada llamada a funcion_radio y la compara contra el g-code emitido."""
import math, sys, json
sys.path.insert(0, '.')
from lamparas.comun import Perfil, generar_pieza, a_gcode, guardar_gcode
from lamparas import rosca

ALTURA = 40.0
p = Perfil(diametro_boquilla=0.8, altura_capa=0.4, ancho_linea=1.2,
           velocidad_impresion=2400, temp_boquilla=245, temp_cama=80, ventilador=50)
base = rosca.caritas_relieve(9, altura=ALTURA, ancho_cordon=p.ancho)
registro = []
def fr(angulo, t):
    r = base(angulo, t)
    registro.append((angulo, t, r))
    return r
pasos = generar_pieza(fr, altura=ALTURA, perfil=p, segmentos_por_capa=360)
ruta = guardar_gcode(a_gcode(pasos, p), "rosca/instr")
print("gcode:", ruta, "| llamadas registradas:", len(registro))
with open("registro.json", "w") as f:
    json.dump(registro[:400000], f)

from lamparas.comun import ULTIMO_MAPEO
zc = ULTIMO_MAPEO["z_capa"]
print(f"\nULTIMO_MAPEO: z0={ULTIMO_MAPEO['z0']:.3f}  z1={ULTIMO_MAPEO['z1']:.3f}  capas={ULTIMO_MAPEO['capas']}")
print(f"altura pedida: {ALTURA}   altura real de la pared: {ULTIMO_MAPEO['z1']-ULTIMO_MAPEO['z0']:.3f}")
print(f"estiramiento: {(ULTIMO_MAPEO['z1']-ULTIMO_MAPEO['z0'])/ALTURA:.4f}x")
print("\nz real de cada capa contra la rampa lineal que supone la funcion:")
n=len(zc)
for i in range(0, n, max(1,n//12)):
    t = i/(n-1)
    print(f"   capa {i:4d}  t={t:.3f}   z real {zc[i]:7.3f}   t*altura {t*ALTURA:7.3f}   "
          f"desfase {zc[i]-ULTIMO_MAPEO['z0']-t*ALTURA:+7.3f} mm")
