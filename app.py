import pygame
import sys
import random
import numpy as np
import math

player_color = 255, 0, 0
resolution = [720, 480]


class Population:
    def __init__(self):
        self.players = []
        self.total_fitness = 0
        self.best_player = None
        self.max_steps = 500
        self.current_gen = 0

        for x in range(50):
            self.players.append(Player(600.0, 200.0))

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

        for player in self.players:
            probabilities.append(player.fitness / self.total_fitness)

            # Find best player to put into the next generation unaltered
            if player.fitness > max_fitness:
                # Do not allow more steps than the best player took
                if player.reached_goal:
                    self.max_steps = player.brain.current_instr

                self.best_player = player.clone(brain_size=self.max_steps)
                max_fitness = player.fitness

        selected = np.random.choice(self.players, 15, False, probabilities)

        for player in selected:
            selected_players.append(player.clone(brain_size=self.max_steps))

        # Ensure the best player is in the reproduction pool
        selected_players.append(
            self.best_player.clone(brain_size=self.max_steps))

        return selected_players

    def crossover(self):
        for x in range(30):
            parent_a = self.players[random.randint(0, len(self.players) - 1)]
            parent_b = self.players[random.randint(0, len(self.players) - 1)]
            child = parent_b.clone(brain_size=self.max_steps)

            crossover_idx = random.randint(0, self.max_steps)
            child.brain.instructions[:crossover_idx] = np.copy(
                parent_a.brain.instructions[:crossover_idx])

            self.players.append(child)
            self.players.append(parent_b.clone(brain_size=self.max_steps))
            self.players.append(parent_a.clone(brain_size=self.max_steps))

    def mutate(self):
        mutation_chance = 2.0

        for player in self.players:
            # Do not mutate the best player
            if player == self.best_player:
                continue
            for idx in range(len(player.brain.instructions)):
                res = random.uniform(0.0, 100.0)
                if res <= mutation_chance:
                    player.brain.instructions[idx] = np.random.randn(1, 2)[0]

    def next_generation(self, goal):
        self.calculate_fitness(goal)
        self.players = self.select()
        self.crossover()
        self.mutate()
        self.total_fitness = 0

        # Place an unaltered clone of the best player in the next generation
        self.players.append(self.best_player)
        self.best_player.color = 0, 0, 255

        self.current_gen += 1


class Brain:
    def __init__(self, size):
        self.current_instr = 0
        self.size = size
        self.instructions = np.random.randn(size, 2)

    # Makes a new Brain with the same instructions but with
    # instruction counter reset to zero
    def clean_clone(self, size=500):
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


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, player_color, 10, 10)
        self.vel = np.array([0.0, 0.0])
        self.acc = np.array([0.0, 0.0])
        self.start_x = x
        self.start_y = y
        self.brain = Brain(500)
        self.dead = False
        self.fitness = 0
        self.reached_goal = False
        self.killed = False

    def die(self):
        self.dead = True
        self.killed = True

    def clone(self, brain_size=500):
        player = Player(self.start_x, self.start_y)
        player.brain = self.brain.clean_clone(size=brain_size)
        return player

    def move(self):
        if not self.dead and self.brain.current_instr < len(self.brain.instructions):
            self.acc = self.brain.instructions[self.brain.current_instr]
            self.brain.current_instr += 1
            self.vel += self.acc
            self.vel = np.clip(self.vel, -4, 4)
            self.pos += self.vel
            self.rect.move_ip(self.vel[0], self.vel[1])

            if self.rect.colliderect(goal):
                self.reached_goal = True
                self.dead = True

            if self.brain.current_instr >= len(self.brain.instructions):
                self.dead = True

    def tick(self):
        if (self.rect.x + self.rect.width > resolution[0]
                or self.rect.x < 0
                or self.rect.y + self.rect.height > resolution[1]
                or self.rect.y < 0):
            self.die()

        self.move()


class Wall(Entity):
    pass


class Goal(Entity):
    pass


goal = Goal(10, 10, (0, 255, 0), 10, 10)


def main():
    pygame.init()

    size = (720, 480)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("Simple Game")

    entities = []
    running = True
    bg_color = 191, 255, 208
    global goal
    population = Population()

    walls = []
    walls.append(Wall(200, 0, (0, 0, 0), 5, 400))
    walls.append(Wall(400, 300, (0, 0, 0), 5, 300))
    walls.append(Wall(0, 50, (0, 0, 0), 80, 5))

    entities += walls
    entities += population.players
    entities.append(goal)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(bg_color)

        for entity in entities:
            entity.draw(screen)
            entity.tick()

        for player in population.players:
            if player.rect.collidelist(walls) != -1:
                player.die()

        if population.all_dead():
            entities = [x for x in entities if x not in population.players]
            population.next_generation(goal)
            entities += population.players
            print("Current generation: " + str(population.current_gen))
            print("Current best steps: " + str(population.max_steps))

        pygame.display.update()
        # pygame.time.delay(20)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
