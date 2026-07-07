from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'nitt_secure_secret_key'
DATABASE = 'syncslot.db'

DEPARTMENTS = [
    "Computer Science and Engineering (CSE)", "Electronics and Communication Engineering (ECE)",
    "Electrical and Electronics Engineering (EEE)", "Instrumentation and Control Engineering (ICE)",
    "Mechanical Engineering (Mech)", "Civil Engineering (Civil)",
    "Production Engineering (Prod)", "Chemical Engineering (Chem)", "Metallurgical and Materials Engineering (MME)"
]
SECTIONS = ["A", "B"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIME_SLOTS = [
    "09:00 AM - 10:00 AM", "10:00 AM - 11:00 AM", "11:00 AM - 12:00 PM",
    "12:00 PM - 01:00 PM", "02:00 PM - 03:00 PM", "03:00 PM - 04:00 PM", "04:00 PM - 05:00 PM"
]

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, role TEXT, dept TEXT, section TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, teacher_username TEXT, dept TEXT, section TEXT, subject TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS timetables (
            dept TEXT, section TEXT, day TEXT, slot TEXT, subject TEXT, prof_id TEXT,
            PRIMARY KEY (dept, section, day, slot))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_username TEXT, subject TEXT, dept TEXT, section TEXT, date TEXT, status TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_username TEXT, subject TEXT, dept TEXT, section TEXT, date TEXT, reason TEXT, status TEXT DEFAULT 'Pending')''')
        # Upgrade: Central Relational Notifications Schema Store Registry
        conn.execute('''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

init_db()

# Global Context Processor to seamlessly inject notifications data across views
@app.context_processor
def inject_global_notifications():
    if 'user' in session:
        with get_db() as conn:
            notifs = conn.execute('SELECT * FROM notifications WHERE username=? ORDER BY id DESC LIMIT 5', (session['user'],)).fetchall()
        return dict(global_notifications=notifs)
    return dict(global_notifications=[])

