from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import project_config as config


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True, # Перед кожним використанням з'єднання з пулу, виконує легкий тестовий запит. Якщо тест провалюється, з'єднання утилізується і створюється нове.
        #future=True,
        echo=True  # логування SQL-запитів для відладки
    )


# def create_session_factory(engine: Engine) -> sessionmaker[Session]:
#     return sessionmaker(
#         bind=engine,
#         autoflush=False, # коли True (за замовченням) автоматично надсилає змінені об'єкти в базу даних (викликає flush()) безпосередньо перед виконанням будь-якого запиту
#         autocommit=False, # in sqlalchemy 2.0 always False
#         expire_on_commit=False  #False, після session.commit() об'єкт user.name миттєво поверне значення з кешу пам'яті Python без додаткового запиту до бази даних.
#     )


database_url = config.DATABASE_URL
engine = create_engine(database_url)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()
