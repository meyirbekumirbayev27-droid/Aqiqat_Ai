/* Басты беттегі интерактивті 3D Жер шары (Three.js) */
import * as THREE from 'three';
import { glowTexture, supportsWebGL } from './three-utils.js';

const container = document.getElementById('globe');
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (container && !supportsWebGL()) {
  document.documentElement.classList.add('no-webgl');
} else if (container) {
  init();
}

function latLon(lat, lon, r) {
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (lon + 180) * Math.PI / 180;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

function init() {
  const small = window.innerWidth < 760;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, small ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
  camera.position.set(0, 0, 9.2);

  const R = 1.9;
  const parallax = new THREE.Group();
  const tilt = new THREE.Group();
  const earth = new THREE.Group();
  scene.add(parallax);
  parallax.add(tilt);
  tilt.add(earth);
  tilt.rotation.x = 0.38;
  tilt.rotation.z = -0.12;

  // ---- Жер беті: күндізгі жақ көгілдір, түнгі жақта қала жарықтары ----
  const loader = new THREE.TextureLoader();
  const base = container.dataset.static || '/static/images/';
  const dayTex = loader.load(base + 'earth-blue-marble.jpg');
  const nightTex = loader.load(base + 'earth-night.jpg');
  dayTex.colorSpace = nightTex.colorSpace = THREE.SRGBColorSpace;
  dayTex.anisotropy = nightTex.anisotropy = 4;

  const earthMat = new THREE.ShaderMaterial({
    uniforms: {
      uDay: { value: dayTex }, uNight: { value: nightTex },
      uLight: { value: new THREE.Vector3(-0.75, 0.4, 0.75).normalize() },
    },
    vertexShader: `
      varying vec2 vUv; varying vec3 vN; varying vec3 vView;
      void main() {
        vUv = uv;
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vN = normalize(mat3(modelMatrix) * normal);
        vView = normalize(cameraPosition - wp.xyz);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: `
      uniform sampler2D uDay; uniform sampler2D uNight; uniform vec3 uLight;
      varying vec2 vUv; varying vec3 vN; varying vec3 vView;
      void main() {
        vec3 day = texture2D(uDay, vUv).rgb;
        vec3 night = texture2D(uNight, vUv).rgb;
        float l = dot(normalize(vN), uLight);
        float dayMix = smoothstep(-0.3, 0.5, l);
        vec3 dayCol = mix(vec3(0.02, 0.07, 0.2), day * vec3(0.75, 1.0, 1.45), 0.92) * (0.42 + 1.0 * max(l, 0.0));
        vec3 nightCol = night * vec3(1.2, 1.0, 1.4) * 1.8 + day * vec3(0.03, 0.06, 0.14);
        vec3 col = mix(nightCol, dayCol, dayMix);
        float rim = pow(1.0 - max(dot(normalize(vN), vView), 0.0), 3.2);
        col += vec3(0.33, 0.9, 1.0) * rim * 0.65;
        gl_FragColor = vec4(col, 1.0);
        #include <colorspace_fragment>
      }`,
  });
  const sphere = new THREE.Mesh(new THREE.SphereGeometry(R, small ? 64 : 96, small ? 64 : 96), earthMat);
  earth.add(sphere);

  // ---- Цифрлық тор (ендік/бойлық сызықтары) ----
  const gridMat = new THREE.LineBasicMaterial({ color: 0x55e7ff, transparent: true, opacity: 0.07 });
  for (let lat = -60; lat <= 60; lat += 30) {
    const pts = [];
    for (let lon = 0; lon <= 360; lon += 4) pts.push(latLon(lat, lon, R * 1.004));
    earth.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), gridMat));
  }
  for (let lon = 0; lon < 360; lon += 30) {
    const pts = [];
    for (let lat = -90; lat <= 90; lat += 4) pts.push(latLon(lat, lon, R * 1.004));
    earth.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), gridMat));
  }

  // ---- Атмосфера жарығы ----
  const atmo = new THREE.Mesh(
    new THREE.SphereGeometry(R * 1.13, 64, 64),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
      vertexShader: `varying vec3 vN; varying vec3 vP;
        void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position,1.0); vP = mv.xyz; gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `varying vec3 vN; varying vec3 vP;
        void main(){ float i = pow(max(0.0, 0.62 - dot(vN, normalize(-vP))), 3.0);
          vec3 c = mix(vec3(0.22,0.48,1.0), vec3(0.33,0.9,1.0), 0.45);
          gl_FragColor = vec4(c, 1.0) * i * 1.5; }`,
    }),
  );
  tilt.add(atmo);

  // ---- Қалалар мен желі доғалары ----
  const cities = [
    [51.17, 71.43], [43.24, 76.89], [55.75, 37.62], [41.01, 28.98], [51.51, -0.13], [40.71, -74.0],
    [35.68, 139.69], [25.2, 55.27], [28.61, 77.21], [39.9, 116.4], [1.35, 103.82], [-33.87, 151.21],
    [48.86, 2.35], [-23.55, -46.63], [37.77, -122.42], [30.04, 31.24], [52.52, 13.4], [42.87, 74.59],
  ];
  const glow = glowTexture();
  const nodeMat = new THREE.SpriteMaterial({ map: glow, color: 0x7ff0ff, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  const cityVecs = cities.map(([la, lo]) => latLon(la, lo, R * 1.01));
  cityVecs.forEach((v, i) => {
    const s = new THREE.Sprite(nodeMat);
    s.position.copy(v);
    const sc = i < 2 ? 0.2 : 0.12;
    s.scale.set(sc, sc, sc);
    earth.add(s);
  });
  const pairs = [[0, 1], [0, 2], [0, 3], [0, 9], [0, 7], [1, 8], [1, 17], [2, 16], [3, 4], [4, 5], [5, 14], [6, 9], [7, 15], [8, 10], [10, 11], [12, 4], [13, 5], [6, 14], [3, 7], [0, 12]];
  const arcs = [];
  const pulseMat = new THREE.SpriteMaterial({ map: glow, color: 0xffffff, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  pairs.forEach(([a, b], i) => {
    const va = cityVecs[a], vb = cityVecs[b];
    const dist = va.distanceTo(vb);
    const mid = va.clone().add(vb).multiplyScalar(0.5).normalize().multiplyScalar(R * 1.01 + dist * 0.38);
    const curve = new THREE.QuadraticBezierCurve3(va, mid, vb);
    const pts = curve.getPoints(60);
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const colors = new Float32Array(pts.length * 3);
    const c1 = new THREE.Color(i % 3 === 0 ? 0xa56bff : 0x55e7ff), c2 = new THREE.Color(0x387bff);
    pts.forEach((_, k) => { const c = c1.clone().lerp(c2, k / pts.length); colors.set([c.r, c.g, c.b], k * 3); });
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }));
    earth.add(line);
    const pulse = new THREE.Sprite(pulseMat.clone());
    pulse.scale.set(0.11, 0.11, 0.11);
    earth.add(pulse);
    arcs.push({ curve, pulse, speed: 0.12 + Math.random() * 0.18, off: Math.random() });
  });

  // ---- Орбиталық сақиналар мен жерсеріктер ----
  const rings = [];
  const ringDefs = [
    { r: R * 1.42, color: 0x55e7ff, rx: 1.25, rz: 0.25, op: 0.38 },
    { r: R * 1.62, color: 0xa56bff, rx: 1.05, rz: -0.55, op: 0.3 },
    { r: R * 1.85, color: 0x387bff, rx: 1.45, rz: 0.75, op: 0.2 },
  ];
  ringDefs.forEach((d, i) => {
    const g = new THREE.Group();
    g.rotation.set(d.rx, 0, d.rz);
    const pts = [];
    for (let k = 0; k <= 200; k++) { const t = (k / 200) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(t) * d.r, Math.sin(t) * d.r, 0)); }
    const ring = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineDashedMaterial({ color: d.color, transparent: true, opacity: d.op, dashSize: i === 2 ? 0.08 : 10, gapSize: i === 2 ? 0.08 : 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    ring.computeLineDistances();
    g.add(ring);
    const sat = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: d.color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    sat.scale.set(0.26, 0.26, 0.26);
    g.add(sat);
    parallax.add(g);
    rings.push({ g, sat, r: d.r, speed: 0.25 - i * 0.06, off: i * 2.1 });
  });

  // ---- Қозғалыстағы бөлшектер ----
  const count = small ? 350 : 800;
  const pos = new Float32Array(count * 3);
  const col = new Float32Array(count * 3);
  const palette = [new THREE.Color(0x55e7ff), new THREE.Color(0xa56bff), new THREE.Color(0x387bff), new THREE.Color(0xec5cff)];
  for (let i = 0; i < count; i++) {
    const rad = R * (1.35 + Math.random() * 1.7);
    const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2;
    const s = Math.sqrt(1 - u * u);
    pos.set([rad * s * Math.cos(th), rad * u * 0.7, rad * s * Math.sin(th)], i * 3);
    const c = palette[i % palette.length];
    col.set([c.r, c.g, c.b], i * 3);
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({
    size: 0.045, map: glow, vertexColors: true, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
  }));
  scene.add(particles);

  // Қазақстанды алдыңғы жаққа бұру
  const kz = latLon(48, 68, 1);
  earth.rotation.y = -Math.atan2(kz.x, kz.z);

  // ---- Өлшем, тышқан, анимация ----
  const resize = () => {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(container);
  resize();

  const target = { x: 0, y: 0 };
  window.addEventListener('pointermove', (e) => {
    target.x = (e.clientX / window.innerWidth - 0.5) * 2;
    target.y = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  let visible = true, running = false;
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible && !running && !reduce) loop(); }).observe(container);

  const clock = new THREE.Clock();
  let last = 0;
  function frame(t) {
    const dt = Math.min(t - last, 0.05);
    last = t;
    earth.rotation.y += dt * 0.06;
    atmo.rotation.y = earth.rotation.y;
    parallax.rotation.y += (target.x * 0.28 - parallax.rotation.y) * 0.04;
    parallax.rotation.x += (target.y * 0.16 - parallax.rotation.x) * 0.04;
    particles.rotation.y = t * 0.02;
    particles.rotation.x = Math.sin(t * 0.1) * 0.05;
    for (const a of arcs) {
      const k = (t * a.speed + a.off) % 1;
      a.pulse.position.copy(a.curve.getPoint(k));
      const f = Math.sin(k * Math.PI);
      a.pulse.scale.setScalar(0.04 + 0.1 * f);
      a.pulse.material.opacity = f;
    }
    for (const r of rings) {
      const a = t * r.speed + r.off;
      r.sat.position.set(Math.cos(a) * r.r, Math.sin(a) * r.r, 0);
    }
    renderer.render(scene, camera);
  }
  function loop() {
    if (!visible) { running = false; return; }
    running = true;
    frame(clock.getElapsedTime());
    requestAnimationFrame(loop);
  }
  if (reduce) {
    // Қозғалыс азайтылған: текстуралар жүктелгенде бір кадр саламыз
    THREE.DefaultLoadingManager.onLoad = () => frame(1.5);
    frame(1.5);
  } else {
    loop();
  }
}
