"""HTTP + actual Oracle smoke tests (no mock DB, no fake success).

Requires API running and Oracle 23ai schema installed/migrated.
--write commits test records and is for disposable DBs only; always tries cleanup.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from uuid import uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

parser=argparse.ArgumentParser()
parser.add_argument('--base',default='http://127.0.0.1:8000')
parser.add_argument('--token',default=os.getenv('LINKO_TOKEN',''),help='Bearer JWT; use Admin role if --write')
parser.add_argument('--write',action='store_true',help='mutating integration tests; use a disposable DEMO PDB only')
args=parser.parse_args()
if not args.token: parser.error('LINKO_TOKEN hoặc --token bắt buộc. Dùng Admin cho --write.')
base=args.base.rstrip('/')

def http(path, method='GET', payload=None):
    data=None if payload is None else json.dumps(payload).encode('utf-8')
    headers={'Content-Type':'application/json'}
    if args.token:headers['Authorization']='Bearer '+args.token
    req=Request(base+path, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=60) as response:
            value=response.read().decode()
            return json.loads(value), response.status
    except HTTPError as e:
        detail=e.read().decode(errors='replace')
        raise RuntimeError(f'{method} {path}: HTTP {e.code}: {detail[:700]}') from e

def check(label,path,method='GET',payload=None):
    obj,code=http(path,method,payload)
    print(f'PASS {label}: HTTP {code}')
    return obj

def teammate_pair_exists(a,b):
    records=check('Knows relation scan',f'/api/connections?employee_id={a}&limit=500')
    return (any(int(x['from_emp'])==a and int(x['to_emp'])==b and x['connection_type']=='TEAMMATE' for x in records)
            and any(int(x['from_emp'])==b and int(x['to_emp'])==a and x['connection_type']=='TEAMMATE' for x in records))

try:
    check('API process','/api/live')
    health=check('Oracle connection','/api/health')
    assert health['status']=='ok' and health['database']
    ready=check('Oracle schema and SQL graph','/api/ready')
    assert ready['status']=='ready'
    employees=check('Oracle employees','/api/employees?limit=10')
    assert isinstance(employees,list)
    check('Oracle departments','/api/departments')
    check('Oracle projects','/api/projects')
    overview=check('Oracle graph totals','/api/stats')
    assert 'vertices' in overview
    print('Current rows:',overview['vertices'],overview['edges'])
    check('Data integrity','/api/network/integrity')
    check('Department connections','/api/stats/cross-department')
    check('Project collaboration','/api/stats/project-collaboration')
    if employees:
        emp_id=employees[0]['employee_id']
        check('PLSQL employee profile',f'/api/employees/{emp_id}/profile')
        check('GRAPH_TABLE k hops',f'/api/graph/khops/{emp_id}?k=1')
    result=check('GRAPH_TABLE shortest path','/api/graph/shortest-path','POST',
                 {'source_id':3,'target_id':1,'max_hops':1,'include_projects':False})
    assert result['found'] and result['path_length']==1,'Seed path 3->1 must have 1 hop'
    if args.write:
        suffix=uuid4().hex[:12]
        deps=[];projects=[];people=[]
        try:
            department=check('INSERT temporary department','/api/departments','POST',
                             {'department_name':'SMOKE_TEMP_'+suffix,'location':'TEST'})
            deps.append(int(department['department_id']))
            for number in range(2):
                project=check('INSERT temporary project','/api/projects','POST',
                              {'project_name':f'SMOKE_TEMP_{suffix}_{number}', 'department_id':deps[0]})
                projects.append(int(project['project_id']))
            for number in range(2):
                person=check('INSERT temporary employee','/api/employees','POST',
                             {'full_name':f'Smoke Agent {number}',
                              'email':f'smoke.{suffix}.{number}@example.invalid',
                              'department_id':deps[0]})
                people.append(int(person['employee_id']))
            for project_id in projects:
                for employee_id in people:
                    check('Assign member',f'/api/projects/{project_id}/members','POST',
                          {'employee_id':employee_id,'role':'MEMBER'})
            assert teammate_pair_exists(*people),'Bidirectional auto TEAMMATE missing after insert'
            for employee_id in people:
                check('Delete first-project membership',f'/api/projects/{projects[0]}/members/{employee_id}', 'DELETE')
            assert teammate_pair_exists(*people),'TEAMMATE removed while 2nd project still shared'
            for employee_id in people:
                check('Delete last shared membership',f'/api/projects/{projects[1]}/members/{employee_id}', 'DELETE')
            assert not teammate_pair_exists(*people),'Stale TEAMMATE after last shared project removed'
            integrity=check('No orphaned TEAMMATEs','/api/network/integrity')
            assert integrity['status']=='ok',integrity
        finally:
            # Delete memberships and records in FK-safe order on any test failure.
            for project_id in projects:
                for employee_id in people:
                    try:http(f'/api/projects/{project_id}/members/{employee_id}','DELETE')
                    except Exception:pass  # Already removed or never inserted
            for employee_id in people:
                try:http(f'/api/employees/{employee_id}?hard=true&confirm=true','DELETE');print('CLEANUP EMPLOYEE',employee_id)
                except Exception as exc:print('CLEANUP EMPLOYEE FAILED:',exc,file=sys.stderr)
            for project_id in projects:
                try:http(f'/api/projects/{project_id}','DELETE');print('CLEANUP PROJECT',project_id)
                except Exception as exc:print('CLEANUP PROJECT FAILED:',exc,file=sys.stderr)
            for dep_id in deps:
                try:http(f'/api/departments/{dep_id}','DELETE');print('CLEANUP DEPARTMENT',dep_id)
                except Exception as exc:print('CLEANUP DEPARTMENT FAILED:',exc,file=sys.stderr)
    print('PASS: all selected HTTP tests reached actual Oracle APIs.')
except (AssertionError,RuntimeError,URLError) as exc:
    print('FAIL:',exc,file=sys.stderr)
    sys.exit(1)
