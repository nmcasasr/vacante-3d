/* global THREE, acquireVsCodeApi */
(function () {
  const vscode = acquireVsCodeApi();
  const hud = document.getElementById('hud');
  const cargando = document.getElementById('cargando');
  // La barra se prende cuando arranca el generador y se apaga recién cuando la
  // pieza nueva está DIBUJADA, no cuando Python termina: entre una cosa y la
  // otra hay medio segundo de parseo en el que la pantalla todavía muestra la
  // versión vieja, y apagarla ahí es prometer que ya está.
  const mostrarCarga = (on) => { if (cargando) cargando.classList.toggle('hidden', !on); };

  const canvas = document.getElementById('c');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  // Paleta del plano. Los viajes van un paso por encima del papel: presentes,
  // pero nunca compitiendo con la pieza.
  const TRAVEL_COL = 0xa8b2c6;
  const TRAVEL_HEX = '#a8b2c6';

  const scene = new THREE.Scene();
  // Azul de plano: el mismo papel que el panel, para que el modelo se lea como
  // un dibujo tecnico sobre la hoja y no como una ventana 3D pegada al lado.
  scene.background = new THREE.Color(0xebeae7);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 5000);
  camera.up.set(0, 0, 1); // printer Z is up
  camera.position.set(200, -200, 200);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  // Ambient stays low and a directional light does the work, because the solid
  // render needs shading to read as a surface. Lines are unaffected: they use
  // LineBasicMaterial, which ignores lights entirely.
  scene.add(new THREE.AmbientLight(0xffffff, 0.62));
  const sol = new THREE.DirectionalLight(0xffffff, 0.85);
  sol.position.set(1, -1.4, 1.2);
  scene.add(sol);

  let printGroup = null;

  function resize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  // --- Tiempo de impresión --------------------------------------------------
  // Un G-code no dice cuánto tarda: dice a qué velocidad PIDE ir. La máquina
  // casi nunca llega a esa velocidad, porque tiene que acelerar y frenar, y en
  // estas piezas el segmento medio mide ~0.4 mm — a 6000 mm/s² un segmento así
  // ni alcanza a estabilizarse. Dividir distancia entre velocidad da un número
  // alegre; lo que sigue es el mismo modelo trapezoidal que corre el firmware.
  //
  // Límites del A1 (ficha de máquina, no invención): 500 mm/s de velocidad, y
  // la aceleración que diga el M204 vigente, 6000 si el archivo no lo dice.
  // El jerk es el salto instantáneo de velocidad que el planificador tolera en
  // una esquina; por debajo de él la esquina no cuesta nada.
  const VEL_MAX = 500;        // mm/s
  const ACC_DEFECTO = 6000;   // mm/s²
  const JERK = 9;             // mm/s
  // Lo que cuesta un cambio de filamento completo, medido sobre el bloque real
  // de Bambu (29 s de descarga + 25 s de carga). Es la misma constante que usa
  // el generador en Python (comun.SEGUNDOS_POR_CAMBIO); si una cambia, la otra
  // también. Pesa: 67 cambios son más de una hora, más que muchas piezas.
  const SEG_POR_CAMBIO = 56;

  // Devuelve { total, porSeg, acum, pausas } en segundos. `porSeg[i]` incluye el
  // cambio de filamento que ocurre justo antes del segmento i, para que el
  // reloj de la barra de reproducción salte donde salta la impresora.
  function estimarTiempo(V, segV, segA, cambios) {
    const n = segV.length;
    const porSeg = new Float32Array(n);
    const acum = new Float64Array(n + 1);
    if (!n) return { total: 0, porSeg, acum, pausas: 0 };

    const d = new Float32Array(n);      // largo del segmento
    const ux = new Float32Array(n), uy = new Float32Array(n), uz = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const o = i * 6;
      const dx = V[o + 3] - V[o], dy = V[o + 4] - V[o + 1], dz = V[o + 5] - V[o + 2];
      const L = Math.hypot(dx, dy, dz) || 1e-9;
      d[i] = L; ux[i] = dx / L; uy[i] = dy / L; uz[i] = dz / L;
    }

    // Velocidad permitida en cada unión. jv[i] = entrada al segmento i.
    // Arranca y termina detenida.
    const jv = new Float64Array(n + 1);
    for (let i = 1; i < n; i++) {
      const v = Math.min(segV[i - 1], segV[i]);
      // Cambio de vector velocidad al doblar, eje por eje: si algún eje pide
      // más de JERK de golpe, hay que entrar más despacio en esa proporción.
      const ax = Math.abs(v * (ux[i] - ux[i - 1]));
      const ay = Math.abs(v * (uy[i] - uy[i - 1]));
      const az = Math.abs(v * (uz[i] - uz[i - 1]));
      const peor = Math.max(ax, ay, az);
      jv[i] = peor > JERK ? v * (JERK / peor) : v;
    }
    // Hacia atrás: nadie puede entrar a un segmento más rápido de lo que pueda
    // frenar dentro de él. Hacia adelante: ni más rápido de lo que alcance a
    // acelerar. Las dos pasadas juntas son lo que hace que una ráfaga de
    // segmentos cortos no llegue nunca a la velocidad pedida.
    for (let i = n - 1; i >= 0; i--) {
      jv[i] = Math.min(jv[i], Math.sqrt(jv[i + 1] * jv[i + 1] + 2 * segA[i] * d[i]));
    }
    for (let i = 0; i < n; i++) {
      jv[i + 1] = Math.min(jv[i + 1], Math.sqrt(jv[i] * jv[i] + 2 * segA[i] * d[i]));
    }

    // Marca de cuánto cuesta el cambio que cae justo antes de cada segmento.
    const extra = new Float32Array(n + 1);
    let pausas = 0;
    for (const c of cambios) {
      if (c.kind === 'manual') { pausas++; continue; } // la espera la fija un humano
      const i = Math.max(0, Math.min(n, c.seg));
      extra[i] += SEG_POR_CAMBIO;
    }

    let total = 0;
    for (let i = 0; i < n; i++) {
      const a = segA[i], ve = jv[i], vx = jv[i + 1];
      // Cima del trapecio si acelerara y frenara sin meseta.
      let vp = Math.sqrt((2 * a * d[i] + ve * ve + vx * vx) / 2);
      if (vp > segV[i]) vp = segV[i];
      const dAcc = Math.max(0, (vp * vp - ve * ve) / (2 * a));
      const dDec = Math.max(0, (vp * vp - vx * vx) / (2 * a));
      const dCru = Math.max(0, d[i] - dAcc - dDec);
      const t = (vp - ve) / a + (vp - vx) / a + (vp > 0 ? dCru / vp : 0);
      const dt = (isFinite(t) && t > 0 ? t : 0) + extra[i];
      porSeg[i] = dt;
      total += dt;
      acum[i + 1] = total;
    }
    return { total, porSeg, acum, pausas };
  }

  // Velocidad real de cada segmento: largo dividido el tiempo que sale del
  // modelo trapezoidal. No es la F del g-code — en un tramo de 0.4 mm entre dos
  // esquinas la máquina no llega ni cerca de lo que se le pidió, y ver dónde
  // pasa eso explica por qué una pieza tarda más de lo que uno calculó.
  // Sobre papel claro, un gris en el medio de la rampa no se ve: se confunde
  // con el fondo justo en los valores más frecuentes. Los tres extremos tienen
  // que ser oscuros. Azul -> violeta -> naranja recorre el tono sin pasar por
  // ningún claro.
  const VEL_LENTO = [0x1b, 0x3a, 0x7a];
  const VEL_MEDIO = [0x8a, 0x2f, 0x8c];
  const VEL_RAPIDO = [0xe8, 0x56, 0x2a];
  const velHex = (t) => {
    const a = t < 0.5 ? VEL_LENTO : VEL_MEDIO;
    const b = t < 0.5 ? VEL_MEDIO : VEL_RAPIDO;
    const k = t < 0.5 ? t * 2 : (t - 0.5) * 2;
    const c = [0, 1, 2].map((i) => Math.round(a[i] + (b[i] - a[i]) * k));
    return '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('');
  };

  function coloresVelocidad(V, ext, porSeg, travelCol) {
    const n = ext.length;
    const colors = new Float32Array(n * 6);
    const v = new Float64Array(n);
    const muestras = [];
    for (let i = 0; i < n; i++) {
      const o = i * 6;
      const d = Math.hypot(V[o + 3] - V[o], V[o + 4] - V[o + 1], V[o + 5] - V[o + 2]);
      v[i] = porSeg[i] > 1e-9 ? d / porSeg[i] : 0;
      if (ext[i] && v[i] > 0) muestras.push(v[i]);
    }
    // Los extremos se toman por percentil: un solo viaje a 500 mm/s aplastaría
    // toda la escala de la pieza contra el extremo lento.
    muestras.sort((a, b) => a - b);
    const lo = muestras.length ? muestras[Math.floor(muestras.length * 0.02)] : 0;
    const hi = muestras.length ? muestras[Math.floor(muestras.length * 0.98)] : 1;
    // Piso absoluto, igual que el mapa de relieve. Una pieza a velocidad
    // constante —que es lo normal: 20.00 mm/s en toda la cabeza del hongo— deja
    // `hi - lo` en cero, y una escala de cero convierte el último bit de un
    // Float32 en contraste a pleno color. Lo que se veía no era velocidad, era
    // ruido de redondeo. Por debajo de este umbral no hay nada que mostrar.
    const RANGO_MINIMO = Math.max(2, 0.08 * hi);   // mm/s
    const plano = hi - lo < RANGO_MINIMO;
    const span = Math.max(1e-6, hi - lo);
    for (let i = 0; i < n; i++) {
      const o = i * 6;
      let r0, g0, b0;
      if (!ext[i]) {
        r0 = travelCol.r; g0 = travelCol.g; b0 = travelCol.b;
      } else if (plano) {
        r0 = VEL_MEDIO[0] / 255; g0 = VEL_MEDIO[1] / 255; b0 = VEL_MEDIO[2] / 255;
      } else {
        const t = Math.max(0, Math.min(1, (v[i] - lo) / span));
        const a = t < 0.5 ? VEL_LENTO : VEL_MEDIO;
        const b = t < 0.5 ? VEL_MEDIO : VEL_RAPIDO;
        const k = t < 0.5 ? t * 2 : (t - 0.5) * 2;
        r0 = (a[0] + (b[0] - a[0]) * k) / 255;
        g0 = (a[1] + (b[1] - a[1]) * k) / 255;
        b0 = (a[2] + (b[2] - a[2]) * k) / 255;
      }
      colors[o] = r0; colors[o + 1] = g0; colors[o + 2] = b0;
      colors[o + 3] = r0; colors[o + 4] = g0; colors[o + 5] = b0;
    }
    return { colors, lo, hi, plano };
  }

  function reloj(s) {
    if (!isFinite(s) || s <= 0) return '0m';
    const h = Math.floor(s / 3600);
    const m = Math.round((s - h * 3600) / 60);
    if (h && m === 60) return `${h + 1}h 0m`;
    return h ? `${h}h ${m}m` : `${m}m`;
  }

  function relojCorto(s) {
    const t = Math.max(0, Math.round(s));
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60);
    return `${h}:${String(m).padStart(2, '0')}`;
  }

  // --- G-code parsing -------------------------------------------------------
  // Produces ONE ordered list of line segments in G-code execution order, so
  // the timelapse bar can reveal them progressively. Each segment carries a
  // baked vertex color (fan-lerp for extrusion, dim gray for travel).
  // Handles G90/G91, M82/M83, G92, M106/M107.
  function parse(text) {
    const lines = text.split(/\r?\n/);
    let absPos = true;    // G90 default
    let absExt = true;    // M82 default (slicer usually sets M83)
    let fan = 0;          // 0..1
    const pos = { x: 0, y: 0, z: 0, e: 0 };

    const V = [];         // ordered segment vertices (6 floats per segment)
    const C = [];         // ordered segment colors (6 floats per segment)
    const ext = [];       // segment index -> 1 if extrusion, 0 if travel
    const segZ = [];      // segment index -> representative Z (mm)
    const segV = [];      // segment index -> commanded speed (mm/s)
    const segA = [];      // segment index -> acceleration in force (mm/s²)
    const bbox = { minx: Infinity, miny: Infinity, minz: Infinity, maxx: -Infinity, maxy: -Infinity, maxz: -Infinity };

    // Sobre papel azul un "frio" azul desaparece, asi que el extremo frio pasa
    // a ser la tinta palida del plano y el calido se queda con el unico acento.
    const cold = new THREE.Color(0xe8562a); // fan off
    const hot = new THREE.Color(0x1f3f8f);  // fan on
    const travelCol = new THREE.Color(TRAVEL_COL);
    const tmp = new THREE.Color();

    // Which AMS slot is loaded, and where it changed. `T0`..`T3` are the four
    // slots; the A1's start G-code also emits `T1000`, a "no tool" sentinel, and
    // the toolchange template can emit `T255` — neither is a slot, so anything
    // outside 0..3 is ignored. `M620 S{n}A` brackets the change but does not
    // perform it, so T is the authoritative signal.
    // A manual pause (`M400 U1`, Bambu's pause — M600 does not exist on these
    // machines) is just as much a colour change, but the G-code cannot say what
    // got loaded: a human swapped the spool. So it gets its own band, painted
    // from a separate palette and labelled "unknown", instead of being silently
    // folded into the slot that was loaded before.
    // La F del G-code es persistente: vale hasta que otra la cambie, y puede
    // venir sola (`G1 F1200`) o dentro de un movimiento. Se lee siempre, incluso
    // en los movimientos degenerados que después se descartan, porque el que
    // sigue hereda esa velocidad.
    let feed = 0;         // mm/min
    let accel = ACC_DEFECTO;
    let tool = 0;
    let manual = 0;       // how many manual pauses so far
    const segBand = [];   // segment index -> band (0..3 = AMS slot, 4+ = manual)
    const segE = [];      // segment index -> mm of filament it consumes
    const changes = [];   // { seg, kind, from, to, x, y, z }
    const band = () => (manual === 0 ? tool : 3 + manual);

    function bump(x, y, z) {
      if (x < bbox.minx) bbox.minx = x;
      if (y < bbox.miny) bbox.miny = y;
      if (z < bbox.minz) bbox.minz = z;
      if (x > bbox.maxx) bbox.maxx = x;
      if (y > bbox.maxy) bbox.maxy = y;
      if (z > bbox.maxz) bbox.maxz = z;
    }

    function num(tok) {
      return parseFloat(tok.slice(1));
    }

    // Antes de la pieza hay líneas de purga: dos trazos de 180 mm en el borde
    // frontal de la cama. Son extrusiones de verdad, así que el bbox las
    // tragaba y la caja pasaba de los 152 mm que mide la pieza a 199 — la
    // cámara encuadraba media cama vacía, el ajuste de circunferencia de esa
    // capa daba un radio de ~90 mm, y en el mapa de relieve salían como dos
    // rayas naranjas cruzando todo.
    let segObjeto = 0;
    let empezado = false;

    for (let raw of lines) {
      if (!empezado && (raw.indexOf('FIN DEL START GCODE') >= 0
                        || /^\s*M1007\s+S1\b/.test(raw))) {
        empezado = true;
        segObjeto = ext.length;
        bbox.minx = bbox.miny = bbox.minz = Infinity;
        bbox.maxx = bbox.maxy = bbox.maxz = -Infinity;
      }
      const semi = raw.indexOf(';');
      if (semi >= 0) raw = raw.slice(0, semi);
      raw = raw.trim();
      if (!raw) continue;
      const t = raw.split(/\s+/);
      const cmd = t[0].toUpperCase();

      const mt = /^T(\d+)$/.exec(cmd);
      if (mt) {
        const n = parseInt(mt[1], 10);
        if (n >= 0 && n <= 3 && n !== tool) {
          const desde = band();
          tool = n;
          // An AMS change tells us exactly what is loaded, so it also cancels
          // any "unknown filament" state a previous manual pause left behind.
          manual = 0;
          changes.push({ seg: ext.length, kind: 'ams', from: desde, to: band(), x: pos.x, y: pos.y, z: pos.z });
        }
        continue;
      }

      // `M400 U1` — pause and wait for the user. `M400` alone is just a queue
      // flush and must not be mistaken for one.
      if (cmd === 'M400' && t.some((tok) => /^U1$/i.test(tok))) {
        const desde = band();
        manual++;
        changes.push({ seg: ext.length, kind: 'manual', from: desde, to: band(), x: pos.x, y: pos.y, z: pos.z });
        continue;
      }

      if (cmd === 'G90') { absPos = true; continue; }
      if (cmd === 'G91') { absPos = false; continue; }
      if (cmd === 'M82') { absExt = true; continue; }
      if (cmd === 'M83') { absExt = false; continue; }
      if (cmd === 'M204') {
        for (let i = 1; i < t.length; i++) {
          if (/^S/i.test(t[i])) { const v = num(t[i]); if (v > 0) accel = v; }
        }
        continue;
      }
      if (cmd === 'M107') { fan = 0; continue; }
      if (cmd === 'M106') {
        let s = 255;
        for (let i = 1; i < t.length; i++) {
          if (t[i][0] === 'S' || t[i][0] === 's') s = num(t[i]);
        }
        fan = Math.max(0, Math.min(1, s / 255));
        continue;
      }
      if (cmd === 'G92') {
        for (let i = 1; i < t.length; i++) {
          const c = t[i][0].toUpperCase();
          const v = num(t[i]);
          if (c === 'X') pos.x = v;
          else if (c === 'Y') pos.y = v;
          else if (c === 'Z') pos.z = v;
          else if (c === 'E') pos.e = v;
        }
        continue;
      }
      // Arcos. Orca los emite cuando "Arc fitting" está activo, y son miles: un
      // corte de la caperuza traía 5107 G2/G3 contra 27957 G1.
      //
      // Ignorarlos era peor que no dibujarlos: como tampoco actualizaban la
      // posición, el G1 siguiente trazaba una recta desde donde había quedado
      // el cabezal hacía cientos de movimientos. La pieza se veía cruzada de
      // líneas largas y con zonas vacías, que es el "no se ve bien" del preview.
      //
      // Se interpolan en tramos rectos —el visor dibuja líneas de todos modos— y
      // se reparte la extrusión por igual entre ellos.
      if (cmd === 'G2' || cmd === 'G3') {
        const start = { x: pos.x, y: pos.y, z: pos.z };
        let i = 0, j = 0, ex = pos.x, ey = pos.y, ez = pos.z, de = 0;
        for (let k = 1; k < t.length; k++) {
          const c = t[k][0].toUpperCase();
          const v = num(t[k]);
          if (isNaN(v)) continue;
          if (c === 'X') ex = absPos ? v : pos.x + v;
          else if (c === 'Y') ey = absPos ? v : pos.y + v;
          else if (c === 'Z') ez = absPos ? v : pos.z + v;
          else if (c === 'I') i = v;
          else if (c === 'J') j = v;
          else if (c === 'F') feed = v;
          else if (c === 'E') {
            if (absExt) { de = v - pos.e; pos.e = v; }
            else { de = v; pos.e += v; }
          }
        }
        const cxA = start.x + i, cyA = start.y + j;
        const r = Math.hypot(i, j);
        let a0 = Math.atan2(start.y - cyA, start.x - cxA);
        let a1 = Math.atan2(ey - cyA, ex - cxA);
        // G2 es horario, G3 antihorario. El barrido se lleva al signo correcto;
        // si da cero es una vuelta completa, no un arco nulo.
        let barrido = a1 - a0;
        if (cmd === 'G2') { while (barrido > 0) barrido -= 2 * Math.PI; if (barrido === 0) barrido = -2 * Math.PI; }
        else { while (barrido < 0) barrido += 2 * Math.PI; if (barrido === 0) barrido = 2 * Math.PI; }
        const largo = Math.abs(barrido) * r;
        const n = Math.max(2, Math.min(64, Math.ceil(largo / 0.5)));
        const extruding = de > 1e-6;
        let px = start.x, py = start.y, pz = start.z;
        for (let s = 1; s <= n; s++) {
          const f = s / n;
          const a = a0 + barrido * f;
          const qx = cxA + r * Math.cos(a);
          const qy = cyA + r * Math.sin(a);
          const qz = start.z + (ez - start.z) * f;
          V.push(px, py, pz, qx, qy, qz);
          if (extruding) {
            tmp.copy(cold).lerp(hot, fan);
            C.push(tmp.r, tmp.g, tmp.b, tmp.r, tmp.g, tmp.b);
            bump(px, py, pz);
            bump(qx, qy, qz);
          } else {
            C.push(travelCol.r, travelCol.g, travelCol.b, travelCol.r, travelCol.g, travelCol.b);
          }
          ext.push(extruding ? 1 : 0);
          segZ.push(qz);
          segBand.push(band());
          segE.push(extruding ? de / n : 0);
          segV.push(Math.min(feed / 60, VEL_MAX));
          segA.push(accel);
          px = qx; py = qy; pz = qz;
        }
        pos.x = ex; pos.y = ey; pos.z = ez;
        continue;
      }
      if (cmd === 'G0' || cmd === 'G1') {
        const start = { x: pos.x, y: pos.y, z: pos.z };
        let de = 0;
        for (let i = 1; i < t.length; i++) {
          const c = t[i][0].toUpperCase();
          const v = num(t[i]);
          if (isNaN(v)) continue;
          if (c === 'X') pos.x = absPos ? v : pos.x + v;
          else if (c === 'Y') pos.y = absPos ? v : pos.y + v;
          else if (c === 'Z') pos.z = absPos ? v : pos.z + v;
          else if (c === 'F') feed = v;
          else if (c === 'E') {
            if (absExt) { de = v - pos.e; pos.e = v; }
            else { de = v; pos.e += v; }
          }
        }
        // A move that extrudes without going anywhere is a prime, a purge or a
        // load — not deposited path. An AMS filament change parks at the cutter
        // (X267, off the bed) and pushes 24 mm through there; counting that as
        // toolpath stretched the bbox to X267 and framed the camera on a model
        // twice as wide as the real one. Skip degenerate moves outright: they
        // draw nothing anyway, and they would also land in a layer bin and in
        // the overhang grid.
        const moved = (pos.x - start.x) ** 2 + (pos.y - start.y) ** 2 + (pos.z - start.z) ** 2 > 1e-12;
        if (!moved) continue;
        const extruding = de > 1e-6;

        V.push(start.x, start.y, start.z, pos.x, pos.y, pos.z);
        if (extruding) {
          tmp.copy(cold).lerp(hot, fan);
          C.push(tmp.r, tmp.g, tmp.b, tmp.r, tmp.g, tmp.b);
          bump(start.x, start.y, start.z);
          bump(pos.x, pos.y, pos.z);
        } else {
          C.push(travelCol.r, travelCol.g, travelCol.b, travelCol.r, travelCol.g, travelCol.b);
        }
        ext.push(extruding ? 1 : 0);
        segZ.push(pos.z);
        segBand.push(band());
        segE.push(extruding ? de : 0);
        segV.push(Math.min(feed / 60, VEL_MAX));
        segA.push(accel);
      }
    }
    return { V, C, ext, segZ, segBand, segE, segV, segA, changes, bbox, segObjeto };
  }

  // Estimate layer height so we can bin segments into layers by real Z. Works
  // for both planar prints (Z jumps between discrete layers) and vase-mode
  // spirals (Z climbs continuously) — the latter is measured by counting how
  // many full revolutions the toolpath makes around the model's center.
  // Median XY of the extrusion path, used as the axis to count revolutions
  // around. NOT the bbox centre: a couple of purge/prime lines at the edge of
  // the bed (every FullControl and slicer start-gcode has them) drag the bbox
  // centre right onto the toolpath, and the angle then wobbles instead of
  // accumulating a full turn per revolution — measured 86 revolutions instead
  // of 375 on a lamp, i.e. a 1.74 mm layer height reported for a 0.4 mm print.
  // The median ignores those outliers; sampling keeps it O(1) memory on big files.
  function extrusionCentre(V, ext) {
    const xs = [], ys = [];
    const step = Math.max(1, Math.floor(ext.length / 20000));
    for (let s = 0; s < ext.length; s += step) {
      if (!ext[s]) continue;
      xs.push(V[s * 6 + 3]);
      ys.push(V[s * 6 + 4]);
    }
    if (!xs.length) return [0, 0];
    xs.sort((a, b) => a - b);
    ys.sort((a, b) => a - b);
    return [xs[xs.length >> 1], ys[ys.length >> 1]];
  }

  function estimateLayerHeight(V, ext, bbox) {
    const span = bbox.maxz - bbox.minz;
    if (!isFinite(span) || span <= 1e-6) return 0.2;

    const zset = new Set();
    let nExt = 0;
    for (let s = 0; s < ext.length; s++) {
      if (!ext[s]) continue;
      nExt++;
      zset.add(Math.round(V[s * 6 + 5] * 1000)); // end Z, µm-rounded
    }
    if (nExt < 2) return 0.2;

    if (zset.size < nExt * 0.4) {
      // Planar: distinct Z levels -> median gap between adjacent levels.
      const sorted = [...zset].map((v) => v / 1000).sort((a, b) => a - b);
      const gaps = [];
      for (let i = 1; i < sorted.length; i++) {
        const g = sorted[i] - sorted[i - 1];
        if (g > 1e-4) gaps.push(g);
      }
      gaps.sort((a, b) => a - b);
      return gaps.length ? gaps[gaps.length >> 1] : span / Math.max(1, sorted.length - 1);
    }

    // Spiral: Z ~ continuous. layers = revolutions = unwrapped angle / 2pi.
    const [cx, cy] = extrusionCentre(V, ext);

    // Skip the leading run at constant Z before counting: a solid-base spiral
    // (a bowl floor is an Archimedean spiral, ~40 turns at one Z), a brim, or
    // just the flat first turn. Those turns gain no height, so counting them
    // shrinks the estimate — a 0.40 mm bowl with a floor measured 0.31 mm, and
    // a 1.19 mm celosia pitch measured 0.62 mm. Height is measured from that
    // same Z so the two stay consistent.
    let z0 = null, start = 0;
    for (let s = 0; s < ext.length; s++) {
      if (!ext[s]) continue;
      const z = V[s * 6 + 5];
      if (z0 === null) { z0 = z; start = s; continue; }
      if (Math.abs(z - z0) > 1e-6) { start = s; break; }
    }
    const climb = bbox.maxz - (z0 === null ? bbox.minz : z0);
    if (climb <= 1e-6) return span;

    let prev = null, total = 0;
    for (let s = start; s < ext.length; s++) {
      if (!ext[s]) continue;
      const a = Math.atan2(V[s * 6 + 4] - cy, V[s * 6 + 3] - cx);
      if (prev !== null) {
        let d = a - prev;
        while (d > Math.PI) d -= 2 * Math.PI;
        while (d < -Math.PI) d += 2 * Math.PI;
        total += d;
      }
      prev = a;
    }
    const revs = Math.max(1, Math.abs(total) / (2 * Math.PI));
    return climb / revs;
  }

  // --- Overhang heat map ----------------------------------------------------
  // For each extrusion segment, look one layer height below for supporting
  // material. The horizontal offset to the nearest support, over the vertical
  // gap, gives the local overhang angle from vertical: 0deg = vertical wall
  // (safe), 90deg = unsupported ceiling. Works off real Z, so it's correct for
  // vase-mode spirals too. Colors go green -> yellow -> orange -> red.
  const OVH_MAX_DIST = 3.0;   // mm: no support found within this = worst case
  const OVH_WARN = 45;        // deg from vertical where risk starts
  const OVH_FAIL = 65;        // deg where it will likely fail

  function overhangAngleToColor(deg, out) {
    let r, g, b;
    if (deg <= OVH_WARN) {
      const t = deg / OVH_WARN;           // verde -> ámbar
      r = 0.08 + t * 0.55; g = 0.50 - t * 0.12; b = 0.24 * (1 - t);
    } else {
      const t = Math.min(1, (deg - OVH_WARN) / (OVH_FAIL - OVH_WARN)); // ámbar -> rojo
      r = 0.63 + t * 0.10; g = 0.38 * (1 - t) + 0.11 * t; b = 0.03 + t * 0.08;
    }
    out.setRGB(r, g, b);
  }

  // Squared distance from point (px,py) to segment (x1,y1)-(x2,y2).
  function distToSegSq(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const len2 = dx * dx + dy * dy;
    let t = len2 > 0 ? ((px - x1) * dx + (py - y1) * dy) / len2 : 0;
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    const cx = x1 + t * dx, cy = y1 + t * dy;
    return (px - cx) ** 2 + (py - cy) ** 2;
  }

  // Returns { colors: Float32Array(len like C), maxDeg }.
  // --- Mapa de solape ------------------------------------------------------
  // Cuánto se pisan dos cordones vecinos. Es el criterio que de verdad gobierna
  // una pieza en modo vaso —si la vuelta nueva no apoya sobre la anterior, la
  // pared se abre— y es el mismo que usan el aviso del generador y el de los
  // toques. Va aparte del ángulo porque no son lo mismo: con paso vertical
  // adaptativo, una vuelta que sube 0.2 mm y se corre 0.5 marca 68° de ángulo y
  // sin embargo tiene 55% de solape, que es sano.
  const SOL_BIEN = [0x15, 0x7f, 0x3c];   // >= 50%
  const SOL_JUSTO = [0xa1, 0x62, 0x07];  // 25%
  const SOL_MAL = [0xb9, 0x1c, 0x1c];    // 0: no se tocan

  function solapeAColor(frac, out) {
    // 0.5 es el umbral que veníamos usando en los avisos: por debajo conviene
    // bajar la velocidad, por debajo de 0.25 no esperes que salga.
    const t = Math.max(0, Math.min(1, frac / 0.5));
    const a = t < 0.5 ? SOL_MAL : SOL_JUSTO;
    const b = t < 0.5 ? SOL_JUSTO : SOL_BIEN;
    const k = t < 0.5 ? t * 2 : (t - 0.5) * 2;
    out.setRGB((a[0] + (b[0] - a[0]) * k) / 255,
               (a[1] + (b[1] - a[1]) * k) / 255,
               (a[2] + (b[2] - a[2]) * k) / 255);
  }

  function computeOverhang(V, ext, segZ, layerH, bbox, travelCol) {
    const segCount = ext.length;
    const colors = new Float32Array(segCount * 6);
    const solape = new Float32Array(segCount * 6);
    const cordon = anchoDeCordon();
    let peorSolape = 1;
    const cell = OVH_MAX_DIST;
    // Las franjas del índice se miden con el RADIO DE BÚSQUEDA, no con la altura
    // de capa. Antes iban en `round(z / layerH)` con una altura constante, y eso
    // se rompió en cuanto el generador pasó a subir distinto según la pendiente
    // (0.20 a 0.40 mm en la misma pieza): las franjas dejaron de coincidir con
    // las vueltas, algunas quedaron vacías, y el segmento que miraba ahí no
    // encontraba apoyo y se pintaba de rojo. Salían salpicaduras aisladas por
    // toda la superficie en vez de agruparse donde la pared se tumba.
    //
    // Con franjas de OVH_MAX_DIST alcanza con mirar la propia y la de abajo para
    // cubrir todo el rango buscado, sea cual sea el paso vertical.
    const zb = (z) => Math.floor(z / OVH_MAX_DIST);
    const key = (b, gx, gy) => b + ':' + gx + ':' + gy;

    // Spatial hash of extrusion SEGMENTS (continuous wall, so distance is the
    // true perpendicular gap — no tangential sampling noise). Each segment is
    // registered in the cells of both its endpoints. Entry: [x1,y1,x2,y2,z].
    const grid = new Map();
    const put = (b, gx, gy, e) => {
      const kk = key(b, gx, gy);
      let arr = grid.get(kk);
      if (!arr) { arr = []; grid.set(kk, arr); }
      arr.push(e);
    };
    for (let s = 0; s < segCount; s++) {
      if (!ext[s]) continue;
      const o = s * 6;
      const x1 = V[o], y1 = V[o + 1], x2 = V[o + 3], y2 = V[o + 4];
      const b = zb(segZ[s]);
      const e = [x1, y1, x2, y2, segZ[s], s];
      put(b, Math.floor(x1 / cell), Math.floor(y1 / cell), e);
      const g2 = key(b, Math.floor(x2 / cell), Math.floor(y2 / cell));
      if (g2 !== key(b, Math.floor(x1 / cell), Math.floor(y1 / cell))) {
        put(b, Math.floor(x2 / cell), Math.floor(y2 / cell), e);
      }
    }

    const col = new THREE.Color();
    const bedZ = bbox.minz + 1.5 * layerH; // first ~layer sits on the bed
    let maxDeg = 0;
    for (let s = 0; s < segCount; s++) {
      const o = s * 6;
      if (!ext[s]) {
        colors[o] = travelCol.r; colors[o + 1] = travelCol.g; colors[o + 2] = travelCol.b;
        colors[o + 3] = travelCol.r; colors[o + 4] = travelCol.g; colors[o + 5] = travelCol.b;
        solape[o] = travelCol.r; solape[o + 1] = travelCol.g; solape[o + 2] = travelCol.b;
        solape[o + 3] = travelCol.r; solape[o + 4] = travelCol.g; solape[o + 5] = travelCol.b;
        continue;
      }
      const mx = (V[o] + V[o + 3]) / 2;
      const my = (V[o + 1] + V[o + 4]) / 2;
      const mz = segZ[s];

      let deg, sep3 = 0;
      if (mz <= bedZ) {
        deg = 0;
      } else {
        const gx = Math.floor(mx / cell), gy = Math.floor(my / cell);
        const qb = zb(mz);
        // Apoyo = el material más cercano que esté DEBAJO, y punto. Sin ventana
        // en múltiplos de la altura de capa: esa ventana daba por "sin apoyo" a
        // una vuelta que subía más que 2×layerH, aunque tuviera pared justo
        // abajo. Se elige por distancia 3D, que es el hueco de verdad.
        let mejor = Infinity, bestH = Infinity, bestDV = layerH;
        for (let bz = qb; bz >= qb - 1; bz--) {
          for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              const arr = grid.get(key(bz, gx + dx, gy + dy));
              if (!arr) continue;
              for (let i = 0; i < arr.length; i++) {
                const e = arr[i];
                const dv = mz - e[4];
                // Se acepta apoyo AL LADO, no solo debajo. Una pasada plana
                // —una repisa, el piso de un bol, el relleno radial de una
                // banda tumbada— se sostiene sobre su vecina a la misma altura,
                // y exigirle material debajo la marca suelta cuando no lo está.
                // Se descartan los vecinos del propio recorrido: el segmento
                // anterior y el siguiente siempre tocan, y contarlos haría que
                // todo pareciera apoyado.
                if (dv < -0.05 || dv > OVH_MAX_DIST) continue;
                if (Math.abs(s - e[5]) < 60) continue;
                const h2 = distToSegSq(mx, my, e[0], e[1], e[2], e[3]);
                const d3 = h2 + dv * dv;
                if (d3 < mejor) { mejor = d3; bestH = h2; bestDV = dv; }
              }
            }
          }
        }
        const dist = bestH === Infinity ? OVH_MAX_DIST : Math.min(OVH_MAX_DIST, Math.sqrt(bestH));
        deg = Math.atan2(dist, bestDV) * 180 / Math.PI;
        // La separación entre los EJES de los dos cordones. Es lo que decide si
        // hay superficie común: por debajo de un ancho de cordón se tocan, por
        // encima no. El ángulo no lo dice —con paso adaptativo un dv chico
        // infla el ángulo aunque el solape sea sano— así que van por separado.
        sep3 = mejor === Infinity ? OVH_MAX_DIST : Math.sqrt(mejor);
      }
      if (deg > maxDeg) maxDeg = deg;
      const frac = Math.max(0, 1 - sep3 / cordon);
      if (frac < peorSolape) peorSolape = frac;
      overhangAngleToColor(deg, col);
      colors[o] = col.r; colors[o + 1] = col.g; colors[o + 2] = col.b;
      colors[o + 3] = col.r; colors[o + 4] = col.g; colors[o + 5] = col.b;
      solapeAColor(frac, col);
      solape[o] = col.r; solape[o + 1] = col.g; solape[o + 2] = col.b;
      solape[o + 3] = col.r; solape[o + 4] = col.g; solape[o + 5] = col.b;
    }
    return { colors, maxDeg, solape, peorSolape };
  }

  // --- Filament colour map --------------------------------------------------
  // Colours the toolpath by which AMS slot was loaded, so a multi-colour print
  // shows where each filament starts and ends. These are IDENTIFIERS, not the
  // real filament colours: the G-code does not carry those (they live in the
  // .3mf's project_settings), and inventing them would be worse than useless —
  // a wrong "white" band reads as the print, not as a legend entry.
  const SLOT_COLOURS = [0x1d4ed8, 0xb45309, 0x15803d, 0xa21caf];
  const SLOT_HEX = ['#1d4ed8', '#b45309', '#15803d', '#a21caf'];
  // Bands 4+ are manual pauses: desaturated on purpose, so "we know this is
  // AMS slot A2" never looks like "someone swapped something in here".
  const MANUAL_COLOURS = [0x6b5b95, 0x8a7350, 0x4f7d70, 0x8a5a5a];
  const MANUAL_HEX = ['#6b5b95', '#8a7350', '#4f7d70', '#8a5a5a'];
  const bandColour = (b) => (b < 4 ? SLOT_COLOURS[b] : MANUAL_COLOURS[(b - 4) % MANUAL_COLOURS.length]);
  const bandHex = (b) => (b < 4 ? SLOT_HEX[b] : MANUAL_HEX[(b - 4) % MANUAL_HEX.length]);
  const bandLabel = (b) => (b < 4 ? `AMS A${b + 1} (T${b})` : `manual pause #${b - 3} (filament unknown)`);

  function computeFilamentColors(V, ext, segBand, travelCol) {
    const n = ext.length;
    const colors = new Float32Array(n * 6);
    const cols = new Map();
    const colourOf = (b) => {
      let c = cols.get(b);
      if (!c) { c = new THREE.Color(bandColour(b)); cols.set(b, c); }
      return c;
    };
    // Travel keeps the neutral grey it has in every mode: in a multi-colour
    // print the change itself is a long travel out to the cutter and back, and
    // painting that in a slot colour draws a bright line across the whole bed.
    for (let i = 0; i < n; i++) {
      const o = i * 6;
      const c = ext[i] ? colourOf(segBand[i]) : travelCol;
      colors[o] = c.r; colors[o + 1] = c.g; colors[o + 2] = c.b;
      colors[o + 3] = c.r; colors[o + 4] = c.g; colors[o + 5] = c.b;
    }
    return colors;
  }

  // Where each change actually shows up on the model: the change block itself
  // runs off the bed (cutter at X267, wiper at X-48.2), so the position
  // recorded when `T` executed is meaningless as a marker. The useful anchor is
  // where printing RESUMES — the first extruding segment after the change.
  function resolveChanges(changes, V, ext) {
    return changes.map((c) => {
      let i = c.seg;
      while (i < ext.length && !ext[i]) i++;
      const o = i * 6;
      return i < ext.length
        ? { ...c, x: V[o], y: V[o + 1], z: V[o + 2], resumed: true }
        : { ...c, resumed: false };
    });
  }

  // --- Bleed simulation -----------------------------------------------------
  // What colour actually LEAVES the nozzle, as opposed to which slot is loaded.
  //
  // A filament change does not swap the colour instantly: the melt zone still
  // holds the old material, and it leaves mixed with the new one over the next
  // stretch of extrusion. Modelled as a first-order lag on extruded length —
  // each mm of filament replaces a fixed fraction of what is in the melt zone:
  //
  //     c += (c_slot - c) · (1 - exp(-dE / L))
  //
  // L is the length constant; a change reads as clean at about 3·L. The number
  // to feed it is NOT folklore — Bambu ships one, in `flush_volumes_matrix`,
  // and it is per colour PAIR. That matrix is in mm³, which is the easy thing
  // to get wrong: divided by the filament cross-section (2.405 mm² for 1.75 mm)
  // the real range is
  //
  //     PLA -> PLA, similar colours    108 mm³ =  45 mm  ->  L ≈ 15
  //     PLA -> PETG                    146 mm³ =  61 mm  ->  L ≈ 20
  //     PLA -> PLA, opposite colours   280 mm³ = 116 mm  ->  L ≈ 39
  //     PETG -> PLA                    551 mm³ = 229 mm  ->  L ≈ 76
  //
  // 20 is the default because it covers the common case. Note this is the
  // volume for an INVISIBLY clean change; an organic patch reads fine well
  // before that. Purging shortens nothing — it spends the same length somewhere
  // other than the part.
  //
  // This is the mode for deciding how tall a colour band has to be. The nominal
  // Filament mode answers "which slot", this one answers "what will I see".
  let BLEED_L = 20;

  function computeBleedColors(ext, segBand, segE, travelCol) {
    const n = ext.length;
    const colors = new Float32Array(n * 6);
    const objetivo = (b) => {
      const h = bandColour(b);
      return [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255];
    };
    // arranca ya cargado con el primer color: antes del primer cambio no hay mezcla
    let c = objetivo(segBand.length ? segBand[0] : 0);
    for (let i = 0; i < n; i++) {
      const o = i * 6;
      if (ext[i]) {
        const t = objetivo(segBand[i]);
        const k = 1 - Math.exp(-(segE[i] || 0) / BLEED_L);
        c = [c[0] + (t[0] - c[0]) * k, c[1] + (t[1] - c[1]) * k, c[2] + (t[2] - c[2]) * k];
        colors[o] = c[0]; colors[o + 1] = c[1]; colors[o + 2] = c[2];
      } else {
        colors[o] = travelCol.r; colors[o + 1] = travelCol.g; colors[o + 2] = travelCol.b;
      }
      colors[o + 3] = colors[o]; colors[o + 4] = colors[o + 1]; colors[o + 5] = colors[o + 2];
    }
    return colors;
  }

  // How much of the print is still visibly mixed: the fraction of extruding
  // segments whose colour has not yet reached 90 % of its slot's colour. This is
  // the number to drive down when tuning band heights.
  function bleedStats(ext, segBand, colors) {
    let sucios = 0, total = 0;
    for (let i = 0; i < ext.length; i++) {
      if (!ext[i]) continue;
      total++;
      const o = i * 6, h = bandColour(segBand[i]);
      const t = [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255];
      const d = Math.hypot(colors[o] - t[0], colors[o + 1] - t[1], colors[o + 2] - t[2]);
      if (d > 0.1) sucios++;
    }
    return total ? sucios / total : 0;
  }

  // --- Relief map -----------------------------------------------------------
  // Colours each extrusion by how far its radius sits from the mean radius of
  // its own layer. That is what makes a SURFACE PATTERN visible.
  //
  // Why it is needed: the path is drawn with flat vertex colours and no
  // lighting, so a one-colour band renders as a flat silhouette and any relief
  // in it is invisible — a 0.6 mm zigzag on a 45 mm radius is under two pixels
  // at normal zoom. The overhang map shows such a pattern only by accident,
  // because bulging also changes the local overhang angle; this measures the
  // relief itself.
  //
  // Assumes a solid of revolution, which every design in this repo is. On a
  // square part the corners would read as "relief" — they are, radially.
  // Sobre papel claro todo lo que pinta la PIEZA tiene que ser oscuro. El
  // neutro es el que más importa y el que más fácil se escapa: si el "sin
  // relieve" es claro, una pieza lisa —que es casi toda la superficie— se
  // vuelve invisible contra el fondo, y lo poco que se ve son los extremos.
  const RELIEF_IN = [0x0e, 0x6f, 0x84];   // hacia adentro
  const RELIEF_FLAT = [0x5a, 0x63, 0x78]; // sin relieve
  const RELIEF_OUT = [0xc2, 0x41, 0x0c];  // hacia afuera

  // Centro y radio de cada capa, por ajuste de circunferencia.
  //
  // Lo usan dos cosas distintas —el mapa de relieve y el picking del esculpido—
  // y las dos dependen de que el centro esté bien: un error `e` inyecta una
  // desviación falsa de e·cos(angulo), o sea una senoide de vuelta entera. Ver
  // el comentario largo en computeRelief para los cuatro estimadores medidos.
  function ajusteDeCapas(V, ext, layerAt, layers, desde) {
    const n = ext.length;
    const ini = desde || 0;
    const centros = new Float64Array(layers * 2);
    const cuenta = new Float64Array(layers);
    {
      // Sumas para el ajuste algebraico (Kåsa): minimiza (x²+y² + Dx + Ey + F)².
      const A = new Float64Array(layers * 8); // Sx Sy Sxx Syy Sxy Sxz Syz Sz
      for (let i = ini; i < n; i++) {
        if (!ext[i]) continue;
        const o = i * 6, l = layerAt[i] * 8;
        const x = (V[o] + V[o + 3]) / 2, y = (V[o + 1] + V[o + 4]) / 2;
        const z = x * x + y * y;
        A[l] += x; A[l + 1] += y; A[l + 2] += x * x; A[l + 3] += y * y;
        A[l + 4] += x * y; A[l + 5] += x * z; A[l + 6] += y * z; A[l + 7] += z;
        cuenta[layerAt[i]]++;
      }
      for (let l = 0; l < layers; l++) {
        const k = l * 8, m = cuenta[l];
        if (m < 8) continue;
        // sistema 3x3 por eliminación de Gauss con pivoteo parcial
        const M = [[A[k + 2], A[k + 4], A[k]], [A[k + 4], A[k + 3], A[k + 1]], [A[k], A[k + 1], m]];
        const v = [-A[k + 5], -A[k + 6], -A[k + 7]];
        let ok = true;
        for (let i = 0; i < 3 && ok; i++) {
          let piv = i;
          for (let r = i + 1; r < 3; r++) if (Math.abs(M[r][i]) > Math.abs(M[piv][i])) piv = r;
          if (Math.abs(M[piv][i]) < 1e-9) { ok = false; break; }
          [M[i], M[piv]] = [M[piv], M[i]]; [v[i], v[piv]] = [v[piv], v[i]];
          for (let r = i + 1; r < 3; r++) {
            const f = M[r][i] / M[i][i];
            for (let c = i; c < 3; c++) M[r][c] -= f * M[i][c];
            v[r] -= f * v[i];
          }
        }
        let cx = A[k] / m, cy = A[k + 1] / m; // si el ajuste falla, el centroide
        if (ok) {
          const sol = [0, 0, 0];
          for (let i = 2; i >= 0; i--) {
            let t = v[i];
            for (let j = i + 1; j < 3; j++) t -= M[i][j] * sol[j];
            sol[i] = t / M[i][i];
          }
          // Una capa MACIZA (el fondo de un bowl es una espiral que barre todo
          // el disco) no es una circunferencia y el ajuste se va lejos. Se
          // descarta comparándolo con el centroide.
          const fx = -sol[0] / 2, fy = -sol[1] / 2;
          if (isFinite(fx) && isFinite(fy) && Math.hypot(fx - cx, fy - cy) < 5) { cx = fx; cy = fy; }
        }
        centros[l * 2] = cx; centros[l * 2 + 1] = cy;
      }
    }

    // Radio de cada segmento contra el centro de SU capa, y radio medio de la capa.
    const rad = new Float64Array(n);
    const suma = new Float64Array(layers);
    const suma2 = new Float64Array(layers);
    for (let i = ini; i < n; i++) {
      if (!ext[i]) continue;
      const o = i * 6, l = layerAt[i];
      const mx = (V[o] + V[o + 3]) / 2, my = (V[o + 1] + V[o + 4]) / 2;
      rad[i] = Math.hypot(mx - centros[l * 2], my - centros[l * 2 + 1]);
      suma[l] += rad[i];
      suma2[l] += rad[i] * rad[i];
    }
    return { centros, cuenta, rad, suma, suma2 };
  }

  function computeRelief(V, ext, layerAt, layers, travelCol, desde) {
    const n = ext.length;
    const colors = new Float32Array(n * 6);

    // The centre is fitted PER LAYER, by least squares, and getting this right
    // is the whole difference between the map working and not working. The
    // relief we are trying to show is 0.6 mm on a 45 mm radius, so an error e
    // in the centre injects a fake deviation of e·cos(angle) — a full-circle
    // sinusoid that reads as vertical stripes. Measured on this part, worst
    // error left on a wall that is provably round (44.999..44.999 mm):
    //
    //     extrusionCentre() (median, whole part)   0.53 mm  -> drew stripes
    //     centroid of the layer                    0.19 mm  -> pattern washed out
    //     median of the layer                      0.41 mm
    //     least-squares circle fit                 0.006 mm
    //
    // The averages fail because a drawing is not distributed symmetrically
    // around the axis: two different faces at 0° and 180° do not cancel. The
    // fit does not care where the points sit, only that they lie on a circle.
    const ini = desde || 0;
    const { centros, cuenta, rad, suma } = ajusteDeCapas(V, ext, layerAt, layers, ini);

    // La referencia contra la que se mide el relieve es la MEDIA MÓVIL del
    // radio a lo largo del recorrido, no el radio medio de la capa.
    //
    // La media por capa supone una pared más o menos vertical. En una cúpula
    // una franja de Z abarca medio casquete —radios de 20 a 88 mm— y en un
    // piso anular una sola capa va de 17 a 58: el "relieve" pasa a ser "dónde
    // estoy en la cúpula" y el mapa se llena de lóbulos naranjas y celestes que
    // no son relieve de nada. La media móvil sigue la forma sea cual sea, así
    // que lo que queda es la desviación local, que es lo que la palabra dice.
    const VENTANA = Math.max(24, Math.min(2000, Math.round(n / Math.max(1, layers))));
    const ref = new Float64Array(n);
    {
      const acum = new Float64Array(n + 1);
      const cnt = new Float64Array(n + 1);
      for (let i = 0; i < n; i++) {
        const vale = ext[i] && i >= ini && cuenta[layerAt[i]] ? 1 : 0;
        acum[i + 1] = acum[i] + (vale ? rad[i] : 0);
        cnt[i + 1] = cnt[i] + vale;
      }
      const h = VENTANA >> 1;
      for (let i = 0; i < n; i++) {
        const a = Math.max(0, i - h), b = Math.min(n, i + h + 1);
        const m = cnt[b] - cnt[a];
        ref[i] = m > 0 ? (acum[b] - acum[a]) / m : rad[i];
      }
    }

    // The scale has to come from the WALL, and a percentile over all segments
    // does not: a solid base is an Archimedean spiral whose radius sweeps from
    // 0 to the full radius, so it alone produced a ±11.93 mm scale on a part
    // whose pattern is 0.6 mm — every wall segment then rendered as flat grey.
    //
    // So: reduce each layer to its own p98 first, then take a percentile ACROSS
    // LAYERS. A solid base is one layer out of hundreds and cannot move that.
    // p75 and not the median, because half the layers here are deliberately
    // smooth (the pattern alternates) and the median would land between the two
    // populations, washing the textured layers out to half intensity.
    // Una capa MACIZA —el piso anular barre de r=17 a r=58— desvía decenas de
    // milímetros respecto de cualquier referencia local, y con eso fijaba la
    // escala de toda la pieza: ±32.89 mm en una pared que no tiene relieve.
    // Se detecta por tener muchísimos más segmentos que una vuelta normal.
    const porSegmentoCapa = new Float64Array(layers);
    for (let i = ini; i < n; i++) if (ext[i]) porSegmentoCapa[layerAt[i]]++;
    const cuentas = [...porSegmentoCapa].filter((c) => c > 0).sort((a, b) => a - b);
    const medianaSegs = cuentas.length ? cuentas[cuentas.length >> 1] : 0;
    const esMaciza = (l) => medianaSegs > 0 && porSegmentoCapa[l] > 4 * medianaSegs;

    const porCapa = [];
    for (let l = 0; l < layers; l++) porCapa.push([]);
    const paso = Math.max(1, Math.floor(n / 40000));
    for (let i = 0; i < n; i += paso) {
      if (!ext[i] || !cuenta[layerAt[i]] || esMaciza(layerAt[i])) continue;
      porCapa[layerAt[i]].push(Math.abs(rad[i] - ref[i]));
    }
    // Per layer take the MAX, not a percentile. A line drawing is sparse — the
    // two faces here cover 5.7 % of their own bounding box, so barely 4 % of a
    // layer's points sit on the pattern at all. A p98 inside the layer lands
    // right at that boundary and read 0.30 mm for a 0.60 mm pattern, halving
    // the contrast. The max is the amplitude, which is what we want to show;
    // the p75 ACROSS layers below is what keeps one odd layer from setting it.
    const picos = [];
    for (const d of porCapa) {
      if (d.length < 4) continue;
      let mx = 0;
      for (const v of d) if (v > mx) mx = v;
      picos.push(mx);
    }
    picos.sort((x, y) => x - y);
    // Piso absoluto. En una pieza lisa la desviación real son micrones, y una
    // escala de micrones convierte el ruido de coma flotante en contraste a
    // pleno color: degradados naranjas y celestes donde no hay relieve ninguno.
    // Por debajo de esto la pieza se declara lisa y se pinta plana, que es la
    // respuesta honesta.
    const RELIEVE_MINIMO = 0.02;   // mm
    const bruto = picos.length ? picos[Math.floor(picos.length * 0.75)] : 0;
    const escala = Math.max(RELIEVE_MINIMO, bruto);

    for (let i = 0; i < n; i++) {
      const o = i * 6;
      let r0, g0, b0;
      if (!ext[i] || !cuenta[layerAt[i]] || i < ini) {
        r0 = travelCol.r; g0 = travelCol.g; b0 = travelCol.b;
      } else {
        const d = (rad[i] - ref[i]) / escala;
        const k = Math.max(-1, Math.min(1, d));
        const dest = k >= 0 ? RELIEF_OUT : RELIEF_IN;
        const t = Math.abs(k);
        r0 = (RELIEF_FLAT[0] + (dest[0] - RELIEF_FLAT[0]) * t) / 255;
        g0 = (RELIEF_FLAT[1] + (dest[1] - RELIEF_FLAT[1]) * t) / 255;
        b0 = (RELIEF_FLAT[2] + (dest[2] - RELIEF_FLAT[2]) * t) / 255;
      }
      colors[o] = r0; colors[o + 1] = g0; colors[o + 2] = b0;
      colors[o + 3] = r0; colors[o + 4] = g0; colors[o + 5] = b0;
    }
    // Los intermedios quedan a mano para repintar el relieve mientras se
    // esculpe. Recalcularlos enteros por frame sería otro ajuste de
    // circunferencia por capa; lo único que cambia al deformar es el radio.
    relieveVivo = { rad, cuenta, ref, escala, ini, ventana: VENTANA };
    return { colors, escala };
  }

  // --- Solid render ---------------------------------------------------------
  // Draws every extrusion as a ribbon one layer height tall instead of a
  // hairline, so the wall reads as a surface and the relief becomes visible.
  //
  // Why it earns its triangles: a line has no thickness at any zoom, so a
  // 0.25 mm zigzag or a 3 mm dimple is invisible in the line view no matter how
  // close you get — which is the whole reason the relief map had to exist. Here
  // the geometry is the real size and a light does the rest.
  //
  // In vase mode a ribbon per segment tiles into a continuous wall, because the
  // path IS the wall. On a normally-sliced part it shows stacked ribbons with
  // gaps between them, which is also the truth.
  //
  // Non-indexed, 6 vertices per segment: costs memory but keeps the buffer in
  // the same order as the line buffer, so the timelapse draw range is just
  // `revealed · 6` and every colour mode carries over unchanged.
  function buildSolid(V, ext, segZ, layerH, cx, cy) {
    let n = 0;
    for (let i = 0; i < ext.length; i++) if (ext[i]) n++;
    const pos = new Float32Array(n * 18);
    const nor = new Float32Array(n * 18);
    const mapa = new Int32Array(n * 6);
    const h = Math.max(0.05, layerH) / 2;
    let v = 0, k = 0;
    for (let i = 0; i < ext.length; i++) {
      if (!ext[i]) continue;
      const o = i * 6;
      const x1 = V[o], y1 = V[o + 1], x2 = V[o + 3], y2 = V[o + 4];
      const z = segZ[i];
      let dx = x2 - x1, dy = y2 - y1;
      const L = Math.hypot(dx, dy) || 1;
      dx /= L; dy /= L;
      // Normal horizontal, perpendicular al segmento, apuntando hacia AFUERA.
      let nx = -dy, ny = dx;
      if ((x1 - cx) * nx + (y1 - cy) * ny < 0) { nx = -nx; ny = -ny; }
      const a = [x1, y1, z - h], b = [x2, y2, z - h];
      const c = [x2, y2, z + h], d = [x1, y1, z + h];
      for (const q of [a, b, c, a, c, d]) {
        pos[v] = q[0]; pos[v + 1] = q[1]; pos[v + 2] = q[2];
        nor[v] = nx; nor[v + 1] = ny; nor[v + 2] = 0;
        v += 3;
      }
      for (let j = 0; j < 6; j++) mapa[k * 6 + j] = i;
      k++;
    }
    return { pos, nor, mapa, segmentos: n };
  }

  // Expande el color por segmento (2 vértices) al color por triángulo (6).
  function coloresSolidos(src, mapa) {
    const out = new Float32Array(mapa.length * 3);
    for (let i = 0; i < mapa.length; i++) {
      const o = mapa[i] * 6, q = i * 3;
      out[q] = src[o]; out[q + 1] = src[o + 1]; out[q + 2] = src[o + 2];
    }
    return out;
  }

  // --- Timelapse state ------------------------------------------------------
  let lineGeom = null;      // the single ordered LineSegments geometry
  let totalSegs = 0;        // number of drawable segments
  let revealed = 0;         // how many segments are currently shown
  let playing = false;
  let segMeta = null;       // { layerAt, layerZ, layers, segsUpToLayer }
  let segExt = [];          // segment index -> 1 if it extrudes

  const timebar = document.getElementById('timebar');
  const playBtn = document.getElementById('play');
  const playIcon = document.getElementById('play-icon');
  const scrub = document.getElementById('scrub');
  const tlabel = document.getElementById('tlabel');

  const layerbar = document.getElementById('layerbar');
  const layerSlider = document.getElementById('layer');
  const layerTop = document.getElementById('layer-top');
  const layerBot = document.getElementById('layer-bot');

  const modeBtn = document.getElementById('modeBtn');
  const travelBtn = document.getElementById('travelBtn');
  const solidBtn = document.getElementById('solidBtn');
  const legendFan = document.getElementById('legend-fan');
  const legendOvh = document.getElementById('legend-ovh');
  const legendSol = document.getElementById('legend-sol');
  const legendVel = document.getElementById('legend-vel');
  const legendFil = document.getElementById('legend-fil');
  const legendRel = document.getElementById('legend-rel');
  const legendBleed = document.getElementById('legend-bleed');

  // Color mode: 'fan', 'overhang' or 'filament'. All three colour arrays are
  // precomputed on load, so switching is a buffer copy and stays instant on a
  // 50k-segment lamp.
  const MODES = ['fan', 'overhang', 'solape', 'velocidad', 'filament', 'bleed', 'relief'];
  let colorMode = 'fan';
  let fanColors = null;
  let overhangColors = null;
  let solapeColors = null;
  let velColors = null;
  let velRango = [0, 0];
  let peorSolape = 1;
  let filamentColors = null;
  let bleedColors = null;
  let bleedDirty = 0;
  let reliefColors = null;
  let reliefScale = 0;
  let maxOverhang = 0;
  let baseInfo = '';
  let tiempo = null;        // { total, porSeg, acum, pausas } — estimación en segundos
  let encuadradoPara = null;  // ruta del archivo que la cámara ya encuadró
  // Hiding travel moves. The segments stay in the buffer — the timelapse and the
  // layer slider index into it, so removing them would renumber everything — and
  // are collapsed to zero length instead, which the LINES primitive rasterises
  // to nothing. `basePos` keeps the real coordinates so it is reversible.
  let hideTravel = false;
  let basePos = null;
  let solidMesh = null;
  let solidMapa = null;
  let solidObj = false;
  let filChanges = [];      // resolved change list, in print order
  let slotsUsed = [];       // slots the print actually loads, ascending
  let changeMarkers = null; // THREE.Group of markers, only shown in filament mode

  const ICON_PLAY = 'M8 5v14l11-7z';
  const ICON_PAUSE = 'M6 5h4v14H6zm8 0h4v14h-4z';

  // Todo lo que mueve vértices pasa por acá, y siempre partiendo de `basePos`.
  // Son dos cosas que se pisan —esconder viajes colapsa segmentos, el esculpido
  // en vivo corre radios— y cada una escribiendo por su cuenta sobre el mismo
  // buffer se borraban entre sí: esconder los viajes deshacía la deformación.
  function repintarGeometria() {
    if (!lineGeom || !basePos) return;
    const pos = lineGeom.getAttribute('position');
    const a = pos.array;
    a.set(basePos);
    const d = deformarEnVivo(a);
    // El sólido no se deforma, así que volver a mostrarlo con un trazo todavía
    // sin hornear sería exactamente el salto que se está evitando. Vuelve recién
    // cuando la resta llegó a cero, o sea cuando el g-code ya lo trae.
    if (!d && solidoAntes) { solidoAntes = null; solidObj = true; applySolid(); }
    // El relieve mide el radio contra el radio medio de su capa, así que
    // deformar lo cambia. Se repinta con el MISMO desplazamiento que ya se
    // calculó para mover los vértices: evaluar el campo dos veces por frame
    // costaría el doble y daría exactamente lo mismo.
    recolorearRelieve(d);
    if (hideTravel) {
      for (let i = 0; i < segExt.length; i++) {
        if (segExt[i]) continue;
        const o = i * 6;
        a[o + 3] = a[o]; a[o + 4] = a[o + 1]; a[o + 5] = a[o + 2];
      }
    }
    pos.needsUpdate = true;
  }

  function applyTravel() {
    repintarGeometria();
    if (travelBtn) travelBtn.textContent = hideTravel ? 'Travel: hidden' : 'Travel: shown';
  }

  function applySolid() {
    if (printGroup) {
      const lineas = printGroup.children.find((o) => o.type === 'LineSegments');
      if (lineas) lineas.visible = !(solidObj && solidMesh);
    }
    if (solidMesh) solidMesh.visible = solidObj;
    if (solidBtn) solidBtn.textContent = solidObj ? 'Render: solid' : 'Render: lines';
    setRevealed(revealed);
  }

  function applyColorMode() {
    if (lineGeom) {
      const src = colorMode === 'overhang' ? overhangColors
        : colorMode === 'solape' ? solapeColors
        : colorMode === 'velocidad' ? velColors
        : colorMode === 'filament' ? filamentColors
        : colorMode === 'bleed' ? bleedColors
        : colorMode === 'relief' ? reliefColors
        : fanColors;
      if (src) {
        lineGeom.getAttribute('color').copyArray(src);
        lineGeom.getAttribute('color').needsUpdate = true;
        if (solidMesh && solidMapa) {
          solidMesh.geometry.getAttribute('color').copyArray(coloresSolidos(src, solidMapa));
          solidMesh.geometry.getAttribute('color').needsUpdate = true;
        }
      }
    }
    if (legendFan) legendFan.style.display = colorMode === 'fan' ? '' : 'none';
    if (legendOvh) legendOvh.style.display = colorMode === 'overhang' ? '' : 'none';
    if (legendSol) legendSol.style.display = colorMode === 'solape' ? '' : 'none';
    if (legendVel) {
      legendVel.style.display = colorMode === 'velocidad' ? '' : 'none';
      if (colorMode === 'velocidad') buildVelLegend();
    }
    if (legendFil) legendFil.style.display = colorMode === 'filament' ? '' : 'none';
    if (legendRel) legendRel.style.display = colorMode === 'relief' ? '' : 'none';
    if (legendBleed) legendBleed.style.display = colorMode === 'bleed' ? '' : 'none';
    if (changeMarkers) changeMarkers.visible = colorMode === 'filament';
    if (modeBtn) {
      modeBtn.textContent = 'Color: ' + colorMode[0].toUpperCase() + colorMode.slice(1);
    }
    updateHud();
  }

  // La leyenda dice mm/s, no "lento" y "rápido". Un número se compara con el
  // de otra pieza; un adjetivo no: esta cabeza va a 20 mm/s, el Squeezy a 8 y
  // el jarrón de referencia a 15, y eso solo se ve si están los números.
  function buildVelLegend() {
    if (!legendVel) return;
    const [lo, hi, plano] = velRango;
    if (plano) {
      legendVel.innerHTML =
        `<div>velocidad real (con aceleración y jerk)</div>` +
        `<div><span class="sw" style="background:${velHex(0.5)}"></span>` +
        `${hi.toFixed(1)} mm/s en toda la pieza</div>`;
      return;
    }
    const filas = [0, 0.25, 0.5, 0.75, 1].map((t) => {
      const v = lo + (hi - lo) * t;
      return `<div><span class="sw" style="background:${velHex(t)}"></span>` +
             `${v.toFixed(v < 10 ? 1 : 0)} mm/s</div>`;
    });
    legendVel.innerHTML = `<div>velocidad real (con aceleración y jerk)</div>` + filas.join('');
  }

  // One legend row per slot the print loads, plus the change heights. Built
  // from the file, not hardcoded: a single-filament print gets no rows at all.
  function buildFilamentLegend() {
    if (!legendFil) return;
    if (!slotsUsed.length) {
      legendFil.innerHTML = '<div>no filament changes in this file</div>';
      return;
    }
    const rows = slotsUsed.map(
      (b) => `<div><span class="sw" style="background:${bandHex(b)}"></span>${bandLabel(b)}</div>`
    );
    rows.push(`<div><span class="sw" style="background:${TRAVEL_HEX}"></span>travel move</div>`);
    // A gradient is 40+ changes and listing them all buried the legend and the
    // model behind it. Past a handful, the count and the range are the useful
    // facts; the individual heights are not.
    const MAX = 5;
    if (filChanges.length <= MAX) {
      for (const c of filChanges) {
        const z = c.resumed ? `Z${c.z.toFixed(1)}` : 'never resumes';
        const como = c.kind === 'manual' ? 'pause' : 'AMS';
        rows.push(`<div style="opacity:.75">${como} → ${bandLabel(c.to).split(' (')[0]} at ${z}</div>`);
      }
    } else {
      const zs = filChanges.filter((c) => c.resumed).map((c) => c.z);
      const desde = Math.min(...zs), hasta = Math.max(...zs);
      rows.push(
        `<div style="opacity:.75">${filChanges.length} changes, Z${desde.toFixed(1)}–${hasta.toFixed(1)}</div>`
      );
    }
    legendFil.innerHTML = rows.join('');
  }

  // main.js and the host's HTML are loaded by two different mechanisms: the
  // HTML is built by src/extension.ts and read once when the extension host
  // starts, while this file is re-read every time the panel is created. So they
  // can drift — a new main.js running against yesterday's HTML — and the only
  // symptom is a control silently missing, which reads as "the extension did not
  // update" and sends you reinstalling. This file knows which elements it
  // expects, so it can just say so.
  const ESPERADOS = ['modeBtn', 'travelBtn', 'legend-fil', 'legend-rel', 'legend-bleed',
                     'escBtn', 'esculpir', 'esc-lista', 'plantilla',
                     'cota-alto', 'cota-ancho', 'cargando', 'esc-titulo', 'esc-gesto', 'legend-sol', 'legend-vel'];
  const faltantes = ESPERADOS.filter((id) => !document.getElementById(id));

  function updateHud() {
    let s = baseInfo;
    if (faltantes.length) {
      s += `  ·  ⚠ host HTML is stale (missing ${faltantes.join(', ')}) — ` +
           `run "Developer: Reload Window"`;
    }
    if (colorMode === 'overhang' && overhangColors) {
      const risk = maxOverhang >= OVH_FAIL ? '⚠ likely fails' : maxOverhang >= OVH_WARN ? 'risky' : 'ok';
      s += `  ·  max overhang ${maxOverhang.toFixed(0)}° (${risk})`;
    }
    if (colorMode === 'bleed' && bleedColors) {
      s += `  ·  ${(bleedDirty * 100).toFixed(0)}% of the print is still mixing` +
           `  (transition ≈ ${(BLEED_L * 3).toFixed(0)} mm of filament)`;
    }
    if (colorMode === 'velocidad' && velColors) {
      s += velRango[2]
        ? `  ·  velocidad constante, ${velRango[1].toFixed(1)} mm/s reales en toda la pieza`
        : `  ·  ${velRango[0].toFixed(0)}–${velRango[1].toFixed(0)} mm/s reales` +
          ` (lo pedido y lo que la máquina alcanza no es lo mismo)`;
    }
    if (colorMode === 'solape' && solapeColors) {
      const pct = peorSolape * 100;
      const juicio = pct <= 0 ? '⚠ hay vueltas que no se tocan'
        : pct < 25 ? '⚠ no esperes que salga'
        : pct < 50 ? 'justo: bajá la velocidad ahí' : 'ok';
      s += `  ·  solape mínimo ${pct.toFixed(0)}% del cordón (${juicio})`;
    }
    if (colorMode === 'relief' && reliefColors) {
      s += `  ·  relief ±${reliefScale.toFixed(2)} mm from the layer's mean radius`;
    }
    if (colorMode === 'filament') {
      const ams = filChanges.filter((c) => c.kind === 'ams').length;
      const man = filChanges.length - ams;
      s += filChanges.length
        ? `  ·  ${filChanges.length} filament change${filChanges.length > 1 ? 's' : ''}` +
          ` (${ams} AMS, ${man} manual)`
        : '  ·  single filament, no changes';
    }
    hud.textContent = s;
  }

  if (solidBtn) {
    solidBtn.addEventListener('click', () => { solidObj = !solidObj; applySolid(); });
  }

  if (travelBtn) {
    travelBtn.addEventListener('click', () => {
      hideTravel = !hideTravel;
      applyTravel();
    applySolid();
    });
  }

  if (modeBtn) {
    modeBtn.addEventListener('click', () => {
      colorMode = MODES[(MODES.indexOf(colorMode) + 1) % MODES.length];
      applyColorMode();
    });
  }

  // Reveal roughly the whole model in ~8s regardless of size; feels timelapse-y.
  function segsPerFrame() {
    return Math.max(1, Math.ceil(totalSegs / (8 * 60)));
  }

  function currentLayer() {
    if (!segMeta || !segMeta.layerAt.length) return 1;
    const idx = Math.max(0, Math.min(revealed - 1, segMeta.layerAt.length - 1));
    return segMeta.layerAt[idx] + 1; // 1-based
  }

  function setRevealed(n) {
    revealed = Math.max(0, Math.min(totalSegs, n | 0));
    if (lineGeom) lineGeom.setDrawRange(0, revealed * 2);
    if (solidMesh) {
      // El sólido solo tiene los segmentos que EXTRUYEN, así que su índice no
      // es el mismo que el de las líneas: hay que traducir cuántos de los
      // revelados extruían.
      let hasta = 0;
      for (let i = 0; i < revealed && i < segExt.length; i++) if (segExt[i]) hasta++;
      solidMesh.geometry.setDrawRange(0, hasta * 6);
    }
    scrub.value = String(revealed);
    if (segMeta) layerSlider.value = String(currentLayer());
    updateLabel();
  }

  // Reveal every segment up to and including layer L (1-based).
  function revealToLayer(L) {
    if (!segMeta) return;
    const l = Math.max(1, Math.min(segMeta.layers, L | 0));
    setRevealed(segMeta.segsUpToLayer[l - 1]);
  }

  function updateLabel() {
    if (!segMeta) { tlabel.textContent = ''; return; }
    const reloj_ = tiempo
      ? `  ${relojCorto(tiempo.acum[Math.min(revealed, tiempo.acum.length - 1)])} / ${relojCorto(tiempo.total)}`
      : '';
    tlabel.textContent = `L${currentLayer()}/${segMeta.layers}  ${revealed}/${totalSegs}${reloj_}`;
  }

  function setPlaying(on) {
    playing = on && revealed < totalSegs;
    playIcon.setAttribute('d', playing ? ICON_PAUSE : ICON_PLAY);
  }

  playBtn.addEventListener('click', () => {
    if (playing) { setPlaying(false); return; }
    if (revealed >= totalSegs) setRevealed(0); // replay from start
    setPlaying(true);
  });

  scrub.addEventListener('input', () => {
    setPlaying(false);
    setRevealed(parseInt(scrub.value, 10));
  });

  layerSlider.addEventListener('input', () => {
    setPlaying(false);
    revealToLayer(parseInt(layerSlider.value, 10));
  });

  window.addEventListener('keydown', (e) => {
    if (e.code === 'KeyS' && totalSegs > 0) {
      solidObj = !solidObj;
      applySolid();
      return;
    }
    if (e.code === 'KeyT' && totalSegs > 0) {
      hideTravel = !hideTravel;
      applyTravel();
      return;
    }
    if (e.code === 'Space' && totalSegs > 0) {
      e.preventDefault();
      playBtn.click();
    }
  });


  // --- cotas ----------------------------------------------------------------
  // Las medidas de la pieza dibujadas como en un plano: una línea de cota con
  // sus marcas en los extremos y sus líneas de referencia saliendo del objeto.
  //
  // Se rearman en cada frame y no una sola vez, porque una cota tiene que estar
  // SIEMPRE de frente: dibujada en un plano fijo del mundo, media órbita
  // después queda de canto y no se lee. El truco es armarlas en la base
  // {u = derecha de la pantalla proyectada al piso, w = Z de la máquina}, que
  // es la misma orientación que tendría un alzado del objeto.
  let cotas = null;
  let medidas = null;          // { sx, sy, sz, zAncho }
  const cotaAltoTxt = document.getElementById('cota-alto');
  const cotaAnchoTxt = document.getElementById('cota-ancho');

  const MARGEN = 14;           // separación entre la pieza y la línea de cota
  const MARCA = 5;             // largo de las marcas de los extremos

  function crearCotas() {
    const geo = new THREE.BufferGeometry();
    // 10 segmentos: línea + 2 marcas + 2 referencias, por cada una de las dos cotas
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(10 * 2 * 3), 3));
    cotas = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0x5d729b }));
    cotas.frustumCulled = false;
    scene.add(cotas);
  }

  function actualizarCotas() {
    if (!cotas) crearCotas();
    const hay = !!medidas && medidas.sz > 0;
    cotas.visible = hay;
    if (cotaAltoTxt) cotaAltoTxt.classList.toggle('hidden', !hay);
    if (cotaAnchoTxt) cotaAnchoTxt.classList.toggle('hidden', !hay);
    if (!hay) return;

    // u = hacia la derecha de la pantalla, aplastado contra el piso; si la
    // cámara mira casi desde arriba, esa proyección se degenera y se usa la
    // dirección "arriba de la pantalla" como respaldo.
    const u = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
    u.z = 0;
    if (u.lengthSq() < 1e-6) u.setFromMatrixColumn(camera.matrixWorld, 1).setZ(0);
    u.normalize();

    const { sx, sy, sz, zAncho } = medidas;
    const R = Math.max(sx, sy) / 2, H = sz / 2;
    const dAlto = R + MARGEN, zBase = -H - MARGEN;
    const P = [];
    const p = (a, b) => new THREE.Vector3(u.x * a, u.y * a, b);

    // Cota de alto: vertical, al costado.
    P.push(p(dAlto, -H), p(dAlto, H));
    for (const z of [-H, H]) {
      P.push(p(dAlto - MARCA, z), p(dAlto + MARCA, z));   // marca del extremo
      P.push(p(R + 2, z), p(dAlto + MARCA, z));           // línea de referencia
    }

    // Cota de ancho: horizontal, debajo. Las referencias bajan desde la altura
    // donde la pieza REALMENTE es más ancha —en un jarrón con vuelo eso es
    // arriba, no en la base—, que es lo que hace que la cota diga de dónde sale.
    P.push(p(-R, zBase), p(R, zBase));
    for (const x of [-R, R]) {
      P.push(p(x, zBase - MARCA), p(x, zBase + MARCA));
      P.push(p(x, zAncho), p(x, zBase - MARCA));
    }

    const arr = cotas.geometry.attributes.position.array;
    for (let i = 0; i < P.length; i++) {
      arr[i * 3] = P[i].x; arr[i * 3 + 1] = P[i].y; arr[i * 3 + 2] = P[i].z;
    }
    cotas.geometry.attributes.position.needsUpdate = true;

    const r = renderer.domElement.getBoundingClientRect();
    const pegar = (el, v, texto) => {
      if (!el) return;
      const q = v.clone().project(camera);
      el.style.left = `${r.left + (q.x * 0.5 + 0.5) * r.width}px`;
      el.style.top = `${r.top + (-q.y * 0.5 + 0.5) * r.height}px`;
      el.textContent = texto;
    };
    // Ø y no "ancho" cuando la pieza es de revolución, que es lo que dice de
    // verdad la medida. Se comprueba comparando los dos lados de la caja en vez
    // de suponerlo: un 2% de diferencia ya no es un círculo.
    const redondo = Math.abs(sx - sy) < 0.02 * Math.max(sx, sy);
    pegar(cotaAltoTxt, p(dAlto + MARCA + 6, 0), `↕ ${sz.toFixed(1)} mm`);
    pegar(cotaAnchoTxt, p(0, zBase - MARCA - 6),
          `${redondo ? 'Ø' : '↔'} ${Math.max(sx, sy).toFixed(1)} mm`);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (playing) {
      setRevealed(revealed + segsPerFrame());
      if (revealed >= totalSegs) setPlaying(false);
    }
    controls.update();
    actualizarCotas();
    renderer.render(scene, camera);
  }
  animate();

  function rebuild(text, ruta) {
    const t0 = performance.now();
    const { V, C, ext, segZ, segBand, segE, segV, segA, changes, bbox, segObjeto } = parse(text);
    tiempo = estimarTiempo(V, segV, segA, changes);
    const travelCol = new THREE.Color(TRAVEL_COL);

    if (printGroup) {
      scene.remove(printGroup);
      printGroup.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) o.material.dispose();
      });
    }
    printGroup = new THREE.Group();
    lineGeom = null;
    changeMarkers = null;
    totalSegs = V.length / 6;

    // Filament changes: resolve each to where printing resumes, and note which
    // slots the file actually loads (slot 0 counts only if something extrudes
    // on it, so a single-filament file reports no changes rather than "A1").
    filChanges = resolveChanges(changes, V, ext);
    const vistos = new Set();
    for (let i = 0; i < ext.length; i++) if (ext[i]) vistos.add(segBand[i]);
    slotsUsed = [...vistos].sort((a, b) => a - b);

    // Bin segments into layers by real Z (robust for planar and vase spirals).
    const layerH = estimateLayerHeight(V, ext, bbox);
    const layers = totalSegs > 0
      ? Math.max(1, Math.round((bbox.maxz - bbox.minz) / layerH) + 1)
      : 0;
    const layerAt = new Array(totalSegs);
    const layerZ = new Array(layers);
    for (let s = 0; s < totalSegs; s++) {
      let l = Math.round((segZ[s] - bbox.minz) / layerH);
      if (l < 0) l = 0; else if (l >= layers) l = layers - 1;
      layerAt[s] = l;
      layerZ[l] = segZ[s];
    }

    // Prefix sum: segsUpToLayer[l] = # of segments in layers 0..l (inclusive).
    const segsUpToLayer = new Array(layers).fill(0);
    for (let i = 0; i < layerAt.length; i++) segsUpToLayer[layerAt[i]]++;
    for (let l = 1; l < layers; l++) segsUpToLayer[l] += segsUpToLayer[l - 1];
    segMeta = { layerAt, layerZ, layers, segsUpToLayer };
    construirCascara(V, ext, segMeta, bbox, segObjeto);

    // Precompute both color schemes: fan (from parse) and overhang heat map.
    fanColors = new Float32Array(C);
    if (V.length) {
      const ovh = computeOverhang(V, ext, segZ, layerH, bbox, travelCol);
      overhangColors = ovh.colors;
      maxOverhang = ovh.maxDeg;
      solapeColors = ovh.solape;
      peorSolape = ovh.peorSolape;
      const vel = coloresVelocidad(V, ext, tiempo.porSeg, travelCol);
      velColors = vel.colors;
      velRango = [vel.lo, vel.hi, vel.plano];
      filamentColors = computeFilamentColors(V, ext, segBand, travelCol);
      bleedColors = computeBleedColors(ext, segBand, segE, travelCol);
      bleedDirty = bleedStats(ext, segBand, bleedColors);
      const rel = computeRelief(V, ext, layerAt, layers, travelCol, segObjeto);
      reliefColors = rel.colors;
      reliefScale = rel.escala;
    } else {
      overhangColors = null;
      maxOverhang = 0;
      solapeColors = null;
      peorSolape = 1;
      velColors = null;
      filamentColors = null;
      reliefColors = null;
      reliefScale = 0;
      bleedColors = null;
      bleedDirty = 0;
    }

    segExt = ext;
    if (V.length) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(V, 3));
      basePos = Float32Array.from(V);
      const startColors = colorMode === 'overhang' && overhangColors ? overhangColors : fanColors;
      g.setAttribute('color', new THREE.Float32BufferAttribute(startColors.slice(), 3));
      const m = new THREE.LineBasicMaterial({ vertexColors: true });
      printGroup.add(new THREE.LineSegments(g, m));
      lineGeom = g;
    }
    // No markers around the model. A ring per change was drawn here and it was
    // a bad idea: a gradient is dozens of changes, so the part ended up inside
    // a cage of concentric rings wider than itself, hiding the very thing they
    // annotated. The change heights are in the legend, which costs no pixels
    // over the model.
    buildFilamentLegend();

    solidMesh = null; solidMapa = null;
    if (V.length) {
      const [scx, scy] = extrusionCentre(V, ext);
      const sd = buildSolid(V, ext, segZ, layerH, scx, scy);
      if (sd.segmentos) {
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.Float32BufferAttribute(sd.pos, 3));
        g.setAttribute('normal', new THREE.Float32BufferAttribute(sd.nor, 3));
        g.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(sd.mapa.length * 3), 3));
        const m = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide });
        solidMesh = new THREE.Mesh(g, m);
        solidMesh.visible = false;
        solidMapa = sd.mapa;
        printGroup.add(solidMesh);
      }
    }

    scene.add(printGroup);
    if (modeBtn) modeBtn.style.display = totalSegs > 0 ? '' : 'none';
    if (solidBtn) solidBtn.style.display = solidMesh ? '' : 'none';
    if (travelBtn) travelBtn.style.display = totalSegs > 0 ? '' : 'none';
    applyTravel();

    // Timelapse + layer bar setup: start fully revealed, ready to scrub/replay.
    setPlaying(false);
    if (totalSegs > 0) {
      timebar.classList.remove('hidden');
      scrub.max = String(totalSegs);
      layerbar.classList.remove('hidden');
      layerSlider.min = '1';
      layerSlider.max = String(layers);
      const topZ = layerZ[layers - 1];
      layerTop.textContent = `${layers}\n${topZ != null ? topZ.toFixed(2) : ''}`.trim();
      layerBot.textContent = '1';
      setRevealed(totalSegs);
    } else {
      timebar.classList.add('hidden');
      layerbar.classList.add('hidden');
    }

    // Center the model on the origin and frame the camera to fit.
    baseInfo = 'no extrusion moves found';
    medidas = null;
    if (isFinite(bbox.minx)) {
      const cx = (bbox.minx + bbox.maxx) / 2;
      const cy = (bbox.miny + bbox.maxy) / 2;
      const cz = (bbox.minz + bbox.maxz) / 2;
      printGroup.position.set(-cx, -cy, -cz);
      const sx = bbox.maxx - bbox.minx;
      const sy = bbox.maxy - bbox.miny;
      const sz = bbox.maxz - bbox.minz;
      const r = Math.max(sx, sy, sz, 1);
      // Encuadrar solo la primera vez que se ve ESTE archivo. Mover un slider
      // regenera la pieza, y volver a encuadrar ahí le arranca al usuario el
      // punto de vista desde el que estaba mirando justo lo que cambió — que
      // es lo único que importa en ese momento.
      if (ruta !== encuadradoPara) {
        encuadradoPara = ruta;
        controls.target.set(0, 0, 0);
        camera.position.set(r * 1.1, -r * 1.1, r * 0.9);
      }
      // Los planos de recorte sí se rehacen siempre: dependen del tamaño de la
      // pieza, y si crece con un slider se la empieza a comer el plano lejano.
      camera.near = r / 100;
      camera.far = r * 100;
      camera.updateProjectionMatrix();

      // A qué altura la pieza es más ancha. Sale de los anillos de la cáscara y
      // no del bbox, porque el bbox dice CUÁNTO mide pero no DÓNDE, y en un
      // jarrón con vuelo el punto más ancho está arriba, no en la base.
      let zAncho = -sz / 2;
      if (cascara && cascara.anillos.length) {
        let mejor = cascara.anillos[0];
        for (const a of cascara.anillos) if (a.r > mejor.r) mejor = a;
        zAncho = mejor.z - cz;
      }
      medidas = { sx, sy, sz, zAncho };
      const pausas = tiempo && tiempo.pausas
        ? ` + ${tiempo.pausas} manual pause${tiempo.pausas > 1 ? 's' : ''}`
        : '';
      baseInfo =
        `≈ ${reloj(tiempo ? tiempo.total : 0)}${pausas} · ` +
        `${totalSegs} moves · ${layers} layers · ` +
        `bbox ${sx.toFixed(1)}×${sy.toFixed(1)}×${sz.toFixed(1)} mm · ` +
        `parsed in ${(performance.now() - t0).toFixed(0)} ms`;
    }
    applyColorMode();
  }

  // --- Parameter controls ---------------------------------------------------
  // One slider per numeric parameter in the recipe the generator left beside the
  // g-code. Dragging re-runs the generator; it does not edit the g-code.
  //
  // Two things make it usable rather than a slideshow: while the thumb is down
  // we ask for a DRAFT (the extension appends --segmentos 120, 1.8 s instead of
  // 8.6 s), and we only send on 'input' after a short idle, so a drag fires a
  // handful of runs and not one per pixel.
  const params = document.getElementById('params');
  const paramsLista = document.getElementById('params-lista');
  const paramsTit = document.getElementById('params-tit');
  // Se toman acá y no más abajo: `construirParams` los usa, y un `const`
  // declarado después queda en zona muerta cuando llega la primera receta.
  const guardarBtn = document.getElementById('guardarBtn');
  const cargarBtn = document.getElementById('cargarBtn');
  const paramsEstado = document.getElementById('params-estado');
  let receta = null;
  let valores = {};
  let arrastrando = false;
  let temporizador = null;

  // Nada se regenera mientras el dedo está abajo. Antes salía un borrador por
  // cada pausa del arrastre: la pieza parpadeaba entre versiones intermedias
  // que nadie pidió y cada una costaba una corrida de Python, así que el valor
  // final llegaba después de la cola de los que ya no importaban. Ahora el
  // arrastre solo mueve el número y la corrida sale UNA vez, al soltar.
  //
  // La espera larga es para el otro camino: con el teclado o clicando el riel
  // no hay "soltar", y ahí lo que marca el final es que la persona dejó de
  // tocar.
  function pedirRegen(borrador, espera) {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => {
      vscode.postMessage({ type: 'regen', valores, borrador });
    }, espera !== undefined ? espera : 60);
  }

  // Los parámetros vienen de cuatro capas distintas y varias comparten nombre:
  // `amplitud` es la profundidad de las arrugas en la estructura y la altura del
  // diente en el patrón. Sin decir de dónde sale cada uno, el panel muestra dos
  // sliders idénticos y no hay forma de saber cuál es cuál.
  const GRUPOS = {
    '--pe': 'estructura — el cuerpo y las arrugas',
    '--p': 'patrón — la textura de la superficie',
    '--pp': 'pintura — dónde va el segundo color',
    '--ps': 'silueta — el perfil de la pieza'
  };
  const GRUPO_OTROS = 'pieza';

  function construirParams(r) {
    receta = r;
    valores = {};
    if (!params || !paramsLista) return;
    // Sin receta igual se muestra el panel, solo que sin sliders. Abrir en
    // Orca y cargar una versión no necesitan receta para nada — la necesitaba
    // el panel entero por estar todo junto, y eso dejaba sin botón a cualquier
    // pieza generada por fuera de la CLI.
    const sinReceta = !r || !r.controles || !r.controles.length;
    params.classList.remove('hidden');
    if (paramsLista) paramsLista.classList.toggle('hidden', sinReceta);
    // Guardar sí la necesita: copia el .params.json a la carpeta de versiones.
    if (guardarBtn) guardarBtn.classList.toggle('hidden', sinReceta);
    if (paramsTit) paramsTit.textContent = sinReceta ? 'Sin receta' : 'Parameters';
    if (sinReceta) {
      if (paramsLista) paramsLista.innerHTML = '';
      return;
    }
    paramsLista.innerHTML = '';
    // Ordenados por grupo, con un título por grupo.
    const orden = ['--ps', '--pe', '--p', '--pp'];
    const porGrupo = new Map();
    for (const c of r.controles) {
      const g = GRUPOS[c.flag] ? c.flag : '';
      if (!porGrupo.has(g)) porGrupo.set(g, []);
      porGrupo.get(g).push(c);
    }
    const claves = [...porGrupo.keys()].sort(
      (a, b) => (a === '' ? 99 : orden.indexOf(a)) - (b === '' ? 99 : orden.indexOf(b))
    );
    // Cada título va seguido de SUS sliders. Construirlos en dos pasadas —
    // todos los títulos y después todos los sliders — deja los cuatro rótulos
    // amontonados arriba, sin nada debajo, y el agrupamiento no se lee.
    for (const g of claves) {
      const t = document.createElement('div');
      t.className = 'par-grupo';
      t.textContent = g ? GRUPOS[g] : GRUPO_OTROS;
      paramsLista.appendChild(t);
      for (const c of porGrupo.get(g)) paramsLista.appendChild(filaDe(c));
    }
    params.classList.remove('hidden');
  }

  function filaDe(c) {
      const id = c.flag + ':' + c.clave;
      valores[id] = c.valor;
      const fila = document.createElement('div');
      fila.className = 'par';
      const cab = document.createElement('div');
      cab.className = 'par-fila';
      const nom = document.createElement('span');
      nom.textContent = c.clave;
      // La descripción sale del docstring de la función que recibe el parámetro
      // — ver comun.descripciones_de. Escribirla acá otra vez sería una copia
      // que se desincroniza en cuanto alguien toca el Python.
      fila.title = c.que ? `${c.clave} — ${c.que}` : c.clave;
      if (c.que) nom.style.borderBottom = '1px dotted var(--tinta-tenue)';
      const val = document.createElement('b');
      val.textContent = String(c.valor);
      cab.appendChild(nom); cab.appendChild(val);
      const sl = document.createElement('input');
      sl.type = 'range';
      sl.min = String(c.min); sl.max = String(c.max); sl.step = String(c.paso);
      sl.value = String(c.valor);
      sl.addEventListener('input', () => {
        const v = parseFloat(sl.value);
        valores[id] = v;
        val.textContent = c.paso >= 1 ? String(Math.round(v)) : v.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
        if (!arrastrando) pedirRegen(false, 400);
      });
      // Al soltar, la buena.
      const fin = () => { if (arrastrando) { arrastrando = false; pedirRegen(false); } };
      sl.addEventListener('pointerdown', () => { arrastrando = true; });
      sl.addEventListener('pointerup', fin);
      sl.addEventListener('change', fin);
      fila.appendChild(cab); fila.appendChild(sl);
      return fila;
  }

  if (guardarBtn) {
    guardarBtn.addEventListener('click', () => vscode.postMessage({ type: 'guardar' }));
  }
  if (cargarBtn) {
    cargarBtn.addEventListener('click', () => vscode.postMessage({ type: 'cargar' }));
  }
  const orcaBtn = document.getElementById('orcaBtn');
  if (orcaBtn) {
    orcaBtn.addEventListener('click', () => vscode.postMessage({ type: 'orca' }));
  }
  // Qué plantilla se está usando, y un clic para cambiarla. Se guarda entre
  // sesiones porque es por impresora, pero guardada y sin mostrar deja al
  // usuario encerrado con la que eligió la primera vez.
  const plantillaFila = document.getElementById('plantilla');
  if (plantillaFila) {
    plantillaFila.addEventListener('click', () => vscode.postMessage({ type: 'plantilla' }));
  }

  window.addEventListener('message', (ev) => {
    const msg = ev.data;
    if (msg && msg.type === 'guardado') {
      if (paramsEstado) {
        paramsEstado.textContent = '✓ ' + msg.donde;
        setTimeout(() => { if (paramsEstado) paramsEstado.textContent = ''; }, 4000);
      }
      return;
    }
    if (msg && msg.type === 'recipe') {
      // Los toques son del ARCHIVO, no de la sesión: recargar la ventana o
      // cargar otra versión tiene que traer los suyos, no dejar los de antes.
      toques = (Array.isArray(msg.toques) ? msg.toques : []).map(limpiarToque);
      // El gcode que está en pantalla se generó con ESTOS toques, así que la
      // resta arranca en cero. Sin esta línea, al abrir un archivo que ya tiene
      // toques se los volvería a aplicar encima de sí mismos.
      toquesEnGcode = clonar(toques);
      deshechos = [];
      seleccionado = -1;
      pintarLista();
      actualizarAvisos();
      construirParams(msg.receta);
      return;
    }
    if (msg && msg.type === 'plantilla') {
      if (plantillaFila) {
        plantillaFila.textContent = msg.nombre
          ? `plantilla: ${msg.nombre}` + (msg.detalle ? ` · ${msg.detalle}` : '')
          : 'plantilla: ninguna — clic para elegir';
      }
      return;
    }
    if (msg && msg.type === 'regen-estado') {
      if (paramsEstado) paramsEstado.textContent = msg.estado === 'corriendo' ? 'generando…' : '';
      if (msg.estado === 'corriendo') mostrarCarga(true);
      return;
    }
    if (msg && msg.type === 'gcode') {
      // Solo la regeneración dice con qué toques se generó lo que manda. Si el
      // mensaje no lo trae —guardar el archivo, teclear en él, cambiar de
      // editor— la deformación viva se queda como está: darla por horneada sin
      // pruebas es lo que hacía saltar la pieza a la forma vieja.
      if (Array.isArray(msg.toquesAplicados)) toquesEnGcode = msg.toquesAplicados;
      try {
        rebuild(msg.text || '', msg.ruta || '');
      } catch (err) {
        hud.textContent = 'parse error: ' + (err && err.message ? err.message : err);
      }
      mostrarCarga(false);
      mostrarEstado('');
    }
  });


  // ==========================================================================
  // Esculpir
  // ==========================================================================
  // Clic sobre la pieza y arrastrar para jalar o empujar. Lo que se manda no es
  // un gcode editado sino un TOQUE —un dato— que el generador vuelve a leer.
  // Es la misma regla que los sliders y por el mismo motivo: un gcode editado
  // no tiene parámetros, así que la siguiente corrida tira el cambio.
  //
  // Hay dos niveles de respuesta y la diferencia es a propósito:
  //
  //   1. el FANTASMA, mientras arrastrás: JS deforma la cáscara de picking —una
  //      superficie de revolución lisa, no el recorrido— a 60 fps.
  //   2. la VERDAD, al soltar: se escribe el archivo de toques y Python
  //      regenera, igual que un slider.
  //
  // El fantasma nunca finge ser el recorrido real, así que si su caída difiere
  // un pelo de la de Python no importa: desaparece en cuanto llega el gcode.
  // Eso ahorra tener que mantener dos implementaciones idénticas del campo.

  // --- pinceles (puerto de lamparas/formas.py) ------------------------------
  const ESC_FORMAS = {
    circulo: () => (u, v) => Math.hypot(u, v),
    cuadrado: () => (u, v) => Math.max(Math.abs(u), Math.abs(v)),
    rombo: () => (u, v) => Math.abs(u) + Math.abs(v),
    poligono: (p) => {
      const n = Math.max(3, p.lados | 0), mitad = Math.PI / n, ap = Math.cos(mitad);
      return (u, v) => {
        const r = Math.hypot(u, v);
        if (r < 1e-12) return 0;
        let ang = Math.atan2(v, u) % (2 * mitad);
        if (ang < 0) ang += 2 * mitad;
        return r * Math.cos(ang - mitad) / ap;
      };
    },
    estrella: (p) => {
      const n = Math.max(2, p.puntas | 0);
      const h = Math.min(Math.max(p.hundido, 0), 0.95);
      return (u, v) => {
        const r = Math.hypot(u, v);
        if (r < 1e-12) return 0;
        const borde = (1 - h) + h * (1 + Math.cos(n * Math.atan2(v, u))) / 2;
        return r / Math.max(borde, 1e-6);
      };
    },
    banda: () => (u, v) => Math.abs(v),
    columna: () => (u, v) => Math.abs(u),
    anillo: (p) => {
      const g = Math.min(Math.max(p.grosor, 0.05), 1), centro = 1 - g / 2;
      return (u, v) => Math.abs(Math.hypot(u, v) - centro) / (g / 2);
    },
    cruz: (p) => {
      const g = Math.min(Math.max(p.grosor, 0.05), 1);
      return (u, v) => Math.min(
        Math.max(Math.abs(u), Math.abs(v) / g),
        Math.max(Math.abs(u) / g, Math.abs(v))
      );
    }
  };
  const ESC_K = 2.3, ESC_E = Math.exp(-ESC_K);
  const ESC_CAIDAS = {
    gauss: (d) => (d >= 1 ? 0 : (Math.exp(-ESC_K * d * d) - ESC_E) / (1 - ESC_E)),
    suave: (d) => { if (d >= 1) return 0; const s = 1 - d; return s * s * (3 - 2 * s); },
    meseta: (d) => {
      if (d <= 0.6) return 1;
      if (d >= 1) return 0;
      const s = (1 - d) / 0.4;
      return s * s * (3 - 2 * s);
    },
    pico: (d) => Math.max(0, 1 - d),
    plano: (d) => (d <= 1 ? 1 : 0)
  };
  // Qué parámetro extra pide cada forma. Se usa para mostrar solo los sliders
  // que esa forma entiende: mandarle `puntas` a un cuadrado es un error, y en
  // Python revienta con ese mismo mensaje.
  const ESC_EXTRA = {
    poligono: ['lados'], estrella: ['puntas', 'hundido'],
    anillo: ['grosor'], cruz: ['grosor']
  };

  function escPincel(t) {
    const forma = (ESC_FORMAS[t.forma] || ESC_FORMAS.circulo)(t);
    const caida = ESC_CAIDAS[t.caida] || ESC_CAIDAS.gauss;
    if (!t.rotacion) return (u, v) => caida(forma(u, v));
    const r = t.rotacion * Math.PI / 180, cs = Math.cos(r), sn = Math.sin(r);
    return (u, v) => caida(forma(u * cs + v * sn, -u * sn + v * cs));
  }

  // El `+ 2π` es para que el resto quede no negativo: en JS `%` conserva el
  // signo del dividendo y en Python no. Estuvo con `3π`, y eso corría CADA
  // toque media vuelta respecto de donde lo pone Python — invisible mientras
  // el fantasma era una cáscara translúcida, imposible de no ver ahora.
  const envolver = (d) => ((d + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;

  // Peso del toque en (angulo, t), con la simetría radial ya resuelta.
  function escPeso(t) {
    const pincel = escPincel(t);
    const ra = t.radio_grados * Math.PI / 180, rt = t.radio_t;
    const n = Math.max(1, t.simetria | 0);
    const centros = [];
    for (let k = 0; k < n; k++) centros.push(t.angulo * Math.PI / 180 + k * 2 * Math.PI / n);
    return (a, tt) => {
      const v = (tt - t.t) / rt;
      if (Math.abs(v) > 1.5) return 0;
      let mejor = 0;
      for (const c of centros) {
        const u = envolver(a - c) / ra;
        if (Math.abs(u) > 1.5) continue;
        const w = pincel(u, v);
        if (w > mejor) mejor = w;
      }
      return mejor;
    };
  }

  // --- la cáscara: dónde cae el clic ---------------------------------------
  // No se hace picking contra las líneas —una polilínea de 244 000 segmentos no
  // da una superficie— sino contra un sólido de revolución armado con el radio
  // medio de cada capa. Ese radio ya se calcula: `ajusteDeCapas` ajusta una
  // circunferencia por mínimos cuadrados a cada vuelta, con 0.006 mm de error.
  // La malla no se dibuja (material.visible = false) pero sí se raycastea:
  // THREE.Mesh.raycast mira la geometría, no si el material pinta.
  let cascara = null;   // { mesh, anillos:[{z,cx,cy,r}], base:Float32Array }
  const ESC_NU = 96;    // divisiones angulares de la cáscara

  function construirCascara(V, ext, meta, bbox, desde) {
    escSoltar();
    if (cascara) {
      printGroup.remove(cascara.mesh);
      cascara.mesh.geometry.dispose();
      cascara.mesh.material.dispose();
      cascara = null;
    }
    if (!meta || meta.layers < 4) return;
    const { centros, cuenta, suma, suma2 } = ajusteDeCapas(V, ext, meta.layerAt, meta.layers, desde);

    // Solo las vueltas que de verdad son una circunferencia. El fondo macizo de
    // un bowl es una espiral que barre todo el disco: ahí no hay radio de pared
    // que valga y el ajuste se va lejos.
    // "Ser una circunferencia" se comprueba, no se supone: se mide cuánto se
    // desvían los puntos de su propio radio medio. Una vuelta de la pared con
    // arrugas de 4.5 mm sobre radio 34 dispersa un 9%; el fondo macizo, que es
    // una espiral que barre todo el disco, un 29%; una línea de purga, más.
    // El 15% las separa sin discusión, y sin depender de dónde empiece la
    // pieza ni de cómo se llamen los comentarios.
    const anillos = [];
    for (let l = 0; l < meta.layers; l++) {
      if (cuenta[l] < 16) continue;
      const r = suma[l] / cuenta[l];
      if (!isFinite(r) || r < 1) continue;
      const rms = Math.sqrt(Math.max(0, suma2[l] / cuenta[l] - r * r));
      if (rms > 0.15 * r) continue;
      anillos.push({ z: meta.layerZ[l], cx: centros[l * 2], cy: centros[l * 2 + 1], r });
    }
    if (anillos.length < 4) return;
    anillos.sort((a, b) => a.z - b.z);

    // Una malla de 375 anillos x 96 es gratis de raycastear, pero deformarla en
    // cada frame no lo es. Se submuestrea a ~140 anillos: el fantasma es una
    // guía, no la pieza.
    const paso = Math.max(1, Math.ceil(anillos.length / 140));
    const usados = anillos.filter((_, i) => i % paso === 0 || i === anillos.length - 1);

    const nf = usados.length, pos = new Float32Array(nf * ESC_NU * 3);
    for (let f = 0; f < nf; f++) {
      const an = usados[f];
      for (let c = 0; c < ESC_NU; c++) {
        const a = c / ESC_NU * 2 * Math.PI, k = (f * ESC_NU + c) * 3;
        pos[k] = an.cx + an.r * Math.cos(a);
        pos[k + 1] = an.cy + an.r * Math.sin(a);
        pos[k + 2] = an.z;
      }
    }
    const idx = [];
    for (let f = 0; f < nf - 1; f++) {
      for (let c = 0; c < ESC_NU; c++) {
        const a = f * ESC_NU + c, b = f * ESC_NU + (c + 1) % ESC_NU;
        idx.push(a, b, a + ESC_NU, b, b + ESC_NU, a + ESC_NU);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    const mat = new THREE.MeshLambertMaterial({
      color: 0x6d86c4, transparent: true, opacity: 0.45, side: THREE.DoubleSide
    });
    mat.visible = false;   // invisible pero raycasteable
    const mesh = new THREE.Mesh(geo, mat);
    printGroup.add(mesh);
    cascara = { mesh, anillos: usados, base: Float32Array.from(pos), z0: usados[0].z,
                z1: usados[nf - 1].z };

    // Cada vértice en polares, una sola vez. Es lo que después permite mover la
    // pared a 60 fps: deformar es sumarle milímetros a un radio.
    //
    // Las capas sin ajuste válido —el fondo macizo, la purga— heredan el centro
    // de la capa buena más cercana. Dejarlas en (0,0) mandaba esos vértices a la
    // esquina de la cama en cuanto un toque los rozaba.
    const centroCapa = new Float64Array(meta.layers * 2);
    let ultimoBueno = -1;
    for (let l = 0; l < meta.layers; l++) {
      if (cuenta[l] >= 16) {
        centroCapa[l * 2] = centros[l * 2]; centroCapa[l * 2 + 1] = centros[l * 2 + 1];
        if (ultimoBueno < 0) {
          for (let k = 0; k < l; k++) { centroCapa[k * 2] = centros[l * 2]; centroCapa[k * 2 + 1] = centros[l * 2 + 1]; }
        }
        ultimoBueno = l;
      } else if (ultimoBueno >= 0) {
        centroCapa[l * 2] = centroCapa[ultimoBueno * 2];
        centroCapa[l * 2 + 1] = centroCapa[ultimoBueno * 2 + 1];
      }
    }

    const nv = V.length / 3;
    polar = {
      r: new Float32Array(nv), a: new Float32Array(nv), t: new Float32Array(nv),
      cx: new Float32Array(nv), cy: new Float32Array(nv)
    };
    for (let i = 0; i < nv; i++) {
      const o = i * 3, l = meta.layerAt[i >> 1] || 0;
      const cx = centroCapa[l * 2], cy = centroCapa[l * 2 + 1];
      const dx = V[o] - cx, dy = V[o + 1] - cy;
      polar.cx[i] = cx; polar.cy[i] = cy;
      polar.r[i] = Math.hypot(dx, dy);
      polar.a[i] = Math.atan2(dy, dx);
      polar.t[i] = Math.min(1, Math.max(0, escT(V[o + 2])));
    }
    actualizarAvisos();
  }

  // z -> t y t -> z. `t` NO es "altura sobre la cama dividido la altura": la
  // base sólida ocupa unas capas abajo y las de transición suben menos que las
  // demás. Python deja la tabla exacta en la receta (`mapeo.z_capa`); sin ella
  // se cae a lineal, que pone los toques unos milímetros más arriba.
  function escT(z) {
    const m = receta && receta.mapeo;
    if (m && Array.isArray(m.z_capa) && m.z_capa.length > 1) {
      const zc = m.z_capa, n = zc.length - 1;
      if (z <= zc[0]) return 0;
      if (z >= zc[n]) return 1;
      let lo = 0, hi = n;
      while (hi - lo > 1) { const md = (lo + hi) >> 1; if (zc[md] <= z) lo = md; else hi = md; }
      const f = (z - zc[lo]) / Math.max(1e-9, zc[hi] - zc[lo]);
      return (lo + f) / n;
    }
    if (!cascara) return 0;
    return (z - cascara.z0) / Math.max(1e-9, cascara.z1 - cascara.z0);
  }

  function escZ(t) {
    const m = receta && receta.mapeo;
    if (m && Array.isArray(m.z_capa) && m.z_capa.length > 1) {
      const zc = m.z_capa, n = zc.length - 1;
      const x = Math.min(Math.max(t, 0), 1) * n, i = Math.min(n - 1, Math.floor(x));
      return zc[i] + (zc[i + 1] - zc[i]) * (x - i);
    }
    if (!cascara) return 0;
    return cascara.z0 + (cascara.z1 - cascara.z0) * t;
  }

  // Radio de la cáscara en (angulo, t), para dibujar el cursor sobre la pieza.
  function escRadio(t) {
    if (!cascara) return 0;
    const z = escZ(t), an = cascara.anillos;
    let lo = 0, hi = an.length - 1;
    if (z <= an[0].z) return an[0].r;
    if (z >= an[hi].z) return an[hi].r;
    while (hi - lo > 1) { const md = (lo + hi) >> 1; if (an[md].z <= z) lo = md; else hi = md; }
    const f = (z - an[lo].z) / Math.max(1e-9, an[hi].z - an[lo].z);
    return an[lo].r + (an[hi].r - an[lo].r) * f;
  }

  function escCentro(t) {
    if (!cascara) return [0, 0];
    const z = escZ(t), an = cascara.anillos;
    let lo = 0, hi = an.length - 1;
    if (z <= an[0].z) return [an[0].cx, an[0].cy];
    if (z >= an[hi].z) return [an[hi].cx, an[hi].cy];
    while (hi - lo > 1) { const md = (lo + hi) >> 1; if (an[md].z <= z) lo = md; else hi = md; }
    const f = (z - an[lo].z) / Math.max(1e-9, an[hi].z - an[lo].z);
    return [an[lo].cx + (an[hi].cx - an[lo].cx) * f, an[lo].cy + (an[hi].cy - an[lo].cy) * f];
  }


  // --- deformación en vivo --------------------------------------------------
  // La pieza se deforma en pantalla mientras arrastrás, sobre el RECORRIDO real
  // y no sobre una cáscara aproximada. Es posible porque cada vértice se guarda
  // también en polares —radio, ángulo y altura relativa contra el centro
  // ajustado de SU capa— una sola vez al cargar el archivo. Con eso, mover la
  // pared es sumarle milímetros a un radio: nada de re-parsear ni de esperar a
  // Python.
  //
  // Lo que se dibuja es siempre  gcode + (lo que quiero − lo que el gcode ya
  // tiene). Esa resta es la que hace que Ctrl+Z sea instantáneo: deshacer no
  // espera una regeneración, aplica el toque con el signo cambiado.
  let polar = null;            // { r, a, t, cx, cy } por vértice
  let toquesEnGcode = [];      // con qué toques se generó lo que se está viendo
  let deshechos = [];          // pila de rehacer
  let despl = null;            // desplazamiento por vértice del trazo en curso
  let relieveVivo = null;      // intermedios de computeRelief, para repintar

  const clonar = (x) => JSON.parse(JSON.stringify(x));

  // Ruido de valor, puerto exacto de estructura._ruido. Los enteros son de 32
  // bits en Python por el `& 0xFFFFFFFF`, pero la SUMA inicial no lo es: llega a
  // 35 bits, así que el desplazamiento de 13 va con una división y no con `>>`,
  // que en JS truncaría a 32 antes de correr.
  function _valorJS(ix, iy, nu, semilla) {
    let x = (((ix % nu) + nu) % nu) * 374761393 + iy * 668265263 + semilla * 2147483647;
    x = (x ^ Math.floor(x / 8192)) >>> 0;
    x = Math.imul(x, 1274126177) >>> 0;
    x = (x ^ (x >>> 16)) >>> 0;
    return x / 0x7FFFFFFF - 1.0;
  }
  const _suaveJS = (a, b, t) => a + (b - a) * (t * t * (3 - 2 * t));
  function _ruidoJS(u, v, nu, nv, semilla) {
    const fu = u * nu, fv = v * nv;
    const iu = Math.floor(fu), iv = Math.floor(fv);
    const du = fu - iu, dv = fv - iv;
    const a = _suaveJS(_valorJS(iu, iv, nu, semilla), _valorJS(iu + 1, iv, nu, semilla), du);
    const b = _suaveJS(_valorJS(iu, iv + 1, nu, semilla), _valorJS(iu + 1, iv + 1, nu, semilla), du);
    return _suaveJS(a, b, dv);
  }

  // Un toque como campo (angulo, t) -> mm, con el signo que corresponda.
  // `suavizar` y `aplanar` devuelven 0: dependen de lo que hay DEBAJO —la
  // estructura, el patrón— y eso el preview no lo tiene. Se ven al regenerar,
  // que es honesto: mejor no mostrar nada que mostrar una forma inventada.
  function campoDeToque(t, signo) {
    if (t.tipo === 'pintar' || t.tipo === 'suavizar' || t.tipo === 'aplanar') return null;
    const w = escPeso(t);
    // El signo lo lleva la FUERZA; el tipo solo dice hacia dónde cuenta. Estuvo
    // con `Math.abs()` y por eso arrastrar hacia abajo se veía igual que hacia
    // arriba: mientras dura el trazo el tipo todavía es 'jalar' y la fuerza es
    // la que ya vale negativo. Recién al soltar se renombra a 'empujar'.
    let f = t.tipo === 'empujar' ? -t.fuerza : t.fuerza;
    f *= signo;
    if (t.tipo === 'textura') {
      const nu = Math.max(2, t.escala | 0), sem = t.semilla | 0;
      return (a, tt) => {
        const k = w(a, tt);
        if (k <= 0) return 0;
        let u = (a % (2 * Math.PI)) / (2 * Math.PI);
        if (u < 0) u += 1;
        return f * k * _ruidoJS(u, Math.min(1, Math.max(0, tt)), nu, nu, sem);
      };
    }
    return (a, tt) => f * w(a, tt);
  }

  // La diferencia entre lo que se quiere ver y lo que el gcode ya trae. Los
  // toques que están en las dos listas se cancelan y no se evalúan: en la
  // práctica queda uno solo, el que se está arrastrando.
  function partesDelta() {
    const quiero = enCurso ? toques.concat([enCurso]) : toques;
    const tengo = toquesEnGcode;
    const cuenta = new Map();
    const clave = (t) => JSON.stringify(t);
    for (const t of quiero) { const k = clave(t); cuenta.set(k, (cuenta.get(k) || 0) + 1); }
    for (const t of tengo) { const k = clave(t); cuenta.set(k, (cuenta.get(k) || 0) - 1); }
    const partes = [];
    for (const t of quiero) {
      const k = clave(t);
      if ((cuenta.get(k) || 0) > 0) { cuenta.set(k, cuenta.get(k) - 1); const f = campoDeToque(t, 1); if (f) partes.push(f); }
    }
    for (const t of tengo) {
      const k = clave(t);
      if ((cuenta.get(k) || 0) < 0) { cuenta.set(k, cuenta.get(k) + 1); const f = campoDeToque(t, -1); if (f) partes.push(f); }
    }
    return partes;
  }

  // Devuelve el desplazamiento por vértice, o null si no hay nada que mover.
  function deformarEnVivo(arr) {
    if (!polar) return null;
    const partes = partesDelta();
    if (!partes.length) return null;
    const n = polar.r.length;
    if (!despl || despl.length !== n) despl = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const a = polar.a[i], t = polar.t[i];
      let d = 0;
      for (let k = 0; k < partes.length; k++) d += partes[k](a, t);
      despl[i] = d;
      if (d === 0) continue;
      const r = polar.r[i] + d, o = i * 3;
      arr[o] = polar.cx[i] + r * Math.cos(a);
      arr[o + 1] = polar.cy[i] + r * Math.sin(a);
    }
    return despl;
  }

  // Relieve en vivo. El radio medio de la capa también se corre —si un toque
  // saca media vuelta, esa capa entera es más ancha— así que se recalcula, o el
  // mapa marcaría en rojo una pared que respecto de SU capa no sobresale nada.
  function recolorearRelieve(d) {
    if (colorMode !== 'relief' || !lineGeom || !segMeta) return;
    const col = lineGeom.getAttribute('color');
    if (!d) {
      if (reliefColors) { col.copyArray(reliefColors); col.needsUpdate = true; }
      return;
    }
    if (!relieveVivo) return;
    const { rad, cuenta, ref, escala, ini, ventana } = relieveVivo;
    const layerAt = segMeta.layerAt;
    const n = segExt.length;
    // El desplazamiento por segmento, y su media móvil con la MISMA ventana que
    // usó el mapa estático: si la referencia no se corre junto con la pared, un
    // toque que saca media vuelta pinta de naranja una zona que respecto de su
    // entorno no sobresale nada.
    const dSeg = new Float64Array(n);
    for (let i = 0; i < n; i++) dSeg[i] = (d[i * 2] + d[i * 2 + 1]) / 2;
    const ac = new Float64Array(n + 1);
    for (let i = 0; i < n; i++) ac[i + 1] = ac[i] + (segExt[i] && i >= ini ? dSeg[i] : 0);
    const cn = new Float64Array(n + 1);
    for (let i = 0; i < n; i++) cn[i + 1] = cn[i] + (segExt[i] && i >= ini ? 1 : 0);
    const h = ventana >> 1;
    const dRef = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const a = Math.max(0, i - h), b = Math.min(n, i + h + 1);
      const m = cn[b] - cn[a];
      dRef[i] = m > 0 ? (ac[b] - ac[a]) / m : dSeg[i];
    }
    const arr = col.array;
    for (let i = 0; i < n; i++) {
      const o = i * 6, l = layerAt[i];
      let r0, g0, b0;
      if (!segExt[i] || !cuenta[l] || i < ini) {
        r0 = 0.659; g0 = 0.698; b0 = 0.776;         // el gris de viaje
      } else {
        const k = Math.max(-1, Math.min(1,
          (rad[i] + dSeg[i] - (ref[i] + dRef[i])) / escala));
        const dest = k >= 0 ? RELIEF_OUT : RELIEF_IN;
        const t = Math.abs(k);
        r0 = (RELIEF_FLAT[0] + (dest[0] - RELIEF_FLAT[0]) * t) / 255;
        g0 = (RELIEF_FLAT[1] + (dest[1] - RELIEF_FLAT[1]) * t) / 255;
        b0 = (RELIEF_FLAT[2] + (dest[2] - RELIEF_FLAT[2]) * t) / 255;
      }
      arr[o] = r0; arr[o + 1] = g0; arr[o + 2] = b0;
      arr[o + 3] = r0; arr[o + 4] = g0; arr[o + 5] = b0;
    }
    col.needsUpdate = true;
  }

  // El sólido no se deforma: son cintas de seis vértices por segmento, medio
  // millón en total, y rehacerlas en cada movimiento del mouse no entra en un
  // frame. Mientras dura el trazo se muestran las líneas, que sí siguen la mano.
  let solidoAntes = null;
  function empezarTrazo() {
    if (solidObj) { solidoAntes = true; solidObj = false; applySolid(); }
  }
  // Nota: el sólido no se restaura al soltar sino en `repintarGeometria`,
  // cuando ya no queda deformación viva pendiente.

  // --- estado del esculpido -------------------------------------------------
  let toques = [];
  let modoEsc = false;
  let enCurso = null;          // el toque que se está arrastrando
  let arrastreY = 0;
  let arrastreX = 0;
  let tamanoBase = null;       // el tamaño del pincel al empezar el trazo
  // Cuánto crece el pincel por pixel horizontal. Multiplicativo y no aditivo:
  // así 100 px a la derecha lo agrandan en la misma proporción en la que 100 px
  // a la izquierda lo achican, y un pincel de 5° responde igual que uno de 90°.
  const ESC_ZOOM_PIXEL = 0.006;
  let seleccionado = -1;

  // Cuánto vale un pixel de arrastre. Por herramienta, porque no todas miden en
  // lo mismo: jalar son milímetros de pared, suavizar y aplanar una fracción.
  const ESC_POR_PIXEL = { jalar: 0.02, textura: 0.006, suavizar: 0.006, aplanar: 0.006 };
  const ESC_TOPE = { jalar: 12, textura: 3, suavizar: 1, aplanar: 1 };

  const escPanel = document.getElementById('esculpir');
  const escCtrl = document.getElementById('esc-ctrl');
  const escLista = document.getElementById('esc-lista');
  const escEstado = document.getElementById('esc-estado');
  const escAviso = document.getElementById('esc-aviso');
  const escBtn = document.getElementById('escBtn');
  const escTitulo = document.getElementById('esc-titulo');

  // Los ajustes del pincel, o sea con qué se va a estampar el próximo toque.
  const pincelActual = {
    tipo: 'jalar', forma: 'circulo', caida: 'gauss', rotacion: 0,
    radio_grados: 30, radio_t: 0.10, simetria: 1,
    lados: 6, puntas: 5, hundido: 0.5, grosor: 0.4
  };

  // Cambiar la forma de un toque ya puesto deja atrás los parámetros de la
  // forma anterior — un círculo con `grosor` de cuando era una cruz. Python es
  // estricto a propósito y lo rechaza ("la forma 'circulo' no acepta grosor"),
  // así que se limpia acá, que es donde se sabe qué acepta cada forma.
  // También se redondea: el ángulo sale de un raycast y trae quince decimales
  // que no significan nada y hacen el archivo ilegible.
  const ESC_TODOS_EXTRA = ['lados', 'puntas', 'hundido', 'grosor'];

  function limpiarToque(t) {
    const acepta = ESC_EXTRA[t.forma] || [];
    for (const k of ESC_TODOS_EXTRA) if (!acepta.includes(k)) delete t[k];
    for (const k of acepta) if (t[k] === undefined) t[k] = pincelActual[k];
    t.angulo = Math.round(t.angulo * 10) / 10;
    t.t = Math.round(t.t * 10000) / 10000;
    t.fuerza = Math.round(t.fuerza * 1000) / 1000;
    return t;
  }

  function nuevoToque(angulo, t) {
    const x = {
      tipo: pincelActual.tipo, forma: pincelActual.forma, caida: pincelActual.caida,
      rotacion: pincelActual.rotacion, angulo, t,
      radio_grados: pincelActual.radio_grados, radio_t: pincelActual.radio_t,
      simetria: pincelActual.simetria, fuerza: 0
    };
    for (const k of (ESC_EXTRA[x.forma] || [])) x[k] = pincelActual[k];
    if (x.tipo === 'textura') { x.escala = 14; x.semilla = (Math.random() * 1000) | 0; }
    return x;
  }

  // Nota: la cáscara quedó solo para el picking. Antes hacía de fantasma —una
  // superficie lisa deformada al lado de la pieza— y era el sustituto de esto:
  // ahora se deforma el recorrido real, así que el sustituto sobra.

  // --- cursor ---------------------------------------------------------------
  // El contorno del pincel dibujado SOBRE la pieza. Se busca por bisección
  // dónde la forma vale 1 a lo largo de cada rayo; así el mismo código sirve
  // para un círculo y para una banda, que en (u,v) no tiene borde en `u` —
  // el tope del rayo la convierte en el aro de vuelta entera que en efecto es.
  let cursor = null;
  const ESC_NC = 72;

  function crearCursor() {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(ESC_NC * 3), 3));
    cursor = new THREE.LineLoop(geo, new THREE.LineBasicMaterial({ color: 0xe8562a }));
    cursor.visible = false;
    scene.add(cursor);
  }

  function moverCursor(t) {
    if (!cursor) crearCursor();
    if (!cascara || !t) { cursor.visible = false; return; }
    const forma = (ESC_FORMAS[t.forma] || ESC_FORMAS.circulo)(t);
    const rot = t.rotacion * Math.PI / 180, cs = Math.cos(rot), sn = Math.sin(rot);
    const d = (u, v) => forma(u * cs + v * sn, -u * sn + v * cs);
    const ra = t.radio_grados * Math.PI / 180, rt = t.radio_t;
    const arr = cursor.geometry.attributes.position.array;
    for (let i = 0; i < ESC_NC; i++) {
      const th = i / ESC_NC * 2 * Math.PI, cu = Math.cos(th), sv = Math.sin(th);
      let lo = 0, hi = 3;
      if (d(hi * cu, hi * sv) < 1) lo = hi;      // el rayo no llega al borde
      else for (let k = 0; k < 24; k++) {
        const md = (lo + hi) / 2;
        if (d(md * cu, md * sv) < 1) lo = md; else hi = md;
      }
      const s = (lo + hi) / 2;
      const tt = Math.min(1, Math.max(0, t.t + s * sv * rt));
      const ang = t.angulo * Math.PI / 180 + s * cu * ra;
      const r = escRadio(tt) + 0.6;             // apenas afuera, para no pelearse con la pared
      const [cx, cy] = escCentro(tt);
      arr[i * 3] = cx + r * Math.cos(ang);
      arr[i * 3 + 1] = cy + r * Math.sin(ang);
      arr[i * 3 + 2] = escZ(tt);
    }
    cursor.geometry.attributes.position.needsUpdate = true;
    cursor.position.copy(printGroup.position);
    cursor.visible = true;
  }

  // --- picking y arrastre ---------------------------------------------------
  const rayo = new THREE.Raycaster();
  const pantalla = new THREE.Vector2();

  function golpear(ev) {
    if (!cascara) return null;
    const r = renderer.domElement.getBoundingClientRect();
    pantalla.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    pantalla.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    rayo.setFromCamera(pantalla, camera);
    const hits = rayo.intersectObject(cascara.mesh, false);
    if (!hits.length) return null;
    const p = printGroup.worldToLocal(hits[0].point.clone());
    const t = Math.min(1, Math.max(0, escT(p.z)));
    const [cx, cy] = escCentro(t);
    let ang = Math.atan2(p.y - cy, p.x - cx) * 180 / Math.PI;
    if (ang < 0) ang += 360;
    return { angulo: ang, t };
  }

  function escSoltar() {
    enCurso = null;
    if (cursor) cursor.visible = false;
    if (cascara) cascara.mesh.material.visible = false;
  }

  renderer.domElement.addEventListener('pointermove', (ev) => {
    if (!modoEsc) return;
    if (enCurso) {
      // Arriba y abajo, la fuerza. El signo sale del gesto y no de un selector:
      // es lo que uno ya está haciendo con la mano.
      const mm = (arrastreY - ev.clientY) * (ESC_POR_PIXEL[enCurso.tipo] || 0.02);
      const tope = ESC_TOPE[enCurso.tipo] || 12;
      enCurso.fuerza = Math.max(-tope, Math.min(tope, mm));

      // Izquierda y derecha, el tamaño — los dos radios a la vez, o la huella se
      // deformaría en vez de crecer. El factor se acota para que NINGUNO de los
      // dos se salga de su rango: si se acotara cada uno por su lado, al llegar
      // uno al tope el otro seguiría creciendo solo y una estrella se volvería
      // una raya.
      if (tamanoBase) {
        const kMin = Math.max(3 / tamanoBase.g, 0.01 / tamanoBase.t);
        const kMax = Math.min(180 / tamanoBase.g, 0.6 / tamanoBase.t);
        const k = Math.min(kMax, Math.max(kMin,
          Math.exp((ev.clientX - arrastreX) * ESC_ZOOM_PIXEL)));
        enCurso.radio_grados = Math.round(tamanoBase.g * k * 10) / 10;
        enCurso.radio_t = Math.round(tamanoBase.t * k * 1000) / 1000;
      }

      moverCursor(enCurso);
      repintarGeometria();
      mostrarEstado(
        `${enCurso.fuerza >= 0 ? 'jala' : 'empuja'} ${Math.abs(enCurso.fuerza).toFixed(2)}` +
        `  ·  ${enCurso.radio_grados.toFixed(0)}° / ${enCurso.radio_t.toFixed(3)}`
      );
      actualizarAvisos(enCurso);
      return;
    }
    const g = golpear(ev);
    moverCursor(g ? Object.assign({}, pincelActual, g) : null);
  });

  renderer.domElement.addEventListener('contextmenu', (ev) => {
    if (modoEsc) ev.preventDefault();   // el derecho ahora orbita
  });

  // Shift + izquierdo devuelve el botón izquierdo a lo que hacía siempre:
  // orbitar. Va en fase de CAPTURA, y eso no es un detalle — OrbitControls lee
  // `mouseButtons.LEFT` en el instante del pointerdown, así que asignarlo desde
  // un listener normal llegaría tarde: para entonces ya decidió que el izquierdo
  // no hace nada y el arrastre entero se pierde.
  renderer.domElement.addEventListener('pointerdown', (ev) => {
    if (!modoEsc) return;
    controls.mouseButtons.LEFT = ev.shiftKey ? THREE.MOUSE.ROTATE : null;
  }, true);

  renderer.domElement.addEventListener('pointerdown', (ev) => {
    if (!modoEsc || ev.button !== 0 || ev.shiftKey) return;
    const g = golpear(ev);
    if (!g) return;
    ev.preventDefault();
    arrastreY = ev.clientY;
    arrastreX = ev.clientX;
    enCurso = nuevoToque(g.angulo, g.t);
    tamanoBase = { g: enCurso.radio_grados, t: enCurso.radio_t };
    renderer.domElement.setPointerCapture(ev.pointerId);
    empezarTrazo();
    moverCursor(enCurso);
    repintarGeometria();
  });

  function terminarArrastre(ev) {
    if (!enCurso) return;
    const t = enCurso;
    // El tamaño con el que se terminó queda cargado para el trazo siguiente:
    // un pincel que uno agrandó sigue agrandado, como cualquier herramienta.
    if (tamanoBase && (t.radio_grados !== tamanoBase.g || t.radio_t !== tamanoBase.t)) {
      pincelActual.radio_grados = t.radio_grados;
      pincelActual.radio_t = t.radio_t;
      construirEsc();
    }
    tamanoBase = null;
    escSoltar();
    if (ev && ev.pointerId !== undefined) {
      try { renderer.domElement.releasePointerCapture(ev.pointerId); } catch (e) { /* ya soltado */ }
    }
    // Un clic sin arrastre no deja nada. Sin este umbral, cada intento fallido
    // de orbitar con el botón equivocado agrega un toque de fuerza cero que
    // igual cuesta una regeneración.
    if (Math.abs(t.fuerza) < 0.05) { mostrarEstado(''); repintarGeometria(); return; }
    if (t.fuerza < 0 && t.tipo === 'jalar') { t.tipo = 'empujar'; t.fuerza = Math.abs(t.fuerza); }
    toques.push(t);
    deshechos = [];               // una rama nueva invalida lo que había para rehacer
    // El toque nuevo NO queda seleccionado. Si quedara, cambiar la forma o la
    // caída del pincel para el trazo SIGUIENTE editaría el anterior y dispararía
    // una regeneración que nadie pidió. Se selecciona a mano, clicando su fila.
    seleccionado = -1;
    pintarLista();
    // La pantalla ya muestra el resultado; lo que sigue es solo confirmarlo en
    // el archivo. Por eso la deformación viva NO se borra acá: si se borrara,
    // la pieza volvería a la forma vieja durante los segundos que tarda Python.
    repintarGeometria();
    enviarToques();
  }
  renderer.domElement.addEventListener('pointerup', terminarArrastre);
  renderer.domElement.addEventListener('pointercancel', terminarArrastre);

  function enviarToques() {
    mostrarEstado('generando…');
    toques.forEach(limpiarToque);
    vscode.postMessage({ type: 'toques', toques, valores, borrador: false });
  }

  function mostrarEstado(txt) { if (escEstado) escEstado.textContent = txt; }

  // --- avisos ---------------------------------------------------------------
  // Lo único que rompe una pieza en modo vaso es que el radio se corra más de
  // un cordón entre dos vueltas: la vuelta nueva no apoya sobre la anterior y
  // la pared se abre. Un toque fuerte y angosto lo consigue sin que se note al
  // mirarlo, así que se mide mientras se arrastra y no después de imprimir.
  function pendienteEnT(t) {
    const pincel = escPincel(t);
    const paso = 3 / 120;
    let dv = 0;
    for (let i = 0; i <= 120; i++) {
      const u = -1.5 + i * paso;
      for (let j = 0; j <= 120; j++) {
        const v = -1.5 + j * paso;
        dv = Math.max(dv, Math.abs(pincel(u, v + paso) - pincel(u, v)) / paso);
      }
    }
    return dv;
  }

  function actualizarAvisos(extra) {
    if (!escAviso) return;
    const m = receta && receta.mapeo;
    const lista = extra ? toques.concat([extra]) : toques;
    if (!lista.length || !m || !m.capas || !cascara) { escAviso.classList.add('hidden'); return; }
    const altura = m.z1 - m.z0;
    const dtPorVuelta = altura > 0 ? (altura / m.capas) / altura : 0;
    const cordon = anchoDeCordon();
    const malos = [];
    for (const t of lista) {
      if (t.tipo === 'suavizar' || t.tipo === 'aplanar') continue;
      // El tope en |fuerza| no es cosmético: el peso va de 0 a 1, así que el
      // radio no puede correrse más que la fuerza entera entre dos vueltas.
      // Sin él, la caída 'plano' —que no tiene derivada— reporta lo que dé la
      // resolución del muestreo.
      const f = Math.abs(t.fuerza);
      const dr = Math.min(f * pendienteEnT(t) / t.radio_t * dtPorVuelta, f);
      if (dr > cordon) malos.push([t, dr]);
    }
    if (!malos.length) { escAviso.classList.add('hidden'); return; }
    const [t, dr] = malos[0];
    escAviso.textContent =
      `⚠ el radio se corre ${dr.toFixed(2)} mm por vuelta y el cordón mide ` +
      `${cordon.toFixed(2)} mm: la vuelta nueva no apoya sobre la anterior y la pared ` +
      `se abre. Bajá la fuerza a ${(Math.abs(t.fuerza) * cordon / dr).toFixed(2)} mm` +
      (t.caida === 'plano'
        ? ` o cambiá la caída: con 'plano' el borde es un escalón.`
        : ` o subí el alto a ${(t.radio_t * dr / cordon).toFixed(3)}.`) +
      (malos.length > 1 ? `  (+${malos.length - 1} más)` : '');
    escAviso.classList.remove('hidden');
  }

  // El ancho del cordón sale de la receta si está; si no, del propio gcode.
  function anchoDeCordon() {
    const c = (receta && receta.controles || []).find((x) => x.clave === 'ancho-linea');
    if (c) return valores[c.flag + ':' + c.clave] || c.valor;
    return 0.8;
  }

  // --- panel ----------------------------------------------------------------
  const ESC_TIPOS = [
    ['jalar', 'jalar / empujar — arrastrá arriba o abajo'],
    ['textura', 'textura — ruido local en ese parche'],
    ['suavizar', 'suavizar — apaga la estructura ahí'],
    ['aplanar', 'aplanar — lleva la zona a un radio parejo']
  ];
  const ESC_LISTA_FORMAS = ['circulo', 'cuadrado', 'rombo', 'poligono', 'estrella',
                            'banda', 'columna', 'anillo', 'cruz'];
  const ESC_LISTA_CAIDAS = ['gauss', 'suave', 'meseta', 'pico', 'plano'];
  const ESC_AYUDA = {
    forma: 'la huella del pincel: dónde termina el toque',
    caida: 'cómo se apaga desde el centro. "plano" deja un escalón; "meseta" es lo que quiere aplanar',
    radio_grados: 'cuánto abarca alrededor del eje, en grados',
    radio_t: 'cuánto abarca en altura, como fracción de la pieza',
    rotacion: 'gira la huella',
    simetria: 'repite el mismo toque N veces alrededor del eje',
    lados: '3 = triángulo, 6 = hexágono…',
    puntas: 'cuántas puntas tiene la estrella',
    hundido: 'qué tanto se mete el valle de la estrella',
    grosor: 'ancho del aro o del brazo, como fracción del radio'
  };

  function selectDe(clave, opciones, etiquetas) {
    const cont = document.createElement('div');
    const rot = document.createElement('div');
    rot.className = 'esc-rot';
    rot.textContent = clave === 'radio_grados' ? 'ancho' : clave === 'radio_t' ? 'alto' : clave;
    const sel = document.createElement('select');
    sel.title = ESC_AYUDA[clave] || clave;
    for (let i = 0; i < opciones.length; i++) {
      const o = document.createElement('option');
      o.value = opciones[i];
      o.textContent = etiquetas ? etiquetas[i] : opciones[i];
      sel.appendChild(o);
    }
    sel.value = pincelActual[clave];
    sel.addEventListener('change', () => {
      pincelActual[clave] = sel.value;
      construirEsc();       // cambiar de forma cambia qué sliders tienen sentido
      aplicarASeleccionado(clave, sel.value);
    });
    cont.appendChild(rot); cont.appendChild(sel);
    return cont;
  }

  function sliderDe(clave, min, max, paso) {
    const fila = document.createElement('div');
    fila.className = 'par';
    fila.title = ESC_AYUDA[clave] || clave;
    const cab = document.createElement('div');
    cab.className = 'par-fila';
    const nom = document.createElement('span');
    nom.textContent = clave === 'radio_grados' ? 'ancho (°)'
      : clave === 'radio_t' ? 'alto (t)' : clave;
    const val = document.createElement('b');
    const fmt = (v) => (paso >= 1 ? String(Math.round(v)) : v.toFixed(3).replace(/0+$/, '').replace(/\.$/, ''));
    val.textContent = fmt(pincelActual[clave]);
    cab.appendChild(nom); cab.appendChild(val);
    const sl = document.createElement('input');
    sl.type = 'range'; sl.min = String(min); sl.max = String(max);
    sl.step = String(paso); sl.value = String(pincelActual[clave]);
    // Mismo criterio que los sliders de arriba: arrastrar solo mueve el número
    // y el fantasma; la corrida de Python sale al soltar.
    let tecla = null;
    sl.addEventListener('input', () => {
      const v = parseFloat(sl.value);
      pincelActual[clave] = v;
      val.textContent = fmt(v);
      aplicarASeleccionado(clave, v, true);
      clearTimeout(tecla);
      tecla = setTimeout(() => aplicarASeleccionado(clave, parseFloat(sl.value)), 400);
    });
    sl.addEventListener('change', () => {
      clearTimeout(tecla);
      aplicarASeleccionado(clave, parseFloat(sl.value));
    });
    fila.appendChild(cab); fila.appendChild(sl);
    return fila;
  }

  // Tocar un control con un toque seleccionado lo EDITA. Poder retocar después
  // vale más que acertar durante el arrastre: al soltar uno ya vio la pieza.
  function aplicarASeleccionado(clave, valor, soloVista) {
    if (seleccionado < 0 || seleccionado >= toques.length) return;
    const t = toques[seleccionado];
    if (!(clave in t) && !ESC_AYUDA[clave]) return;
    t[clave] = valor;
    if (clave === 'forma') limpiarToque(t);
    pintarLista();
    repintarGeometria();
    actualizarAvisos();
    if (!soloVista) enviarToques();
  }

  function construirEsc() {
    if (!escCtrl) return;
    escCtrl.innerHTML = '';
    escCtrl.appendChild(selectDe('tipo', ESC_TIPOS.map((x) => x[0]), ESC_TIPOS.map((x) => x[1])));
    escCtrl.appendChild(selectDe('forma', ESC_LISTA_FORMAS));
    escCtrl.appendChild(selectDe('caida', ESC_LISTA_CAIDAS));
    escCtrl.appendChild(sliderDe('radio_grados', 3, 180, 1));
    escCtrl.appendChild(sliderDe('radio_t', 0.01, 0.6, 0.005));
    escCtrl.appendChild(sliderDe('rotacion', 0, 180, 1));
    escCtrl.appendChild(sliderDe('simetria', 1, 12, 1));
    for (const k of (ESC_EXTRA[pincelActual.forma] || [])) {
      if (k === 'lados') escCtrl.appendChild(sliderDe('lados', 3, 12, 1));
      if (k === 'puntas') escCtrl.appendChild(sliderDe('puntas', 2, 12, 1));
      if (k === 'hundido') escCtrl.appendChild(sliderDe('hundido', 0, 0.95, 0.05));
      if (k === 'grosor') escCtrl.appendChild(sliderDe('grosor', 0.05, 1, 0.05));
    }
  }

  function pintarLista() {
    if (!escLista) return;
    if (escTitulo) {
      escTitulo.textContent = seleccionado >= 0
        ? `editando #${seleccionado + 1}` : 'pincel';
    }
    escLista.innerHTML = '';
    toques.forEach((t, i) => {
      const fila = document.createElement('div');
      fila.className = 'esc-toque' + (i === seleccionado ? ' sel' : '');
      const txt = document.createElement('span');
      txt.textContent = `${t.tipo} ${t.forma} ${Math.round(t.angulo)}° t${t.t.toFixed(2)}`;
      const f = document.createElement('b');
      f.textContent = (t.fuerza >= 0 ? '+' : '') + t.fuerza.toFixed(2);
      const menos = document.createElement('button');
      menos.textContent = '−'; menos.title = 'menos fuerza';
      const mas = document.createElement('button');
      mas.textContent = '+'; mas.title = 'más fuerza';
      const x = document.createElement('button');
      x.textContent = '×'; x.title = 'borrar este toque';
      const ajustar = (d) => {
        t.fuerza = Math.round((t.fuerza + d) * 100) / 100;
        pintarLista(); repintarGeometria(); actualizarAvisos(); enviarToques();
      };
      menos.addEventListener('click', (e) => { e.stopPropagation(); ajustar(-0.25); });
      mas.addEventListener('click', (e) => { e.stopPropagation(); ajustar(0.25); });
      x.addEventListener('click', (e) => {
        e.stopPropagation();
        toques.splice(i, 1);
        if (seleccionado >= toques.length) seleccionado = toques.length - 1;
        pintarLista(); repintarGeometria(); actualizarAvisos(); enviarToques();
      });
      fila.addEventListener('click', () => {
        // Clic sobre la fila ya seleccionada = soltarla, y los controles vuelven
        // a ser los del próximo trazo.
        if (seleccionado === i) {
          seleccionado = -1;
          pintarLista();
          return;
        }
        seleccionado = i;
        for (const k of ['tipo', 'forma', 'caida', 'rotacion', 'radio_grados', 'radio_t',
                         'simetria', 'lados', 'puntas', 'hundido', 'grosor']) {
          if (t[k] !== undefined) pincelActual[k] = t[k];
        }
        construirEsc(); pintarLista(); repintarGeometria();
      });
      fila.appendChild(txt); fila.appendChild(f);
      fila.appendChild(menos); fila.appendChild(mas); fila.appendChild(x);
      escLista.appendChild(fila);
    });
  }

  // En modo esculpir el botón izquierdo es solo del pincel y el derecho pasa a
  // orbitar. Con el reparto de fábrica —izquierdo orbita, derecho encuadra— cada
  // trazo que no acertaba a la pieza giraba la cámara, y no había forma de girar
  // sin arriesgarse a pintar.
  function repartirBotones(esculpiendo) {
    controls.mouseButtons = esculpiendo
      ? { LEFT: null, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE }
      : { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  }

  function modoEsculpir(on) {
    modoEsc = on;
    repartirBotones(on);
    if (escBtn) {
      escBtn.textContent = 'Sculpt: ' + (on ? 'on' : 'off');
      escBtn.classList.toggle('on', on);
    }
    if (escPanel) escPanel.classList.toggle('hidden', !on);
    if (!on) { escSoltar(); mostrarEstado(''); }
    else if (!cascara) mostrarEstado('sin pieza');
  }

  if (escBtn) escBtn.addEventListener('click', () => modoEsculpir(!modoEsc));
  const escDeshacer = document.getElementById('escDeshacer');
  const escLimpiar = document.getElementById('escLimpiar');
  // Deshacer es inmediato porque no espera a Python: quitar un toque de la
  // lista cambia la resta «lo que quiero − lo que el gcode tiene», y la pared
  // vuelve en el mismo frame. La regeneración sale igual, en segundo plano,
  // para que el archivo termine diciendo lo mismo que la pantalla.
  function deshacer() {
    if (!toques.length) return;
    deshechos.push(toques.pop());
    seleccionado = -1;
    pintarLista(); repintarGeometria(); actualizarAvisos(); enviarToques();
  }
  function rehacer() {
    if (!deshechos.length) return;
    toques.push(deshechos.pop());
    seleccionado = -1;
    pintarLista(); repintarGeometria(); actualizarAvisos(); enviarToques();
  }
  if (escDeshacer) escDeshacer.addEventListener('click', deshacer);
  if (escLimpiar) escLimpiar.addEventListener('click', () => {
    if (!toques.length) return;
    deshechos = toques.slice().reverse().concat(deshechos);
    toques = []; seleccionado = -1;
    pintarLista(); repintarGeometria(); actualizarAvisos(); enviarToques();
  });
  window.addEventListener('keydown', (ev) => {
    // Un select con el foco se traga las letras para saltar a una opción; si
    // no se filtra, elegir 'estrella' con el teclado prende y apaga el modo.
    const dst = ev.target && ev.target.tagName;
    if (dst === 'INPUT' || dst === 'SELECT' || dst === 'TEXTAREA') return;
    if (ev.key === 'e' || ev.key === 'E') { modoEsculpir(!modoEsc); return; }
    // Ctrl+Z / Cmd+Z aunque el modo esculpir esté apagado: es la pieza lo que
    // se deshace, no una herramienta.
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'z' || ev.key === 'Z')) {
      ev.preventDefault();
      if (ev.shiftKey) rehacer(); else deshacer();
      return;
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'y' || ev.key === 'Y')) {
      ev.preventDefault();
      rehacer();
    }
  });

  construirEsc();

  vscode.postMessage({ type: 'ready' });
})();
