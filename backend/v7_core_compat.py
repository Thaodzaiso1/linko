"""Real Oracle compatibility routes for the *in-scope* Linko V7 directory/graph UI.

No mocks. V7 auth, feeds, chats, and SQLite-only extras are deliberately excluded
because they are not part of the project's seven-table relational/graph schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from database import query_all, query_one, scalar
from exceptions import api_error
from graph_service import find_employee, shortest_path, stats
from schemas import ShortestPathRequest


class LegacyPath(BaseModel):
    from_id: int = Field(gt=0)
    to_id: int = Field(gt=0)
    max_hops: int = Field(default=6, ge=1, le=6)


def make_compat_router(db_action):
    r=APIRouter(prefix='/api', tags=['Linko V7 Oracle compatibility'])

    @r.post('/paths/shortest')
    def path_shortest(body:LegacyPath):
        def op(c):
            outcome=shortest_path(c,ShortestPathRequest(source_id=body.from_id,target_id=body.to_id,max_hops=body.max_hops))
            if not outcome['found']:
                return {'found':False,'message':outcome['message'],'path_length':None,'nodes':[],'steps':[]}
            ids=[outcome['steps'][0]['from_id']]+[s['to_id'] for s in outcome['steps']]
            params={f'id_{i}':v for i,v in enumerate(ids)}
            listing=query_all(c,'SELECT e.employee_id,e.full_name,e.title,e.email,e.department_id,e.status '
                'FROM employees e WHERE employee_id IN ('+', '.join(':'+p for p in params)+')',params)
            byid={x['employee_id']:x for x in listing}
            ordered=[byid[i] for i in ids]
            return {'found':True,'path_length':outcome['path_length'],'message':outcome['message'],
                    'nodes':ordered,'from':ordered[0],'to':ordered[-1],
                    'steps':[{'from_id':s['from_id'],'from_name':s['from_name'],'to_id':s['to_id'],
                              'to_name':s['to_name'],'relation':s['relation_category'],
                              'relation_type':s['relation_detail']} for s in outcome['steps']]}
        return db_action(op)

    @r.get('/employees/{employee_id}/connections')
    def direct_connections(employee_id:int):
        def op(c):
            find_employee(c,employee_id)
            return query_all(c,'''SELECT DISTINCT e.employee_id,e.full_name,e.email,e.title,e.department_id,
                d.department_name,e.status,k.connection_type AS relation_type,'Knows' AS relation
                FROM knows k JOIN employees e ON e.employee_id=CASE WHEN k.from_emp=:id THEN k.to_emp ELSE k.from_emp END
                LEFT JOIN departments d ON d.department_id=e.department_id
                WHERE k.from_emp=:id OR k.to_emp=:id
                ORDER BY e.full_name''',{'id':employee_id})
        return db_action(op)

    @r.get('/employees/{employee_id}/teammates')
    def teammates(employee_id:int):
        def op(c):
            find_employee(c,employee_id)
            return query_all(c,'''SELECT DISTINCT e.employee_id,e.full_name,e.email,e.title,e.status,
                e.department_id,d.department_name
                FROM project_members pm1 JOIN project_members pm2 ON pm1.project_id=pm2.project_id
                JOIN employees e ON pm2.employee_id=e.employee_id
                LEFT JOIN departments d ON e.department_id=d.department_id
                WHERE pm1.employee_id=:id AND pm2.employee_id<>:id ORDER BY e.full_name''',{'id':employee_id})
        return db_action(op)

    @r.get('/employees/{employee_id}/managers')
    def managers(employee_id:int):
        def op(c):
            find_employee(c,employee_id)
            return query_all(c,'''SELECT m.employee_id,m.full_name,m.title,m.status,m.department_id,
                LEVEL AS depth FROM employees m
                JOIN reports_to r ON r.manager_id=m.employee_id
                START WITH r.employee_id=:id
                CONNECT BY NOCYCLE PRIOR r.manager_id=r.employee_id''',{'id':employee_id})
        return db_action(op)

    @r.get('/employees/{employee_id}/stats')
    def employee_stats(employee_id:int):
        def op(c):
            find_employee(c,employee_id)
            return query_one(c,'''SELECT
                (SELECT COUNT(*) FROM knows WHERE from_emp=:id) AS outgoing,
                (SELECT COUNT(*) FROM knows WHERE to_emp=:id) AS incoming,
                (SELECT COUNT(*) FROM project_members WHERE employee_id=:id) AS projects
                FROM dual''',{'id':employee_id})
        return db_action(op)

    @r.get('/employees/{employee_id}/common/{other_id}')
    def common(employee_id:int,other_id:int):
        def op(c):
            find_employee(c,employee_id);find_employee(c,other_id)
            return query_all(c,'''SELECT DISTINCT e.employee_id,e.full_name,e.email,e.title,e.status,e.department_id
                FROM employees e WHERE e.employee_id NOT IN (:a,:b)
                AND EXISTS (SELECT 1 FROM knows k WHERE (k.from_emp=:a AND k.to_emp=e.employee_id)
                    OR (k.to_emp=:a AND k.from_emp=e.employee_id))
                AND EXISTS (SELECT 1 FROM knows k WHERE (k.from_emp=:b AND k.to_emp=e.employee_id)
                    OR (k.to_emp=:b AND k.from_emp=e.employee_id))
                ORDER BY e.full_name''',{'a':employee_id,'b':other_id})
        return db_action(op)

    @r.get('/stats/overview')
    def stats_overview():
        def op(c):
            val=stats(c)
            return {'employees':val['vertices']['employees'],'departments':val['vertices']['departments'],
                    'projects':val['vertices']['projects'],'edges_total':val['edges']['total'],
                    'edges_knows':val['edges']['knows'],'edges_reports_to':val['edges']['reports_to'],
                    'edges_works_on':val['edges']['works_on'],'mode':'oracle23ai'}
        return db_action(op)

    @r.get('/departments/stats')
    def dept_stats():
        return db_action(lambda c:query_all(c,'''SELECT d.department_id,d.department_name,d.location,
            COUNT(DISTINCT e.employee_id) AS employee_count, COUNT(DISTINCT p.project_id) AS project_count
            FROM departments d LEFT JOIN employees e ON e.department_id=d.department_id
            LEFT JOIN projects p ON p.department_id=d.department_id
            GROUP BY d.department_id,d.department_name,d.location ORDER BY d.department_id'''))

    @r.get('/departments/{department_id}/employees')
    def dept_employees(department_id:int):
        return db_action(lambda c:query_all(c,'''SELECT employee_id,full_name,email,title,status,department_id
            FROM employees WHERE department_id=:id ORDER BY full_name''',{'id':department_id}))

    @r.get('/departments/{department_id}/projects')
    def dept_projects(department_id:int):
        return db_action(lambda c:query_all(c,'''SELECT project_id,project_name,status,start_date,end_date,department_id
            FROM projects WHERE department_id=:id ORDER BY project_name''',{'id':department_id}))

    @r.get('/org/summary')
    def org_summary():
        return db_action(lambda c:query_one(c,'''SELECT
            (SELECT COUNT(*) FROM departments) AS departments,
            (SELECT COUNT(*) FROM projects) AS projects,
            (SELECT COUNT(*) FROM employees) AS employees,
            (SELECT COUNT(*) FROM projects WHERE status='ACTIVE') AS active_projects FROM dual'''))

    @r.get('/graph/degree/{employee_id}')
    def graph_degree(employee_id:int):
        def op(c):
            find_employee(c,employee_id)
            outgoing=scalar(c,'SELECT COUNT(*) FROM knows WHERE from_emp=:id',{'id':employee_id})
            incoming=scalar(c,'SELECT COUNT(*) FROM knows WHERE to_emp=:id',{'id':employee_id})
            bytype=query_all(c,'''SELECT connection_type,COUNT(*) AS total FROM knows
                WHERE from_emp=:id OR to_emp=:id GROUP BY connection_type''',{'id':employee_id})
            touching=scalar(c,'''SELECT COUNT(*) FROM knows WHERE from_emp=:id OR to_emp=:id''',{'id':employee_id})
            return {'out_degree':outgoing,'in_degree':incoming,
                    'total_touching':touching,'by_type':{row['connection_type']:row['total'] for row in bytype}}
        return db_action(op)

    @r.get('/paths/exists')
    def path_exists(from_id:int=Query(gt=0),to_id:int=Query(gt=0)):
        def op(c):
            result=shortest_path(c,ShortestPathRequest(source_id=from_id,target_id=to_id,max_hops=6))
            return {'exists':result['found'],'path_length':result['path_length']}
        return db_action(op)

    @r.get('/metrics')
    def metrics():
        def op(c):
            val=stats(c)
            return {'version':'6.0.0','mode':'oracle23ai','employees':val['vertices']['employees'],
                    'edges':val['edges']['total'],
                    'edges_by_type':{row['connection_type']:row['total'] for row in val['connection_types']}}
        return db_action(op)

    @r.get('/dashboard/overview')
    def dashboard_overview():
        def op(c):
            val=stats(c)
            deps=query_all(c,'''SELECT d.department_id,d.department_name AS name,COUNT(e.employee_id) AS employee_count,
                (SELECT COUNT(*) FROM projects p WHERE p.department_id=d.department_id) AS project_count
                FROM departments d LEFT JOIN employees e ON d.department_id=e.department_id
                GROUP BY d.department_id,d.department_name ORDER BY d.department_id''')
            top=query_all(c,'''SELECT e.employee_id,e.full_name AS name,e.title,d.department_name AS department,
                (SELECT COUNT(*) FROM knows k WHERE k.from_emp=e.employee_id OR k.to_emp=e.employee_id) AS connections
                FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id
                WHERE e.status='ACTIVE' ORDER BY connections DESC FETCH FIRST 10 ROWS ONLY''')
            projects=query_all(c,'''SELECT p.project_id,p.project_name AS name,p.status,
                d.department_name AS department FROM projects p
                LEFT JOIN departments d ON d.department_id=p.department_id
                ORDER BY p.project_id FETCH FIRST 25 ROWS ONLY''')
            return {'generated_at':datetime.now(timezone.utc).isoformat(),
                    'stats':{'employees':val['vertices']['employees'],'departments':val['vertices']['departments'],
                        'projects':val['vertices']['projects'],'edges_total':val['edges']['total'],
                        'edges_knows':val['edges']['knows'],'edges_reports_to':val['edges']['reports_to'],
                        'edges_works_on':val['edges']['works_on'],'mode':'oracle23ai'},
                    'departments':deps,'relationships':[{'key':r['connection_type'], 'name':r['connection_type'],
                            'count':r['total']} for r in val['connection_types']],
                    'top_people':top,'projects':projects}
        return db_action(op)

    return r
