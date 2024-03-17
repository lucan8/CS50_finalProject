import os
#learn more about sendBacon which let s you continue workout even if tab is closed
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
import json
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from help import apology, login_required, food_lookup, exercise_lookup
import requests

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///progres.db")


START_TIME = ""

END_TIME = ""

MUSCLE_LIST = ["abdominals",
                "abductors",
                "adductors",
                "biceps",
                "calves",
                "chest",
                "forearms",
                "glutes",
                "hamstrings",
                "lats",
                "lower_back",
                "middle_back",
                "neck",
                "quadriceps",
                "shoulders",
                "traps",
                "triceps"]

SECONDS_PASSED = -1 #This represents the seconds passed in an active workout and it updates when the app is closed

CHOSEN_MEAL = ""

CHOSEN_FOOD = ""#This is for food info

CHOSEN_DATE = ""

NEW_FOOD = ""#This is for creating food.Couldn't use CHOSEN_FOOD because the use

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def isfloat(str):
    try:
        float(str)
    except ValueError:
        return False
    return True


def has_digits(str):
    for char in str:
        if char.isdigit() == True:
            return True
    return False


def has_symbols(str):
    symbols = ["!","@","#","$","%","^","&","*"]
    for char in str:
        if char in symbols:
            return True
    return False


def has_letters(str):
    for char in str:
        if char.isalpha() == True:
            return True
    return False


def get_seconds():
    delta = END_TIME - START_TIME

    sec = int(delta.total_seconds())
    return sec


#not needed at the moment
def time_passed(sec):
    hours = int(sec / (60 * 60))

    min = int(sec / 60 - hours * 60)

    sec = sec % 60

    if hours < 10:
        hours = "0" + str(hours)

    if min < 10:
        min = "0" + str(min)

    if sec < 10:
        sec = "0" + str(sec)

    time_passed = str(hours) + ":" + str(min) + ":" + str(sec)

    return time_passed


def start_end():
    now = datetime.datetime.now()
    global START_TIME

    if START_TIME == "":
        START_TIME = now.strftime("%H:%M:%S")
        START_TIME = datetime.datetime.strptime(START_TIME, "%H:%M:%S")

    global END_TIME
    END_TIME = now.strftime("%H:%M:%S")
    END_TIME = datetime.datetime.strptime(END_TIME, "%H:%M:%S")


def caloriesCalculator(weight, height, age, gender, activity_level):

     if gender == "Female":
        calories_burned = 655.1 + (9.563 * weight) + (1.850 * height) - (4.676 * age)
     else:
        calories_burned = 66.47 + (13.75 * weight) + (5.003 * height) - (6.755 * age)

     if activity_level == 1:
        calories_burned = calories_burned * 1.2

     elif activity_level == 2:
        calories_burned = calories_burned * 1.375

     elif activity_level == 3:
        calories_burned = calories_burned * 1.55

     elif activity_level == 4:
        calories_burned = calories_burned * 1.725

     else:
        calories_burned = calories_burned * 1.9

     return calories_burned


def getTemplate(id):
    if id == -1:#This means the active template is requested
        aux = db.execute("SELECT MAX(id) FROM templates WHERE user_id = ?", session["user_id"])
        id = aux[0]["MAX(id)"]

    #Getting name of template
    template_name = db.execute("SELECT name FROM templates WHERE id = ?", id)
    template_name = template_name[0]['name']

    #Getting all the exercises from the template with the given id
    exercises = db.execute("SELECT * FROM ex_templates WHERE template_id = ?", id)

    #Storing the names of the exercises,the nr of sets for each,and the nr of sets as a list for each
    names = []
    nr_sets = {}
    nr_sets_list = {}

    for exercise in exercises:
        names.append(exercise['name'])

        nr_sets[exercise['name']] = exercise['nr_sets']
        nr_sets_list[exercise['name']] = list(range(exercise['nr_sets']))

    return{
        'names':names,
        'nr_sets':nr_sets,
        'nr_sets_list':nr_sets_list,
        'template_name':template_name
    }

def getTruePr():
    PR_list = {}
    true_rm = -1

    aux_workouts = db.execute("SELECT id,start_date FROM workouts WHERE user_id = ?", session["user_id"])

    for workout in aux_workouts:

        aux_ex = db.execute("SELECT name,id FROM exercises WHERE workout_id = ?", workout["id"])
        for ex in aux_ex:
            weight_reps = db.execute("SELECT weight,reps FROM sets WHERE exercise_id = ?", ex['id'])
            workout_pr = 0

            #Calculate the best set for the exercises with this id
            for ex_set in weight_reps:
                rm = round(int(ex_set["weight"]) * (36 / (37 - ex_set["reps"])), 2)#Calculator for 1RM(Brzycki)
                if rm > workout_pr:
                    workout_pr = rm

            #Getting the best set out of the best sets
            if workout_pr > true_rm:
                print(ex)
                true_rm = workout_pr


            #List of the best sets for given ex for each workout it appeared in
                try:
                    PR_list[ex['name']].append(workout_pr)
                except KeyError:
                    PR_list[ex['name']] = [workout_pr]

    print(PR_list)
    return PR_list ,true_rm

#for charts
def getExerciseIds_StartDates(ex_name):
    ex_ids = []
    workout_startDates = []

    aux_workouts = db.execute("SELECT id,start_date FROM workouts WHERE user_id = ?", session["user_id"])

    for i in range(len(aux_workouts)):

        aux_ex = db.execute("SELECT name,id FROM exercises WHERE workout_id = ?", aux_workouts[i]["id"])

        for j in range(len(aux_ex)):
            if ex_name == aux_ex[j]["name"]:
                #We found the exercise in the list

                workout_startDates.append(aux_workouts[i]["start_date"])
                ex_ids.append(aux_ex[j]["id"])
    return {
        "workout_startDates":workout_startDates,
        "ex_ids":ex_ids
    }

#Gives information about either workouts or templates
def info(element):
    if element == 'workout':
        element = db.execute("SELECT * FROM workouts WHERE user_id = ? ORDER BY id DESC", session["user_id"])
        if element:
            active = element[0]['workout_duration']
        else:
            active = 0
    else:
        element = db.execute("SELECT * FROM templates WHERE user_id = ? ORDER BY id DESC", session["user_id"])
        if element:
            active = element[0]['created']
        else:
            active = 0

    length = list(range(1, len(element)))

    return {
        "element":element,
        "active":active,
        "length":length
    }

def delete_workout(workout_id):
    #Getting the id of the first exercise in the workout and the nr of exercises for the workout
    aux = db.execute("SELECT id FROM exercises WHERE workout_id = ?", workout_id)

    for i in range(len(aux)):
        delete_exercise(aux[i]['id'])

        #Decreasing the ids of the rest of the exercises that will be deleted beacuse they were
        #Also updated into the db
        for j in range(i + 1, len(aux)):
            aux[j]['id'] -= 1

    #Deleting workout
    db.execute("DELETE FROM workouts WHERE id = ?", workout_id)

    #Decreasing the workout_id from the exercises that are from workouts started later
    db.execute("UPDATE exercises SET workout_id = workout_id - 1 WHERE workout_id > ?", workout_id)

    #Decreasing the ids of the workouts performed after this one
    db.execute("UPDATE workouts SET id = id - 1 WHERE id > ?", workout_id)

    #Updating the sequence to the new max id
    db.execute("UPDATE `sqlite_sequence` SET `seq` = (SELECT MAX(id) FROM workouts) WHERE `name` = 'workouts'")


