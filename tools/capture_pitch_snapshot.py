"""Capture a demonstration frame separately from the benchmark suite."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from transport import ProcessRuntime
from warehouse import make_config

def main():
 config=make_config(200,'warehouse',3,6,'normal','heuristic')
 rt=ProcessRuntime(config)
 try:
  for _ in range(200):rt.step()
  state=rt.world.snapshot();state['policy']='heuristic';state['config_seed']=200
  (root/'evidence/pitch_snapshot.json').write_text(json.dumps(state,indent=2))
  print(json.dumps({k:state[k] for k in ['time','complete','collisions','robots']},indent=2)[:5000])
 finally:rt.close()
if __name__=='__main__':main()
