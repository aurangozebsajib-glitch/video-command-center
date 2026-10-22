from manim import *


class PythonTutorial(Scene):
    def construct(self):
        title = Text("Python 🐍", font_size=36, color=YELLOW)
        title.to_edge(UP, buff=0.25)

        head = Circle(radius=0.22, color=WHITE).move_to([-2.9, 0.9, 0])
        torso = Line([-2.9, 0.68, 0], [-2.9, -0.05, 0], color=WHITE)
        arms = VGroup(
            Line([-2.9, 0.42, 0], [-2.35, 0.05, 0], color=WHITE),
            Line([-2.35, 0.05, 0], [-1.9, 0.05, 0], color=WHITE),
        )
        legs = VGroup(
            Line([-2.9, -0.05, 0], [-2.45, -0.42, 0], color=WHITE),
            Line([-2.45, -0.42, 0], [-1.95, -0.42, 0], color=WHITE),
            Line([-2.9, -0.05, 0], [-3.25, -0.42, 0], color=WHITE),
            Line([-3.25, -0.42, 0], [-3.55, -0.42, 0], color=WHITE),
        )
        laptop_screen = Rectangle(
            width=0.85,
            height=0.58,
            color=GRAY,
            fill_color=GRAY,
            fill_opacity=1,
        ).move_to([-1.55, 0.0, 0])
        laptop_base = Line([-2.05, -0.33, 0], [-1.05, -0.33, 0], color=GRAY)
        figure = VGroup(head, torso, arms, legs, laptop_screen, laptop_base)

        terminal = Rectangle(
            width=5.8,
            height=3.4,
            color=GRAY,
            fill_color=BLACK,
            fill_opacity=1,
            stroke_width=1.5,
        ).move_to([2.8, 0.15, 0])

        self.play(Write(title), run_time=0.55)
        self.play(Create(figure), run_time=0.85)
        self.play(Create(terminal), run_time=0.35)
        self.wait(1.25)

        def show_example(code_lines, result, keep_on_screen=False):
            active_code = VGroup()
            for index, code in enumerate(code_lines):
                line = Text(
                    code,
                    font="Monospace",
                    font_size=24,
                    color=GREEN,
                )
                if index == 0:
                    line.move_to(
                        terminal.get_left() + RIGHT * 0.35 + UP * 0.65,
                        aligned_edge=LEFT,
                    )
                else:
                    line.next_to(
                        active_code[-1],
                        DOWN,
                        aligned_edge=LEFT,
                        buff=0.18,
                    )
                active_code.add(line)
                self.play(AddTextLetterByLetter(line), run_time=0.55)

            output = Text(result, font_size=36, color=YELLOW)
            output.next_to(figure, LEFT, buff=0.35)
            self.play(FadeIn(output), run_time=0.4)

            elapsed = len(code_lines) * 0.55 + 0.4
            if keep_on_screen:
                self.wait(4 - elapsed)
                return

            self.wait(0.5)
            elapsed += 0.5
            self.play(FadeOut(active_code, output), run_time=0.3)
            elapsed += 0.3
            self.wait(4 - elapsed)

        show_example(['print("hi")'], "hi")
        show_example(["a = 1", "print(a)"], "1")
        show_example(["a = 2", "print(a)"], "2")
        show_example(["a = 3", "print(a)"], "3")
        show_example(["a = 3/2", "print(a)"], "1.5")
        show_example(['a = "string"', 'print(a + "ing")'], "stringing", keep_on_screen=True)

        outro = Text("print() -> OUTPUT", font_size=36, color=YELLOW)
        outro.to_edge(DOWN, buff=0.25)
        self.play(Write(outro), run_time=0.5)
        self.wait(2)
        self.wait(0.5)
