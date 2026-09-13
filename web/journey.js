// Pure, renderer-independent camera and storytelling math; shared with the regression checks.
export const CHAPTERS = ['arrival', 'challenge', 'coordination', 'evidence'];
export const clamp = (value, low=0, high=1) => Math.min(high, Math.max(low, Number.isFinite(value) ? value : low));
const smooth = t => t*t*(3-2*t);
const mix = (a,b,t) => a+(b-a)*t;
const SHOTS = [
  {position:[4.5,6.5,23],target:[0,1,-7]},
  {position:[-16,19,16],target:[0,0,-1]},
  {position:[13,29,13],target:[0,0,-2]},
  {position:[21,21,31],target:[0,0,-2]}
];
export function journeyProgress(scrollY, tops) {
  if (!Array.isArray(tops) || tops.length < 2) return 0;
  for (let i=0; i<tops.length-1; i++) {
    if (scrollY < tops[i+1]) return clamp(i+clamp((scrollY-tops[i])/Math.max(1,tops[i+1]-tops[i])),0,3);
  }
  return 3;
}
export function cameraPose(progress, aspect=1.6) {
  const p=clamp(progress,0,3), index=Math.min(2,Math.floor(p)), t=smooth(p-index);
  const a=SHOTS[index],b=SHOTS[index+1];
  const position=a.position.map((v,i)=>mix(v,b.position[i],t));
  const target=a.target.map((v,i)=>mix(v,b.target[i],t));
  // More scene visible below the reading area on a narrow display.
  if(aspect<.85){position[1]+=5;position[2]+=7;target[1]+=3;}
  return {position,target};
}
export function samplePath(points, phase) {
  const p=clamp(phase), lengths=points.slice(1).map((v,i)=>Math.hypot(v[0]-points[i][0],v[1]-points[i][1]));
  let distance=lengths.reduce((a,b)=>a+b,0)*p;
  for(let i=0;i<lengths.length;i++){
    if(distance<=lengths[i] || i===lengths.length-1){const t=lengths[i]?clamp(distance/lengths[i]):0;return {x:mix(points[i][0],points[i+1][0],t),z:mix(points[i][1],points[i+1][1],t),heading:Math.atan2(points[i+1][0]-points[i][0],points[i+1][1]-points[i][1])};}
    distance-=lengths[i];
  }
  return {x:points[0]?.[0]||0,z:points[0]?.[1]||0,heading:0};
}
export function benchmarkSummary(data) {
  if (!Number.isInteger(data?.total_runs) || !Number.isFinite(data?.collisions) || !Array.isArray(data?.cohorts) || !data.cohorts.length) throw Error('Saved benchmark is incomplete.');
  const rows=data.cohorts.map(row=>{
    const b=row.mean_seconds?.baseline, h=row.mean_seconds?.heuristic, p=row.mean_seconds?.predictive;
    if(!(b>0) || !(h>0) || !(p>0)) throw Error('Saved benchmark times are incomplete.');
    return {gain:(b-h)/b*100,fixedFaster:h<p};
  });
  return {runs:data.total_runs,collisions:data.collisions,total:rows.length,meets:rows.filter(r=>r.gain>=20).length,fixedFaster:rows.filter(r=>r.fixedFaster).length};
}
