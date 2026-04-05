import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import DigestPreference, User
from app.services.digest import digest_channels, rank_for_user
from sqlalchemy import select


def main() -> None:
    db = SessionLocal()
    try:
        users = db.scalars(select(User)).all()
        if not users:
            print("No users found.")
            return

        for user in users:
            pref = db.scalar(select(DigestPreference).where(DigestPreference.user_id == user.id))
            if not pref:
                continue
            ranked = rank_for_user(db, user, limit=5)
            print(f"\nUser: {user.email} | frequency={pref.frequency} | channels={digest_channels(pref)}")
            for item in ranked:
                print(f"- {item.vacancy.title} @ {item.vacancy.company} ({item.reason})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
