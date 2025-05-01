import redis


class FlaskRedis(object):
    def __init__(self, app=None, config_prefix="REDIS", **kwargs):
        self._redis_client = None
        self.provider_kwargs = kwargs
        self.config_prefix = config_prefix

        if app is not None:
            self.init_app(app)

    def init_app(self, app, **kwargs):
        redis_cluster_url = app.config.get(
            "{0}_CLUSTER_URL".format(self.config_prefix), ""
        )
        if redis_cluster_url:
            self.provider_class = redis.RedisCluster
            url = redis_cluster_url
        else:
            self.provider_class = redis.Redis
            url = app.config.get(
                "{0}_URL".format(self.config_prefix), "redis://localhost:6379/0"
            )

        self.provider_kwargs.update(kwargs)
        self._redis_client = self.provider_class.from_url(
            url=url, **self.provider_kwargs
        )

        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions[self.config_prefix.lower()] = self

    def __getattr__(self, name):
        return getattr(self._redis_client, name)

    def __getitem__(self, name):
        return self._redis_client[name]

    def __setitem__(self, name, value):
        self._redis_client[name] = value

    def __delitem__(self, name):
        del self._redis_client[name]
