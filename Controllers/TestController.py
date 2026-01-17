from fastapi import APIRouter, HTTPException
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Models.TestProjects import TestProjects
from psycopg import AsyncConnection
from psycopg.rows import dict_row

router = APIRouter(prefix="/api/test", tags=["test"])

async def get_db_connection():
    """Get a database connection - only called when endpoint is accessed, not on import"""
    connection_string = os.getenv("DATABASE_URL")
    if not connection_string:
        raise HTTPException(status_code=500, detail="DATABASE_URL environment variable not set")
    try:
        # Use async connection for FastAPI async endpoints
        # psycopg3 async connection - AsyncConnection.connect is the correct method
        conn = await AsyncConnection.connect(connection_string, row_factory=dict_row)
        return conn
    except Exception as e:
        error_msg = f"Database connection error: {str(e)}"
        print(error_msg)
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=503, detail=error_msg)

@router.get("/")
async def get_all():
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # Set search_path to public schema (required because isolated role has restricted search_path)
            await cur.execute('SET search_path = public, "$user"')
            await cur.execute('SELECT "Id", "Name" FROM "TestProjects" ORDER BY "Id"')
            results = await cur.fetchall()
            await conn.commit()
            return results
    finally:
        if conn:
            await conn.close()
    # Do NOT catch generic Exception - let it bubble up to global exception handler

@router.get("/{id}")
async def get(id: int):
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # Set search_path to public schema (required because isolated role has restricted search_path)
            await cur.execute('SET search_path = public, "$user"')
            await cur.execute('SELECT "Id", "Name" FROM "TestProjects" WHERE "Id" = %s', (id,))
            result = await cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Project not found")
            await conn.commit()
            return result
    except HTTPException:
        raise
    finally:
        if conn:
            await conn.close()
    # Do NOT catch generic Exception - let it bubble up to global exception handler

@router.post("/")
async def create(project: TestProjects):
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # Set search_path to public schema (required because isolated role has restricted search_path)
            await cur.execute('SET search_path = public, "$user"')
            await cur.execute('INSERT INTO "TestProjects" ("Name") VALUES (%s) RETURNING "Id"', (project.name,))
            result = await cur.fetchone()
            project_id = result["Id"]
            await conn.commit()
            project.id = project_id
            return project
    finally:
        if conn:
            await conn.close()
    # Do NOT catch generic Exception - let it bubble up to global exception handler

@router.put("/{id}")
async def update(id: int, project: TestProjects):
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # Set search_path to public schema (required because isolated role has restricted search_path)
            await cur.execute('SET search_path = public, "$user"')
            await cur.execute('UPDATE "TestProjects" SET "Name" = %s WHERE "Id" = %s', (project.name, id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Project not found")
            await conn.commit()
            return {"message": "Updated successfully"}
    except HTTPException:
        raise
    finally:
        if conn:
            await conn.close()
    # Do NOT catch generic Exception - let it bubble up to global exception handler

@router.delete("/{id}")
async def delete(id: int):
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # Set search_path to public schema (required because isolated role has restricted search_path)
            await cur.execute('SET search_path = public, "$user"')
            await cur.execute('DELETE FROM "TestProjects" WHERE "Id" = %s', (id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Project not found")
            await conn.commit()
            return {"message": "Deleted successfully"}
    except HTTPException:
        raise
    finally:
        if conn:
            await conn.close()
    # Do NOT catch generic Exception - let it bubble up to global exception handler