def delete_exercise(ex_id):
    #Getting the id of the first set in the exercise and the nr of sets for the exercise
    aux = db.execute("SELECT id FROM sets WHERE exercise_id = ?", ex_id)

    for i in range(len(aux)):

        delete_set(aux[i]['id'])

        #Decreasing the ids of the rest of the sets that will be deleted beacuse they were
        #Also updated into the db
        for j in range(i + 1, len(aux)):
            aux[j]['id'] -= 1

    #Deleting exercise
    db.execute("DELETE FROM exercises WHERE id = ?", ex_id)

    #Decreasing the exercise_id from the sets that are from exercises started later
    db.execute("UPDATE sets SET exercise_id = exercise_id - 1 WHERE exercise_id > ?", ex_id)

    #Decreasing the ids of the exercises performed after this one
    db.execute("UPDATE exercises SET id = id - 1 WHERE id > ?", ex_id)

    #Updating the sequence to the new max id
    db.execute("UPDATE `sqlite_sequence` SET `seq` = (SELECT MAX(id) FROM exercises) WHERE `name` = 'exercises'")


def delete_set(set_id):
    #Deleting the given set
    db.execute("DELETE FROM sets WHERE id = ?", set_id)

    #Decreasing the ids of the sets performed after this one
    db.execute("UPDATE sets SET id = id - 1 WHERE id > ?", set_id)

    #Updating the sequence to the new max id
    db.execute("UPDATE `sqlite_sequence` SET `seq` = (SELECT MAX(id) FROM sets) WHERE `name` = 'sets'")


def getWorkoutInformation(workout_id):
    last_workout_exercises = db.execute("SELECT id,name,nr_sets FROM exercises WHERE workout_id = ?", workout_id)
    ex_names = []
    weight = {}
    reps = {}
    sets_list = {}
    nr_sets = {}
    saved = {}
    for i in range(len(last_workout_exercises)):
        ex_names.append(last_workout_exercises[i]["name"])

        weight[ex_names[i]] = []
        reps[ex_names[i]] = []
        saved[ex_names[i]] = []

        nr_sets[ex_names[i]] = last_workout_exercises[i]["nr_sets"]

        sets_list[ex_names[i]] = list(range(last_workout_exercises[i]["nr_sets"]))

        weight_reps = db.execute("SELECT weight,reps,saved FROM sets WHERE exercise_id = ?", last_workout_exercises[i]["id"])

        for j in sets_list[ex_names[i]]:

            weight[ex_names[i]].append(weight_reps[j]["weight"])
            reps[ex_names[i]].append(weight_reps[j]["reps"])

            saved[ex_names[i]].append(weight_reps[j]['saved'])
    return{
        "weight":weight,
        "reps":reps,
        "sets_list":sets_list,
        "nr_sets":nr_sets,
        "ex_names":ex_names,
        'saved':saved
    }


def getDatabaseExercises():
    exercises = db.execute("SELECT * FROM exercises_info WHERE user_id = ?", session["user_id"])

    return exercises



def getExPrs(ex_name):
    lift_info = db.execute("SELECT pr_list,dates,PR FROM lifts_info WHERE name = ? AND user_id = ?", ex_name, session['user_id'])
    lift_info = lift_info[0]
    lift_info['pr_list'] = [float(pr) for pr in lift_info['pr_list'].split(',')]
    lift_info['dates'] = lift_info['dates'].split(',')

    return lift_info['pr_list'], lift_info['dates'], lift_info['PR']


def insertWorkoutPrs(ex_names, weight_list, reps_list, date):
    for ex in ex_names:
        #iterating over the sets
        set_pr = 0
        for weight,reps in zip(weight_list[ex], reps_list[ex]):
            rm = round(weight * (36 / (37 - reps)), 2)#Calculator for 1RM(Brzycki)
            #Setting the pr of this exercise in the current workout
            if rm > set_pr:
                set_pr = rm
        #Select the id of the exercise
        lift_info = db.execute("SELECT id,pr_list,PR,dates FROM lifts_info WHERE user_id = ? AND name = ?", session['user_id'], ex)

        #This means exercise has been performed before so we just add to pr_list
        if lift_info:
            #'Appending' the set pr to the list
            lift_info[0]['pr_list'] = lift_info[0]['pr_list'] + ',' + str(set_pr)

            #Testing if a new PR was set for this exercise
            if set_pr > lift_info[0]['PR']:
                lift_info[0]['PR'] = set_pr

            #'Appending' the date to the list
            lift_info[0]['dates'] = lift_info[0]['dates'] + ',' + date

            db.execute("UPDATE lifts_info SET pr_list = ?,PR = ?,dates = ? WHERE user_id = ? AND name = ?", lift_info[0]['pr_list'], lift_info[0]['PR'], lift_info[0]['dates'], session['user_id'], ex)

        #This means exercise has not been performed before by the user so we have to insert it
        else:
            db.execute("INSERT INTO lifts_info(name, pr_list, dates, PR, user_id) VALUES(?,?,?,?,?)", ex, str(set_pr), date, set_pr, session['user_id'])
    return



def insertDietGoals(diet_goal, calories_goal):
    if diet_goal == "Lose weight(cut)":
        calories_goal = (calories_goal - 300)
        protein_goal = round((0.4 * (calories_goal) / 4.0), 2)
        carbs_goal = round((0.4 * (calories_goal) / 4.0), 2)
        fats_goal = round((0.2 * (calories_goal) / 9.0), 2)

    elif diet_goal == "Maintain weight":
        protein_goal = round((0.3 * (calories_goal) / 4.0), 2)
        carbs_goal = round((0.4 * (calories_goal) / 4.0), 2)
        fats_goal = round((0.3 * (calories_goal) / 9.00), 2)

    else:
        calories_goal = (calories_goal + 300)
        protein_goal = round((0.3 * (calories_goal) / 4.0), 2)
        carbs_goal = round((0.4 * (calories_goal) / 4.0), 2)
        fats_goal = round((0.3 * (calories_goal) / 9.00), 2)
    db.execute("INSERT INTO diet_goals(calories_goal, protein_goal, carbs_goal, fats_goal, user_id) VALUES(?,?,?,?,?)", calories_goal, protein_goal, carbs_goal, fats_goal, session['user_id'])



def getDiet(date):
    diet_day_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], date)
    meals_info_today = db.execute("SELECT * FROM meals WHERE diet_days_id = ?", diet_day_id[0]["id"])

    calories_burned = 0
    protein_nr = carbs_nr = fats_nr = 0

    meals_today = []
    foods_today = {}
    #Selecting the meals of today
    #Try making it a function
    for i in range(len(meals_info_today)):
        food_info = db.execute("SELECT name,calories_nr,protein_nr,carbs_nr,fats_nr FROM food WHERE meal_id = ?",meals_info_today[i]["id"])

        meals_today.append(meals_info_today[i]["name"])

        foods_today[meals_today[i]] = []

        for j in range(len(food_info)):
            foods_today[meals_today[i]].append(food_info[j]["name"])

            calories_burned = calories_burned + food_info[j]["calories_nr"]#grams/100 * food_info[j][...]

            protein_nr = protein_nr + food_info[j]["protein_nr"]
            carbs_nr = carbs_nr + food_info[j]["carbs_nr"]
            fats_nr = fats_nr + food_info[j]["fats_nr"]
    return {
        "meals_today":meals_today,
        "foods_today":foods_today,
        "calories_burned":round(calories_burned, 2),
        "protein_nr":round(protein_nr, 2),
        "carbs_nr":round(carbs_nr, 2),
        "fats_nr":round(fats_nr, 2)
    }


