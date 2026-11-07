import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const PARAM_CONFIG = [
  { key: "cut_diameter", label: "Cut diameter", min: 40, max: 90, step: 1, unit: "mm", decimals: 0, group: "cutter" },
  { key: "wall", label: "Wall thickness", min: 1.2, max: 3.0, step: 0.1, unit: "mm", decimals: 1, group: "cutter" },
  { key: "height", label: "Wall height", min: 6, max: 30, step: 1, unit: "mm", decimals: 0, group: "cutter", note: "Outer ring height; the minimum depends on rim depth and flat rear." },
  { key: "rim_depth", label: "Rim depth", min: 4, max: 12, step: 0.5, unit: "mm", decimals: 1, group: "cutter", note: "Cutting wall below the embosser plate; 4 mm leaves 1 mm above 3 mm fondant." },
  { key: "flange_width", label: "Flange width", min: 2, max: 8, step: 0.5, unit: "mm", decimals: 1, group: "cutter" },
  { key: "bird_depth", label: "Bird emboss", min: 0.8, max: 2.5, step: 0.1, unit: "mm", decimals: 1, group: "cutter" },
  { key: "shield_depth", label: "Shield emboss", min: 0.2, max: 2.0, step: 0.1, unit: "mm", decimals: 1, group: "cutter" },
  { key: "lime_depth", label: "Lime emboss", min: 0.2, max: 1.5, step: 0.1, unit: "mm", decimals: 1, group: "cutter" },
  {
    key: "logo_scale",
    label: "Logo scale",
    min: 50,
    max: 100,
    step: 1,
    unit: "%",
    decimals: 0,
    group: "logo",
    toSlider: (value) => value * 100,
    fromSlider: (value) => value / 100,
  },
  { key: "logo_offset_x", label: "X offset", min: -10, max: 10, step: 0.1, unit: "mm", decimals: 1, group: "logo" },
  { key: "logo_offset_y", label: "Y offset", min: -10, max: 10, step: 0.1, unit: "mm", decimals: 1, group: "logo" },
  { key: "logo_rotation", label: "Rotation", min: -180, max: 180, step: 1, unit: "°", decimals: 0, group: "logo" },
];

const NOZZLE_OPTIONS = [0.2, 0.4, 0.6, 0.8];

const EXPLODE_FACTORS = {
  ring: 0,
  plate: 0.45,
  bird: 1,
  shield: 1,
  lime: 1,
  back: 0,
  print_model: 0,
};

const state = {
  params: {},
  defaults: {},
  parts: [],
  partState: {},
  nodes: {},
  model: null,
  urls: {},
  info: null,
  explode: 0,
  loading: false,
  paramInputs: {},
  partInputs: {},
  editCount: 0,
  ready: false,
  lastGeneratedKey: "",
  pendingAutoUpdate: false,
  rearMode: false,
};

const REAR_HIDDEN = new Set(["plate", "bird", "shield", "lime", "print_model"]);

const viewer = document.getElementById("viewer");
const canvas = document.getElementById("scene");
const loadingEl = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const dimensionsEl = document.getElementById("dimension-grid");
const warningsEl = document.getElementById("warnings");
const statsEl = document.getElementById("model-stats");
const parametersEl = document.getElementById("parameters");
const logoPlacementEl = document.getElementById("logo-placement");
const partsEl = document.getElementById("parts");
const hudMeta = document.getElementById("hud-meta");
const explodeEl = document.getElementById("explode");
const explodeValue = document.getElementById("explode-value");
const regenerateButton = document.getElementById("regenerate");
const resetButton = document.getElementById("reset");
const centerLogoButton = document.getElementById("center-logo");
const topViewButton = document.getElementById("top-view");
const rearViewButton = document.getElementById("rear-view");
const isoViewButton = document.getElementById("iso-view");
const stlLink = document.getElementById("download-stl");
const tmfLink = document.getElementById("download-3mf");
const dxfLink = document.getElementById("download-dxf");
const toastEl = document.getElementById("toast");

