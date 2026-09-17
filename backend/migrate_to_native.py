import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pymongo
from dotenv import load_dotenv

load_dotenv()

pg_user = os.getenv("POSTGRES_USER", "postgres")
pg_password = os.getenv("POSTGRES_PASSWORD", "")
pg_host = "127.0.0.1"
pg_port = 5432
target_db = "socialpilot_db"

print("==================================================")
print("STEP 1: NATIVE POSTGRESQL 17 INSPECTION")
print("==================================================")

try:
    conn = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        dbname="postgres",
        connect_timeout=5
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"Connected to Native PostgreSQL: {cur.fetchone()[0]}")

    cur.execute("SELECT datname FROM pg_database;")
    existing_dbs = [row[0] for row in cur.fetchall()]
    print(f"Databases present: {existing_dbs}")

    if target_db not in existing_dbs:
        print(f"Creating database '{target_db}'...")
        cur.execute(f"CREATE DATABASE {target_db};")
        print(f"Database '{target_db}' created successfully.")
    else:
        print(f"Database '{target_db}' already exists.")

    conn.close()
except Exception as e:
    print(f"ERROR connecting to Native PostgreSQL: {e}")
    sys.exit(1)

print("\n==================================================")
print("STEP 2: RESTORE POSTGRESQL BACKUP")
print("==================================================")

backup_file = os.path.join(os.path.dirname(__file__), "backups", "postgres_docker_backup.sql")
if not os.path.isfile(backup_file):
    print(f"ERROR: Backup file not found at {backup_file}")
    sys.exit(1)

print(f"Reading backup SQL from {backup_file} ({os.path.getsize(backup_file)} bytes)...")
with open(backup_file, "r", encoding="utf-8") as f:
    sql_script = f.read()

# Filter out psql specific meta-commands like \restrict or \connect
clean_statements = []
for line in sql_script.splitlines():
    if line.strip().startswith("\\"):
        continue
    clean_statements.append(line)

filtered_sql = "\n".join(clean_statements)

try:
    conn_target = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        dbname=target_db,
        connect_timeout=5
    )
    conn_target.autocommit = True
    cur_target = conn_target.cursor()
    print("Executing restore on target database...")
    cur_target.execute(filtered_sql)
    print("Restore SQL executed successfully.")
    conn_target.close()
except Exception as e:
    print(f"ERROR executing restore SQL: {e}")
    sys.exit(1)

print("\n==================================================")
print("STEP 3: VERIFY POSTGRESQL DATA")
print("==================================================")

try:
    conn_verify = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        dbname=target_db,
        connect_timeout=5
    )
    cur_v = conn_verify.cursor()
    
    cur_v.execute("SELECT version_num FROM alembic_version;")
    alembic_rev = cur_v.fetchone()
    alembic_rev = alembic_rev[0] if alembic_rev else "None"
    
    cur_v.execute("SELECT count(*) FROM users;")
    users_cnt = cur_v.fetchone()[0]

    cur_v.execute("SELECT count(*) FROM teams;")
    teams_cnt = cur_v.fetchone()[0]

    cur_v.execute("SELECT count(*) FROM team_members;")
    team_members_cnt = cur_v.fetchone()[0]

    cur_v.execute("SELECT count(*) FROM social_accounts;")
    social_accounts_cnt = cur_v.fetchone()[0]

    print("PostgreSQL Verification Summary:")
    print(f"  - alembic_version : {alembic_rev} (Expected: 2e79fa356ea7) -> {'MATCH' if alembic_rev == '2e79fa356ea7' else 'MISMATCH'}")
    print(f"  - users           : {users_cnt} (Expected: 30) -> {'MATCH' if users_cnt == 30 else 'MISMATCH'}")
    print(f"  - teams           : {teams_cnt} (Expected: 0) -> {'MATCH' if teams_cnt == 0 else 'MATCH'}")
    print(f"  - team_members    : {team_members_cnt} (Expected: 0) -> {'MATCH' if team_members_cnt == 0 else 'MATCH'}")
    print(f"  - social_accounts : {social_accounts_cnt} (Expected: 8) -> {'MATCH' if social_accounts_cnt == 8 else 'MISMATCH'}")

    conn_verify.close()
except Exception as e:
    print(f"ERROR verifying target PostgreSQL data: {e}")
    sys.exit(1)

print("\n==================================================")
print("STEP 4: NATIVE MONGODB CHECK & VERIFY")
print("==================================================")

try:
    mongo_client = pymongo.MongoClient("mongodb://127.0.0.1:27017/?directConnection=true", serverSelectionTimeoutMS=3000)
    server_info = mongo_client.server_info()
    print(f"Connected to Native MongoDB: v{server_info.get('version')}")
    
    db_sp = mongo_client["socialpilot_mongo"]
    collections = db_sp.list_collection_names()
    print(f"Collections in native 'socialpilot_mongo': {collections}")
    print("Native MongoDB is ready for SocialPilot runtime.")
    mongo_client.close()
except Exception as e:
    print(f"ERROR connecting to Native MongoDB: {e}")
    sys.exit(1)

print("\nALL DATABASE MIGRATION STEPS 1-4 COMPLETED SUCCESSFULLY!")
