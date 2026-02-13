"""Config schema for wandering_agents_adv simulation plugin."""

REQUIRED_PARAMS = {
    "initial_agents": int,
}

DEFAULTS = {
    "room_width": 50,
    "room_height": 50,
    "initial_agents": 20,
    "max_hunger": 10,
    "move_distance": 5,
    "food_hunger_gain": 3,
    "hunger_decay_per_step": 1,
    "food_spawn_per_step": -1,
    "food_spawn_divisor": 2,
    "mating_hunger_fraction": 0.5,
    "mating_min_hunger": 5,
    "mating_hunger_cost": 2,
    "offspring_deviation_pct": 0.2,
    "initial_agreeable_min": 0.0,
    "initial_agreeable_max": 1.0,
    "initial_aggression_min": 0.0,
    "initial_aggression_max": 1.0,
    "max_population": 500,
}

OPTIONAL_PARAMS = {
    "room_width": int,
    "room_height": int,
    "max_hunger": int,
    "move_distance": int,
    "food_hunger_gain": int,
    "hunger_decay_per_step": int,
    "food_spawn_per_step": int,
    "food_spawn_divisor": int,
    "mating_hunger_fraction": float,
    "mating_min_hunger": int,
    "mating_hunger_cost": int,
    "offspring_deviation_pct": float,
    "initial_agreeable_min": float,
    "initial_agreeable_max": float,
    "initial_aggression_min": float,
    "initial_aggression_max": float,
    "max_population": int,
}
