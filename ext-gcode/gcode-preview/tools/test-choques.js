#!/usr/bin/env node
// Casos con la respuesta sabida de antemano para `revisarChoques`.
//
// Existe por la misma razón que `test_verificar.py` del generador: un medidor
// roto da veredictos enteros equivocados y no se nota mirando un archivo de
// 200 000 líneas. La primera versión de este chequeo, en Python, tuvo CINCO
// bugs —no leía G91, contaba la cama como material, el signo de la holgura al
// revés, medía el raspado de la línea de purga de la máquina, y contaba la
// retracción final parada en el sitio— y los cinco daban números que parecían
// razonables.
//
//   node tools/test-choques.js

const { revisarChoques } = require('../out/bambu.js');

let fallando = 0;

function caso(nombre, lineas, esperado) {
  const { choques, holgura } = revisarChoques(lineas);
  const hubo = choques.length > 0;
  const ok = hubo === esperado.choca &&
    (esperado.holgura === undefined ||
     Math.abs((holgura.cola === Infinity ? -1 : holgura.cola) - esperado.holgura) < 0.06);
  if (!ok) {
    fallando++;
    console.log(`  FALLA  ${nombre}`);
    console.log(`         esperaba choca=${esperado.choca}` +
      (esperado.holgura !== undefined ? ` holgura=${esperado.holgura}` : '') +
      `, dio choca=${hubo} holgura=${holgura.cola === Infinity ? 'n/a' : holgura.cola.toFixed(2)}`);
    if (hubo) console.log(`         ${choques[0].texto}  (${choques[0].dentro.toFixed(2)} mm dentro)`);
  } else {
    console.log(`  ok     ${nombre}`);
  }
}

// Una pared de 10 mm de alto en X100..110, y después algo en la cola.
// Se cuenta en enteros: sumando 0.4 en coma flotante la pared terminaba en
// 9.6 y no en 10, y las holguras esperadas salían todas 0.4 corridas.
const CAPAS = 25, PASO_Z = 0.4;
const TECHO = CAPAS * PASO_Z;            // 10.00 exacto
const pared = ['; CHANGE_LAYER', 'G90', 'M83'];
for (let i = 1; i <= CAPAS; i++) {
  const z = (i * PASO_Z).toFixed(2);
  pared.push(`G1 X100 Y100 Z${z} E0.5`);
  pared.push(`G1 X110 Y100 Z${z} E0.5`);
}
const cola = ['; ---- gcode-preview: end of grafted body ----'];

caso('la cola pasa POR ENCIMA de la pieza',
  [...pared, ...cola, 'G1 Z15 F900', 'G1 X0 Y100 F18000'],
  { choca: false, holgura: 5.0 });

caso('la cola baja DENTRO de la pieza y la cruza',
  [...pared, ...cola, 'G1 Z2 F900', 'G1 X0 Y100 F18000'],
  { choca: true });

caso('la cola baja pero se queda quieta (retracción)',
  [...pared, ...cola, 'G1 E-0.8 F1800'],
  { choca: false });

caso('rasante: 0.2 mm sobre la pieza, no choca pero avisa',
  [...pared, ...cola, 'G1 Z10.2 F900', 'G1 X0 Y100 F18000'],
  { choca: false, holgura: 0.2 });

caso('G91: una Z relativa NO es una altura absoluta',
  [...pared, ...cola, 'G1 Z15 F900', 'G91', 'G1 Z-1', 'G90', 'G1 X0 Y100 F18000'],
  { choca: false });

caso('la cama vacía no es material: Z negativa fuera de la pieza',
  [...pared, ...cola, 'G1 Z15 F900', 'G1 X0 Y200 F18000', 'G1 Z-5 F1200'],
  { choca: false });

caso('sin pieza no hay nada contra qué chocar',
  ['; CHANGE_LAYER', 'G90', 'M83', ...cola, 'G1 Z-5 F1200', 'G1 X0 Y100 F18000'],
  { choca: false });

console.log(`\n7 casos · ${fallando} fallando`);
process.exit(fallando ? 1 : 0);