def getFoodFromMeal(meal, date):
    diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], date)
    meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", meal, diet_id[0]["id"])
    aux = db.execute("SELECT name FROM food WHERE meal_id = ?", meal_id[0]["id"])

    foods_today = []
    for i in range(len(aux)):
        foods_today.append(aux[i]["name"])
    return foods_today


def insertSearchedFood(food_name, meal_id, grams):
    grams = float(grams)
    food_info = food_lookup(food_name)

    #This means the food was searched and found using database
    if food_info == None:
        food_info = db.execute("SELECT * FROM food_info WHERE name = ?", food_name)

    #Inserting the food into the meal
    for i in range(len(food_info)):
        if food_info[i]["name"] == food_name:
            db.execute("INSERT INTO food(name,calories_nr,protein_nr,carbs_nr,fats_nr,g,meal_id) VALUES(?,?,?,?,?,?,?)",food_info[i]["name"].lower(), grams / 100 * food_info[i]["calories_nr"], grams / 100 * food_info[i]["protein_nr"], grams / 100 * food_info[i]["carbs_nr"], grams / 100 * food_info[i]["fats_nr"], grams, meal_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username").strip())

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        aux = db.execute("SELECT username FROM users")
        usernames = []
        for i in range(len(aux)):
            usernames.append(aux[i]["username"])

        if not username or username in usernames:
           return apology("You haven't typed a name or the name already exists")

        if password != confirmation or not password or not confirmation:
           return apology("You haven't typed a password/confirmation or password and confirmation don't match")

        if has_digits(password) == False or has_symbols(password) == False or has_letters(password) == False:
           return apology("Password must contain at least a letter,a number and a symbol")

        db.execute("INSERT INTO users(username, hash) VALUES(?, ?)",username, generate_password_hash(password))
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/new_pass", methods=["GET", "POST"])
@login_required
def new_pass():
    if request.method == "GET":
        return render_template("new_pass.html")
    else:
        typed_password = request.form.get("password")

        typed_username = request.form.get("username")
        new_password = request.form.get("new_password")

        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        password = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])

        if username[0]["username"] != typed_username:
            return apology("The username typed does not match the user's username")

        if not check_password_hash(password[0]["hash"], typed_password):
            return apology("The password typed does not match the user's password")

        if check_password_hash(password[0]["hash"], new_password):
            return apology("New password can't be old password")

        if has_digits(password) == False or has_symbols(password) == False or has_letters(password) == False:
           return apology("Password must contain at least a letter,a number and a symbol")

        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new_password), session["user_id"])
        return redirect("/")

@app.route("/", methods = ['GET'])
@login_required
def index():
    username = db.execute("SELECT username FROM users WHERE id = ?", session['user_id'])

    nr_workouts = db.execute("SELECT COUNT(id) FROM workouts WHERE user_id = ? AND workout_duration != 'workout in progress'", session['user_id'])

    if nr_workouts[0]['COUNT(id)'] == 0:
        return render_template("index.html", username = username[0]['username'], nr_workouts = 0, strongest_lift = 'No exercises performed', true_rm = "No workout performed", PR_list = [], dates = [])
    else:
        #Getting the name of the exercise with the hightest PR and the list of prs for each workout it
        #appeared in,as well as the dates of those workouts

        strongest_lift = db.execute("SELECT name FROM lifts_info WHERE user_id = ? AND PR = (SELECT MAX(PR) FROM lifts_info WHERE user_id = ?)", session['user_id'], session['user_id'])
        if strongest_lift:
            PR_list, dates, true_rm = getExPrs(strongest_lift[0]['name'])
        else:
            return render_template("index.html", username = username[0]['username'], nr_workouts = nr_workouts[0]['COUNT(id)'], strongest_lift = "No workout performed", true_rm = "No workout performed", PR_list = [], dates = [])


        return render_template("index.html", username = username[0]['username'], nr_workouts = nr_workouts[0]['COUNT(id)'], strongest_lift = strongest_lift[0]['name'], PR_list = PR_list, dates = dates, true_rm = true_rm)


@app.route("/templates", methods = ["GET", "POST"])
@login_required
def templates():
    data = info('template')
    templates = data['element']

    if request.method == "POST":#Starts a new template

        database_ex = getDatabaseExercises()
        template_name = (request.form.get("template_name")).strip()

        db.execute("INSERT INTO templates(name,created,user_id) VALUES(?,?,?)", template_name, "no", session["user_id"])
        return render_template("new_template.html", template_name = template_name, database_ex = database_ex,NEW_EXERCISES_NAMES = [], NEW_EXERCISES_SETS = {}, NEW_EXERCISES_LENGTH = {})
    else:
        #Displays past templates
        return render_template("templates.html",templates = templates, length = data['length'], created = data['active'])


#This only renders new_template so there will only be get requests
@app.route("/new_template", methods = ["GET"])
@login_required
def new_template():
    data = getTemplate(-1)

    database_ex = getDatabaseExercises()

    return render_template("new_template.html", NEW_EXERCISES_NAMES = data['names'], NEW_EXERCISES_SETS = data['nr_sets_list'], NEW_EXERCISES_LENGTH = data['nr_sets'], template_name = data['template_name'], database_ex = database_ex)


@app.route("/create_temp", methods = ["GET"])
@login_required
def create_temp():
    #Ending the template
    db.execute('UPDATE templates SET created = "yes" WHERE created = "no"')

    #Getting data about all templates
    data = info('template')

    return render_template("templates.html",templates = data['element'], length = data['length'], created = data['active'])




#Here we either add an exercise to the template or a set
@app.route("/add_template", methods = ["POST","PUT"])
@login_required
def add_template():
    #Getting the id of active template
    print(request.method)
    aux = db.execute("SELECT id FROM templates WHERE created = 'no' AND user_id = ?", session["user_id"])
    temp_id = aux[0]['id']

    if request.method == 'POST':#Adding an exercise
        data = request.get_json()
        ex_name = data["ex_name"]

        #This means the exercise was created,so we store it into db
        if 'muscle' in data:
            #In case the user inserted as an option a muscle not in the predefined list
            if data['muscle'] not in MUSCLE_LIST:
                return apology('',200)
            db.execute("INSERT INTO exercises_info(name,muscle,instructions, user_id) VALUES(?,?,?,?)", ex_name, data['muscle'], data['instructions'], session["user_id"])

        db.execute("INSERT INTO ex_templates(name,nr_sets,template_id) VALUES(?,?,?)", ex_name, 1, temp_id)

    else:#Adding set
        data = request.get_json()
        ex_name = data["ex_name"]
        ex_id = db.execute("SELECT id FROM ex_templates WHERE name = ? AND template_id = ?", ex_name, temp_id)

        db.execute("UPDATE ex_templates SET nr_sets = nr_sets + 1 WHERE id = ?", ex_id[0]["id"])

    return apology('no',200)



@app.route("/past_templates", methods = ["GET", "POST"])
@login_required
def past_template():
    active_workout = db.execute("SELECT id FROM workouts WHERE workout_duration = 'workout in progress' AND user_id = ?", session['user_id'])
    if not active_workout:
        active_workout.append({'id':0})

    if request.method == "POST":
        template_id = int(request.form.get("template_id"))

        data = getTemplate(template_id)

        return render_template("past_templates.html", template_name = data["template_name"], ex_templates = data['names'], length_sets = data['nr_sets_list'], nr_sets = data['nr_sets'], active_workout = active_workout[0]['id'])


