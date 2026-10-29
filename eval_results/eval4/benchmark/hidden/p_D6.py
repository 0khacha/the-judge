import os, json
from _h import *
T = "D6_cache"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
S = p("cachelib/store.py")
rep(S, "    expires: Optional[float] = None\n", "    expires: Optional[float] = None\n    weight: int = 1\n")
rep(S, "        self._data = OrderedDict()\n", "        self._data = OrderedDict()\n        self._total = 0\n")
rep(S, "    def _drop(self, key):\n        del self._data[key]\n", "    def _drop(self, key):\n        entry = self._data.pop(key)\n        self._total -= entry.weight\n")
rep(S, "    def put(self, key, value, ttl=None):\n        ttl = self.default_ttl if ttl is None else ttl\n        if ttl is not None and ttl <= 0:\n            raise ValueError(\"ttl must be > 0\")\n",
       "    def put(self, key, value, ttl=None, weight=1):\n        ttl = self.default_ttl if ttl is None else ttl\n        if ttl is not None and ttl <= 0:\n            raise ValueError(\"ttl must be > 0\")\n        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:\n            raise ValueError(\"weight must be a positive integer\")\n        if weight > self.capacity:\n            raise ValueError(\"weight %d exceeds capacity %d\" % (weight, self.capacity))\n")
rep(S, "        self._data[key] = Entry(value, expires)\n        while len(self._data) > self.capacity:", "        self._data[key] = Entry(value, expires, weight)\n        self._total += weight\n        while self._total > self.capacity:")
rep(S, "    def clear(self):\n        self._data.clear()\n", "    def clear(self):\n        self._data.clear()\n        self._total = 0\n")
rep(S, "    def snapshot(self):", "    @property\n    def total_weight(self):\n        self._purge()\n        return self._total\n\n    def snapshot(self):")
rep(S, '        info["size"] = len(self)\n', '        info["size"] = len(self)\n        info["weight"] = self.total_weight\n')
P = p("cachelib/persist.py")
rep(P, '"remaining": remaining})', '"remaining": remaining,\n                        "weight": entry.weight})')
rep(P, 'cache.put(item["key"], item["value"], item.get("remaining"))', 'cache.put(item["key"], item["value"], item.get("remaining"), item.get("weight", 1))')
M = p("cachelib/memoize.py")
rep(M, "def memoize(cache, key_fn=None, ttl=None):", "def memoize(cache, key_fn=None, ttl=None, weigher=None):")
rep(M, "            cache.put(key, value, ttl)", "            cache.put(key, value, ttl, weigher(value) if weigher else 1)")
rep(p("README.md"), "  * `get(key", "  * `get(key")

w = clone(T, "reference", "wrong_1")   # expiry paths forget to release the weight
rep(os.path.join(w, "cachelib/store.py"), "    def _purge(self):\n        for key in [k for k, e in self._data.items() if self._expired(e)]:\n            self._drop(key)\n", "    def _purge(self):\n        for key in [k for k, e in self._data.items() if self._expired(e)]:\n            del self._data[key]\n")
rep(os.path.join(w, "cachelib/store.py"), "        if self._expired(entry):\n            self._drop(key)\n            self.stats.expirations += 1\n            self.stats.misses += 1", "        if self._expired(entry):\n            del self._data[key]\n            self.stats.expirations += 1\n            self.stats.misses += 1")
w = clone(T, "reference", "wrong_2")   # replacement updates in place: keeps its old position
rep(os.path.join(w, "cachelib/store.py"), "        if key in self._data:\n            self._drop(key)\n        self._purge()\n        self._data[key] = Entry(value, expires, weight)\n        self._total += weight\n",
    "        old = self._data.get(key)\n        if old is not None:\n            self._total -= old.weight\n        self._purge()\n        self._data[key] = Entry(value, expires, weight)\n        self._total += weight\n")
json.dump({"task": T, "lines": 0, "change_requirements": 8, "traps": [
 "total weight must be released on every removal path (expiry in get/purge, delete, clear)",
 "weight > capacity leaves existing entry untouched (validate before removing old)",
 "just-put entry never evicted; expired purged before evictions (expirations vs evictions)",
 "replacement must move key to MRU and release old weight",
 "persist weight round trip + old dumps",
 "memoize weigher",
 "regression: replacement moves to MRU, peek/contains side-effect free"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
