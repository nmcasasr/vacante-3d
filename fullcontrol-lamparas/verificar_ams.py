"""
Compara el cambio de filamento que genera `colores.cambio_ams()` contra el que
emite Bambu Studio de verdad.

Esto es lo que hace que el bloque esté *verificado* y no adivinado, así que
conviene volver a correrlo cada vez que se lo toque, y sobre todo cuando
aparezca una versión nueva de Bambu Studio:

    python verificar_ams.py [ruta/a/un.gcode.3mf]

Por defecto usa `../../gcodes/multi_color_cube.gcode.3mf`, un cubo de dos
colores laminado para una A1 con boquilla de 0.8, cuya plantilla de cambio está
rotulada `;===== A1 20251031 =====`.

Del .3mf se sacan los cuatro bloques de cambio (`; CP TOOLCHANGE START`), se les
quitan comentarios, líneas en blanco y marcadores de progreso `M73`, y se los
compara comando por comando con lo que genera este repo para ESE mismo par de
filamentos.

Las únicas diferencias esperadas son dos, y las dos son a propósito:

  * `M9833 F...` — el caudal de referencia para la compensación dinámica de
    extrusión. El slicer pone el de su perfil; nosotros el de la pieza que
    estamos generando de verdad.
  * la cola — el slicer vuelve a la pieza con un movimiento que le sale del
    siguiente objeto a imprimir; nosotros tenemos que armarlo (ver `cambio_ams`).

Si aparece cualquier otra, el bloque dejó de estar calcado.
"""

import json
import re
import sys
import zipfile
from difflib import unified_diff
from pathlib import Path

import fullcontrol as fc

from lamparas.colores import Filamento, cambio_ams
from lamparas.comun import Perfil

REFERENCIA = Path(__file__).resolve().parent.parent.parent / "gcodes" / "multi_color_cube.gcode.3mf"

# Las diferencias que sí esperamos. Todo lo demás es una regresión.
ESPERADAS = ("M9833",)


def _normalizar(lineas):
    """Sin comentarios, sin líneas en blanco y sin marcadores de progreso."""
    salida = []
    for linea in lineas:
        limpia = linea.split(";")[0].strip()
        if not limpia or limpia.startswith("M73"):
            continue
        salida.append(re.sub(r"\s+", " ", limpia))
    return salida


def _filamentos(cfg, primera_capa=False):
    """
    Reconstruye un `Filamento` por slot a partir del project_settings.config.

    `M104 S[old_filament_temp]` y `M109 S[new_filament_temp]` son la
    temperatura DE ESA CAPA: en la primera, `nozzle_temperature_initial_layer`;
    en el resto, `nozzle_temperature`. En este .3mf son 250 y 245 para el PETG,
    así que confundirlas hace fallar 63 de los 64 bloques.
    """
    tipos = cfg["filament_type"]
    clave_temp = "nozzle_temperature_initial_layer" if primera_capa else "nozzle_temperature"
    return [
        Filamento(
            slot=i + 1,
            tipo=tipos[i],
            temp=int(cfg[clave_temp][i]),
            temp_flush=int(cfg["nozzle_temperature_range_high"][i]),
            vel_volumetrica=float(cfg["filament_max_volumetric_speed"][i]),
            corte=(
                float(cfg["filament_retraction_distances_when_cut"][i])
                if cfg["filament_long_retractions_when_cut"][i] == "1"
                else 0.0
            ),
        )
        for i in range(len(tipos))
    ]


def _bloques_reales(gcode):
    """Los cambios de filamento del .3mf, de `M1007 S0` hasta `M1007 S1`."""
    lineas = gcode.split("\n")
    bloques, dentro = [], None
    for i, linea in enumerate(lineas):
        if linea.startswith("M1007 S0"):
            dentro = i
        elif linea.startswith("M1007 S1") and dentro is not None:
            bloques.append(lineas[dentro : i + 1])
            dentro = None
    return bloques


def auditar_purga(lineas, etiqueta=""):
    """
    Contabiliza el filamento que mueve un bloque de cambio, para poder afirmar
    que NO purga.

    Lo que tiene que hacer un cambio sin purga es: cortar, sacar el filamento
    viejo, meter el nuevo. Nada más. Los dos únicos empujes positivos que
    quedan son parte de meterlo:

      * `G1 E18` devuelve la retracción larga del corte (`M620.11 ... E-18`).
        Rellena la zona de fusión que el corte dejó vacía: es la CARGA, no una
        purga. Neto contra la retracción: ~0.
      * `G1 E6` compensa lo que goteó mientras la boquilla esperaba la
        temperatura nueva. Lo dice el comentario del propio slicer.

    Una purga de verdad se ve distinta: `L` distinto de 0 en `M620.10 A1`, un
    bloque `; FLUSH_START`, o decenas de mm de `G1 E` seguidos.

    Returns:
        (mm netos de G1 E, hay_bloque_flush, valor de L en la carga)
    """
    neto, flush, carga_l = 0.0, False, None
    for linea in lineas:
        code = linea.split(";")[0].strip()
        if "FLUSH_START" in linea:
            flush = True
        m = re.match(r"^G1\b(?!.*\b[XYZ])\s+E(-?[\d.]+)", code)
        if m:
            neto += float(m.group(1))
        elif code.startswith("M620.10") and " A1" in code:
            l = re.search(r"\bL([\d.]+)", code)
            carga_l = float(l.group(1)) if l else None
    return neto, flush, carga_l