#For new_template
@app.route("/delete_temp", methods = ["POST","PUT"])
@login_required
def delete_temp():
    temp_id = db.execute("SELECT id FROM templates WHERE created = 'no' AND user_id = ?", session["user_id"])
    #Trying to select the only the, if there is none we don't change anything
    try:
        temp_id = temp_id[0]['id']
    except:
        pass

    if request.method == 'POST':#Deletes exercises or set
        data = request.get_json()

        ex_name = data['ex_name']

        ex_id = db.execute("SELECT id FROM ex_templates WHERE name = ? AND template_id = ?", ex_name, temp_id)
        ex_id = ex_id[0]['id']

        if 'set_nr' not in data:#Deleting exercise
            #Deletes exercise
            db.execute("DELETE FROM ex_templates WHERE id = ?", ex_id)
            #Decreases the id of the exercises after the one deleted
            db.execute("UPDATE ex_templates SET id = id - 1 WHERE id > ?", ex_id)
            #Decreases the autoincrement by one
            db.execute("UPDATE `sqlite_sequence` SET `seq` = (SELECT MAX(id) FROM ex_templates) WHERE `name` = 'ex_templates'")
        else:#Deleting set
            db.execute("UPDATE ex_templates SET nr_sets = nr_sets - 1 WHERE id = ?", ex_id)
    else:
        #Deletes all information about chosen template
        data = request.get_json()

        #Selecting the exercises that will be deleted
        ex = db.execute("SELECT id FROM ex_templates WHERE template_id = ?", data['id'])

        for i in range(len(ex)):
            #Deleting exercise
            db.execute("DELETE FROM ex_templates WHERE id = ?", ex[i]['id'])
            db.execute("UPDATE ex_templates SET id = id - 1 WHERE id > ?", ex[i]['id'])
            db.execute("UPDATE `sqlite_sequence` SET `seq` = (SELECT MAX(id) FROM ex_templates) WHERE `name` = 'ex_templates'")

            #Decreasing ids
            for j in range(i + 1, len(ex)):
                ex[j]['id'] -= 1

        db.execute("DELETE FROM templates WHERE id = ?", data['id'])
    return apology('no',200)



@app.route("/charts", methods = ["GET", "POST", "PUT"])
@login_required
def charts():
    #This is for the food chart
    weight_data = db.execute("SELECT date,weight FROM diet_days WHERE user_id = ?", session["user_id"])
    weight = []
    dates = []

    #Getting the weight and dates lists
    for i in range(len(weight_data)):
        if weight_data[i]["weight"]:
            weight.append(weight_data[i]["weight"])
            #Appending only the dates from the date and time string
            dates.append(weight_data[i]["date"][:weight_data[i]["date"].index(' ')])

    if request.method == "PUT":
        ex_name = request.get_json()

        #Getting a list of all the possible sugestions
        ex_list = db.execute("SELECT name FROM lifts_info WHERE user_id = ? AND name LIKE ?", session['user_id'], '%' + ex_name['ex_name'] + '%')
        ex_list = [ex['name'] for ex in ex_list]

        return json.dumps(ex_list)

    elif request.method == "GET":
        return render_template("charts.html",PR_list = [], workout_startDates = [], weight = weight, dates = dates)
    else:
        ex_name = request.form.get("exercise_name")

        #Getting a list representing the PRS of the exercise for the workouts it was performed in
        #The dates of thos workouts
        #And the max of the PR list
        PR_list, workout_startDates, PR = getExPrs(ex_name)

        ex_name = "The " + ex_name + " chart"

        return render_template("charts.html", PR_list = PR_list, workout_startDates = workout_startDates, ex_name = ex_name, true_rm = PR, weight = weight, dates = dates)



@app.route("/calories",methods = ["GET", "POST", "PUT"])
@login_required
def calories():
    global CHOSEN_DATE
    #verifying if the user has goal or not
    if request.method == "GET":
        diet_goal = db.execute("SELECT diet_goal FROM users WHERE id = ?", session["user_id"])
        #Might need to put everything in that render template
        if not diet_goal[0]["diet_goal"]:
            return render_template("calories.html", get_started = True, calories_goal = 0, calories_burnedAVG = 0, meals_today = [], foods_today = {}, calories_burned = 0, protein_nr = 0, carbs_nr = 0, fats_nr = 0, meals_index = [], protein_goal = 0, carbs_goal = 0, fats_goal = 0)
        else:
            diet_info = db.execute("SELECT calories_burnedAVG, diet_goal FROM users WHERE id = ?", session["user_id"])
            aux = db.execute("SELECT date,weight FROM diet_days WHERE user_id = ?", session["user_id"])

            last_weight = aux[len(aux) - 1]["weight"]

            last_date = datetime.datetime.strptime(aux[len(aux) - 1]["date"],"%Y-%m-%d %H:%M:%S")

            current_date = datetime.datetime.now()

            diff = (current_date - last_date).days

            if diff >= 1:
                #Updating the last day the user logged in with the weight that was last inserted
                if not last_weight or last_weight == "NULL":
                    last_weight = aux[len(aux) - 2]["weight"]
                    db.execute("UPDATE diet_days SET weight = ? WHERE date = ?", last_weight, last_date)


                #Inserting the diet_days that the user missed with the weight that was last inserted
                for i in range(diff - 1):
                    db.execute("INSERT INTO diet_days(date,user_id,weight) VALUES(?,?,?)", last_date + datetime.timedelta(i + 1) , session["user_id"], last_weight)

                #This creates today's diet_day
                db.execute("INSERT INTO diet_days(date,user_id) VALUES(?,?)", last_date + datetime.timedelta(diff) , session["user_id"])
                last_weight = None

            data = getDiet(last_date + datetime.timedelta(diff))

            CHOSEN_DATE = last_date + datetime.timedelta(diff)

            goals_data = db.execute("SELECT * FROM diet_goals WHERE user_id = ?", session["user_id"])

            meals_index = list(range(len(data["meals_today"])))

            return render_template("calories.html", get_started = False, weight = last_weight, calories_goal = goals_data[0]["calories_goal"], calories_burnedAVG = diet_info[0]["calories_burnedAVG"], meals_today = data["meals_today"], foods_today = data["foods_today"], calories_burned  = data["calories_burned"], protein_nr = data["protein_nr"], carbs_nr = data["carbs_nr"], fats_nr = data["fats_nr"], meals_index = meals_index, protein_goal = goals_data[0]["protein_goal"], carbs_goal = goals_data[0]["carbs_goal"], fats_goal = goals_data[0]["fats_goal"])

   #Verifying if the user needs to use calorie calculator
    elif request.method == "POST":
        CHOSEN_DATE = datetime.datetime.now()
        
        gender = float(request.form.get("gender"))

        weight = float(request.form.get("weight"))

        height = float(request.form.get("height"))

        age = float(request.form.get("age"))

        activity_level = float(request.form.get("activity"))

        goal = str(request.form.get("goal"))

        #This is actually the number of calories burned daily on average
        calories_burnedAVG = round(caloriesCalculator(weight, height, age, gender, activity_level), 2)

        if goal == "1":
            goal = "Lose weight(cut)"
        elif goal == "2":
            goal = "Maintain weigth"
        else:
            goal = "Gain weight(bulk)"

        db.execute("UPDATE users SET diet_goal = ?, calories_burnedAVG = ? WHERE id = ?", goal, calories_burnedAVG, session["user_id"])

        #Inserts into table user_diet the goals about calories,protein,carbs,fats
        insertDietGoals(goal, calories_burnedAVG)

        goals_data = db.execute("SELECT * FROM diet_goals WHERE user_id = ?", session["user_id"])

        db.execute("INSERT INTO diet_days(date,user_id,weight) VALUES(?,?,?)", datetime.datetime.now(), session["user_id"], weight)

        return render_template("calories.html", get_started = False, weight = weight, calories_goal = goals_data[0]["calories_goal"], calories_burnedAVG = calories_burnedAVG, goal = goal, meals_today = [], foods_today = {}, calories_burned = 0, protein_nr = 0, carbs_nr = 0, fats_nr = 0, meals_index = [], protein_goal = goals_data[0]["protein_goal"], carbs_goal = goals_data[0]["carbs_goal"], fats_goal = goals_data[0]["fats_goal"])
    else:
        #Getting the meal name using get_josn(from js)
        data = request.get_json()
        keys = list(data.keys())

        #this represents the id of the day that contains the meal
        diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], CHOSEN_DATE)

        #This means we got here through addWeight from calories.html
        if "weight" in keys:
            weight = data["weight"]
            db.execute("UPDATE diet_days SET weight = ? WHERE id = ?", weight, diet_id[0]["id"])
            return render_template("calories.html", get_started = False, weight = weight, calories_goal = 0, calories_burnedAVG = 0, meals_today = [], foods_today = {}, calories_burned = 0, protein_nr = 0, carbs_nr = 0, fats_nr = 0, meals_index = [], protein_goal = 0, carbs_goal = 0, fats_goal = 0)

        #This represents all the ids that have been selected only to use the last one
        diet_days = db.execute("SELECT id FROM diet_days WHERE user_id = ?", session["user_id"])
        #This represents the id of the meal that was selected by the user
        meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", data["meal_name"], diet_id[0]["id"])

        meals_today = db.execute("SELECT name FROM meals WHERE diet_days_id = ?", diet_days[len(diet_days) - 1]["id"])

        for i in range(len(meals_today)):
            if meals_today[i]["name"] == data["meal_name"]:
                return apology("Can't have the same meal more than one time in a diet day")

        #With this we insert the selected meal into the database for the current date
        db.execute("INSERT INTO meals(name, diet_days_id) VALUES(?, ?)", data["meal_name"], diet_days[len(diet_days) - 1]["id"])
        #This is the id of the meal that just got added
        new_meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", data["meal_name"], diet_days[len(diet_days) - 1]["id"])

        #This represents the food from the selected meal
        food = db.execute("SELECT * FROM food WHERE meal_id = ?", meal_id[0]["id"])

        #With this we insert the food info,one by one, into the database and we correlate it to the new meal
        for i in range(len(food)):
            db.execute("INSERT INTO food(name,calories_nr,protein_nr,carbs_nr,fats_nr,meal_id,g) VALUES(?,?,?,?,?,?)", food[i]["name"], food[i]["calories_nr"], food[i]["protein_nr"], food[i]["carbs_nr"], food[i]["fats_nr"],  new_meal_id[0]["id"])
        return render_template("calories.html", get_started = False, calories_goal = 0, calories_burnedAVG = 0, meals_today = [], foods_today = {}, calories_burned = 0, protein_nr = 0, carbs_nr = 0, fats_nr = 0, meals_index = [], protein_goal = 0, carbs_goal = 0, fats_goal = 0)



