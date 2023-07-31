from flask import Flask, render_template, session, request, redirect, send_file
from flask_session import Session
import uuid
import logging
import sqlite3 as sl
import math
from datetime import datetime

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

logging.basicConfig(filename='survey.log', encoding='utf-8', level=logging.DEBUG)

db = sl.connect('survey.db', check_same_thread=False)
cursor = db.cursor()

class SurveyAnswerOption:
    def __init__(self, id: int, value, value_string: str):
        self.id = id
        self.value = value
        self.value_string = value_string
    
    def __str__(self):
        return f'{self.id}: {self.value_string}'

class SurveyAnswerFilter:
    def __init__(self, question_id: int, answer_option_id: int):
        self.question_id = question_id
        self.answer_option_id = answer_option_id
    
    def __str__(self):
        return f'{self.question_id} == {self.answer_option_id}'

class SurveyQuestion:
    def __init__(self, group: int, id: int, depth: int, question: str, answer_options: list[SurveyAnswerOption], filter: SurveyAnswerFilter, meta: int = 0, info: str = "", redirect: str = ""):
        self.group = group
        self.id = id
        self.depth = depth
        self.question = question
        self.answer_options = answer_options
        self.filter = filter
        self.meta = meta
        self.info = info
        self.redirect = redirect
    
    def __str__(self):
        return f'{self.id}: {self.question} [{", ".join([str(answer_option) for answer_option in self.answer_options])}], {self.filter}, {self.meta}'

