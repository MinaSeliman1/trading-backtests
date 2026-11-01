import pytest
from qqq_eod import cloud as c
ID={'repository':'MinaSeliman1/trading-backtests','workflow_id':7,'generation':'v1','branch':'main'}
def run(i,conclusion='success',active=True):return dict(id=i,run_number=i,run_attempt=1,head_sha=str(i)*40,repository=ID['repository'],workflow_id=7,branch='main',generation='v1',active=active,status='completed',conclusion=conclusion)
def artifact(r):return dict(id=r['id'],name='qqq-eod-state-v1-'+str(r['id'])+'-1',run_id=r['id'],run_attempt=1,head_sha=r['head_sha'],branch='main',expired=False)

def test_latest_uploaded_state_is_authoritative_even_if_run_failed():
 a=run(1);b=run(2,'failure')
 assert c.select_head([a,b],[artifact(a),artifact(b)],ID)['id']==2
 b['conclusion']='cancelled';assert c.select_head([a,b],[artifact(a),artifact(b)],ID)['id']==2

def test_missing_latest_artifact_never_falls_back():
 a=run(1);b=run(2)
 with pytest.raises(ValueError):c.select_head([a,b],[artifact(a)],ID)
 b['conclusion']='failure'
 with pytest.raises(ValueError):c.select_head([a,b],[artifact(a)],ID)

def test_foreign_branch_or_workflow_cannot_supply_state():
 a=run(1);bad=run(2);bad['branch']='pull-request'
 assert c.select_head([a,bad],[artifact(a),artifact(bad)],ID)['id']==1
 bad=run(2);bad['workflow_id']=99
 assert c.select_head([a,bad],[artifact(a),artifact(bad)],ID)['id']==1

def test_expired_or_wrong_head_is_fatal():
 a=run(1);x=artifact(a);x['expired']=True
 with pytest.raises(ValueError):c.select_head([a],[x],ID)
 x=artifact(a);x['head_sha']='wrong'
 with pytest.raises(ValueError):c.select_head([a],[x],ID)

def test_inactive_verify_runs_are_not_initialized_generations():
 assert c.select_head([run(1,active=False)],[],ID) is None

def test_initialization_only_before_first_statistical_date():
 assert c.may_initialize('2026-11-02','2026-11-01T22:00:00-05:00',False)
 assert not c.may_initialize('2026-11-02','2026-11-02T00:00:00-05:00',False)
 assert not c.may_initialize('2026-11-02','2026-11-01T22:00:00-05:00',True)
