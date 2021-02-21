import pygame
import sys
import random
import numpy as np

import settings


class Brain:
    def __init__(self, size):
        self.current_instr = 0
        self.size = size
        self.instructions = np.random.randn(size, 2)

    # Makes a new Brain with the same instructions but with
    # instruction counter reset to zero
    def clean_clone(self, size=settings.BRAIN_SIZE):
        brain = Brain(size)
        brain.instructions = np.copy(self.instructions)[:size]
        return brain


class Entity:
    def __init__(self, x, y, color, width, height):
        self.pos = np.array([x, y])
        self.color = color
        self.rect = pygame.Rect((x, y, width, height))

    def draw(self, surface):
        pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(
            self.rect.x - 2, self.rect.y - 2, self.rect.width + 4, self.rect.height + 4))
        pygame.draw.rect(surface, self.color, self.rect)

    def tick(self):
        pass


# Enemy movement behaviour
class Bounce:
    def move(self, entity):
        entity.rect.move_ip(entity.vel[0], entity.vel[1])
        entity.x += entity.vel[0]
        entity.y += entity.vel[1]

    def wall_collide_handler(self, entity):
        entity.vel[0] *= -1
        entity.vel[1] *= -1


class Enemy(Entity):
    def __init__(self, x, y, color, width, height, move_strategy, velocity):
        super().__init__(x, y, color, width, height)
        self.move_strategy = move_strategy
        self.x = x
        self.original_x = x
        self.y = y
        self.original_y = y
        self.color = color
        self.width = width
        self.height = height
        self.vel = list(velocity)
        self.original_vel = list(velocity)

    def tick(self):
        self.move()

    def move(self):
        self.move_strategy.move(self)

    def wall_collide_handler(self):
        self.move_strategy.wall_collide_handler(self)

    def clone(self):
        return Enemy(self.original_x, self.original_y, self.color,
                     self.width, self.height, Bounce(), self.original_vel)


class Goal(Entity):
    pass


class Wall(Entity):
    pass


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, settings.PLAYER_COLOR,
                         settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT)
        self.vel = np.array([0.0, 0.0])
        self.acc = np.array([0.0, 0.0])
        self.start_x = x
        self.start_y = y
        self.brain = Brain(settings.BRAIN_SIZE)
        self.dead = False
        self.fitness = 0
        self.reached_goal = False
        self.killed = False

    def die(self):
        self.dead = True
        self.killed = True

    def win(self):
        self.reached_goal = True
        self.dead = True

    def clone(self, brain_size=settings.BRAIN_SIZE):
        player = Player(self.start_x, self.start_y)
        player.brain = self.brain.clean_clone(size=brain_size)
        return player

    def move(self):
        if not self.dead and self.brain.current_instr < len(self.brain.instructions):
            self.acc = self.brain.instructions[self.brain.current_instr]
            self.brain.current_instr += 1
            self.vel += self.acc

            # Restrict maximum player velocity to be between -5 and 5
            self.vel = np.clip(self.vel, -5, 5)
            self.pos += self.vel
            self.rect.move_ip(self.vel[0], self.vel[1])

            # The player is exhausted and cannot move anymore. Method of only selecting
            # the most straight-to-the-point players
            if self.brain.current_instr >= len(self.brain.instructions):
                self.dead = True

    def tick(self):
        self.move()


class Population:
    def __init__(self):
        self.players = []
        self.total_fitness = 0
        self.best_player = None
        self.max_steps = settings.BRAIN_SIZE
        self.current_gen = 0

        for x in range(settings.POPULATION_SIZE):
            self.players.append(
                Player(settings.PLAYER_SPAWN_X, settings.PLAYER_SPAWN_Y))

    def all_dead(self):
        for player in self.players:
            if not player.dead:
                return False

        return True

    def calculate_fitness(self, goal):
        for player in self.players:
            if player.reached_goal:
                player.fitness = 1600.0 / \
                    pow((1.0 / 16.0 + player.brain.current_instr), 2)
            else:
                player.fitness = 1.0/1600.0 + 1.0 / \
                    pow((abs(player.rect.x - goal.rect.x) +
                         abs(player.rect.y - goal.rect.y)), 2)
            if player.killed:
                player.fitness *= 0.9
            self.total_fitness += player.fitness

    def select(self):
        selected_players = []
        probabilities = []
        max_fitness = 0
        num_to_select = int(settings.POPULATION_SIZE / 2)

        # Even numbers of players need to be selected to make crossover easier.
        # The selection here is made odd because the best player is added at the end manually.
        if num_to_select % 2 == 0:
            num_to_select += 1

        for player in self.players:
            probabilities.append(player.fitness / self.total_fitness)

            # Find best player to put into the next generation unaltered
            if player.fitness > max_fitness:
                # Do not allow more steps than the best player took
                if player.reached_goal:
                    self.max_steps = player.brain.current_instr

                self.best_player = player.clone(brain_size=self.max_steps)
                max_fitness = player.fitness

        selected = np.random.choice(
            self.players, num_to_select, False, probabilities)

        for player in selected:
            selected_players.append(player.clone(brain_size=self.max_steps))

        # Ensure the best player is in the reproduction pool
        selected_players.append(
            self.best_player.clone(brain_size=self.max_steps))

        return selected_players

    def crossover(self):
        for idx, player in enumerate(range(0, len(self.players), 2)):
            parent_a = self.players[idx]
            parent_b = self.players[idx + 1]

            # Every pair of parents creates two offspring
            self.players.append(self.get_child(parent_a, parent_b))
            self.players.append(self.get_child(parent_b, parent_a))

    def get_child(self, parent_a, parent_b):
        child = parent_a.clone(brain_size=self.max_steps)
        crossover_idx = random.randint(0, self.max_steps)

        child.brain.instructions[:crossover_idx] = np.copy(
            parent_b.brain.instructions[:crossover_idx])

        return child

    def mutate(self):
        for player in self.players:
            # Do not mutate the best player
            if player == self.best_player:
                continue
            for idx in range(len(player.brain.instructions)):
                res = random.uniform(0.0, 100.0)
                if res <= settings.MUTATION_RATE:
                    player.brain.instructions[idx] = np.random.randn(1, 2)[0]

    def next_generation(self, goal):
        self.calculate_fitness(goal)
        self.players = self.select()
        self.crossover()
        self.mutate()
        self.total_fitness = 0

        # Place an unaltered clone of the best player in the next generation
        self.players.append(self.best_player)
        self.best_player.color = settings.BEST_PLAYER_COLOR

        self.current_gen += 1


