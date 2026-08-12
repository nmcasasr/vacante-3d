"""
Cambios de filamento a media pieza: pausa manual o cambio de slot del AMS.

## Las dos formas de hacerlo

- `pausa_manual()`: la impresora para, cambiás el rollo con la mano y reanudás.
  Usa `M400 U1`, que es el comando nativo de pausa de Bambu (M600 no existe en
  estas máquinas). No toca el AMS, no purga nada y no depende de ningún comando
  propietario. Es la opción segura.

- `cambio_ams()`: dispara un cambio de slot del AMS. La secuencia que emite es
  la misma que emite Bambu Studio, extraída de un `.gcode.3mf` laminado de
  verdad (ver abajo).

## De dónde salen los comandos del AMS

Bambu no documenta los comandos del AMS, así que esto NO se puede escribir "de
memoria": se saca del gcode que produce el slicer. El de acá está calcado de
`gcodes/multi_color_cube.gcode.3mf` — un cubo de dos colores laminado por Bambu
Studio 02.06.00.51 para una A1 con boquilla de 0.8 — y de la plantilla
`change_filament_gcode` que ese mismo archivo trae en su cabecera, rotulada
`;===== A1 20251031 =====`.

Los cuatro cambios de filamento de ese archivo se diferencian SOLO en el slot y
en las temperaturas y velocidades del filamento; el resto de la secuencia es
idéntica. O sea que el bloque es una plantilla con huecos, y esos huecos son
exactamente los campos de `Filamento`.

Qué hace cada comando, en orden:

    M1007 S0        apaga la estimación de masa mientras dura el cambio
    G392 S0         cede el control del motor de extrusión al cambiador
    M620 S{n}A      ABRE el cambio hacia el slot n (0..3)
    G1 Z{z+3}       levanta la boquilla 3 mm sobre lo impreso
    M106 P1/P2 S0   apaga ventilador de capa y auxiliar
    M104 S{vieja}   mantiene la temperatura del filamento QUE SALE
    G1 X267         lleva el cabezal al cortador, a la derecha, fuera de la cama
    M620.11 S1 I{p} E-18    retracción larga del filamento viejo, ya cortado
    M620.1 / M620.10 A0     descarga (A0 = unload) a la velocidad del viejo
    T{n}            el cambio en sí
    M620.1 / M620.10 A1     carga (A1 = load) con L=purga, H=boquilla
    M620.11 S1 I{p} E+18    devuelve la retracción larga
    M109 S{nueva}   temperatura del filamento NUEVO
    G1 X-38.2/-48.2 limpieza contra el limpiador, a la izquierda de la cama
    M9833           recalibra la compensación dinámica de extrusión
    M621 S{n}A      CIERRA el cambio
    M1007 S1        vuelve a estimar masa

## Por qué acá la purga es 0 por defecto

`M620.10 A1 ... L{purga}` es la longitud de flush. El .3mf de referencia se
laminó con `flush_multiplier = 0` y emite **`L0`**: o sea que la purga en cero
no es un invento nuestro, es algo que el propio Bambu Studio produce y la
máquina acepta.

Y es justo lo que estos diseños quieren: lo que quedaba del color viejo en la
zona de fusión sale mezclado con el nuevo durante las primeras vueltas, y esa
mezcla ES el efecto. Con purga la transición sale limpia y de golpe.

## Cuánto dura la mezcla

El color viejo no desaparece de golpe: hay que empujarlo fuera del bloque
caliente. Los números que reporta la comunidad, en milímetros de filamento
hasta que el color sale limpio:

    blanco -> negro     60-80 mm
    gris   -> azul      ~48 mm
    negro  -> blanco    250-300 mm

Tapar claro con oscuro es rápido; al revés cuesta cuatro veces más. Para saber
cuánta altura de pieza es eso, usá `altura_de_mezcla()`.

## OJO con el .3mf

El gcode que sale de acá se empaqueta en un `.gcode.3mf` con la plantilla de la
extensión `gcode-preview`, y esa plantilla lleva la lista de filamentos del
plato. Un `T2` contra una plantilla de un solo filamento no tiene a qué slot
mapear. La plantilla tiene que ser un export multicolor — el propio
`gcodes/multi_color_cube.gcode.3mf` sirve. Ver `verificar_slots()`.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from .comun import Perfil

# Posiciones de servicio de la A1, sacadas del gcode laminado. Están FUERA de la
# cama: X267 es el cortador (derecha) y X-38.2/-48.2 el limpiador (izquierda).
X_CORTADOR = 267.0
X_LIMPIADOR = (-38.2, -48.2)

# Retracción de cambio de herramienta (`retract_length_toolchange` del perfil).
RETRACCION_CAMBIO = 2.0

# Segundos de máquina por cambio (29 s descarga + 25 s carga del perfil de Bambu).
SEG_POR_CAMBIO = 56

# Velocidad del viaje de vuelta a la pieza, en mm/min. El cambio deja la
# boquilla en el limpiador, a 180-300 mm de la pieza, recién cargada y caliente:
# cuanto menos tiempo pase cruzando por encima, menos gotea sobre lo impreso. Es
# la que usa el slicer para este mismo tramo (F42000 = 700 mm/s). NO es la
# velocidad de impresión ni la de viaje del perfil, que son mucho más bajas.
VIAJE_MAQUINA = 42000

# `M620.1 E F...` y `M620.10 F...` no llevan mm³/s sino mm/min de filamento. La
# constante es la que usa la plantilla de Bambu: F = mm³/s / 2.4053 * 60.
# Comprobado contra el archivo: 21 mm³/s -> F523.843 y 16 mm³/s -> F399.119.
_MM3S_A_F = 60.0 / 2.4053


@dataclass(frozen=True)
class Filamento:
    """
    Un filamento cargado en un slot del AMS.

    Los valores por defecto son los de `Bambu PLA Basic @BBL A1`. Los nombres
    entre paréntesis son la clave equivalente en el `project_settings.config`
    de un .3mf, por si querés sacar los tuyos de ahí en vez de confiar en
    `MATERIALES`.

    Args:
        slot: 1..4, **como los rotula el AMS y como los numera Bambu Studio**.
            En el gcode van con base 0 (`T0`..`T3`); la conversión la hace `t`.
        tipo: nombre del material, solo para los comentarios (`filament_type`).
        temp: temperatura de impresión (`nozzle_temperature`).
        temp_flush: temperatura a la que se hace el cambio, más alta que la de
            impresión para que el material viejo salga fluido
            (`nozzle_temperature_range_high`).
        vel_volumetrica: caudal máximo en mm³/s (`filament_max_volumetric_speed`).
        corte: retracción larga tras el corte, en mm
            (`filament_retraction_distances_when_cut`). 0 desactiva el corte
            largo y emite `M620.11 S0`, que es lo que hace el slicer cuando el
            filamento tiene `filament_long_retractions_when_cut = nil`.
    """

    slot: int
    tipo: str = "PLA"
    temp: int = 220
    temp_flush: int = 240
    vel_volumetrica: float = 21.0
    corte: float = 18.0

    def __post_init__(self):
        if not 1 <= self.slot <= 4:
            raise ValueError(f"slot del AMS fuera de rango: {self.slot} (tiene que ser 1..4)")

    @property
    def t(self) -> int:
        """El índice con base 0 que va en `T`, `M620 S..A` y `M620.11 I..`."""
        return self.slot - 1

    @property
    def f_flush(self) -> float:
        """El caudal en mm/min que esperan `M620.1` y `M620.10`."""
        return round(self.vel_volumetrica * _MM3S_A_F, 3)


# Temperaturas y caudales de los perfiles de filamento de Bambu para la A1 con
# boquilla de 0.8. PLA y PETG salen medidos del project_settings.config de
# `gcodes/multi_color_cube.gcode.3mf`; los otros, del perfil de Bambu Studio.
MATERIALES: Dict[str, dict] = {
    "PLA":  dict(temp=220, temp_flush=240, vel_volumetrica=21.0),
    "PETG": dict(temp=245, temp_flush=270, vel_volumetrica=16.0),
    "ABS":  dict(temp=260, temp_flush=270, vel_volumetrica=18.0),
    "TPU":  dict(temp=235, temp_flush=240, vel_volumetrica=3.6, corte=0.0),
    "PLA-CF": dict(temp=230, temp_flush=250, vel_volumetrica=15.0),
    "PETG-CF": dict(temp=255, temp_flush=270, vel_volumetrica=12.0),
}


def filamento(slot: int, material: str = "PLA") -> Filamento:
    """
    Atajo: `filamento(2, "PETG")` -> el `Filamento` del slot A2 con los valores
    del perfil de Bambu para PETG.

    Si el material no está en `MATERIALES` avisa y usa los de PLA, que es lo
    más conservador (temperatura y caudal bajos).
    """
    clave = material.upper()
    if clave not in MATERIALES:
        print(
            f"AVISO: material desconocido {material!r}; se usan los valores de PLA. "
            f"Conocidos: {', '.join(sorted(MATERIALES))}. Para otro, construí "
            f"Filamento(slot={slot}, temp=..., temp_flush=..., vel_volumetrica=...)."
        )
        clave = "PLA"
    return Filamento(slot=slot, tipo=clave, **MATERIALES[clave])


def pausa_manual(nota: str = "") -> str:
    """
    Bloque que pausa la impresión para cambiar el filamento a mano.

    `M400 U1` es el comando de pausa de Bambu: vacía la cola de movimientos y
    espera a que el usuario reanude desde la pantalla. La impresora aparca el
    cabezal y lo devuelve sola al reanudar, así que no hace falta guardar ni
    restaurar la posición — que es justo lo contrario del cambio por AMS, donde
    la restauración corre por nuestra cuenta.

    No purga nada. Lo que quede del color anterior en la boquilla se va a
    mezclar con el nuevo durante las primeras vueltas.
    """
    comentario = f"; {nota}\n" if nota else ""
    return (
        ";----- CAMBIO DE FILAMENTO (pausa manual) -----\n"
        f"{comentario}"
        "M400 U1 ; pausar y esperar al usuario\n"
        "M83 ; por las dudas: extrusión relativa al reanudar\n"
        ";----- FIN DEL CAMBIO -----"
    )


def _bloque_purga(purga: float, nuevo: Filamento, anterior: Filamento) -> List[str]:
    """
    Purga pulsada, tal como la emite la plantilla cuando `flush_length_1 > 1`.

    Los primeros 23.7 mm salen de corrido y el resto va a tirones (tramos
    largos a caudal pleno alternados con tramos cortos a F50). El tironeo es lo
    que despega el color viejo de la pared del fusor: a caudal constante el
    material nuevo se abre camino por el medio y deja el viejo pegado a los
    costados, y la purga rinde mucho menos.

    Con `purga = 0` esta función no se llama y el bloque queda como el del .3mf
    de referencia, que emite `L0` y no purga nada.
    """
    if purga <= 1:
        return []
    lineas = [
        "; FLUSH_START",
        "M400",
        "M1002 set_filament_type:UNKNOWN",
        f"M109 S{nuevo.temp_flush} ; purgar siempre a la temperatura más alta",
        "M106 P1 S60",
    ]
    if purga > 23.7:
        resto = purga - 23.7
        lineas.append(f"G1 E23.7 F{anterior.f_flush} ; el arranque no necesita tironeo")
        for i in range(4):
            f = anterior.f_flush if i == 0 else nuevo.f_flush
            lineas.append(f"G1 E{resto * 0.02:.4f} F50")
            lineas.append(f"G1 E{resto * 0.23:.4f} F{f}")
    else:
        lineas.append(f"G1 E{purga:.4f} F{anterior.f_flush}")
    lineas += [
        "; FLUSH_END",
        f"G1 E-{RETRACCION_CAMBIO:g} F1800",
        f"G1 E{RETRACCION_CAMBIO:g} F300",
        "M400",
        f"M1002 set_filament_type:{nuevo.tipo}",
    ]
    return lineas


def cambio_ams(
    nuevo: Filamento,
    anterior: Filamento,
    *,
    purga: float = 0.0,
    aceleracion: int = 6000,
    perfil: Optional["Perfil"] = None,
    nota: str = "",
) -> Callable[[object], str]:
    """
    Cambio de slot del AMS, calcado del gcode que emite Bambu Studio.

    Devuelve **una función**, no una cadena: el bloque necesita saber dónde
    quedó la boquilla para poder volver, y eso solo se sabe en el punto de
    inserción. `generar_pieza(cambios=...)` la llama con el último punto
    impreso. Ver `comun._insertar_cambios`.

    La vuelta es la parte que el slicer no nos regala. Cuando termina el
    cambio, el cabezal está en el limpiador (X-48.2, fuera de la cama) y 3 mm
    por encima de la pieza. Si se dejara ahí, el siguiente movimiento de
    FullControl sería una línea EXTRUYENDO desde el limpiador hasta la pieza,
    cruzando la cama entera. Por eso el bloque termina viajando de vuelta al
    último punto —primero en XY estando alto, después bajando la Z— y recién
    ahí ceba.

    Args:
        nuevo: el filamento que entra.
        anterior: el que sale. Hace falta de verdad: su temperatura, su caudal
            y su retracción de corte se usan durante la descarga, antes de que
            el nuevo entre.
        purga: mm de filamento a purgar (`L` de `M620.10 A1`). 0 = sin purga,
            que es lo que emite el .3mf de referencia y lo que estos diseños
            quieren. Ver el docstring del módulo.
        aceleracion: la que queda puesta al salir del cambio, en mm/s²
            (`M204`). El slicer usa `initial_layer_acceleration` (500 en el
            perfil de la A1) si el cambio cae en la primera capa y
            `default_acceleration` (6000) en cualquier otra. Un cambio de color
            a media pieza es siempre el segundo caso, así que 6000 es el que
            corresponde: dejar 500 haría que el resto de la pieza se imprima
            con la aceleración de la primera capa, doce veces más lenta.
        perfil: para restaurar el ventilador y para calcular el caudal de
            referencia de `M9833`. Si es None se usa `Perfil()`.
        nota: comentario que se escribe al principio del bloque.
    """
    from .comun import Perfil

    perfil = perfil or Perfil()
    if nuevo.slot == anterior.slot:
        print(
            f"AVISO: el cambio pide el slot A{nuevo.slot}, que es el que ya está "
            "cargado. El bloque se emite igual, pero no va a cambiar nada."
        )

    ventilador = round(perfil.ventilador * 255 / 100)
    y_medio = round(perfil.tamano_cama[1] / 2, 1)
    # `M9833 F{outer_wall_volumetric_speed/2.4}`: el caudal real de la pared,
    # que en modo vaso es todo lo que se imprime.
    caudal = perfil.ancho * perfil.altura_capa * (perfil.velocidad_impresion / 60.0)

    # `M620.11` activa la retracción larga tras el corte. Con `corte = 0` el
    # slicer emite la variante S0, que la desactiva.
    if anterior.corte > 0:
        corte_saca = f"M620.11 S1 I{anterior.t} E-{anterior.corte:g} F1200"
        corte_mete = (
            f"M620.11 S1 I{anterior.t} E{anterior.corte:g} F{anterior.f_flush}\n"
            "M628 S1\n"
            "G92 E0\n"
            f"G1 E{anterior.corte:g} F{anterior.f_flush}\n"
            "M400\n"
            "M629 S1"
        )
    else:
        corte_saca = "M620.11 S0"
        corte_mete = "M620.11 S0"

    def _limpieza(pasadas: int, sangria: str = "", ultima_lenta: bool = False) -> str:
        """
        Pasadas contra el limpiador, a la izquierda de la cama.

        La cuenta y las velocidades salen del gcode de referencia y NO son las
        mismas en los dos sitios donde aparece: la limpieza principal son
        cuatro pasadas a F18000, y la de después de la calibración son tres,
        con la última a F12000 para sacudir.
        """
        salida = []
        for i in range(pasadas):
            f = 12000 if (ultima_lenta and i == pasadas - 1) else 18000
            salida.append(f"{sangria}G1 X{X_LIMPIADOR[0]} F{f}")
            salida.append(f"{sangria}G1 X{X_LIMPIADOR[1]} F3000")
        return "\n".join(salida)

    limpieza = _limpieza(4)
    limpieza_cali = _limpieza(3, sangria="  ", ultima_lenta=True)
    # Sin purga no hay bloque: la línea desaparece en vez de dejar un hueco.
    purgado = "\n".join(_bloque_purga(purga, nuevo, anterior) + [""])

    def bloque(punto, velocidad: Optional[float] = None) -> str:
        """
        Arma el bloque.

        Args:
            punto: el último `fc.Point` impreso, o sea adonde hay que volver.
            velocidad: la velocidad de impresión vigente en ese momento, en
                mm/min. Hay que reponerla a mano al final: el bloque emite `F`
                para sus propios movimientos (la última es la retracción de
                cebado, a F1800) y FullControl no la vuelve a emitir, porque
                solo lo hace cuando la velocidad CAMBIA y para él nunca cambió.
                Sin esto, todo lo que se imprime después del cambio sale a
                F1800 en vez de a la velocidad pedida, y no se recupera nunca.
        """
        z = punto.z
        # `:g` para que un entero salga `Z5` y no `Z5.0`, como lo escribe el slicer
        z_alto = f"{round(z + 3.0, 3):g}"
        f_impresion = velocidad if velocidad is not None else perfil.velocidad_impresion
        comentario = f"; {nota}\n" if nota else ""
        return f"""