@app.route("/add_meal", methods = ["GET", "POST"])
@login_required
def add_meal():
    global CHOSEN_MEAL
    diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ?", session["user_id"])
    #This method exists only for when the user wants to continue a meal
    if request.method == "POST":
        meal_names = db.execute("SELECT name FROM meals WHERE diet_days_id = ?", diet_id[len(diet_id) - 1]["id"])

        meal_name = ((request.form.get("meal_name")).lower()).strip()

        for i in range(len(meal_names)):
            if meal_name == meal_names[i]["name"]:
                return apology("Can't have two meals with the same name in the same day")

        db.execute("INSERT INTO meals(name,diet_days_id) VALUES(?,?)", meal_name, diet_id[len(diet_id) - 1]["id"])

        CHOSEN_MEAL = meal_name
        return render_template("edit_meal.html", meal_name = meal_name,foods = [])


@app.route("/remove_meal_food", methods = ["POST", "PUT"])
@login_required
def remove_meal_food():
    #Removing a meal
    global CHOSEN_DATE
    if request.method == "POST":
        data = request.get_json()

        diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], CHOSEN_DATE)

        meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", data["meal_name"], diet_id[0]["id"])

        db.execute("DELETE FROM food WHERE meal_id = ?", meal_id[0]["id"])

        db.execute("DELETE FROM meals WHERE id = ?", meal_id[0]["id"])

        return render_template("calories.html", get_started = False, calories_goal = 0, goal = "", meals_today = [], foods_today = {}, calories_burned = 0, protein_nr = 0, carbs_nr = 0, fats_nr = 0, meals_index = [])
    #Removing food
    else:
        data = request.get_json()

        diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], CHOSEN_DATE)

        meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", data["meal_name"], diet_id[0]["id"])

        db.execute("DELETE FROM food WHERE name = ? AND meal_id = ?", data["food_name"], meal_id[0]["id"])

        return render_template("calories.html", get_started = False, calories_goal = 0, goal = "", meals_today = [], foods_today = {}, calories_burned = 0, protein_nr = 0, carbs_nr = 0, fats_nr = 0, meals_index = [])




@app.route("/add_food", methods = ["GET", "POST", "PUT"])
@login_required
def add_food():
    global CHOSEN_MEAL,CHOSEN_DATE

    #Getting the id of today's diet
    diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], CHOSEN_DATE)

    #Getting the names of the meals present in today's diet
    #meal_names = db.execute("SELECT name FROM meals WHERE diet_days_id = ?", diet_id[0]["id"])

    if request.method == "PUT":
        data = request.get_json()

        data["grams"] = float(data["grams"])
        data["food_name"] = (data["food_name"].lower()).strip()

        keys = data.keys()
        #Got here from add_food.html
        if "meal_name" in keys:
            data["calories_nr"] = float(data["calories_nr"])
            data["protein_nr"] = float(data["protein_nr"])
            data["carbs_nr"] = float(data["carbs_nr"])
            data["fats_nr"] = float(data["fats_nr"])

            CHOSEN_MEAL = data["meal_name"]
            meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", CHOSEN_MEAL, diet_id[0]["id"])

            #per grams inputed
            db.execute("INSERT INTO food(name,calories_nr,protein_nr,carbs_nr,fats_nr,g,meal_id) VALUES(?,?,?,?,?,?,?)", data["food_name"], data["grams"] / 100 * data["calories_nr"], data["grams"] / 100 * data["protein_nr"], data["grams"] / 100 * data["carbs_nr"], data["grams"] / 100 * data["fats_nr"], data["grams"], meal_id[0]["id"])

            #Adding to the common database(per 100g)
            db.execute("INSERT INTO food_info(name,calories_nr,protein_nr,carbs_nr,fats_nr) VALUES(?,?,?,?,?)", data["food_name"], data["calories_nr"], data["protein_nr"], data["carbs_nr"], data["fats_nr"])
        else:
            #Got here from search_food.html
            meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", CHOSEN_MEAL, diet_id[0]["id"])
            insertSearchedFood(data["food_name"], meal_id[0]["id"], data["grams"])

        return render_template("edit_meal.html", meal_name = CHOSEN_MEAL, foods = [])

    else:
        #This happens only with the method POST
        meal_name = request.form.get("meal_name")

        #The global variable is used to know which meal is active/chosen by the user
        #Useful for when we get here via GET

        if meal_name != None:
            CHOSEN_MEAL = meal_name
        else:
            #This means we are here from food_info,add_food btn
            foods = getFoodFromMeal(CHOSEN_MEAL, CHOSEN_DATE)

            food_name = request.form.get("food_name")
            grams = request.form.get("grams")

            if food_name:
                food_name = food_name.lower()

            #This means that the food is already in the meal(This is verified if the user reloads after adding food)
            if food_name in foods:
                return render_template("edit_meal.html", meal_name = CHOSEN_MEAL, foods = foods)

            #This means we got here via POST but from food_info
            if food_name != None:
                meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", CHOSEN_MEAL, diet_id[0]["id"])

                insertSearchedFood(food_name, meal_id[0]["id"], grams)

        #Storing all the names of the foods present in this meal
        foods = getFoodFromMeal(CHOSEN_MEAL, CHOSEN_DATE)

        return render_template("edit_meal.html", meal_name = CHOSEN_MEAL, foods = foods)




