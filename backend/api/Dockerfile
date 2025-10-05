FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN pip install --no-cache-dir \
    fastapi==0.118.* \
    uvicorn==0.37.* \
    pydantic>=2.6,<3.0 \
    pydantic-settings>=2.4,<3.0 \
    python-dotenv>=1.0,<2.0 \
    sqlalchemy>=2.0,<3.0 \
    psycopg[binary]>=3.1,<4.0 \
    pandas>=2.2,<3.0 \
    numpy>=1.26,<3.0 \
    python-jose[cryptography]>=3.3,<4.0 \
    passlib[bcrypt]>=1.7,<2.0 \
    python-multipart>=0.0.9,<0.0.10 \
    alembic>=1.13,<2.0

COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]