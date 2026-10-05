import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


MARKET_COORDINATES = {
    "AT": (48.2085, 16.3721),
    "BE": (50.8505, 4.3488),
    "BALTIC": (59.4370, 24.7540),
    "BG": (42.7333, 25.4858),
    "DE-LU": (52.5200, 13.4050),
    "DK": (55.6761, 12.5683),
    "FI": (60.1700, 24.9400),
    "FR": (48.8566, 2.3522),
    "NL": (52.3700, 4.8900),
    "NO": (59.9100, 10.7500),
    "PL": (52.2297, 21.0122),
    "RO": (44.4268, 26.1025),
    "SE": (59.3300, 18.0600),
}

INTERCONNECTORS = [
    ("AT", "DE-LU", 4_000.0),
    ("BE", "DE-LU", 2_000.0),
    ("BE", "FR", 3_500.0),
    ("BE", "NL", 2_400.0),
    ("DE-LU", "FR", 4_000.0),
    ("DE-LU", "NL", 5_000.0),
    ("DE-LU", "PL", 2_500.0),
    ("DE-LU", "DK", 2_500.0),
    ("DE-LU", "SE", 600.0),
    ("DK", "NL", 700.0),
    ("DK", "NO", 1_700.0),
    ("DK", "SE", 2_000.0),
    ("FI", "NO", 100.0),
    ("FI", "SE", 2_700.0),
    ("NO", "NL", 700.0),
    ("NO", "SE", 3_500.0),
    ("BALTIC", "FI", 1_000.0),
    ("BALTIC", "PL", 500.0),
    ("BALTIC", "SE", 700.0),
    ("PL", "SE", 600.0),
    ("BG", "RO", 1_500.0),
]

missing_markets = {
    market
    for from_market, to_market, _ in INTERCONNECTORS
    for market in (from_market, to_market)
    if market not in MARKET_COORDINATES
}
if missing_markets:
    raise ValueError(f"Missing map coordinates for markets: {sorted(missing_markets)}")


# ------------------------------------------------------------
# FIGURE
# ------------------------------------------------------------

fig = plt.figure(figsize=(12, 9))

ax = plt.axes(
    projection=ccrs.PlateCarree()
)

ax.set_extent(
    [-12, 35, 35, 72],
    crs=ccrs.PlateCarree()
)


# ------------------------------------------------------------
# MAP BACKGROUND
# ------------------------------------------------------------

# Ocean
ax.add_feature(
    cfeature.OCEAN,
    facecolor="#F7F9FB",
    zorder=0
)

# Land
ax.add_feature(
    cfeature.LAND,
    facecolor="#E8EBEE",
    edgecolor="none",
    zorder=1
)

# Country borders
ax.add_feature(
    cfeature.BORDERS,
    edgecolor="#FFFFFF",
    linewidth=1.0,
    zorder=2
)

# Coastlines
ax.add_feature(
    cfeature.COASTLINE,
    edgecolor="#AEB5BC",
    linewidth=0.8,
    zorder=3
)

# ------------------------------------------------------------
# INTERCONNECTORS
# ------------------------------------------------------------

MIN_EDGE_WIDTH = 0.8
MAX_EDGE_WIDTH = 3.2
MIN_CAPACITY = min(capacity for _, _, capacity in INTERCONNECTORS)
MAX_CAPACITY = max(capacity for _, _, capacity in INTERCONNECTORS)

for from_market, to_market, capacity in INTERCONNECTORS:
    from_lat, from_lon = MARKET_COORDINATES[from_market]
    to_lat, to_lon = MARKET_COORDINATES[to_market]
    width = MIN_EDGE_WIDTH + (
        (capacity - MIN_CAPACITY) / (MAX_CAPACITY - MIN_CAPACITY)
    ) * (MAX_EDGE_WIDTH - MIN_EDGE_WIDTH)
    ax.plot(
        [from_lon, to_lon],
        [from_lat, to_lat],
        color="#527A9E",
        linewidth=width,
        alpha=0.72,
        transform=ccrs.PlateCarree(),
        zorder=5,
    )

legend_capacities = (500.0, 2_000.0, 4_000.0, 5_000.0)
legend_handles = [
    plt.Line2D(
        [0],
        [0],
        color="#527A9E",
        linewidth=MIN_EDGE_WIDTH + (
            (capacity - MIN_CAPACITY) / (MAX_CAPACITY - MIN_CAPACITY)
        ) * (MAX_EDGE_WIDTH - MIN_EDGE_WIDTH),
        label=f"{capacity:,.0f} MW",
    )
    for capacity in legend_capacities
]


# ------------------------------------------------------------
# MARKET NODES
# ------------------------------------------------------------

# Manual label offsets so labels don't overlap nodes
LABEL_OFFSETS = {
    "AT": (0.45, -0.15),
    "BE": (-2.0, 0.35),
    "BALTIC": (0.5, 0.35),
    "BG": (0.45, -0.15),
    "DE-LU": (0.45, 0.35),
    "DK": (0.45, 0.35),
    "FI": (0.45, 0.35),
    "FR": (-1.9, -0.25),
    "NL": (0.45, 0.35),
    "NO": (0.45, 0.35),
    "PL": (0.45, -0.15),
    "RO": (0.45, -0.15),
    "SE": (0.45, 0.35),
}


for market, (lat, lon) in MARKET_COORDINATES.items():

    # # Outer circle
    # ax.scatter(
    #     lon,
    #     lat,
    #     s=420,
    #     facecolor="white",
    #     edgecolor="#1F4E79",
    #     linewidth=2.5,
    #     transform=ccrs.PlateCarree(),
    #     zorder=10
    # )

    # Inner circle
    ax.scatter(
        lon,
        lat,
        s=180,
        facecolor="#1F4E79",
        edgecolor="none",
        transform=ccrs.PlateCarree(),
        zorder=11
    )

    # Label
    dx, dy = LABEL_OFFSETS[market]

    ax.text(
        lon + dx,
        lat + dy,
        market,
        fontsize=10.5,
        fontweight="bold",
        color="#1F2933",
        transform=ccrs.PlateCarree(),
        zorder=12
    )



# ------------------------------------------------------------
# TITLE
# ------------------------------------------------------------

ax.set_title(
    "European Electricity Markets",
    fontsize=21,
    fontweight="bold",
    color="#17202A",
    pad=18
)


# ------------------------------------------------------------
# CLEANUP
# ------------------------------------------------------------

ax.axis("off")

plt.tight_layout()

plt.show()