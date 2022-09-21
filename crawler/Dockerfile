FROM python

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py config.py
COPY crawlall.py main.py

CMD ["python", "main.py"]
