import sqlite3 as sl

db = sl.connect('survey.db', check_same_thread=False)
cursor = db.cursor()

def get_results():
    cursor.execute("""
        SELECT * FROM participants
        LEFT JOIN answers ON participants.uuid = answers.uuid
    """)
    return cursor.fetchall()

if __name__ == '__main__':
    results = get_results()
    entries = []
    entry = ()
    uuid = ''
    for result in results:
        if result[0] != uuid:
            if entry:
                entries.append(entry)
            entry = result[:-4]
            uuid = result[0]
        entry += result[-1:]
    
    with open('results.csv', 'w') as f:
        f.write('uuid,age,gender,education,employment,income,saving,debt,created_at,1M-200€,6M-200€,1J-200€,5J-200€,10J-200€,1M-3000€,6M-3000€,1J-3000€,5J-3000€,10J-3000€,95%-200€,90%-200€,75%-200€,33%-200€,10%-200€,95%-3000€,90%-3000€,75%-3000€,33%-3000€,10%-3000\n')
        for entry in entries:
            f.write(','.join(map(str, entry)) + '\n')
