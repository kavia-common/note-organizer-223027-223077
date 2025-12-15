from flask_smorest import Blueprint
from flask.views import MethodView

# PUBLIC_INTERFACE
blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")


@blp.route("/")
class HealthCheck(MethodView):
    """Health check endpoint."""
    def get(self):
        return {"message": "Healthy"}
