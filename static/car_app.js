// 3D Scrollable Car Showcase - Three.js Application (Realistic Custom Renders)

let scene, camera, renderer;
let carGroup, wheels = [];
let roadGrid;
let particles;
let lights = {};

// Materials
let paintMaterial, glassMaterial, wheelMaterial, rimMaterial, brakeDiscMaterial;
let carbonMaterial, grilleMaterial, interiorMaterial, emissiveCyan, emissiveRed, underglowMaterial;

// Scroll state
let currentScroll = 0;
let targetScroll = 0;
const scrollLerpFactor = 0.05; // Smoothing factor for camera movement

// Animation speeds
let wheelSpinSpeed = 0;
let roadMoveSpeed = 0;

// Camera path checkpoints
const cameraPath = [
  {
    progress: 0.0,
    camPos: new THREE.Vector3(3.6, 1.2, 4.8),
    lookAt: new THREE.Vector3(0, 0.35, 0.2)
  },
  {
    progress: 0.25,
    camPos: new THREE.Vector3(-3.5, 0.8, -2.5),
    lookAt: new THREE.Vector3(-0.2, 0.35, -0.6)
  },
  {
    progress: 0.5,
    camPos: new THREE.Vector3(-4.6, 0.45, 0.6),
    lookAt: new THREE.Vector3(0, 0.4, 0)
  },
  {
    progress: 0.75,
    camPos: new THREE.Vector3(2.2, 2.6, 2.2),
    lookAt: new THREE.Vector3(0, 0.3, -0.2)
  },
  {
    progress: 1.0,
    camPos: new THREE.Vector3(1.0, 0.5, 3.8),
    lookAt: new THREE.Vector3(0, 0.35, 0.5)
  }
];

// Initialize Three.js Scene
function init() {
  const container = document.getElementById('canvas-container');
  
  // Scene
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x07080a, 0.075);

  // Camera
  camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.copy(cameraPath[0].camPos);

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  container.appendChild(renderer.domElement);

  // Materials setup
  initMaterials();

  // Create Scene Elements
  createCar();
  createRoad();
  createParticles();
  setupLighting();

  // Event Listeners
  window.addEventListener('resize', onWindowResize);
  window.addEventListener('scroll', onScroll);

  // Set initial scroll state
  onScroll();
  currentScroll = targetScroll;

  // Initialize Configurator UI bindings
  initConfigurator();

  // Start Loop
  animate();
}

function initMaterials() {
  // Ultra-realistic Metallic Paint Material with Clearcoat
  paintMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x00e660,
    metalness: 0.92,
    roughness: 0.08,
    clearcoat: 1.0,
    clearcoatRoughness: 0.03,
    reflectivity: 1.0,
    roughnessMap: null // could add micro-texture noise later if needed
  });

  // Refractive tinted glass for the cockpit
  glassMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x0f1115,
    transparent: true,
    opacity: 0.35,
    transmission: 0.85,
    roughness: 0.03,
    metalness: 0.1,
    ior: 1.55,
    thickness: 0.25,
    side: THREE.DoubleSide
  });

  // Carbon Fiber trim material
  carbonMaterial = new THREE.MeshStandardMaterial({
    color: 0x18191c,
    roughness: 0.45,
    metalness: 0.85
  });

  // Dark matte plastic / grille mesh
  grilleMaterial = new THREE.MeshStandardMaterial({
    color: 0x070809,
    roughness: 0.85,
    metalness: 0.1
  });

  // Interior cockpit seat & steering wheel material
  interiorMaterial = new THREE.MeshStandardMaterial({
    color: 0x1f2128,
    roughness: 0.6,
    metalness: 0.2
  });

  // Rubber Tires
  wheelMaterial = new THREE.MeshStandardMaterial({
    color: 0x151619,
    roughness: 0.75,
    metalness: 0.05
  });

  // Machined aluminum rims
  rimMaterial = new THREE.MeshStandardMaterial({
    color: 0xe5e7eb,
    metalness: 0.95,
    roughness: 0.08
  });

  // High quality steel brake discs
  brakeDiscMaterial = new THREE.MeshStandardMaterial({
    color: 0x9ca3af,
    metalness: 0.95,
    roughness: 0.25
  });

  // Emissive lights (Headlights, Taillights, Underglow)
  emissiveCyan = new THREE.MeshBasicMaterial({
    color: 0x00e660
  });

  emissiveRed = new THREE.MeshBasicMaterial({
    color: 0xfe0979
  });

  underglowMaterial = new THREE.MeshBasicMaterial({
    color: 0x00e660
  });
}

