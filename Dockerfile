FROM python:3.5.2

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update -qy && \
    apt-get install -qy \
        redis-tools \
        swig && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

COPY redswitch /src

CMD ["/usr/local/bin/python3", "-m", "src.redswitch"]
