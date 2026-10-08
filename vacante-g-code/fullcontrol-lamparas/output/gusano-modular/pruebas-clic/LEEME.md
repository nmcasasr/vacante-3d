# Pruebas del clic: Gusi Ø95

Piezas cortas para probar cómo encastran los módulos, en minutos en vez de una
hora por módulo. Son tramos exactos del módulo Ø95: la boca de abajo y el
hombro con el labio de arriba. Comparé el labio de la prueba contra el módulo
completo: la bolita queda a la misma altura sobre el anillo de la boca, con
menos de 0.1 mm de diferencia.

## Las piezas

| pieza | qué es | tiempo* |
|---|---|---|
| `prueba_boca_D95` | las primeras 4 vueltas del módulo, sin piso: la boca tal cual | ~6 min |
| `prueba_boca_D95_adentro1` | la misma boca con dos protuberancias de 1 mm hacia adentro en las primeras vueltas (la idea de la boca) | ~6 min |
| `prueba_labio_D95` | hombro + labio liso, con piso para que se pare: el de siempre | ~18 min |
| `prueba_labio_D95_clic0.8` | ídem con las dos bolitas, sale 0.7 mm | ~18 min |
| `prueba_labio_D95_clic1.1` | sale 1.05 mm | ~18 min |
| `prueba_labio_D95_clic1.4` | sale 1.4 mm | ~18 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

Las bolitas van enfrentadas: una en +X de la cama y otra en −X. Miden ~6 mm
de ancho y ~3 mm de alto y arrancan justo encima de donde termina el anillo de
la boca.

## Cómo probar

Encajar cada boca en cada labio. Lo que importa:

- **boca lisa + labio liso** es la referencia: el encastre de hoy.
- **boca lisa + labio con clic** es la propuesta. Hay juego de 0.6 mm por lado
  entre boca y labio, así que cada bolita traba lo que sobresale por encima
  de eso:

  | bolita | traba por lado |
  |---|---|
  | 0.8 | ~0.1 mm: casi nada, roce |
  | 1.1 | ~0.45 mm |
  | 1.4 | ~0.8 mm: firme, puede costar sacarlo |

  La primera capa sale aplastada y se mete un poco hacia adentro, así que en
  la pieza real traba algo más que el número.
- **boca adentro + labio liso** es la otra idea, para comparar. Según la
  geometría, esas protuberancias caen contra el hombro curvo y no contra el
  labio: el módulo debería quedar levantado sobre ellas, sin clic. La prueba
  lo confirma o lo desmiente.

Hay que mirar si hace clic, si se sostiene al levantarlo de arriba, si sale
con un tirón razonable, y si las bolitas se imprimieron limpias (sin hilos ni
colgados debajo).

## Lo que no se puede

- **Una bolita más petisa:** el radio no puede crecer más de ~0.6 mm por
  vuelta, porque cada vuelta sube 0.8 y si se corre más ya no apoya en la de
  abajo. Con 1.1 mm de bolita eso da dos vueltas de subida y dos de bajada.
- **Sin juego vertical:** entre el tope del anillo y la altura donde la bolita
  ya agarra quedan ~0.9 mm. El módulo puede subir eso antes de trabar.

## Generar de nuevo

    python gen_gusano_modular.py 95 --prueba --clic 0.8 1.1 1.4 --boca-adentro 1.0

Y el módulo entero con el clic que gane:

    python gen_gusano_modular.py 95 --solo-modulos --clic 1.1
