/* Функция беттеріндегі голографиялық 3D көріністер */
import * as THREE from 'three';
import { edges, glowLine, glowTexture, holoMaterial, particleField, roundedRectShape, shieldShape, supportsWebGL, textTexture } from './three-utils.js';

const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const CYAN = 0x55e7ff, BLUE = 0x387bff, VIOLET = 0xa56bff, MAGENTA = 0xec5cff, RED = 0xff5c78, GREEN = 0x49e5b1;

function spriteGlow(color, scale) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  s.scale.setScalar(scale);
  return s;
}

// ---------- Дереккөз: голографиялық браузер + үлкейткіш + глобус ----------
function buildBrowser(root) {
  const win = new THREE.Group();
  root.add(win);
  const shape = roundedRectShape(3.2, 2.1, 0.14);
  win.add(new THREE.Mesh(new THREE.ShapeGeometry(shape), holoMaterial(CYAN, 0.07)));
  win.add(glowLine(shape.getPoints(12).map((p) => new THREE.Vector3(p.x, p.y, 0)).concat([new THREE.Vector3(-1.46, -1.05, 0)]), CYAN, 0.9));
  win.add(glowLine([new THREE.Vector3(-1.6, 0.72, 0), new THREE.Vector3(1.6, 0.72, 0)], CYAN, 0.6));
  [-1.38, -1.2, -1.02].forEach((x, i) => { const d = spriteGlow([RED, 0xffc857, GREEN][i], 0.16); d.position.set(x, 0.88, 0.01); win.add(d); });
  const bar = new THREE.Mesh(new THREE.ShapeGeometry(roundedRectShape(1.7, 0.16, 0.08)), holoMaterial(CYAN, 0.18));
  bar.position.set(0.25, 0.88, 0.01);
  win.add(bar);
  const lines = [];
  [[0.42, 2.4], [0.18, 2.0], [-0.06, 2.6], [-0.3, 1.6], [-0.54, 2.3], [-0.78, 1.2]].forEach(([y, w], i) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, 0.07), holoMaterial(i === 0 ? CYAN : BLUE, i === 0 ? 0.55 : 0.28));
    m.position.set(-1.35 + w / 2, y, 0.01);
    win.add(m);
    lines.push(m);
  });
  // Үлкейткіш әйнек
  const mag = new THREE.Group();
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.045, 16, 64), new THREE.MeshBasicMaterial({ color: CYAN }));
  const lens = new THREE.Mesh(new THREE.CircleGeometry(0.4, 48), holoMaterial(CYAN, 0.16));
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.06, 0.6, 16), new THREE.MeshBasicMaterial({ color: BLUE }));
  handle.position.set(0.48, -0.48, 0);
  handle.rotation.z = Math.PI / 4;
  mag.add(ring, lens, handle, spriteGlow(CYAN, 1.6));
  mag.position.z = 0.6;
  root.add(mag);
  // Цифрлық глобус
  const globe = new THREE.Group();
  globe.add(edges(new THREE.IcosahedronGeometry(0.62, 2), BLUE, 0.45));
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(0.6, 32, 32), holoMaterial(BLUE, 0.1)));
  globe.position.set(1.85, 1.0, -0.6);
  root.add(globe);
  return (t) => {
    win.rotation.y = Math.sin(t * 0.5) * 0.18 - 0.12;
    win.position.y = Math.sin(t * 0.8) * 0.06;
    mag.position.x = Math.cos(t * 0.7) * 0.9 - 0.2;
    mag.position.y = Math.sin(t * 1.1) * 0.45;
    lines.forEach((l, i) => { l.material.opacity = (i === 0 ? 0.35 : 0.15) + 0.25 * (0.5 + 0.5 * Math.sin(t * 2 - i * 0.6)); });
    globe.rotation.y = t * 0.4;
    globe.rotation.x = t * 0.15;
  };
}

