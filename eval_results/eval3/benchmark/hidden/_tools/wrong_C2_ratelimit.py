PATCHES = {
    1: {"ratelimit/bucket.py": [
        ("        if now > self._last:\n", "        if now != self._last:\n            if now < self._last:\n                self._last = now\n                return\n"),
        ("        if cost > self.capacity:\n            return False\n", "        if cost > self.capacity:\n            raise ValueError('cost exceeds capacity')\n"),
    ]},
    2: {"ratelimit/limiter.py": [
        ("        if key in self._buckets:\n            self._buckets.move_to_end(key)\n            return self._buckets[key]\n",
         "        if key in self._buckets:\n            return self._buckets[key]\n"),
        ("        check_cost(cost)\n        return self._get(key).allow(cost)", "        b = self._get(key)\n        check_cost(cost)\n        return b.allow(cost)"),
    ]},
}
