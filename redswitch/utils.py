# redis://host:port or redis://password@host:port
def parse_redis_url(url):
    _, host, port = url.split(':')
    try:
        password, host = host.split('@')
    except ValueError:
        return host[2:], int(port), None

    return host, int(port), password[2:]
