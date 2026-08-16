from flask import Flask, jsonify, render_template, request


def _response(state, status=200, error=None):
    return jsonify({"state": state, "error": error}), status


def create_app(controller):
    app = Flask(__name__)
    app.config["DISPLAY_CONTROLLER"] = controller

    @app.get("/")
    def index():
        return render_template("index.html", page="display")

    @app.get("/automation")
    def automation():
        return render_template("index.html", page="automation")

    @app.get("/api/state")
    def state():
        return _response(controller.get_state())

    @app.get("/api/modes")
    def modes():
        return _response({"modes": controller.list_modes()})

    @app.get("/api/assets")
    def assets():
        return _response({"assets": controller.list_assets()})

    @app.post("/api/mode")
    def select_mode():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _response(None, 400, "Request body must be a JSON object.")
        try:
            return _response(controller.select_mode(body.get("mode"), body.get("asset_id")))
        except ValueError as error:
            return _response(None, 400, str(error))
        except RuntimeError as error:
            return _response(None, 409, str(error))

    @app.patch("/api/settings")
    def settings():
        body = request.get_json(silent=True)
        try:
            return _response(controller.update_settings(body))
        except ValueError as error:
            return _response(None, 400, str(error))

    @app.post("/api/power")
    def power():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or "on" not in body:
            return _response(None, 400, "Request body must include boolean 'on'.")
        try:
            return _response(controller.set_power(body["on"]))
        except ValueError as error:
            return _response(None, 400, str(error))

    return app
