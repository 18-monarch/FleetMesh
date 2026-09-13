"""Rebuild the model and compare policies on fixed paired scenarios.
Training: compact map, seeds 0-11. Test: seeds 200-207 on three map sizes.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path
from simulation import Simulation
from warehouse import make_config

ROOT = Path(__file__).resolve().parent

def fit(rows):
    a = [[sum(r['features'][i]*r['features'][j] for r in rows)+(.1 if i == j else 0) for j in range(3)] for i in range(3)]
    b = [sum(r['features'][i]*r['wait'] for r in rows) for i in range(3)]
    for i in range(3):
        k = max(range(i, 3), key=lambda k: abs(a[k][i])); a[i], a[k] = a[k], a[i]; b[i], b[k] = b[k], b[i]
        pivot = a[i][i]; a[i] = [v/pivot for v in a[i]]; b[i] /= pivot
        for k in range(3):
            if k != i:
                value = a[k][i]; a[k] = [v-value*w for v, w in zip(a[k], a[i])]; b[k] -= value*b[i]
    return b

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--seeds', type=int, default=8); args = parser.parse_args()
    evidence = ROOT/'evidence'; evidence.mkdir(exist_ok=True)
    rows = []
    for seed in range(12):
        simulation = Simulation(make_config(seed, 'compact', job_count=6, mode='baseline'))
        simulation.run()
        for agent in simulation.agents:
            rows.extend(dict(row, seed=seed, robot=agent.id) for row in agent.samples)
    model = {'version': 1, 'type': 'ridge regression', 'features': ['bias', 'remaining_peer_hold_seconds', 'waiting_peers'],
             'weights': fit(rows), 'training_map': 'compact', 'training_seeds': list(range(12)),
             'training_samples': len(rows), 'limits': 'Synthetic road-zone waits. No physical robot validation.'}
    (ROOT/'model.json').write_text(json.dumps(model, indent=2))
    (evidence/'training.json').write_text(json.dumps(rows))
    print('Trained',len(rows),'samples:',model['weights'], flush=True)
    results = []
    for map_name, scenario in [('compact','normal'),('warehouse','normal'),('extended','congestion'),('warehouse','network'),('warehouse','blocked')]:
        for seed in range(200,200+args.seeds):
            for mode in ['baseline','atomic','heuristic','predictive']:
                result = Simulation(make_config(seed,map_name,job_count=6,scenario=scenario,mode=mode),model).run()
                results.append(result)
        print('Evaluated', map_name, scenario, flush=True)
    with (evidence/'benchmark.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=results[0].keys());writer.writeheader();writer.writerows(results)
    summary=[]
    for map_name, scenario in dict.fromkeys((r['map'],r['scenario']) for r in results):
        cohort=[r for r in results if r['map']==map_name and r['scenario']==scenario]
        means={mode:statistics.mean(r['seconds'] for r in cohort if r['mode']==mode) for mode in ['baseline','atomic','heuristic','predictive']}
        summary.append({'map':map_name,'scenario':scenario,'seeds':args.seeds,'mean_seconds':means,
                        'predictive_change_pct':100*(means['baseline']-means['predictive'])/means['baseline'],
                        'collisions':sum(r['collisions'] for r in cohort),'completed':sum(r['completed'] for r in cohort),'runs':len(cohort)})
    document={'version':'1.0.0','metric':'Mission makespan: start through final delivery and return to dock',
              'training':{k:v for k,v in model.items() if k!='weights'},'cohorts':summary,
              'total_runs':len(results),'collisions':sum(r['collisions'] for r in results),
              'completed':sum(r['completed'] for r in results),
              'limits':['Finite synthetic scenarios; shared graph families.','No physical, Wi-Fi or certification claims.','No general 20% guarantee.','No statistical confidence intervals.']}
    (evidence/'summary.json').write_text(json.dumps(document,indent=2));print(json.dumps(document,indent=2))
if __name__=='__main__':
    main()
