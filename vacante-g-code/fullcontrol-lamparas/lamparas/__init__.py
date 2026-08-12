"""Diseños paramétricos de lámparas para impresión 3D con FullControl."""

from .comun import Perfil, a_gcode, generar_lampara, guardar_gcode
from .impresoras import cargar_gcode
from .preview import guardar_html, previsualizar

__all__ = [
    "Perfil",
    "generar_lampara",
    "a_gcode",
    "guardar_gcode",
    "cargar_gcode",
    "guardar_html",
    "previsualizar",
]
