import {CHAPTERS,clamp,journeyProgress,benchmarkSummary} from './journey.js';
import {ScrollSequence} from './sequence-player.js';

const byId=id=>document.getElementById(id);
const body=document.body,video=byId('warehouse-film'),toggle=byId('motion-toggle'),status=byId('scene-status');
const sections=CHAPTERS.map(byId),reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
let tops=[],target=0,lastChapter='';

const film=new ScrollSequence(video,{
  template:video.dataset.frames,count:Number(video.dataset.count),paused:reduced.matches,
  onState:state=>{
    toggle.hidden=false;toggle.disabled=false;
    toggle.textContent=state.status==='error'?'Retry motion':state.paused?(state.loaded?'Resume motion':'Enable motion'):'Pause motion';
    toggle.setAttribute('aria-pressed',String(!state.paused));
    body.classList.toggle('scene-ready',state.loaded);
    body.classList.toggle('motion-paused',state.paused);
    status.textContent=state.status==='error'?'Motion unavailable · still view':state.status==='loading'?'Preparing motion…':state.paused?'Motion paused':'Scroll to explore';
  }
});

function updateChapter(){
  const name=CHAPTERS[Math.min(3,Math.round(target))];
  byId('journey-progress').style.transform=`scaleX(${clamp(target/3)})`;
  if(name===lastChapter)return;
  if(lastChapter)body.classList.remove('chapter-'+lastChapter);
  body.classList.add('chapter-'+name);lastChapter=name;
  byId('chapter-number').textContent=String(CHAPTERS.indexOf(name)+1).padStart(2,'0');
  document.querySelectorAll('.floating-nav nav a').forEach(link=>{
    if(link.getAttribute('href')==='#'+name)link.setAttribute('aria-current','step');else link.removeAttribute('aria-current');
  });
}
function onScroll(){target=journeyProgress(window.scrollY,tops);film.setProgress(clamp(target/2));updateChapter();}
function measure(){tops=sections.map(section=>section.getBoundingClientRect().top+window.scrollY);onScroll();}
toggle.addEventListener('click',()=>{if(film.failed)film.retry();else film.setPaused(!film.paused);});
window.addEventListener('scroll',onScroll,{passive:true});
window.addEventListener('resize',measure,{passive:true});
document.addEventListener('visibilitychange',()=>film.setVisible(!document.hidden));
reduced.addEventListener('change',event=>film.setPaused(event.matches));
window.addEventListener('pagehide',event=>{if(event.persisted)film.setVisible(false);else film.dispose();});
window.addEventListener('pageshow',()=>{film.setVisible(!document.hidden);measure();});

async function loadEvidence(){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6500);
  try{
    const response=await fetch('/api/evidence',{signal:controller.signal});
    if(!response.ok)throw Error('Benchmark unavailable');
    const stats=benchmarkSummary(await response.json());
    byId('stat-runs').textContent=String(stats.runs);
    byId('stat-collisions').textContent=String(stats.collisions);
    byId('stat-target').textContent=`${stats.meets} / ${stats.total}`;
    byId('evidence-detail').textContent=`Saved development benchmark: ${stats.runs} runs across ${stats.total} cohorts. The fixed rule is faster than the learned policy in ${stats.fixedFaster} of ${stats.total} cohort means. Time includes final delivery and return to dock. All four policies and benchmark limits are available in the console.`;
  }catch{
    byId('evidence-detail').textContent='Saved benchmark could not be loaded. Keep the FleetMesh terminal open and refresh. You can still enter the console and inspect available records.';
  }finally{clearTimeout(timer);byId('evidence-grid').setAttribute('aria-busy','false');}
}
measure();film.setVisible(!document.hidden);loadEvidence();if(!reduced.matches)film.load();
