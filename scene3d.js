import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const KEYFRAMES = [
  { p: 0.0, rotY: -0.22, rotX: 0.05, rotZ: 0.0, y: 0.02, camZ: 4.15 },
  { p: 0.30, rotY: 0.58, rotX: -0.08, rotZ: 0.03, y: 0.06, camZ: 3.85 },
  { p: 0.65, rotY: -0.45, rotX: 0.14, rotZ: -0.04, y: -0.02, camZ: 3.65 },
  { p: 1.0, rotY: 0.08, rotX: 0.03, rotZ: 0.0, y: 0.0, camZ: 4.0 },
];

const CHAPTER_LABELS = {
  profile: '01 Profile',
  opensource: '02 Open Source',
  ryocantsleep: '03 RyoCantSleep',
  stack: '04 Tech Stack',
};

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function smoothstep(t) {
  return t * t * (3 - 2 * t);
}

function samplePose(p) {
  if (p <= KEYFRAMES[0].p) return KEYFRAMES[0];
  for (let i = 0; i < KEYFRAMES.length - 1; i++) {
    const a = KEYFRAMES[i];
    const b = KEYFRAMES[i + 1];
    if (p <= b.p) {
      const span = Math.max(1e-4, b.p - a.p);
      const t = smoothstep(clamp((p - a.p) / span, 0, 1));
      return {
        rotY: lerp(a.rotY, b.rotY, t),
        rotX: lerp(a.rotX, b.rotX, t),
        rotZ: lerp(a.rotZ, b.rotZ, t),
        y: lerp(a.y, b.y, t),
        camZ: lerp(a.camZ, b.camZ, t),
      };
    }
  }
  return KEYFRAMES[KEYFRAMES.length - 1];
}

