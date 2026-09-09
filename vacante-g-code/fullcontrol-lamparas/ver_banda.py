#!/usr/bin/env python3
"""
La banda de una rosca, reconstruida del G-CODE EMITIDO y a alta resolución.

Desenrollar por (ángulo, z) desperdicia casi todo: en 12 mm de alto y 55° de
arco el recorrido pasa 40 veces y cada pasada llena UNA fila de píxeles. Pero el
patrón no es función de (ángulo, z) sino de (ángulo, FASE DEL HILO), y en esa
grilla cada vuelta cae en una fila distinta: 45 vueltas llenan la banda entera.

La figura depende además de `fila`, así que se pliega una sola pasada de banda
—las vueltas que comparten `fila`—, no la pieza entera: si no, se superponen
cuatro figuras distintas en la misma celda.

    python ver_banda.py output/rosca/final/cupon_40mm/macho_pastillas_v1329.gcode salida.png 0 45

Deja dos PNG: el sombreado (cómo se va a ver) y `_altura` (gris = radio). Para
juzgar DÓNDE está y CUÁNTO mide una figura hay que mirar el de altura: en el
sombreado la luz viene de un lado y el lado oscuro parece vacío.
"""
import math, sys
import numpy as np
from PIL import Image

PASO, D_CRESTA = 13.5, 8.75

def leer(ruta):
    x=y=z=0.0; pts=[]
    for ln in open(ruta, errors="ignore"):
        c=ln.split(";")[0].strip()
        if not c[:2] in ("G0","G1"): continue
        nx,ny,nz,e=x,y,z,0.0
        for tok in c.split()[1:]:
            k=tok[0].upper()
            try: v=float(tok[1:])
            except ValueError: continue
            if k=="X": nx=v
            elif k=="Y": ny=v
            elif k=="Z": nz=v
            elif k=="E": e=v
        if e>0: pts.append((nx,ny,nz))
        x,y,z=nx,ny,nz
    return np.array(pts)

