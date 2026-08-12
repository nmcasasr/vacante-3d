"""La forma de glitch2, generada con pasadas planas en vez de espiral apretada.

Los parámetros del campo de deformación son EXACTAMENTE los de glitch2.gcode,
sacados de output/glitch2.params.json: es la misma pantalla, con otra forma de
recorrerla.
"""
import sys, math
sys.path.insert(0, '.')
from lamparas.comun import Perfil, a_gcode, guardar_gcode
from lamparas.recorrido import pasos_pantalla_glitch
from lamparas.estructura import glitch3

nombre = "glitch/" + (sys.argv[1] if len(sys.argv) > 1 else "glitch6")
solape = float(sys.argv[2]) if len(sys.argv) > 2 else 0.92

p = Perfil(diametro_boquilla=0.8, altura_capa=0.4, ancho_linea=1.8,
           velocidad_impresion=1200, temp_boquilla=245, temp_cama=80, ventilador=0)
g = glitch3(salto=38, sectores=7, bloques=4, rampa=0.18, desvio=14,
            centro=0.5, alto=0.42, solo_afuera=(len(sys.argv) > 3))
deform = lambda a, t: g(a, t) + 2.2 * (2 * abs(((44 * a / (2 * math.pi)) % 1) - 0.5))
pasos = pasos_pantalla_glitch(p, altura=140, silueta=lambda t: 95 - 40 * t,
                              deformacion=deform, segmentos=400, solape=solape)
print("guardado:", guardar_gcode(a_gcode(pasos, p), nombre), f"({len(pasos)} pasos)")
