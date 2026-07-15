import os
from datetime import timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Cryptographically sign cookie sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cosmic_super_secret_key_99182")
app.permanent_session_lifetime = timedelta(hours=2)

# Pull Supabase Connection URI from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    """Establishes a live connection pool to Supabase Postgres using RealDictCursor."""
    if not DATABASE_URL:
        raise ValueError("Critical Error: DATABASE_URL environment variable is missing on this server!")
    
    # RealDictCursor returns database rows as Python dictionaries: row['field_name']
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

@app.route('/')
def landing():
    return render_template('landing.html')

# ==========================================
# AUTHENTICATION ROUTING SYSTEM
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()
        dept = request.form.get('dept', '').strip() or None
        section = request.form.get('section', '').strip() or None
        
        hashed_pw = generate_password_hash(password)
        
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    # Check for username duplicates
                    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                    if cur.fetchone():
                        flash("Username already exists in the registry!", "error")
                        return redirect(url_for('register'))
                    
                    cur.execute(
                        "INSERT INTO users (username, password_hash, role, dept, section) VALUES (%s, %s, %s, %s, %s)",
                        (username, hashed_pw, role, dept, section)
                    )
                conn.commit()
            flash("Account registered successfully! You can now log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Database registry exception: {str(e)}", "error")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cur.fetchone()
                    
                    if user and check_password_hash(user['password_hash'], password):
                        session.permanent = True
                        session['user'] = user['username']
                        session['role'] = user['role']
                        session['dept'] = user['dept']
                        session['section'] = user['section']
                        
                        if user['role'] == 'ccm':
                            return redirect(url_for('ccm_dashboard'))
                        elif user['role'] == 'teacher':
                            return redirect(url_for('teacher_dashboard'))
                        else:
                            return redirect(url_for('student_dashboard'))
                    else:
                        flash("Invalid credentials. Please verify and try again.", "error")
        except Exception as e:
            flash(f"Login pipeline database error: {str(e)}", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Successfully logged out of the terminal session.", "success")
    return redirect(url_for('login'))

# ==========================================
# CURRICULUM COORDINATOR PORTAL (CCM)
# ==========================================

@app.route('/ccm', methods=['GET', 'POST'])
def ccm_dashboard():
    if 'user' not in session or session['role'] != 'ccm':
        flash("Unauthorized access blocked!", "error")
        return redirect(url_for('login'))
        
    selected_dept = request.args.get('dept', session.get('dept', 'CSE'))
    selected_section = request.args.get('section', session.get('section', 'A'))
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM timetables WHERE dept = %s AND section = %s",
                (selected_dept, selected_section)
            )
            rows = cur.fetchall()
            
    timetable = {}
    for r in rows:
        key = f"{r['day']}_{r['slot']}"
        timetable[key] = r

    return render_template('ccm.html', timetable=timetable, dept=selected_dept, section=selected_section)

@app.route('/ccm/publish', methods=['POST'])
def ccm_publish():
    if 'user' not in session or session['role'] != 'ccm':
        return jsonify({"error": "Unauthorized"}), 403
        
    s_dept = request.form.get('dept')
    s_sect = request.form.get('section')
    
    DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("BEGIN;") # Open atomic transactional boundaries
                
                # Drop previous allocations to rebuild table cleanly
                cur.execute('DELETE FROM timetables WHERE dept = %s AND section = %s', (s_dept, s_sect))
                
                bulk_data = []
                for day in DAYS:
                    for slot in range(1, 6):
                        sub = request.form.get(f"sub_{day}_{slot}", "").strip()
                        prof = request.form.get(f"prof_{day}_{slot}", "").strip()
                        
                        if sub and prof:
                            # Strict conflict engine search
                            cur.execute(
                                "SELECT dept, section FROM timetables WHERE day = %s AND slot = %s AND teacher = %s",
                                (day, slot, prof)
                            )
                            conflict = cur.fetchone()
                            if conflict:
                                conn.rollback() # Terminate block safely
                                return jsonify({
                                    "error": "ConflictDetected",
                                    "message": f"Professor {prof} is already scheduled at {day} (Slot {slot}) for {conflict['dept']}-{conflict['section']}."
                                }), 409
                                
                            bulk_data.append((s_dept, s_sect, day, slot, sub, prof))
                
                if bulk_data:
                    # High-speed upsert operation on PostgreSQL using unique constraints
                    cur.executemany(
                        """INSERT INTO timetables (dept, section, day, slot, subject, teacher)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (dept, section, day, slot) 
                           DO UPDATE SET subject = EXCLUDED.subject, teacher = EXCLUDED.teacher;""",
                        bulk_data
                    )
                
                # Broadcast real-time notifications to the target department students
                cur.execute(
                    "INSERT INTO notifications (username, message) SELECT username, %s FROM users WHERE role='student'",
                    (f"The weekly schedule map for {s_dept}-{s_sect} has been updated.",)
                )
                
                conn.commit()
        return jsonify({"status": "success", "message": "Timetable successfully mapped and published!"})
    except Exception as e:
        return jsonify({"error": "SystemException", "message": str(e)}), 500

# ==========================================
# TEACHER / FACULTY PORTAL
# ==========================================

@app.route('/teacher')
def teacher_dashboard():
    if 'user' not in session or session['role'] != 'teacher':
        flash("Unauthorized access blocked!", "error")
        return redirect(url_for('login'))
        
    teacher_id = session['user']
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Fetch class schedule allocated to this specific professor
            cur.execute("SELECT * FROM timetables WHERE teacher = %s", (teacher_id,))
            schedule = cur.fetchall()
            
            # 2. Pull pending OD/Leave request alerts for active subjects
            cur.execute(
                """SELECT * FROM leave_requests 
                   WHERE subject IN (SELECT DISTINCT subject FROM timetables WHERE teacher = %s) 
                   AND status = 'Pending'""", 
                (teacher_id,)
            )
            leaves = cur.fetchall()
            
    return render_template('teacher.html', schedule=schedule, leaves=leaves)

