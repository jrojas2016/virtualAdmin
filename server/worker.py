import os
import redis
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']

REDISTOGO_URL = "redis://redistogo:0c21c0c5d46d82902a81da390df0e794@tarpon.redistogo.com:10606/"
# LOCAL_URL = 'REDISTOGO_URL' 
redis_url = os.getenv("REDISTOGO_URL", REDISTOGO_URL)
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
