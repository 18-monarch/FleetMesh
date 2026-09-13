import {clamp} from './journey.js';

export function filmTime(progress,duration){
  if(!Number.isFinite(duration)||duration<=0)return 0;
  const margin=Math.min(.05,duration/4);
  return margin+clamp(progress)*(duration-2*margin);
}

// A seek controller, never an autoplay loop. At most one decoder request is in flight.
export class ScrollFilm {
  constructor(video,{src,onState=()=>{},paused=false,scheduler={}}){
    this.video=video;this.src=src;this.onState=onState;
    this.raf=scheduler.raf||requestAnimationFrame;this.caf=scheduler.caf||cancelAnimationFrame;
    this.later=scheduler.later||setTimeout;this.cancel=scheduler.cancel||clearTimeout;
    this.paused=paused;this.visible=true;this.progress=0;this.loaded=false;this.loading=false;
    this.failed=false;this.disposed=false;this.inFlight=false;this.frame=0;this.loadTimer=0;this.seekTimer=0;this.lastSeek=-Infinity;this.duration=0;
    this.listeners={
      loadedmetadata:()=>this.metadata(),durationchange:()=>this.metadata(),
      loadeddata:()=>this.ready(),canplay:()=>this.ready(),
      seeked:()=>this.seeked(),error:()=>this.fail()
    };
    for(const [name,listener] of Object.entries(this.listeners))video.addEventListener(name,listener);
    video.muted=true;video.playsInline=true;
    this.publish();
  }
  publish(){
    const state={loaded:this.loaded,paused:this.paused,status:this.failed?'error':this.loading?'loading':this.loaded?(this.paused?'paused':'ready'):'poster'};
    const key=JSON.stringify(state);
    if(key!==this.stateKey){this.stateKey=key;this.onState(state);}
  }
  load(){
    if(this.disposed||this.failed||this.loading||this.loaded)return;
    this.loading=true;this.publish();
    this.loadTimer=this.later(()=>this.fail(),12000);
    try{this.video.preload='auto';this.video.src=this.src;this.video.load();}catch{this.fail();}
  }
  metadata(){
    if(this.disposed||this.failed||!this.loading&&!this.loaded)return;
    const duration=Number(this.video.duration);
    if(!Number.isFinite(duration)||duration<=0){this.fail();return;}
    this.duration=duration;
    if(this.video.readyState>=2)this.ready();
  }
  ready(){
    if(this.disposed||this.failed||this.video.readyState<2)return;
    const duration=Number(this.video.duration);
    if(!Number.isFinite(duration)||duration<=0){this.fail();return;}
    this.duration=duration;this.loaded=true;this.loading=false;
    this.cancel(this.loadTimer);this.loadTimer=0;
    this.video.pause();this.publish();this.request();
  }
  setProgress(value){this.progress=clamp(value);this.request();}
  setPaused(value){
    if(this.disposed)return;
    this.paused=!!value;
    if(this.paused){this.caf(this.frame);this.frame=0;}
    else{if(!this.loaded)this.load();this.request();}
    this.publish();
  }
  setVisible(value){
    this.visible=!!value;
    if(!this.visible){this.caf(this.frame);this.frame=0;}
    else this.request();
  }
  request(){
    if(!this.frame&&!this.disposed&&!this.failed&&this.loaded&&!this.paused&&this.visible&&!this.inFlight&&!this.video.seeking)
      this.frame=this.raf(now=>this.tick(now));
  }
  tick(now){
    this.frame=0;
    if(this.disposed||this.failed||this.paused||!this.visible||!this.loaded||this.inFlight||this.video.seeking)return;
    const destination=filmTime(this.progress,this.duration),current=Number(this.video.currentTime);
    if(!Number.isFinite(current)){this.fail();return;}
    const difference=destination-current;
    if(Math.abs(difference)<=1/48)return;
    if(now-this.lastSeek<32){this.request();return;}
    const next=Math.abs(difference)<.12?destination:current+difference*.35;
    this.inFlight=true;this.lastSeek=now;
    this.cancel(this.seekTimer);this.seekTimer=this.later(()=>this.fail(),8000);
    try{this.video.currentTime=next;}catch{this.fail();}
  }
  seeked(){
    if(this.disposed||this.failed)return;
    this.inFlight=false;this.cancel(this.seekTimer);this.seekTimer=0;
    this.request();
  }
  fail(){
    if(this.disposed||this.failed)return;
    this.failed=true;this.loaded=false;this.loading=false;this.inFlight=false;this.paused=true;
    this.caf(this.frame);this.frame=0;this.cancel(this.loadTimer);this.cancel(this.seekTimer);
    this.loadTimer=0;this.seekTimer=0;
    try{this.video.pause();}catch{}
    this.publish();
  }
  retry(){
    if(this.disposed)return;
    this.failed=false;this.paused=false;this.lastSeek=-Infinity;this.load();
  }
  dispose(){
    if(this.disposed)return;
    this.disposed=true;this.caf(this.frame);this.frame=0;this.cancel(this.loadTimer);this.cancel(this.seekTimer);
    for(const [name,listener] of Object.entries(this.listeners))this.video.removeEventListener(name,listener);
    try{this.video.pause();this.video.removeAttribute('src');this.video.load();}catch{}
  }
}