// Procedurally build the realistic sports car model
function createCar() {
  carGroup = new THREE.Group();
  carGroup.position.y = 0.05; 
  scene.add(carGroup);

  // 1. Carbon Fiber Chassis Platform
  const chassisGeo = new THREE.BoxGeometry(1.64, 0.14, 3.8);
  const chassis = new THREE.Mesh(chassisGeo, carbonMaterial);
  chassis.position.y = 0.15;
  chassis.castShadow = true;
  chassis.receiveShadow = true;
  carGroup.add(chassis);

  // 2. Realistic Front Aero Assembly
  const frontAero = new THREE.Group();
  frontAero.position.set(0, 0.15, 1.9);

  // Splitter
  const splitter = new THREE.Mesh(new THREE.BoxGeometry(1.72, 0.04, 0.35), carbonMaterial);
  splitter.position.y = -0.06;
  splitter.castShadow = true;
  frontAero.add(splitter);

  // Splitter struts
  const strutGeo = new THREE.BoxGeometry(0.02, 0.06, 0.02);
  const strutL = new THREE.Mesh(strutGeo, rimMaterial);
  strutL.position.set(-0.3, -0.02, 0.1);
  frontAero.add(strutL);
  const strutR = strutL.clone();
  strutR.position.x = 0.3;
  frontAero.add(strutR);

  // Front bumper grilles (radiator vents)
  const grilleGeo = new THREE.BoxGeometry(0.65, 0.22, 0.1);
  const grilleL = new THREE.Mesh(grilleGeo, grilleMaterial);
  grilleL.position.set(-0.4, 0.1, 0.02);
  grilleL.rotation.y = -0.15;
  frontAero.add(grilleL);

  const grilleR = grilleL.clone();
  grilleR.position.x = 0.4;
  grilleR.rotation.y = 0.15;
  frontAero.add(grilleR);

  carGroup.add(frontAero);

  // 3. Curved Front Hood (Sculpted with central recess)
  const hoodGroup = new THREE.Group();
  hoodGroup.position.set(0, 0.35, 1.15);

  const hoodCenter = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.22, 1.3), paintMaterial);
  hoodCenter.position.set(0, 0.08, 0);
  hoodCenter.castShadow = true;
  hoodCenter.receiveShadow = true;
  hoodGroup.add(hoodCenter);

  // Sloped hood left and right flares (Fenders)
  const fenderL = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.32, 1.3), paintMaterial);
  fenderL.position.set(-0.56, 0.13, 0);
  fenderL.rotation.z = -0.08;
  fenderL.castShadow = true;
  hoodGroup.add(fenderL);

  const fenderR = fenderL.clone();
  fenderR.position.x = 0.56;
  fenderR.rotation.z = 0.08;
  hoodGroup.add(fenderR);

  // Recessed air vents on the hood
  const hoodVentGeo = new THREE.BoxGeometry(0.24, 0.02, 0.6);
  const hoodVentL = new THREE.Mesh(hoodVentGeo, carbonMaterial);
  hoodVentL.position.set(-0.25, 0.2, 0.1);
  hoodVentL.rotation.x = 0.1;
  hoodGroup.add(hoodVentL);

  const hoodVentR = hoodVentL.clone();
  hoodVentR.position.x = 0.25;
  hoodGroup.add(hoodVentR);

  carGroup.add(hoodGroup);

  // 4. Side Skirts & Door Panels (Aerodynamic profiles)
  const sideSkirtL = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.18, 2.1), carbonMaterial);
  sideSkirtL.position.set(-0.84, 0.18, 0);
  sideSkirtL.castShadow = true;
  carGroup.add(sideSkirtL);

  const sideSkirtR = sideSkirtL.clone();
  sideSkirtR.position.x = 0.84;
  carGroup.add(sideSkirtR);

  const doorL = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.44, 1.4), paintMaterial);
  doorL.position.set(-0.76, 0.45, -0.1);
  doorL.castShadow = true;
  carGroup.add(doorL);

  const doorR = doorL.clone();
  doorR.position.x = 0.76;
  carGroup.add(doorR);

  // Side mirrors
  const mirrorLGroup = new THREE.Group();
  mirrorLGroup.position.set(-0.82, 0.75, 0.5);
  const mirrorStem = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.03, 0.03), carbonMaterial);
  mirrorStem.rotation.z = 0.2;
  mirrorLGroup.add(mirrorStem);
  const mirrorCap = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.08, 0.1), paintMaterial);
  mirrorCap.position.set(-0.1, 0.03, -0.02);
  mirrorLGroup.add(mirrorCap);
  carGroup.add(mirrorLGroup);

  const mirrorRGroup = mirrorLGroup.clone();
  mirrorRGroup.position.x = 0.82;
  mirrorRGroup.children[0].rotation.z = -0.2;
  mirrorRGroup.children[1].position.x = 0.1;
  carGroup.add(mirrorRGroup);

  // 5. Rear Engine Deck & Diffuser Tunnel
  const rearDiffuser = new THREE.Mesh(new THREE.BoxGeometry(1.68, 0.16, 0.8), carbonMaterial);
  rearDiffuser.position.set(0, 0.12, -1.9);
  rearDiffuser.castShadow = true;
  carGroup.add(rearDiffuser);

  // Diffuser fins
  for (let i = -3; i <= 3; i++) {
    if (i === 0) continue;
    const fin = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.12, 0.6), carbonMaterial);
    fin.position.set(i * 0.2, 0.08, -1.95);
    carGroup.add(fin);
  }

  // Engine Cover Vent Slots (Hypercar styling)
  const engineCover = new THREE.Group();
  engineCover.position.set(0, 0.58, -1.15);
  
  const coverBase = new THREE.Mesh(new THREE.BoxGeometry(1.42, 0.18, 1.1), paintMaterial);
  coverBase.castShadow = true;
  engineCover.add(coverBase);

  // Vent louvers (louvres)
  for (let l = 0; l < 4; l++) {
    const louver = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.02, 0.12), carbonMaterial);
    louver.position.set(0, 0.10, -0.3 + l * 0.2);
    louver.rotation.x = -0.35;
    engineCover.add(louver);
  }
  carGroup.add(engineCover);

  // 6. Detailed Cockpit & Interior Elements (Visible through glass)
  const interiorGroup = new THREE.Group();
  interiorGroup.position.set(0, 0.24, -0.2);
  
  // Floor tub
  const tub = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.1, 1.2), interiorMaterial);
  tub.position.y = 0.1;
  interiorGroup.add(tub);

  // Dashboard console
  const dash = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.35, 0.35), interiorMaterial);
  dash.position.set(0, 0.38, 0.45);
  interiorGroup.add(dash);

  // Futuristic steering wheel
  const wheelRim = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.02, 8, 24), interiorMaterial);
  wheelRim.position.set(-0.25, 0.46, 0.3);
  wheelRim.rotation.x = 0.3; // tilted back
  interiorGroup.add(wheelRim);

  const wheelCenter = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.14, 0.04), carbonMaterial);
  wheelCenter.position.copy(wheelRim.position);
  wheelCenter.rotation.x = 0.3;
  interiorGroup.add(wheelCenter);

  // Two sports bucket seats
  const seatLGroup = new THREE.Group();
  seatLGroup.position.set(-0.25, 0.2, -0.15);

  const seatCushion = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.16, 0.42), interiorMaterial);
  seatLGroup.add(seatCushion);

  const seatBack = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.54, 0.12), interiorMaterial);
  seatBack.position.set(0, 0.25, -0.2);
  seatBack.rotation.x = -0.22; // reclined
  seatBack.castShadow = true;
  seatLGroup.add(seatBack);

  interiorGroup.add(seatLGroup);

  const seatRGroup = seatLGroup.clone();
  seatRGroup.position.x = 0.25;
  interiorGroup.add(seatRGroup);

  carGroup.add(interiorGroup);

  // 7. Refractive Glass Greenhouse (Cabin)
  const windshieldFrame = new THREE.Mesh(new THREE.BoxGeometry(1.18, 0.44, 1.48), glassMaterial);
  windshieldFrame.position.set(0, 0.82, -0.18);
  windshieldFrame.castShadow = true;
  carGroup.add(windshieldFrame);

  // A-Pillars / Roof Arch (body colored)
  const roofArch = new THREE.Mesh(new THREE.BoxGeometry(1.02, 0.03, 1.15), paintMaterial);
  roofArch.position.set(0, 1.04, -0.22);
  roofArch.rotation.x = 0.03;
  carGroup.add(roofArch);

  const pillarL = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.55, 0.04), paintMaterial);
  pillarL.position.set(-0.55, 0.84, 0.35);
  pillarL.rotation.x = 0.7;
  pillarL.rotation.z = -0.2;
  carGroup.add(pillarL);

  const pillarR = pillarL.clone();
  pillarR.position.x = 0.55;
  pillarR.rotation.z = 0.2;
  carGroup.add(pillarR);

  // 8. Active Double-Wing Rear Spoiler
  const wingGroup = new THREE.Group();
  wingGroup.position.set(0, 0.62, -1.9);

  // Aerodynamic Carbon support arms
  const supportL = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.26, 0.12), carbonMaterial);
  supportL.position.set(-0.55, 0.12, 0.05);
  supportL.rotation.x = -0.2;
  wingGroup.add(supportL);

  const supportR = supportL.clone();
  supportR.position.x = 0.55;
  wingGroup.add(supportR);

  // Main high-downforce wing profile
  const wingBlade = new THREE.Mesh(new THREE.BoxGeometry(1.72, 0.03, 0.36), paintMaterial);
  wingBlade.position.set(0, 0.25, 0);
  wingBlade.rotation.x = -0.06;
  wingBlade.castShadow = true;
  wingGroup.add(wingBlade);

  // Endplates
  const endplateGeo = new THREE.BoxGeometry(0.02, 0.18, 0.44);
  const endplateL = new THREE.Mesh(endplateGeo, carbonMaterial);
  endplateL.position.set(-0.86, 0.25, 0);
  wingGroup.add(endplateL);
  
  const endplateR = endplateL.clone();
  endplateR.position.x = 0.86;
  wingGroup.add(endplateR);

  carGroup.add(wingGroup);

  // 9. Wheels & Detailed Suspension (Machined metal look)
  const wheelPositions = [
    [-0.86, 0.36, 1.15],  // Front Left
    [0.86, 0.36, 1.15],   // Front Right
    [-0.86, 0.36, -1.15], // Back Left
    [0.86, 0.36, -1.15]   // Back Right
  ];

  wheelPositions.forEach((pos, idx) => {
    const wheelHub = new THREE.Group();
    wheelHub.position.set(pos[0], pos[1], pos[2]);

    // Outer tire rubber (rounded profiles)
    const tireGeo = new THREE.CylinderGeometry(0.38, 0.38, 0.32, 40);
    const tire = new THREE.Mesh(tireGeo, wheelMaterial);
    tire.rotation.z = Math.PI / 2;
    tire.castShadow = true;
    wheelHub.add(tire);

    // Tread lines (fine detail)
    const treadCount = 10;
    const treadMat = new THREE.MeshStandardMaterial({ color: 0x0b0c0e, roughness: 0.9 });
    for (let t = 0; t < treadCount; t++) {
      const treadRing = new THREE.Mesh(new THREE.TorusGeometry(0.382, 0.005, 4, 32), treadMat);
      treadRing.rotation.y = Math.PI / 2;
      treadRing.position.x = -0.12 + (t * 0.24) / (treadCount - 1);
      wheelHub.add(treadRing);
    }

    // Deep-dish aluminum rim
    const rimGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.33, 24);
    const rim = new THREE.Mesh(rimGeo, rimMaterial);
    rim.rotation.z = Math.PI / 2;
    wheelHub.add(rim);

    // Realistic Brake Discs (rotors)
    const discGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.05, 24);
    const disc = new THREE.Mesh(discGeo, brakeDiscMaterial);
    disc.rotation.z = Math.PI / 2;
    disc.position.x = pos[0] > 0 ? -0.06 : 0.06;
    wheelHub.add(disc);

    // Detailed Rim Spokes (5-split spoke design)
    const spokesGroup = new THREE.Group();
    spokesGroup.rotation.y = Math.PI / 2;
    const spokeLen = 0.26;
    const spokeG = new THREE.BoxGeometry(0.03, spokeLen, 0.05);

    for (let s = 0; s < 5; s++) {
      const angle = (s * Math.PI * 2) / 5;
      const spoke = new THREE.Mesh(spokeG, rimMaterial);
      spoke.position.set(Math.cos(angle) * (spokeLen / 2), Math.sin(angle) * (spokeLen / 2), pos[0] > 0 ? 0.12 : -0.12);
      spoke.rotation.z = angle;
      wheelHub.add(spoke);
    }

    // Brake caliper (positioned statically inside the wheel fender)
    const caliperGeo = new THREE.BoxGeometry(0.06, 0.12, 0.08);
    const caliperMat = new THREE.MeshStandardMaterial({ color: 0xfe0979, roughness: 0.15, metalness: 0.8 }); // Red calipers
    const caliper = new THREE.Mesh(caliperGeo, caliperMat);
    caliper.position.set(pos[0] > 0 ? -0.11 : 0.11, 0.12, 0.06);

    // Caliper frame attached to car chassis
    const suspensionCal = new THREE.Group();
    suspensionCal.position.copy(wheelHub.position);
    suspensionCal.add(caliper);
    carGroup.add(suspensionCal);

    carGroup.add(wheelHub);
    wheels.push(wheelHub);
  });

  // 10. Front Headlight Enclosures with Projector Nodes
  const lightHousingL = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.06, 0.08), carbonMaterial);
  lightHousingL.position.set(-0.52, 0.34, 1.82);
  lightHousingL.rotation.y = -0.12;
  carGroup.add(lightHousingL);

  const headlightL = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.03, 0.01), emissiveCyan);
  headlightL.position.set(-0.52, 0.34, 1.86);
  headlightL.rotation.y = -0.12;
  carGroup.add(headlightL);

  const lightHousingR = lightHousingL.clone();
  lightHousingR.position.x = 0.52;
  lightHousingR.rotation.y = 0.12;
  carGroup.add(lightHousingR);

  const headlightR = headlightL.clone();
  headlightR.position.x = 0.52;
  headlightR.rotation.y = 0.12;
  carGroup.add(headlightR);

  // 11. Sleek Laser Taillight Bar
  const tailHousing = new THREE.Mesh(new THREE.BoxGeometry(1.44, 0.06, 0.06), carbonMaterial);
  tailHousing.position.set(0, 0.38, -1.97);
  carGroup.add(tailHousing);

  const taillight = new THREE.Mesh(new THREE.BoxGeometry(1.42, 0.02, 0.01), emissiveRed);
  taillight.position.set(0, 0.38, -2.0);
  carGroup.add(taillight);

  // 12. Carbon Diffuser center strip
  const stripe = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.02, 0.8), emissiveCyan);
  stripe.position.set(0, 0.48, 1.25);
  stripe.rotation.x = -0.12;
  carGroup.add(stripe);

  // 13. LED Underglow neon bars
  const underglowSideGeo = new THREE.BoxGeometry(0.05, 0.01, 1.9);
  const underglowSideL = new THREE.Mesh(underglowSideGeo, underglowMaterial);
  underglowSideL.position.set(-0.7, 0.09, 0);
  carGroup.add(underglowSideL);

  const underglowSideR = underglowSideL.clone();
  underglowSideR.position.x = 0.7;
  carGroup.add(underglowSideR);
}

