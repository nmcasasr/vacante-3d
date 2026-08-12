"""
Previsualización de un diseño antes de imprimirlo.

Dos opciones:

- `guardar_html(pasos, nombre)`: escribe un HTML autocontenido en `output/` que
  se abre en cualquier navegador. Funciona sin entorno gráfico, así que sirve
  también por SSH o en un contenedor.
- `previsualizar(pasos)`: abre el visor propio de FullControl (simula el ancho
  y alto real de cada línea extruida). Necesita un navegador en la misma
  máquina.
"""

from pathlib import Path
from typing import Optional

import fullcontrol as fc
import plotly.graph_objects as go

from .comun import DIR_OUTPUT, Perfil


def _extraer_puntos(pasos: list):
    """Devuelve (xs, ys, zs) de los pasos que son puntos, arrastrando las coordenadas omitidas."""
    xs, ys, zs = [], [], []
    x = y = z = 0.0
    for paso in pasos:
        if isinstance(paso, fc.Point):
            x = paso.x if paso.x is not None else x
            y = paso.y if paso.y is not None else y
            z = paso.z if paso.z is not None else z
            xs.append(x)
            ys.append(y)
            zs.append(z)
    return xs, ys, zs


def guardar_html(
    pasos: list,
    nombre: str = "preview",
    perfil: Optional[Perfil] = None,
    max_puntos: int = 20000,
    plotly_inline: bool = True,
) -> Path:
    """
    Genera un HTML 3D interactivo (rotar/zoom) del recorrido de la boquilla.

    Args:
        pasos: los pasos del diseño.
        nombre: nombre del archivo, sin extensión, dentro de `output/`.
        perfil: se usa solo para dibujar el contorno de la cama.
        max_puntos: submuestrea el recorrido si tiene más puntos que esto.
            La forma se ve igual y el HTML pesa mucho menos.
        plotly_inline: True embebe plotly.js en el archivo (~4 MB, funciona sin
            internet). False lo toma de un CDN (archivo chico, requiere red).

    Returns:
        La ruta del HTML generado.
    """
    perfil = perfil or Perfil()
    xs, ys, zs = _extraer_puntos(pasos)
    if not xs:
        raise ValueError("El diseño no tiene ningún punto para previsualizar.")

    paso_muestreo = max(1, len(xs) // max_puntos)
    if paso_muestreo > 1:
        # se conserva siempre el último punto para no cortar la lámpara
        xs = xs[::paso_muestreo] + [xs[-1]]
        ys = ys[::paso_muestreo] + [ys[-1]]
        zs = zs[::paso_muestreo] + [zs[-1]]

    figura = go.Figure()
    figura.add_trace(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="lines",
            line=dict(color=zs, colorscale="Turbo", width=3),
            hoverinfo="skip",
            name="recorrido",
        )
    )

    # contorno de la cama, para ver que la pieza entra
    ancho, largo = perfil.tamano_cama
    figura.add_trace(
        go.Scatter3d(
            x=[0, ancho, ancho, 0, 0],
            y=[0, 0, largo, largo, 0],
            z=[0, 0, 0, 0, 0],
            mode="lines",
            line=dict(color="grey", width=2),
            hoverinfo="skip",
            name="cama",
        )
    )

    altura = max(zs)
    figura.update_layout(
        title=f"{nombre} — {altura:.0f} mm de alto, {len(xs)} puntos dibujados",
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
        scene=dict(
            aspectmode="data",  # sin distorsión: 1 mm es 1 mm en los tres ejes
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
        ),
    )

    DIR_OUTPUT.mkdir(parents=True, exist_ok=True)
    ruta = DIR_OUTPUT / f"{nombre}.html"
    figura.write_html(str(ruta), include_plotlyjs=True if plotly_inline else "cdn")
    return ruta


def previsualizar(pasos: list, estilo: str = "line") -> None:
    """
    Abre el visor interactivo de FullControl.

    `estilo='tube'` simula el ancho y alto real de cada línea (mucho más lento
    y pesado); `estilo='line'` dibuja el recorrido como una línea simple.
    """
    fc.transform(
        pasos,
        "plot",
        fc.PlotControls(style=estilo, color_type="z_gradient"),
        show_tips=False,
    )
