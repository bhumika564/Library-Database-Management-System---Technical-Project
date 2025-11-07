import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import mysql.connector
import hashlib 
from datetime import datetime # Date calculation ke liye
from decimal import Decimal # Decimal bug fix ke liye

# --- Flask App Initialization ---
app = Flask(__name__, template_folder='templates') 
app.secret_key = os.urandom(24) 

# --- Database Connection ---
def get_db_connection():
    try:
        db_host = os.environ.get("DATABASE_HOST", "host.docker.internal")

        connection = mysql.connector.connect(
            host=db_host,
            user="root",
            password="",  # Blank password
            database="library_system"
        )
        print("Database connection successful")
        return connection
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None

# --- Helper Function to Hash Passwords ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Page Routes (Serving HTML) ---
@app.route('/')
@app.route('/admin-login')
def admin_login_page():
    return render_template('admin_login.html')

@app.route('/admin-home')
def admin_home_page():
    return render_template('admin_home.html')

@app.route('/add-membership-page')
def add_membership_page():
    return render_template('add_membership.html')

@app.route('/add-book-page')
def add_book_page():
    return render_template('add_book.html')

@app.route('/user-management')
def user_management_page():
    return render_template('user_management.html')

@app.route('/update-membership-page')
def update_membership_page():
    return render_template('update_membership.html')

@app.route('/master-list-books')
def master_list_books_page():
    return render_template('master_list_books.html')

# --- YAHAN NAYA CODE ADD HUA HAI (Book Available Page) ---
@app.route('/book-available-page')
def book_available_page():
    return render_template('book_available.html')
# --------------------------------------------------

# --- (Book Issue Page ko update kar rahe hain taaki wo search se link ho) ---
@app.route('/book-issue-page')
def book_issue_page():
    # URL se 'serial' parameter lene ki koshish karna
    serial_number = request.args.get('serial', '') # Default = khaali string
    # Serial number ko HTML page par bhej dena
    return render_template('book_issue.html', serial_number_from_search=serial_number)
# --------------------------------------------------

@app.route('/active-issues-page')
def active_issues_page():
    return render_template('active_issues.html')

@app.route('/master-list-memberships')
def master_list_memberships_page():
    return render_template('master_list_memberships.html')

@app.route('/return-book-page')
def return_book_page():
    return render_template('return_book.html')

@app.route('/pay-fine-page')
def pay_fine_page():
    return render_template('pay_fine.html')
    
@app.route('/user-login')
def user_login_page():
    return render_template('user_login.html')

@app.route('/user-home')
def user_home_page():
    if 'user_id' in session and not session.get('is_admin'):
        return render_template('user_home.html')
    return redirect(url_for('user_login_page'))
    
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    print("User logged out.")
    return redirect(url_for('admin_login_page'))

@app.route('/confirmation')
def confirmation_page():
    # Ye user ko check karega aur sahi home page par waapas bhejega
    if 'is_admin' in session and session['is_admin']:
        home_url = url_for('admin_home_page')
    else:
        home_url = url_for('user_home_page')
    return f"<h1>Transaction Completed Successfully!</h1><a href='{home_url}'>Go Home</a>"

# --- YAHAN NAYA API ROUTE ADD HUA HAI (Search Results) ---
@app.route('/search-results', methods=['GET'])
def search_results_page():
    # URL se search terms lena (e.g., /search-results?bookName=History)
    book_name = request.args.get('bookName', '')
    author_name = request.args.get('authorName', '')

    if not book_name and not author_name:
        # Agar dono khaali hain, to khaali results dikhao
        return render_template('search_results.html', items=[])

    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query_parts = []
        params = []
        
        if book_name:
            query_parts.append("Title LIKE %s")
            params.append(f"%{book_name}%")
        
        if author_name:
            query_parts.append("AuthorName LIKE %s")
            params.append(f"%{author_name}%")

        sql_query = "SELECT * FROM Items WHERE " + " AND ".join(query_parts)
        
        cursor.execute(sql_query, tuple(params))
        items = cursor.fetchall()
        
        # Date/Decimal objects ko string mein badalna
        for item in items:
            for key, value in item.items():
                if isinstance(value, (datetime, Decimal)):
                    item[key] = str(value)

        return render_template('search_results.html', items=items)

    except mysql.connector.Error as e:
        print(f"Error searching items: {e}")
        return "An error occurred during search.", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
