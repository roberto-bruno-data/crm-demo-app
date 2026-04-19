from sqlalchemy import create_engine

DB_URL = "postgresql://rob:postgres@localhost:5432/crm_system"

engine = create_engine(DB_URL)