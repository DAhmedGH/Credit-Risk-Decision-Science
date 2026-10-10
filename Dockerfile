ARG PYTHON_BASE=public.ecr.aws/docker/library/python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7
FROM ${PYTHON_BASE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements.lock /app/requirements.lock
COPY requirements-phase*.in /app/
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY tests /app/tests
COPY scripts /app/scripts
COPY sql /app/sql
COPY configs /app/configs
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