function initShowcase() {
  const stageEl = document.getElementById('stage-3d');
  const canvas = document.getElementById('canvas-3d');
  if (!stageEl || !canvas) return;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
  } catch {
    return;
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envTex;
  scene.environmentIntensity = 0.72;

  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 40);
  camera.position.set(0, 0.04, 4.15);

  const keyLight = new THREE.DirectionalLight(0xfff9f4, 2.1);
  keyLight.position.set(3.4, 4.2, 5.2);
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0xeef4ff, 1.0);
  fillLight.position.set(-4.0, 1.5, 2.5);
  scene.add(fillLight);

  const crimsonRim = new THREE.SpotLight(0xd70015, 7.0, 16, Math.PI / 3.2, 0.55, 1.2);
  crimsonRim.position.set(-2.6, 2.0, -3.2);
  scene.add(crimsonRim);

  const topHairLight = new THREE.DirectionalLight(0x0071e3, 0.75);
  topHairLight.position.set(2.2, 3.8, -2.5);
  scene.add(topHairLight);

  const pivot = new THREE.Group();
  scene.add(pivot);

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let dragYaw = 0;
  let dragPitch = 0;
  let hoverX = 0;
  let hoverY = 0;
  let isDragging = false;
  let prevX = 0;
  let prevY = 0;

  stageEl.addEventListener('pointerdown', (e) => {
    isDragging = true;
    prevX = e.clientX;
    prevY = e.clientY;
    stageEl.setPointerCapture(e.pointerId);
  });

  stageEl.addEventListener('pointermove', (e) => {
    const rect = stageEl.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      hoverX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      hoverY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    }
    if (!isDragging) return;
    const dx = e.clientX - prevX;
    const dy = e.clientY - prevY;
    prevX = e.clientX;
    prevY = e.clientY;
    dragYaw += dx * 0.011;
    dragPitch = clamp(dragPitch + dy * 0.008, -0.55, 0.55);
  });

  const endDrag = () => {
    isDragging = false;
  };
  stageEl.addEventListener('pointerup', endDrag);
  stageEl.addEventListener('pointercancel', endDrag);
  stageEl.addEventListener('pointerleave', () => {
    hoverX = 0;
    hoverY = 0;
  });

  function resize() {
    const w = Math.max(1, stageEl.clientWidth);
    const h = Math.max(1, stageEl.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  if ('ResizeObserver' in window) {
    new ResizeObserver(resize).observe(stageEl);
  }
  window.addEventListener('resize', resize, { passive: true });

  const chapterEl = document.getElementById('stage-chapter');
  const progressBar = document.getElementById('scroll-progress-bar');
  const chapterEls = Array.from(document.querySelectorAll('[data-chapter]'));

  function computeScrollProgress() {
    const doc = document.documentElement;
    const maxScroll = Math.max(1, doc.scrollHeight - window.innerHeight);
    return clamp(window.scrollY / maxScroll, 0, 1);
  }

  function updateChapterHud(p) {
    if (progressBar) {
      progressBar.style.transform = `scaleX(${p.toFixed(4)})`;
    }
    if (!chapterEl || chapterEls.length === 0) return;
    const triggerY = window.innerHeight * 0.36;
    let activeKey = chapterEls[0].dataset.chapter;
    for (const el of chapterEls) {
      if (el.getBoundingClientRect().top <= triggerY) {
        activeKey = el.dataset.chapter;
      }
    }
    const label = CHAPTER_LABELS[activeKey];
    if (label && chapterEl.textContent !== label) {
      chapterEl.textContent = label;
    }
  }

  let curRotY = KEYFRAMES[0].rotY;
  let curRotX = KEYFRAMES[0].rotX;
  let curRotZ = KEYFRAMES[0].rotZ;
  let curY = KEYFRAMES[0].y;
  let curCamZ = KEYFRAMES[0].camZ;
  let curHoverX = 0;
  let curHoverY = 0;
  let elapsed = 0;
  let lastTime = performance.now();
  let rafId = 0;
  let loaded = false;

  const loader = new GLTFLoader();
  loader.load(
    './models/radityobw.glb',
    (gltf) => {
      const model = gltf.scene;
      model.traverse((obj) => {
        if (obj.isMesh && obj.material) {
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
          mats.forEach((m) => {
            m.needsUpdate = true;
          });
        }
      });

      const upright = new THREE.Group();
      upright.rotation.x = Math.PI / 2;
      const box = new THREE.Box3().setFromObject(model);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z) || 1;
      const normScale = 2.15 / maxDim;

      model.position.sub(center);
      upright.add(model);
      upright.scale.setScalar(normScale);
      pivot.add(upright);

      loaded = true;
      stageEl.classList.add('is-ready');
      resize();
    },
    undefined,
    () => {
      stageEl.classList.add('is-fallback');
    }
  );

  function frame(now) {
    rafId = requestAnimationFrame(frame);
    const dt = Math.min(0.05, Math.max(0.001, (now - lastTime) * 0.001));
    lastTime = now;

    const p = computeScrollProgress();
    updateChapterHud(p);
    const pose = samplePose(p);

    if (!isDragging) {
      dragYaw *= Math.exp(-1.4 * dt);
      dragPitch *= Math.exp(-1.6 * dt);
    }

    const alpha = reducedMotion ? 1 : 1 - Math.exp(-8.5 * dt);
    curRotY = lerp(curRotY, pose.rotY, alpha);
    curRotX = lerp(curRotX, pose.rotX, alpha);
    curRotZ = lerp(curRotZ, pose.rotZ, alpha);
    curY = lerp(curY, pose.y, alpha);
    curCamZ = lerp(curCamZ, pose.camZ, alpha);
    curHoverX = lerp(curHoverX, hoverX, alpha);
    curHoverY = lerp(curHoverY, hoverY, alpha);

    elapsed += dt;
    const breatheY = reducedMotion ? 0 : Math.sin(elapsed * 1.15) * 0.025;
    const breatheRot = reducedMotion ? 0 : Math.sin(elapsed * 0.8) * 0.04;

    if (loaded) {
      pivot.rotation.y = curRotY + dragYaw + curHoverX * 0.14 + breatheRot;
      pivot.rotation.x = curRotX + dragPitch + curHoverY * 0.08;
      pivot.rotation.z = curRotZ;
      pivot.position.y = curY + breatheY;
      camera.position.z = curCamZ;
      renderer.render(scene, camera);
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    } else if (!rafId) {
      lastTime = performance.now();
      rafId = requestAnimationFrame(frame);
    }
  });

  lastTime = performance.now();
  rafId = requestAnimationFrame(frame);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initShowcase, { once: true });
} else {
  initShowcase();
}