// Procedural grid road floor with glossy wet reflections
function createRoad() {
  const roadWidth = 35;
  const roadLength = 110;
  
  // Custom procedural texture for grid
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  
  // Deep dark carbon-matte background
  ctx.fillStyle = '#060709';
  ctx.fillRect(0, 0, 512, 512);
  
  // Cybernetic neon cyan primary lines
  ctx.strokeStyle = 'rgba(0, 242, 254, 0.22)';
  ctx.lineWidth = 6;
  
  // Main Grid horizontal
  ctx.beginPath();
  ctx.moveTo(0, 256);
  ctx.lineTo(512, 256);
  ctx.stroke();
  
  // Main Grid vertical
  ctx.beginPath();
  ctx.moveTo(256, 0);
  ctx.lineTo(256, 512);
  ctx.stroke();

  // Secondary sub-grid lines for realistic texture scaling
  ctx.strokeStyle = 'rgba(254, 9, 121, 0.06)'; // subtle purple secondary
  ctx.lineWidth = 2;
  
  ctx.beginPath();
  ctx.moveTo(0, 128); ctx.lineTo(512, 128);
  ctx.moveTo(0, 384); ctx.lineTo(512, 384);
  ctx.moveTo(128, 0); ctx.lineTo(128, 512);
  ctx.moveTo(384, 0); ctx.lineTo(384, 512);
  ctx.stroke();

  const gridTexture = new THREE.CanvasTexture(canvas);
  gridTexture.wrapS = THREE.RepeatWrapping;
  gridTexture.wrapT = THREE.RepeatWrapping;
  gridTexture.repeat.set(12, 35);
  gridTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();

  // MeshPhysicalMaterial makes the floor reflect light boxes, headlights, and underglow!
  const roadMat = new THREE.MeshPhysicalMaterial({
    map: gridTexture,
    roughness: 0.25, // Sleek wet reflection
    metalness: 0.8,
    clearcoat: 0.6,
    clearcoatRoughness: 0.2,
    reflectivity: 1.0,
    side: THREE.DoubleSide
  });

  roadGrid = new THREE.Mesh(new THREE.PlaneGeometry(roadWidth, roadLength), roadMat);
  roadGrid.rotation.x = -Math.PI / 2;
  roadGrid.receiveShadow = true;
  scene.add(roadGrid);
}

