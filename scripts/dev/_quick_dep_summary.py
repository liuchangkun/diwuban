from pathlib import Path
import csv
p = max(Path('reports').glob('dependency_matrix_*.csv'))
rows = list(csv.DictReader(p.open('r', encoding='utf-8')))
sec_total = sum(int(r['secs_total'] or 0) for r in rows)
sec_all = sum(int(r['secs_match_all'] or 0) for r in rows)
sec_all_run = sum(int(r['secs_match_all_running'] or 0) for r in rows)
count_all_pos = sum(1 for r in rows if int(r['secs_match_all'] or 0) > 0)
count_all_run_pos = sum(1 for r in rows if int(r['secs_match_all_running'] or 0) > 0)
count_all_pos_run_zero = sum(1 for r in rows if int(r['secs_match_all'] or 0) > 0 and int(r['secs_match_all_running'] or 0) == 0)
print('rows:', len(rows))
print('secs_total:', sec_total)
print('secs_match_all:', sec_all)
print('secs_match_all_running:', sec_all_run)
print('method entries with deps_available>0:', count_all_pos)
print('method entries with deps_available_running>0:', count_all_run_pos)
print('deps_available>0 but running=0 entries:', count_all_pos_run_zero)

