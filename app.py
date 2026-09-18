
import os
import sqlite3
import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'farhath_hotel_secret_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "menu.db")
HOTEL_NAME = "Farhath Hotel"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT
        )'''
    )
    c.execute(
        '''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            total_amount REAL,
            order_date TEXT,
            items TEXT
        )'''
    )
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    menu_items = conn.execute("SELECT * FROM menu ORDER BY id").fetchall()
    conn.close()
    
    cart_count = sum(item['qty'] for item in session.get('cart', {}).values())
    
    return render_template('index.html', menu=menu_items, hotel_name=HOTEL_NAME, cart_count=cart_count)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item_id = request.form.get('item_id')
    name = request.form.get('name')
    price = float(request.form.get('price'))
    qty = int(request.form.get('qty', 1))
    
    if 'cart' not in session:
        session['cart'] = {}
        
    cart = session['cart']
    if str(item_id) in cart:
        cart[str(item_id)]['qty'] += qty
    else:
        cart[str(item_id)] = {'name': name, 'price': price, 'qty': qty}
        
    session.modified = True
    flash(f"Added {qty} x {name} to cart.", "success")
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total = sum(item['price'] * item['qty'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=total, hotel_name=HOTEL_NAME)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    item_id = request.form.get('item_id')
    action = request.form.get('action')
    
    cart = session.get('cart', {})
    if str(item_id) in cart:
        if action == 'increase':
            cart[str(item_id)]['qty'] += 1
        elif action == 'decrease':
            cart[str(item_id)]['qty'] -= 1
            if cart[str(item_id)]['qty'] <= 0:
                del cart[str(item_id)]
        elif action == 'remove':
            del cart[str(item_id)]
            
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('index'))
        
    total = sum(item['price'] * item['qty'] for item in cart.values())
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', 'Walk-in Customer')
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        items_str = ", ".join([f"{item['qty']}x {item['name']}" for item in cart.values()])
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO orders (customer_name, total_amount, order_date, items) VALUES (?, ?, ?, ?)",
                  (customer_name, total, now, items_str))
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        
        order_details = {'id': order_id, 'customer': customer_name, 'date': now, 'total': total, 'items': cart}
        session['cart'] = {}
        session.modified = True
        
        return render_template('receipt.html', order=order_details, hotel_name=HOTEL_NAME)
        
    return render_template('checkout.html', total=total, hotel_name=HOTEL_NAME)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