# ----------------------------------------------------


# --- API Endpoints (Handling Data) ---
@app.route('/api/admin-login', methods=['POST'])
def handle_admin_login():
    """ Hamesha login kar dega (Login Bypass) """
    print("Login attempt received. Bypassing database check.")
    session['user_id'] = 1 
    session['username'] = 'adm'
    session['is_admin'] = True
    return jsonify({"success": True, "message": "Login successful!"})

@app.route('/api/user-login', methods=['POST'])
def api_user_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        hashed_pass = hash_password(password)
        query = "SELECT * FROM Users WHERE Username = %s AND PasswordHash = %s AND IsAdmin = 0 AND IsActive = 1"
        cursor.execute(query, (username, hashed_pass))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['UserID']
            session['username'] = user['Username']
            session['is_admin'] = False
            print(f"Normal User login successful for: {username}")
            return jsonify({"success": True, "message": "Login successful!"})
        else:
            print(f"User login failed for: {username}")
            return jsonify({"success": False, "message": "Invalid username or password, or user is an admin."}), 401
    except mysql.connector.Error as e:
        print(f"User Login API error: {e}")
        return jsonify({"success": False, "message": "An error occurred."}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- Maintenance Module APIs ---

@app.route('/api/add-member', methods=['POST'])
def api_add_member():
    data = request.get_json()
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        sql_query = """
            INSERT INTO Memberships 
            (FirstName, LastName, ContactNumber, ContactAddress, AadharCardNo, MembershipStartDate, MembershipEndDate, Status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')
        """
        sql_values = (
            data['firstName'], data['lastName'], data['contactNumber'], 
            data['contactAddress'], data['aadharCardNo'], data['startDate'], data['endDate']
        )
        cursor.execute(sql_query, sql_values)
        conn.commit()
        return jsonify({"message": "Member added successfully"}), 201
    except mysql.connector.Error as e:
        conn.rollback()
        if e.errno == 1062: return jsonify({"message": "Aadhar Card No already exists."}), 400
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/add-book', methods=['POST'])
def api_add_book():
    data = request.get_json()
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        sql_query = """
            INSERT INTO Items 
            (SerialNumber, ItemType, Title, AuthorName, ProcurementDate, TotalCopies, AvailableCopies, Status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Available')
        """
        sql_values = (
            data['serialNumber'], data['itemType'], data['title'],
            data.get('authorName'), data['procurementDate'],
            data['quantity'], data['quantity']
        )
        cursor.execute(sql_query, sql_values)
        conn.commit()
        return jsonify({"message": "Item added successfully"}), 201
    except mysql.connector.Error as e:
        conn.rollback() 
        if e.errno == 1062: return jsonify({"message": "Serial Number already exists."}), 400
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/add-user', methods=['POST'])
def api_add_user():
    data = request.get_json()
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        hashed_pass = hash_password(data['password'])
        sql_query = """
            INSERT INTO Users 
            (Username, PasswordHash, IsAdmin, IsActive)
            VALUES (%s, %s, %s, %s)
        """
        sql_values = (data['username'], hashed_pass, data['isAdmin'], data['isActive'])
        cursor.execute(sql_query, sql_values)
        conn.commit()
        return jsonify({"message": "User created successfully"}), 201
    except mysql.connector.Error as e:
        conn.rollback() 
        if e.errno == 1062: return jsonify({"message": "Username already exists."}), 400
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/search-member', methods=['POST'])
def api_search_member():
    data = request.get_json()
    member_id = data.get('memberId')
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True) 
        cursor.execute("SELECT * FROM Memberships WHERE MembershipID = %s", (member_id,))
        member = cursor.fetchone() 
        if member:
            for key, value in member.items():
                if isinstance(value, datetime):
                    member[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    member[key] = f"{value:.2f}"
            return jsonify(member), 200
        else:
            return jsonify({"message": "Member not found with that ID."}), 404
    except mysql.connector.Error as e:
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/update-member', methods=['POST'])
def api_update_member():
    data = request.get_json()
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT MembershipEndDate FROM Memberships WHERE MembershipID = %s", (data['membershipID'],))
        member = cursor.fetchone()
        if not member:
            return jsonify({"message": "Member not found."}), 404
            
        current_end_date = member['MembershipEndDate']
        
        if data['action'] == 'extend_6':
            sql_query = "UPDATE Memberships SET MembershipEndDate = DATE_ADD(%s, INTERVAL 6 MONTH) WHERE MembershipID = %s"
            sql_values = (current_end_date, data['membershipID'])
        elif data['action'] == 'extend_12':
            sql_query = "UPDATE Memberships SET MembershipEndDate = DATE_ADD(%s, INTERVAL 12 MONTH) WHERE MembershipID = %s"
            sql_values = (current_end_date, data['membershipID'])
        elif data['action'] == 'extend_24':
            sql_query = "UPDATE Memberships SET MembershipEndDate = DATE_ADD(%s, INTERVAL 24 MONTH) WHERE MembershipID = %s"
            sql_values = (current_end_date, data['membershipID'])
        elif data['action'] == 'cancel':
            sql_query = "UPDATE Memberships SET Status = 'Cancelled' WHERE MembershipID = %s"
            sql_values = (data['membershipID'],)
        else:
            return jsonify({"message": "Invalid action."}), 400

        cursor.execute(sql_query, sql_values)
        conn.commit()
        return jsonify({"message": "Membership updated successfully"}), 200
    except mysql.connector.Error as e:
        conn.rollback()
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

# --- Reports Module APIs ---

@app.route('/api/get-all-items', methods=['GET'])
def api_get_all_items():
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True) 
        cursor.execute("SELECT * FROM Items")
        items = cursor.fetchall()
        for item in items:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    item[key] = f"{value:.2f}"
        return jsonify(items), 200
    except mysql.connector.Error as e:
        print(f"Error fetching items: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/get-active-issues', methods=['GET'])
def api_get_active_issues():
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True) 
        sql_query = """
            SELECT 
                t.MembershipID, 
                t.IssueDate, 
                t.DueDate,
                i.SerialNumber,
                i.Title
            FROM 
                IssueTransactions t
            JOIN 
                Items i ON t.ItemID = i.ItemID
            WHERE 
                t.Status = 'Issued'
            ORDER BY
                t.DueDate ASC;
        """
        cursor.execute(sql_query)
        issues = cursor.fetchall()
        for issue in issues:
            for key, value in issue.items():
                if isinstance(value, datetime):
                    issue[key] = value.isoformat()
        return jsonify(issues), 200
    except mysql.connector.Error as e:
        print(f"Error fetching active issues: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/get-all-memberships', methods=['GET'])
def api_get_all_memberships():
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True) 
        sql_query = "SELECT * FROM Memberships ORDER BY MembershipID ASC"
        cursor.execute(sql_query)
        members = cursor.fetchall() 
        for member in members:
            for key, value in member.items():
                if isinstance(value, datetime):
                    member[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    member[key] = f"{value:.2f}"
        return jsonify(members), 200
    except mysql.connector.Error as e:
        print(f"Error fetching memberships: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

# --- Transactions Module APIs ---

@app.route('/api/search-book-by-serial', methods=['POST'])
def api_search_book():
    data = request.get_json()
    serial_number = data.get('serialNumber')
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True) 
        cursor.execute("SELECT * FROM Items WHERE SerialNumber = %s", (serial_number,))
        item = cursor.fetchone()
        if item:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    item[key] = f"{value:.2f}"
            return jsonify(item), 200
        else:
            return jsonify({"message": "Item not found with that Serial Number."}), 404
    except mysql.connector.Error as e:
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/issue-book', methods=['POST'])
def api_issue_book():
    data = request.get_json()
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction()
        
        cursor.execute("SELECT ItemID, Status FROM Items WHERE SerialNumber = %s", (data['serialNumber'],))
        item = cursor.fetchone()
        if not item:
            conn.rollback()
            return jsonify({"message": "Item not found."}), 404
        if item['Status'] != 'Available':
            conn.rollback()
            return jsonify({"message": "This item is not available for issue."}), 400
        item_id = item['ItemID']
        
        cursor.execute("SELECT MembershipID, Status FROM Memberships WHERE MembershipID = %s", (data['memberId'],))
        member = cursor.fetchone()
        if not member:
            conn.rollback()
            return jsonify({"message": "Member not found."}), 404
        if member['Status'] != 'Active':
            conn.rollback()
            return jsonify({"message": "This member is not active."}), 400
        member_id = member['MembershipID']

        sql_insert_transaction = """
            INSERT INTO IssueTransactions
            (ItemID, MembershipID, IssueDate, DueDate, Status)
            VALUES (%s, %s, %s, %s, 'Issued')
        """
        sql_values_transaction = (item_id, member_id, data['issueDate'], data['returnDate'])
        cursor.execute(sql_insert_transaction, sql_values_transaction)
        
        sql_update_item = "UPDATE Items SET Status = 'Issued', AvailableCopies = AvailableCopies - 1 WHERE ItemID = %s"
        cursor.execute(sql_update_item, (item_id,))
        
        conn.commit()
        return jsonify({"message": "Book issued successfully"}), 201
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"Database issue error: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/search-issued-book', methods=['POST'])
def api_search_issued_book():
    data = request.get_json()
    serial_number = data.get('serialNumber')
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        sql_query = """
            SELECT 
                t.TransactionID, t.IssueDate, t.DueDate,
                i.Title,
                m.FirstName, m.LastName,
                DATEDIFF(CURDATE(), t.DueDate) AS DaysOverdue,
                (DATEDIFF(CURDATE(), t.DueDate) * 1.00) AS FineCalculated 
            FROM 
                IssueTransactions t
            JOIN 
                Items i ON t.ItemID = i.ItemID
            JOIN
                Memberships m ON t.MembershipID = m.MembershipID
            WHERE 
                i.SerialNumber = %s AND t.Status = 'Issued'
        """
        cursor.execute(sql_query, (serial_number,))
        transaction = cursor.fetchone() 
        if transaction:
            for key, value in transaction.items():
                if isinstance(value, datetime):
                    transaction[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    transaction[key] = float(value)
            if transaction['DaysOverdue'] < 0:
                transaction['DaysOverdue'] = 0
                transaction['FineCalculated'] = 0.0
            return jsonify(transaction), 200
        else:
            return jsonify({"message": "No active issue found for that Serial Number."}), 404
    except mysql.connector.Error as e:
        print(f"Error searching issued book: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/return-book', methods=['POST'])
def api_return_book():
    data = request.get_json()
    transaction_id = data.get('transactionID')
    actual_return_date = data.get('actualReturnDate')
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction() 

        cursor.execute("SELECT ItemID, MembershipID, DueDate FROM IssueTransactions WHERE TransactionID = %s", (transaction_id,))
        transaction = cursor.fetchone()
        if not transaction:
            conn.rollback()
            return jsonify({"message": "Transaction not found."}), 404
        
        item_id = transaction['ItemID']
        member_id = transaction['MembershipID']
        due_date = transaction['DueDate']

        sql_update_trans = """
            UPDATE IssueTransactions 
            SET Status = 'Returned', ActualReturnDate = %s 
            WHERE TransactionID = %s
        """
        cursor.execute(sql_update_trans, (actual_return_date, transaction_id))
        
        sql_update_item = "UPDATE Items SET Status = 'Available', AvailableCopies = AvailableCopies + 1 WHERE ItemID = %s"
        cursor.execute(sql_update_item, (item_id,))
        
        cursor.execute("SELECT DATEDIFF(%s, %s) AS DaysOverdue", (actual_return_date, due_date))
        overdue_result = cursor.fetchone()
        days_overdue = overdue_result['DaysOverdue']
        
        if days_overdue > 0:
            fine_amount = days_overdue * 1.00 # ₹1 per day fine
            sql_add_fine = """
                INSERT INTO Fines (TransactionID, MembershipID, FineAmountCalculated, DateFined, FinePaid)
                VALUES (%s, %s, %s, CURDATE(), FALSE)
            """
            cursor.execute(sql_add_fine, (transaction_id, member_id, fine_amount))
            
            sql_update_member_fine = "UPDATE Memberships SET TotalFineDue = TotalFineDue + %s WHERE MembershipID = %s"
            cursor.execute(sql_update_member_fine, (fine_amount, member_id))

        conn.commit()
        return jsonify({"message": "Book returned successfully"}), 200
    except mysql.connector.Error as e:
        conn.rollback() 
        print(f"Error returning book: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/pay-fine', methods=['POST'])
def api_pay_fine():
    data = request.get_json()
    member_id = data.get('membershipID')
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        conn.start_transaction() 
        
        sql_update_member = "UPDATE Memberships SET TotalFineDue = 0.00 WHERE MembershipID = %s"
        cursor.execute(sql_update_member, (member_id,))
        
        sql_update_fines = "UPDATE Fines SET FinePaid = TRUE, DatePaid = CURDATE() WHERE MembershipID = %s AND FinePaid = FALSE"
        cursor.execute(sql_update_fines, (member_id,))
        
        conn.commit() 
        return jsonify({"message": "Fine paid successfully"}), 200
    except mysql.connector.Error as e:
        conn.rollback() 
        print(f"Error paying fine: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

# --- Run the Server ---
# --- YAHAN NAYA CODE ADD HUA HAI (Overdue Returns Page) ---
@app.route('/overdue-returns-page')
def overdue_returns_page():
    return render_template('overdue_returns.html')
# --------------------------------------------------

# --- YAHAN NAYA API ROUTE ADD HUA HAI (Get Overdue Returns) ---
@app.route('/api/get-overdue-returns', methods=['GET'])
def api_get_overdue_returns():
    conn = get_db_connection()
    if not conn: return jsonify({"message": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True) 
        
        # Ye SQL query 'IssueTransactions' table ko 'Items' table se JODTI (JOIN) hai
        # Hum sirf unhi transactions ko dhoondh rahe hain jinka status 'Issued' hai
        # AUR jinka DueDate aaj se pehle (past) mein hai.
        # 'DATEDIFF(CURDATE(), t.DueDate)' se hum late dino (days) ka count nikaalte hain.
        # Hum maan rahe hain ki fine ₹ 1/- per day hai.
        
        sql_query = """
            SELECT 
                t.MembershipID, 
                t.IssueDate, 
                t.DueDate,
                i.SerialNumber,
                i.Title,
                DATEDIFF(CURDATE(), t.DueDate) AS DaysOverdue,
                (DATEDIFF(CURDATE(), t.DueDate) * 1.00) AS FineCalculated 
            FROM 
                IssueTransactions t
            JOIN 
                Items i ON t.ItemID = i.ItemID
            WHERE 
                t.Status = 'Issued' AND t.DueDate < CURDATE()
            ORDER BY
                t.DueDate ASC;
        """
        cursor.execute(sql_query)
        items = cursor.fetchall() # Saari overdue rows ko le aao
        
        # JSON ko clean data chahiye. Humein Date aur Decimal ko string mein badalna hoga.
        for item in items:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat() # Date ko string banao
                elif isinstance(value, Decimal):
                    item[key] = float(value) # Decimal ko float banao (JSON ke liye safe)
        
        return jsonify(items), 200
    
    except mysql.connector.Error as e:
        print(f"Error fetching overdue returns: {e}")
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()
# ----------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)