;----- CAMBIO DE FILAMENTO (AMS) ------------------------------
; A{anterior.slot} ({anterior.tipo}) -> A{nuevo.slot} ({nuevo.tipo}), purga {purga:g} mm
; Secuencia calcada de la plantilla "A1 20251031" de Bambu Studio.
; Ver lamparas/colores.py para qué hace cada comando.
{comentario}G1 E-{RETRACCION_CAMBIO:g} F1800 ; retraer antes de irse
M1007 S0 ; apagar la estimación de masa
G392 S0
M620 S{nuevo.t}A ; abrir el cambio hacia el slot A{nuevo.slot}
M204 S9000
G1 Z{z_alto} F1200 ; levantar 3 mm sobre lo impreso
M400
M106 P1 S0 ; ventilador de capa y auxiliar, apagados durante el cambio
M106 P2 S0
M104 S{anterior.temp} ; mantener la temperatura del filamento que SALE
G1 X{X_CORTADOR:g} F18000 ; al cortador, a la derecha de la cama
{corte_saca}
M400
M620.1 E F{anterior.f_flush} T{anterior.temp_flush}
M620.10 A0 F{anterior.f_flush} ; A0 = descargar
T{nuevo.t}
M620.1 E F{nuevo.f_flush} T{nuevo.temp_flush}
M620.10 A1 F{nuevo.f_flush} L{purga:g} H{perfil.diametro_boquilla:g} T{nuevo.temp_flush} ; A1 = cargar
G1 Y{y_medio:g} F9000
{corte_mete}
M400
G92 E0
M628 S0
{purgado}M629
M400
M106 P1 S60
M109 S{nuevo.temp} ; temperatura del filamento NUEVO
G1 E6 F{nuevo.f_flush} ; compensar el goteo mientras esperaba la temperatura
M400
G92 E0
G1 E-{RETRACCION_CAMBIO:g} F1800
M400
M106 P1 S178
M400 S3
{limpieza}
M400
G1 Z{z_alto}
M106 P1 S0
M204 S{aceleracion}
M622.1 S0
M9833 F{caudal / 2.4:.5f} A0.3 ; recalibrar la compensación dinámica de extrusión
M1002 judge_flag filament_need_cali_flag
M622 J1
  G92 E0
  G1 E-{RETRACCION_CAMBIO:g} F1800
  M400
  M106 P1 S178
  M400 S4
{limpieza_cali}
  M400
  M106 P1 S0
