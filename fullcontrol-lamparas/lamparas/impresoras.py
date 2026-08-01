"""
Start/end gcode de impresora.

FullControl solo genera los movimientos de la pieza: no sabe hacer homing, ni
nivelar la cama, ni purgar. Este módulo aporta esa parte para la Bambu Lab A1.

IMPORTANTE: la secuencia de acá NO es el start gcode de fábrica de Bambu
Studio. Es una secuencia mínima, escrita a mano, con comandos estándar. Es
suficiente para imprimir, pero si querés la rutina completa de Bambu (AMS,
calibración de flujo, compensación de vibraciones) exportala desde Bambu Studio
y pasala con `Perfil(start_gcode=cargar_gcode("mi_start.gcode"))` o con
`--start-gcode mi_start.gcode` desde la línea de comandos.
"""

import math
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # evita import circular en runtime
    from .comun import Perfil


def _e_para_linea(largo: float, perfil: "Perfil") -> float:
    """mm de filamento necesarios para una línea de `largo` mm con la sección actual."""
    area_filamento = math.pi * (perfil.diametro_filamento / 2) ** 2
    volumen = largo * perfil.diametro_boquilla * perfil.altura_capa
    return volumen / area_filamento


def start_a1(perfil: "Perfil") -> str:
    """
    Secuencia de arranque para la Bambu Lab A1.

    Hace: calentar -> homing -> (nivelación) -> dos líneas de purga en el borde
    frontal de la cama -> retracción corta y salto de Z para no arrastrar.
    """
    largo_purga = 180.0
    e_purga = round(_e_para_linea(largo_purga, perfil), 3)
    z1 = perfil.altura_capa
    nivelacion = "G29 ; nivelación automática de cama" if perfil.nivelar else "; (nivelación desactivada: perfil.nivelar = False)"

    return f"""
;===== START GCODE - Bambu Lab A1 =============================
; OJO: secuencia mínima escrita a mano, NO es la de Bambu Studio.
; Si algo no te cierra, reemplazá este bloque por el Machine start
; G-code que exporta Bambu Studio para tu A1.
G90 ; coordenadas absolutas
M83 ; extrusión relativa
M104 S{perfil.temp_boquilla} ; empezar a calentar la boquilla
M140 S{perfil.temp_cama} ; empezar a calentar la cama
M190 S{perfil.temp_cama} ; esperar temperatura de cama
M109 S{perfil.temp_boquilla} ; esperar temperatura de boquilla
G28 ; homing de todos los ejes
{nivelacion}
G92 E0
; --- líneas de purga en el borde frontal de la cama ---
G1 Z{z1} F1200
G1 X20 Y5 F6000
G1 X{20 + largo_purga} Y5 E{e_purga} F1000 ; primera línea de purga
G1 Y5.8 F6000
G1 X20 Y5.8 E{e_purga} F1000 ; segunda línea de purga
G1 E-0.4 F2100 ; retracción corta
G1 Z{round(z1 + 2, 2)} F1200 ; levantar para no arrastrar
G92 E0
M106 S{round(perfil.ventilador * 255 / 100)} ; ventilador de capa
;===== FIN DEL START GCODE ====================================
""".strip()


def end_a1(perfil: "Perfil") -> str:
    """Secuencia de cierre: retraer, alejar la boquilla, apagar todo."""
    cx, cy = perfil.centro
    return f"""
;===== END GCODE - Bambu Lab A1 ===============================
M400 ; esperar a que terminen los movimientos pendientes
G91 ; coordenadas relativas
G1 E-2 F2100 ; retraer
G1 Z20 F1200 ; separar la boquilla de la pieza
G90 ; coordenadas absolutas
G1 X{cx} Y{perfil.tamano_cama[1] - 6} F6000 ; adelantar la cama para sacar la pieza
M104 S0 ; apagar boquilla
M140 S0 ; apagar cama
M106 S0 ; apagar ventilador
M84 ; desactivar motores
;===== FIN DEL END GCODE ======================================
""".strip()


def cargar_gcode(ruta) -> str:
    """
    Lee un bloque de gcode desde un archivo.

    Sirve para usar el start/end gcode real exportado desde Bambu Studio
    (Ajustes de impresora -> Machine G-code -> Machine start/end G-code).
    """
    return Path(ruta).read_text().strip()
