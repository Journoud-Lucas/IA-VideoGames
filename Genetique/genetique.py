import pygame
import random
import math
from dataclasses import dataclass
from typing import List, Tuple
import colorsys

pygame.init()

# Configuration
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

# Genetic Algorithm
POPULATION_SIZE = 100
GENE_LENGTH = 300
MUTATION_RATE = 0.20
ELITISM_COUNT = 5
TOURNAMENT_SIZE = 5

# Creature
CREATURE_SPEED = 4
CREATURE_SIZE = 6

# Colors
COLOR_BG = (15, 15, 25)
COLOR_TARGET = (255, 80, 80)
COLOR_START = (80, 255, 120)
COLOR_TEXT = (220, 220, 220)
COLOR_PANEL = (30, 30, 45)


@dataclass
class Gene:
    angle: float

    @staticmethod
    def random():
        return Gene(random.uniform(0, 2 * math.pi))

    def mutate(self):
        return Gene(self.angle + random.gauss(0, 0.5))


class DNA:
    def __init__(self, genes=None):
        if genes is None:
            self.genes = [Gene.random() for _ in range(GENE_LENGTH)]
        else:
            self.genes = genes

    def crossover(self, partner):
        crossover_point = random.randint(0, len(self.genes) - 1)
        new_genes = self.genes[:crossover_point] + partner.genes[crossover_point:]
        return DNA(new_genes)

    def mutate(self, mutation_rate):
        for i in range(len(self.genes)):
            if random.random() < mutation_rate:
                self.genes[i] = self.genes[i].mutate()


class Creature:
    def __init__(self, start_pos, dna=None):
        self.start_pos = start_pos
        self.pos = list(start_pos)
        self.dna = dna if dna else DNA()
        self.fitness = 0.0
        self.current_gene = 0
        self.reached_target = False
        self.dead = False
        self.distance_record = float('inf')
        self.steps_to_target = GENE_LENGTH

        # Color
        hue = hash(tuple(g.angle for g in self.dna.genes[:10])) % 360 / 360
        rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
        self.color = tuple(int(c * 255) for c in rgb)

    def update(self, target, obstacles):
        if self.dead or self.reached_target or self.current_gene >= len(self.dna.genes):
            return

        # Apply gene
        gene = self.dna.genes[self.current_gene]
        dx = math.cos(gene.angle) * CREATURE_SPEED
        dy = math.sin(gene.angle) * CREATURE_SPEED
        self.pos[0] += dx
        self.pos[1] += dy
        self.current_gene += 1

        # Bounds
        if (self.pos[0] < 0 or self.pos[0] > WINDOW_WIDTH or
            self.pos[1] < 0 or self.pos[1] > WINDOW_HEIGHT):
            self.dead = True

        # Obstacles
        creature_rect = pygame.Rect(self.pos[0] - CREATURE_SIZE//2,
                                     self.pos[1] - CREATURE_SIZE//2,
                                     CREATURE_SIZE, CREATURE_SIZE)
        for obs in obstacles:
            if creature_rect.colliderect(obs):
                self.dead = True
                break

        # Target
        dist = math.hypot(self.pos[0] - target[0], self.pos[1] - target[1])
        if dist < self.distance_record:
            self.distance_record = dist
        if dist < 20:
            self.reached_target = True
            self.steps_to_target = self.current_gene

    def calculate_fitness(self, target):
        if self.reached_target:
            self.fitness = 10000 + (GENE_LENGTH - self.steps_to_target) * 10
        elif self.dead:
            self.fitness = 1.0 / (self.distance_record ** 2 + 1)
        else:
            self.fitness = 100.0 / (self.distance_record ** 2 + 1)

    def draw(self, surf):
        if self.dead:
            color = (100, 100, 100)
        elif self.reached_target:
            color = (255, 215, 0)
        else:
            color = self.color

        # Triangle
        if self.current_gene > 0 and self.current_gene <= len(self.dna.genes):
            angle = self.dna.genes[self.current_gene - 1].angle
        else:
            angle = 0

        size = CREATURE_SIZE
        points = [
            (self.pos[0] + math.cos(angle) * size * 1.5,
             self.pos[1] + math.sin(angle) * size * 1.5),
            (self.pos[0] + math.cos(angle + 2.5) * size,
             self.pos[1] + math.sin(angle + 2.5) * size),
            (self.pos[0] + math.cos(angle - 2.5) * size,
             self.pos[1] + math.sin(angle - 2.5) * size),
        ]
        pygame.draw.polygon(surf, color, points)