// Particle System (Embers/Sparkles moving past the car)
function createParticles() {
  const particleCount = 180;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const speeds = [];

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 16; // X
    positions[i * 3 + 1] = Math.random() * 6 + 0.1; // Y
    positions[i * 3 + 2] = (Math.random() - 0.5) * 45; // Z
    
    speeds.push(Math.random() * 0.12 + 0.06);
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  // Glowing particle material
  const particleMat = new THREE.PointsMaterial({
    color: 0x00e660,
    size: 0.06,
    transparent: true,
    opacity: 0.55,
    blending: THREE.AdditiveBlending
  });

  particles = new THREE.Points(geometry, particleMat);
  particles.userData = { speeds: speeds };
  scene.add(particles);
}

// Set up studio and accent lights
function setupLighting() {
  // Ambient light
  const ambient = new THREE.AmbientLight(0x080c14, 0.9);
  scene.add(ambient);

  // Large Overhead Studio Lightbox (Reflected in shiny car shell!)
  const lightBoxGeo = new THREE.PlaneGeometry(8, 12);
  const lightBoxMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
  const lightBox = new THREE.Mesh(lightBoxGeo, lightBoxMat);
  lightBox.position.set(0, 7.5, 0);
  lightBox.rotation.x = Math.PI / 2; // facing down
  scene.add(lightBox);

  // Corresponding overhead directional light for shadows
  lights.overhead = new THREE.DirectionalLight(0xffffff, 2.5);
  lights.overhead.position.set(0, 7.5, 0);
  lights.overhead.castShadow = true;
  lights.overhead.shadow.mapSize.width = 2048;
  lights.overhead.shadow.mapSize.height = 2048;
  lights.overhead.shadow.camera.near = 0.5;
  lights.overhead.shadow.camera.far = 15;
  lights.overhead.shadow.camera.left = -3;
  lights.overhead.shadow.camera.right = 3;
  lights.overhead.shadow.camera.top = 4;
  lights.overhead.shadow.camera.bottom = -4;
  lights.overhead.shadow.bias = -0.0004;
  scene.add(lights.overhead);

  // Soft front key light L
  lights.keyL = new THREE.SpotLight(0xffffff, 45);
  lights.keyL.position.set(6, 5, 7);
  lights.keyL.angle = Math.PI / 6;
  lights.keyL.penumbra = 0.6;
  lights.keyL.castShadow = true;
  lights.keyL.shadow.bias = -0.001;
  scene.add(lights.keyL);

  // Soft front key light R
  lights.keyR = new THREE.SpotLight(0x00e660, 35);
  lights.keyR.position.set(-6, 5, 7);
  lights.keyR.angle = Math.PI / 6;
  lights.keyR.penumbra = 0.6;
  scene.add(lights.keyR);

  // Rim back spotlight
  lights.rim = new THREE.SpotLight(0xfe0979, 45);
  lights.rim.position.set(3, 4.5, -8);
  lights.rim.angle = Math.PI / 5;
  lights.rim.penumbra = 0.7;
  scene.add(lights.rim);

  // Headlights
  lights.headlightL = new THREE.SpotLight(0xffffff, 22);
  lights.headlightL.position.set(-0.52, 0.35, 1.82);
  lights.headlightL.target.position.set(-0.52, 0.1, 15);
  lights.headlightL.angle = Math.PI / 4;
  lights.headlightL.penumbra = 0.8;
  scene.add(lights.headlightL);
  scene.add(lights.headlightL.target);

  lights.headlightR = new THREE.SpotLight(0xffffff, 22);
  lights.headlightR.position.set(0.52, 0.35, 1.82);
  lights.headlightR.target.position.set(0.52, 0.1, 15);
  lights.headlightR.angle = Math.PI / 4;
  lights.headlightR.penumbra = 0.8;
  scene.add(lights.headlightR);
  scene.add(lights.headlightR.target);

  // Underglow light underneath the car
  lights.underglow = new THREE.PointLight(0x00e660, 18, 6.5);
  lights.underglow.position.set(0, -0.08, 0);
  carGroup.add(lights.underglow);
}

