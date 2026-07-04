from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User

EVAL_EMAIL_PREFIX = "eval_"
EVAL_EMAIL_SUFFIX = "@test.com"


def delete_eval_user(email: str) -> bool:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            return False
        db.delete(user)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_stale_eval_users() -> int:
    db = SessionLocal()
    try:
        users = db.execute(
            select(User).where(
                User.email.like(f"{EVAL_EMAIL_PREFIX}%{EVAL_EMAIL_SUFFIX}")
            )
        ).scalars().all()
        for user in users:
            db.delete(user)
        db.commit()
        return len(users)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
