




from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client
from werkzeug.security import check_password_hash
import uuid

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = "hackathon_secret_key"

SUPABASE_URL = "https://ofyhamnfkpgtnujmqgiv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9meWhhbW5ma3BndG51am1xZ2l2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTM4MzIyMiwiZXhwIjoyMDgwOTU5MjIyfQ.YLtXejHgDlLr1es0suj06eP1-WUp7kBriaLgSVf37Ds"   # ⚠️ keep secret
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- ROOT ROUTE ----------------
@app.route("/")
def home():
    # Redirect root URL to hospital login
    return redirect("/hospital/login")

# ---------------- HOSPITAL LOGIN ----------------
@app.route("/hospital/login", methods=["GET", "POST"])
def hospital_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        hospital_data = (
            supabase.table("hospitals")
            .select("*")
            .eq("email", email)
            .execute()
            .data
        )

        # Check hospital exists
        if not hospital_data:
            flash("❌ Invalid hospital credentials", "error")
            return redirect("/hospital/login")

        hospital = hospital_data[0]

        # ✅ PLAIN TEXT PASSWORD CHECK
        if hospital["password"] != password:
            flash("❌ Invalid hospital credentials", "error")
            return redirect("/hospital/login")

        # ✅ Store hospital session
        session["hospital_id"] = hospital["id"]
        session["hospital_name"] = hospital["hospital_name"]
        session["hospital_district_id"] = hospital["district_id"]
        session["hospital_constituency_id"] = hospital["constituency_id"]
        session["hospital_place_id"] = hospital["place_id"]

        return redirect("/hospital/dashboard")

    return render_template("hospital_login.html")


@app.route("/hospital/dashboard")
def hospital_dashboard():
    if "hospital_id" not in session:
        return redirect("/hospital/login")

    return render_template(
        "hospital_dashboard.html",
        hospital=session["hospital_name"]
    )

@app.route("/hospital/donors")
def hospital_donors():
    if "hospital_id" not in session:
        return redirect("/hospital/login")

    donors = (
        supabase.table("users")
        .select("name,age,blood_group,phone")
        .eq("place_id", session["hospital_place_id"])
        .execute()
        .data
    )

    return render_template(
        "hospital_donors.html",
        donors=donors
    )
import smtplib
from email.message import EmailMessage

EMAIL_ADDRESS = "d35001122@gmail.com"
EMAIL_PASSWORD = "jizq ouay ttev iyeq"

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

@app.route("/hospital/request-blood", methods=["GET", "POST"])
def hospital_request_blood():
    if "hospital_id" not in session:
        return redirect("/hospital/login")

    if request.method == "POST":
        patient_name = request.form.get("patient_name")
        patient_age = request.form.get("patient_age")
        blood_group = request.form.get("blood_group")
        urgency_time = request.form.get("urgency_time")

        if not all([patient_name, patient_age, blood_group, urgency_time]):
            flash("❌ Fill all details", "error")
            return redirect("/hospital/request-blood")

        # 1️⃣ Insert request into database
        request_data = {
            "id": str(uuid.uuid4()),
            "hospital_id": session["hospital_id"],
            "patient_name": patient_name,
            "patient_age": int(patient_age),
            "blood_group": blood_group,
            "urgency_time": urgency_time,
            "place_id": session["hospital_place_id"]
        }

        supabase.table("blood_requests").insert(request_data).execute()

        # 🔹 Fetch hospital contact number DIRECTLY from hospitals table
        hospital_data = (
            supabase.table("hospitals")
            .select("hospital_name, contact_number")
            .eq("id", session["hospital_id"])
            .execute()
            .data
        )

        hospital_name = hospital_data[0]["hospital_name"]
        hospital_phone = hospital_data[0]["contact_number"]

        # 2️⃣ Fetch donors in same place
        donors = (
            supabase.table("users")
            .select("email")
            .eq("place_id", session["hospital_place_id"])
            .eq("blood_group", blood_group)
            .execute()
            .data
        )

        # 3️⃣ Send email to each donor
        for donor in donors:
            send_email(
                donor["email"],
                "🩸 Urgent Blood Requirement",
                f"""
Patient Name: {patient_name}
Age: {patient_age}
Blood Group Needed: {blood_group}
Urgency: {urgency_time}

Hospital: {hospital_name}
📞 Contact: {hospital_phone}

Please respond immediately if you can donate.
"""
            )

        flash("✅ Blood request sent to all nearby donors", "success")
        return redirect("/hospital/dashboard")

    return render_template("hospital_request_blood.html")

@app.route("/hospital/requests")
def hospital_requests():
    if "hospital_id" not in session:
        return redirect("/hospital/login")

    hospital_id = session["hospital_id"]

    requests = (
        supabase.table("blood_requests")
        .select("*")
        .eq("hospital_id", hospital_id)
        .execute()
        .data
    )

    return render_template("hospital_requests.html", requests=requests)
@app.route("/hospital/request/<request_id>/responses")
def hospital_request_responses(request_id):
    if "hospital_id" not in session:
        return redirect("/hospital/login")

    # Fetch responses with donor profiles
    responses = (
        supabase.table("blood_request_responses")
        .select(
            "response, users(name, age, blood_group, phone)"
        )
        .eq("blood_request_id", request_id)
        .execute()
        .data
    )

    return render_template(
        "hospital_request_responses.html",
        responses=responses
    )




# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
