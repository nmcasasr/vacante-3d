"""Diseños paramétricos de lámparas para impresión 3D con FullControl."""

from .comun import Perfil, a_gcode, generar_lampara, guardar_gcode, previsualizar

__all__ = ["Perfil", "generar_lampara", "a_gcode", "guardar_gcode", "previsualizar"]
