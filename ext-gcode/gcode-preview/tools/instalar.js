#!/usr/bin/env node
// Instala el .vsix en todas las copias de VS Code que haya en esta máquina.
//
// Antes esto era una ruta de macOS escrita a mano dentro de `package.json`
// ("$HOME/Desktop/Visual Studio Code.app/..."), así que `npm run reinstall`
// nunca corrió en Windows ni en WSL: había que acordarse de invocar
// `code --install-extension` a mano.
//
// Y en WSL hay DOS instalaciones que importan y son distintas: el servidor
// remoto (~/.vscode-server/extensions) y la de Windows
// (C:\Users\<user>\.vscode\extensions). Instalar en una sola deja la otra con
// la versión vieja, y la extensión parece no haberse actualizado según desde
// qué ventana se abra el proyecto.

const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const vsix = path.join(__dirname, '..', 'gcode-preview.vsix');
if (!fs.existsSync(vsix)) {
  console.error(`no existe ${vsix} — corré primero "npm run package"`);
  process.exit(1);
}

function correr(cmd, args) {
  try {
    execFileSync(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    return true;
  } catch {
    return false;
  }
}

let ok = 0;

// 1. El `code` que esté en el PATH. En una ventana Remote-WSL, este instala en
//    el servidor, que es el que corre la extensión desde esa ventana.
if (correr('code', ['--install-extension', vsix, '--force'])) {
  console.log('  instalado con "code" del PATH (servidor / ventana actual)');
  ok++;
} else {
  console.log('  aviso: no se pudo usar "code" del PATH');
}

// 2. La instalación de Windows, si estamos en WSL. Su `code.cmd` no siempre
//    está en el PATH, así que se copia el build directamente sobre la carpeta
//    de la extensión: es lo mismo que hace el instalador y no depende de él.
const dirs = [];
for (const base of ['/mnt/c/Users']) {
  if (!fs.existsSync(base)) continue;
  for (const user of fs.readdirSync(base)) {
    const ext = path.join(base, user, '.vscode', 'extensions');
    if (fs.existsSync(ext)) dirs.push(ext);
  }
}
dirs.push(path.join(os.homedir(), '.vscode-server', 'extensions'));
// 3. La instalación LOCAL y normal: macOS, Linux nativo y Windows nativo usan
//    todos `~/.vscode/extensions`.
//
//    Faltaba, y era el caso más común de todos. Al generalizar esto de la ruta
//    de macOS escrita a mano a "todas las copias de la máquina" se cubrió WSL
//    —las dos instalaciones— y se perdió justo la que había antes. En una Mac
//    sin `code` en el PATH —que es lo normal si no se corrió "Shell Command:
//    Install 'code' command in PATH"— el script no instalaba en ningún lado y
//    decía "No se pudo instalar", con el .vsix recién construido al lado.
//    Resultado: la extensión seguía corriendo el código viejo y rechazaba
//    piezas que el CLI ya empaquetaba bien.
dirs.push(path.join(os.homedir(), '.vscode', 'extensions'));

for (const dir of dirs) {
  let destinos;
  try {
    destinos = fs.readdirSync(dir).filter((n) => n.includes('gcode-preview'));
  } catch { continue; }
  for (const d of destinos) {
    const destino = path.join(dir, d);
    for (const parte of ['out', 'media', 'package.json']) {
      const origen = path.join(__dirname, '..', parte);
      if (!fs.existsSync(origen)) continue;
      fs.cpSync(origen, path.join(destino, parte), { recursive: true, force: true });
    }
    console.log(`  actualizado ${destino}`);
    ok++;
  }
}

console.log(ok
  ? '\nListo. Recargá la ventana: Ctrl+Shift+P -> "Developer: Reload Window".'
  : '\nNo se pudo instalar en ningún lado.');
process.exit(ok ? 0 : 1);
