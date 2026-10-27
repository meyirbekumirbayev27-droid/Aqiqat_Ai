/* Three.js көріністеріне ортақ көмекші функциялар */
import * as THREE from 'three';

let glowCache = null;

export function supportsWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch (e) {
    return false;
  }
}

export function glowTexture() {
  if (glowCache) return glowCache;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.2, 'rgba(255,255,255,0.85)');
  grd.addColorStop(0.45, 'rgba(255,255,255,0.25)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  glowCache = new THREE.CanvasTexture(c);
  glowCache.colorSpace = THREE.SRGBColorSpace;
  return glowCache;
}

export function textTexture(text, { size = 256, font = '700 150px Inter, sans-serif', color = '#ffffff', bg = null } = {}) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  if (bg) { g.fillStyle = bg; g.fillRect(0, 0, size, size); }
  g.fillStyle = color;
  g.font = font;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(text, size / 2, size / 2 + size * 0.04);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function glowLine(points, color, opacity = 0.9) {
  return new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
}

export function edges(geometry, color, opacity = 0.9) {
  return new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
}

export function holoMaterial(color, opacity = 0.12) {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
}

export function roundedRectShape(w, h, r) {
  const s = new THREE.Shape();
  const x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

export function shieldShape(w, h) {
  const s = new THREE.Shape();
  s.moveTo(0, h / 2);
  s.quadraticCurveTo(w * 0.3, h * 0.42, w / 2, h * 0.38);
  s.lineTo(w / 2, -h * 0.02);
  s.quadraticCurveTo(w * 0.45, -h * 0.35, 0, -h / 2);
  s.quadraticCurveTo(-w * 0.45, -h * 0.35, -w / 2, -h * 0.02);
  s.lineTo(-w / 2, h * 0.38);
  s.quadraticCurveTo(-w * 0.3, h * 0.42, 0, h / 2);
  return s;
}

export function particleField(count, radius, colors, size = 0.04) {
  const pos = new Float32Array(count * 3), col = new Float32Array(count * 3);
  const pal = colors.map((c) => new THREE.Color(c));
  for (let i = 0; i < count; i++) {
    const r = radius * (0.5 + Math.random() * 0.6);
    const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    pos.set([r * s * Math.cos(th), r * u * 0.6, r * s * Math.sin(th) - 1], i * 3);
    const c = pal[i % pal.length];
    col.set([c.r, c.g, c.b], i * 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return new THREE.Points(geo, new THREE.PointsMaterial({ size, map: glowTexture(), vertexColors: true, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
}
