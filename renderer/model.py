import os
import message
import pygame as pg
from instruction import Line, CubicBezier, BladeOn, BladeOff, \
    to_json_value, from_json_value

from json import dump, dumps, load
from math import tau

from tkinter.filedialog import askopenfilename, asksaveasfilename

from subprocess import Popen, PIPE


blade_radius = 0.25


class InstructionBuilderModel:
    def __init__(self):
        self.instructions = []
        self.overlay = None
        self.overlay_path = None

    def receive(self, m):
        end = self.end_point()

        def add(p0, p1):
            return (p0[0] + p1[0], p0[1] + p1[1])

        if isinstance(m, message.PopInstruction):
            if len(self.instructions) > 0:
                self.instructions.pop()

        elif isinstance(m, message.AddLine):
            dx = -0.5 if end[0] > 0 else 0.5
            dy = -0.5 if end[1] > 0 else 0.5
            self.instructions.append(Line(end, add(end, (dx, dy))))

        elif isinstance(m, message.AddCurve):
            dx = -0.25 if end[0] > 0 else 0.25
            dy = -0.25 if end[1] > 0 else 0.25
            self.instructions.append(CubicBezier(end,
                                                 add(end, (dx, dy)),
                                                 add(end, (dx * 2, -dy)),
                                                 add(end, (dx * 4, 0))))

        elif isinstance(m, message.BladeOn):
            self.instructions.append(BladeOn())

        elif isinstance(m, message.BladeOff):
            self.instructions.append(BladeOff())

        elif isinstance(m, message.UpdatePoint):
            length = len(self.instructions)
            if length < 1:
                return
            selected = self.instructions[length - 1]
            if isinstance(selected, Line):
                if m.index == 0:
                    selected.start = m.pos
                if m.index == 1:
                    selected.end = m.pos
            if isinstance(selected, CubicBezier):
                if m.index == 0:
                    selected.p0 = m.pos
                if m.index == 1:
                    selected.p1 = m.pos
                if m.index == 2:
                    selected.p2 = m.pos
                if m.index == 3:
                    selected.p3 = m.pos

        elif isinstance(m, message.Export):
            self.export_instructions()
        elif isinstance(m, message.Import):
            self.import_instructions()
        elif isinstance(m, message.Simulate):
            self.run_simulation()
        elif isinstance(m, message.AddOverlay):
            self.add_overlay()

    def end_point(self) -> tuple[int, int]:
        i = len(self.instructions) - 1
        while i >= 0:
            inst = self.instructions[i]
            if isinstance(inst, Line):
                return inst.end
            if isinstance(inst, CubicBezier):
                return inst.p3
            i -= 1
        return (0, 0)

    def sim_dict(self):
        obj = {}
        obj['wheel_distance'] = 0.70
        obj['wheel_radius'] = 0.2
        obj['max_motor_speed'] = 5.0 * tau
        obj['blade_radius'] = blade_radius
        obj['sim_length'] = "Indefinite"
        obj['delta_time'] = {"secs": 0, "nanos": 1000000}

        if isinstance(self.overlay_path, str):
            obj['overlay_path'] = f"\"{self.overlay_path}\""
        else:
            obj['overlay_path'] = "null"

        obj['instructions'] = [to_json_value(i) for i in self.instructions]
        return obj

    def export_instructions(self, filepath=None):
        if filepath is None:
            filepath = asksaveasfilename()
            if not isinstance(filepath, str):
                return
            filepath = str(filepath)
        obj = self.sim_dict()
        with open(filepath, "w") as f:
            dump(obj, f)

    def import_instructions(self, filepath=None):
        if filepath is None:
            filepath = askopenfilename()
            if not isinstance(filepath, str):
                return
            filepath = str(filepath)
        with open(filepath, "r") as f:
            obj = dict(load(f))

        if "instructions" in obj.keys():
            obj_list = obj["instructions"]
            self.instructions = [from_json_value(o) for o in obj_list]

        if "overlay_path" in obj.keys():
            overlay_path = obj["instructions"]
            if overlay_path == 'null':
                self.overlay_path = None
            else:
                self.overlay_path = overlay_path[1:-1]

    def run_simulation(self):
        sim_input = dumps(self.sim_dict())
        dir = os.path.dirname(os.path.realpath(__file__))
        path = f"{dir}/.isp_auto_output"
        cmd = ['isp-sim', '--output', path]
        calculations = Popen(cmd, stdin=PIPE)
        calculations.communicate(sim_input.encode())
        cmd = ['python', f'{dir}/visualizer.py']
        p = Popen(cmd)
        p.wait()

    def add_overlay(self):
        if self.overlay is not None:
            self.overlay = None
            self.overlay_path = None
        else:
            filepath = askopenfilename()
            if not isinstance(filepath, str):
                return

            self.overlay = pg.image.load(filepath)
            self.overlay_path = filepath