@app.route('/')
def landing():
    if 'user' in session: return redirect(url_for(session['role']))
    return render_template('landing.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ? AND role = ?', (username, role)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            session['role'] = role
            session['dept'] = user['dept']
            session['section'] = user['section']
            return redirect(url_for(role))
        flash(f'Invalid credentials for {role.upper()} portal gateway entry.')
    return render_template(f'{role}_login.html')

@app.route('/register/ccm', methods=['GET', 'POST'])
def register_ccm():
    if request.method == 'POST':
        u = request.form.get('username').strip()
        p = request.form.get('password')
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users VALUES (?, ?, "ccm", NULL, NULL)', (u, generate_password_hash(p)))
                conn.commit()
            flash('CCM Profile committed to database. Please sign in.')
            return redirect(url_for('login', role='ccm'))
        except sqlite3.IntegrityError: flash('Primary Key Violation: Username already exists!')
    return render_template('ccm_register.html')

@app.route('/register/teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        u = request.form.get('username').strip()
        p = request.form.get('password')
        d, s, sub = request.form.get('dept'), request.form.get('section'), request.form.get('subject').strip()
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users VALUES (?, ?, "teacher", ?, ?)', (u, generate_password_hash(p), d, s))
                conn.execute('INSERT INTO assignments (teacher_username, dept, section, subject) VALUES (?, ?, ?, ?)', (u, d, s, sub))
                conn.commit()
            flash('Faculty profile initialized securely.'); return redirect(url_for('login', role='teacher'))
        except sqlite3.IntegrityError: flash('Primary Key Violation: Username already registered!')
    return render_template('teacher_register.html', depts=DEPARTMENTS, sections=SECTIONS)

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        u = request.form.get('username').strip()
        p = request.form.get('password')
        d, s = request.form.get('dept'), request.form.get('section')
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users VALUES (?, ?, "student", ?, ?)', (u, generate_password_hash(p), d, s))
                conn.commit()
            flash('Student entry initialized.'); return redirect(url_for('login', role='student'))
        except sqlite3.IntegrityError: flash('Primary Key Violation: Roll Number already exists!')
    return render_template('student_register.html', depts=DEPARTMENTS, sections=SECTIONS)

@app.route('/ccm', methods=['GET', 'POST'])
def ccm():
    if session.get('role') != 'ccm': return redirect(url_for('landing'))
    s_dept = request.args.get('dept', DEPARTMENTS[0])
    s_sect = request.args.get('section', SECTIONS[0])
    
    if request.method == 'POST':
        collisions = []
        with get_db() as conn:
            conn.execute('DELETE FROM timetables WHERE dept = ? AND section = ?', (s_dept, s_sect))
            for day in DAYS:
                for slot in TIME_SLOTS:
                    sub = request.form.get(f"sub_{day}_{slot}", "").strip()
                    prof = request.form.get(f"prof_{day}_{slot}", "").strip()
                    if prof:
                        conflict = conn.execute('''SELECT dept, section FROM timetables 
                            WHERE day=? AND slot=? AND prof_id=? AND (dept!=? OR section!=?)''', 
                            (day, slot, prof, s_dept, s_sect)).fetchone()
                        if conflict:
                            collisions.append(f"Professor '{prof}' has a scheduling collision on {day} during {slot} with {conflict['dept']} Sec {conflict['section']}!")
                        
                        # Automated Trigger Notification targeting professors during timetable updates
                        conn.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', 
                                     (prof, f"Your timetable grid allocation has been updated for {s_dept} Section {s_sect} on {day}."))
                    
                    conn.execute('INSERT OR REPLACE INTO timetables VALUES (?, ?, ?, ?, ?, ?)', (s_dept, s_sect, day, slot, sub, prof))
            
            # Broadcast update notification to all students in the branch
            stus = conn.execute('SELECT username FROM users WHERE role="student" AND dept=? AND section=?', (s_dept, s_sect)).fetchall()
            for s in stus:
                conn.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', (s['username'], "Your master department timetable layout has been updated by the CCM."))
            conn.commit()
        if collisions:
            for c in collisions: flash(f"Warning: {c}")
        else: flash("Timetable published with zero schedule validation conflicts!")
        return redirect(url_for('ccm', dept=s_dept, section=s_sect))

    current_tt = {d: {s: {"subject": "", "prof_id": ""} for s in TIME_SLOTS} for d in DAYS}
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM timetables WHERE dept = ? AND section = ?', (s_dept, s_sect)).fetchall()
    for r in rows: current_tt[r['day']][r['slot']] = {"subject": r['subject'], "prof_id": r['prof_id']}
    return render_template('ccm.html', depts=DEPARTMENTS, sections=SECTIONS, days=DAYS, slots=TIME_SLOTS, current_tt=current_tt, s_dept=s_dept, s_sect=s_sect)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if session.get('role') != 'teacher': return redirect(url_for('landing'))
    user = session['user']
    
    with get_db() as conn:
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add_assignment':
                conn.execute('INSERT INTO assignments (teacher_username, dept, section, subject) VALUES (?, ?, ?, ?)',
                             (user, request.form.get('dept'), request.form.get('section'), request.form.get('subject').strip()))
                conn.commit(); flash("Bound tracking mapping layout successfully.")
            elif action == 'mark_attendance':
                idx = int(request.form.get('active_idx', 0))
                assigns = conn.execute('SELECT * FROM assignments WHERE teacher_username=?', (user,)).fetchall()
                cur = assigns[idx]
                stus = conn.execute('SELECT username FROM users WHERE role="student" AND dept=? AND section=?', (cur['dept'], cur['section'])).fetchall()
                date_str = request.form.get('date')
                for s in stus:
                    stat = request.form.get(f"status_{s['username']}")
                    conn.execute('INSERT INTO attendance (student_username, subject, dept, section, date, status) VALUES (?,?,?,?,?,?)',
                                 (s['username'], cur['subject'], cur['dept'], cur['section'], date_str, stat))
                    # Live Trigger: Notify students regarding newly registered roll updates
                    conn.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', 
                                 (s['username'], f"Attendance for {cur['subject']} on {date_str} marked as {stat.upper()}."))
                conn.commit(); flash("Attendance logs synchronized perfectly across all records.")
                return redirect(url_for('teacher', idx=idx))
            elif action == 'approve_leave':
                req_id = request.form.get('req_id')
                conn.execute('UPDATE leave_requests SET status="Approved" WHERE id=?', (req_id,))
                conn.execute('INSERT INTO attendance (student_username, subject, dept, section, date, status) VALUES (?,?,?,?,?, "OD")',
                             (request.form.get('stu'), request.form.get('sub'), request.form.get('dept'), request.form.get('sect'), request.form.get('date'),))
                # Live Trigger: Inform student that their OD leave waiver is approved
                conn.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', 
                             (request.form.get('stu'), f"Your OD waiver request for {request.form.get('sub')} on {request.form.get('date')} was APPROVED."))
                conn.commit(); flash("On-Duty parameter granted. Student dashboard updated.")

        assignments = conn.execute('SELECT * FROM assignments WHERE teacher_username = ?', (user,)).fetchall()
        idx = int(request.args.get('idx', 0))
        if not assignments: return render_template('teacher.html', assignments=[], depts=DEPARTMENTS, sections=SECTIONS)
        if idx >= len(assignments): idx = 0
        cur = assignments[idx]
        
        tt_rows = conn.execute('SELECT * FROM timetables WHERE dept=? AND section=? AND LOWER(prof_id)=LOWER(?)', (cur['dept'], cur['section'], user)).fetchall()
        tt = {d: {s: "" for s in TIME_SLOTS} for d in DAYS}
        for r in tt_rows: tt[r['day']][r['slot']] = r['subject']
        
        students = conn.execute('SELECT username FROM users WHERE role="student" AND dept=? AND section=?', (cur['dept'], cur['section'])).fetchall()
        
        att_report = {}
        for s in students:
            p = conn.execute('SELECT COUNT(*) FROM attendance WHERE student_username=? AND subject=? AND status IN ("present", "OD")', (s['username'], cur['subject'])).fetchone()[0]
            t = conn.execute('SELECT COUNT(*) FROM attendance WHERE student_username=? AND subject=?', (s['username'], cur['subject'])).fetchone()[0]
            att_report[s['username']] = {"present": p, "total": t}
            
        pending_leaves = conn.execute('SELECT * FROM leave_requests WHERE dept=? AND section=? AND LOWER(subject)=LOWER(?) AND status="Pending"', (cur['dept'], cur['section'], cur['subject'])).fetchall()
        
    return render_template('teacher.html', assignments=assignments, active_idx=idx, tt=tt, days=DAYS, slots=TIME_SLOTS, students=[s['username'] for s in students], att_data=att_report, depts=DEPARTMENTS, sections=SECTIONS, pending_leaves=pending_leaves)

