#!/usr/bin/env node
// Casos con la respuesta sabida para el campo numérico del panel de parámetros.
//
// Existe por lo mismo que `test-choques.js`: la primera versión de `campoNumero`
// parecía andar y tenía un defecto que ninguna lectura del código iba a mostrar.
// Un `input[type=range]` CUANTIZA lo que se le asigna a la grilla de su `step`
// —con min 55.5 y paso 0.592, pedirle 130 lo deja en 130.092—, así que usarlo
// para recuperar el valor vigente devolvía el número pegado a la grilla y no el
// que se había escrito. Es exactamente el redondeo que el campo viene a
// esquivar, y el banco lo cazó en la primera corrida.
//
// Corre en CHROME de verdad, no en un DOM de mentira: lo que se está probando
// es el comportamiento del navegador —la cuantización del range, cuándo dispara
// `change`, qué hace `parseFloat` con una coma—, y un shim escrito por uno
// mismo contesta lo que uno ya supone.
//
// La función se EXTRAE de `media/main.js` tal cual está escrita. Copiarla acá
// sería probar una copia, que es la forma más segura de tener un banco en verde
// y la extensión rota.
//
//   node tools/test-campo.js

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const CHROMES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
];

function chrome() {
  if (process.env.CHROME && fs.existsSync(process.env.CHROME)) return process.env.CHROME;
  return CHROMES.find((p) => fs.existsSync(p)) || null;
}

function fuente() {
  const src = fs.readFileSync(path.join(__dirname, '..', 'media', 'main.js'), 'utf8');
  // Por el PREFIJO, no por la firma entera: agregarle un parámetro a la
  // función no puede romper el banco que la prueba.
  const i = src.indexOf('  function campoNumero(');
  if (i < 0) throw new Error('no encontré campoNumero en media/main.js');
  const j = src.indexOf('\n  }\n', i);
  if (j < 0) throw new Error('no encontré el final de campoNumero');
  return src.slice(i, j + 5);
}

const BANCO = `
const log = [];
const ok = (n, a, b) => log.push((JSON.stringify(a) === JSON.stringify(b) ? 'ok   ' : 'FALLA') + '\\t' + n + '\\t' + JSON.stringify(a) + '\\t' + JSON.stringify(b));
const escribir = (t) => { campo.focus(); campo.value = t; campo.dispatchEvent(new Event('change', { bubbles: true })); };
const tecla = (k) => { campo.focus(); campo.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true })); };

escribir('130');
ok('el valor tipeado no se pega a la grilla del slider', [campo.value, aplicado.at(-1)], ['130', [130, false]]);
ok('el slider si cuantiza: por eso no puede ser la fuente de verdad', slider.value !== '130', true);

escribir('1,5');
ok('coma decimal de teclado latino', [campo.value, aplicado.at(-1)], ['1.5', [1.5, false]]);
ok('fuera de rango por abajo: el slider se ensancha y queda marcado', [slider.min, campo.classList.contains('fuera')], ['1.5', true]);

escribir('300');
ok('fuera de rango por arriba', [slider.max, campo.classList.contains('fuera')], ['300', true]);

escribir('124.4');
ok('de vuelta adentro: se desmarca', [campo.value, campo.classList.contains('fuera')], ['124.4', false]);

const n = aplicado.length;
escribir('perejil');
ok('texto ilegible: revierte al valor exacto y no regenera', [campo.value, aplicado.length], ['124.4', n]);

tecla('ArrowUp');
ok('flecha arriba avanza un paso y pide esperar antes de regenerar', [campo.value, aplicado.at(-1)], ['124.992', [124.992, true]]);
tecla('ArrowDown');
ok('flecha abajo vuelve', [campo.value], ['124.4']);

campo.focus(); campo.value = '9';
tecla('Escape');
ok('Escape restaura el valor exacto, no el de la grilla', [campo.value], ['124.4']);

slider.value = '90'; slider.dispatchEvent(new Event('input', { bubbles: true }));
campo.focus(); campo.value = '7'; tecla('Escape');
ok('despues de arrastrar, Escape vuelve a lo arrastrado', [campo.value], [fmtRef(parseFloat(slider.value))]);

// --- el reset --------------------------------------------------------------
ok('con el valor cambiado, el reset esta a la vista', reset.classList.contains('oculto'), false);
const m = aplicado.length;
reset.click();
ok('el reset vuelve al valor original y lo aplica',
   [campo.value, aplicado.at(-1), aplicado.length], ['124.4', [124.4, false], m + 1]);
ok('ya en el original, el reset se esconde', reset.classList.contains('oculto'), true);

// Ida y vuelta con flechas: 124.4 + 0.592 - 0.592 no da 124.4 exacto en coma
// flotante, y comparar crudo dejaba el boton visible sobre un valor que en
// pantalla es el original.
tecla('ArrowUp'); tecla('ArrowDown');
ok('tras ir y volver con flechas, el reset se esconde igual',
   [campo.value, reset.classList.contains('oculto')], ['124.4', true]);

document.title = 'RESULTADO';
document.getElementById('log').textContent = log.join('\\n');
`;

function pagina() {
  return `<meta charset="utf-8"><body>
<div class="par"><div class="par-fila"><span>demo</span></div></div>
<pre id="log"></pre>
<script>
${fuente()}
const fila = document.querySelector('.par-fila');
const sl = document.createElement('input');
sl.type = 'range'; sl.min = '55.5'; sl.max = '173.9'; sl.step = '0.592'; sl.value = '124.4';
const fmt = (v) => (0.592 >= 1 ? String(Math.round(v)) : v.toFixed(3).replace(/0+$/, '').replace(/\\.$/, ''));
window.fmtRef = fmt;
window.aplicado = [];
const el = campoNumero(sl, fmt, (v, esperar) => window.aplicado.push([v, !!esperar]), 124.4);
el.mostrar(124.4);
fila.appendChild(el.reset);
fila.appendChild(el);
// El mismo puente que arma filaDe: arrastrar pasa por mostrar, no por .value.
sl.addEventListener('input', () => el.mostrar(parseFloat(sl.value)));
window.campo = el; window.slider = sl; window.reset = el.reset;
<\/script>
<script>${BANCO}<\/script></body>`;
}

function main() {
  const bin = chrome();
  if (!bin) {
    console.log('  sin Chrome instalado: banco del campo numérico SALTEADO');
    console.log('  (poné la ruta en $CHROME para correrlo)');
    return 0;
  }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'campo-'));
  const html = path.join(tmp, 'campo.html');
  fs.writeFileSync(html, pagina());
  const dom = execFileSync(bin, ['--headless', '--disable-gpu', '--dump-dom',
                                 '--virtual-time-budget=3000', 'file://' + html],
                           { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  fs.rmSync(tmp, { recursive: true, force: true });

  const m = dom.match(/<pre id="log">([\s\S]*?)<\/pre>/);
  if (!m) {
    console.log('  FALLA  la página no dejó resultados: el banco no llegó a correr');
    return 1;
  }
  const filas = m[1].split('\n').filter(Boolean).map((l) => l.split('\t'));
  let fallando = 0;
  for (const [estado, nombre, dio, esperaba] of filas) {
    console.log(`  ${estado}  ${nombre}`);
    if (estado === 'FALLA') {
      fallando++;
      console.log(`         dio ${dio}, esperaba ${esperaba}`);
    }
  }
  console.log(`\n${filas.length} casos · ${fallando ? fallando + ' fallando' : 'todos bien'}`);
  return fallando ? 1 : 0;
}

process.exit(main());
