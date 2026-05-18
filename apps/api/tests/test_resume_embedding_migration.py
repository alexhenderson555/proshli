import pytest
from sqlalchemy import inspect, text
from app.db import engine

@pytest.mark.asyncio
async def test_resumes_table_has_embedding_column():
    async with engine.connect() as conn:
        cols = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("resumes")
        )
    names = {c["name"] for c in cols}
    assert "embedding" in names

@pytest.mark.asyncio
async def test_resume_embedding_is_nullable_vector_1024():
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT data_type, udt_name, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'resumes' AND column_name = 'embedding'"
                )
            )
        ).first()
    assert row is not None
    assert row.is_nullable == "YES"
    assert row.udt_name == "vector"
