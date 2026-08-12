"""Genera la pantalla glitch: pared intacta + lenguas colocadas a mano."""
import sys
sys.path.insert(0, '.')
from lamparas.comun import Perfil, a_gcode, guardar_gcode
from lamparas import recorrido
from lamparas.recorrido import pasos_pantalla_lenguas

nombre = sys.argv[1] if len(sys.argv) > 1 else "glitch4"
LENGUAS_GLITCH = getattr(recorrido, sys.argv[2] if len(sys.argv) > 2 else "LENGUAS_GLITCH")
p = Perfil(diametro_boquilla=0.8, altura_capa=0.4, ancho_linea=1.8,
           velocidad_impresion=1200, temp_boquilla=245, temp_cama=80, ventilador=0)
pasos = pasos_pantalla_lenguas(p, altura=140, radio=lambda t: 95 - 40 * t,
                               lenguas=LENGUAS_GLITCH)
print("guardado:", guardar_gcode(a_gcode(pasos, p), nombre), f"({len(pasos)} pasos)")