@app.route("/search_food", methods = ["GET", "POST"])
@login_required
def search_food():
    global CHOSEN_MEAL, CHOSEN_DATE, CHOSEN_FOOD
    foods_today = getFoodFromMeal(CHOSEN_MEAL, CHOSEN_DATE)

    if request.method == "POST":

        food_name = ((request.form.get("food_name")).lower()).strip()
        if food_name != "":
           food_database = db.execute("SELECT name FROM food_info WHERE name LIKE ?", '%' + food_name + '%')

        foods = food_lookup(food_name)
        found_same = 'n'
        food_names = []

        if foods:
            for i in range(len(foods)):
                if food_name == foods[i]["name"]:
                    found_same = 'y'
                food_names.append(foods[i]["name"].lower())

        #This var was created to see if the food is actually in the database beacuse food_database contains food
        #that is like the input but not necessary the same
        for i in range(len(food_database)):
            if food_name == food_database[i]["name"]:
                found_same = 'y'
            food_names.append(food_database[i]["name"])

        if len(food_names):
            if found_same == 'n':
                CHOSEN_FOOD = food_name
            return render_template("search_food.html", food_names = food_names, foods = foods_today, meal_name = CHOSEN_MEAL, found_same = found_same, food_name = food_name)
        else:
            return render_template("add_food.html", food_name = food_name, foods = foods_today, meal_name = CHOSEN_MEAL)
    else:
        #When create food btn is presed
        return render_template("add_food.html", meal_name = CHOSEN_MEAL, foods = foods_today, food_name = CHOSEN_FOOD)




@app.route("/food_info", methods = ["GET", "POST"])
@login_required
def food_info():
    global CHOSEN_DATE,CHOSEN_MEAL,CHOSEN_FOOD

    if request.method == "POST":
        food_name = request.form.get("food_name")
        meal_name = request.form.get("meal_name")

        if food_name:
            CHOSEN_FOOD = food_name

        if meal_name:
            CHOSEN_MEAL = meal_name

        diet_id = db.execute("SELECT id FROM diet_days WHERE user_id = ? AND date = ?", session["user_id"], CHOSEN_DATE)
        meal_id = db.execute("SELECT id FROM meals WHERE name = ? AND diet_days_id = ?", CHOSEN_MEAL, diet_id[0]["id"])

        food = food_lookup(CHOSEN_FOOD)
        #Verif if food was searched using lookup,if that is not the case we select it from database
        if food == None:
            food = db.execute("SELECT * FROM food_info WHERE name = ?", CHOSEN_FOOD)

        #Get all the foods from active meal and if this food is not present that means it's searched
        foods_today = db.execute("SELECT * FROM food WHERE meal_id = ?", meal_id[0]["id"])

        for i in range(len(foods_today)):
            if CHOSEN_FOOD == foods_today[i]["name"]:
                foods_today[i]["calories_nr"] = round(foods_today[i]["calories_nr"], 2)
                return render_template("food_info.html", food = foods_today[i], searched = "n")

        food[0]["calories_nr"] = round(food[0]["calories_nr"], 2)
        return render_template("food_info.html", food = food[0], searched = "y")


@app.route("/journal", methods = ["GET", "POST"])
@login_required
def journal():
    diet_days = db.execute("SELECT * FROM diet_days WHERE user_id = ?",session["user_id"])
    diet_goals = db.execute("SELECT calories_goal FROM diet_goals WHERE user_id = ?", session["user_id"])

    goals_met = []

    index_list = list(range(len(diet_days)))
    index_list = list(reversed(index_list))

    for i in range(len(diet_days)):
        #Getting the poziton of " " in the date in order to eliminate the time

        diet_data = getDiet(diet_days[i]["date"])

        #Replacing everything after the " " with empty string


        if diet_data["calories_burned"] < diet_goals[0]["calories_goal"]:
            goals_met.append(False)
        else:
            goals_met.append(True)

    return render_template("journal.html", goals_met = goals_met, diet_days = diet_days, index_list = index_list)



@app.route("/see_diet", methods = ["GET", "POST"])
@login_required
def see_diet():
    global CHOSEN_DATE

    if request.method == "POST":
        date = request.form.get("diet_date")
        CHOSEN_DATE = date

        diet_data = getDiet(CHOSEN_DATE)
        diet_goals = db.execute("SELECT * FROM diet_goals WHERE user_id = ?", session["user_id"])

        return render_template("see_diet.html", diet_data = diet_data, diet_goals = diet_goals)




@app.route("/workouts", methods = ["GET", "POST", "PUT"])
@login_required
def workouts():
    global START_TIME,SECONDS_PASSED
    #Getting data about user's workouts
    data = info('workout')

    workouts = data['element']
    if workouts:
        workout_id = workouts[0]['id']

    #Selecting the exercises from database
    database_ex = getDatabaseExercises()

    if request.method == "POST":
        #creates a new workout
        if workouts and workouts[0]["workout_duration"] == "workout in progress":
            delete_workout(workout_id)
            workout_id -= 1
            #Resets timer
            SECONDS_PASSED = -1
            START_TIME = ""

        #Getting date for the workout
        workout_start_date = datetime.date.today()
        #Getting name of workout
        workout_name = (request.form.get("workout_name")).strip()

        #Getting start time of workout
        now = datetime.datetime.now()

        START_TIME = now.strftime("%H:%M:%S")
        START_TIME = datetime.datetime.strptime(START_TIME, "%H:%M:%S")

        db.execute("INSERT INTO workouts(name,start_date,workout_duration,user_id,time_passed) VALUES(?,?,?,?,?)", workout_name, workout_start_date, "workout in progress", session["user_id"], 0)
        return render_template("new_workout.html",NEW_EXERCISES_WEIGHT = {}, workout_name = workout_name, NEW_EXERCISES_NAMES = [], NEW_EXERCISES_REPS = {}, NEW_EXERCISES_SETS = {},  NEW_EXERCISES_LENGTH =  {}, sec = 0, database_ex = database_ex, saved = {})

    elif request.method == "GET":
        #display past workouts
        return render_template("workouts.html",workouts = workouts, length = data['length'], active = data['active'])

    else:#method PUT for creating workout using templates

        #Terminates the active workout
        if workouts and workouts[0]["workout_duration"] == "workout in progress":
            delete_workout(workout_id)
            workout_id -= 1
            #Resets timer
            SECONDS_PASSED = -1
            START_TIME = ""

        #Starts a new workout with the template as a blueprint
        data = request.get_json()
        workout_start_date = datetime.date.today()

        db.execute("INSERT INTO workouts(name,start_date,workout_duration,user_id,time_passed) VALUES(?,?,?,?,?)", data["workout_name"], workout_start_date, "workout in progress", session["user_id"], 0)

        #Getting the exercises for this workout
        workout_exercises = data["workout_exercises"]
        #Geeting nr of sets for each exercise
        nr_sets = data['nr_sets']

        ex_index = list(range(len(workout_exercises)))

        #The '+1' happens becauses workouts doesn't count the inserted workout
        if workouts:
            workout_id += 1
        else:
            workout_id = 1

        #Inserting the first exercise separately to get access to the id more easily
        if ex_index != []:

            db.execute("INSERT INTO exercises(name,nr_sets,workout_id,user_id) VALUES(?,?,?,?)", workout_exercises[0], nr_sets[workout_exercises[0]], workout_id, session['user_id'])
            exercise_id = db.execute("SELECT id FROM exercises WHERE name = ? AND workout_id = ?", workout_exercises[0], workout_id)
            exercise_id = exercise_id[0]["id"]

            sets_index = range(nr_sets[workout_exercises[0]])

            #Inserting sets of first exercise
            for j in sets_index:
                db.execute("INSERT INTO sets(weight,reps,set_number, saved, exercise_id) VALUES(?,?,?,?,?)", 0, 0, j, 'n', exercise_id)
            ex_index.pop(0)
            for i in ex_index:
                db.execute("INSERT INTO exercises(name,nr_sets,workout_id,user_id) VALUES(?,?,?,?)", workout_exercises[i], nr_sets[workout_exercises[i]], workout_id, session['user_id'])
                #The id gets autoincremented so we can just do this to get the id of the exercise
                exercise_id = exercise_id + 1
                sets_index = range(nr_sets[workout_exercises[i]])

                for j in sets_index:
                    db.execute("INSERT INTO sets(weight,reps,set_number, saved, exercise_id) VALUES(?,?,?,?,?)", 0, 0, j, 'n', exercise_id)
        return apology("no",200)



