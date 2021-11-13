"""
The Generator is a module for the model. it can generate
random states to initialize a model based on 3 parameters:
    -number of objects
    -number of gripper
    -whether the grippers should be positioned randomly
"""


import random
import math

from model.grid import Grid
from model.obj import Obj
from model.state import State
from model.gripper import Gripper


class Generator:
    def __init__(self, model, attempts=100):
        self.model = model
        self.attempts = attempts
        self.target_grid = Grid(
            self.model.config.width,
            self.model.config.height,
            self.model.config.move_step
        )

    def _generate_grippers(self, n_grippers, random_gr_position):
        grippers = dict()
        while len(grippers) < n_grippers:
            if random_gr_position:
                taken = set()
                x = random.randint(0, self.model.config.width)
                y = random.randint(0, self.model.config.height)

                # check that grippers do not overlap
                if (x, y) not in taken:
                    taken.add((x, y))
                    index = len(grippers)
                    grippers[index] = Gripper(index, x, y)
            else:
                index = len(grippers)
                x = self.model.config.width / 2
                y = self.model.config.height / 2
                grippers[index] = Gripper(index, x, y)

        return grippers

    def _generate_target(self, index, piece_type, width, height, block_matrix):
        """
        this function generates a target block for the object mantaining:
            - index
            - piece type
            - width
            - height
            - block matrix
        parameters that will be changed:
            - x and y coordinates
            - rotation
            - if flipped
        """
        while True:
            # generate random coordinates
            x = random.randint(0, self.model.config.width - width)
            y = random.randint(0, self.model.config.height - height)

            # randomize rotation and mirrored
            rotation = 0
            mirrored = False
            if "rotate" in self.model.config.actions:
                # generate random angle for rotation
                random_rot = random.randint(
                    0, math.floor(360/self.model.config.rotation_step)
                )
                rotation = self.model.config.rotation_step * random_rot

                # rotate matrix
                block_matrix = self.model.state.rotate_block_matrix(
                    block_matrix, rotation
                )

            if "flip" in self.model.config.actions:
                mirrored = bool(random.randint(0, 1))
                if mirrored:
                    # flip matrix
                    block_matrix = self.model.state.flip_block_matrix(
                        block_matrix
                    )

            # create target object
            target_obj = Obj(
                id_n=index,
                obj_type=piece_type,
                x=x,
                y=y,
                width=width,
                height=height,
                block_matrix=block_matrix,
                rotation=rotation,
                mirrored=mirrored,
                color=None,
                is_target=True
            )

            if self.target_grid.can_move(target_obj.occupied(), index):
                self.target_grid.add_obj(target_obj)
                break

        return target_obj

    def _generate_objects(self, n_objs, target=True):
        objects = dict()
        targets = dict()
        attempt = 0
        while len(objects) < n_objs:
            # pick a random type and its height and width
            piece_type = random.choice(
                list(self.model.config.type_config.keys())
            )
            block_matrix = self.model.config.type_config[piece_type]
            height = len(block_matrix)
            width = len(block_matrix[0])

            # generate random coordinates
            x = random.randint(0, self.model.config.width - width)
            y = random.randint(0, self.model.config.height - height)

            # generate random attributes
            color = random.choice(self.model.config.colors)
            rotation = 0
            mirrored = False

            if "rotate" in self.model.config.actions:
                random_rot = random.randint(
                    0, math.floor(360/self.model.config.rotation_step)
                )
                rotation = self.model.config.rotation_step * random_rot
                block_matrix = self.model.state.rotate_block_matrix(
                    block_matrix, rotation
                )

            if "flip" in self.model.config.actions:
                mirrored = bool(random.randint(0, 1))
                if mirrored:
                    block_matrix = self.model.state.flip_block_matrix(
                        block_matrix
                    )

            # generate object
            obj = Obj(
                id_n=None,
                obj_type=piece_type,
                x=x,
                y=y,
                width=width,
                height=height,
                block_matrix=block_matrix,
                rotation=rotation,
                mirrored=mirrored,
                color=color
            )

            # if object does not overlap, add it
            if self.model.grid.can_move(obj.occupied(), None):
                index = str(len(objects))
                obj.id_n = index
                self.model.grid.add_obj(obj)

                # create a target
                if target:
                    target_obj = self._generate_target(
                        index, piece_type, width, height, block_matrix
                    )
                    obj.target = target_obj
                    targets[index] = target_obj

                objects[index] = obj
                attempt = 0
            else:
                # object overlaps, try again until number of
                # maximum attempts is reached
                if self.model.config.prevent_overlap:
                    attempt += 1
                    if attempt > self.attempts:
                        break

        return objects, targets

    def load_random_state(self, n_objs, n_grippers, random_gr_position=False):
        # get grippers
        grippers = self._generate_grippers(n_grippers, random_gr_position)

        # get objects
        objects, targets = self._generate_objects(n_objs)

        # create state
        state = State()
        state.grippers = grippers
        state.objs = objects
        state.targets = targets

        # load state
        self.model.set_state(state)
