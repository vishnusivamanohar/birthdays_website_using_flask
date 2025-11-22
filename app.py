from flask import Flask, render_template, request, redirect, session
import mysql.connector
import re
import datetime

# Get today's date formatted as MM-DD for comparison with database entries
# Example: '11-21'
today_date = datetime.date.today().strftime("%m-%d")

app = Flask(__name__)
app.secret_key = "secret123"

# --- Database Connection ---
def get_db_connection():
    """Establishes and returns a database connection."""
    # NOTE: Update these credentials to match your MySQL setup
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Vishnu@2022",
        database="birthday_db"
    )

# Function to sanitize username for safe table naming
def clean_username(name):
    """Replaces non-alphanumeric characters with underscores."""
    # This prevents special characters/spaces from breaking SQL identifiers
    return re.sub(r'[\W]+', '_', name)


# ----------------------------------------------------------------------
# 🌟 CORE APPLICATION ROUTES
# ----------------------------------------------------------------------

@app.route("/")
def home():
    """Renders the login page."""
    return render_template("login.html")


@app.route("/index")
def index():
    if "user" not in session:
        return redirect("/")
        
    db = get_db_connection()
    cursor = db.cursor()

    username = session["user"]
    clean_name = clean_username(username)
    table_name = clean_name

    # SQL query: Select name and format the date as MM-DD (to match Python's today_date)
    sql_query = f"""
        SELECT 
            name, 
            DATE_FORMAT(date, '%m-%d') AS formatted_date 
        FROM `{table_name}` 
        ORDER BY MONTH(date), DAY(date)
    """
    try:
        cursor.execute(sql_query)
        data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error fetching data for index: {err}")
        data = []
    
    today_birthdays = []    
    
    for row in data:
        name = row[0]
        date_mm_dd = row[1] # This is a string like '11-21'
        # Correct comparison of MM-DD strings
        if date_mm_dd == today_date:
            today_birthdays.append(name.capitalize())

    cursor.close()
    db.close()

    # Pass the list of dictionary objects to the template
    return render_template("index.html", birthdays=today_birthdays)


# ----------------------------------------------------------------------
# 🔐 AUTHENTICATION ROUTES
# ----------------------------------------------------------------------

@app.route("/auth", methods=["POST"])
def auth():
    """Handles both user login and signup logic."""
    db = get_db_connection()
    cursor = db.cursor()

    name = request.form["name"].strip()
    password = request.form["password"].strip()
    action = request.form["action"]

    clean_name = clean_username(name)
    table_name = clean_name

    # --- SIGN UP ---
    if action == "signup":
        # Check if username exists
        cursor.execute("SELECT name FROM users WHERE name=%s", (name,))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return "<script>alert('Username already exists! Try another one.'); window.location.href = '/';</script>"

        # Insert new user
        cursor.execute("INSERT INTO users (name, password) VALUES (%s, %s)", (name, password))
        
        # Create user's custom birthday table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                date DATE
            );
        """)
        db.commit()
        session["user"] = name
        cursor.close()
        db.close()
        return "<script>alert('Account Created Successfully!'); window.location.href = '/index';</script>"


    # --- LOGIN ---
    elif action == "login":
        cursor.execute("SELECT * FROM users WHERE name=%s AND password=%s", (name, password))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            db.close()
            return "<script>alert('Invalid Username or Password!'); window.location.href = '/';</script>"

        # Check if user's custom birthday table exists
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return "<script>alert('User table missing! Please register again.'); window.location.href = '/';</script>"

        session["user"] = name
        cursor.close()
        db.close()
        return redirect("/index")


@app.route("/logout")
def logout():
    """Clears the session and redirects to the login page."""
    session.pop("user", None)
    return redirect("/")


# ----------------------------------------------------------------------
# 🎁 BIRTHDAY MANAGEMENT ROUTES
# ----------------------------------------------------------------------

@app.route("/birthday_input")
def birthday_input():
    """Renders the form for adding a new birthday."""
    if "user" not in session:
        return redirect("/")
    return render_template("birthday_input.html")


@app.route("/save_birthday", methods=["POST"])
def save_birthday():
    """Saves a new birthday entry to the user's custom table."""
    if "user" not in session:
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor()

    username = session["user"]
    table_name = clean_username(username)

    name = request.form["name"]
    date = request.form["date"]

    cursor.execute(f"INSERT INTO `{table_name}` (name, date) VALUES (%s, %s)", (name, date))
    db.commit()
    cursor.close()
    db.close()

    return "<script>alert('Birthday Saved Successfully!'); window.location.href = '/birthday_input';</script>"


@app.route("/view_birthday")
def view_birthday():
    """Fetches and displays all saved birthdays, sorted by month/day."""
    if "user" not in session:
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor()

    username = session["user"]
    table_name = clean_username(username)

    # Select ID (for deletion), name, and date
    cursor.execute(f"SELECT id, name, date FROM `{table_name}` ORDER BY MONTH(date), DAY(date)")
    data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("view_birthdays.html", data=data, username=username)


@app.route("/delete_birthday/<int:birthday_id>")
def delete_birthday(birthday_id):
    """Deletes a birthday record using its ID."""
    if "user" not in session:
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor()

    username = session["user"]
    table_name = clean_username(username)

    try:
        # Securely execute DELETE query using the table name and the record ID
        cursor.execute(f"DELETE FROM `{table_name}` WHERE id = %s", (birthday_id,))
        db.commit()
        alert_msg = "Birthday Deleted Successfully!"
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        alert_msg = "Error deleting birthday."

    cursor.close()
    db.close()

    return f"""
        <script>
            alert("{alert_msg}");
            window.location.href = "/view_birthday";
        </script>
    """


if __name__ == "__main__":
    app.run(debug=True)