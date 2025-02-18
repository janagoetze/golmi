from state import State
from gripper import Gripper
from obj import Obj
from timed_loop import TimedLoop
import requests
import json
from math import floor

# TODO: no object collision

class Model:
	def __init__(self, config):
		self.views = list()
		self.state = State()
		self.config = config

		# handles for loops will be saved in here to start / stop periodic actions
		# the nested dicts map gripper ids to the loop handles
		self.loops = {"move": dict(), "grip": dict(), "flip": dict(), "rotate": dict()}

	# --- getter --- #

	def get_objects(self):
		return self.state.get_objects()

	def get_object_ids(self):
		return self.state.get_object_ids()

	def get_obj_by_id(self, id):
		return self.state.get_obj_by_id(id)

	def get_grippers(self):
		return self.state.get_grippers()

	def get_gripper_ids(self):
		return self.state.get_gripper_ids()

	def get_gripper_by_id(self, id):
		return self.state.get_gripper_by_id(id)

	def get_gripped_obj(self, id):
		return self.state.get_gripped_obj(id)

	def get_gripper_coords(self, id):
		"""
		@return list: [x-coordinate, y-coordinate]
		"""
		return self.state.get_gripper_coords(id)

	def get_config(self):
		return self.config.to_dict()

	def get_width(self):
		return self.config.width

	def get_height(self):
		return self.config.height

	def get_type_config(self):
		return self.config.type_config

	#  --- events --- #

	def get_gripper_updated_event(self, id): 
		#TODO: only gripper with id!
		return {"grippers": self.get_grippers()}

	def get_new_state_loaded_event(self): 
		# update all grippers and objects. Config does not need to be reloaded.
		return {"grippers": self.get_grippers(), "objs": self.get_objects()}
	
	def get_obj_updated_event(self, id): 
		return {"objs": self.get_objects()}

	# currently unused
	def get_config_changed_event(self):
		return {"config": True}

	# --- Communicating with views --- # 

	def attach_view(self, view):
		"""
		Link a new view. Each view is notified of model changes via events.
		@param view 	URL of view API
		"""
		if view not in self.views:
			self.views.append(view)

	def detach_view(self, view):
		"""
		Removes a view from the list of listeners.
		@param view 	registered URL of view to remove
		@return true if the view was found and removed, false if the view was not subscribed
		"""
		# use while loop to deal with possible duplicate registration
		found = False
		while view in self.views:
			self.views.remove(view)
			found = True
		return True
		
	def clear_views(self):
		"""
		Removes all view listeners.
		"""
		self.views.clear()

	def _notify_views(self, updates):
		"""
		Notify all listening views of model events (usually data updates)
		@param updates 	dictionary of updates. Sent to each of the model's views
		"""
		for view in self.views:
			requests.post("http://{}/updates".format(view), data=json.dumps(updates))

	# --- Set up and configuration --- #

	def set_initial_state(self, state):
		"""
		Initialize the model's (game) state.
		@param state	State object or dict or JSON file
		"""
		# state is a JSON string or parsed JSON dictionary
		if type(state) == str or type(state) == dict:
			self._state_from_JSON(state)
		# state is a State instance
		else:
			self.state = state
		self._notify_views(self.get_new_state_loaded_event())

	def reset(self):
		"""
		Reset the current state.
		"""
		self.state = State()
		self._notify_views(self.get_new_state_loaded_event())

	# TODO: make sure pieces are on the board! (at least emit warning)
	def _state_from_JSON(self, json_data):
		if type(json_data) == str:
			# a JSON string
			json_data = json.loads(json_data)
		# otherwise assume json_data is a dict 
		try:
			# initialize an empty state
			self.state = State()
			for gr in json_data["grippers"]:
				self.state.grippers[gr] = Gripper(
					json_data["grippers"][gr]["x"],
					json_data["grippers"][gr]["y"])
				# process optional info
				if "gripped" in json_data["grippers"][gr]:
					self.state.grippers[gr].gripped = json_data["grippers"][gr]["gripped"]
				if "width" in json_data["grippers"][gr]:
					self.state.grippers[gr].width = json_data["grippers"][gr]["width"]
				elif "height" in json_data["grippers"][gr]:
					self.state.grippers[gr].height = json_data["grippers"][gr]["height"]
				elif "color" in json_data["grippers"][gr]:
					self.state.grippers[gr].color = json_data["grippers"][gr]["color"]
			
			# construct objects
			for obj in json_data["objs"]:
				self.state.objs[obj] = Obj(
					json_data["objs"][obj]["type"],
					json_data["objs"][obj]["x"],
					json_data["objs"][obj]["y"],
					json_data["objs"][obj]["width"],
					json_data["objs"][obj]["height"],
					self.get_type_config()[json_data["objs"][obj]["type"]] # block matrix for given type
				)
				# process optional info
				if "rotation" in json_data["objs"][obj]:
					# rotate the object
					self.state.rotate_obj(obj, json_data["objs"][obj]["rotation"])
				if "mirrored" in json_data["objs"][obj] and json_data["objs"][obj]["mirrored"]:
					# flip the object if "mirrored" is true in the JSON
					self.state.flip_obj(obj)
				if "color" in json_data["objs"][obj]:
					self.state.objs[obj].color = json_data["objs"][obj]["color"]
		except: 
			raise SyntaxError("Error during state initialization: JSON data does not have the right format.\n" + \
				"Please refer to the documentation.")

	# --- Gripper manipulation --- #

	def start_gripping(self, id):
		"""
		Start calling the function grip periodically until stop_gripping is called, essentially 
		repeatedly gripping / ungripping with a specified gripper.
		@param id 	gripper id
		"""
		self.stop_gripping(id)
		self.start_loop("grip", id, self.grip, id)

	def stop_gripping(self, id):
		"""
		Stop periodically gripping.
		@param id 	gripper id
		"""
		self.stop_loop("grip", id)

	def grip(self, id):
		"""
		Attempt a grip / ungrip.
		@param id 	gripper id
		"""
		# if some object is already gripped, ungrip it
		old_gripped = self.get_gripped_obj(id)
		if old_gripped:
			# state takes care of detaching object and gripper
			self.state.ungrip(id)
			self._notify_views(self.get_obj_updated_event(old_gripped))
			# notify view of gripper change.
			self._notify_views(self.get_gripper_updated_event(id))
		else: 
			# Check if gripper hovers over some object
			new_gripped = self._get_grippable(id)
			# changes to object and gripper
			if new_gripped: 
				self.state.grip(id, new_gripped)
				# notify views of the now attached object
				self._notify_views(self.get_obj_updated_event(new_gripped))
				# notify view of gripper change.
				self._notify_views(self.get_gripper_updated_event(id))

	def start_moving(self, id, x_steps, y_steps, step_size=None):
		"""
		Start calling the function move periodically until stop_moving is called.
		@param id 	gripper id
		@param x_steps	steps to move in x direction. Step size is defined by model configuration
		@param y_steps	steps to move in y direction. Step size is defined by model configuration
		@param step_size 	Optional: size of step unit in blocks. Default: use move_step of config
		"""
		# cancel any ongoing movement
		self.stop_moving(id)
		self.start_loop("move", id, self.move, id, x_steps, y_steps, step_size)

	def stop_moving(self, id):
		"""
		Stop calling move periodically.
		@param id 	gripper id
		"""
		self.stop_loop("move", id)

	def move(self, id, x_steps, y_steps, step_size=None):
		"""
		If allowed, move the gripper x_steps steps in x direction and y_steps steps in y direction.
		Only executes if the goal position is inside the game dimensions. Notifies views of change.
		@param id 	gripper id
		@param x_steps	steps to move in x direction. Step size is defined by model configuration
		@param y_steps	steps to move in y direction. Step size is defined by model configuration
		@param step_size 	Optional: size of step unit in blocks. Default: use move_step of config
		"""
		# if no step_size was given, query the config
		if not step_size: step_size = self.config.move_step
		dx = x_steps*step_size # distance in x direction to move
		dy = y_steps*step_size # distance in y direction to move
		gripper_x, gripper_y = self.get_gripper_coords(id)
		gr_obj = self.get_gripped_obj(id)
		if gr_obj:
			gr_obj = self.get_obj_by_id(gr_obj)
			# if an object is gripped, both the gripper and the object have to stay inside the board
			if self._is_in_limits(gripper_x + dx, gripper_y + dy) and \
			   self._is_in_limits(gr_obj.get_center_x() + dx, gr_obj.get_center_y() + dy):

				self.state.move_gr(id, dx, dy)
				self.state.move_obj(self.get_gripped_obj(id), dx, dy)
				# notify the views. A gripped object is implicitly redrawn. 
				self._notify_views(self.get_gripper_updated_event(id))

		# if no object is gripped, only move the gripper
		elif self._is_in_limits(gripper_x + dx, gripper_y + dy):
			self.state.move_gr(id, dx, dy)
			# notify the views. A gripped object is implicitly redrawn. 
			self._notify_views(self.get_gripper_updated_event(id))

	def start_rotating(self, id, direction, step_size=None):
		"""
		Start calling the function rotate periodically until stop_rotating is called.
		@param id 	id of the gripper whose gripped object should be rotated
		@param direction	-1 for leftwards rotation, 1 for rightwards rotation
		@param step_size	Optional: angle to rotate per step. Default: use rotation_step of config
		"""
		# cancel any ongoing rotation
		self.stop_rotating(id)
		self.start_loop("rotate", id, self.rotate, id, direction, step_size)

	def stop_rotating(self, id):
		"""
		Stop calling rotate periodically.
		@param id 	gripper id
		"""
		self.stop_loop("rotate", id)

	def rotate(self, id, direction, step_size=None):
		"""
		If the gripper 'id' currently grips some object, rotate this object one step.
		@param id 	id of the gripper whose gripped object should be rotated
		@param direction	-1 for leftwards rotation, 1 for rightwards rotation
		@param step_size	Optional: angle to rotate per step. Default: use rotation_step of config
		"""
		# check if an object is gripped
		gr_obj = self.get_gripped_obj(id) 
		if gr_obj:
			# if not step_size was given, use the default from the configuration
			if not step_size: step_size = self.config.rotation_step
			self.state.rotate_obj(gr_obj, direction * step_size)
			# notify the views. The gripped object is implicitly redrawn. 
			self._notify_views(self.get_gripper_updated_event(id))

	def start_flipping(self, id):
		"""
		Start calling the function flip periodically until stop_flipping is called.
		@param id 	id of the gripper whose gripped object should be flipped
		"""
		# cancel any ongoing flipping
		self.stop_flipping(id)
		self.start_loop("flip", id, self.flip, id)

	def stop_flipping(self, id):
		"""
		Stop calling flip periodically.
		@param id 	gripper id
		"""
		self.stop_loop("flip", id)

	def flip(self, id):
		"""
		Mirror the object currently gripped by some gripper.
		@param id 	gripper id
		"""
		# check if an object is gripped
		gr_obj = self.get_gripped_obj(id) 
		if gr_obj:
			self.state.flip_obj(gr_obj)
			# notify the views. The gripped object is implicitly redrawn. 
			self._notify_views(self.get_gripper_updated_event(id))
		
	def _get_grippable(self, gr_id):
		"""
		Find an object that is in the range of the gripper.
		@param id 	gripper id 
		@return id of object to grip or None
		"""
		# Gripper position. It is just a point.
		x, y = self.get_gripper_coords(gr_id)
		for obj_id in self.get_object_ids(): 
			obj = self.get_obj_by_id(obj_id)
			# (gridX, gridY) is the position on the type grid the gripper would be on
			grid_x = floor(x-obj.x)
			grid_y = floor(y-obj.y)
			# get the object block matrix - rotation and flip are already applied to the matrix
			type_matrix = obj.block_matrix

			# check whether the gripper is on the object matrix
			if grid_x >= 0 and grid_y >= 0 and grid_y < len(type_matrix) and grid_x < len(type_matrix[0]):
				# check whether a block is present at the grid position
				if type_matrix[grid_y] and type_matrix[grid_y][grid_x]: 
					return obj_id
		return None
		
	def _is_in_limits(self, x, y):
		"""
		Check whether given coordinates are within the space limits.
		@param x 	x coordinate to check
		@param y 	y coordinate to check
		"""
		return self._x_in_limits(x) and self._y_in_limits(y)
		
	def _x_in_limits(self, x):
		"""
		Check whether given x coordinate is within the space limits.
		@param x 	x coordinate to check
		"""
		return (x >= 0 and x<= self.get_width())
		
	def _y_in_limits(self, y):
		"""
		Check whether given y coordinate is within the space limits.
		@param y 	y coordinate to check
		"""
		return (y >= 0 and y <= self.get_height())

	# --- Loop functionality ---

	def start_loop(self, action_type, gripper, fn, *args, **kwargs):
		self.loops[action_type][gripper] = TimedLoop(self.config.action_interval, fn, *args, **kwargs)

	def stop_loop(self, action_type, gripper):
		if gripper in self.loops[action_type]: 
			self.loops[action_type][gripper].cancel()

if __name__ == "__main__":
	# Unit tests
	from config import Config
	test_config = Config("../pentomino/pentomino_types.json")
	test_model = Model(test_config)
	assert len(test_model.get_objects())

	test_model.add_view("address:port")
	assert test_model.views == ["address:port"]
