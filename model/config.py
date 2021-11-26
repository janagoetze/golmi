"""
Class to store settings such as board width, allowable actions, etc.
"""

import json
import random


class Config:
    def __init__(self, config):
        """
        Constructor.
        @param type_config	    json file or object mapping types
                                to 0/1 matrices indicating type shapes
        @param width 	        number of vertical 'blocks' on the board
                                e.g. for block-based rendering. default:20
        @param height	        number of horizontal 'blocks' on the board
                                e.g. for block-based rendering. default:20
        @param snap_to_grid 	True to lock objects to the nearest block at
                                gripper release. default:False
        @param prevent_overlap 	True to prohibit any action that would lead
                                to objects overlapping. default:True
        @param actions 	        array of strings naming allowed object
                                manipulations. default:['move', 'rotate']
        @param move_step	    step size for object movement. default:0.2[blocks]
        @param rotation_step	applied angle when object is rotated. Limitations
                                might exist for View implementations.
                                default:90
        @param action_interval	frequency of repeating looped actions in seconds
                                default: 0.5
        """

        with open(config, "r", encoding="utf-8") as infile:
            configs = json.load(infile)

        self.width = configs.get('width', 20)
        self.height = configs.get('height', 20)
        self.snap_to_grid = configs.get('snap_to_grid', False)
        self.prevent_overlap = configs.get('prevent_overlap', True)
        self.actions = configs.get('actions', ["move", "rotate", "flip", "grip"])
        self.move_step = configs.get('move_step', 0.5)
        self.rotation_step = configs.get('rotation_step', 90)
        self.action_interval = configs.get('action_interval', 0.1)
        self.verbose = configs.get('verbose', False)
        self.block_on_target = configs.get('block_on_target', True)
        self.type_config = configs.get('pieces', None)

        # make sure step size is allowed
        if not ( isinstance(self.move_step, int)
          or (1/(self.move_step % 1)).is_integer()
          ):
            raise ValueError(
                f"Selected step size of {self.move_step} is not allowed\n"
                "Please select a step size that satisfies the following "
                "condition: (1/(step size % 1)) must be an integer"
            )

        if not self.type_config:
            raise ValueError("No pieces specified.")

        self.colors = configs.get('colors',
                                  ["red",
                                   "orange",
                                   "yellow",
                                   "green",
                                   "blue",
                                   "purple",
                                   "saddlebrown",
                                   "grey"
                                   ])
        if isinstance(self.colors[0], list):
            self.colors = random.choice(self.colors)

    def __repr__(self):
        properties = ", ".join(vars(self).keys())
        return f"Config({properties})"

    def get_types(self):
        return self.type_config.keys()

    def to_dict(self):
        """
        Constructs a dictionary from this instance.
        """
        return {
            "width": self.width,
            "height": self.height,
            "actions": self.actions,
            "rotation_step": self.rotation_step,
            "type_config": self.type_config,
            "colors": self.colors
        }
