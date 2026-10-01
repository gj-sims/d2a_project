#!/usr/bin/env python3
import re
from pathlib import Path

import sys
import pathlib

# ensure repo root is on sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network_fix import build_problem, solve_network_prices

LOG = Path('/tmp/ode_dyn.log')

# parse final prices and surplus from ODE log
ode_prices = {}
ode_surplus = None
if LOG.exists():
    text = LOG.read_text()
    # final surplus line
    m = re.search(r"final social surplus\s*=\s*([0-9.,]+)", text, re.IGNORECASE)
    if m:
        ode_surplus = float(m.group(1).replace(',', ''))
    # final prices block (lines like '  dk: 211.5774')
    m2 = re.search(r"\[ode_greedy\] final prices:\n((?:.+\n)+)$", text)
    if m2:
        block = m2.group(1)
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            # accept formats: 'dk: 211.5774' or 'dk: 211.5774'
            parts = line.split(':')
            if len(parts) >= 2:
                name = parts[0].strip()
                try:
                    val = float(parts[1].strip())
                except ValueError:
                    continue
                ode_prices[name] = val

# build LP problem and solve via network_fix
problem, markets = build_problem()
# store autarky
autarky = {name: float(m.price) for name, m in markets.items()}

solve_network_prices(problem, markets)
lp_prices = {}
for m in markets.values():
    ap = getattr(m, 'adj_price', None)
    if ap is None:
        ap = getattr(m, 'price', None)
    lp_prices[m.name] = float(ap) if ap is not None else float('nan')

# print comparison
all_markets = sorted(set(list(autarky.keys()) + list(lp_prices.keys()) + list(ode_prices.keys())))

print('Market | Autarky | LP adj  | ODE adj | ODE~autarky?')
print('-------|---------|---------|---------|-----------')
near_count = 0
for mk in all_markets:
    a = autarky.get(mk, float('nan'))
    lp = lp_prices.get(mk, float('nan'))
    od = ode_prices.get(mk, float('nan'))
    near = False
    if mk in ode_prices and mk in autarky:
        near = abs(od - a) < max(0.01, 0.001 * abs(a))
        if near:
            near_count += 1
    print(f"{mk:6} | {a:7.4f} | {lp:7.4f} | {od:7.4f} | {'YES' if near else 'NO'}")

print('\nParsed ODE surplus:', ode_surplus)
print('LP surplus: (from LP solve not computed here)')
print('Markets near autarky in ODE:', near_count, '/', len(all_markets))

# quick statistic: mean absolute differences
import math

diffs_lp = []
diffs_ode = []
for mk in all_markets:
    if mk in autarky and mk in lp_prices:
        diffs_lp.append(abs(lp_prices[mk] - autarky[mk]))
    if mk in autarky and mk in ode_prices:
        diffs_ode.append(abs(ode_prices[mk] - autarky[mk]))

if diffs_lp:
    print('Mean |LP - autarky| =', sum(diffs_lp)/len(diffs_lp))
if diffs_ode:
    print('Mean |ODE - autarky| =', sum(diffs_ode)/len(diffs_ode))

print('\nIf ODE prices are much closer to autarky than LP prices, the dynamic solver likely failed to enable cross-market trade (small traded volumes).')