M623
M621 S{nuevo.t}A ; cerrar el cambio
G392 S0
M1007 S1
; --- volver a la pieza (esto NO lo da el slicer, ver cambio_ams) ---
M83 ; extrusión relativa, como el resto del cuerpo
M106 S{ventilador} ; restaurar el ventilador de capa
G1 X{punto.x:.3f} Y{punto.y:.3f} F{VIAJE_MAQUINA} ; viajar alto y RÁPIDO, para gotear menos encima
G1 Z{z:.3f} F1200 ; recién ahora bajar
G1 E{RETRACCION_CAMBIO:g} F1800 ; cebar
G1 F{f_impresion:g} ; reponer la velocidad de impresión (si no, sigue a F1800)
;----- FIN DEL CAMBIO -----------------------------------------
""".strip()

    return bloque


def parsear_filamento(spec: str) -> Filamento:
    """
    `"2"` -> slot A2 con PLA. `"2:PETG"` -> slot A2 con PETG.

    Es el formato que usan las CLI. El slot va con base 1, como lo rotula el
    AMS, no con la base 0 del gcode.
    """
    partes = spec.split(":")
    slot = int(partes[0])
    return filamento(slot, partes[1] if len(partes) > 1 and partes[1] else "PLA")


def cambios_desde_specs(
    specs,
    inicial: Filamento,
    purga: float = 0.0,
    perfil: Optional["Perfil"] = None,
) -> Dict[float, Callable]:
    """
    Traduce las especificaciones de la línea de comandos a `{altura: bloque}`.

    Cada spec es `ALTURA:SLOT[:MATERIAL]`, por ejemplo `20:2` o `40:3:PETG`.

    Se ordenan por altura y se encadenan: el filamento "anterior" de cada
    cambio es el que dejó el cambio de más abajo, arrancando por `inicial`. Eso
    importa porque la descarga se hace a la temperatura y al caudal del
    filamento que SALE, no del que entra: descargar PETG a 240 en vez de a 270
    lo deja pegado.

    Args:
        specs: lista de cadenas `ALTURA:SLOT[:MATERIAL]`.
        inicial: el filamento con el que arranca la pieza.
        purga: mm de purga en cada cambio (0 = sin purga).
        perfil: parámetros de impresión, para el ventilador y el caudal.

    Returns:
        `{altura_mm: bloque}` listo para `generar_pieza(cambios=...)`.
    """
    pedidos = []
    for spec in specs:
        partes = spec.split(":", 1)
        if len(partes) < 2:
            raise ValueError(f"se esperaba ALTURA:SLOT[:MATERIAL], llegó {spec!r}")
        pedidos.append((float(partes[0]), parsear_filamento(partes[1])))
    pedidos.sort(key=lambda kv: kv[0])

    cambios: Dict[float, Callable] = {}
    anterior = inicial
    for altura, nuevo in pedidos:
        cambios[altura] = cambio_ams(
            nuevo, anterior, purga=purga, perfil=perfil, nota=f"a {altura:.1f} mm"
        )
        print(
            f"Cambio AMS a {altura:.1f} mm: A{anterior.slot} ({anterior.tipo}) -> "
            f"A{nuevo.slot} ({nuevo.tipo}), o sea T{anterior.t} -> T{nuevo.t} en el gcode."
        )
        anterior = nuevo
    return cambios


def degradado(
    desde: Filamento,
    hasta: Filamento,
    z0: float,
    z1: float,
    pasos: int = 12,
    purga: float = 0.0,
    perfil: Optional["Perfil"] = None,
) -> Dict[float, Callable]:
    """
    Degradado entre dos filamentos, encadenando cambios con proporción variable.

    Este es el único caso donde el sangrado juega a favor. En todo el resto del
    módulo es el problema: el color viejo tarda ~2 vueltas en salir del bloque
    caliente y ensucia lo que venga después. Para un ombré eso es exactamente
    lo que se quiere — la mezcla ES el degradado.

    Cómo funciona: el tramo `z0..z1` se parte en `pasos` franjas. En la franja
    i se imprime una fracción `(i+0.5)/pasos` con el filamento nuevo y el resto
    con el viejo. Abajo casi todo es el viejo, arriba casi todo el nuevo, y el
    sangrado difumina cada salto hasta que no se distingue el escalón.

    Cuesta `2·pasos − 1` cambios, o sea ~56 s cada uno. Con 12 pasos son 23
    cambios, unos 21 minutos de máquina por transición.

    **Un rollo de filamento degradado hace esto mejor y gratis.** En modo vaso
    el color se mapea solo a la altura, porque la pieza es un trazo continuo de
    abajo hacia arriba, y la transición es perfectamente suave en vez de tener
    `pasos` escalones. Esto sirve cuando querés un degradado entre dos colores
    que ya tenés en el AMS.

    Args:
        desde: el filamento con el que arranca el tramo.
        hasta: el filamento con el que termina.
        z0, z1: alturas en mm entre las que ocurre la transición.
        pasos: en cuántas franjas se parte. Más pasos = más suave y más caro.
        purga: mm de purga por cambio. **Dejalo en 0**: purgar acá borra
            justamente la mezcla que produce el degradado.
        perfil: parámetros de impresión.

    Returns:
        `{altura_mm: bloque}` para `generar_pieza(cambios=...)`.
    """
    if z1 <= z0:
        raise ValueError(f"el degradado necesita z1 > z0, llegó {z0}..{z1}")
    if pasos < 1:
        raise ValueError("`pasos` tiene que ser >= 1")
    if purga > 0:
        print(
            "AVISO: degradado con purga > 0. La purga saca justamente la mezcla "
            "que hace el degradado; el resultado van a ser escalones marcados."
        )

    alto = (z1 - z0) / pasos
    # Lista de (altura, filamento que entra), en orden.
    transiciones = []
    for i in range(pasos):
        base = z0 + i * alto
        fraccion = (i + 0.5) / pasos          # cuánto de esta franja va con el nuevo
        if fraccion > 0:
            transiciones.append((base + (1 - fraccion) * alto, hasta))
        if i + 1 < pasos:
            transiciones.append((base + alto, desde))

    cambios: Dict[float, Callable] = {}
    anterior = desde
    for altura, nuevo in transiciones:
        if nuevo.slot == anterior.slot:
            continue
        cambios[altura] = cambio_ams(
            nuevo, anterior, purga=purga, perfil=perfil,
            nota=f"degradado {z0:.0f}->{z1:.0f} mm, a {altura:.1f}",
        )
        anterior = nuevo
    print(
        f"Degradado A{desde.slot} ({desde.tipo}) -> A{hasta.slot} ({hasta.tipo}) "
        f"entre {z0:.0f} y {z1:.0f} mm: {len(cambios)} cambios en {pasos} pasos "
        f"(~{len(cambios)*56/60:.0f} min de máquina)."
    )
    return cambios


def manchas(
    filamentos: List[Filamento],
    z0: float,
    z1: float,
    radio: float,
    min_vueltas: float = 2.0,
    max_vueltas: float = 9.0,
    semilla: int = 0,
    purga: float = 0.0,
    perfil: Optional["Perfil"] = None,
) -> Dict[float, Callable]:
    """
    Cambia de color a intervalos ALEATORIOS, usando el sangrado como mínimo.

    Es la vuelta de tuerca que hace que valga la pena. Pintar una figura cuesta
    dos cambios por capa y por parche, y nunca sale limpia porque el tramo dura
    menos que la transición. Acá se invierte: **el tramo más corto que se emite
    es el que la transición necesita**, así que ningún cambio sale a pérdida, y
    se paga UN cambio por tramo en vez de dos por capa.

    Y como los largos son aleatorios y no múltiplos de una vuelta, los bordes
    no caen siempre en el mismo ángulo: un tramo de 2.5 vueltas deja dos vueltas
    de un lado y tres del otro. Esa asimetría, acumulada a lo largo de decenas
    de tramos, es lo que despega el resultado de un rayado horizontal y lo lleva
    a manchas.

    Lo que NO puede hacer, y conviene saberlo antes: un tramo de una vuelta o
    más da la vuelta entera a la pieza, así que **no hay manchas aisladas**. Lo
    que sale son bandas de alto variable con bordes difuminados y densidad
    despareja alrededor. Para manchas de verdad hay que bajar de una vuelta, y
    ahí el color no llega nunca — es lo que mide `--pintar parches`.

    Args:
        filamentos: dos o más, se van alternando al azar sin repetir.
        z0, z1: entre qué alturas ocurre, en mm.
        radio: radio de la pieza, para convertir vueltas en mm de filamento.
        min_vueltas: largo mínimo de un tramo, en vueltas. Ponelo en lo que
            tarda la transición del par que uses: ~1.4 para dos PLA parecidos,
            ~1.9 para PLA->PETG, ~7 para PETG->PLA. Ver `flush_volumes_matrix`.
        max_vueltas: largo máximo. La diferencia con el mínimo es de dónde sale
            la variedad; con los dos iguales salen bandas parejas.
        semilla: cambiala para otra distribución.
        purga: dejala en 0 — purgar borra el degradado de los bordes.
        perfil: parámetros de impresión.

    Returns:
        `{altura_mm: bloque}` para `generar_pieza(cambios=...)`.
    """
    from .comun import Perfil
    from .estructura import _fases

    perfil = perfil or Perfil()
    if len(filamentos) < 2:
        raise ValueError("`manchas` necesita al menos dos filamentos")
    if z1 <= z0:
        raise ValueError(f"necesita z1 > z0, llegó {z0}..{z1}")

    # Una vuelta sube una altura de capa, así que el largo de un tramo en
    # milímetros de PIEZA es simplemente vueltas x altura_capa. El radio no
    # entra acá — entra en cuánto filamento consume, que es lo que decide la
    # transición y por eso se informa aparte.
    area = math.pi * (perfil.diametro_filamento / 2) ** 2
    mm_por_vuelta = (2 * math.pi * radio) * perfil.area_extrusion / area

    r = _fases(semilla, 4096)
    cambios: Dict[float, Callable] = {}
    actual = filamentos[0]
    z = z0
    while True:
        vueltas = min_vueltas + next(r) * (max_vueltas - min_vueltas)
        z += vueltas * perfil.altura_capa
        if z >= z1:
            break
        otros = [f for f in filamentos if f.slot != actual.slot]
        nuevo = otros[int(next(r) * len(otros)) % len(otros)]
        cambios[z] = cambio_ams(
            nuevo, actual, purga=purga, perfil=perfil,
            nota=f"mancha a {z:.1f} mm ({vueltas:.1f} vueltas)",
        )
        actual = nuevo

    print(
        f"Manchas entre {z0:.0f} y {z1:.0f} mm: {len(cambios)} cambios "
        f"(~{len(cambios)*SEG_POR_CAMBIO/60:.0f} min de máquina). "
        f"Tramos de {min_vueltas:.1f}-{max_vueltas:.1f} vueltas = "
        f"{min_vueltas*mm_por_vuelta:.0f}-{max_vueltas*mm_por_vuelta:.0f} mm de filamento, "
        f"{min_vueltas*perfil.altura_capa:.1f}-{max_vueltas*perfil.altura_capa:.1f} mm de altura."
    )
    return cambios


def verificar_slots(slots, ruta_3mf) -> None:
    """
    Avisa si la plantilla del .3mf no declara todos los slots que usa la pieza.

    El empaquetador de `gcode-preview` copia el `project_settings.config` de la
    plantilla tal cual, y ahí vive la lista de filamentos del plato. Un `T2`
    contra una plantilla de un solo filamento no tiene a qué slot mapear, y
    Bambu Studio no va a ofrecer el mapeo de AMS al abrirlo.

    Args:
        slots: los slots del AMS que usa la pieza, con base 1.
        ruta_3mf: la plantilla que se le va a pasar al empaquetador.
    """
    import json
    import zipfile

    try:
        with zipfile.ZipFile(ruta_3mf) as z:
            cfg = json.loads(z.read("Metadata/project_settings.config"))
    except Exception as e:  # noqa: BLE001 - es un chequeo de cortesía, no un paso obligatorio
        print(f"AVISO: no se pudo leer {ruta_3mf} para verificar los slots ({e}).")
        return

    declarados = len(cfg.get("filament_type", []))
    faltan = sorted(s for s in set(slots) if s > declarados)
    if faltan:
        print(
            f"AVISO: la pieza usa el/los slot(s) A{', A'.join(map(str, faltan))} pero la "
            f"plantilla {ruta_3mf} declara solo {declarados} filamento(s). Usá una "
            "plantilla exportada de Bambu Studio con al menos esa cantidad de "
            "filamentos en el plato."
        )
    else:
        tipos = cfg.get("filament_type", [])
        detalle = ", ".join(f"A{i + 1}={t}" for i, t in enumerate(tipos))
        print(f"Plantilla {ruta_3mf}: {declarados} filamento(s) declarados ({detalle}).")


def quitar_purga(bloque: str, umbral_e: float = 5.0) -> str:
    """
    Saca las líneas de purga de un bloque de cambio de filamento real.

    Ya no hace falta para generar un cambio —`cambio_ams(purga=0)` nace sin
    purga—, pero sigue sirviendo para lo otro: agarrar el bloque de TU Bambu
    Studio (por si tu firmware difiere del de la plantilla de referencia) y
    dejarlo sin purga para compararlo con el de acá.

    Se le quitan los movimientos que extruyen mucho (`G1 E...` por encima de
    `umbral_e` mm) y el `M620.10`, que es el que lleva la longitud de flush.

    **Revisá el resultado antes de usarlo.** La función no entiende el bloque,
    solo filtra por patrón. Imprime lo que sacó para que se pueda auditar.
    """
    import re

    salida, quitadas = [], []
    for linea in bloque.splitlines():
        limpia = linea.split(";")[0].strip()
        es_purga = False
        if limpia.startswith("M620.10"):
            es_purga = True
        else:
            m = re.match(r"^G1\b(?!.*\b[XYZ])(?=.*\bE(-?\d+\.?\d*))", limpia)
            if m and float(m.group(1)) > umbral_e:
                es_purga = True
        (quitadas if es_purga else salida).append(linea)

    if quitadas:
        print(f"quitar_purga(): {len(quitadas)} línea(s) removidas —")
        for l in quitadas:
            print(f"    {l}")
    else:
        print("quitar_purga(): no se encontró ninguna línea de purga que quitar.")
    return "\n".join(salida)


def altura_de_mezcla(mm_filamento: float, radio: float, perfil: Optional["Perfil"] = None) -> float:
    """
    Cuánta altura de pieza sube mientras el color todavía está mezclándose.

    Args:
        mm_filamento: cuánto filamento tarda el color nuevo en salir limpio
            (ver la tabla del módulo).
        radio: radio de la pieza a la altura del cambio, en mm.

    Returns:
        La altura en mm a lo largo de la cual se ve la mezcla.
    """
    from .comun import Perfil

    perfil = perfil or Perfil()
    area_filamento = math.pi * (perfil.diametro_filamento / 2) ** 2
    filamento_por_vuelta = (2 * math.pi * radio) * perfil.area_extrusion / area_filamento
    return (mm_filamento / filamento_por_vuelta) * perfil.altura_capa


def alturas_regulares(desde: float, hasta: float, cantidad: int) -> List[float]:
    """Reparte `cantidad` cambios entre dos alturas, para encadenar un degradado."""
    if cantidad < 1:
        return []
    if cantidad == 1:
        return [(desde + hasta) / 2]
    paso = (hasta - desde) / (cantidad - 1)
    return [desde + i * paso for i in range(cantidad)]
