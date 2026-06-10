"""Fix Alembic version"""
from sqlalchemy import text, create_engine
from app.core.config import Settings

settings = Settings()
engine = create_engine(settings.database_url)

with engine.begin() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    current = result.fetchone()
    print(f'Current version in DB: {current}')
    
    conn.execute(text('DELETE FROM alembic_version'))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('20260429_consolidated')"))
    
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    print(f'Updated to: {result.fetchone()[0]}')
