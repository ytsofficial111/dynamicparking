from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key
import os
import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal


app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with a strong secret key
app.permanent_session_lifetime = timedelta(minutes=30)

# DynamoDB resource
dynamodb = boto3.resource('dynamodb')


# DynamoDB Tables setup functions
def setup_users_table():
    table_name = 'Userdata'
    try:
        # Try to get the table first
        table = dynamodb.Table(table_name)
        table.table_status  # This will raise an exception if table doesn't exist
        return table
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        # Create table if it doesn't exist
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'email', 'KeyType': 'HASH'},  # Primary key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'},
                {'AttributeName': 'username', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UsernameIndex',
                    'KeySchema': [
                        {'AttributeName': 'username', 'KeyType': 'HASH'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Wait until the table exists
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        return table
    except Exception as e:
        print(f"Error setting up Userdata table: {str(e)}")
        return None

def setup_owners_table():
    table_name = 'Owners'
    try:
        # Try to get the table first
        table = dynamodb.Table(table_name)
        table.table_status  # This will raise an exception if table doesn't exist
        return table
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        # Create table if it doesn't exist
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'email', 'KeyType': 'HASH'},  # Primary key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Wait until the table exists
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        return table
    except Exception as e:
        print(f"Error setting up Owners table: {str(e)}")
        return None

def setup_slots_table():
    table_name = 'SlotDetails'
    try:
        # Try to get the table first
        table = dynamodb.Table(table_name)
        table.table_status  # This will raise an exception if table doesn't exist
        return table
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        # Create table if it doesn't exist
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'},  # Primary key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'ownerEmail', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'OwnerEmailIndex',
                    'KeySchema': [
                        {'AttributeName': 'ownerEmail', 'KeyType': 'HASH'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Wait until the table exists
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        return table
    except Exception as e:
        print(f"Error setting up SlotDetails table: {str(e)}")
        return None

# Initialize tables
users_table = None
owners_table = None
slots_table = None

def verify_tables():
    try:
        # List all tables
        existing_tables = dynamodb.meta.client.list_tables()['TableNames']
        print("Existing DynamoDB tables:", existing_tables)
        
        # Check Owners table
        if 'Owners' in existing_tables:
            owners_table = dynamodb.Table('Owners')
            print("Owners table exists with schema:", owners_table.key_schema)
        else:
            print("Owners table does not exist!")
        
        # Check Userdata table
        if 'Userdata' in existing_tables:
            users_table = dynamodb.Table('Userdata')
            print("Userdata table exists with schema:", users_table.key_schema)
        else:
            print("Userdata table does not exist!")
            
    except Exception as e:
        print("Error verifying tables:", str(e))

def init_tables():
    global users_table, owners_table, slots_table
    print("Initializing DynamoDB tables...")
    verify_tables()
    users_table = setup_users_table()
    owners_table = setup_owners_table()
    slots_table = setup_slots_table()
    print("Tables initialized:", {
        'users_table': users_table is not None,
        'owners_table': owners_table is not None,
        'slots_table': slots_table is not None
    })

# Initialize tables at startup
with app.app_context():
    init_tables()

# Model helper functions
def find_user_by_email(email):
    try:
        if not users_table:
            init_tables()
        response = users_table.get_item(Key={'email': email})
        return response.get('Item')
    except Exception as e:
        print(f"Error finding user by email: {str(e)}")
        return None

def find_user_by_username(username):
    try:
        if not users_table:
            init_tables()
        response = users_table.query(
            IndexName='UsernameIndex',
            KeyConditionExpression=Key('username').eq(username)
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"Error finding user by username: {str(e)}")
        return None

def find_owner_by_email(email):
    try:
        if not owners_table:
            init_tables()
        print("Looking up owner with email:", email)
        response = owners_table.get_item(Key={'email': email})
        owner = response.get('Item')
        print("Found owner:", owner)
        return owner
    except Exception as e:
        print(f"Error finding owner by email: {str(e)}")
        return None

def find_all_owners():
    try:
        if not owners_table:
            init_tables()
        response = owners_table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error finding all owners: {str(e)}")
        return []

def find_slot_by_id(id):
    try:
        if not slots_table:
            init_tables()
        response = slots_table.get_item(Key={'id': id})
        return response.get('Item')
    except Exception as e:
        print(f"Error finding slot by id: {str(e)}")
        return None

def find_slots_by_owner_email(ownerEmail):
    try:
        if not slots_table:
            init_tables()
        response = slots_table.query(
            IndexName='OwnerEmailIndex',
            KeyConditionExpression=Key('ownerEmail').eq(ownerEmail)
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error finding slots by owner email: {str(e)}")
        return []

def save_user(user_data):
    try:
        if not users_table:
            init_tables()
        response = users_table.put_item(Item=user_data)
        return response
    except Exception as e:
        print(f"Error saving user: {str(e)}")
        return None

def save_owner(owner_data):
    try:
        if not owners_table:
            init_tables()
        # Convert costPerHour to Decimal for DynamoDB
        owner_data['costPerHour'] = Decimal(str(owner_data['costPerHour']))
        print("Attempting to save owner data to DynamoDB:", owner_data)
        response = owners_table.put_item(
            Item={
                'email': owner_data['email'],
                'password': owner_data['password'],
                'orgType': owner_data['orgType'],
                'orgName': owner_data['orgName'],
                'costPerHour': owner_data['costPerHour']
            }
        )
        print("DynamoDB response:", response)
        return response
    except Exception as e:
        print(f"Error saving owner: {str(e)}")
        raise e

def save_slot(slot_data):
    try:
        if not slots_table:
            init_tables()
        response = slots_table.put_item(Item=slot_data)
        return response
    except Exception as e:
        print(f"Error saving slot: {str(e)}")
        return None

# Routes
@app.route('/')
def show_landing_page():
    return render_template('land.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = find_user_by_username(username)
        
        if user and user.get('password') == password:
            session['logged_in_email'] = user.get('email')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', status='Invalid credentials. Please try again.')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if find_user_by_email(email):
            return render_template('register.html', status='Email is already registered!')
        
        user_data = {
            'email': email,
            'username': username,
            'password': password
        }
        
        save_user(user_data)
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/index')
def index():
    if 'logged_in_email' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html')

@app.route('/ownregister', methods=['GET', 'POST'])
def owner_register():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            org_type = request.form.get('orgType', '').lower()
            org_name = request.form.get('orgName')
            cost_per_hour = request.form.get('costPerHour', '0')
            
            # Debug print
            print("Registration Data:", {
                'email': email,
                'org_type': org_type,
                'org_name': org_name,
                'cost_per_hour': cost_per_hour
            })
            
            # Input validation
            if not all([email, password, org_type, org_name, cost_per_hour]):
                return render_template('ownerreg.html', status='All fields are required!')
            
            try:
                cost_per_hour = float(cost_per_hour)
            except ValueError:
                return render_template('ownerreg.html', status='Invalid cost per hour value!')
            
            # Validate organization type
            valid_org_types = ['mall', 'restaurant', 'hospital']
            if org_type not in valid_org_types:
                return render_template('ownerreg.html', status='Invalid organization type!')
            
            # Check if email already exists
            existing_owner = find_owner_by_email(email)
            if existing_owner:
                return render_template('ownerreg.html', status='Email is already registered!')
            
            # Validate password
            if len(password) < 8:
                return render_template('ownerreg.html', status='Password must be at least 8 characters long!')
            
            owner_data = {
                'email': email,
                'password': password,
                'orgType': org_type,
                'orgName': org_name,
                'costPerHour': cost_per_hour
            }
            
            # Debug print
            print("Saving owner data:", owner_data)
            
            # Save owner data
            save_owner(owner_data)
            print("Owner data saved successfully")
            return redirect(url_for('owner_login'))
            
        except Exception as e:
            print("Error in owner registration:", str(e))
            return render_template('ownerreg.html', status='Error registering owner. Please try again.')
    
    return render_template('ownerreg.html')

@app.route('/ownerlog', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Debug print
        print("Login attempt for email:", email)
        
        owner = find_owner_by_email(email)
        
        # Debug print
        print("Found owner data:", owner)
        
        if owner and owner.get('password') == password:
            session['logged_in_email'] = email
            print("Login successful for email:", email)
            return redirect(url_for('owner_dashboard'))
        else:
            error_message = 'Invalid email or password!'
            if not owner:
                error_message = 'Email not found!'
            elif owner.get('password') != password:
                error_message = 'Incorrect password!'
            print("Login failed:", error_message)
            return render_template('ownerlogin.html', status=error_message)
    
    return render_template('ownerlogin.html')

@app.route('/ownerdashboard')
def owner_dashboard():
    if 'logged_in_email' not in session:
        return redirect(url_for('owner_login'))
    
    return render_template('ownerhome.html', email=session['logged_in_email'])

@app.route('/addslot', methods=['GET', 'POST'])
def add_slot():
    if 'logged_in_email' not in session:
        return redirect(url_for('owner_login'))
    
    return render_template('addslot.html', email=session['logged_in_email'])

@app.route('/addSlotDetails', methods=['POST'])
def add_slot_details():
    if 'logged_in_email' not in session:
        return redirect(url_for('owner_login'))
    
    owner_email = session['logged_in_email']
    slot_number = request.form.get('slotNumber')
    floor_number = request.form.get('floorNumber')
    
    # Validate input fields
    if not slot_number or not floor_number:
        return render_template('addslot.html', status='Slot number and floor number cannot be empty!')
    
    slot_data = {
        'id': str(uuid.uuid4()),
        'ownerEmail': owner_email,
        'slotNumber': slot_number,
        'floorNumber': floor_number,
        'bookingDate': None,
        'checkinTime': None,
        'status': None
    }
    
    save_slot(slot_data)
    return redirect(url_for('owner_dashboard'))

@app.route('/ownerslots')
def owner_slots():
    if 'logged_in_email' not in session:
        return redirect(url_for('owner_login'))
    
    owner_email = session['logged_in_email']
    slots = find_slots_by_owner_email(owner_email)
    
    return render_template('ownerslot.html', slots=slots)

@app.route('/owners')
def get_all_owners():
    if 'logged_in_email' not in session:
        return redirect(url_for('login'))
    
    owners = find_all_owners()
    return render_template('bookslot.html', owners=owners)

@app.route('/slots/<owner_email>')
def get_owner_slots(owner_email):
    if 'logged_in_email' not in session:
        return redirect(url_for('login'))
    
    slots = find_slots_by_owner_email(owner_email)
    return render_template('viewSlots.html', slots=slots, logged_in_email=session['logged_in_email'])

@app.route('/book', methods=['POST'])
def book_slot():
    if 'logged_in_email' not in session:
        print("User not logged in")
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
    
    logged_in_email = session.get('logged_in_email')
    print(f"Booking request from user: {logged_in_email}")
    
    slot_id = request.form.get('slotId')
    print(f"Slot ID to book: {slot_id}")
    
    slot = find_slot_by_id(slot_id)
    print(f"Found slot: {slot}")
    
    if not slot:
        return jsonify({'status': 'error', 'message': 'Slot not found'}), 404
    
    if slot.get('status'):
        print(f"Slot already booked by: {slot.get('status')}")
        return jsonify({'status': 'error', 'message': 'Slot is already booked'}), 409
    
    # Update the slot details
    today = date.today().isoformat()
    current_time = datetime.now().time().isoformat()
    
    slot['bookingDate'] = today
    slot['checkinTime'] = current_time
    slot['status'] = logged_in_email
    
    print(f"Updating slot with data: {slot}")
    save_slot(slot)
    print("Slot booked successfully")
    
    return jsonify({'status': 'success', 'message': 'Slot booked successfully'})

@app.route('/cancel', methods=['POST'])
def cancel_slot():
    if 'logged_in_email' not in session:
        print("User not logged in")
        return jsonify({
            'status': 'error',
            'message': 'User not logged in'
        }), 401
    
    logged_in_email = session.get('logged_in_email')
    print(f"Cancel request from user: {logged_in_email}")
    
    slot_id = request.form.get('slotId')
    print(f"Slot ID to cancel: {slot_id}")
    
    if not slot_id:
        print("No slot ID provided")
        return jsonify({
            'status': 'error',
            'message': 'Slot ID is required'
        }), 400
    
    try:
        slot = find_slot_by_id(slot_id)
        print(f"Found slot: {slot}")
        
        if not slot:
            print("Slot not found")
            return jsonify({
                'status': 'error',
                'message': 'Slot not found'
            }), 404

        slot_status = slot.get('status')
        print(f"Comparing slot status: '{slot_status}' with logged in email: '{logged_in_email}'")
        
        if not slot_status:
            print("Slot is not booked")
            return jsonify({
                'status': 'error',
                'message': 'This slot is not booked'
            }), 400
            
        if slot_status.strip() != logged_in_email.strip():
            print(f"Authorization failed. Slot booked by '{slot_status}'")
            return jsonify({
                'status': 'error',
                'message': f"You are not authorized to cancel this booking. The slot was booked by {slot_status}"
            }), 403

        owner = find_owner_by_email(slot.get('ownerEmail'))
        if not owner:
            print(f"Owner not found for email: {slot.get('ownerEmail')}")
            return jsonify({
                'status': 'error',
                'message': 'Owner not found'
            }), 404

        if slot.get('bookingDate') and slot.get('checkinTime'):
            try:
                booking_time = datetime.combine(
                    date.fromisoformat(slot.get('bookingDate')),
                    time.fromisoformat(slot.get('checkinTime'))
                )
                current_time = datetime.now()
                
                # Calculate the duration in hours
                duration_in_hours = (current_time - booking_time).total_seconds() / 3600
                print(f"Duration: {duration_in_hours:.2f} hours")
                
                if duration_in_hours < 0:
                    print("Invalid duration (negative time)")
                    return jsonify({
                        'status': 'error',
                        'message': 'Invalid booking time'
                    }), 400
                
                # Calculate the bill amount
                cost_per_hour = float(owner.get('costPerHour', 0))
                bill_amount = cost_per_hour * duration_in_hours
                print(f"Bill amount: ₹{bill_amount:.2f} (₹{cost_per_hour}/hour)")
                
                # Reset the slot details
                slot['bookingDate'] = None
                slot['checkinTime'] = None
                slot['status'] = None
                
                print(f"Resetting slot with data: {slot}")
                save_slot(slot)
                print("Slot reset successfully")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Booking cancelled successfully. Bill Amount: ₹{bill_amount:.2f}'
                })
            except (ValueError, TypeError) as e:
                print(f"Error calculating bill: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Error calculating bill: Invalid date/time format'
                }), 400
        else:
            print("Incomplete booking details")
            return jsonify({
                'status': 'error',
                'message': 'Booking details are incomplete'
            }), 400
    except Exception as e:
        print(f"Error in cancel_slot: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while cancelling the slot'
        }), 500

@app.route('/get_bill', methods=['POST'])
def get_bill():
    if 'logged_in_email' not in session:
        print("User not logged in")
        return jsonify({
            'status': 'error',
            'message': 'User not logged in'
        }), 401
    
    logged_in_email = session.get('logged_in_email')
    print(f"Bill request from user: {logged_in_email}")
    
    slot_id = request.form.get('slotId')
    print(f"Slot ID for bill: {slot_id}")
    
    try:
        slot = find_slot_by_id(slot_id)
        print(f"Found slot: {slot}")
        
        if not slot:
            print("Slot not found")
            return jsonify({
                'status': 'error',
                'message': 'Slot not found'
            }), 404

        slot_status = slot.get('status')
        print(f"Comparing slot status: '{slot_status}' with logged in email: '{logged_in_email}'")
        
        if not slot_status:
            print("Slot is not booked")
            return jsonify({
                'status': 'error',
                'message': 'This slot is not booked'
            }), 400
            
        if slot_status.strip() != logged_in_email.strip():
            print(f"Authorization failed. Slot booked by '{slot_status}'")
            return jsonify({
                'status': 'error',
                'message': f"You are not authorized to view bill for this booking"
            }), 403

        owner = find_owner_by_email(slot.get('ownerEmail'))
        if not owner:
            print(f"Owner not found for email: {slot.get('ownerEmail')}")
            return jsonify({
                'status': 'error',
                'message': 'Owner not found'
            }), 404

        if slot.get('bookingDate') and slot.get('checkinTime'):
            try:
                booking_time = datetime.combine(
                    date.fromisoformat(slot.get('bookingDate')),
                    time.fromisoformat(slot.get('checkinTime'))
                )
                current_time = datetime.now()
                
                # Calculate the duration in hours
                duration_in_hours = (current_time - booking_time).total_seconds() / 3600
                print(f"Duration: {duration_in_hours:.2f} hours")
                
                if duration_in_hours < 0:
                    print("Invalid duration (negative time)")
                    return jsonify({
                        'status': 'error',
                        'message': 'Invalid booking time'
                    }), 400
                
                # Calculate the bill amount
                cost_per_hour = float(owner.get('costPerHour', 0))
                bill_amount = cost_per_hour * duration_in_hours
                print(f"Bill amount: ₹{bill_amount:.2f} (₹{cost_per_hour}/hour)")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Bill Amount: ₹{bill_amount:.2f}',
                    'amount': bill_amount
                })
            except (ValueError, TypeError) as e:
                print(f"Error calculating bill: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': 'Error calculating bill: Invalid date/time format'
                }), 400
        else:
            print("Incomplete booking details")
            return jsonify({
                'status': 'error',
                'message': 'Booking details are incomplete'
            }), 400
    except Exception as e:
        print(f"Error in get_bill: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while calculating the bill'
        }), 500

@app.route('/logout')
def logout():
    session.pop('logged_in_email', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)