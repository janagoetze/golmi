from flask import Flask, request
from flask_cors import CORS
from view_update_storage import ViewUpdateStorage
import requests
import json
import argparse

# GOLMI's view API
# author: clpresearch, Karla Friedrichs
# usage: python3 view_api.py [-h] [--host HOST] [--port PORT] [--test]
# Runs on host 127.0.0.1 and port 5002 per default

# --- define globals --- #
app = Flask(__name__)
# enable cross-origin requests 
# TODO: restrict sources
CORS(app)

update_storage = ViewUpdateStorage()

# --- define routes --- # 

@app.route("/updates", methods=["POST", "GET", "DELETE"])
def updates():
	# store new updates
	if request.method == "POST":
		if not request.data:
			return "1", 400
		else:
			json_data = json.loads(request.data)
		# Attempt to store updates. Return BAD REQUEST if something went wrong
		return "0" if update_storage.store_update(json_data) else ("1", 400)
	# return stored updates. Delete updates after this
	elif request.method == "GET":
		updates = update_storage.get_updates()
		update_storage.clear()
		return updates
	# clear any stored updates
	elif request.method == "DELETE":
		update_storage.clear()
		return "0"
	return "1", 405

def selftest():
	with app.test_client() as c:
		# clear the storage
		clear_storage = c.delete("/updates")
		assert clear_storage.status == "200 OK"

		# post an update of the gripper 1
		example_update1 = {"grippers": {"1": {"type": "gripper", "x": 1, "y": 1, "width": 1, "height": 1, "rotation": 0, "mirrored": 0, "color": "blue", "gripped": None}}}
		post_new_update = c.post("/updates", data=json.dumps(example_update1))
		assert post_new_update.status == "200 OK"
	    # Make sure the updates are correctly stored
		assert update_storage.get_updates()["grippers"] == example_update1["grippers"] and \
			update_storage.get_updates()["objs"] == dict() and \
			update_storage.get_updates()["config"] == False, update_storage.get_updates()

		# post another update and make sure the old updates are still there
		# this update contains one object and a configuration update
		example_update2 = {"objs": {"1": {"type": "I", "x": 12, "y": 12, "width": 5, "height": 5, "rotation": 0, "mirrored": 0, "color": "black"}}, "config": True}
		post_new_update2 = c.post("/updates", data=json.dumps(example_update2))
		assert post_new_update2.status == "200 OK"
	    # Make sure the updates are correctly stored
		assert update_storage.get_updates()["grippers"] == example_update1["grippers"] and \
			update_storage.get_updates()["objs"] == example_update2["objs"] and \
			update_storage.get_updates()["config"] == True, update_storage.get_updates()

		# get pending updates
		get_updates = c.get("/updates")
		assert get_updates.status == "200 OK"
		assert json.loads(get_updates.data) == {"grippers": example_update1["grippers"], "objs": example_update2["objs"], "config": True}
		# make sure the updates were deleted
		assert update_storage.get_updates() == {"grippers": dict(), "objs": dict(), "config": False}

# --- command line arguments ---
parser = argparse.ArgumentParser(description="Run GOLMI's view API.")
parser.add_argument("--host", type=str, default="127.0.0.1", help="Adress to run the API on. Default: localhost.")
parser.add_argument("--port", type=str, default="5002", help="Port to run the API on. Default: 5002.")
parser.add_argument("--test", action="store_true", help="Pass this argument to perform some tests before the API is run.")

if __name__ == "__main__":
	args = parser.parse_args()
	if args.test:
		selftest()
		print("All tests passed.")
	app.run(host=args.host, port=args.port)