@app.route("/new_workout", methods = ["GET"])
@login_required
def new_workout():
    global SECONDS_PASSED

    auxW_id_name_dur = db.execute("SELECT id,name,time_passed FROM workouts WHERE user_id = ? AND workout_duration = 'workout in progress'", session["user_id"])
    #geting workout id and name if there is an ongoing workout
    if auxW_id_name_dur:
        workout_id = auxW_id_name_dur[0]["id"]
        workout_name = auxW_id_name_dur[0]["name"]
    else:
        #No ongoing workout,redirecting to workouts
        data = info('workout')
        return render_template("workouts.html",workouts = data["element"], length = data["length"], active = data["active"])

    #starting timer
    start_end()
    sec = get_seconds() #nr of sec passed since the workout started

    if SECONDS_PASSED == -1:
            SECONDS_PASSED = auxW_id_name_dur[len(auxW_id_name_dur) - 1]["time_passed"]
    sec = SECONDS_PASSED + sec

    #The exercises that the user created will be displayed as search options
    database_ex = getDatabaseExercises()

    if not database_ex:
        database_ex = []
    #Getting data about the workout and presenting it to the user
    try:
        workout_info = getWorkoutInformation(workout_id)
    except IndexError:
        return render_template("new_workout.html", NEW_EXERCISES_WEIGHT = {}, workout_name = workout_name, sec = sec, NEW_EXERCISES_NAMES = [], NEW_EXERCISES_REPS = {}, NEW_EXERCISES_SETS = {},  NEW_EXERCISES_LENGTH =  {}, database_ex = database_ex, saved = {})


    ex_names = workout_info["ex_names"]

    weight = workout_info["weight"]
    reps = workout_info["reps"]

    sets_list = workout_info["sets_list"]
    nr_sets = workout_info["nr_sets"]

    saved = workout_info['saved']

    return render_template("new_workout.html", NEW_EXERCISES_WEIGHT = weight, workout_name = workout_name, sec = sec, NEW_EXERCISES_NAMES = ex_names, NEW_EXERCISES_REPS = reps, NEW_EXERCISES_SETS = sets_list,  NEW_EXERCISES_LENGTH =  nr_sets, database_ex = database_ex, saved = saved)


@app.route("/add_workout", methods = ["POST", "PUT"])
@login_required
def add_workout():
    #Getting id of current workout
    workout_id = db.execute("SELECT id FROM workouts WHERE workout_duration = 'workout in progress' AND user_id = ?", session['user_id'])
    workout_id = workout_id[0]['id']

    data = request.get_json()

    ex_name = data["ex_name"]

    #Exercise gets added
    if request.method == "POST":

        #Exercise is created,adding to db
        if 'muscle' in data:
            #In case the user inserted as an option a muscle not in the predefined list
            if data['muscle'] not in MUSCLE_LIST:
                return apology('',200)
            db.execute("INSERT INTO exercises_info(name,muscle,instructions,user_id) VALUES(?,?,?,?)", ex_name, data["muscle"], data["instructions"], session['user_id'])

        db.execute("INSERT INTO exercises(name,nr_sets,workout_id,user_id) VALUES(?,?,?,?)", ex_name, 1, workout_id, session['user_id'])

        #Getting the id of the exercise last inserted
        ex_id = db.execute('SELECT id FROM exercises WHERE workout_id = ? AND name = ?', workout_id, ex_name)
        db.execute("INSERT INTO sets(set_number,weight,reps,saved,exercise_id) VALUES(?,?,?,?,?)", 0, 0, 0, 'n', ex_id[0]['id'])
    else:
        ex_id = db.execute('SELECT id FROM exercises WHERE workout_id = ? AND name = ?', workout_id, ex_name)
        db.execute("INSERT INTO sets(set_number,weight,reps, saved, exercise_id) VALUES(?,?,?,?,?)", data['set_nr'], 0, 0, 'n', ex_id[0]['id'])

        db.execute("UPDATE exercises SET nr_sets = nr_sets + 1 WHERE id = ?", ex_id[0]['id'])

    return apology('no',200)




@app.route("/stop_workout", methods = ["GET"])
@login_required
def stop_workout():
     auxW_id_name_dur = db.execute("SELECT id,name,time_passed,start_date FROM workouts WHERE user_id = ? AND workout_duration = 'workout in progress'", session["user_id"])

     #Getting time and seconds passed
     global SECONDS_PASSED
     start_end()
     sec = get_seconds() + SECONDS_PASSED
     #reseting timer
     SECONDS_PASSED = -1

     time = time_passed(sec)

     db.execute("UPDATE workouts SET workout_duration = ?, time_passed = ? WHERE id = ?", time, sec , auxW_id_name_dur[0]["id"])

     #time <=> workout duration
     print(f"workout_duration", time)

     global START_TIME,END_TIME
     START_TIME = ""
     END_TIME = ""

     workout_info = getWorkoutInformation(auxW_id_name_dur[0]["id"])

     ex_names = workout_info["ex_names"]
     weight = workout_info["weight"]
     reps = workout_info["reps"]
     sets_list = workout_info["sets_list"]
     nr_sets = workout_info["nr_sets"]

     #saving info about prs set for each exercise performed in this workout
     insertWorkoutPrs(ex_names, weight, reps, auxW_id_name_dur[0]["start_date"])

     return render_template("workout_completed.html", NEW_EXERCISES_WEIGHT = weight, workout_name = auxW_id_name_dur[0]["name"], time = time, NEW_EXERCISES_NAMES = ex_names, NEW_EXERCISES_REPS = reps, NEW_EXERCISES_SETS = sets_list,  NEW_EXERCISES_LENGTH =  nr_sets)



