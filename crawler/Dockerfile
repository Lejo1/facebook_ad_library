FROM python

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY tokens.py tokens.py
COPY queing.py queing.py
COPY crawlall.py main.py
COPY config.py config.py


CMD ["python", "main.py"]
