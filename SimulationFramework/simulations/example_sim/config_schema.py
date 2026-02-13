"""Schema for the example simulation plugin."""

REQUIRED_PARAMS = {
    "world_size": int,
    "num_agents": int,
}

DEFAULTS = {
    "world_size": 10,
    "num_agents": 5,
}

OPTIONAL_PARAMS = {
    "food_spawn_rate": float,
}
