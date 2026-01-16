from app.db.session import SessionLocal


def save_message(*_args, **_kwargs) -> None:
    # TODO: persist messages into Postgres
    db = SessionLocal()
    try:
        pass
    finally:
        db.close()
