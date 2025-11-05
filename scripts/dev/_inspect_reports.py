from pathlib import Path
import json

files = sorted(Path('reports').glob('missing_metrics_full_*.json'))
for p in files:
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        print('ERR reading', p.name, e)
        continue
    sm = obj.get('summary', {})
    plan = obj.get('plan', {})
    print('file:', p.name)
    print('  summary.keys=', list(sm.keys()))
    print('  summary.windows=', sm.get('windows'))
    print('  summary.success_tasks=', sm.get('success_tasks'))
    print('  summary.filter_running=', sm.get('filter_running'))
    print('  plan.filter_running=', plan.get('filter_running'))
    print('  metrics=', (plan.get('metrics') or [])[:5], '...')
    print('')

