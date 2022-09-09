"""A Pong clone made in Python using Turtle graphics"""

__author__ = "Jake Mareno jmareno@unc.edu"

from turtle import Turtle, Screen, tracer, update, colormode, onkeypress, onkeyrelease, listen
from typing import Tuple, List
from random import randint
from math import sin, cos, radians
from time import sleep

# Window constants
WIDTH: int = 600
HEIGHT: int = 600
RIGHT: int = int(WIDTH/2)
LEFT: int = -RIGHT
TOP: int = int(HEIGHT/2)
BOTTOM: int = -TOP

# Ball constants
BALL_SIZE: int = 12
BALL_SPEED: int = 10
BALL_SPEED_INCREASE: float = 0.25 # How much the ball's speed increases after each bounce

# Paddle constants
PADDLE_WIDTH: int = 80
PADDLE_HEIGHT: int = 10
PADDLE_SPEED: int = 8
PADDLE_DIST_FROM_BORDER: int = 50
PADDLE_BOUNDARY: int = 5
TOP_PADDLE_Y: int = int(HEIGHT/2) - PADDLE_DIST_FROM_BORDER
BOTTOM_PADDLE_Y = -TOP_PADDLE_Y

# Scorekeeper constants
SCORE_FONT: str = "Courier New"
SCORE_SIZE: int = 40

# Bounce behavior constants
BOUNCE_SHARPNESS: int = 90    # Maximum possible offset from straight forwards or backwards
BOUNCE_RAND_FACTOR: int = 25    # Maximum possible random angle added during bounce calculation

# AI constants
AI_VISIBILITY_RANGE: int = int(HEIGHT/1.8) # HOW CLOSE BALL HAS TO BE FOR AI TO TRACK
AI_PADDLE_SPEED: int = 5

# Defines hitbox for a sprite: [min_x, max_x, min_y, max_y]
Hitbox = Tuple[float, float, float, float]

#Initialize screen/background
screen = Screen()

tracer(0, 0)
colormode(255)
screen.bgcolor("blue")
screen.title("PONG")
screen.setup(WIDTH, HEIGHT)


class Sprite:
    """Base parent class for all on screen objects."""
    t: Turtle
    width: int
    height: int
    x: float
    y: float
    hitbox: Hitbox
    changed: bool # Used to determine if an update is necessary


    def __init__(self, width: int, height: int, x: float, y: float, color: str):
        self.t = Turtle()
        self.t.color(color)
        self.t.hideturtle()
        self.t.speed(0)

        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.hitbox = (self.x-(self.width/2), self.x+(self.width/2), self.y-(self.height/2), self.y+(self.height/2))

        self.changed = True
        self.t.penup()


    def update(self) -> None:
        """Updates sprite's hitbox and renders it if changed is True."""
        if self.changed:
            self.update_hitbox()
            self.draw()
            self.changed = False


    def update_hitbox(self) -> None:
        """Defines a new hitbox based on the sprite's x, y, width, and height."""
        self.hitbox = (self.x-(self.width/2), self.x+(self.width/2), self.y-(self.height/2), self.y+(self.height/2))
    

    def draw(self) -> None:
        """Draws the sprite as a rectangle based on its hitbox."""
        self.t.clear()
        self.t.goto(self.hitbox[0], self.hitbox[2])
        self.t.setheading(90)
        self.t.pendown()
        self.t.begin_fill()
        self.t.penup()

        for _ in range(2):
            self.t.forward(self.height)
            self.t.right(90)
            self.t.forward(self.width)
            self.t.right(90)

        self.t.end_fill()


class Scorekeeper(Sprite):
    score: int

    def __init__(self, x: float, y: float, color: str, width: int = 0, height: int = 0):
        super().__init__(width, height, x, y, color)
        self.score = 0
        self.t.goto(x, y)


    def draw(self) -> None:
        self.t.clear()
        self.t.write(self.score, move=False, font=(SCORE_FONT, SCORE_SIZE, "normal"))


    def scored(self):
        self.score += 1
        self.changed = True


