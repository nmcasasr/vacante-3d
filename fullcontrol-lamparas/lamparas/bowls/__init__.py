"""
Bowls con patrones tejidos, generados por gcode.

Los cuatro diseños comparten toda la infraestructura (silueta, base sólida,
modo vaso, exportación) y se diferencian solo en el patrón:

- `cesta`   -> trenzado de cestería, tejas horizontales alternadas
- `malla`   -> malla fina de rombos
- `celosia` -> calado real, con agujeros pasantes
- `tramado` -> entramado diagonal, una tira pasa por encima de la otra

Ninguno de los cuatro se puede hacer con un slicer: los tres primeros porque el
patrón cambia dentro de cada vuelta y de una vuelta a la otra, y la celosía
porque además mueve la Z dentro de la capa.
"""

from typing import Optional

from ..comun import Perfil, a_gcode, generar_pieza, guardar_gcode
from . import celosia, cesta, malla, siluetas, tramado
from .siluetas import SILUETAS

DISENOS = {
    "cesta": cesta,
    "malla": malla,
    "celosia": celosia,
    "tramado": tramado,
}


def pasos_bowl(
    diseno: str = "cesta",
    silueta: str = "bol",
    altura: float = 60.0,
    perfil: Optional[Perfil] = None,
    parametros: Optional[dict] = None,
    parametros_silueta: Optional[dict] = None,
    segmentos_por_capa: Optional[int] = None,
    base_solida: bool = True,
    capas_transicion: int = 6,
) -> list:
    """
    Arma los pasos de FullControl de un bowl.

    Args:
        diseno: uno de `DISENOS` ('cesta', 'malla', 'celosia', 'tramado').
        silueta: una de `SILUETAS` ('bol', 'copa', 'platillo', 'campana').
        altura: altura de la pared en mm (sin contar el espesor de la base).
        perfil: parámetros de impresión.
        parametros: kwargs propios del patrón (ver el `construir()` de cada uno).
        parametros_silueta: kwargs de la silueta (radio_base, radio_boca, ...).
        segmentos_por_capa: si es None se usa el que recomienda el patrón, que
            sale de su cantidad de lóbulos.
        base_solida: rellena el fondo. False deja el bowl abierto abajo.
        capas_transicion: capas en las que el patrón nace desde un círculo liso.
    """
    if diseno not in DISENOS:
        raise ValueError(f"diseño desconocido: {diseno!r}. Opciones: {sorted(DISENOS)}")
    if silueta not in SILUETAS:
        raise ValueError(f"silueta desconocida: {silueta!r}. Opciones: {sorted(SILUETAS)}")

    fn_silueta = SILUETAS[silueta](**(parametros_silueta or {}))
    fn_radio, fn_dz, segmentos, paso_z = DISENOS[diseno].construir(
        fn_silueta, altura=altura, **(parametros or {})
    )

    return generar_pieza(
        fn_radio,
        altura=altura,
        perfil=perfil,
        segmentos_por_capa=segmentos_por_capa or segmentos,
        funcion_dz=fn_dz,
        base_solida=base_solida,
        capas_transicion=capas_transicion,
        paso_z=paso_z,
        # el voladizo se mide sobre la silueta lisa: el relieve del patrón hace
        # oscilar el radio medio y daría falsas alarmas
        silueta_referencia=fn_silueta,
    )


def generar_bowl(nombre: Optional[str] = None, guardar: bool = True, **kwargs) -> str:
    """
    Genera el gcode de un bowl y lo deja en `output/`.

    Acepta los mismos argumentos que `pasos_bowl()`. Devuelve el gcode.
    """
    perfil = kwargs.get("perfil")
    pasos = pasos_bowl(**kwargs)
    gcode = a_gcode(pasos, perfil)
    if guardar:
        nombre = nombre or f"bowl_{kwargs.get('diseno', 'cesta')}"
        ruta = guardar_gcode(gcode, nombre)
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas)")
    return gcode


__all__ = ["DISENOS", "SILUETAS", "pasos_bowl", "generar_bowl", "siluetas"]
