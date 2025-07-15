"""Blueprint for generic site pages (landing, FAQ)."""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# expose legacy endpoint name 'faq'
@main_bp.route("/faq", endpoint="faq")
def faq():
    return render_template("faq.html")
