"""Tools for storing REDIS data (especially numpy arrays)."""
import msgpack
import msgpack_numpy as m
import numpy as np
import subprocess
from redis import Redis
from redis.exceptions import ConnectionError

m.patch()  # Important line to monkey-patch for numpy support!


def is_redis_available() -> bool:
    """Check whether a redis server connection is available."""
    r = Redis()

    try:
        r.ping()
        return True
    except redis.exceptions.ConnectionError:
        return False


def redis_server() -> Redis:
    """Start a redis-server if one does not exist."""
    if not is_redis_available():
        subprocess.Popen(["redis-server"])

    return Redis()


def array_to_redis(redis, array, name):
    """Store given Numpy array 'array' in Redis under key 'name'."""
    packed = m.packb(array)
    redis.set(name, packed)


def array_from_redis(redis, name) -> np.ndarray:
    """Retrieve Numpy array from Redis key 'name'."""
    encoded = redis.get(name)
    if encoded:
        return m.unpackb(encoded)
    else:
        raise KeyError(f"Key {name} not found in redis server!")


redis = redis_server()
