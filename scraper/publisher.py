from collections import namedtuple

import yaml


Publisher = namedtuple('Publisher', ('url', 'selector'))


def all_publishers():
    with open('../publishers.yml') as f:
        publishers = yaml.load(f)
    return [_parse_publisher(p) for _, p in publishers.items()]


def _parse_publisher(p):
    return Publisher(p['url'], p['selector'])