class Population:
    def __init__(self, start_pos):
        self.start_pos = start_pos
        self.creatures = [Creature(start_pos) for _ in range(POPULATION_SIZE)]
        self.generation = 1
        self.best_fitness = 0
        self.avg_fitness = 0
        self.mutation_rate = MUTATION_RATE
        self.target_reached_count = 0
        self.best_ever_fitness = 0
        self.fitness_history = []

    def update(self, target, obstacles):
        all_done = True
        for creature in self.creatures:
            creature.update(target, obstacles)
            if not creature.dead and not creature.reached_target and creature.current_gene < GENE_LENGTH:
                all_done = False
        return all_done

    def calculate_all_fitness(self, target):
        for creature in self.creatures:
            creature.calculate_fitness(target)

        # Stats
        fitnesses = [c.fitness for c in self.creatures]
        self.best_fitness = max(fitnesses)
        self.avg_fitness = sum(fitnesses) / len(fitnesses)
        self.target_reached_count = sum(1 for c in self.creatures if c.reached_target)

        if self.best_fitness > self.best_ever_fitness:
            self.best_ever_fitness = self.best_fitness

        self.fitness_history.append(self.best_fitness)

    def selection(self):
        tournament = random.sample(self.creatures, TOURNAMENT_SIZE)
        return max(tournament, key=lambda c: c.fitness)

    def evolve(self):
        new_creatures = []

        # Elitism
        sorted_creatures = sorted(self.creatures, key=lambda c: c.fitness, reverse=True)
        for i in range(ELITISM_COUNT):
            elite = Creature(self.start_pos, DNA([Gene(g.angle) for g in sorted_creatures[i].dna.genes]))
            new_creatures.append(elite)

        # Reproduction
        while len(new_creatures) < POPULATION_SIZE:
            parent1 = self.selection()
            parent2 = self.selection()
            child_dna = parent1.dna.crossover(parent2.dna)
            child_dna.mutate(self.mutation_rate)
            new_creatures.append(Creature(self.start_pos, child_dna))

        self.creatures = new_creatures
        self.generation += 1

    def draw(self, surf):
        for creature in self.creatures:
            creature.draw(surf)


