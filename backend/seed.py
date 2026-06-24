#!/usr/bin/env python3
"""Seed the database with demo data. Run: python -m backend.seed"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import init_postgresql, SessionLocal
from backend.models.user import User
from backend.models.source import Source
from backend.models.threat_actor import ThreatActor
from passlib.context import CryptContext
from datetime import datetime, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_data():
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "admin").first()
        if not existing_user:
            admin = User(
                username="admin",
                email="admin@night-watch.local",
                hashed_password=pwd_context.hash("admin123"),
                role="admin",
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(admin)
            db.commit()
            print("[+] Admin user created (admin / admin123)")

        if db.query(Source).count() == 0:
            sources = [
                Source(name="Mock Dark Web Leak Site", type="simulated_darkweb",
                       url="http://127.0.0.1:9999", language="en",
                       is_active=True, is_onion=False, uses_tor=False,
                       scrape_interval_minutes=10, reliability_score=1.0),
                Source(name="BleepingComputer", type="rss",
                       url="https://www.bleepingcomputer.com/feed/", language="en",
                       is_active=True, is_onion=False, uses_tor=False,
                       scrape_interval_minutes=60, reliability_score=0.9),
            ]
            db.add_all(sources)
            db.commit()
            print(f"[+] Created {len(sources)} sources")
    finally:
        db.close()


async def main():
    print("[*] Seeding database...")
    await init_postgresql()
    await seed_data()
    print("[+] Database seeding complete")


if __name__ == "__main__":
    asyncio.run(main())
