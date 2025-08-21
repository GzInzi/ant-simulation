# -*- coding: utf-8 -*-
"""
Emergent Mind: An Ant Colony Simulation
sim.py

This simulation explores how complex, intelligent-like behavior can emerge from a
set of simple, physically-grounded rules. It is not a traditional pathfinding
algorithm but a model of a self-organizing, adaptive system.

Core Principles Implemented:
1.  Stigmergy (Environmental Memory): Ants leave pheromone trails.
2.  Goal-Oriented Bias (Nest Gravity): Ants have an innate sense of home.
3.  Forgetting (Evaporation/Diffusion): Information fades, allowing adaptation.
4.  Systemic Failure (Mental Fatigue/Panic): A novel mechanism to break out of
    non-productive, ritualistic loops.
"""
import pygame
import numpy as np
import random
import math
from scipy.ndimage import gaussian_filter

# --- SIMULATION CONSTANTS (THE "LAWS OF PHYSICS") ---

# SCREEN & DISPLAY
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
WINDOW_TITLE = "Emergent Mind: An Ant Colony Simulation"

# COLORS
BG_COLOR = (20, 20, 20)
ANT_COLOR = (255, 255, 255)
PANIC_ANT_COLOR = (255, 100, 100)
COLONY_COLOR = (0, 150, 255)
FOOD_COLOR = (0, 255, 0)

# ANT AGENT PROPERTIES
ANT_COUNT = 200
ANT_SPEED = 1.5
ANT_ROTATION_SPEED = 0.2
ANT_SENSOR_ANGLE = math.pi / 4  # 45 degrees
ANT_SENSOR_DISTANCE = 10
WANDER_STRENGTH = 0.3

# PHEROMONE GRID PROPERTIES
EVAPORATION_RATE = 0.998
DIFFUSION_RATE = 0.5
DIFFUSION_INTERVAL = 5  # Diffusion is computationally expensive, run every N frames
MAX_PHEROMONE = 1000.0
PHEROMONE_DEPOSIT_AMOUNT = 500

# EMERGENT BEHAVIOR LOGIC
NEST_GRAVITY_STRENGTH = 0.1  # The strength of the "internal compass"
MAX_PATIENCE = 300  # Steps an ant can follow a trail without reaching a goal
PANIC_DURATION = 100  # Steps an ant stays in "panic" mode