@app.route('/student', methods=['GET', 'POST'])
def student():
    if session.get('role') != 'student': return redirect(url_for('landing'))
    user = session['user']
    
    with get_db() as conn:
        if request.method == 'POST':
            sub = request.form.get('subject')
            date_val = request.form.get('date')
            conn.execute('INSERT INTO leave_requests (student_username, subject, dept, section, date, reason) VALUES (?,?,?,?,?,?)',
                         (user, sub, session['dept'], session['section'], date_val, request.form.get('reason')))
            
            # Live Trigger: Alert the assigned class professor regarding the newly filed OD request
            prof_row = conn.execute('SELECT prof_id FROM timetables WHERE dept=? AND section=? AND LOWER(subject)=LOWER(?) LIMIT 1', (session['dept'], session['section'], sub)).fetchone()
            if prof_row and prof_row['prof_id']:
                conn.execute('INSERT INTO notifications (username, message) VALUES (?, ?)', 
                             (prof_row['prof_id'], f"Student {user} has submitted a new pending OD waiver request for {sub}."))
            conn.commit(); flash("On-Duty Request filed to course professor.")
            
        tt_rows = conn.execute('SELECT * FROM timetables WHERE dept=? AND section=?', (session['dept'], session['section'])).fetchall()
        tt = {d: {s: "" for s in TIME_SLOTS} for d in DAYS}
        subjects = set()
        for r in tt_rows:
            if r['subject']:
                tt[r['day']][r['slot']] = f"{r['subject']} (Prof: {r['prof_id']})"
                subjects.add(r['subject'])
                
        attendance_report = {}
        for sub in subjects:
            p = conn.execute('SELECT COUNT(*) FROM attendance WHERE student_username=? AND subject=? AND status IN ("present", "OD")', (user, sub)).fetchone()[0]
            t = conn.execute('SELECT COUNT(*) FROM attendance WHERE student_username=? AND subject=?', (user, sub)).fetchone()[0]
            pct = round((p / t * 100), 2) if t > 0 else 100.0
            attendance_report[sub] = {"present": p, "total": t, "percentage": pct}
            
        leaves = conn.execute('SELECT * FROM leave_requests WHERE student_username=?', (user,)).fetchall()
        s_info = {"dept": session['dept'], "section": session['section']}
        
    return render_template('student.html', s_info=s_info, days=DAYS, slots=TIME_SLOTS, tt=tt, attendance=attendance_report, leaves=leaves)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('landing'))

if __name__ == '__main__':
    app.run(debug=True)