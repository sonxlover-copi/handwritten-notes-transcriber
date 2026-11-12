FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tectonic compiles the generated LaTeX source locally and writes a PDF.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl fonts-dejavu-core \
    && curl -fsSL "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-x86_64-unknown-linux-musl.tar.gz" -o /tmp/tectonic.tar.gz \
    && echo "8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7  /tmp/tectonic.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tectonic.tar.gz -C /usr/local/bin tectonic \
    && rm -f /tmp/tectonic.tar.gz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY tex/latex-smoke.tex /tmp/latex-smoke.tex

# Download the small TeX package bundle during image build, not on the first upload.
RUN tectonic --untrusted --keep-logs /tmp/latex-smoke.tex \
    && rm -f /tmp/latex-smoke.tex /tmp/latex-smoke.pdf /tmp/latex-smoke.log

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
