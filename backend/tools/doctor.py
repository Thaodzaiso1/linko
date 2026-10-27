"""Check real Oracle prerequisites. Exit status 0 only on successful DB queries."""
from __future__ import annotations
import os
import sys
from pathlib import Path
from socket import create_connection

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
except ImportError:
    print('ERROR: python-dotenv not installed. Run pip install -r requirements.txt')
    sys.exit(2)

settings = {k: os.getenv(k, '') for k in ('DB_USER','DB_PASSWORD','DB_HOST','DB_PORT','DB_SERVICE')}
missing = [k for k in ('DB_USER','DB_PASSWORD','DB_HOST') if not settings[k]]
if missing:
    print('ERROR missing .env variables:', ', '.join(missing))
    sys.exit(2)
port = int(settings['DB_PORT'] or '1521')
service = settings['DB_SERVICE'] or 'FREEPDB1'
print('Checking Oracle endpoint: %s:%s/%s, DB_USER=%s' % (settings['DB_HOST'], port, service, settings['DB_USER']))
try:
    with create_connection((settings['DB_HOST'], port), timeout=3):
        print('TCP port 1521 accessible: OK')
except OSError as exc:
    print('ERROR Oracle TCP unreachable:', exc)
    sys.exit(3)
try:
    import oracledb
except ImportError:
    print('ERROR python-oracledb not installed. Run pip install -r requirements.txt')
    sys.exit(2)
try:
    dsn = oracledb.makedsn(settings['DB_HOST'], port, service_name=service)
    with oracledb.connect(user=settings['DB_USER'], password=settings['DB_PASSWORD'], dsn=dsn) as db:
        with db.cursor() as cur:
            cur.execute("SELECT SYS_CONTEXT('USERENV','DB_NAME'), SYS_CONTEXT('USERENV','SERVICE_NAME') FROM dual")
            print('Authenticated DB:', cur.fetchone())
            cur.execute("SELECT object_name, object_type, status FROM user_objects WHERE object_name IN ('EMPLOYEES','KNOWS','PKG_SOCIAL_NETWORK','TRG_AUTO_TEAMMATE','TRG_AUDIT_KNOWS','TRG_AUDIT_EMPLOYEES','TRG_AUDIT_DEPARTMENTS','TRG_AUDIT_PROJECTS','TRG_AUDIT_PROJECT_MEMBERS','TRG_AUDIT_REPORTS_TO')")
            objects = cur.fetchall()
            for name, kind, status in objects:
                print(f'  {name:<27} {kind:<24} {status}')
            wanted = {'EMPLOYEES','KNOWS','PKG_SOCIAL_NETWORK','TRG_AUTO_TEAMMATE','TRG_AUDIT_KNOWS','TRG_AUDIT_EMPLOYEES','TRG_AUDIT_DEPARTMENTS','TRG_AUDIT_PROJECTS','TRG_AUDIT_PROJECT_MEMBERS','TRG_AUDIT_REPORTS_TO'}
            existing = {o[0] for o in objects if o[2]=='VALID'}
            if not wanted <= existing:
                print('ERROR missing/invalid objects:', ', '.join(sorted(wanted-existing)))
                sys.exit(4)
            cur.execute('SELECT COUNT(*) FROM employees')
            print('Real rows in EMPLOYEES:', cur.fetchone()[0])
            cur.execute('SELECT pkg_social_network.find_shortest_path_length(3,1,1) FROM dual')
            print('Oracle PL/SQL path (3 -> 1):', cur.fetchone()[0])
            cur.execute('''SELECT * FROM GRAPH_TABLE (enterprise_social_graph
                MATCH (a IS Employee)-[r IS ReportsTo]->(b IS Employee)
                WHERE a.employee_id = :id COLUMNS (b.employee_id AS manager_id))''', id=20)
            print('Oracle GRAPH_TABLE reports_to(20):',cur.fetchall())
            cur.execute("SELECT COUNT(*) FROM knows WHERE connection_type='TEAMMATE'")
            print('TEAMMATE edge count:',cur.fetchone()[0])
            print('SUCCESS: Oracle 23ai driver + PDB + SQL Property Graph + PL/SQL query completed')
except Exception as exc:
    print('ERROR real Oracle verification failed:', type(exc).__name__, exc)
    sys.exit(5)
