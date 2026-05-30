FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV UPLOAD_FOLDER=/data/uploads
ENV DATABASE_URL=sqlite:////data/winpatch.db

EXPOSE 5000

CMD ["python", "run.py"]
