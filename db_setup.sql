-- First drop the database if it exists
DROP DATABASE IF EXISTS attendance_system;

-- Create the database
CREATE DATABASE attendance_system;

-- Use the database
USE attendance_system;

-- Create students table with proper foreign key constraints
CREATE TABLE students (
    roll_number VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL -- Added NOT NULL for name
) ENGINE=InnoDB;

-- Create attendance table with proper foreign key constraints
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20),
    date_time DATETIME NOT NULL, -- Added NOT NULL for timestamp
    FOREIGN KEY (roll_number) REFERENCES students(roll_number) ON DELETE CASCADE -- Cascade delete if student is removed
) ENGINE=InnoDB;

-- Optional: Add some sample students for testing
-- INSERT INTO students (roll_number, name) VALUES ('BTECH/101/22', 'Alice Smith');
-- INSERT INTO students (roll_number, name) VALUES ('BTECH/102/22', 'Bob Johnson');
-- INSERT INTO students (roll_number, name) VALUES ('BTECH/103/22', 'Charlie Brown');