def main(ruta=REFERENCIA) -> int:
    ruta = Path(ruta)
    if not ruta.exists():
        print(f"No encuentro la referencia: {ruta}")
        print("Pasá la ruta de un .gcode.3mf multicolor laminado por tu Bambu Studio.")
        return 2

    with zipfile.ZipFile(ruta) as z:
        gcode = z.read("Metadata/plate_1.gcode").decode("utf8", "replace")
        cfg = json.loads(z.read("Metadata/project_settings.config"))

    boquilla = float(cfg["nozzle_diameter"][0])
    altura_primera_capa = float(cfg["initial_layer_print_height"])
    aceleraciones = (int(cfg["initial_layer_acceleration"][0]), int(cfg["default_acceleration"][0]))
    perfil = Perfil(diametro_boquilla=boquilla, altura_capa=float(cfg["layer_height"]))
    bloques = _bloques_reales(gcode)
    print(f"{ruta.name}: {len(bloques)} cambio(s) de filamento, boquilla {boquilla} mm.")

    fallos = 0
    for n, real in enumerate(bloques, 1):
        # De qué slot a qué slot: `M620 S{n}A` abre y `M620.11 ... I{p}` dice
        # cuál sale. Sin corte largo hay que deducirlo del cambio anterior.
        m_nuevo = re.search(r"^M620 S(\d+)A", "\n".join(real), re.M)
        m_viejo = re.search(r"^M620\.11 S1 I(\d+) E-", "\n".join(real), re.M)
        if not (m_nuevo and m_viejo):
            print(f"  cambio #{n}: no pude leer los slots, lo salteo.")
            continue
        nuevo = _filamentos(cfg)[int(m_nuevo.group(1))]
        viejo = _filamentos(cfg)[int(m_viejo.group(1))]

        # La Z del bloque: el slicer sube a max_layer_z + 3.
        z_alto = float(re.search(r"^G1 Z([\d.]+) F1200", "\n".join(real), re.M).group(1))
        z = round(z_alto - 3.0, 3)
        punto = fc.Point(x=0.0, y=0.0, z=z)

        # temperaturas y aceleración dependen de si el cambio cae en la primera capa
        primera = z <= altura_primera_capa + 0.001
        filamentos = _filamentos(cfg, primera_capa=primera)
        nuevo = filamentos[nuevo.slot - 1]
        viejo = filamentos[viejo.slot - 1]
        generado = cambio_ams(
            nuevo, viejo, perfil=perfil, aceleracion=aceleraciones[0 if primera else 1]
        )(punto).split("\n")
        esperado = _normalizar(real)
        nuestro = _normalizar(generado)
        # nuestro bloque agrega la retracción de entrada y la vuelta a la pieza
        nuestro = nuestro[1 : nuestro.index("M1007 S1") + 1]

        diff = [
            l
            for l in unified_diff(esperado, nuestro, lineterm="", n=0)
            if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))
        ]
        inesperadas = [l for l in diff if not any(e in l for e in ESPERADAS)]
        estado = "OK" if not inesperadas else "DIFERENCIAS"
        print(
            f"  cambio #{n}: A{viejo.slot} ({viejo.tipo}) -> A{nuevo.slot} ({nuevo.tipo}), "
            f"{len(esperado)} comandos ... {estado}"
        )
        for l in inesperadas:
            print(f"      {l}")
        fallos += bool(inesperadas)

        # Que no purgue no es algo que el diff garantice: si el .3mf de
        # referencia se hubiera laminado CON purga, el diff seguiría dando OK y
        # estaríamos copiando una purga. Se chequea aparte, contra el generado.
        neto_r, flush_r, l_r = auditar_purga(real)
        neto_g, flush_g, l_g = auditar_purga(generado)
        problemas = []
        if flush_g:
            problemas.append("el bloque generado trae un ; FLUSH_START")
        if l_g:
            problemas.append(f"la carga lleva purga L={l_g:g}")
        if abs(neto_g - neto_r) > 0.01:
            problemas.append(f"empuja {neto_g:+.2f} mm contra los {neto_r:+.2f} mm del real")
        if problemas:
            print(f"      PURGA: {'; '.join(problemas)}")
            fallos += 1
        elif n == 1:
            print(
                f"      sin purga: L={l_g if l_g is not None else 0:g}, sin bloque FLUSH, "
                f"{neto_g:+.2f} mm netos de G1 E (los mismos que el real).\n"
                f"      Esos {neto_g:+.0f} mm son la carga: +18 devuelve la retracción del "
                f"corte y +6 compensa el goteo; -4 son retracciones."
            )

    print("\nTodo calcado." if not fallos else f"\n{fallos} bloque(s) con diferencias inesperadas.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
