FROM python:3.12-slim-bookworm

# MariaDB lives in the same container as the web app, so the whole challenge
# is one deployable unit (works on Render, Fly, Railway, plain `docker run`).
RUN apt-get update \
 && apt-get install -y --no-install-recommends mariadb-server \
 && rm -rf /var/lib/apt/lists/* /var/lib/mysql \
 && mkdir -p /var/lib/mysql /run/mysqld \
 && chown -R mysql:mysql /var/lib/mysql /run/mysqld \
 && useradd --create-home --shell /usr/sbin/nologin ctf

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py init.sql entrypoint.sh ./
# Strip Windows line endings in case the files were committed from Windows.
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

ENV PORT=5000
EXPOSE 5000
CMD ["/app/entrypoint.sh"]
