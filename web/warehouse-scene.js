import * as THREE from './vendor/three.module.min.js';
import {clamp, cameraPose, samplePath} from './journey.js';

const ROUTES = [
  [[1.5,12],[-2,12],[-2,3],[5,3],[5,-10],[1,-10]],
  [[2,-17],[2,-5],[2,3],[12,3],[12,10]],
  [[4.3,17],[4.3,4],[-4,4],[-4,-13]]
];
const PALETTE = [0x4ade80,0x67e8f9,0xa99bff];

export function buildWarehouse() {
  const scene=new THREE.Scene();
  scene.background=new THREE.Color(0x06101b);
  scene.fog=new THREE.FogExp2(0x071421,.016);
  const materials={
    floor:new THREE.MeshStandardMaterial({color:0x172a38,roughness:.57,metalness:.35}),
    steel:new THREE.MeshStandardMaterial({color:0x284351,roughness:.4,metalness:.75}),
    rail:new THREE.MeshStandardMaterial({color:0x537077,roughness:.42,metalness:.6}),
    shelf:new THREE.MeshStandardMaterial({color:0x223744,roughness:.7,metalness:.4}),
    box:new THREE.MeshStandardMaterial({color:0x786e57,roughness:.9}),
    box2:new THREE.MeshStandardMaterial({color:0x526163,roughness:.9}),
    pallet:new THREE.MeshStandardMaterial({color:0x554b3f,roughness:1}),
    wall:new THREE.MeshStandardMaterial({color:0x112431,roughness:.7}),
    lane:new THREE.MeshBasicMaterial({color:0x4a766d}),
    white:new THREE.MeshStandardMaterial({color:0xc4d9dc,metalness:.48,roughness:.31}),
    rubber:new THREE.MeshStandardMaterial({color:0x08111a,roughness:.85}),
    glass:new THREE.MeshStandardMaterial({color:0x163845,roughness:.12,metalness:.65}),
    glow:new THREE.MeshBasicMaterial({color:0x92e1e2}),
    amber:new THREE.MeshStandardMaterial({color:0xf4b44d,emissive:0xb0651d,emissiveIntensity:.35,roughness:.5})
  };
  const unit=new THREE.BoxGeometry(1,1,1), batches=new Map();
  const box=(material,x,y,z,w,h,d)=>{
    if(!batches.has(material)) batches.set(material,[]);
    batches.get(material).push([x,y,z,w,h,d]);
  };
  box('floor',0,-.22,0,45,.4,53);
  // Open roof and cross aisle keep the camera's route and the AMRs visible.
  for(const x of [-16,-9,9,16]) for(const z of [-17,-10,10,17]) {
    for(const dx of [-2.35,2.35]) for(const dz of [-2.25,2.25]) box('steel',x+dx,3.4,z+dz,.12,6.8,.12);
    for(const y of [.25,2.5,4.75]) {
      box('shelf',x,y,z,4.85,.12,4.65);
      for(const side of [-1,1]) box('rail',x,y+.18,z+side*2.32,4.9,.16,.09);
      for(let c=0;c<3;c++) for(let r=0;r<2;r++){
        const bx=x+(c-1)*1.44,bz=z+(r-.5)*2.18;
        box('pallet',bx,y+.2,bz,1.31,.18,1.88);
        const height=1.05+((c+r+(z>0?1:0))%3)*.21;
        box((c+r)%2?'box':'box2',bx,y+.3+height/2,bz,1.22,height,1.74);
        box('rail',bx,y+.3+height/2,bz+.882,.034,height,.012);
      }
    }
  }
  box('wall',0,4,-25,45,8,.3);
  for(let x=-20;x<=20;x+=5){
    box('steel',x,5,-24.7,.18,10,.18);
    box('glass',x,4,-24.5,3.8,5,.08);
    box('glow',x,7.8,-24.4,3.8,.045,.08);
  }
  for(const z of [-23,23]){
    for(const x of [-21,21])box('steel',x,5,z,.3,10,.3);
    box('steel',0,10,z,42,.23,.23);
    box('glow',0,9.84,z,25,.035,.07);
  }
  for(const x of [-5.7,5.7]) for(let z=-22;z<=22;z+=2)box('lane',x,.004,z,.07,.015,.9);
  for(const z of [-3.1,5.9])for(let x=-20;x<=20;x+=2)box('lane',x,.005,z,.9,.015,.07);
  for(const x of [-2,2,6]){
    box('shelf',x,.04,20,2.8,.08,3.1);
    box('glow',x,.09,21.5,2.7,.03,.04);
  }
  const matrix=new THREE.Matrix4(), quaternion=new THREE.Quaternion();
  for(const [name,items] of batches){
    const mesh=new THREE.InstancedMesh(unit,materials[name],items.length);
    items.forEach(([x,y,z,w,h,d],i)=>{matrix.compose(new THREE.Vector3(x,y,z),quaternion,new THREE.Vector3(w,h,d));mesh.setMatrixAt(i,matrix);});
    mesh.instanceMatrix.needsUpdate=true;mesh.castShadow=!['floor','lane','glow'].includes(name);mesh.receiveShadow=true;mesh.name='warehouse-'+name;scene.add(mesh);
  }
  const grid=new THREE.GridHelper(50,50,0x29434c,0x243b48);grid.position.y=.01;grid.material.transparent=true;grid.material.opacity=.28;scene.add(grid);
  scene.add(new THREE.HemisphereLight(0xb7e9ff,0x0a1e21,2));
  const key=new THREE.DirectionalLight(0xd2f3ff,3.6);key.position.set(10,26,16);key.castShadow=true;
  key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-27,right:27,top:27,bottom:-27,near:1,far:75});key.shadow.bias=-.0007;key.shadow.normalBias=.12;scene.add(key);
  const fill=new THREE.DirectionalLight(0x5fbba8,1.8);fill.position.set(-15,10,-20);scene.add(fill);
  const floorLight=new THREE.PointLight(0x3cf0a4,24,22,2);floorLight.position.set(0,3,4);scene.add(floorLight);

  function meshBox(group,material,x,y,z,w,h,d){const mesh=new THREE.Mesh(unit,material);mesh.position.set(x,y,z);mesh.scale.set(w,h,d);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);return mesh;}
  const robots=PALETTE.map((color,id)=>{
    const group=new THREE.Group();group.name='AMR-'+(id+1);
    const accent=new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.9,roughness:.4});
    meshBox(group,materials.rubber,0,.27,0,1.55,.32,1.92);
    meshBox(group,materials.white,0,.57,0,1.6,.42,1.85);
    meshBox(group,materials.glass,0,.82,0,1.39,.12,1.58);
    meshBox(group,accent,0,.46,.941,1.23,.06,.025);
    meshBox(group,accent,0,.46,-.941,1.23,.06,.025);
    meshBox(group,materials.rubber,0,.7,.937,.62,.09,.03);
    const lid=new THREE.Mesh(new THREE.CylinderGeometry(.17,.2,.13,16),materials.rubber);lid.position.set(0,.95,.2);group.add(lid);
    const eye=new THREE.Mesh(new THREE.CylinderGeometry(.177,.177,.028,16),accent);eye.position.set(0,.98,.2);group.add(eye);
    const wheelGeometry=new THREE.CylinderGeometry(.23,.23,.14,12);wheelGeometry.rotateZ(Math.PI/2);
    for(const x of [-.82,.82]) for(const z of [-.56,.56]){const wheel=new THREE.Mesh(wheelGeometry,materials.rubber);wheel.position.set(x,.24,z);group.add(wheel);}
    for(let i=0;i<=id;i++)meshBox(group,accent,(i-id/2)*.16,.886,-.42,.07,.015,.22);
    const halo=new THREE.Mesh(new THREE.RingGeometry(1.14,1.19,48),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.65,side:THREE.DoubleSide}));halo.rotation.x=-Math.PI/2;halo.position.y=.055;group.add(halo);
    scene.add(group);return {group,halo};
  });
  const routes=ROUTES.map((points,id)=>{
    const curve=new THREE.CurvePath();for(let i=1;i<points.length;i++)curve.add(new THREE.LineCurve3(new THREE.Vector3(points[i-1][0],.045,points[i-1][1]),new THREE.Vector3(points[i][0],.045,points[i][1])));
    const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,60,.038,5,false),new THREE.MeshBasicMaterial({color:PALETTE[id],transparent:true,opacity:.45}));scene.add(mesh);return mesh;
  });
  const barrier=new THREE.Group();barrier.name='illustrative-barrier';
  for(const x of [-2.9,2.9]){meshBox(barrier,materials.rubber,x,.1,0,.7,.15,.85);meshBox(barrier,materials.amber,x,.75,0,.11,1.5,.11);}
  meshBox(barrier,materials.amber,0,1.06,0,6,.32,.13);
  for(let x=-2.6;x<2.8;x+=.7){const stripe=meshBox(barrier,materials.rubber,x,1.06,.075,.27,.33,.022);stripe.rotation.z=-.5;}
  scene.add(barrier);
  const peersGeometry=new THREE.BufferGeometry();peersGeometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(18),3));
  const peers=new THREE.LineSegments(peersGeometry,new THREE.LineDashedMaterial({color:0x67e8f9,dashSize:.3,gapSize:.24,transparent:true,opacity:.55}));scene.add(peers);
  const camera=new THREE.PerspectiveCamera(48,1.6,.1,110);
  function update(progress, time=0, aspect=1.6){
    const p=clamp(progress,0,3),pose=cameraPose(p,aspect);camera.position.fromArray(pose.position);camera.lookAt(...pose.target);
    const phases=[clamp(p/2.8),p<2?clamp(p*.2):clamp(.4+(p-2)*.6),clamp((p-.3)/2.7)];
    robots.forEach(({group,halo},i)=>{const point=samplePath(ROUTES[i],phases[i]);group.position.set(point.x,0,point.z);group.rotation.y=point.heading;halo.material.opacity=.4+Math.sin(time*1.4+i)*.14;});
    barrier.visible=p>.5 && p<2.45;
    routes.forEach(route=>{route.material.opacity=.18+.45*clamp(p-.4);});
    peers.visible=p>1.3 && p<2.85;
    const a=peers.geometry.attributes.position;let n=0;
    for(const [i,j] of [[0,1],[1,2],[2,0]])for(const r of [robots[i],robots[j]])a.setXYZ(n++,r.group.position.x,1.18,r.group.position.z);
    a.needsUpdate=true;peers.computeLineDistances();peers.geometry.computeBoundingSphere();
    return pose;
  }
  update(0);
  function dispose(){
    const geometries=new Set(),mats=new Set(Object.values(materials));
    scene.traverse(object=>{if(object.geometry)geometries.add(object.geometry);if(object.material)for(const m of Array.isArray(object.material)?object.material:[object.material])mats.add(m);if(object.isInstancedMesh)object.dispose();});
    geometries.forEach(geometry=>geometry.dispose());mats.forEach(material=>material.dispose());key.shadow.dispose();
  }
  return {scene,camera,robots,barrier,peers,update,dispose};
}

export function createWarehouse(canvas) {
  let renderer,world;
  try{
    renderer=new THREE.WebGLRenderer({canvas,antialias:false,alpha:false,powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,window.innerWidth<700?1.25:1.5));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
    renderer.shadowMap.enabled=window.innerWidth>=900;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    world=buildWarehouse();
    let aspect=1;
    return {
      resize(width,height){aspect=Math.max(1,width)/Math.max(1,height);world.camera.aspect=aspect;world.camera.updateProjectionMatrix();renderer.setSize(width,height,false);},
      render(progress,time){world.update(progress,time,aspect);renderer.render(world.scene,world.camera);},
      dispose(){world.dispose();renderer.dispose();renderer.forceContextLoss();}
    };
  }catch(error){world?.dispose();renderer?.dispose();throw error;}
}
