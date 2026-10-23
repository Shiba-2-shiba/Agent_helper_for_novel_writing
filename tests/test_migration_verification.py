import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_cli(script, *args):
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str,args)],
                          capture_output=True,text=True)


def migrate(tmp_path, corrupt=False):
    project=tmp_path/'book'
    init=run_cli('init_project.py',project,'--target-total-chars','100000')
    assert init.returncode==0, init.stdout+init.stderr
    if corrupt:
        (project/'runtime').mkdir(exist_ok=True)
        (project/'runtime/approval_ledger.json').write_text('{broken',encoding='utf-8')
    dry=run_cli('migrate_project_state.py','--project',project,'--target-total-chars','200000','--dry-run')
    assert dry.returncode==0,dry.stdout+dry.stderr
    plan=json.loads(dry.stdout)
    result=run_cli('migrate_project_state.py','--project',project,'--apply-plan',plan['plan_path'],
                   '--expected-plan-hash',plan['plan_hash'])
    return project,result,json.loads(result.stdout)


def test_target_apply_reports_readback_and_readonly_health(tmp_path):
    project,result,payload=migrate(tmp_path)
    assert result.returncode==0,result.stdout+result.stderr
    assert payload['status']=='committed'
    assert payload['verification']['planning']['target_total_chars']==200000
    assert payload['verification']['planning']['planning_gate_min_chars']==160000
    assert payload['verification']['health']['status'] in ('pass','warning')
    assert not (project/'runtime/approval_ledger.json').exists()


def test_committed_target_change_does_not_hide_health_failure(tmp_path):
    project,result,payload=migrate(tmp_path,True)
    assert result.returncode==2,result.stdout+result.stderr
    assert payload['status']=='committed'
    assert payload['verification']['status']=='fail'
    assert (project/'runtime/approval_ledger.json').read_text()=='{broken'
    assert 'target_total_chars: 200000' in (project/'agent/state_schema_novel.yaml').read_text()