let renderer;
let scene;
let camera;
let controls;
let gridHelper = null;
let modelRoot = null;
let toastTimer = null;
let autoUpdateTimer = null;

function setupThree() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(35, 1, 0.1, 2000);
  camera.up.set(0, 0, 1);
  camera.position.set(95, -115, 95);

  controls = new OrbitControls(camera, canvas);
  controls.target.set(0, 0, 9);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 45;
  controls.maxDistance = 420;
  controls.maxPolarAngle = Math.PI;

  const hemi = new THREE.HemisphereLight(0xe7f4ff, 0x14212d, 1.15);
  scene.add(hemi);

  const key = new THREE.DirectionalLight(0xffffff, 2.15);
  key.position.set(85, -110, 140);
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x7bc8ff, 0.85);
  fill.position.set(-90, 70, 70);
  scene.add(fill);

  const rim = new THREE.DirectionalLight(0x9ee7ff, 0.55);
  rim.position.set(0, 110, 40);
  scene.add(rim);

  gridHelper = new THREE.GridHelper(190, 19, 0x2d455a, 0x1b2b39);
  gridHelper.rotation.x = Math.PI / 2;
  gridHelper.position.z = -0.12;
  gridHelper.material.transparent = true;
  gridHelper.material.opacity = 0.52;
  scene.add(gridHelper);

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(41, 42, 128),
    new THREE.MeshBasicMaterial({ color: 0x1d3345, side: THREE.DoubleSide, transparent: true, opacity: 0.4 })
  );
  ring.position.z = -0.1;
  scene.add(ring);

  const resize = () => {
    const width = Math.max(1, viewer.clientWidth);
    const height = Math.max(1, viewer.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(viewer);
  resize();

  const animate = () => {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();
}

function formatNumber(value, decimals = 1) {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return Number(value).toFixed(decimals);
}

function displayValue(config, rawValue) {
  const value = config.toSlider ? config.toSlider(rawValue) : rawValue;
  return `${formatNumber(value, config.decimals)} ${config.unit}`;
}

function sliderValue(config, rawValue) {
  return config.toSlider ? config.toSlider(rawValue) : rawValue;
}

function paramValue(config, sliderRaw) {
  return config.fromSlider ? config.fromSlider(sliderRaw) : sliderRaw;
}

function buildParameterUI() {
  const cutterFragment = document.createDocumentFragment();
  const logoFragment = document.createDocumentFragment();
  for (const config of PARAM_CONFIG) {
    const row = document.createElement("div");
    row.className = "param";
    row.dataset.key = config.key;

    const head = document.createElement("div");
    head.className = "param-head";

    const label = document.createElement("span");
    label.className = "param-label";
    label.textContent = config.label;

    const output = document.createElement("output");
    output.className = "param-value";
    output.textContent = "—";

    head.append(label, output);

    const input = document.createElement("input");
    input.type = "range";
    input.className = "range";
    input.min = String(config.min);
    input.max = String(config.max);
    input.step = String(config.step);
    input.dataset.key = config.key;
    input.addEventListener("input", () => {
      const raw = paramValue(config, parseFloat(input.value));
      state.params[config.key] = raw;
      output.textContent = displayValue(config, raw);
      if (config.key === "rim_depth") {
        updateHeightBounds();
      }
      markDirty();
      scheduleAutoUpdate();
    });

    row.append(head, input);
    if (config.note) {
      const note = document.createElement("div");
      note.className = "param-note";
      note.textContent = config.note;
      row.append(note);
    }
    const target = config.group === "logo" ? logoFragment : cutterFragment;
    target.append(row);
    state.paramInputs[config.key] = { input, output, config };
  }

  const nozzleRow = document.createElement("div");
  nozzleRow.className = "param";
  const nozzleHead = document.createElement("div");
  nozzleHead.className = "param-head";
  const nozzleLabel = document.createElement("span");
  nozzleLabel.className = "param-label";
  nozzleLabel.textContent = "Print nozzle";
  const nozzleOutput = document.createElement("output");
  nozzleOutput.className = "param-value";
  nozzleOutput.textContent = "0.4 mm";
  nozzleHead.append(nozzleLabel, nozzleOutput);
  const nozzleSelect = document.createElement("select");
  nozzleSelect.className = "select";
  nozzleSelect.id = "nozzle-select";
  for (const nozzle of NOZZLE_OPTIONS) {
    const option = document.createElement("option");
    option.value = String(nozzle);
    option.textContent = `${nozzle.toFixed(1)} mm nozzle`;
    nozzleSelect.append(option);
  }
  nozzleSelect.value = "0.4";
  const nozzleNote = document.createElement("div");
  nozzleNote.className = "param-note";
  nozzleNote.textContent = "Min feature 0.8 mm · layer 0.16 mm";
  nozzleSelect.addEventListener("change", () => {
    const nozzle = parseFloat(nozzleSelect.value);
    state.params.nozzle = nozzle;
    nozzleOutput.textContent = `${nozzle.toFixed(1)} mm`;
    nozzleNote.textContent = `Min feature ${Math.max(0.4, nozzle * 2).toFixed(1)} mm · layer ${(nozzle * 0.4).toFixed(2)} mm`;
    markDirty();
    scheduleAutoUpdate();
  });
  nozzleRow.append(nozzleHead, nozzleSelect, nozzleNote);
  state.paramInputs.nozzle = { input: nozzleSelect, output: nozzleOutput, note: nozzleNote };

  const flatRow = document.createElement("div");
  flatRow.className = "toggle-row";
  const flatLabel = document.createElement("label");
  flatLabel.htmlFor = "flat-back";
  flatLabel.textContent = "Flat rear";
  const flatInput = document.createElement("input");
  flatInput.id = "flat-back";
  flatInput.type = "checkbox";
  flatInput.checked = true;
  flatInput.addEventListener("change", () => {
    state.params.flat_back = flatInput.checked;
    if (flatInput.checked) {
      state.params.vents = false;
      const vents = state.paramInputs.vents;
      if (vents) {
        vents.input.checked = false;
      }
    }
    setVentsUI(flatInput.checked);
    updateHeightBounds();
    markDirty();
    scheduleAutoUpdate();
  });
  flatRow.append(flatLabel, flatInput);
  const flatNote = document.createElement("div");
  flatNote.className = "param-note";
  flatNote.textContent = "Complete flat back; air vents are disabled.";
  state.paramInputs.flat_back = { input: flatInput, output: null, config: null };

  const autoRow = document.createElement("div");
  autoRow.className = "toggle-row";
  const autoLabel = document.createElement("label");
  autoLabel.htmlFor = "auto-offset";
  autoLabel.textContent = "Auto offset";
  const autoInput = document.createElement("input");
  autoInput.id = "auto-offset";
  autoInput.type = "checkbox";
  autoInput.checked = true;
  autoInput.addEventListener("change", () => {
    state.params.logo_auto_offset = autoInput.checked;
    setAutoOffsetUI(autoInput.checked);
    markDirty();
    scheduleAutoUpdate();
  });
  autoRow.append(autoLabel, autoInput);
  state.paramInputs.logo_auto_offset = { input: autoInput, output: null, config: null };

  const ventsRow = document.createElement("div");
  ventsRow.className = "toggle-row";
  const ventsLabel = document.createElement("label");
  ventsLabel.htmlFor = "vents-toggle";
  ventsLabel.textContent = "Air vents";
  const ventsInput = document.createElement("input");
  ventsInput.id = "vents-toggle";
  ventsInput.type = "checkbox";
  ventsInput.addEventListener("change", () => {
    state.params.vents = ventsInput.checked;
    markDirty();
    scheduleAutoUpdate();
  });
  ventsRow.append(ventsLabel, ventsInput);
  state.paramInputs.vents = { input: ventsInput, output: null, config: null };

  parametersEl.append(cutterFragment, nozzleRow, flatRow, flatNote, ventsRow);
  logoPlacementEl.append(logoFragment, autoRow);
}

function setVentsUI(flatBack) {
  const entry = state.paramInputs.vents;
  if (!entry) {
    return;
  }
  entry.input.disabled = Boolean(flatBack);
  const row = entry.input.closest(".toggle-row");
  if (row) {
    row.classList.toggle("disabled", Boolean(flatBack));
  }
}

function setAutoOffsetUI(enabled) {
  for (const key of ["logo_offset_x", "logo_offset_y"]) {
    const entry = state.paramInputs[key];
    if (!entry) {
      continue;
    }
    entry.input.disabled = Boolean(enabled);
    const row = entry.input.closest(".param");
    if (row) {
      row.classList.toggle("disabled", Boolean(enabled));
    }
  }
}

function syncParameterUI(params) {
  state.params = { ...params };
  for (const config of PARAM_CONFIG) {
    const entry = state.paramInputs[config.key];
    if (!entry) {
      continue;
    }
    const value = sliderValue(config, params[config.key]);
    entry.input.value = String(value);
    entry.output.textContent = displayValue(config, params[config.key]);
  }
  const auto = state.paramInputs.logo_auto_offset;
  if (auto) {
    auto.input.checked = Boolean(params.logo_auto_offset);
    setAutoOffsetUI(Boolean(params.logo_auto_offset));
  }
  const nozzle = state.paramInputs.nozzle;
  if (nozzle) {
    nozzle.input.value = String(params.nozzle);
    nozzle.output.textContent = `${formatNumber(params.nozzle, 1)} mm`;
    nozzle.note.textContent = `Min feature ${formatNumber(Math.max(0.4, params.nozzle * 2), 1)} mm · layer ${formatNumber(
      params.nozzle * 0.4,
      2
    )} mm`;
  }
  const flat = state.paramInputs.flat_back;
  if (flat) {
    flat.input.checked = Boolean(params.flat_back);
  }
  const vents = state.paramInputs.vents;
  if (vents) {
    vents.input.checked = params.flat_back ? false : Boolean(params.vents);
    setVentsUI(Boolean(params.flat_back));
  }
  updateHeightBounds();
}

function updateHeightBounds() {
  const entry = state.paramInputs.height;
  if (!entry) {
    return;
  }
  const rim = Number(state.params.rim_depth ?? 10);
  const flat = Boolean(state.params.flat_back);
  const min = flat ? Math.max(7, rim + 3) : Math.max(18, rim + 6);
  entry.input.min = String(min);
  if (parseFloat(entry.input.value) < min) {
    entry.input.value = String(min);
    state.params.height = min;
    entry.output.textContent = displayValue(entry.config, min);
  }
}

function buildPartsUI() {
  partsEl.innerHTML = "";
  state.partInputs = {};
  for (const part of state.parts) {
    const row = document.createElement("label");
    row.className = "part-row";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(part.visible);
    checkbox.addEventListener("change", () => {
      state.partState[part.name].visible = checkbox.checked;
      applyPartState();
    });

    const color = document.createElement("input");
    color.type = "color";
    color.value = part.color;
    color.addEventListener("input", () => {
      state.partState[part.name].color = color.value;
      applyPartState();
    });

    const label = document.createElement("span");
    label.textContent = part.label;

    row.append(checkbox, color, label);
    partsEl.append(row);
    state.partState[part.name] = { visible: Boolean(part.visible), color: part.color };
    state.partInputs[part.name] = { checkbox, color, row };
  }
}

function updatePartsAvailability(flatBack) {
  const entry = state.partInputs.back;
  if (!entry) {
    return;
  }
  const available = Boolean(flatBack);
  entry.row.classList.toggle("disabled", !available);
  entry.checkbox.disabled = !available;
  entry.color.disabled = !available;
  if (!available) {
    entry.checkbox.checked = false;
    state.partState.back.visible = false;
  } else {
    entry.checkbox.checked = true;
    state.partState.back.visible = true;
  }
}

function markDirty() {
  state.editCount += 1;
  regenerateButton.classList.add("dirty");
}

function clearDirty() {
  state.editCount = 0;
  regenerateButton.classList.remove("dirty");
}

function scheduleAutoUpdate(delay = 650) {
  if (!state.ready) {
    return;
  }
  clearTimeout(autoUpdateTimer);
  autoUpdateTimer = setTimeout(() => {
    autoUpdateTimer = null;
    regenerate({ auto: true });
  }, delay);
}

function setLoading(active, text = "Working…") {
  state.loading = active;
  loadingText.textContent = text;
  loadingEl.classList.toggle("active", active);
  regenerateButton.disabled = active;
  resetButton.disabled = active;
  stlLink.setAttribute("aria-disabled", active ? "true" : "false");
  tmfLink.setAttribute("aria-disabled", active ? "true" : "false");
}

function showToast(message, kind = "error") {
  clearTimeout(toastTimer);
  toastEl.textContent = message;
  toastEl.className = `toast visible${kind === "ok" ? " ok" : ""}`;
  toastTimer = setTimeout(() => {
    toastEl.className = "toast";
  }, 4200);
}

function updateInfo(info) {
  state.info = info;
  const cards = [
    ["Cut diameter", `${formatNumber(info.cut_diameter, 1)} mm`],
    ["Overall", `${formatNumber(info.overall_diameter, 1)} mm`],
    ["Wall height", `${formatNumber(info.height, 1)} mm`],
    ["Rim depth", `${formatNumber(info.rim_depth, 1)} mm`],
    ["Wall", `${formatNumber(info.wall, 1)} mm`],
    [
      "Emboss",
      `${formatNumber(info.emboss_bird, 1)} / ${formatNumber(info.emboss_shield, 1)} / ${formatNumber(info.emboss_lime, 1)} mm`,
    ],
  ];
  dimensionsEl.innerHTML = cards
    .map(
      ([label, value]) =>
        `<div class="dim-card"><div class="dim-label">${label}</div><div class="dim-value">${value}</div></div>`
    )
    .join("");

  const warnings = info.warnings || [];
  warningsEl.innerHTML = warnings
    .map((warning) => `<div class="warning">${escapeHtml(warning)}</div>`)
    .join("");

  statsEl.textContent = [
    `Volume ${Math.round(info.volume).toLocaleString()} mm³`,
    `Watertight ${info.watertight ? "yes" : "no"}`,
    `Ring clearance ${formatNumber(info.ring_clearance, 2)} mm`,
    `Logo X ${formatNumber(info.logo_offset_x, 1)} / Y ${formatNumber(info.logo_offset_y, 1)} mm`,
    `Rot ${formatNumber(info.logo_rotation, 0)}°`,
    `Nozzle ${formatNumber(info.nozzle, 1)} mm`,
    `Layer ${formatNumber(info.recommended_layer_height, 2)} mm`,
    info.flat_back
      ? `Flat back ${formatNumber(info.height - info.plate_top, 1)} mm`
      : `Upper cavity ${formatNumber(info.upper_cavity, 1)} mm`,
  ].join(" · ");

  const nozzle = state.paramInputs.nozzle;
  if (nozzle && info.min_feature !== undefined) {
    nozzle.note.textContent = `Min feature ${formatNumber(info.min_feature, 1)} mm · layer ${formatNumber(
      info.recommended_layer_height,
      2
    )} mm`;
  }

  hudMeta.textContent = `${formatNumber(info.cut_diameter, 0)} mm cut · ${formatNumber(
    info.rim_depth,
    1
  )} mm rim · ${formatNumber(info.nozzle, 1)} mm nozzle · ${formatNumber(
    info.emboss_bird,
    1
  )} / ${formatNumber(info.emboss_shield, 1)} / ${formatNumber(info.emboss_lime, 1)} mm emboss`;

  updatePartsAvailability(info.flat_back);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function updateDownloads(urls) {
  state.urls = urls;
  stlLink.href = urls.stl || "#";
  tmfLink.href = urls["3mf"] || "#";
  stlLink.setAttribute("aria-disabled", urls.stl ? "false" : "true");
  tmfLink.setAttribute("aria-disabled", urls["3mf"] ? "false" : "true");
}

function applyPartState() {
  for (const [name, node] of Object.entries(state.nodes)) {
    if (!node) {
      continue;
    }
    const entry = state.partState[name];
    if (!entry) {
      continue;
    }
    node.visible = entry.visible && !(state.rearMode && REAR_HIDDEN.has(name));
    node.traverse((child) => {
      if (!child.isMesh) {
        return;
      }
      if (!child.geometry.attributes.normal) {
        child.geometry.computeVertexNormals();
      }
      if (child.material) {
        child.material.dispose();
      }
      child.material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(entry.color),
        metalness: 0.06,
        roughness: 0.54,
        side: THREE.DoubleSide,
      });
    });
  }
}

function applyExplode() {
  for (const [name, node] of Object.entries(state.nodes)) {
    if (!node) {
      continue;
    }
    const baseZ = node.userData.baseZ ?? node.position.z;
    node.userData.baseZ = baseZ;
    const factor = EXPLODE_FACTORS[name] ?? 0;
    node.position.z = baseZ + state.explode * factor;
  }
}

function disposeModel() {
  if (!modelRoot) {
    return;
  }
  scene.remove(modelRoot);
  modelRoot.traverse((child) => {
    if (child.geometry) {
      child.geometry.dispose();
    }
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach((mat) => mat.dispose());
      } else {
        child.material.dispose();
      }
    }
  });
  modelRoot = null;
  state.nodes = {};
}

