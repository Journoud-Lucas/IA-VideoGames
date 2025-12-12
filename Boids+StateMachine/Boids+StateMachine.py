import pygame
import random
import math

pygame.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT),
    pygame.NOFRAME
)

pygame.event.set_blocked(None)
pygame.event.set_allowed([pygame.QUIT, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP])

clock = pygame.time.Clock()

BOIDS_PER_COLOR = 50
MAX_BOIDS = 4*BOIDS_PER_COLOR+10
MAX_SPEED = 5
MAX_FORCE = 0.05

BAR_GAP = HEIGHT // 25
BAR_WIDTH = WIDTH // 35
BAR_OFFSET = 0

REPULSION_RADIUS = HEIGHT // 10
REPULSION_FORCE = 0.1
HALO_RADIUS = 2

mouse_kill_active = False
mouse_left_down = False
mouse_spawn_color = None

COLORS = {
    "white": ((255, 255, 255), pygame.Rect(BAR_OFFSET, 0, BAR_WIDTH, HEIGHT // 2 - BAR_GAP // 2)),
    "red": ((255, 60, 60), pygame.Rect(BAR_OFFSET, HEIGHT // 2 + BAR_GAP // 2, BAR_WIDTH, HEIGHT // 2 - BAR_GAP // 2)),
    "green": ((60, 255, 60), pygame.Rect(WIDTH - BAR_OFFSET - BAR_WIDTH, 0, BAR_WIDTH, HEIGHT // 2 - BAR_GAP // 2)),
    "yellow": ((230, 200, 40), pygame.Rect(WIDTH - BAR_OFFSET - BAR_WIDTH, HEIGHT // 2 + BAR_GAP // 2, BAR_WIDTH, HEIGHT // 2 - BAR_GAP // 2)),
}
COLOR_NAMES = list(COLORS.keys())


def limit(vec, max_val):
    mag = math.sqrt(vec[0] ** 2 + vec[1] ** 2)
    if mag > max_val:
        return pygame.Vector2(vec[0] / mag * max_val, vec[1] / mag * max_val)
    return pygame.Vector2(vec)


class Particle:
    def __init__(self, pos, color):
        self.pos = pygame.Vector2(pos)
        self.color = color
        self.radius = random.randint(2, 4)
        self.life = 255
    def update(self):
        self.life -= 5
        self.radius *= 0.97
    def draw(self, surf):
        if self.life > 0:
            col = (*self.color, max(self.life, 0))
            pygame.draw.circle(surf, col, (int(self.pos.x), int(self.pos.y)), int(self.radius))


particles = []


class BoidState:
    ATTRACT_COLOR = 0
    REPULSE_MOUSE = 1


class Boid:
    def __init__(self, color_name, pos=None):
        self.set_color(color_name)
        if pos is None:
            self.pos = pygame.Vector2(random.randint(100, WIDTH - 100),
                                      random.randint(100, HEIGHT - 100))
        else:
            self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.acc = pygame.Vector2(0, 0)
        self.state = BoidState.ATTRACT_COLOR

    def set_color(self, name):
        self.color_name = name
        self.color, self.attractor = COLORS[name]

    def change_color(self):
        new_color = random.choice([c for c in COLOR_NAMES if c != self.color_name])
        self.set_color(new_color)

    def apply_force(self, f):
        self.acc += f

    def attraction_color(self, boids):
        perception = HEIGHT // 4
        center = pygame.Vector2(0, 0)
        count = 0
        for b in boids:
            if b is self or b.color_name != self.color_name:
                continue
            if self.pos.distance_to(b.pos) < perception:
                center += b.pos
                count += 1
        if count == 0:
            return pygame.Vector2(0, 0)
        center /= count
        desired = center - self.pos
        if desired.length() > 0:
            desired.scale_to_length(MAX_SPEED)
        return limit(desired - self.vel, MAX_FORCE)

    def attraction_bar(self):
        rect = self.attractor
        target = pygame.Vector2(rect.centerx, rect.centery)
        desired = target - self.pos
        if desired.length() > 0:
            desired.scale_to_length(MAX_SPEED)
        return limit(desired - self.vel, MAX_FORCE * 1.5)

    def repel_from_mouse(self):
        mouse = pygame.Vector2(pygame.mouse.get_pos())
        d = self.pos.distance_to(mouse)
        if d < REPULSION_RADIUS and d > 0:
            force = (self.pos - mouse).normalize() * (REPULSION_RADIUS - d) * REPULSION_FORCE
            self.apply_force(force)

    def check_bar_collision(self):
        future = self.pos + self.vel
        for cname, (col, rect) in COLORS.items():
            if rect.collidepoint(future.x, future.y):
                if future.x < rect.left:
                    self.pos.x = rect.left - 2
                elif future.x > rect.right:
                    self.pos.x = rect.right + 2
                self.vel.x *= -1
                self.change_color()
                return

    def update_state(self, boids):
        self.check_bar_collision()
        mouse_dist = self.pos.distance_to(pygame.Vector2(pygame.mouse.get_pos()))
        if mouse_dist < REPULSION_RADIUS:
            self.state = BoidState.REPULSE_MOUSE
        else:
            self.state = BoidState.ATTRACT_COLOR

    def update(self):
        if self.state == BoidState.ATTRACT_COLOR:
            self.apply_force(self.attraction_color(boids))
            self.apply_force(self.attraction_bar())
        elif self.state == BoidState.REPULSE_MOUSE:
            self.repel_from_mouse()
            self.apply_force(self.attraction_color(boids))

        self.vel += self.acc
        if self.vel.length() > MAX_SPEED:
            self.vel.scale_to_length(MAX_SPEED)
        self.pos += self.vel
        self.acc *= 0

        if self.pos.y < 0:
            self.pos.y = 0
            self.vel.y *= -1
        elif self.pos.y > HEIGHT:
            self.pos.y = HEIGHT
            self.vel.y *= -1

        for _ in range(2):
            particles.append(Particle(self.pos, self.color))

    def draw(self, surf):
        for size, alpha in [(HALO_RADIUS, 20), (HALO_RADIUS + 1, 8)]:
            glow = (*self.color, alpha)
            pygame.draw.circle(surf, glow, (int(self.pos.x), int(self.pos.y)), size)
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), 1)

    def run(self, boids):
        self.update_state(boids)
        self.update()
        self.draw(screen)


boids = [Boid(color) for color in COLOR_NAMES for _ in range(BOIDS_PER_COLOR)]

running = True
while running:
    pygame.event.pump()
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                mouse_left_down = True
                mx, my = pygame.mouse.get_pos()
                mouse_spawn_color = None
                for cname, (col, rect) in COLORS.items():
                    if rect.collidepoint(mx, my):
                        mouse_spawn_color = cname
                        break
                if mouse_spawn_color is None:
                    mouse_kill_active = True
                else:
                    mouse_kill_active = False

            if e.button == 3:
                mx, my = pygame.mouse.get_pos()
                for cname, (col, rect) in COLORS.items():
                    if rect.collidepoint(mx, my):
                        if len(boids) < MAX_BOIDS:
                            boids.append(Boid(cname, pos=(WIDTH // 2, HEIGHT // 2)))

        if e.type == pygame.MOUSEBUTTONUP:
            if e.button == 1:
                mouse_left_down = False
                mouse_kill_active = False
                mouse_spawn_color = None

    if mouse_left_down and mouse_spawn_color is not None:
        if len(boids) < MAX_BOIDS:
            boids.append(Boid(mouse_spawn_color, pos=(WIDTH // 2, HEIGHT // 2)))

    screen.fill((40, 60, 90))

    for name, (col, rect) in COLORS.items():
        pygame.draw.rect(screen, col, rect)

    mouse_pos = pygame.mouse.get_pos()
    s = pygame.Surface((REPULSION_RADIUS * 2, REPULSION_RADIUS * 2), pygame.SRCALPHA)

    for i in range(REPULSION_RADIUS, 0, -1):
        alpha = int(50 * (i / REPULSION_RADIUS))
        color = (150, 100, 255, alpha) if not mouse_kill_active else (255, 60, 60, alpha)
        pygame.draw.circle(s, color, (REPULSION_RADIUS, REPULSION_RADIUS), i)

    screen.blit(s, (mouse_pos[0] - REPULSION_RADIUS, mouse_pos[1] - REPULSION_RADIUS))

    if mouse_kill_active:
        for b in boids[:]:
            if b.pos.distance_to(pygame.Vector2(mouse_pos)) < REPULSION_RADIUS:
                boids.remove(b)

    for p in particles[:]:
        p.update()
        p.draw(screen)
        if p.life <= 0:
            particles.remove(p)

    for b in boids:
        b.run(boids)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()