class GeneticAlgorithmSimulation:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Genetic Algorithm - Creature Evolution")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.font_large = pygame.font.Font(None, 42)

        # Start & Target
        self.start_pos = (100, WINDOW_HEIGHT // 2)
        self.target_pos = (WINDOW_WIDTH - 150, WINDOW_HEIGHT // 2)

        # Obstacles
        self.obstacles = [
            pygame.Rect(400, 100, 30, 300),
            pygame.Rect(400, 500, 30, 300),
            pygame.Rect(700, 0, 30, 350),
            pygame.Rect(700, 450, 30, 350),
        ]

        # Population
        self.population = Population(self.start_pos)

        # State
        self.running = True
        self.paused = False
        self.speed_multiplier = 15

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.population = Population(self.start_pos)
                elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                    self.population.mutation_rate = min(0.5, self.population.mutation_rate + 0.01)
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    self.population.mutation_rate = max(0.001, self.population.mutation_rate - 0.01)
                elif event.key == pygame.K_UP:
                    self.speed_multiplier = min(30, self.speed_multiplier + 1)
                elif event.key == pygame.K_DOWN:
                    self.speed_multiplier = max(1, self.speed_multiplier - 1)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.target_pos = event.pos
                    self.population = Population(self.start_pos)

    def draw_ui(self):
        # Info panel
        panel_rect = pygame.Rect(10, 10, 320, 280)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, (60, 60, 80), panel_rect, 2, border_radius=10)

        # Title
        title = self.font_large.render("Genetic Algorithm", True, COLOR_TEXT)
        self.screen.blit(title, (20, 20))

        # Stats
        stats = [
            f"Made by : JOURNOUD Lucas",
            f"Generation : {self.population.generation}",
            f"Population : {POPULATION_SIZE}",
            f"Best fitness : {self.population.best_fitness:.2f}",
            f"Avg fitness : {self.population.avg_fitness:.2f}",
            f"Record : {self.population.best_ever_fitness:.2f}",
            f"Target reached : {self.population.target_reached_count}",
            f"Mutation rate : {self.population.mutation_rate:.1%}",
            f"Speed : x{self.speed_multiplier}",
        ]
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, COLOR_TEXT)
            self.screen.blit(text, (25, 65 + i * 26))

        # Controls panel
        controls_rect = pygame.Rect(10, WINDOW_HEIGHT - 130, 320, 120)
        pygame.draw.rect(self.screen, COLOR_PANEL, controls_rect, border_radius=10)
        pygame.draw.rect(self.screen, (60, 60, 80), controls_rect, 2, border_radius=10)

        controls = [
            "Controls :",
            "Left Click : Move target",
            "Space : Pause | R : Reset",
            "+/- : Mutation | Up/Down : Speed",
        ]
        for i, control in enumerate(controls):
            color = (150, 200, 255) if i == 0 else COLOR_TEXT
            text = self.font.render(control, True, color)
            self.screen.blit(text, (25, WINDOW_HEIGHT - 120 + i * 26))

        # Pause
        if self.paused:
            pause_text = self.font_large.render("PAUSE", True, (255, 200, 100))
            pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, 50))
            pygame.draw.rect(self.screen, COLOR_PANEL, pause_rect.inflate(40, 20), border_radius=10)
            self.screen.blit(pause_text, pause_rect)

    def draw(self):
        self.screen.fill(COLOR_BG)

        # Grid
        for x in range(0, WINDOW_WIDTH, 50):
            pygame.draw.line(self.screen, (25, 25, 40), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, 50):
            pygame.draw.line(self.screen, (25, 25, 40), (0, y), (WINDOW_WIDTH, y))

        # Obstacles
        for obs in self.obstacles:
            pygame.draw.rect(self.screen, (80, 80, 100), obs, border_radius=5)
            pygame.draw.rect(self.screen, (120, 120, 150), obs, 2, border_radius=5)

        # Start
        pygame.draw.circle(self.screen, COLOR_START, self.start_pos, 25)
        pygame.draw.circle(self.screen, (255, 255, 255), self.start_pos, 25, 3)
        start_text = self.font.render("START", True, (0, 0, 0))
        start_rect = start_text.get_rect(center=self.start_pos)
        self.screen.blit(start_text, start_rect)

        # Target
        pygame.draw.circle(self.screen, COLOR_TARGET, self.target_pos, 25)
        pygame.draw.circle(self.screen, (255, 255, 255), self.target_pos, 25, 3)
        for i in range(3):
            pygame.draw.circle(self.screen, (255, 255, 255), self.target_pos, 15 - i * 5, 1)
        target_text = self.font.render("TARGET", True, (255, 255, 255))
        target_rect = target_text.get_rect(center=(self.target_pos[0], self.target_pos[1] + 40))
        self.screen.blit(target_text, target_rect)

        # Population
        self.population.draw(self.screen)

        # UI
        self.draw_ui()

        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()

            if not self.paused:
                for _ in range(self.speed_multiplier):
                    generation_done = self.population.update(self.target_pos, self.obstacles)
                    if generation_done:
                        self.population.calculate_all_fitness(self.target_pos)
                        self.population.evolve()
                        break

            self.draw()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    simulation = GeneticAlgorithmSimulation()
    simulation.run()