class Ant:
    """
    Represents an agent governed by simple rules, not complex logic.
    Its intelligence is a result of its interaction with the environment and its
    own simple internal state (patience, panic).
    """

    def __init__(self, x, y):
        self.pos = np.array([x, y], dtype=float)
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = ANT_SPEED
        self.state = "SEARCHING"  # "SEARCHING" or "CARRYING_FOOD"

        # Internal state for the "Mental Fatigue" mechanism
        self.patience = MAX_PATIENCE
        self.panic_timer = 0

    def update(self, home_pheromones, food_pheromones, foods, colony_pos):
        # --- PANIC STATE: THE LAW OF SYSTEMIC FAILURE ---
        # If in panic, ignore all rules and move randomly to break loops.
        if self.panic_timer > 0:
            self.angle += (random.uniform(-1, 1) * WANDER_STRENGTH * 2)
            self.pos += self.speed * np.array([math.cos(self.angle), math.sin(self.angle)])
            self.panic_timer -= 1
            self.handle_boundaries()
            return

        # --- SENSING ---
        sensor_ahead_pos = self.pos + ANT_SENSOR_DISTANCE * np.array([math.cos(self.angle), math.sin(self.angle)])

        def get_pheromone_value(pos, grid):
            x, y = int(pos[0]), int(pos[1])
            if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                return grid[y, x]
            return 0

        # --- DECISION MAKING & PATIENCE MANAGEMENT ---
        on_trail = False
        if self.state == "SEARCHING":
            smell_ahead = get_pheromone_value(sensor_ahead_pos, food_pheromones)
            if smell_ahead > 10:
                self.patience -= 1
                on_trail = True

            # Standard search logic based on food pheromones
            sensor_left_pos = self.pos + ANT_SENSOR_DISTANCE * np.array(
                [math.cos(self.angle - ANT_SENSOR_ANGLE), math.sin(self.angle - ANT_SENSOR_ANGLE)])
            sensor_right_pos = self.pos + ANT_SENSOR_DISTANCE * np.array(
                [math.cos(self.angle + ANT_SENSOR_ANGLE), math.sin(self.angle + ANT_SENSOR_ANGLE)])
            smell_left = get_pheromone_value(sensor_left_pos, food_pheromones)
            smell_right = get_pheromone_value(sensor_right_pos, food_pheromones)

            if smell_ahead > smell_left and smell_ahead > smell_right:
                self.angle += (random.uniform(-1, 1) * WANDER_STRENGTH)
            elif smell_left > smell_right:
                self.angle -= ANT_ROTATION_SPEED
            elif smell_right > smell_left:
                self.angle += ANT_ROTATION_SPEED
            else:
                self.angle += (random.uniform(-1, 1) * WANDER_STRENGTH)

        elif self.state == "CARRYING_FOOD":
            smell_ahead = get_pheromone_value(sensor_ahead_pos, home_pheromones)
            if smell_ahead > 10:
                self.patience -= 1
                on_trail = True

            # Return-to-home logic combines pheromones and nest gravity
            home_smell_left = get_pheromone_value(self.pos + ANT_SENSOR_DISTANCE * np.array(
                [math.cos(self.angle - ANT_SENSOR_ANGLE), math.sin(self.angle - ANT_SENSOR_ANGLE)]), home_pheromones)
            home_smell_right = get_pheromone_value(self.pos + ANT_SENSOR_DISTANCE * np.array(
                [math.cos(self.angle + ANT_SENSOR_ANGLE), math.sin(self.angle + ANT_SENSOR_ANGLE)]), home_pheromones)

            direction_to_colony = colony_pos - self.pos
            angle_to_colony = math.atan2(direction_to_colony[1], direction_to_colony[0])

            angle_ahead_diff = abs(((self.angle - angle_to_colony + math.pi) % (2 * math.pi)) - math.pi)
            angle_left_diff = abs(
                ((self.angle - ANT_SENSOR_ANGLE - angle_to_colony + math.pi) % (2 * math.pi)) - math.pi)
            angle_right_diff = abs(
                ((self.angle + ANT_SENSOR_ANGLE - angle_to_colony + math.pi) % (2 * math.pi)) - math.pi)

            # Confidence is a blend of pheromone smell and correctness of direction
            confidence_ahead = smell_ahead + (math.pi - angle_ahead_diff) * NEST_GRAVITY_STRENGTH * 100
            confidence_left = home_smell_left + (math.pi - angle_left_diff) * NEST_GRAVITY_STRENGTH * 100
            confidence_right = home_smell_right + (math.pi - angle_right_diff) * NEST_GRAVITY_STRENGTH * 100

            if confidence_ahead > confidence_left and confidence_ahead > confidence_right:
                self.angle += (random.uniform(-1, 1) * WANDER_STRENGTH)
            elif confidence_left > confidence_right:
                self.angle -= ANT_ROTATION_SPEED
            elif confidence_right > confidence_left:
                self.angle += ANT_ROTATION_SPEED
            else:
                angle_diff = (angle_to_colony - self.angle + math.pi) % (2 * math.pi) - math.pi
                self.angle += angle_diff * ANT_ROTATION_SPEED

        if not on_trail:
            self.patience = min(MAX_PATIENCE, self.patience + 2)

        if self.patience <= 0:
            self.panic_timer = PANIC_DURATION
            self.patience = MAX_PATIENCE

        # --- MOVEMENT & INTERACTION ---
        self.pos += self.speed * np.array([math.cos(self.angle), math.sin(self.angle)])
        self.handle_boundaries()
        self.interact_with_objects(home_pheromones, food_pheromones, foods, colony_pos)

    def interact_with_objects(self, home_pheromones, food_pheromones, foods, colony_pos):
        if self.state == "SEARCHING":
            food_found = False
            for food in foods:
                if np.linalg.norm(self.pos - food.pos) < 10 and food.amount > 0:
                    self.state = "CARRYING_FOOD"
                    food.amount -= 1
                    self.angle += math.pi
                    self.patience = MAX_PATIENCE
                    food_found = True
                    break

            # If no food found, leave "to-home" trail as breadcrumbs
            if not food_found:
                x, y = int(self.pos[0]), int(self.pos[1])
                if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                    home_pheromones[y, x] = min(MAX_PHEROMONE, home_pheromones[y, x] + PHEROMONE_DEPOSIT_AMOUNT * 0.5)

        elif self.state == "CARRYING_FOOD":
            if np.linalg.norm(self.pos - colony_pos) < 20:
                self.state = "SEARCHING"
                self.angle += math.pi
                self.patience = MAX_PATIENCE
            else:
                # Leave "to-food" trail while returning home
                x, y = int(self.pos[0]), int(self.pos[1])
                if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                    food_pheromones[y, x] = min(MAX_PHEROMONE, food_pheromones[y, x] + PHEROMONE_DEPOSIT_AMOUNT)

    def handle_boundaries(self):
        # Bounce off screen edges
        if not (20 < self.pos[0] < SCREEN_WIDTH - 20 and 20 < self.pos[1] < SCREEN_HEIGHT - 20):
            self.pos = np.clip(self.pos, 20, [SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20])
            self.angle += math.pi + random.uniform(-0.5, 0.5)

    def draw(self, screen):
        color = PANIC_ANT_COLOR if self.panic_timer > 0 else ANT_COLOR
        pygame.draw.circle(screen, color, self.pos, 2)
        # Draw a small line to indicate direction
        nose_pos = self.pos + 4 * np.array([math.cos(self.angle), math.sin(self.angle)])
        pygame.draw.line(screen, color, self.pos, nose_pos, 1)


