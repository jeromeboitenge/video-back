FROM python:3.12-slim
WORKDIR /srv/frameforge
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN pip install --no-cache-dir '.[postgres]'
ENV DATABASE_URL=postgresql+psycopg://frameforge:frameforge@db:5432/frameforge
ENV MEDIA_ROOT=/srv/frameforge/media
VOLUME ["/srv/frameforge/media"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
