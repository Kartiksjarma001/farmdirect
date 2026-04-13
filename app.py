from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from sqlalchemy import func



app = Flask(__name__)

# ✅ SECRET KEY
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# Upload folder
UPLOAD_FOLDER = "static/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL") or 'sqlite:///farm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------- MODELS --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    role = db.Column(db.String(10))
    location = db.Column(db.String(100))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    farmer = db.Column(db.String(100))
    image = db.Column(db.String(200))
    location = db.Column(db.String(100))   # ✅ added

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    user = db.Column(db.String(100))
    farmer =db.Column(db.String(100))


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer = db.Column(db.String(100))
    user = db.Column(db.String(100))
    stars = db.Column(db.Integer)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100))
    receiver = db.Column(db.String(100))
    text = db.Column(db.String(500))

# 🚚 Truck (real data)
class Truck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_name = db.Column(db.String(100))
    route_from = db.Column(db.String(100))
    route_to = db.Column(db.String(100))
    date = db.Column(db.String(50))
    slots = db.Column(db.Integer)


# 📦 Booking (real tracking)
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer = db.Column(db.String(100))
    truck_id = db.Column(db.Integer)
    product = db.Column(db.String(100))

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    farmer = db.Column(db.String(100))
    product = db.Column(db.String(100))
    total = db.Column(db.Integer)
    status = db.Column(db.String(20), default="Pending")
    truck_id = db.Column(db.Integer)   # ✅ IMPORTANT
    eta = db.Column(db.String(50))

class TruckLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    truck_id = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)    


# -------------------- HOME (LOCATION FILTER) --------------------

@app.route("/")
def home():
    search_location = request.args.get("location")

    if search_location:
        products = Product.query.filter(
            Product.location.ilike(f"%{search_location}%")
        ).all()
    else:
        products = Product.query.all()

    ratings = db.session.query(
        Rating.farmer,
        func.avg(Rating.stars)
    ).group_by(Rating.farmer).all()

    rating_dict = {r[0]: round(r[1], 1) for r in ratings}

    return render_template(
        "index.html",
        products=products,
        ratings=rating_dict,
        user=session.get('user'),
        role=session.get('role')
    )

# -------------------- AUTH --------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=request.form['password'],
            role=request.form['role'],
            location=request.form.get('location', 'unknown')   # ✅ FIXED
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            email=request.form['email'],
            password=request.form['password']
        ).first()

        if user:
            session['user'] = user.name
            session['role'] = user.role
            session['location'] = user.location   # ✅ store
            return redirect("/")
        else:
            return "Invalid credentials"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -------------------- PRODUCT --------------------

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if 'user' not in session:
        return redirect("/login")

    if session.get('role') != "farmer":
        return "Only farmers can add products"

    if request.method == "POST":
        file = request.files['image']

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        product = Product(
            name=request.form['name'],
            price=request.form['price'],
            farmer=session['user'],
            image=filename,
            location=request.form.get('location', 'unknown')   # ✅ SAFE FIX
        )

        db.session.add(product)
        db.session.commit()
        return redirect("/")

    return render_template("add_product.html")

#-------------------truck-----------------#

@app.route("/add_truck", methods=["GET", "POST"])
def add_truck():
    if 'user' not in session:
        return redirect("/login")

    if request.method == "POST":
        truck = Truck(
            driver_name=request.form['driver'],
            route_from=request.form['from'],
            route_to=request.form['to'],
            date=request.form['date'],
            slots=int(request.form['slots']),
        )

        db.session.add(truck)
        db.session.commit()

        return redirect("/delivery")

    return render_template("truck.html")

# -------------------- CART --------------------

@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    if 'user' not in session:
        return redirect("/login")

    product = Product.query.get_or_404(id)

    cart_item = Cart(
    product_id=product.id,
    product_name=product.name,
    price=product.price,
    user=session['user'],
    farmer=product.farmer   # ✅ IMPORTANT

)

    db.session.add(cart_item)
    db.session.commit()

    return redirect("/")