// Window resizing
function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

// Scroll interaction
function onScroll() {
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
  const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  
  targetScroll = maxScroll > 0 ? scrollTop / maxScroll : 0;

  // Reveal UI sections
  const sections = document.querySelectorAll('.content-box');
  sections.forEach((sec, index) => {
    const rect = sec.getBoundingClientRect();
    const isVisible = (rect.top < window.innerHeight * 0.85) && (rect.bottom > window.innerHeight * 0.15);
    if (isVisible) {
      sec.classList.add('active');
    } else {
      sec.classList.remove('active');
    }
  });

  // Toggle float configurator
  const configPanel = document.querySelector('.configurator-panel');
  if (targetScroll > 0.08) {
    configPanel.classList.remove('hidden');
  } else {
    configPanel.classList.add('hidden');
  }
}

// Interpolate camera values
function updateCamera(progress) {
  let segmentIndex = 0;
  for (let i = 0; i < cameraPath.length - 1; i++) {
    if (progress >= cameraPath[i].progress && progress <= cameraPath[i + 1].progress) {
      segmentIndex = i;
      break;
    }
  }

  const currentPoint = cameraPath[segmentIndex];
  const nextPoint = cameraPath[segmentIndex + 1];

  const segmentDuration = nextPoint.progress - currentPoint.progress;
  const segmentProgress = segmentDuration > 0 ? (progress - currentPoint.progress) / segmentDuration : 0;

  const easedProgress = easeInOutCubic(segmentProgress);

  // Interpolate camera position
  const targetCamPos = new THREE.Vector3().lerpVectors(currentPoint.camPos, nextPoint.camPos, easedProgress);
  camera.position.lerp(targetCamPos, scrollLerpFactor);

  // Interpolate camera target
  const targetLookAt = new THREE.Vector3().lerpVectors(currentPoint.lookAt, nextPoint.lookAt, easedProgress);
  
  if (!this.camLookTarget) {
    this.camLookTarget = new THREE.Vector3().copy(currentPoint.lookAt);
  }
  this.camLookTarget.lerp(targetLookAt, scrollLerpFactor);
  camera.lookAt(this.camLookTarget);
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Configurator UI bindings
function initConfigurator() {
  const swatches = document.querySelectorAll('.swatch');
  swatches.forEach(swatch => {
    swatch.addEventListener('click', (e) => {
      swatches.forEach(s => s.classList.remove('active'));
      swatch.classList.add('active');

      let paintHexColor = 0x00e660; 
      if (swatch.classList.contains('swatch-dark')) paintHexColor = 0x121316;
      if (swatch.classList.contains('swatch-cyan')) paintHexColor = 0x00f2fe;
      if (swatch.classList.contains('swatch-purple')) paintHexColor = 0xfe0979;
      if (swatch.classList.contains('swatch-gold')) paintHexColor = 0xffd700;

      gsap.to(paintMaterial.color, {
        r: ((paintHexColor >> 16) & 255) / 255,
        g: ((paintHexColor >> 8) & 255) / 255,
        b: (paintHexColor & 255) / 255,
        duration: 0.8
      });
    });
  });

  const underglowToggle = document.getElementById('underglow-color');
  if (underglowToggle) {
    underglowToggle.addEventListener('change', (e) => {
      let activeColor = e.target.checked ? 0xfe0979 : 0x00e660;
      
      gsap.to(lights.underglow.color, {
        r: ((activeColor >> 16) & 255) / 255,
        g: ((activeColor >> 8) & 255) / 255,
        b: (activeColor & 255) / 255,
        duration: 0.5
      });
      
      gsap.to(underglowMaterial.color, {
        r: ((activeColor >> 16) & 255) / 255,
        g: ((activeColor >> 8) & 255) / 255,
        b: (activeColor & 255) / 255,
        duration: 0.5
      });
    });
  }

  const lightsToggle = document.getElementById('headlights-power');
  if (lightsToggle) {
    lightsToggle.addEventListener('change', (e) => {
      const lightsOn = e.target.checked;
      
      gsap.to(lights.headlightL, { intensity: lightsOn ? 22 : 0, duration: 0.3 });
      gsap.to(lights.headlightR, { intensity: lightsOn ? 22 : 0, duration: 0.3 });

      gsap.to(emissiveCyan.color, {
        r: lightsOn ? 0.0 : 0.05,
        g: lightsOn ? 0.95 : 0.05,
        b: lightsOn ? 1.0 : 0.05,
        duration: 0.3
      });
    });
  }
}

// Rendering Loop
function animate() {
  requestAnimationFrame(animate);

  // Smooth out scroll position
  currentScroll += (targetScroll - currentScroll) * scrollLerpFactor;

  // Update Camera based on scroll
  updateCamera(currentScroll);

  // Speed values
  const scrollDelta = Math.abs(targetScroll - currentScroll);
  wheelSpinSpeed = 0.035 + scrollDelta * 0.55;
  roadMoveSpeed = 0.012 + scrollDelta * 0.22;

  // Spin Wheels
  wheels.forEach(wheel => {
    wheel.rotation.x += wheelSpinSpeed;
  });

  // Scroll Road Grid
  if (roadGrid && roadGrid.material.map) {
    roadGrid.material.map.offset.y -= roadMoveSpeed;
  }

  // Animate Particles
  if (particles) {
    const posAttribute = particles.geometry.attributes.position;
    const count = posAttribute.count;
    
    for (let i = 0; i < count; i++) {
      let z = posAttribute.getZ(i);
      z -= particles.userData.speeds[i] * (1.0 + scrollDelta * 12.0);
      
      if (z < -22) {
        z = 22;
        posAttribute.setX(i, (Math.random() - 0.5) * 16);
        posAttribute.setY(i, Math.random() * 6 + 0.1);
      }
      posAttribute.setZ(i, z);
    }
    posAttribute.needsUpdate = true;
    particles.rotation.y += 0.0004;
  }

  // Underglow breathing intensity
  if (lights.underglow) {
    const time = Date.now() * 0.0035;
    lights.underglow.intensity = 18 + Math.sin(time) * 4;
  }

  renderer.render(scene, camera);
}

// Run initialization on load
window.onload = () => {
  init();
  
  const toggleBtn = document.querySelector('.mobile-config-toggle');
  const configPanel = document.querySelector('.configurator-panel');
  if (toggleBtn && configPanel) {
    toggleBtn.addEventListener('click', () => {
      toggleBtn.classList.toggle('active');
      configPanel.classList.toggle('mobile-visible');
    });
  }
};
