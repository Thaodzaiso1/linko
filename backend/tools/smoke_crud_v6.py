#!/usr/bin/env python3
"""Opt-in real HTTP -> FastAPI -> Oracle CRUD smoke test.

Creates two new test employees + department + project; cleans up its own records.
Never uses static IDs or mock data; Oracle must be running and SQL setup complete.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


class Client:
    def __init__(self, url, token):
        self.url = url.rstrip('/')
        self.headers = {'Content-Type': 'application/json'}
        if token: self.headers['Authorization'] = 'Bearer ' + token

    def call(self, method, path, data=None, allow_error=False):
        payload = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
        request = Request(self.url + path, data=payload, method=method, headers=self.headers)
        try:
            with urlopen(request, timeout=25) as response:
                result = json.loads(response.read().decode('utf-8'))
                status = response.status
        except HTTPError as exc:
            status = exc.code
            result = json.loads(exc.read().decode('utf-8'))
        except URLError as exc:
            raise RuntimeError('Không kết nối được API: ' + str(exc)) from exc
        if status >= 400 and not allow_error:
            raise RuntimeError(f'{method} {path}: HTTP {status} {result}')
        return status, result


def check(condition, title):
    if not condition:
        raise AssertionError(title)
    print('  OK:', title)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--write', action='store_true', help='Bắt buộc để xác nhận sẽ ghi/xóa các bản ghi mới tạo.')
    args = parser.parse_args()
    if not args.write:
        parser.error('Thêm --write để chạy smoke test có INSERT/UPDATE/DELETE trên Oracle TEST/DEMO.')

    token=os.getenv('LINKO_TOKEN','')
    if not token: parser.error('Cần LINKO_TOKEN có quyền Admin để smoke test ghi/xóa.')
    api = Client(args.base_url, token)
    _, ready = api.call('GET','/api/ready')
    check(ready.get('status') == 'ready', 'Oracle + GRAPH_TABLE ready')
    suffix = uuid4().hex[:12]
    dept = project = person_a = person_b = None
    try:
        _, result = api.call('POST','/api/departments',{'department_name':f'V6_TEST_{suffix}','location':'TEST'})
        dept = int(result['department_id'])
        check(dept > 0, 'Tạo phòng ban')

        def employee(label):
            _, row = api.call('POST','/api/employees',{
                'full_name':f'V6 {label} {suffix}', 'email':f'v6_{label}_{suffix}@example.test',
                'title':'Test Engineer','department_id':dept})
            return int(row['employee_id'])

        person_a = employee('alpha')
        person_b = employee('beta')
        check(person_a != person_b, 'Tạo hai nhân viên')
        _, edited=api.call('PATCH',f'/api/employees/{person_a}',{'title':'Senior Test Engineer'})
        check(edited['title']=='Senior Test Engineer', 'Cập nhật thông tin nhân viên')

        _, result=api.call('POST','/api/projects',{'project_name':f'V6 project {suffix}',
                       'department_id':dept,'status':'ACTIVE'})
        project=int(result['project_id'])
        _, edited=api.call('PATCH',f'/api/projects/{project}',{'description':'V6 REST CRUD test'})
        check(edited['description']=='V6 REST CRUD test','Cập nhật dự án')

        _, edge=api.call('POST','/api/connections',{'from_emp':person_a,'to_emp':person_b,
                          'connection_type':'FRIEND','strength':3.0,'notes':'V6 manual test'})
        check(edge['success'],'Tạo quan hệ thủ công trước khi gán dự án')
        for employee_id in (person_a,person_b):
            api.call('PUT',f'/api/data/projects/{project}/members/{employee_id}',{'role':'MEMBER'})
        _, members=api.call('GET',f'/api/projects/{project}/members')
        check(len(members)==2,'Gán thành viên dự án và tự động sinh teammate')

        _, updated=api.call('PATCH',f'/api/data/connections/{person_a}/{person_b}',{'strength':4.2})
        check(float(updated['record']['strength'])==4.2,'Sửa quan hệ thủ công')
        protected_status,protected=api.call('DELETE',f'/api/data/connections/{person_b}/{person_a}',allow_error=True)
        check(protected_status==409 and protected['detail']['code']=='AUTO_TEAMMATE_PROTECTED',
              'Không được xóa TEAMMATE do trigger sinh')

        _, impact=api.call('GET',f'/api/data/projects/{project}/delete-impact')
        check(impact['dependencies']['memberships']==2,'Xem trước số quan hệ bị ảnh hưởng khi xóa')
        status,_=api.call('DELETE',f'/api/projects/{project}',allow_error=True)
        check(status==409,'Xóa dự án còn thành viên bị chặn mặc định')
        _, result=api.call('DELETE',f'/api/projects/{project}?cascade=true&confirm=true')
        project=None
        check(result['success'],'Xóa dự án có xác nhận, trigger đồng bộ TEAMMATE')

        _, result=api.call('POST','/api/data/employees/bulk-status',{'employee_ids':[person_a,person_b],
                          'status':'ON_LEAVE'})
        check(result['updated']==2,'Cập nhật trạng thái nhiều nhân viên trong một transaction')
        api.call('PATCH',f'/api/data/employees/{person_a}/status',{'status':'ACTIVE'})
        api.call('PATCH',f'/api/data/employees/{person_b}/status',{'status':'ACTIVE'})
        _, result=api.call('DELETE',f'/api/data/connections/{person_a}/{person_b}')
        check(result['record']['from_emp']==person_a,'Xóa kết nối thủ công (trigger audit)')

        api.call('DELETE',f'/api/employees/{person_a}?hard=true&confirm=true')
        person_a=None
        api.call('DELETE',f'/api/employees/{person_b}?hard=true&confirm=true')
        person_b=None
        _, result=api.call('DELETE',f'/api/departments/{dept}')
        dept=None
        check(result['success'],'Xóa nhân viên và phòng ban thử nghiệm')
        print('\nPASS: REST CRUD đã thực hiện thật trên Oracle, không mock.')
        return 0
    finally:
        # Own-data-only best effort cleanup in case a step failed halfway.
        for path in ([f'/api/projects/{project}?cascade=true&confirm=true'] if project else []) + [
            f'/api/data/connections/{person_a}/{person_b}' if person_a and person_b else None,
            f'/api/data/connections/{person_b}/{person_a}' if person_a and person_b else None,
            f'/api/employees/{person_a}?hard=true&cascade=true&confirm=true' if person_a else None,
            f'/api/employees/{person_b}?hard=true&cascade=true&confirm=true' if person_b else None,
            f'/api/departments/{dept}' if dept else None,
        ]:
            if path:
                try: api.call('DELETE',path,allow_error=True)
                except Exception as exc: print('CLEANUP warning:',path,str(exc), file=sys.stderr)


if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print('FAIL:',exc,file=sys.stderr)
        sys.exit(1)
