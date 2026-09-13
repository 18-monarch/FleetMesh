import {clamp} from './journey.js';

// Show frames from the supplied film without relying on video codecs or seek events.
// Only a small, bounded neighbourhood of the requested frame is kept decoded.
export class ScrollSequence {
  constructor(canvas,{template,count,paused=false,onState=()=>{},imageFactory=()=>new Image(),scheduler={}}){
    this.canvas=canvas;this.context=canvas.getContext('2d',{alpha:false});
    this.template=template;this.count=count;this.paused=paused;this.onState=onState;this.imageFactory=imageFactory;
    this.raf=scheduler.raf||requestAnimationFrame;this.caf=scheduler.caf||cancelAnimationFrame;
    this.later=scheduler.later||setTimeout;this.cancel=scheduler.cancel||clearTimeout;
    this.cache=new Map();this.pending=new Map();this.errors=new Set();
    this.progress=0;this.target=0;this.drawn=-1;this.direction=1;this.frame=0;
    this.visible=true;this.enabled=false;this.failed=false;this.disposed=false;
    this.loaded=false;this.loading=false;this.maxCache=16;this.maxRequests=4;
    this.publish();
  }
  publish(){
    const state={loaded:this.loaded,paused:this.paused,status:this.failed?'error':this.loading?'loading':this.loaded?'ready':'poster'};
    const key=JSON.stringify(state);
    if(key!==this.stateKey){this.stateKey=key;this.onState(state);}
  }
  load(){
    if(this.disposed||this.failed||this.paused)return;
    if(!this.context||!Number.isInteger(this.count)||this.count<2||!this.template.includes('{index}')){this.fail();return;}
    this.enabled=true;this.loading=!this.loaded;this.publish();this.request();
  }
  setProgress(value){
    this.progress=clamp(value);
    const next=Math.round(this.progress*(this.count-1));
    if(next!==this.target)this.direction=next>this.target?1:-1;
    this.target=next;this.request();
  }
  active(){return this.enabled&&!this.disposed&&!this.failed&&!this.paused&&this.visible;}
  request(){if(this.active()&&!this.frame)this.frame=this.raf(()=>{this.frame=0;this.update();});}
  update(){
    if(!this.active())return;
    if(this.cache.has(this.target))this.draw(this.target);
    if(this.errors.has(this.target)){this.fail();return;}
    // Cancel obsolete downloads after a large scroll jump; latest visible frame wins.
    const wanted=[this.target];
    for(let distance=1;distance<=5;distance++)for(const sign of [this.direction,-this.direction]){
      const index=this.target+distance*sign;if(index>=0&&index<this.count)wanted.push(index);
    }
    for(const [index,job] of this.pending)if(!wanted.includes(index))this.abort(index,job);
    for(const index of wanted){
      if(this.pending.size>=this.maxRequests)break;
      if(!this.cache.has(index)&&!this.pending.has(index)&&!this.errors.has(index))this.fetchFrame(index);
    }
  }
  fetchFrame(index){
    const image=this.imageFactory(),job={image,timer:0};this.pending.set(index,job);
    const finish=okay=>{
      if(this.disposed||this.pending.get(index)!==job)return;
      this.cancel(job.timer);image.onload=null;image.onerror=null;this.pending.delete(index);
      if(!okay||!image.naturalWidth){
        try{image.src='';}catch{}
        this.errors.add(index);if(index===this.target){this.fail();return;}
      }else{
        this.cache.set(index,image);this.trim();
        if(index===this.target&&this.active())this.draw(index);
      }
      this.request();
    };
    image.decoding='async';image.onload=()=>finish(true);image.onerror=()=>finish(false);
    job.timer=this.later(()=>finish(false),5000);
    try{image.src=this.template.replace('{index}',String(index).padStart(3,'0'));}catch{finish(false);}
  }
  trim(){
    while(this.cache.size>this.maxCache){
      const farthest=[...this.cache.keys()].sort((a,b)=>Math.abs(b-this.target)-Math.abs(a-this.target))[0];
      this.cache.delete(farthest);
    }
  }
  draw(index){
    if(index===this.drawn)return;
    try{this.context.drawImage(this.cache.get(index),0,0,this.canvas.width,this.canvas.height);}
    catch{this.errors.add(index);this.fail();return;}
    this.drawn=index;this.canvas.dataset.frame=String(index);this.loaded=true;this.loading=false;this.publish();
  }
  abort(index,job){
    this.pending.delete(index);this.cancel(job.timer);job.image.onload=null;job.image.onerror=null;
    try{job.image.src='';}catch{}
  }
  stopRequests(){
    this.caf(this.frame);this.frame=0;
    for(const [index,job] of this.pending)this.abort(index,job);
  }
  setPaused(value){
    if(this.disposed)return;
    this.paused=!!value;
    if(this.paused){this.stopRequests();this.loading=false;}
    else this.load();
    this.publish();
  }
  setVisible(value){
    this.visible=!!value;
    if(!this.visible)this.stopRequests();else this.request();
  }
  fail(){
    if(this.disposed||this.failed)return;
    this.failed=true;this.paused=true;this.loading=false;this.stopRequests();this.publish();
  }
  retry(){
    if(this.disposed)return;
    this.failed=false;this.paused=false;this.errors.clear();this.load();
  }
  dispose(){this.disposed=true;this.stopRequests();this.cache.clear();this.errors.clear();}
}