class Referee:
    # Enforces the rules by making players die on wall collisions and win on goal collision
    def validate_collision(self, entity, collidable_entities):
        if entity.rect.collidelist(collidable_entities) != -1:
            return True

        return False

    def check_out_of_bounds(self, entity):
        if (entity.rect.x + entity.rect.width > settings.RESOLUTION[0]
                or entity.rect.x < 0
                or entity.rect.y + entity.rect.height > settings.RESOLUTION[1]
                or entity.rect.y < 0):
            return True

    def eliminate_wall_huggers(self, players, walls):
        for player in players:
            if self.validate_collision(player, walls) or self.check_out_of_bounds(player):
                player.die()

    def find_enemy_wall_collisions(self, enemies, walls):
        for enemy in enemies:
            if self.validate_collision(enemy, walls) or self.check_out_of_bounds(enemy):
                enemy.wall_collide_handler()

    def find_enemy_player_collisions(self, enemies, players):
        for player in players:
            if self.validate_collision(player, enemies):
                player.die()

    def find_winners(self, players, goal):
        for player in players:
            if self.validate_collision(player, [goal]):
                player.win()


def main():
    pygame.init()

    screen = pygame.display.set_mode(settings.RESOLUTION)
    pygame.display.set_caption("Genetic ML Algo Demo")

    entities = []
    running = True
    bg_color = settings.BG_COLOR
    delay = 20

    population = Population()
    referee = Referee()

    # Rudimentary level creation section
    goal = Goal(10, 200, (0, 255, 0), 10, 10)

    walls = []
    # walls.append(Wall(0, 130, (0, 0, 0), 800, 5))
    # walls.append(Wall(0, 290, (0, 0, 0), 800, 5))
    # walls.append(Wall(200, 0, (0, 0, 0), 5, 300))
    walls.append(Wall(400, 200, (0, 0, 0), 5, 400))
    walls.append(Wall(200, 0, (0, 0, 0), 5, 300))
    # walls.append(Wall(200, 320, (0, 0, 0), 5, 300))

    enemies = []
    original_enemies = []
    # original_enemies.append(
    #     Enemy(360, 140, (255, 255, 0), 20, 20, Bounce(), [5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(360, 165, (255, 255, 0), 20, 20, Bounce(), [-5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(360, 190, (255, 255, 0), 20, 20, Bounce(), [5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(360, 215, (255, 255, 0), 20, 20, Bounce(), [-5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(360, 240, (255, 255, 0), 20, 20, Bounce(), [5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(360, 265, (255, 255, 0), 20, 20, Bounce(), [-5.0, 0.0]))
    #
    # original_enemies.append(
    #     Enemy(100, 140, (255, 255, 0), 20, 20, Bounce(), [-5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(100, 165, (255, 255, 0), 20, 20, Bounce(), [5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(100, 190, (255, 255, 0), 20, 20, Bounce(), [-5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(100, 215, (255, 255, 0), 20, 20, Bounce(), [5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(100, 240, (255, 255, 0), 20, 20, Bounce(), [-5.0, 0.0]))
    # original_enemies.append(
    #     Enemy(100, 265, (255, 255, 0), 20, 20, Bounce(), [5.0, 0.0]))

    for enemy in original_enemies:
        enemies.append(enemy.clone())

    entities += walls
    entities += population.players
    entities += enemies
    entities.append(goal)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Control the speed of the simulation using arrow keys
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    delay += 10
                elif event.key == pygame.K_RIGHT:
                    delay -= 10

        screen.fill(bg_color)

        for entity in entities:
            entity.draw(screen)
            entity.tick()

        referee.eliminate_wall_huggers(population.players, walls)
        referee.find_winners(population.players, goal)
        referee.find_enemy_wall_collisions(enemies, walls)
        referee.find_enemy_player_collisions(enemies, population.players)

        if population.all_dead():

            entities = [x for x in entities if x not in population.players]
            entities = [x for x in entities if x not in enemies]
            population.next_generation(goal)
            entities += population.players

            # Reset enemies
            enemies = []
            for enemy in original_enemies:
                enemies.append(enemy.clone())

            entities += enemies

            print("Current generation: " + str(population.current_gen))
            print("Current best steps: " + str(population.max_steps))
            print("=====================")

        pygame.display.update()
        pygame.time.delay(delay)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