function findPart(root, name) {
  return root.getObjectByName(name) || null;
}

function fitCamera(root) {
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) {
    return;
  }
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxSize = Math.max(size.x, size.y, size.z);
  const fitHeight = maxSize / (2 * Math.tan((camera.fov * Math.PI) / 360));
  const fitWidth = fitHeight / Math.max(0.2, camera.aspect);
  const distance = Math.max(fitHeight, fitWidth) * 1.85;
  state.rearMode = false;
  applyPartState();
  camera.up.set(0, 0, 1);
  if (gridHelper) {
    gridHelper.visible = true;
  }
  const direction = new THREE.Vector3(0.45, -0.6, 1.55).normalize();
  camera.position.copy(center).add(direction.multiplyScalar(distance));
  camera.near = Math.max(0.1, distance / 100);
  camera.far = Math.max(1000, distance * 8);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.minDistance = Math.max(30, maxSize * 0.55);
  controls.maxDistance = Math.max(300, distance * 3);
  controls.update();
}

function topView() {
  if (!modelRoot) {
    return;
  }
  const box = new THREE.Box3().setFromObject(modelRoot);
  if (box.isEmpty()) {
    return;
  }
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const distance = Math.max(size.x, size.y) * 1.35;
  state.rearMode = false;
  applyPartState();
  camera.up.set(0, 1, 0);
  camera.position.set(center.x, center.y, center.z + distance);
  camera.near = 0.1;
  camera.far = Math.max(1000, distance * 10);
  camera.updateProjectionMatrix();
  if (gridHelper) {
    gridHelper.visible = true;
  }
  controls.target.copy(center);
  controls.update();
}

