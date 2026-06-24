#!/usr/bin/env python3
import asyncio

from sqlalchemy import create_engine, text


async def init_database():
    print("Initializing test database...")

    # SQLite connection
    sync_engine = create_engine('sqlite:///./night-watch.db', echo=False)

    with sync_engine.connect() as conn:
        conn.execute(text('CREATE TABLE IF NOT EXISTS users ('
                        'id INTEGER PRIMARY KEY,'
                        'username VARCHAR(100) NOT NULL,'
                        'email VARCHAR(255) NOT NULL,'
                        'hashed_password VARCHAR(255) NOT NULL,'
                        'role VARCHAR(50) NOT NULL,'
                        'is_active BOOLEAN NOT NULL'
                        ')'))
        print("Created users table")

    with sync_engine.connect() as conn:
        conn.execute(text('INSERT INTO users (id, username, email, hashed_password, role, is_active) '
                     'VALUES (1, \"admin\", \"admin@night-watch.io\", '
                     '\"$2b$12\\$KzDznk0agj2TKGl6/0ydq.Z3a4X8HLS4nY/.tckOvnXJ8ems9GLaS\", '
                     '\"admin\", 1) ON CONFLICT (id) DO NOTHING'))
        print("Inserted admin user")

    with sync_engine.connect() as conn:
        result = conn.execute(text('SELECT * FROM users'))
        for row in result:
            print(f"User: id={row[0]}, username={row[1]}")

    print("Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_database())
