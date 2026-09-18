"""
online_food_ordering_tkinter_farhath_hotel.py

Single-file Tkinter + SQLite3 demo app: "Farhath Hotel" Online Food Ordering System
Features:
 - Menu stored in local SQLite database (menu.db)
 - Add to cart system
 - Order summary
 - Bill generation (saves text file with bill)
 - Simple, clear Tkinter UI

Requirements: Python 3.8+ (no external packages)
"""

import os
import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

DB_FILE = "menu.db"
HOTEL_NAME = "Farhath Hotel"

# Expanded sample menu (the list you confirmed)
SAMPLE_MENU = [
    ("Margherita Pizza", 200.0, "Classic cheese pizza"),
    ("Chicken Biryani", 250.0, "Spicy chicken biryani with raita"),
    ("Mutton Biryani", 320.0, "Slow-cooked mutton biryani"),
    ("Veg Biryani", 200.0, "Aromatic veg biryani"),
    ("Chicken Shawarma", 150.0, "Wrap with marinated chicken"),
    ("Paneer Butter Masala", 180.0, "Creamy paneer curry"),
    ("Gobi Manchurian", 160.0, "Crispy cauliflower in sauce"),
    ("Chicken 65", 170.0, "Spicy fried chicken appetizer"),
    ("Egg Noodles", 140.0, "Egg noodles with veggies"),
    ("Veg Noodles", 120.0, "Stir-fried veg noodles"),
    ("Chicken Fried Rice", 150.0, "Fried rice with chicken"),
    ("Masala Dosa", 90.0, "Crispy dosa with potato masala"),
    ("Idli Sambar", 80.0, "Steamed idli with sambar"),
    ("Parotta + Kurma", 110.0, "Flaky parotta with kurma"),
    ("Cold Coffee", 70.0, "Iced coffee with milk"),
    ("Ice Cream (Vanilla)", 60.0, "Vanilla scoop"),
    ("French Fries", 80.0, "Crispy potato fries"),
    ("Veg Fried Rice", 120.0, "Mixed vegetables and rice"),
]

# ---------- Database helpers ----------