class Food:
    """A simple food source object."""

    def __init__(self, x, y, amount):
        self.pos = np.array([x, y], dtype=float)
        self.amount = amount

    def draw(self, screen):
        if self.amount > 0:
            size = min(10 + self.amount / 20, 30)
            pygame.draw.circle(screen, FOOD_COLOR, self.pos, size)


class Simulation:
    """Manages the main simulation loop, state, and rendering."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()

        # The environment: two grids for two types of pheromones
        self.home_pheromones = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH), dtype=float)
        self.food_pheromones = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH), dtype=float)

        # Simulation objects
        self.colony_pos = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2], dtype=float)
        self.ants = [Ant(self.colony_pos[0], self.colony_pos[1]) for _ in range(ANT_COUNT)]
        self.foods = [
            Food(100, 100, 1000),
            Food(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 100, 1000),
            Food(SCREEN_WIDTH - 200, 150, 1000),
            Food(120, SCREEN_HEIGHT - 80, 1000)
        ]
        self.frame_count = 0

    def start(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.foods.append(Food(event.pos[0], event.pos[1], 1000))

            self.update()
            self.draw()
            self.clock.tick(FPS)
            pygame.display.set_caption(f"{WINDOW_TITLE} | FPS: {self.clock.get_fps():.2f}")

        pygame.quit()

    def update(self):
        for ant in self.ants:
            ant.update(self.home_pheromones, self.food_pheromones, self.foods, self.colony_pos)

        # Update the environment based on the Law of Forgetting
        self.home_pheromones *= EVAPORATION_RATE
        self.food_pheromones *= EVAPORATION_RATE

        if self.frame_count % DIFFUSION_INTERVAL == 0:
            self.home_pheromones = gaussian_filter(self.home_pheromones, sigma=DIFFUSION_RATE)
            self.food_pheromones = gaussian_filter(self.food_pheromones, sigma=DIFFUSION_RATE)

        self.frame_count += 1

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_pheromones()

        pygame.draw.circle(self.screen, COLONY_COLOR, self.colony_pos, 15)
        for food in self.foods:
            food.draw(self.screen)
        for ant in self.ants:
            ant.draw(self.screen)

        pygame.display.flip()

    def draw_pheromones(self):
        # Create RGB arrays from pheromone grids and draw them efficiently
        # Home pheromones are BLUE
        if np.any(self.home_pheromones > 0):
            home_pixels = np.zeros((SCREEN_WIDTH, SCREEN_HEIGHT, 3), dtype=np.uint8)
            home_pheromones_t = self.home_pheromones.T
            home_pixels[:, :, 2] = np.clip(home_pheromones_t, 0, 255)
            home_surface = pygame.surfarray.make_surface(home_pixels)
            home_surface.set_colorkey((0, 0, 0))
            self.screen.blit(home_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # Food pheromones are GREEN
        if np.any(self.food_pheromones > 0):
            food_pixels = np.zeros((SCREEN_WIDTH, SCREEN_HEIGHT, 3), dtype=np.uint8)
            food_pheromones_t = self.food_pheromones.T
            food_pixels[:, :, 1] = np.clip(food_pheromones_t, 0, 255)
            food_surface = pygame.surfarray.make_surface(food_pixels)
            food_surface.set_colorkey((0, 0, 0))
            self.screen.blit(food_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


if __name__ == "__main__":
    simulation = Simulation()
    simulation.start()