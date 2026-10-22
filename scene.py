from manim import *


class AutomatedIntro(Scene):
    def construct(self):
        square = Square(color=BLUE, fill_opacity=0.5)
        circle = Circle(color=RED, fill_opacity=0.5)

        self.play(Create(square))
        self.play(Transform(square, circle))

        title = Text("Automated in the Cloud!", color=YELLOW).scale(0.7)
        title.next_to(square, DOWN, buff=0.5)
        self.play(FadeIn(title))
        self.wait(2)
