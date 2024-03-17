import csv
import requests
import subprocess
import urllib
import uuid

from cs50 import SQL

from flask import redirect, render_template, session
from functools import wraps

db = SQL("sqlite:///progres.db")


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function



def food_lookup(food):
    url = "https://nutrition-by-api-ninjas.p.rapidapi.com/v1/nutrition"

    querystring = {"query":food}

    headers = {
        "X-RapidAPI-Key": "58a63dc3b0msh579d67bed6ce70bp1f6552jsnf0d699611444",
        "X-RapidAPI-Host": "nutrition-by-api-ninjas.p.rapidapi.com"
    }

    try:
        response = (requests.get(url, headers=headers, params=querystring)).json()
        return [{
            "name":response[0]["name"],
            "calories_nr":response[0]["calories"],
            "protein_nr":response[0]["protein_g"],
            "carbs_nr":response[0]["carbohydrates_total_g"],
            "fats_nr":response[0]["fat_total_g"]
        }]
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def exercise_lookup(exercise):
    url = "https://exercises-by-api-ninjas.p.rapidapi.com/v1/exercises"

    querystring = {"name":exercise}

    headers = {
        "X-RapidAPI-Key": "58a63dc3b0msh579d67bed6ce70bp1f6552jsnf0d699611444",
        "X-RapidAPI-Host": "exercises-by-api-ninjas.p.rapidapi.com"
    }

    try:
        responses = requests.get(url, headers=headers, params=querystring).json()
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None

    for response in responses:
        if response["name"].lower() == exercise:
            return {
                "name":response["name"],
                "muscle":response["muscle"],
                "instructions":response["instructions"]
            }