@app.route("/order_success")
def order_success():
    if 'user' not in session:
        return redirect("/login")

    total = session.get('total', 0)

    order = Order(user=session['user'], total=total)
    db.session.add(order)

    # cart clear
    items = Cart.query.filter_by(user=session['user']).all()
    for item in items:
        db.session.delete(item)

    db.session.commit()

    return render_template("success.html", total=total)


@app.route("/cart")
def cart():
    if 'user' not in session:
        return redirect("/login")

    items = Cart.query.filter_by(user=session['user']).all()
    total = sum(item.price for item in items)

    return render_template("cart.html", items=items, total=total)


@app.route("/remove_from_cart/<int:id>")
def remove_from_cart(id):
    item = Cart.query.get_or_404(id)

    db.session.delete(item)
    db.session.commit()

    return redirect("/cart")
#----------------inbox---------------#

@app.route("/inbox")
def inbox():
    if 'user' not in session:
        return redirect("/login")

    current_user = session['user']

    sent = db.session.query(Message.receiver).filter_by(sender=current_user).distinct()
    received = db.session.query(Message.sender).filter_by(receiver=current_user).distinct()

    users = set()

    for u in sent:
        users.add(u[0])

    for u in received:
        users.add(u[0])

    return render_template("inbox.html", users=users)

# -------------------- CHAT --------------------

@app.route("/chat/<farmer>", methods=["GET", "POST"])
def chat(farmer):
    if 'user' not in session:
        return redirect("/login")

    current_user = session['user']

    if request.method == "POST":
        msg = request.form.get('message')

        if msg:   # ✅ empty msg avoid
            new_msg = Message(
                sender=current_user,
                receiver=farmer,
                text=msg
            )
            db.session.add(new_msg)
            db.session.commit()

    messages = Message.query.filter(
        ((Message.sender == current_user) & (Message.receiver == farmer)) |
        ((Message.sender == farmer) & (Message.receiver == current_user))
    ).order_by(Message.id.asc()).all()

    return render_template("chat.html", messages=messages, farmer=farmer)

# -------------------- RATING --------------------

@app.route("/rate/<farmer>", methods=["POST"])
def rate(farmer):
    if 'user' not in session:
        return redirect("/login")

    stars = request.form.get("stars")

    if not stars:
        return "Invalid rating ❌"

    rating = Rating(
        farmer=farmer,
        user=session['user'],
        stars=int(stars)
    )

    db.session.add(rating)
    db.session.commit()

    return redirect("/")
#-----------------delivery-----------------#

@app.route("/delivery")
def delivery():
    if 'user' not in session:
        return redirect("/login")

    trucks = Truck.query.all()

    # 👇 Farmer ke products
    products = Product.query.filter_by(farmer=session['user']).all()

    return render_template("delivery.html", trucks=trucks, products=products)


#--------------------slot bokking-----------------#
@app.route("/book_truck/<int:truck_id>", methods=["POST"])
def book_truck(truck_id):
    if 'user' not in session:
        return redirect("/login")

    product = request.form.get('product')

    if not product:
        return "Product not selected ❌"

    truck = Truck.query.get_or_404(truck_id)

    if truck.slots == 0:
        return "No slots available ❌"

    truck.slots -= 1

    # ✅ Booking save
    booking = Booking(
        farmer=session['user'],
        truck_id=truck_id,
        product=product
    )
    db.session.add(booking)

    # 🔥 YAHI ADD KARNA HAI (IMPORTANT)
    order = Order.query.filter_by(
        product=product,
        
    ).first()

    if order:
        order.truck_id = truck_id
        order.status = "Shipped"
        order.eta = "2 hours"#----------------only for demo -----------#

    # ✅ FINAL SAVE
    db.session.commit()

    return redirect("/my_bookings")





@app.route("/my_bookings")
def my_bookings():
    if 'user' not in session:
        return redirect("/login")

    bookings = Booking.query.filter_by(farmer=session['user']).all()

    return render_template("my_bookings.html", bookings=bookings)