function rearView() {
  if (!modelRoot) {
    return;
  }
  const box = new THREE.Box3().setFromObject(modelRoot);
  if (box.isEmpty()) {
    return;
  }
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const distance = Math.max(size.x, size.y, size.z) * 1.45;
  state.rearMode = true;
  applyPartState();
  camera.up.set(0, 1, 0);
  camera.position.set(center.x, center.y, center.z - distance);
  camera.near = 0.1;
  camera.far = Math.max(1000, distance * 10);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  if (gridHelper) {
    gridHelper.visible = false;
  }
  controls.update();
}

function loadModel(url, options = {}) {
  const shouldFit = options.fit !== false;
  return new Promise((resolve, reject) => {
    const loader = new GLTFLoader();
    loader.load(
      url,
      (gltf) => {
        disposeModel();
        modelRoot = gltf.scene;
        scene.add(modelRoot);
        state.nodes = {};
        for (const part of state.parts) {
          const node = findPart(modelRoot, part.name);
          if (node) {
            node.userData.baseZ = node.position.z;
            state.nodes[part.name] = node;
          }
        }
        applyPartState();
        applyExplode();
        if (shouldFit) {
          fitCamera(modelRoot);
        }
        resolve();
      },
      undefined,
      (error) => {
        reject(new Error(error?.message || "Could not load the 3D model."));
      }
    );
  });
}

