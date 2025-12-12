import pygame
import random
import heapq
import sys
import time
from collections import deque

# Configuration
CELL_SIZE = 24
COLS = 31
ROWS = 21
FPS = 60
SEARCH_SPEED_MS = 15
DELAY_BETWEEN_ALGORITHM = 3000

# Colors
COLOR_BG = (30, 30, 30)
COLOR_WALL = (10, 10, 10)
COLOR_CELL = (220, 220, 220)
COLOR_START = (30, 160, 30)
COLOR_END = (200, 30, 30)
COLOR_OPEN = (100, 180, 250)
COLOR_CLOSED = (90, 90, 200)
COLOR_PATH = (240, 200, 65)
COLOR_HIGHLIGHT = (160, 160, 160)

TOP = 1
RIGHT = 2
BOTTOM = 4
LEFT = 8
DIR_VECTORS = {TOP: (0, -1), RIGHT: (1, 0), BOTTOM: (0, 1), LEFT: (-1, 0)}
OPPOSITE = {TOP: BOTTOM, RIGHT: LEFT, BOTTOM: TOP, LEFT: RIGHT}

# Maze
class Maze:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.grid = [0] * (cols * rows)

    def in_bounds(self, x, y):
        return 0 <= x < self.cols and 0 <= y < self.rows

    def idx(self, x, y):
        return y * self.cols + x

    def get(self, x, y):
        return self.grid[self.idx(x, y)]

    def set(self, x, y, mask):
        self.grid[self.idx(x, y)] = mask

    def carve(self, x, y, direction):
        nx = x + DIR_VECTORS[direction][0]
        ny = y + DIR_VECTORS[direction][1]
        if not self.in_bounds(nx, ny):
            return False
        self.grid[self.idx(x, y)] |= direction
        self.grid[self.idx(nx, ny)] |= OPPOSITE[direction]
        return True

    def neighbors_coords(self, x, y):
        for d, v in DIR_VECTORS.items():
            nx = x + v[0]
            ny = y + v[1]
            if self.in_bounds(nx, ny):
                yield nx, ny, d

    def generate_recursive_backtracker(self, seed=None):
        rng = random.Random(seed)
        self.grid = [0] * (self.cols * self.rows)
        stack = []
        sx = rng.randrange(0, self.cols)
        sy = rng.randrange(0, self.rows)
        stack.append((sx, sy))
        visited = set()
        visited.add((sx, sy))

        while stack:
            x, y = stack[-1]
            unvisited = []
            for nx, ny, d in self.neighbors_coords(x, y):
                if (nx, ny) not in visited:
                    unvisited.append((nx, ny, d))
            if unvisited:
                nx, ny, d = rng.choice(unvisited)
                self.carve(x, y, d)
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()

    def passages_from(self, x, y):
        mask = self.get(x, y)
        for bit, vec in DIR_VECTORS.items():
            if mask & bit:
                nx = x + vec[0]
                ny = y + vec[1]
                yield nx, ny


class Pathfinder:
    def __init__(self, maze, start, goal):
        self.maze = maze
        self.start = start
        self.goal = goal
        self.came_from = {}
        self.g_score = {}
        self.open_set = []
        self.open_lookup = set()
        self.closed_set = set()
        self.counter = 0
        self.finished = False
        self.found = False

    def reconstruct_path(self):
        path = []
        cur = self.goal
        while cur != self.start:
            path.append(cur)
            cur = self.came_from.get(cur)
            if cur is None:
                return []
        path.append(self.start)
        path.reverse()
        return path

    def neighbors(self, node):
        x, y = node
        for nx, ny in self.maze.passages_from(x, y):
            yield nx, ny


class Dijkstra(Pathfinder):
    def __init__(self, maze, start, goal):
        super().__init__(maze, start, goal)
        self.g_score[start] = 0
        heapq.heappush(self.open_set, (0, self.counter, start))
        self.open_lookup.add(start)

    def step(self):
        if not self.open_set or self.finished:
            self.finished = True
            return
        _, _, current = heapq.heappop(self.open_set)
        self.open_lookup.discard(current)
        if current == self.goal:
            self.finished = True
            self.found = True
            return
        self.closed_set.add(current)
        cxg = self.g_score[current]
        for n in self.neighbors(current):
            tentative_g = cxg + 1
            if n in self.closed_set:
                continue
            if tentative_g < self.g_score.get(n, float('inf')):
                self.came_from[n] = current
                self.g_score[n] = tentative_g
                if n not in self.open_lookup:
                    self.counter += 1
                    heapq.heappush(self.open_set, (tentative_g, self.counter, n))
                    self.open_lookup.add(n)


class AStar(Pathfinder):
    def __init__(self, maze, start, goal):
        super().__init__(maze, start, goal)
        self.g_score[start] = 0
        f = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
        heapq.heappush(self.open_set, (f, self.counter, start))
        self.open_lookup.add(start)

    def step(self):
        if not self.open_set or self.finished:
            self.finished = True
            return
        _, _, current = heapq.heappop(self.open_set)
        self.open_lookup.discard(current)
        if current == self.goal:
            self.finished = True
            self.found = True
            return
        self.closed_set.add(current)
        cxg = self.g_score[current]
        for n in self.neighbors(current):
            tentative_g = cxg + 1
            if n in self.closed_set:
                continue
            if tentative_g < self.g_score.get(n, float('inf')):
                self.came_from[n] = current
                self.g_score[n] = tentative_g
                if n not in self.open_lookup:
                    self.counter += 1
                    priority = tentative_g + abs(n[0] - self.goal[0]) + abs(n[1] - self.goal[1])
                    heapq.heappush(self.open_set, (priority, self.counter, n))
                    self.open_lookup.add(n)