// ---------- Медиа: голографиялық кадр + сканер сәулесі ----------
function buildMedia(root) {
  const frame = new THREE.Group();
  root.add(frame);
  const c = document.createElement('canvas');
  c.width = 512; c.height = 320;
  const g = c.getContext('2d');
  const sky = g.createLinearGradient(0, 0, 0, 320);
  sky.addColorStop(0, '#1b2a7a'); sky.addColorStop(0.6, '#6a4bd6'); sky.addColorStop(1, '#ec5cff');
  g.fillStyle = sky; g.fillRect(0, 0, 512, 320);
  g.fillStyle = 'rgba(255,220,150,.9)'; g.beginPath(); g.arc(360, 120, 40, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#0b1440';
  g.beginPath(); g.moveTo(0, 320); g.lineTo(0, 220); g.lineTo(120, 140); g.lineTo(220, 230); g.lineTo(330, 160); g.lineTo(512, 250); g.lineTo(512, 320); g.fill();
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const img = new THREE.Mesh(new THREE.PlaneGeometry(3, 1.9), new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.8 }));
  frame.add(img);
  const shape = roundedRectShape(3.3, 2.2, 0.12);
  frame.add(glowLine(shape.getPoints(12).map((p) => new THREE.Vector3(p.x, p.y, 0.01)).concat([new THREE.Vector3(-1.53, -1.1, 0.01)]), 0x6f9dff));
  // Бұрыштық жақшалар
  [[-1, 1], [1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => {
    const x = sx * 1.85, y = sy * 1.3;
    frame.add(glowLine([new THREE.Vector3(x, y - sy * 0.35, 0.02), new THREE.Vector3(x, y, 0.02), new THREE.Vector3(x - sx * 0.35, y, 0.02)], VIOLET));
  });
  const beam = new THREE.Mesh(new THREE.PlaneGeometry(3.5, 0.22), holoMaterial(0x6f9dff, 0.55));
  beam.position.z = 0.05;
  const beamLine = glowLine([new THREE.Vector3(-1.75, 0, 0.06), new THREE.Vector3(1.75, 0, 0.06)], 0xffffff);
  frame.add(beam, beamLine);
  const pts = [];
  for (let i = 0; i < 8; i++) {
    const p = spriteGlow(i % 2 ? VIOLET : CYAN, 0.22);
    p.position.set((Math.random() - 0.5) * 2.8, (Math.random() - 0.5) * 1.7, 0.08);
    p.material.opacity = 0;
    frame.add(p);
    pts.push(p);
  }
  return (t) => {
    frame.rotation.y = Math.sin(t * 0.45) * 0.25;
    frame.rotation.x = Math.sin(t * 0.3) * 0.08;
    const y = Math.sin(t * 1.3) * 0.95;
    beam.position.y = y; beamLine.position.y = y;
    pts.forEach((p) => { p.material.opacity = Math.max(0, 1 - Math.abs(p.position.y - y) * 3); });
  };
}

// ---------- Алаяқтық: смартфон + ескерту + қалқан ----------
function buildPhone(root) {
  const phone = new THREE.Group();
  root.add(phone);
  const body = roundedRectShape(1.35, 2.6, 0.2);
  phone.add(new THREE.Mesh(new THREE.ShapeGeometry(body), holoMaterial(CYAN, 0.08)));
  phone.add(glowLine(body.getPoints(12).map((p) => new THREE.Vector3(p.x, p.y, 0)).concat([new THREE.Vector3(-0.475, -1.3, 0)]), CYAN));
  const msgs = [];
  [[0.75, 0.9, CYAN], [0.35, 0.7, RED], [-0.05, 0.95, CYAN], [-0.45, 0.6, VIOLET]].forEach(([y, w, col], i) => {
    const m = new THREE.Mesh(new THREE.ShapeGeometry(roundedRectShape(w, 0.26, 0.08)), holoMaterial(col, 0.35));
    m.position.set(i % 2 ? 0.15 : -0.12, y, 0.01);
    phone.add(m);
    msgs.push(m);
  });
  const notch = new THREE.Mesh(new THREE.ShapeGeometry(roundedRectShape(0.4, 0.07, 0.035)), holoMaterial(CYAN, 0.5));
  notch.position.y = 1.15;
  phone.add(notch);
  // Ескерту белгісі
  const warn = new THREE.Group();
  const tri = new THREE.Shape();
  tri.moveTo(0, 0.48); tri.lineTo(0.5, -0.36); tri.lineTo(-0.5, -0.36); tri.lineTo(0, 0.48);
  warn.add(new THREE.Mesh(new THREE.ShapeGeometry(tri), holoMaterial(RED, 0.35)));
  warn.add(glowLine(tri.getPoints().map((p) => new THREE.Vector3(p.x, p.y, 0.01)), RED));
  const ex = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.4), new THREE.MeshBasicMaterial({ map: textTexture('!', { font: '800 200px Inter, sans-serif' }), transparent: true, depthWrite: false }));
  ex.position.set(0, -0.02, 0.02);
  warn.add(ex, spriteGlow(RED, 1.6));
  warn.position.set(1.05, 0.85, 0.5);
  root.add(warn);
  // Қорғаныс қалқаны
  const shield = new THREE.Group();
  const sh = shieldShape(1.1, 1.3);
  shield.add(new THREE.Mesh(new THREE.ShapeGeometry(sh), holoMaterial(VIOLET, 0.16)));
  shield.add(glowLine(sh.getPoints(16).map((p) => new THREE.Vector3(p.x, p.y, 0.01)), VIOLET));
  shield.add(glowLine([new THREE.Vector3(-0.22, 0, 0.02), new THREE.Vector3(-0.05, -0.18, 0.02), new THREE.Vector3(0.25, 0.18, 0.02)], GREEN));
  shield.position.set(-1.25, -0.55, 0.3);
  root.add(shield);
  return (t) => {
    phone.rotation.y = Math.sin(t * 0.5) * 0.3;
    phone.position.y = Math.sin(t * 0.9) * 0.08;
    msgs.forEach((m, i) => { m.material.opacity = 0.18 + 0.3 * (0.5 + 0.5 * Math.sin(t * 2.2 - i)); });
    const pulse = 1 + 0.08 * Math.sin(t * 5);
    warn.scale.setScalar(pulse);
    warn.rotation.z = Math.sin(t * 3) * 0.06;
    shield.rotation.y = t * 0.8;
    shield.position.y = -0.55 + Math.sin(t * 1.2) * 0.1;
  };
}

