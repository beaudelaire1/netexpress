# syntax=docker/dockerfile:1

FROM python:3.11-slim as base

# Do not write .pyc files and ensure stdout/stderr are unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by WeasyPrint.  In addition to
# the libraries explicitly requested (libcairo2, libpango-1.0-0,
# libgdk-pixbuf2.0-0), build-essential and python3-cffi are installed
# to compile any native extensions.  libffi-dev is included because
# certain cffi modules require it at runtime.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        python3-cffi \
        libcairo2 \
        libpango-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Install Python dependencies.  Copy only the requirements file first
# to leverage Docker layer caching.  Render will provide the
# ``requirements/prod.txt`` file so we install from that list.
COPY requirements/prod.txt ./requirements/prod.txt
RUN pip install --upgrade pip \
    && pip install -r requirements/prod.txt

# Copy the project source
COPY . .

# Collect static files for deployment.  During container build there is
# no need for interactive input.
RUN python manage.py collectstatic --noinput

# Expose the port used by the application.  Render assigns the
# environment variable ``PORT`` which defaults to 8000.  This port
# must be exposed for the container runtime.
ENV PORT=8000
EXPOSE $PORT

# Start the application using Gunicorn.  The ``--bind`` option uses
# the PORT environment variable provided at runtime by Render.
CMD ["gunicorn", "netexpress.wsgi:application", "--bind", "0.0.0.0:$PORT"]