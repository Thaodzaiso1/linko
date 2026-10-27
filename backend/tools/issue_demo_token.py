"""Demo ONLY. Tokens never issued from a public API endpoint.

AUTH_MODE=local JWT_SECRET=<32+ random chars> python tools/issue_demo_token.py --sub alice --role hr
DO NOT use local token minting for real users; configure OIDC instead.
"""
import argparse
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
import jwt

parser = argparse.ArgumentParser()
parser.add_argument('--sub', required=True)
parser.add_argument('--role', choices=['employee','hr','admin'], required=True)
parser.add_argument('--minutes', type=int, default=60)
args = parser.parse_args()
if os.getenv('AUTH_MODE') != 'local' or len(os.getenv('JWT_SECRET', '')) < 32:
    raise SystemExit('Chỉ dùng với AUTH_MODE=local và JWT_SECRET tối thiểu 32 ký tự.')
if not 1 <= args.minutes <= 120:
    raise SystemExit('Token demo tối đa 120 phút.')
now = datetime.now(timezone.utc)
print(jwt.encode({'sub':args.sub,'roles':[args.role], 'iss':'linko-local',
                  'aud':'linko-api', 'iat':now, 'exp':now+timedelta(minutes=args.minutes),
                  'jti': secrets.token_hex(8)}, os.environ['JWT_SECRET'], algorithm='HS256'))
