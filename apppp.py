from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim
import razorpay

app = Flask(__name__)

# Razorpay test credentials (replace with your own)
razorpay_client = razorpay.Client(auth=("rzp_test_xxxxxxxx", "your_secret_key"))

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Geolocation setup
geolocator = Nominatim(user_agent="disaster_app")

# -----------------------------
# Database Models
# -----------------------------
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    disaster = db.Column(db.String(100))
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    description = db.Column(db.Text)
    total_donations = db.Column(db.Float, default=0.0)
    donations = db.relationship('Donation', backref='report', lazy=True)

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    message = db.Column(db.Text)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))

# -----------------------------
# Routes
# -----------------------------
@app.route('/')
def home():
    reports = Report.query.all()

    # Convert SQLAlchemy objects to dicts (for map display or JSON)
    report_data = []
    for r in reports:
        report_data.append({
            'id': r.id,
            'name': r.name,
            'disaster': r.disaster,
            'location': r.location,
            'latitude': r.latitude,
            'longitude': r.longitude,
            'description': r.description,
            'total_donations': r.total_donations
        })

    return render_template('index.html', reports=reports, report_data=report_data)


@app.route('/report', methods=['POST'])
def report():
    name = request.form['name']
    disaster_type = request.form['disaster']
    location = request.form['location']
    description = request.form['description']

    latitude, longitude = None, None
    try:
        geo = geolocator.geocode(location)
        if geo:
            latitude, longitude = geo.latitude, geo.longitude
    except Exception as e:
        print("Geocoding error:", e)

    report = Report(
        name=name,
        disaster=disaster_type,
        location=location,
        latitude=latitude,
        longitude=longitude,
        description=description
    )

    db.session.add(report)
    db.session.commit()
    return redirect('/')


@app.route('/donate/<int:report_id>')
def donate_page(report_id):
    report = Report.query.get_or_404(report_id)
    order_amount = 100 * 50  # Example amount (in paise)
    order_currency = 'INR'
    order_receipt = f'order_rcptid_{report_id}'
    order = razorpay_client.order.create(dict(amount=order_amount, currency=order_currency, receipt=order_receipt))
    return render_template('donate.html', report=report, order=order)


@app.route('/donate/<int:report_id>', methods=['POST'])
def donate(report_id):
    donor_name = request.form['donor_name']
    amount = float(request.form['amount'])
    message = request.form['message']

    donation = Donation(donor_name=donor_name, amount=amount, message=message, report_id=report_id)
    db.session.add(donation)

    report = Report.query.get(report_id)
    report.total_donations += amount
    db.session.commit()

    return redirect(url_for('success', rid=report_id))


@app.route('/success/<int:rid>')
def success(rid):
    report = Report.query.get(rid)
    return render_template('success.html', report=report)

# -----------------------------
# Run Flask App
# -----------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
