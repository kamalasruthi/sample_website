from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message as MailMessage
from datetime import datetime

app = Flask(__name__)

# ========================
# CONFIGURATION
# ========================

app.config['SECRET_KEY'] = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail Config (Use Gmail App Password)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'

db = SQLAlchemy(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"


# ========================
# DATABASE MODELS
# ========================

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="Unread")
    date = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ========================
# PUBLIC ROUTES
# ========================

@app.route('/')
def home():
    services = Service.query.all()
    return render_template("index.html", services=services)


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/services')
def services():
    services = Service.query.all()
    return render_template("services.html", services=services)


@app.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        new_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        db.session.add(new_message)
        db.session.commit()

        # Send Email (optional)
        try:
            msg = MailMessage(
                subject=subject,
                sender=app.config['MAIL_USERNAME'],
                recipients=[app.config['MAIL_USERNAME']],
                body=f"From: {name}\nEmail: {email}\n\n{message}"
            )
            mail.send(msg)
        except Exception as e:
            print("Mail error:", e)

        flash("Message sent successfully!", "success")
        return redirect(url_for('contact'))

    return render_template("contact.html")


# ========================
# ADMIN AUTHENTICATION
# ========================

@app.route('/admin/login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            flash("Login successful!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template("admin/login.html")


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for('admin_login'))


# ========================
# ADMIN DASHBOARD
# ========================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    total_services = Service.query.count()
    total_messages = ContactMessage.query.count()
    unread_messages = ContactMessage.query.filter_by(status="Unread").count()

    return render_template(
        "admin/dashboard.html",
        total_services=total_services,
        total_messages=total_messages,
        unread_messages=unread_messages
    )


# ========================
# MANAGE SERVICES
# ========================

@app.route('/admin/services', methods=["GET", "POST"])
@login_required
def admin_services():
    if request.method == "POST":
        title = request.form['title']
        description = request.form['description']

        new_service = Service(title=title, description=description)
        db.session.add(new_service)
        db.session.commit()

        flash("Service added successfully!", "success")

    services = Service.query.all()
    return render_template("admin/services.html", services=services)


@app.route('/admin/service/delete/<int:id>')
@login_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash("Service deleted", "warning")
    return redirect(url_for('admin_services'))


# ========================
# MANAGE MESSAGES WITH PAGINATION
# ========================

@app.route('/admin/messages')
@login_required
def admin_messages():
    page = request.args.get('page', 1, type=int)

    messages = ContactMessage.query.order_by(
        ContactMessage.date.desc()
    ).paginate(page=page, per_page=5)

    return render_template("admin/messages.html", messages=messages)


@app.route('/admin/message/read/<int:id>')
@login_required
def mark_as_read(id):
    message = ContactMessage.query.get_or_404(id)
    message.status = "Read"
    db.session.commit()
    return redirect(url_for('admin_messages'))


@app.route('/admin/message/delete/<int:id>')
@login_required
def delete_message(id):
    message = ContactMessage.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    flash("Message deleted", "danger")
    return redirect(url_for('admin_messages'))


# ========================
# INITIAL DATABASE SETUP (Flask 3 Compatible)
# ========================

with app.app_context():
    db.create_all()

    # Create default admin if not exists
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(
            username="admin",
            password=generate_password_hash("admin123")
        )
        db.session.add(admin)
        db.session.commit()


# ========================
# RUN APP
# ========================

if __name__ == "__main__":
    app.run(debug=True)