def banda(ruta, salida, a0=0.0, a1=60.0, px_mm=14, z_min=6.0, escala=2,
          centro=10.425,         # D_CRESTA + centro de la meseta
          impreso=False):
    P = leer(ruta)
    # el centro se saca DESPUÉS de descartar la purga: las líneas del borde de
    # la cama están a 20 mm y corren el centro 50 mm, con lo que el radio medido
    # sale entre 52 y 75 en vez de ~51
    P = P[P[:,2] > z_min]
    cx,cy = (P[:,0].min()+P[:,0].max())/2, (P[:,1].min()+P[:,1].max())/2
    R = np.hypot(P[:,0]-cx, P[:,1]-cy)
    TH = np.degrees(np.arctan2(P[:,1]-cy, P[:,0]-cx)) % 360
    Z  = P[:,2]
    D  = (Z - PASO*np.radians(TH)/(2*math.pi)) % PASO
    # La fila se agrupa EXACTAMENTE como la calcula el patrón: `d` rebasado
    # para que envuelva medio paso más allá del centro de la banda. Agrupar de
    # otra forma superpone figuras distintas en la misma celda y las pastillas
    # salen rayadas.
    V = (D - centro + PASO/2) % PASO - PASO/2
    D_FILA = (D - (centro + PASO/2)) % PASO
    FILA = np.round((Z - D_FILA)/PASO).astype(int)
    # una sola pasada de banda: la `fila` más poblada
    vals, cuenta = np.unique(FILA, return_counts=True)
    f = vals[np.argmax(cuenta)]
    m = (FILA == f) & (TH>=a0) & (TH<=a1)
    R,TH,V = R[m],TH[m],V[m]
    print(f"  fila {f}: {m.sum()} puntos entre {a0:.0f}° y {a1:.0f}°")
    r_med = R.mean()
    ancho_mm = math.radians(a1-a0)*r_med
    # La resolución VERTICAL no se elige: en `d` sólo hay una muestra por
    # vuelta, o sea una cada 0.30 mm. Pedir más píxeles no agrega información,
    # sólo hace que el sombreado se coma las líneas de capa (probado: la banda
    # salía rayada de punta a punta y no se veía ninguna figura).
    # La resolución vertical es UNA MUESTRA POR VUELTA, y esa distancia es el
    # paso de capa de la pieza — que ya no es siempre 0.30. Se mide en vez de
    # suponerse: con el valor equivocado el render no muestra la mejora de
    # bajar el paso, que es justo lo que se quiere ver.
    dv = np.diff(np.sort(np.unique(np.round(V, 3))))
    paso_capa = float(np.median(dv[dv > 0.02])) if (dv > 0.02).any() else 0.30
    W, H = int(ancho_mm*px_mm), max(20, int(PASO/paso_capa))
    g = np.full((H,W), -1e9)
    gi = np.clip(((TH-a0)/(a1-a0)*(W-1)).astype(int),0,W-1)
    gj = np.clip(((PASO/2 - V)/PASO*(H-1)).astype(int),0,H-1)
    np.maximum.at(g,(gj,gi),R)
    g[g<-1e8] = np.nan
    for j in range(H):
        fl=g[j]; idx=np.flatnonzero(~np.isnan(fl))
        if len(idx)>1: g[j]=np.interp(np.arange(W), idx, fl[idx])
    for i in range(W):
        col=g[:,i]; idx=np.flatnonzero(~np.isnan(col))
        if len(idx)>1: g[:,i]=np.interp(np.arange(H), idx, col[idx])
    g=np.nan_to_num(g, nan=np.nanmin(g[~np.isnan(g)]))
    if impreso:
        # Cómo va a salir IMPRESA, no cómo está en el recorrido.
        #
        # El recorrido es una línea sin espesor; el plástico lo pone una
        # boquilla de 0.8 mm que no puede doblar en menos que su propio
        # diámetro. Así que en `u` —la dirección de avance— todo lo que mida
        # menos que la boquilla sale redondeado. En `v` no hace falta filtrar
        # nada: ahí ya hay una sola muestra por vuelta, que es la resolución
        # real de la pieza.
        k = max(1, int(round(0.8*px_mm)))
        nucleo = np.ones(k)/k
        # los bordes se rellenan con el propio valor del borde: con el relleno
        # de ceros de `mode="same"` la pieza se "hunde" en los extremos y el
        # radio da 27 en vez de 49.5
        g = np.apply_along_axis(
            lambda f: np.convolve(np.pad(f, k, mode="edge"), nucleo, mode="same")[k:-k],
            1, g)
    gy,gx=np.gradient(g, PASO/H, 1.0/px_mm)
    n=np.stack([-gx,-gy,np.ones_like(g)],-1); n/=np.linalg.norm(n,axis=-1,keepdims=True)
    luz=np.array([-0.45,0.55,0.70]); luz/=np.linalg.norm(luz)
    img=0.12+0.88*np.clip((n*luz).sum(-1),0,1)**0.85
    # se estira en vertical para que el píxel quede cuadrado en mm
    alto_px = int(PASO*px_mm*escala)
    Image.fromarray((np.clip(img,0,1)*255).astype(np.uint8),"L")\
         .resize((W*escala, alto_px), Image.LANCZOS).save(salida)
    # y el mapa de ALTURAS crudo: el sombreado dice cómo se va a ver, pero para
    # juzgar dónde está y cuánto mide una figura engaña —la luz viene de un lado
    # y el lado oscuro parece vacío—. Acá gris = radio, y nada más.
    alt = (g - g.min()) / max(1e-9, g.max() - g.min())
    Image.fromarray((alt*255).astype(np.uint8),"L")\
         .resize((W*escala, alto_px), Image.NEAREST).save(salida.replace(".png","_altura.png"))
    print(f"  {salida}  {ancho_mm:.1f} x {PASO} mm   radio {g.min():.2f}..{g.max():.2f}")

if __name__=="__main__":
    banda(sys.argv[1], sys.argv[2],
          float(sys.argv[3]) if len(sys.argv)>3 else 0.0,
          float(sys.argv[4]) if len(sys.argv)>4 else 60.0,
          impreso="--impreso" in sys.argv)