async function regenerate(options = {}) {
  const auto = Boolean(options.auto);
  if (state.loading) {
    state.pendingAutoUpdate = true;
    return;
  }
  if (!state.ready) {
    return;
  }
  clearTimeout(autoUpdateTimer);
  autoUpdateTimer = null;
  const requestParams = { ...state.params };
  const requestKey = JSON.stringify(requestParams);
  if (auto && requestKey === state.lastGeneratedKey) {
    return;
  }
  setLoading(true, auto ? "Updating model…" : "Regenerating model…");
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestParams),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Generation failed.");
    }
    const currentKey = JSON.stringify(state.params);
    if (currentKey === requestKey) {
      syncParameterUI(data.params);
      state.lastGeneratedKey = JSON.stringify(data.params);
      clearDirty();
    }
    updateInfo(data.info);
    updateDownloads(data.urls);
    await loadModel(data.urls.glb, { fit: false });
    if (!auto && currentKey === requestKey) {
      showToast("Model updated.", "ok");
    }
  } catch (error) {
    showToast(error.message || String(error));
  } finally {
    setLoading(false);
    if (state.pendingAutoUpdate) {
      state.pendingAutoUpdate = false;
      scheduleAutoUpdate(0);
    }
  }
}

async function reset() {
  if (state.loading || !state.defaults) {
    return;
  }
  syncParameterUI(state.defaults);
  await regenerate();
}