// ---------- Манипуляция: нейрондық желі / цифрлық ми ----------
function buildBrain(root) {
  const brain = new THREE.Group();
  root.add(brain);
  const nodes = [];
  const N = 90;
  for (let i = 0; i < N; i++) {
    let v;
    do {
      v = new THREE.Vector3((Math.random() * 2 - 1) * 1.7, (Math.random() * 2 - 1) * 1.05, (Math.random() * 2 - 1) * 1.1);
    } while ((v.x * v.x) / 2.9 + (v.y * v.y) / 1.1 + (v.z * v.z) / 1.2 > 1 || Math.abs(v.x) < 0.08);
    nodes.push(v);
  }
  const edgesArr = [];
  nodes.forEach((a, i) => nodes.forEach((b, j) => { if (j > i && a.distanceTo(b) < 0.62 && Math.sign(a.x) === Math.sign(b.x)) edgesArr.push([i, j]); }));
  const linePos = new Float32Array(edgesArr.length * 6);
  edgesArr.forEach(([i, j], k) => { linePos.set([nodes[i].x, nodes[i].y, nodes[i].z, nodes[j].x, nodes[j].y, nodes[j].z], k * 6); });
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.BufferAttribute(linePos, 3));
  brain.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: VIOLET, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false })));
  const np = new Float32Array(N * 3);
  nodes.forEach((n, i) => np.set([n.x, n.y, n.z], i * 3));
  const ng = new THREE.BufferGeometry();
  ng.setAttribute('position', new THREE.BufferAttribute(np, 3));
  brain.add(new THREE.Points(ng, new THREE.PointsMaterial({ size: 0.13, map: glowTexture(), color: CYAN, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })));
  brain.add(spriteGlow(VIOLET, 4.2));
  const pulses = [];
  for (let i = 0; i < 26 && edgesArr.length; i++) {
    const s = spriteGlow(i % 3 ? CYAN : MAGENTA, 0.2);
    brain.add(s);
    pulses.push({ s, e: edgesArr[Math.floor(Math.random() * edgesArr.length)], k: Math.random(), v: 0.6 + Math.random() * 0.9 });
  }
  let last = 0;
  return (t) => {
    const dt = Math.min(t - last, 0.05);
    last = t;
    brain.rotation.y = Math.sin(t * 0.35) * 0.6;
    brain.rotation.x = Math.sin(t * 0.25) * 0.12;
    for (const p of pulses) {
      p.k += dt * p.v;
      if (p.k >= 1) { p.k = 0; p.e = edgesArr[Math.floor(Math.random() * edgesArr.length)]; }
      p.s.position.lerpVectors(nodes[p.e[0]], nodes[p.e[1]], p.k);
    }
  };
}

