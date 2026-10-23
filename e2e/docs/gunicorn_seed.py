"""gunicorn config for the docs stack only (docker-compose.docs.yml).

Seeds the worker's `random`, so the home page's "random" quote depends only on
the order of the tour's requests. It has to be post_worker_init: gunicorn
reseeds `random` in the worker after post_fork.

With 103 fixture quotes, the 3rd to 5th home-page visits of the tour (German
hero, English home, phone) show Schiller's "Alles wiederholt sich im Leben",
Einstein's bicycle and Franklin's candle. Re-pick the seed when the fixtures or
that order change.
"""
import random


def post_worker_init(worker):
    random.seed(13623)
