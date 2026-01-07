#!/usr/bin/env python3
"""
Simple script to add demographic fields to existing User table
"""

import sqlite3
import sys
import os

def add_demographic_fields():
    """Add age_group and gender columns to user table"""
    
    # Path to database
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ateker_voices.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'age_group' not in columns:
            print("Adding age_group column...")
            cursor.execute("ALTER TABLE user ADD COLUMN age_group VARCHAR(20)")
        else:
            print("age_group column already exists")
            
        if 'gender' not in columns:
            print("Adding gender column...")
            cursor.execute("ALTER TABLE user ADD COLUMN gender VARCHAR(10)")
        else:
            print("gender column already exists")
        
        conn.commit()
        conn.close()
        print("Database updated successfully!")
        
    except Exception as e:
        print(f"Error updating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    add_demographic_fields()
