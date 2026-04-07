from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from sqlalchemy import func

app = Flask(__name__)

# ✅ SECRET KEY (Render compatible)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# Upload folder
UPLOAD_FOLDER = "static/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ DATABASE (Render compatible)
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

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    farmer = db.Column(db.String(100))
    image = db.Column(db.String(200))

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    user = db.Column(db.String(100))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    total = db.Column(db.Integer)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer = db.Column(db.String(100))
    user = db.Column(db.String(100))
    stars = db.Column(db.Integer)

# ✅ Chat Model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100))
    receiver = db.Column(db.String(100))
    text = db.Column(db.String(500))

# -------------------- ROUTES --------------------

@app.route("/")
def home():
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
            role=request.form['role']
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
            image=filename
        )

        db.session.add(product)
        db.session.commit()
        return redirect("/")

    return render_template("add_product.html")

# -------------------- CART --------------------

@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    if 'user' not in session:
        return redirect("/login")

    product = Product.query.get_or_404(id)

    cart_item = Cart(
        product_name=product.name,
        price=product.price,
        user=session['user']
    )

    db.session.add(cart_item)
    db.session.commit()
    return redirect("/")

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

# -------------------- PAYMENT --------------------

@app.route("/place_order")
def place_order():
    if 'user' not in session:
        return redirect("/login")

    items = Cart.query.filter_by(user=session['user']).all()
    total = sum(item.price for item in items)

    session['total'] = total

    return render_template("payment.html", total=total)

@app.route("/order_success")
def order_success():
    if 'user' not in session:
        return redirect("/login")

    total = session.get('total', 0)

    order = Order(user=session['user'], total=total)
    db.session.add(order)

    items = Cart.query.filter_by(user=session['user']).all()
    for item in items:
        db.session.delete(item)

    db.session.commit()

    return "🎉 Payment Successful & Order Placed!"

# -------------------- RATING --------------------

@app.route("/rate/<farmer>/<int:stars>")
def rate(farmer, stars):
    if 'user' not in session:
        return redirect("/login")

    rating = Rating(
        farmer=farmer,
        user=session['user'],
        stars=stars
    )

    db.session.add(rating)
    db.session.commit()

    return redirect("/")

# -------------------- CHAT --------------------

@app.route("/chat/<farmer>", methods=["GET", "POST"])
def chat(farmer):
    if 'user' not in session:
        return redirect("/login")

    current_user = session['user']

    if request.method == "POST":
        msg = request.form['message']

        new_msg = Message(
            sender=current_user,
            receiver=farmer,
            text=msg
        )

        db.session.add(new_msg)
        db.session.commit()

    # ✅ Sorted messages (important fix)
    messages = Message.query.filter(
        ((Message.sender == current_user) & (Message.receiver == farmer)) |
        ((Message.sender == farmer) & (Message.receiver == current_user))
    ).order_by(Message.id.asc()).all()

    return render_template("chat.html", messages=messages, farmer=farmer)

# -------------------- INBOX --------------------

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

# -------------------- RUN --------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)