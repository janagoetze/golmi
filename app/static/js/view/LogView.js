$(document).ready(function () {
	/**
	 * Logger class. Relies on events exchanged between a specific client and server.
	 * Starts logging as soon as the client receives the first state
	 * @param {Socket io connection to the server} modelSocket
	 * @param {set true to save the full state at every change, false to only log the update}
	 */
	this.LogView = class LogView {
		constructor(modelSocket, logFullState=true) {
			this.socket = modelSocket;

			this.data = {"log": new Array()};
			this.logFullState = logFullState;
			this.startTime;
			// only used if logFullState is true
			this.currentObjs = new Object();
			this.currentGrippers = new Object();
			this.currentConfig = new Object();
			// start listening to events
			this._initSocketEvents();
		}

		/**
		 * Start listening to events emitted by the model socket. After this 
		 * initialization, the view logs the client-server communication.
		 */
		_initSocketEvents() {
			this.socket.on("update_state", (state) => {
				// Assumes the logging starts at first 'update_state' event.
				let timeOffset;
				if (!this.startTime) {
					// don't start logging if an empty state was sent
					if (Object.keys(state["objs"]).length == 0 && 
						Object.keys(state["grippers"]).length == 0) {
						return;
					}
					this.startTime = Date.now();
					timeOffset = 0;
				} else {
					timeOffset = Date.now() - this.startTime;
				}
				if (this.logFullState) {
					this.currentObjs = state["objs"];
					this.currentGrippers = state["grippers"];
					this._addSnapshot(timeOffset, this._getFullState());
				} else {
					this._addSnapshot(timeOffset, state);
				}
			})
			this.socket.on("update_grippers", (grippers) => {
				if (this.startTime) {
					let timeOffset = Date.now() - this.startTime;
					if (this.logFullState) {
						this.currentGrippers = grippers;
						this._addSnapshot(timeOffset, this._getFullState());
					} else {
						this._addSnapshot(timeOffset, {"gripper": grippers});
					}
				}
				
			});
			this.socket.on("update_objs", (objs) => {
				if (this.startTime) {
					let timeOffset = Date.now() - this.startTime;
					if (this.logFullState) {
						this.currentObjs = objs;
						this._addSnapshot(timeOffset, this._getFullState());
					} else {
						this._addSnapshot(timeOffset, {"objs": objs});
					}
				}
			});
			this.socket.on("update_config", (config) => {
				if (this.startTime) {
					let timeOffset = Date.now() - this.startTime;
					if (this.logFullState) {
						this.currentConfig = config;
						this._addSnapshot(timeOffset, this._getFullState());
					} else {
						this._addSnapshot(timeOffset, {"config": config});
					}
				} else if (this.logFullState) {
					// save the config for later in case it arrived before the first state
					this.currentConfig = config;
				} else {
					// save the config once in the beginning in case it arrived before the first state
					this._addSnapshot(-1, {"config": config});
				}
			});
		}

		/**
		 * Add additional data to the current log. Will be saved at 
		 * the top-level of the log object.
		 * @param {string, identifier for the data, 'log' is reserved} key
		 * @param {data to save, can be any json-friendly format, e.g. object, list, string} data
		 */
		addData(key, data) {
			if (key == "log") {
				// 'log' key is reserved for the collected event data
				console.log("Error at LogView: Cannot manually add data with reserved key 'log'.");
			} else {
				this.data[key] = data;
			}
		}

		/**
		 * Save the data on the server.
		 * @param {route to POST the collected data to, default: /save_log} endpoint
		 * @return true at success
		 */
		sendData(endpoint="/save_log") {
			fetch(new Request(endpoint, {
				method:"POST", 
				headers: { "Content-Type": "application/json;charset=utf-8" },
				body:JSON.stringify(this.data)}))
			.then(response => {
				if (!response.ok) {
					console.log("Error saving log data!");
					return true;
				} else {
					console.log("Saved log data to the server.");
					return false;
				}
			});
		}

		/**
		 * Delete any data collected so far.
		 */
		clear() {
			this.data = {"log": new Array()};
			this.startTime = undefined;
			this.currentObjs = new Object();
			this.currentGrippers = new Object();
			this.currentConfig = new Object();
		}

		// --- helper functions --- //

		/**
		 * @return a state object containing the objects, grippers and config as received last
		 */
		_getFullState() {
			return {"objs": this.currentObjs,
					"grippers": this.currentGrippers,
					"config": this.currentConfig};
		}

		/**
		 * Add a single data update with a timestamp to the log.
		 * @param {timestamp to associate the data with, e.g. time passed since log start} timestamp
		 * @param {update to save} data
		 */
		_addSnapshot(timestamp, data) {
			this.data["log"].push([timestamp, data]);
		}
	}; // class LogView end
}); // on document ready end