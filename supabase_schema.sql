-- SyncSlotNITT PostgreSQL Schema (Supabase Compatible)

-- Drop existing tables to avoid duplicate key conflicts on initial setup
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS leave_requests CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS timetables CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Create Users Table
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ccm', 'teacher', 'student')),
    dept TEXT,
    section TEXT
);

-- 2. Create Timetables Table
CREATE TABLE timetables (
    id SERIAL PRIMARY KEY,
    dept TEXT NOT NULL,
    section TEXT NOT NULL,
    day TEXT NOT NULL,
    slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 5),
    subject TEXT,
    teacher TEXT,
    UNIQUE (dept, section, day, slot)
);

-- 3. Create Attendance Table
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    student_roll TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Present', 'Absent')),
    date DATE NOT NULL,
    UNIQUE (student_roll, subject, date)
);

-- 4. Create Leave Requests Table (OD Applications)
CREATE TABLE leave_requests (
    id SERIAL PRIMARY KEY,
    student_roll TEXT NOT NULL,
    subject TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    date DATE NOT NULL
);

-- 5. Create Notifications Table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert a default Administrator (CCM) for testing
-- The password is 'admin123'
INSERT INTO users (username, password_hash, role, dept, section)
VALUES (
    'ccm_admin', 
    'pbkdf2:sha256:260000$tY9r2H9D$cc84fa5ba2e4dcb23be143f6ffebdf6ee256a021bbd9fc781b2a92618991f866', 
    'ccm', 
    'CSE', 
    'A'
) ON CONFLICT DO NOTHING;