@app.route('/teacher/mark-attendance', methods=['POST'])
def mark_attendance():
    if 'user' not in session or session['role'] != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
        
    student_roll = request.form['student_roll'].strip()
    subject = request.form['subject'].strip()
    status = request.form['status'].strip()
    date_str = request.form['date'].strip()
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Security boundary checking: confirm teaching assignment ownership
                cur.execute(
                    "SELECT 1 FROM timetables WHERE subject = %s AND teacher = %s",
                    (subject, session['user'])
                )
                if not cur.fetchone():
                    return jsonify({
                        "error": "InvalidAllocation", 
                        "message": "You are not authorized to log attendance metrics for this subject."
                    }), 400
                
                # PostgreSQL standard upsert logic
                cur.execute(
                    """INSERT INTO attendance (student_roll, subject, status, date)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (student_roll, subject, date) 
                       DO UPDATE SET status = EXCLUDED.status;""",
                    (student_roll, subject, status, date_str)
                )
                
                # Write individual notification directly to the student portal
                cur.execute(
                    "INSERT INTO notifications (username, message) VALUES (%s, %s)",
                    (student_roll, f"Attendance logged for {subject} on {date_str}: Status is {status}.")
                )
                
                conn.commit()
        return jsonify({"status": "success", "message": "Attendance record updated successfully."})
    except Exception as e:
        return jsonify({"error": "SystemException", "message": str(e)}), 500

@app.route('/teacher/process-od', methods=['POST'])
def process_od():
    if 'user' not in session or session['role'] != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403
        
    req_id = request.form['request_id']
    decision = request.form['decision']  # Expected: 'Approved' or 'Rejected'
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Query target request data to verify status transitions
                cur.execute("SELECT * FROM leave_requests WHERE id = %s", (req_id,))
                req = cur.fetchone()
                
                if not req:
                    return jsonify({"error": "NotFound"}), 404
                    
                cur.execute("UPDATE leave_requests SET status = %s WHERE id = %s", (decision, req_id))
                
                # If application is Approved, immediately update the corresponding attendance record to 'Present'
                if decision == 'Approved':
                    cur.execute(
                        """INSERT INTO attendance (student_roll, subject, status, date)
                           VALUES (%s, %s, 'Present', %s)
                           ON CONFLICT (student_roll, subject, date) 
                           DO UPDATE SET status = 'Present';""",
                        (req['student_roll'], req['subject'], req['date'])
                    )
                
                cur.execute(
                    "INSERT INTO notifications (username, message) VALUES (%s, %s)",
                    (req['student_roll'], f"Your OD application for {req['subject']} on {req['date']} was {decision}.")
                )
                conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": "SystemException", "message": str(e)}), 500

# ==========================================
# STUDENT PORTAL
# ==========================================

@app.route('/student')
def student_dashboard():
    if 'user' not in session or session['role'] != 'student':
        flash("Unauthorized access blocked!", "error")
        return redirect(url_for('login'))
        
    roll_no = session['user']
    dept = session.get('dept', 'CSE')
    section = session.get('section', 'A')
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Pull active timetable configurations
            cur.execute("SELECT * FROM timetables WHERE dept = %s AND section = %s", (dept, section))
            timetable = cur.fetchall()
            
            # 2. Fetch and calculate attendance stats
            cur.execute(
                """SELECT subject,
                       COUNT(CASE WHEN status = 'Present' THEN 1 END) as attended,
                       COUNT(*) as total
                       FROM attendance WHERE student_roll = %s GROUP BY subject""",
                (roll_no,)
            )
            attendance_rows = cur.fetchall()
            
    return render_template(
        'student.html', 
        student_name=roll_no, 
        roll_no=roll_no, 
        dept=dept, 
        section=section, 
        timetable=timetable, 
        attendance_data=attendance_rows
    )

@app.route('/student/apply-od', methods=['POST'])
def apply_od():
    if 'user' not in session or session['role'] != 'student':
        flash("Unauthorized access blocked!", "error")
        return redirect(url_for('login'))
        
    subject = request.form['subject'].strip()
    date_str = request.form['date'].strip()
    reason = request.form['reason'].strip()
    student_roll = session['user']
    
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO leave_requests (student_roll, subject, reason, date) VALUES (%s, %s, %s, %s)",
                    (student_roll, subject, reason, date_str)
                )
                conn.commit()
        flash("OD application successfully submitted to course instructor.", "success")
    except Exception as e:
        flash(f"Error submitting application to cloud registry: {str(e)}", "error")
        
    return redirect(url_for('student_dashboard'))

# ==========================================
# ASYNC API NOTIFICATION FEED
# ==========================================

@app.route('/api/notifications')
def fetch_notifications():
    if 'user' not in session:
        return jsonify({"notifications": []}), 401
        
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT message, timestamp FROM notifications WHERE username = %s ORDER BY id DESC LIMIT 5",
                    (session['user'],)
                )
                rows = cur.fetchall()
                
                # Ensure datetime objects translate correctly into JSON strings
                for r in rows:
                    if r.get('timestamp'):
                        r['timestamp'] = r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        
                return jsonify({"notifications": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run server on port 10000 (Render default mapping target)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), debug=True)