def get_question_groups() -> list[list]:
    return [
        [100, 200, "1 Monat", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [100, 200, "6 Monaten", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [100, 200, "1 Jahr", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [100, 200, "5 Jahren", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [100, 200, "10 Jahren", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [1500, 3000, "1 Monat", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [1500, 3000, "6 Monaten", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [1500, 3000, "1 Jahr", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [1500, 3000, "5 Jahren", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", ""],
        [1500, 3000, "10 Jahren", "", "Möchten Sie lieber in {0} {1} € zahlen oder {2} € jetzt?", "{1} € jetzt", "{2} € in {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>jetzt zahlen</b> müssen, oder {2} € die Sie <b>in {0} zahlen</b> müssen.", "survey_delay_info"],
        [100, 200, "95 %", "5 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [100, 200, "90 %", "10 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [100, 200, "75 %", "25 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [100, 200, "33 %", "67 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [100, 200, "10 %", "90 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [1500, 3000, "95 %", "5 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [1500, 3000, "90 %", "10 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [1500, 3000, "75 %", "25 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [1500, 3000, "33 %", "67 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
        [1500, 3000, "10 %", "90 %", "Möchten Sie lieber {2} € mit Sicherheit zahlen oder {1} € mit einer Wahrscheinlichkeit von {0}?", "{1} € mit Sicherheit", "{2} € zu {0}", "Entscheiden Sie sich zwischen dem Betrag, den Sie <b>mit Sicherheit zahlen</b> müssen, oder {2} € die Sie <b>mit einer Wahrscheinlichkeit von {0} zahlen</b> müssen (d.h. zu {3} müssen Sie nichts zahlen).", ""],
    ]

def get_questions() -> list[SurveyQuestion]:
    questions: list[SurveyQuestion] = []
    for group, [min, max, change, change_else, string, opt1, opt2, info, redirect] in enumerate(get_question_groups()):
        # Flat binary decision tree
        group_base = len(questions)
        id = group_base
        for depth in range(5):
            for width in range(2**depth):
                parent_id = (id - group_base - 1) // 2 + group_base
                filter = None
                adjust_side = width % 2
                low = min
                high = max
                adjustment = max - min
                if depth > 0:
                    adjustment = math.ceil(questions[parent_id].meta / 2)
                    filter = SurveyAnswerFilter(parent_id, adjust_side)
                    low = int(questions[parent_id].answer_options[0].value)
                    high = int(questions[parent_id].answer_options[1].value)
                    if adjust_side == 0:
                        low += adjustment
                    else:
                        low -= adjustment
                low = round(low)
                question_string = string.format(change, high, low)
                questions.append(SurveyQuestion(
                    group,
                    id,
                    depth,
                    f'{group+1}.{depth+1} {question_string}',
                    [
                        SurveyAnswerOption(0, low, opt1.format(change, low, high)),
                        SurveyAnswerOption(1, high, opt2.format(change, low, high))
                    ],
                    filter,
                    adjustment,
                    info.format(change, low, high, change_else) if depth == 0 else "",
                    redirect if depth == 0 else ""
                ))
                id += 1
    return questions

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/start_survey', methods=['POST', 'GET'])
def start_survey():
    session['uuid'] = uuid.uuid4()
    session['question_id'] = 0
    session['answers'] = {}
    session['delay'] = {}
    session['value'] = {}
    init()

    logging.debug(f'UUID[{session["uuid"]}]: Start survey')

    return redirect('/survey_demographic')

@app.route('/survey_demographic', methods=['POST', 'GET'])
def survey_demographic():
    if 'uuid' not in session or 'question_id' not in session or 'answers' not in session:
        logging.error(f"Missing session data: {session}")
        return redirect('/')

    if request.method == "POST":
        # Store demographic data in session
        logging.debug(f'UUID[{session["uuid"]}]: demographic: {str(request.form)}')
        session['demographic'] = request.form
        return redirect('/survey_delay_info')
    
    return render_template('survey_demographic.html')

@app.route('/survey_delay_info', methods=['POST', 'GET'])
def survey_delay_info():
    if 'uuid' not in session or 'question_id' not in session or 'answers' not in session:
        logging.error(f"Missing session data: {session}")
        return redirect('/')

    if request.method == "POST":
        return redirect('/survey_delay_question')
    
    return render_template('survey_delay_info.html', id=session['question_id'])

@app.route('/survey_delay_question', methods=['GET', 'POST'])
def survey():
    if 'uuid' not in session or 'question_id' not in session or 'answers' not in session or 'demographic' not in session or 'delay' not in session:
        logging.error(f"Missing session data: {session}")
        return redirect('/')
    questions = get_questions()

    if request.method == 'POST':
        if 'question_id' not in request.form or 'question_group' not in request.form or 'answer_option_id' not in request.form or request.form['question_id'].isnumeric() == False or request.form['answer_option_id'].isnumeric() == False or request.form['question_group'].isnumeric() == False:
            logging.error(f'UUID[{session["uuid"]}]: Invalid POST request: {request.form}')
            return redirect(request.url)
        
        # Check if ID is old and discard
        if int(request.form['question_id']) < session['question_id']:
            logging.debug(f'UUID[{session["uuid"]}]: Discarded old question {request.form["question_id"]}')
            return redirect(request.url)
            
        question_group = int(request.form['question_group'])
        question_id = int(request.form['question_id'])
        answer_option_id = int(request.form['answer_option_id'])
        session['answers'][question_id] = answer_option_id
        logging.debug(f'UUID[{session["uuid"]}]: Answered question {question_group}:{question_id} with {answer_option_id}')

        previous_question_id = session['question_id']
        session['question_id'] += 1

        while session['question_id'] < len(questions):
            # If no filter is set, choose next question
            if questions[session['question_id']].filter is None:
                break
            # If filter condition is met, choose next question
            if questions[session['question_id']].filter.question_id in session['answers'] and session['answers'][questions[session['question_id']].filter.question_id] == questions[session['question_id']].filter.answer_option_id:
                break
            # Otherwise, skip question
            session['question_id'] += 1
        
        if question_group not in session['delay']:
            session['delay'][question_group] = {
                'min_immediate': None,
                'max_immediate': None,
                'has_selected_immediate': False,
                'has_selected_delayed': False
            }
        
        if answer_option_id == 1:
            session['delay'][question_group]['has_selected_delayed'] = True
        else:
            session['delay'][question_group]['has_selected_immediate'] = True

            # Update min/max immediate
            if session['delay'][question_group]['min_immediate'] is None or session['delay'][question_group]['min_immediate'] > questions[question_id].answer_options[answer_option_id].value:
                session['delay'][question_group]['min_immediate'] = questions[question_id].answer_options[answer_option_id].value
            if session['delay'][question_group]['max_immediate'] is None or session['delay'][question_group]['max_immediate'] < questions[question_id].answer_options[answer_option_id].value:
                session['delay'][question_group]['max_immediate'] = questions[question_id].answer_options[answer_option_id].value
            
        if (session['question_id'] >= len(questions)) or questions[session['question_id']].group != questions[previous_question_id].group:
            # Calculate subjective value
            if session['delay'][question_group]['has_selected_delayed'] and session['delay'][question_group]['has_selected_immediate']:
                session['value'][question_group] = (session['delay'][question_group]['min_immediate'] + session['delay'][question_group]['max_immediate']) / 2
                logging.debug(f'UUID[{session["uuid"]}]: Calculated subjective value for group {question_group}: {session["value"][question_group]}')
            else:
                session['value'][question_group] = (questions[question_id].answer_options[0].value + questions[question_id].answer_options[1].value) / 2
                logging.debug(f'UUID[{session["uuid"]}]: Calculated subjective value for group {question_group}: {session["value"][question_group]} (only delayed/immediate)')
            pass

        # Redirect end
        if (session['question_id'] >= len(questions)):
            return redirect('/end_survey', code=307)

        # Redirect info
        if questions[session['question_id']].redirect != "":
            return redirect(questions[session['question_id']].redirect)
        
        return redirect('/survey_delay_question')
    
    id = session['question_id'] or 0
    if id >= len(questions):
        return redirect('/end_survey', code=307)
    
    question = questions[id]
    progress = question.group / len(get_question_groups()) * 100 + question.depth
    return render_template('survey_delay_question.html', question=question, progress=progress)

@app.route('/end_survey', methods=['GET', 'POST'])
def end_survey():
    if 'uuid' not in session or 'question_id' not in session or 'answers' not in session or 'demographic' not in session:
        logging.error(f"Missing session data: {session}")
        return redirect('/')
    
    if request.method == 'POST':
        logging.debug(f'UUID[{session["uuid"]}]: End survey')

        # Insert demographic data into database
        insert = """
            INSERT INTO participants(uuid, age, gender, education, employment, income, saving, debt) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        demographic = session['demographic']
        cursor.execute(insert, (str(session['uuid']), demographic.get("age"), demographic.get("gender"), demographic.get("education"), demographic.get("employment"), demographic.get("income"), demographic.get("saving"), demographic.get("debt")))

        # Insert answers into database
        values = session['value']
        question_groups = get_question_groups()
        answers = [(str(session['uuid']), key, question_groups[key][4].format(question_groups[key][2], question_groups[key][0], question_groups[key][1]), values[key]) for key in values.keys()]
        insert = """
            INSERT INTO answers(uuid, question_group_id, question_group_string, value) VALUES (?, ?, ?, ?)
        """
        cursor.executemany(insert, answers)
        db.commit()
        
        return redirect('/end_survey')
    
    return render_template('end_survey.html', results=session['value'])

@app.route('/stats', methods=['GET'])
def stats():
    cursor.execute("SELECT COUNT(*) FROM participants")
    num_participants = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM (SELECT uuid, COUNT(*) FROM answers GROUP BY uuid HAVING COUNT(*) = ?)", (len(get_question_groups()),))
    num_completed = cursor.fetchone()[0]

    cursor.execute("SELECT created_at FROM participants ORDER BY created_at DESC LIMIT 1")
    last_participation = cursor.fetchone()[0]

    cursor.execute("SELECT DATETIME('now')")
    time_now = cursor.fetchone()[0]
    last_participation_hours_ago = round((datetime.strptime(time_now, '%Y-%m-%d %H:%M:%S') - datetime.strptime(last_participation, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)

    cursor.execute("SELECT COUNT(*) FROM participants WHERE created_at >= DATE('now')")
    num_completed_today = cursor.fetchone()[0]

    cursor.execute("SELECT created_at FROM participants WHERE uuid IN (SELECT uuid FROM (SELECT uuid, COUNT(*) FROM answers GROUP BY uuid HAVING COUNT(*) = ?))", (len(get_question_groups()),))
    completed_timestamps = cursor.fetchall()

    stats = {
        'num_participants': num_participants,
        'num_completed': num_completed,
        'last_participation': last_participation,
        'last_participation_hours_ago': last_participation_hours_ago,
        'num_completed_today': num_completed_today,
        'completed_timestamps': completed_timestamps
    }

    return render_template('stats.html', stats=stats)

@app.route('/credits', methods=['GET'])
def credits():
    return render_template('credits.html')

def init():
    # Create database
    cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS participants (
            uuid VARCHAR(36) PRIMARY KEY,
            age INTEGER NOT NULL,
            gender INTEGER NOT NULL,
            education INTEGER NOT NULL,
            employment INTEGER NOT NULL,
            income INTEGER NOT NULL,
            saving INTEGER NOT NULL,
            debt INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute(
    """
        CREATE TABLE IF NOT EXISTS answers (
            uuid VARCHAR(36) NOT NULL,
            question_group_id INTEGER NOT NULL,
            question_group_string VARCHAR(255) NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY(uuid) REFERENCES participants(uuid)
        );
    """)
    db.commit()
    pass

if __name__ == '__main__':
    init()
    app.run(host='0.0.0.0', port=80, debug=True)