class Paddle(Sprite):
    """Base parent class for a paddle that will strike the ball."""
    shift: int
    moving_left: bool
    moving_right: bool


    def __init__(self, width: int, height: int, x: float, y: float, speed: int, color: str):
        super().__init__(width, height, x, y, color)
        self.shift = speed
        self.moving_left = False
        self.moving_right = False

    
    def update(self) -> None:
        """Moves the paddle, updates its hitbox, and renders it."""
        if self.moving_left:
            self.left()
            self.changed = True

        elif self.moving_right:
            self.right()
            self.changed = True
        
        if self.changed:
            self.t.clear()
            self.update_hitbox()
            self.draw()

        self.changed = False


    def left(self) -> None:
        """Atempts to move the paddle to the left."""
        if self.hitbox[0] > -WIDTH/2 + PADDLE_BOUNDARY:
            self.x -= self.shift


    def right(self) -> None:
        """Atempts to move the paddle to the left."""
        if self.hitbox[1] < WIDTH/2 - PADDLE_BOUNDARY:
            self.x += self.shift


    def start_left(self) -> None:
        """Sets moving_left to True."""
        self.moving_left = True


    def start_right(self) -> None:
        """Sets moving_right to True."""
        self.moving_right = True

    
    def stop_left(self) -> None:
        """Sets moving_left to False."""
        self.moving_left = False


    def stop_right(self) -> None:
        """Sets moving_right to False."""
        self.moving_right = False


class PlayerPaddle(Paddle):
    """Subclass of Paddle used for a human controlled paddle."""
    left_button: str
    right_button: str


    def __init__(self, width: int, height: int, x: float, y: float, speed: int, color: str, left_button: str, right_button: str):
        super().__init__(width, height, x, y, speed, color)
        self.left_button = left_button
        self.right_button = right_button

    
    def update(self) -> None:
        """Modified from parent class to add key detection"""
        self.key_listen()

        super().update()

    
    def key_listen(self) -> None:
        """Checks if the left/right trigger keys are pressed or released."""
        onkeypress(self.start_left, self.left_button)
        onkeyrelease(self.stop_left, self.left_button)
        onkeypress(self.start_right, self.right_button)
        onkeyrelease(self.stop_right, self.right_button)
        listen()


class Ball(Sprite):
    """Creates a ball that is bonced around and use for hit and goal detection"""
    dir: float
    base_speed: int
    shift: float
    bounces: int
    paddles: List[Paddle]
    scores: List[Scorekeeper]


    def __init__(self, size: int, speed: int, color: str, paddles: List[Paddle], scores: List[Scorekeeper]):
        super().__init__(size, size, 0, 0, color)
        self.rand_dir()
        self.base_speed = speed
        self.shift = float(self.base_speed)
        self.bounces = 0
        self.paddles = paddles
        self.scores = scores


    def rand_dir(self):
        self.dir = randint(25, 155)
        if randint(0,1) == 1:
            self.dir += 180


    def reset(self):
        self.x = 0
        self.y = 0
        self.bounces = 0
        self.shift = self.base_speed
        self.rand_dir()
        self.update_hitbox()
        self.draw()
        sleep(.5)



    def update(self) -> None:
        """Checks for collisions and moves/renders the ball."""
        self.check_collisions()
        self.shift = self.base_speed + self.bounces * BALL_SPEED_INCREASE
        self.x += self.shift * cos(radians(self.dir))
        self.y += self.shift * sin(radians(self.dir))
        self.changed = True

        super().update()

    
    def check_collisions(self) -> None:
        """Checks if the ball collides with a paddle or screen boundary."""
        if self.hitbox[0] <= LEFT or self.hitbox[1] >= RIGHT:
            self.dir = 180 - (self.dir % 360)

        elif self.hitbox[2] <= BOTTOM+10:
            self.dir = 360 - (self.dir % 360)
            self.scores[0].scored()
            self.reset()
            if self.scores[0].score >= 9:
                pass
        elif self.hitbox[3] >= TOP:
            self.dir = 360 - (self.dir % 360)
            self.scores[1].scored()
            self.reset()
            if self.scores[1].score >= 9:
                pass
        
        for paddle in self.paddles:
            if self.hitbox[2] <= paddle.hitbox[3] and self.hitbox[3] >= paddle.hitbox[3] and self.hitbox[0] <= paddle.hitbox[1] and self.hitbox[1] >= paddle.hitbox[0]:
                self.bounces += 1
                print(f"Direction: {round(self.dir, 1)}  Speed: {self.shift}  Bounces: {self.bounces}")
                if paddle.y < 0:
                    self.dir = 90 + (BOUNCE_SHARPNESS * ((paddle.x-self.x)/2)/((paddle.width/2))) + randint(-BOUNCE_RAND_FACTOR, BOUNCE_RAND_FACTOR)
                else:
                    self.dir = 270 - (BOUNCE_SHARPNESS * ((paddle.x-self.x)/2)/((paddle.width/2))) + randint(-BOUNCE_RAND_FACTOR, BOUNCE_RAND_FACTOR)