async function init() {
  setupThree();
  buildParameterUI();

  regenerateButton.addEventListener("click", regenerate);
  resetButton.addEventListener("click", reset);
  const uploadInput = document.getElementById("logo-upload");
  const uploadButton = document.getElementById("upload-logo");
  uploadButton.addEventListener("click", async () => {
    if (!uploadInput.files.length) {
      showToast("Select an image first.");
      return;
    }
    const file = uploadInput.files[0];
    const form = new FormData();
    form.append("image", file);
    setLoading(true, "Converting image to DXF…");
    try {
      const resp = await fetch("/api/upload", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || "Upload failed");
      }
      if (!data.dxf_name) {
        throw new Error("Image uploaded, but DXF conversion failed.");
      }
      state.params.logo_dxf = data.dxf_name;
      dxfLink.href = data.dxf_url;
      dxfLink.setAttribute("aria-disabled", "false");
      showToast("Image converted to DXF. Regenerating model…", "ok");
      setLoading(false);
      markDirty();
      scheduleAutoUpdate(0);
    } catch (e) {
      setLoading(false);
      showToast(e.message);
    }
  });
  centerLogoButton.addEventListener("click", () => {
    state.params.logo_auto_offset = true;
    state.params.logo_offset_x = 0;
    state.params.logo_offset_y = 0;
    state.params.logo_rotation = 0;
    syncParameterUI(state.params);
    markDirty();
    scheduleAutoUpdate(0);
  });
  topViewButton.addEventListener("click", topView);
  rearViewButton.addEventListener("click", rearView);
  isoViewButton.addEventListener("click", () => {
    if (modelRoot) {
      fitCamera(modelRoot);
    }
  });
  explodeEl.addEventListener("input", () => {
    state.explode = parseFloat(explodeEl.value);
    explodeValue.textContent = `${formatNumber(state.explode, 0)} mm`;
    applyExplode();
  });

  setLoading(true, "Building default model…");
  try {
    const response = await fetch("/api/default");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not load the default model.");
    }
    state.defaults = { ...data.params };
    syncParameterUI(data.params);
    state.parts = data.parts;
    buildPartsUI();
    updateInfo(data.info);
    updateDownloads(data.urls);
    await loadModel(data.urls.glb, { fit: true });
    state.lastGeneratedKey = JSON.stringify(data.params);
    state.ready = true;
    clearDirty();
  } catch (error) {
    showToast(error.message || String(error));
  } finally {
    setLoading(false);
  }
}

init();
