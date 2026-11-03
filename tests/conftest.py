import pytest

from app.database.session import Base, engine
from app.models import Project, User  # noqa: F401


@pytest.fixture(autouse=True)
def create_test_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