// ---------- Құпиялылық: құлып + қалқан + айналатын белгішелер ----------
function buildLock(root) {
  const lock = new THREE.Group();
  root.add(lock);
  const body = roundedRectShape(1.5, 1.2, 0.16);
  lock.add(new THREE.Mesh(new THREE.ShapeGeometry(body), holoMaterial(MAGENTA, 0.18)));
  lock.add(glowLine(body.getPoints(12).map((p) => new THREE.Vector3(p.x, p.y - 0.35, 0.01)).concat([new THREE.Vector3(-0.59, -0.95, 0.01)]), MAGENTA));
  lock.children[0].position.y = -0.35;
  const shackle = new THREE.Mesh(new THREE.TorusGeometry(0.48, 0.07, 16, 48, Math.PI), new THREE.MeshBasicMaterial({ color: CYAN }));
  shackle.position.y = 0.25;
  lock.add(shackle);
  const legs = [-0.48, 0.48].map((x) => { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.3, 12), new THREE.MeshBasicMaterial({ color: CYAN })); l.position.set(x, 0.12, 0); lock.add(l); return l; });
  const hole = new THREE.Mesh(new THREE.CircleGeometry(0.13, 32), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  hole.position.set(0, -0.28, 0.02);
  const slot = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 0.3), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  slot.position.set(0, -0.48, 0.02);
  lock.add(hole, slot, spriteGlow(MAGENTA, 3.2));
  const sh = shieldShape(2.8, 3.1);
  const shield = glowLine(sh.getPoints(20).map((p) => new THREE.Vector3(p.x, p.y, -0.5)), VIOLET, 0.55);
  root.add(shield);
  const orbit = new THREE.Group();
  root.add(orbit);
  const icons = ['✉', '☎', '▤', '★'].map((ch, i) => {
    const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: textTexture(ch, { font: '700 140px "Segoe UI Symbol", Inter, sans-serif', color: i % 2 ? '#55E7FF' : '#EC5CFF' }), transparent: true, depthWrite: false }));
    m.scale.setScalar(0.5);
    orbit.add(m);
    return m;
  });
  return (t) => {
    lock.rotation.y = Math.sin(t * 0.6) * 0.35;
    lock.position.y = Math.sin(t * 0.9) * 0.07;
    shackle.position.y = 0.25 + Math.max(0, Math.sin(t * 0.8)) * 0.12;
    legs.forEach((l) => { l.position.y = 0.12 + Math.max(0, Math.sin(t * 0.8)) * 0.12; });
    shield.material.opacity = 0.35 + 0.25 * Math.sin(t * 1.5);
    icons.forEach((m, i) => {
      const a = t * 0.6 + (i / icons.length) * Math.PI * 2;
      m.position.set(Math.cos(a) * 2.1, Math.sin(a * 1.3) * 0.5, Math.sin(a) * 0.9);
    });
  };
}