#---------------------order----------#

@app.route("/place_order", methods=["GET", "POST"])
def place_order():
    if 'user' not in session:
        return redirect("/login")

    items = Cart.query.filter_by(user=session['user']).all()

    if not items:
        return "Cart empty ❌"

    total = sum(item.price for item in items)

    if request.method == "POST":
        for item in items:

            # ✅ SAFE FETCH
            product = Product.query.get(item.product_id)

            # ❌ अगर product नहीं मिला
            if not product:
                print("ERROR: Product not found for cart item", item.id)
                continue

            print("DEBUG:", product.name, product.farmer)

            order = Order(
                user=session['user'],
                farmer=product.farmer,
                product=product.name,
                total=product.price,
                status="Pending"
            )

            db.session.add(order)
            db.session.delete(item)

        db.session.commit()
        return redirect("/order_success")

    return render_template("payment.html", total=total)

#-------------------acceptorder-------------#
@app.route("/accept_order/<int:id>")
def accept_order(id):
    order = Order.query.get_or_404(id)

    order.status = "Accepted"

    # message send
    msg = Message(
        sender=order.farmer,
        receiver=order.user,
        text="✅ Your order is accepted. Delivery on the way 🚚"
    )

    db.session.add(msg)
    db.session.commit()

    return redirect("/")


#---------------------farmer route-------------------#
@app.route("/farmer_orders")
def farmer_orders():
    if 'user' not in session:
        return redirect("/login")

    print("LOGIN FARMER:", session['user'])  # 👈 ADD

    orders = Order.query.filter_by(farmer=session['user']).all()

    print("ALL ORDERS", orders)  # 👈 ADD

    trucks = Truck.query.all()

    return render_template("farmer_orders.html", orders=orders, trucks=trucks)

#-----------------assign---------------------#
@app.route("/assign_truck/<int:id>", methods=["POST"])
def assign_truck(id):
    order = Order.query.get_or_404(id)

    truck_id = request.form.get("truck_id")

    order.truck_id = int(truck_id)
    order.status = "Shipped"

    # 🔥 MESSAGE SEND
    msg = Message(
        sender=order.farmer,
        receiver=order.user,
        text=f"🚚 Your order is out for delivery. Track here: /track/{truck_id}"
    )

    db.session.add(msg)
    db.session.commit()

    return redirect("/farmer_orders")

#---------------------farmer route-------------#
@app.route("/deliver_order/<int:id>")
def deliver_order(id):
    order = Order.query.get_or_404(id)

    order.status = "Delivered"

    msg = Message(
        sender=order.farmer,
        receiver=order.user,
        text="🎉 Your order has been delivered successfully!"
    )

    db.session.add(msg)
    db.session.commit()

    return redirect("/farmer_orders")

#-----------------------orderpagefarmerside---------------------#
@app.route("/my_orders")
def my_orders():
    if 'user' not in session:
        return redirect("/login")

    orders = Order.query.filter_by(user=session['user']).all()

    return render_template("my_orders.html", orders=orders)


#--------------trucklocation-------------#
@app.route("/update_location/<int:truck_id>")
def update_location(truck_id):
    lat = request.args.get("lat")
    lng = request.args.get("lng")

    loc = TruckLocation(
        truck_id=truck_id,
        latitude=float(lat),
        longitude=float(lng)
    )

    db.session.add(loc)
    db.session.commit()

    return "Location Updated"

#-------------------track------------------#
@app.route("/track/<int:truck_id>")
def track(truck_id):
    loc = TruckLocation.query.filter_by(truck_id=truck_id).order_by(TruckLocation.id.desc()).first()

    return render_template("track.html", loc=loc)

#------------------productroute ----------------#
@app.route("/product/<int:id>")
def product_detail(id):
    try:
        product = product[id-1]
        return render_template("product_details.html", product=product)
    except:
        return "Product not found"

# -------------------- RUN --------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)