class AIPaddle(Paddle):
    """Subclass of Paddle used for an AI constrolled Paddle."""
    ball: Ball
    base_speed: int
    sees_ball: bool = True
    rand_dir_set: bool = False


    def __init__(self, width: int, height: int, x: float, y: float, speed: int, color: str):
        super().__init__(width, height, x, y, speed, color)
        self.base_speed = speed


    def set_ball(self, b: Ball) -> None:
        """Gives the AI acess to the ball for tracking purposes."""
        self.ball = b

    
    def update(self) -> None:
        if abs(self.y - self.ball.y) < AI_VISIBILITY_RANGE:
            self.sees_ball = True
        else:
            self.sees_ball = False
        if self.sees_ball:
            self.shift = self.base_speed
            self.set_dir()
            self.rand_dir_set = False
        else:
            if not self.rand_dir_set:
                self.rand_dir()
                self.rand_dir_set = True

        if self.moving_left:
            self.left()
            self.changed = True
        if self.moving_right:
            self.right()
            self.changed = True
        
        super().update()


    def set_dir(self) -> None:
        """Sets the paddle's direction based on the current position of the ball"""
        if abs(self.x - self.ball.x) < 1.5 * self.base_speed:
            self.shift = 0
        elif self.x > self.ball.x:
            self.start_left()
            self.stop_right()
        else:
            self.start_right()
            self.stop_left()

    
    def rand_dir(self):
        """Sends the paddle in a random direction at a random speed when it cannot see the ball."""
        self.shift = randint(0, self.base_speed)
        if randint(0,1) == 1:
            self.start_left()
            self.stop_right()
        else:
            self.start_right()
            self.stop_left()


def main() -> None:
    """Creates the paddles, scorekeepers, and ball and starts the game."""
    playing: bool = True
    objects: List[Sprite] = []

    paddle1: PlayerPaddle = PlayerPaddle(PADDLE_WIDTH, PADDLE_HEIGHT, 0, TOP_PADDLE_Y, PADDLE_SPEED, "white", "Left", "Right")
    paddle2: AIPaddle = AIPaddle(PADDLE_WIDTH, PADDLE_HEIGHT, 0, BOTTOM_PADDLE_Y, AI_PADDLE_SPEED, "white")
    paddles: List[Paddle] = [paddle1, paddle2]

    score1: Scorekeeper = Scorekeeper(-WIDTH/2 + 50, 100, "white")
    score2: Scorekeeper = Scorekeeper(-WIDTH/2 + 50, -100, "white")
    scores: List[Scorekeeper] = [score1, score2]

    ball = Ball(BALL_SIZE, BALL_SPEED, "white", paddles, scores)
    paddle2.set_ball(ball)
    objects.append(ball)

    for paddle in paddles:
        objects.append(paddle)

    for scorekeeper in scores:
        objects.append(scorekeeper)

    while playing:
        for obj in objects:
            obj.update()
        update()

    


if __name__ == "__main__":
    main()
