# El turupe en ROMBO en vez de en cuña

El grumo sube hasta la mitad de la banda y VUELVE A BAJAR, en vez de crecer
hasta el final y cortar. De perfil, cada tira pasa de cuña a rombo.

```
--p crecer_pico=0.5      el maximo cae a la mitad de la banda
--p crecer_pico=1.0      como estaba (por defecto, no mueve nada)
```

Es una sola funcion: `crecida()` en `bowls/puas.py`. `crecer_pico` dice en que
punto de la banda cae el maximo, y con 1.0 devuelve la rampa de siempre.

Medido en la pua 5, vuelta a vuelta:

```
cuña    0  0  0.33 0.67 1.00 1.33 1.67 2.00 2.33 2.67 3.00 | corta
rombo   0  0  0.60 1.20 1.80 2.40 3.00 2.40 1.80 1.20 0.60 | corta
```

## Lo que cuesta

El vuelo entero se alcanza en la MITAD de las vueltas, asi que **el salto radial
por vuelta se duplica**. Ese es el numero que decide si se imprime.

La bajada no cuesta nada: correrse hacia ADENTRO apoya sobre lo de afuera de la
vuelta de abajo. De hecho el contacto MEJORA (0.61 % -> 0.02 % en el cupon),
porque la cuña termina en un voladizo y el rombo no.

```
cupon Ø50, 9 vueltas, vuelo 3.0     cuña   59 % de solape
                                    rombo  49 %
con 18 vueltas en vez de 9          rombo  61 %
con vuelo 1.8 en vez de 3.0         rombo  69 %

matera (prueba3), 9 vueltas         cuña   72 % de solape · logo 324/324
matera rombo, vuelo 3.0             rombo  50 % · logo 324/324 · IMPRIMIBLE
matera rombo, vuelo 2.4             rombo  60 % · logo 324/324 · IMPRIMIBLE
```

**Subir `con_patron` a 18 no sirve en la matera**: la banda pasa de 4.4 a 8.0 mm
y el logo, que son 9 filas, pasaria a medir 72 mm en una pieza de 50.

## Ojo al verificar

El pico de la banda YA NO es la ultima vuelta, es la del medio. Un verificador
que lea la ultima vuelta da 212/324 y parece que el logo se rompio; leyendo la
del medio da 324/324. Pasó en la primera medicion.