def init_db(db_file=DB_FILE):
    created = not os.path.exists(db_file)
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT
        )
        """
    )
    conn.commit()

    # Insert sample data if new (or if empty)
    if created:
        c.executemany(
            "INSERT INTO menu (name, price, description) VALUES (?, ?, ?)",
            SAMPLE_MENU
        )
        conn.commit()
    else:
        # if database exists but empty, also populate with SAMPLE_MENU
        c.execute("SELECT COUNT(*) FROM menu")
        count = c.fetchone()[0]
        if count == 0:
            c.executemany(
                "INSERT INTO menu (name, price, description) VALUES (?, ?, ?)",
                SAMPLE_MENU
            )
            conn.commit()
    return conn


def fetch_menu(conn):
    c = conn.cursor()
    c.execute("SELECT id, name, price, description FROM menu ORDER BY id")
    return c.fetchall()


def add_menu_item(conn, name, price, description=""):
    c = conn.cursor()
    c.execute("INSERT INTO menu (name, price, description) VALUES (?, ?, ?)", (name, price, description))
    conn.commit()
    return c.lastrowid


def update_menu_item(conn, item_id, name, price, description=""):
    c = conn.cursor()
    c.execute("UPDATE menu SET name=?, price=?, description=? WHERE id=?", (name, price, description, item_id))
    conn.commit()


def delete_menu_item(conn, item_id):
    c = conn.cursor()
    c.execute("DELETE FROM menu WHERE id=?", (item_id,))
    conn.commit()


# ---------- App UI ----------

class FoodOrderingApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{HOTEL_NAME} — Online Ordering")
        self.conn = init_db()
        self.cart = {}  # item_id -> {id, name, price, qty}

        self.setup_ui()
        self.load_menu()

    def setup_ui(self):
        # Top frame: title
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)
        title = ttk.Label(top, text=HOTEL_NAME, font=(None, 20, "bold"))
        title.pack()

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: Menu list
        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        menu_label = ttk.Label(left, text="Menu")
        menu_label.pack(anchor=tk.W)

        # SHOW name column explicitly so the name appears
        self.menu_tree = ttk.Treeview(
            left,
            columns=("name", "price", "desc"),
            show="headings",
            selectmode="browse",
            height=14
        )
        self.menu_tree.heading("name", text="Item")
        self.menu_tree.heading("price", text="Price")
        self.menu_tree.heading("desc", text="Description")
        self.menu_tree.column("name", width=180, anchor=tk.W)
        self.menu_tree.column("price", width=80, anchor=tk.CENTER)
        self.menu_tree.column("desc", width=240, anchor=tk.W)
        self.menu_tree.pack(fill=tk.BOTH, expand=True)
        self.menu_tree.bind("<Double-1>", self.on_menu_double)

        qty_frame = ttk.Frame(left)
        qty_frame.pack(fill=tk.X, pady=6)
        ttk.Label(qty_frame, text="Quantity:").pack(side=tk.LEFT)
        self.qty_spin = ttk.Spinbox(qty_frame, from_=1, to=50, width=5)
        self.qty_spin.set(1)
        self.qty_spin.pack(side=tk.LEFT, padx=6)

        add_btn = ttk.Button(qty_frame, text="Add to Cart", command=self.add_to_cart)
        add_btn.pack(side=tk.LEFT, padx=6)

        # Buttons to manage menu
        manage_frame = ttk.Frame(left)
        manage_frame.pack(fill=tk.X, pady=6)
        ttk.Button(manage_frame, text="Add Menu Item", command=self.add_menu_item_prompt).pack(side=tk.LEFT)
        ttk.Button(manage_frame, text="Refresh Menu", command=self.load_menu).pack(side=tk.LEFT, padx=6)
        ttk.Button(manage_frame, text="Delete Selected Menu Item", command=self.delete_selected_menu_item).pack(side=tk.LEFT, padx=6)

        # Right: Cart and actions
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,0))

        cart_label = ttk.Label(right, text="Cart")
        cart_label.pack(anchor=tk.W)

        # CART now has the item name column explicitly
        self.cart_tree = ttk.Treeview(
            right,
            columns=("name", "qty", "price", "total"),
            show="headings",
            height=12
        )
        self.cart_tree.heading("name", text="Item")
        self.cart_tree.heading("qty", text="Qty")
        self.cart_tree.heading("price", text="Unit Price")
        self.cart_tree.heading("total", text="Total")
        self.cart_tree.column("name", width=180, anchor=tk.W)
        self.cart_tree.column("qty", width=50, anchor=tk.CENTER)
        self.cart_tree.column("price", width=90, anchor=tk.CENTER)
        self.cart_tree.column("total", width=90, anchor=tk.CENTER)
        self.cart_tree.pack(fill=tk.BOTH, expand=True)

        cart_btn_frame = ttk.Frame(right)
        cart_btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(cart_btn_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT)
        ttk.Button(cart_btn_frame, text="Clear Cart", command=self.clear_cart).pack(side=tk.LEFT, padx=6)

        summary_frame = ttk.Frame(right)
        summary_frame.pack(fill=tk.X, pady=6)
        self.total_var = tk.StringVar(value="Total: ₹0.00")
        ttk.Label(summary_frame, textvariable=self.total_var, font=(None,12,"bold")).pack(anchor=tk.E)

        action_frame = ttk.Frame(right)
        action_frame.pack(fill=tk.X, pady=6)
        ttk.Button(action_frame, text="Order Summary", command=self.show_summary).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="Generate Bill", command=self.generate_bill).pack(side=tk.LEFT, padx=6)

    def load_menu(self):
        for r in self.menu_tree.get_children():
            self.menu_tree.delete(r)
        rows = fetch_menu(self.conn)
        for row in rows:
            item_id, name, price, desc = row
            # Insert name explicitly into values so it shows
            self.menu_tree.insert("", tk.END, iid=str(item_id), values=(name, f"₹{price:.2f}", desc))

    def on_menu_double(self, event):
        # Show quick details and prompt to add
        sel = self.menu_tree.selection()
        if not sel:
            return
        iid = sel[0]
        item = self.menu_tree.item(iid)
        name, price_text, desc = item.get('values')
        messagebox.showinfo("Item Details", f"{name}\n\n{desc}\n\nPrice: {price_text}")

    def add_to_cart(self):
        sel = self.menu_tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Please select a menu item to add.")
            return
        iid = sel[0]
        item = self.menu_tree.item(iid)
        name = item.get('values')[0]
        price_text = item.get('values')[1]
        try:
            price = float(str(price_text).replace('₹','').strip())
        except Exception:
            messagebox.showerror("Price error", "Could not parse item price.")
            return
        try:
            qty = int(self.qty_spin.get())
            if qty < 1:
                qty = 1
        except Exception:
            qty = 1
        item_id = int(iid)
        if item_id in self.cart:
            self.cart[item_id]['qty'] += qty
        else:
            self.cart[item_id] = {'id': item_id, 'name': name, 'price': price, 'qty': qty}
        self.refresh_cart()

    def refresh_cart(self):
        for r in self.cart_tree.get_children():
            self.cart_tree.delete(r)
        total = 0.0
        for item_id, info in self.cart.items():
            qty = info['qty']
            price = info['price']
            line_total = qty * price
            total += line_total
            # Insert all columns including name so it displays fully
            self.cart_tree.insert("", tk.END, iid=str(item_id),
                                  values=(info['name'], qty, f"₹{price:.2f}", f"₹{line_total:.2f}"))
        self.total_var.set(f"Total: ₹{total:.2f}")

    def remove_selected(self):
        sel = self.cart_tree.selection()
        if not sel:
            messagebox.showinfo("Remove item", "Select item in cart to remove.")
            return
        for iid in sel:
            iid_int = int(iid)
            if iid_int in self.cart:
                del self.cart[iid_int]
        self.refresh_cart()

    def clear_cart(self):
        if not self.cart:
            return
        if not messagebox.askyesno("Clear cart", "Clear all items from cart?"):
            return
        self.cart.clear()
        self.refresh_cart()

    def show_summary(self):
        if not self.cart:
            messagebox.showinfo("Order Summary", "Cart is empty.")
            return
        lines = [f"{HOTEL_NAME} — Order Summary", "----------------------------------------"]
        total = 0.0
        for info in self.cart.values():
            line = f"{info['name']}  x{info['qty']}  @ ₹{info['price']:.2f}  = ₹{info['qty']*info['price']:.2f}"
            lines.append(line)
            total += info['qty']*info['price']
        lines.append("----------------------------------------")
        lines.append(f"Total: ₹{total:.2f}")
        messagebox.showinfo("Order Summary", "\n".join(lines))

    def generate_bill(self):
        if not self.cart:
            messagebox.showinfo("No items", "Cart is empty — nothing to bill.")
            return
        # ask customer name (optional)
        cust_name = simpledialog.askstring("Customer", "Enter customer name (optional):") or "Walk-in Customer"
        now = datetime.datetime.now()
        bill_lines = []
        bill_lines.append(f"{HOTEL_NAME}")
        bill_lines.append(f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        bill_lines.append(f"Customer: {cust_name}")
        bill_lines.append("========================================")
        total = 0.0
        for info in self.cart.values():
            line_total = info['qty']*info['price']
            bill_lines.append(f"{info['name'][:30]:30} {info['qty']:3d} x ₹{info['price']:.2f} = ₹{line_total:.2f}")
            total += line_total
        bill_lines.append("========================================")
        bill_lines.append(f"TOTAL: ₹{total:.2f}")
        bill_text = "\n".join(bill_lines)

        # Save to a file
        safe_time = now.strftime('%Y%m%d_%H%M%S')
        filename = f"bill_{safe_time}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(bill_text)

        messagebox.showinfo("Bill Generated", f"Bill saved as {filename}")
        # Optionally clear cart after billing
        if messagebox.askyesno("Clear cart?", "Clear cart after generating bill?"):
            self.cart.clear()
            self.refresh_cart()

    # ---------- Menu management dialogs ----------
    def add_menu_item_prompt(self):
        d = MenuItemDialog(self.root, title="Add Menu Item")
        if d.result:
            name, price, desc = d.result
            try:
                price_f = float(price)
            except ValueError:
                messagebox.showerror("Invalid price", "Enter a valid numeric price")
                return
            add_menu_item(self.conn, name, price_f, desc)
            messagebox.showinfo("Added", f"Added '{name}' to menu")
            self.load_menu()

    def delete_selected_menu_item(self):
        sel = self.menu_tree.selection()
        if not sel:
            messagebox.showinfo("Delete menu item", "Select a menu item to delete.")
            return
        iid = sel[0]
        name = self.menu_tree.item(iid).get('values')[0]
        if not messagebox.askyesno("Delete", f"Delete '{name}' from menu?"):
            return
        try:
            delete_menu_item(self.conn, int(iid))
            messagebox.showinfo("Deleted", f"Deleted '{name}' from menu.")
            self.load_menu()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete menu item: {e}")


class MenuItemDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.e_name = ttk.Entry(master, width=40)
        self.e_name.grid(row=0, column=1)
        ttk.Label(master, text="Price:").grid(row=1, column=0, sticky=tk.W)
        self.e_price = ttk.Entry(master, width=20)
        self.e_price.grid(row=1, column=1)
        ttk.Label(master, text="Description:").grid(row=2, column=0, sticky=tk.W)
        self.e_desc = ttk.Entry(master, width=40)
        self.e_desc.grid(row=2, column=1)
        return self.e_name

    def apply(self):
        name = self.e_name.get().strip()
        price = self.e_price.get().strip()
        desc = self.e_desc.get().strip()
        if not name or not price:
            self.result = None
            return
        self.result = (name, price, desc)


if __name__ == '__main__':
    root = tk.Tk()
    app = FoodOrderingApp(root)
    root.mainloop()


# to run this output click on run it can open website