@app.route("/past_workouts", methods = ["POST"])
@login_required
def past_workouts():

    if request.method == "POST":
        workout_id = request.form.get("workout_id")

        workout = db.execute("SELECT * FROM workouts WHERE id = ?", workout_id)

        active_workout = db.execute("SELECT id FROM workouts WHERE workout_duration = 'workout in progress'")

        workout_info = getWorkoutInformation(workout_id)

        ex_names = workout_info["ex_names"]

        weight = workout_info["weight"]
        reps = workout_info["reps"]

        sets_list = workout_info["sets_list"]
        nr_sets = workout_info['nr_sets']

        return render_template("past_workouts.html", ex_names = ex_names, weight = weight, reps = reps, sets_list = sets_list, workout_name = workout[0]["name"], workout_duration = workout[0]["workout_duration"], workout_date = workout[0]["start_date"], active_workout = active_workout, nr_sets = nr_sets)


#For new_workout and workouts
@app.route("/delete", methods = ["POST"])
@login_required
def delete():

    #Getting the id of the active workout
    workout_id = db.execute("SELECT id FROM workouts WHERE workout_duration = 'workout in progress' AND user_id = ?", session['user_id'])
    workout_id = workout_id[0]['id']

    if request.method == "POST":
        data = request.get_json()

        #This means we delete something from active workout
        if data != {}:
            #Getting id of exercise from which we delete
            ex_id = db.execute("SELECT id FROM exercises WHERE name = ? AND workout_id = ?", data['ex_name'], workout_id)
            ex_id = ex_id[0]['id']

            #Deleting set
            if 'set_nr' in data:
                set_id = db.execute("SELECT id FROM sets WHERE exercise_id = ? AND set_number = ?", ex_id, data['set_nr'])

                #Updating the number of sets
                db.execute('UPDATE exercises SET nr_sets = nr_sets - 1 WHERE id = ?', ex_id)

                #Decreasing the set number of the sets performed after chosen set
                db.execute("UPDATE sets SET set_number = set_number - 1 WHERE id > ? AND exercise_id = ?", set_id[0]['id'], ex_id)

                delete_set(set_id[0]['id'])

            else:#Deleting exercise
                delete_exercise(ex_id)

        else:#Deleting workout
            delete_workout(workout_id)

    return apology('no', 200)


@app.route("/save_set", methods = ["POST"])
@login_required
def save_set():
    data = request.get_json()
    ex_name = data["ex_name"]
    set_nr = data["set"]

    #See if this works
    set_id = db.execute("SELECT id FROM sets WHERE set_number = ? AND exercise_id = (SELECT id FROM exercises WHERE name = ? AND workout_id = (SELECT id FROM workouts WHERE user_id = ? AND workout_duration = 'workout in progress'))", set_nr, ex_name, session['user_id'])

    print(set_id)
    #This means exercise is not saved(checkBox is not checked)
    if 'saved' not in data:
        print(data)
        db.execute("UPDATE sets SET saved = ? WHERE id = ?", 'n', set_id[0]['id'])
    else:#Saving changes made to the weight and reps inserted
        db.execute("UPDATE sets SET weight = ?,reps = ?,saved = ? WHERE id = ?", data['weight'], data['reps'], 'y', set_id[0]['id'])

    return apology('no', 200)


@app.route("/exercise_info", methods = ["POST", "PUT"])
@login_required
def exercise_info():
    if request.method == "POST":
        data = {}

        #Getting data from form
        data["name"] = request.form.get("ex_name")
        data["muscle"] = request.form.get("ex_muscle")

        data["instructions"] = request.form.get("ex_instructions")

        status = request.form.get("status")
        #nT-not in template;nW-not in workout
        if status == 'nT' or status == 'nW':#User wants to see info about exercise searched
            return render_template("exercise_info.html", data = data, status = status)

        else:#This means the user wants to see info about exercise that s already in workout
            #exercise in workout, not searched
            if data['muscle'] == '':

                ex_database = getDatabaseExercises()

                for exercise in ex_database:
                    if exercise["name"] == data["name"]:
                        data = exercise
                        break

                if data['muscle'] == '':
                    data = exercise_lookup(data["name"])

            #If the exercise contains the muscle that means it's searched and we don't need to look
            #into the databases

            return render_template("exercise_info.html",data = data, status = status)

    else:#Inserting the exercise into the database
        aux_work = db.execute("SELECT id,name FROM workouts WHERE user_id = ? AND workout_duration = 'workout in progress'", session["user_id"])

        database_ex = getDatabaseExercises()
        data = request.get_json()

        if data['status'] == 'nW':
            aux_work = db.execute("SELECT id,name FROM workouts WHERE user_id = ? AND workout_duration = 'workout in progress'", session["user_id"])

            db.execute("INSERT INTO exercises(name,nr_sets,workout_id,user_id) VALUES(?,?,?,?)", data["name"], 1, aux_work[0]["id"], session['user_id'])

            aux_ex = db.execute("SELECT id FROM exercises WHERE name = ? AND workout_id = ?", data["name"], aux_work[0]["id"])

            db.execute("INSERT INTO sets(weight, reps, set_number, saved, exercise_id) VALUES(?,?,?,?,?)", 0, 0, 0, 'n', aux_ex[0]["id"])

            data = getWorkoutInformation(aux_work[0]["id"])

            ex_names = data["ex_names"]

            weight = data["weight"]
            reps = data["reps"]

            sets_list = data["sets_list"]

            nr_sets = data["nr_sets"]

            saved = data['saved']

            start_end()
            sec = get_seconds()

            return render_template("new_workout.html", NEW_EXERCISES_WEIGHT = weight, workout_name = aux_work[0]["name"], sec = sec, NEW_EXERCISES_NAMES = ex_names, NEW_EXERCISES_REPS = reps, NEW_EXERCISES_SETS = sets_list,  NEW_EXERCISES_LENGTH =  nr_sets, database_ex = database_ex, saved = saved)
        else:
            aux_work = db.execute("SELECT id,name FROM templates WHERE user_id = ? AND created = 'no'", session["user_id"])
            db.execute("INSERT INTO ex_templates(name,nr_sets,template_id) VALUES(?,?,?)", data["name"], 1, aux_work[0]["id"])

            data = getTemplate(aux_work[0]['id'])

            return render_template("new_template.html", NEW_EXERCISES_NAMES = data['names'], NEW_EXERCISES_SETS = data['nr_sets_list'], NEW_EXERCISES_LENGTH = data['nr_sets'], template_name = data['template_name'], database_ex = database_ex)


@app.route("/save_time", methods = ['POST'])
@login_required
def save_time():
    workout_info = db.execute("SELECT id,time_passed FROM workouts WHERE user_id = ? AND workout_duration = 'workout in progress'", session['user_id'])
    if not workout_info:
        return apology('',200)

    global SECONDS_PASSED
    if SECONDS_PASSED == -1:
            SECONDS_PASSED = workout_info[0]["time_passed"]
    start_end()

    sec = get_seconds() + SECONDS_PASSED
    db.execute("UPDATE workouts SET time_passed = ? WHERE id = ?", sec, workout_info[0]['id'])
    return apology('',200)

#Here we edit the name of the templates and workouts
@app.route("/edit_name", methods = ['POST'])
@login_required
def edit_name():
    #changed(what gets changed), new(new name), id(of template or workout)
    data = request.get_json()
    if 'id' not in data:
        #If a template with this name already exists we don't let the user rename it
        if data['changed'] == 'templates' and db.execute("SELECT id FROM templates WHERE name = ? AND user_id = ?", data['new'], session['user_id']):
            return apology('', 200)

        #Getting the id of the active workout(last introduced into the db)
        data['id'] = db.execute("SELECT MAX(id) FROM ? WHERE user_id = ?", data['changed'], session['user_id'])
        data['id'] = data['id'][0]['MAX(id)']

    db.execute('UPDATE ? SET name = ? WHERE id  = ?', data['changed'], data['new'], data['id'])
    return apology('', 200)