// ---------- Ойын: қалқыған сұрақ карточкалары + шағын Жер ----------
function buildCards(root) {
  const loader = new THREE.TextureLoader();
  const earthTex = loader.load('/static/images/earth-night.jpg');
  earthTex.colorSpace = THREE.SRGBColorSpace;
  const earth = new THREE.Mesh(new THREE.SphereGeometry(0.7, 48, 48), new THREE.MeshBasicMaterial({ map: earthTex }));
  root.add(earth, spriteGlow(CYAN, 2.4));
  const ring = edges(new THREE.TorusGeometry(0.95, 0.002, 4, 80), CYAN, 0.4);
  ring.rotation.x = 1.3;
  root.add(ring);
  const defs = [['?', VIOLET, '#A56BFF'], ['✓', GREEN, '#49E5B1'], ['✕', RED, '#FF5C78'], ['?', CYAN, '#55E7FF']];
  const cards = defs.map(([ch, col, css], i) => {
    const g = new THREE.Group();
    const sh = roundedRectShape(0.75, 1.0, 0.1);
    g.add(new THREE.Mesh(new THREE.ShapeGeometry(sh), holoMaterial(col, 0.18)));
    g.add(glowLine(sh.getPoints(8).map((p) => new THREE.Vector3(p.x, p.y, 0.01)).concat([new THREE.Vector3(-0.275, -0.5, 0.01)]), col));
    const sym = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.55), new THREE.MeshBasicMaterial({ map: textTexture(ch, { color: css, font: '800 170px Inter, "Segoe UI Symbol", sans-serif' }), transparent: true, depthWrite: false }));
    sym.position.z = 0.02;
    g.add(sym);
    root.add(g);
    return { g, a: (i / defs.length) * Math.PI * 2 };
  });
  let flash = 0, flashColor = new THREE.Color(GREEN), shake = 0;
  const glow = spriteGlow(GREEN, 5);
  glow.material.opacity = 0;
  root.add(glow);
  window.addEventListener('aq:quiz', (e) => {
    if (e.detail === 'right') { flash = 1; flashColor.set(GREEN); }
    if (e.detail === 'wrong') { flash = 1; flashColor.set(RED); shake = 1; }
    if (e.detail === 'next') { cards.forEach((c) => { c.spin = 1; }); }
  });
  let last = 0;
  return (t) => {
    const dt = Math.min(t - last, 0.05);
    last = t;
    earth.rotation.y = t * 0.3;
    cards.forEach((c, i) => {
      const a = c.a + t * 0.35;
      c.g.position.set(Math.cos(a) * 1.9, Math.sin(t * 0.9 + i) * 0.25, Math.sin(a) * 0.8);
      c.g.rotation.y = -a + Math.PI / 2 + (c.spin ? (1 - c.spin) * Math.PI * 2 : 0) + Math.sin(t + i) * 0.2;
      if (c.spin) { c.spin = Math.max(0, c.spin - dt * 1.6); }
    });
    flash = Math.max(0, flash - dt * 1.2);
    glow.material.color.copy(flashColor);
    glow.material.opacity = flash * 0.8;
    shake = Math.max(0, shake - dt * 2.5);
    root.position.x = Math.sin(t * 60) * 0.08 * shake;
  };
}

const BUILDERS = { browser: buildBrowser, media: buildMedia, phone: buildPhone, brain: buildBrain, lock: buildLock, cards: buildCards };
const PARTICLES = {
  browser: [CYAN, BLUE], media: [BLUE, VIOLET], phone: [CYAN, RED, VIOLET], brain: [VIOLET, CYAN], lock: [CYAN, VIOLET, MAGENTA], cards: [CYAN, VIOLET, GREEN],
};

function mount(el) {
  const kind = el.dataset.scene;
  if (!BUILDERS[kind]) return;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  el.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0, 0, 6.4);
  const root = new THREE.Group();
  const hover = new THREE.Group();
  hover.add(root);
  scene.add(hover);
  scene.add(particleField(window.innerWidth < 760 ? 70 : 140, 4.5, PARTICLES[kind], 0.06));
  const update = BUILDERS[kind](root);

  const resize = () => {
    const w = el.clientWidth, h = el.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.position.z = w / h < 1.2 ? 8.2 : 6.4;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(el);
  resize();

  const target = { x: 0, y: 0 };
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    target.x = ((e.clientX - r.left) / r.width - 0.5) * 2;
    target.y = ((e.clientY - r.top) / r.height - 0.5) * 2;
  });
  el.addEventListener('pointerleave', () => { target.x = 0; target.y = 0; });

  const clock = new THREE.Clock();
  let visible = true, running = false;
  const frame = (t) => {
    hover.rotation.y += (target.x * 0.45 - hover.rotation.y) * 0.06;
    hover.rotation.x += (target.y * 0.3 - hover.rotation.x) * 0.06;
    update(t);
    renderer.render(scene, camera);
  };
  const loop = () => {
    if (!visible) { running = false; return; }
    running = true;
    frame(clock.getElapsedTime());
    requestAnimationFrame(loop);
  };
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible && !running && !reduce) loop(); }).observe(el);
  if (reduce) { frame(1.2); setTimeout(() => frame(1.2), 600); } else loop();
}

if (!supportsWebGL()) {
  document.documentElement.classList.add('no-webgl');
} else {
  // Көріністерді тек экранға жақындағанда жүктейміз
  const els = document.querySelectorAll('[data-scene]');
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => { if (en.isIntersecting) { io.unobserve(en.target); try { mount(en.target); } catch (e) { document.documentElement.classList.add('no-webgl'); } } });
  }, { rootMargin: '200px' });
  els.forEach((el) => io.observe(el));
}
