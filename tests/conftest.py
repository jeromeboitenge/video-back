import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app
from app.models import MediaAsset, Project, User  # noqa: F401


@pytest.fixture(autouse=True)
def isolated_test_database():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)
        test_engine.dispose()
