from typing import Dict
from app.utilities.typing import Pos

from app.map_maker.utilities import get_random_seed
from app.map_maker import simplex_noise

class NoiseInterface:
    noise_vertices: Dict[Pos, bool] = {}
    noise_threshold: float = 0.5
    noise_frequency: float = 0.125

    def single_process(self, tilemap):
        # Generate a noise map and use that to fill the noise_vertices with True or False
        # depending on threshold
        seed = get_random_seed()
        noise_map: Dict[Pos, float] = simplex_noise.gen_noise_map(
            (tilemap.width * 2 + 1, tilemap.height * 2 + 1), seed,
            starting_frequency=self.noise_frequency)
        self.noise_vertices = {pos: value > self.noise_threshold for pos, value in noise_map.items()}
