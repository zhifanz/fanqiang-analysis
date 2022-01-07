FROM python:3.9
WORKDIR /usr/src/app

RUN apt update && apt --yes install iputils-ping
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "ping_statistics.py"]
CMD ["--days", "30", "--pingcount", "10", "domains", "domestic"]