# Draw
def draw_grid(screen, maze, start, goal, pathfinder, path):
    screen.fill(COLOR_BG)
    w = maze.cols * CELL_SIZE
    h = maze.rows * CELL_SIZE

    # Cell Floor
    for y in range(maze.rows):
        for x in range(maze.cols):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, COLOR_CELL, rect)

    # Walls
    wall_w = max(2, CELL_SIZE // 6)
    for y in range(maze.rows):
        for x in range(maze.cols):
            mask = maze.get(x, y)
            cx = x * CELL_SIZE
            cy = y * CELL_SIZE
            if not (mask & TOP):
                pygame.draw.line(screen, COLOR_WALL, (cx, cy), (cx + CELL_SIZE, cy), wall_w)
            if not (mask & LEFT):
                pygame.draw.line(screen, COLOR_WALL, (cx, cy), (cx, cy + CELL_SIZE), wall_w)
            if y == maze.rows - 1 and not (mask & BOTTOM):
                pygame.draw.line(screen, COLOR_WALL, (cx, cy + CELL_SIZE), (cx + CELL_SIZE, cy + CELL_SIZE), wall_w)
            if x == maze.cols - 1 and not (mask & RIGHT):
                pygame.draw.line(screen, COLOR_WALL, (cx + CELL_SIZE, cy), (cx + CELL_SIZE, cy + CELL_SIZE), wall_w)

    if pathfinder is not None:
        for node in getattr(pathfinder, 'open_lookup', set()):
            x, y = node
            rect = pygame.Rect(x * CELL_SIZE + 3, y * CELL_SIZE + 3, CELL_SIZE - 6, CELL_SIZE - 6)
            pygame.draw.rect(screen, COLOR_OPEN, rect)
        for node in getattr(pathfinder, 'closed_set', set()):
            x, y = node
            rect = pygame.Rect(x * CELL_SIZE + 3, y * CELL_SIZE + 3, CELL_SIZE - 6, CELL_SIZE - 6)
            pygame.draw.rect(screen, COLOR_CLOSED, rect)

    # Path
    if path:
        for (x, y) in path:
            rect = pygame.Rect(x * CELL_SIZE + 6, y * CELL_SIZE + 6, CELL_SIZE - 12, CELL_SIZE - 12)
            pygame.draw.rect(screen, COLOR_PATH, rect)

    # Start/End
    if start:
        x, y = start
        rect = pygame.Rect(x * CELL_SIZE + 4, y * CELL_SIZE + 4, CELL_SIZE - 8, CELL_SIZE - 8)
        pygame.draw.rect(screen, COLOR_START, rect)
    if goal:
        x, y = goal
        rect = pygame.Rect(x * CELL_SIZE + 4, y * CELL_SIZE + 4, CELL_SIZE - 8, CELL_SIZE - 8)
        pygame.draw.rect(screen, COLOR_END, rect)

    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((COLS * CELL_SIZE, ROWS * CELL_SIZE))
    pygame.display.set_caption("Maze + Dijkstra & A* Auto")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)

    while True:
        # Generate Maze
        maze = Maze(COLS, ROWS)
        maze.generate_recursive_backtracker()
        start = (0, 0)
        goal = (COLS - 1, ROWS - 1)
        path = []

        # Dijkstra
        pathfinder = Dijkstra(maze, start, goal)
        running_search = True
        last_step_time = 0
        dijkstra_start_time = time.time()
        dijkstra_done = False
        astar_done = False
        astar_path = []

        while running_search:
            now = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    running_search = False
                    break

            # Dijkstra step
            if not dijkstra_done and not pathfinder.finished and now - last_step_time >= SEARCH_SPEED_MS:
                last_step_time = now
                pathfinder.step()
                path = pathfinder.reconstruct_path() if pathfinder.finished and pathfinder.found else []
                draw_grid(screen, maze, start, goal, pathfinder, path)

            # Dijkstra ended
            if not dijkstra_done and pathfinder.finished:
                dijkstra_done = True
                dijkstra_time = time.time() - dijkstra_start_time
                pygame.display.flip()
                pygame.time.delay(DELAY_BETWEEN_ALGORITHM)

                # Start A*
                pathfinder = AStar(maze, start, goal)
                last_step_time = 0
                astar_start_time = time.time()

            # A* step
            if dijkstra_done and not astar_done and not pathfinder.finished and now - last_step_time >= SEARCH_SPEED_MS:
                last_step_time = now
                pathfinder.step()
                astar_path = pathfinder.reconstruct_path() if pathfinder.finished and pathfinder.found else []
                draw_grid(screen, maze, start, goal, pathfinder, astar_path)

            # A* ended
            if dijkstra_done and not astar_done and pathfinder.finished:
                astar_done = True
                astar_time = time.time() - astar_start_time
                draw_grid(screen, maze, start, goal, pathfinder, astar_path)
                pygame.time.delay(DELAY_BETWEEN_ALGORITHM)

                # Print time of 2 algorithm
                screen.fill(COLOR_BG)
                text1 = font.render(f"Dijkstra: {dijkstra_time:.3f}s", True, (255, 255, 255))
                text2 = font.render(f"A*: {astar_time:.3f}s", True, (255, 255, 255))
                text3 = font.render(f"Right click for generate and start a new maze...", True, (255, 255, 255))
                screen.blit(text1, (20, 20))
                screen.blit(text2, (20, 60))
                screen.blit(text3, (20, 100))
                pygame.display.flip()
                # Right Click
                waiting_click = True
                while waiting_click:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit(0)
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            waiting_click = False
                    clock.tick(FPS)
                running_search = False  # Start again

            if not astar_done:
                draw_grid(screen, maze, start, goal, pathfinder, path if not dijkstra_done else astar_path)

            clock.tick(FPS)


if __name__ == '__main__':
    main()