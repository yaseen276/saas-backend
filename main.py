from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, Project, Subscription, Payment, Notification
from auth import hash_password, verify_password, create_token, verify_token, generate_otp
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import stripe
from sqlalchemy import func

# -----------------------------
# STRIPE CONFIG
# -----------------------------
import os
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# -----------------------------
# DB Setup
# -----------------------------
#Base.metadata.create_all(bind=engine)

app = FastAPI(title="SaaS Backend")

# -----------------------------
# Security
# -----------------------------
api_key_scheme = APIKeyHeader(name="Authorization", auto_error=True)

# -----------------------------
# DB Dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# AUTH
# -----------------------------
def get_current_user(token: str = Depends(api_key_scheme), db: Session = Depends(get_db)):
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token_value = token.split(" ")[1]
    email = verify_token(token_value)

    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# -----------------------------
# ADMIN CHECK
# -----------------------------
def get_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# -----------------------------
# SCHEMAS
# -----------------------------
class RegisterModel(BaseModel):
    email: str
    password: str

class OTPVerifyModel(BaseModel):
    email: str
    otp: str

class ProjectModel(BaseModel):
    name: str
    description: str = None

class AdminNotificationModel(BaseModel):
    title: str
    message: str
    user_id: int = None

# -----------------------------
# BASIC
# -----------------------------
@app.get("/")
def root():
    return {"message": "API Working"}

# -----------------------------
# REGISTER + OTP
# -----------------------------
@app.post("/register")
def register(data: RegisterModel, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="User already exists")

    otp = generate_otp()

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        otp_code=otp,
        otp_verified=False
    )

    db.add(user)
    db.commit()

    return {"message": "OTP generated", "otp": otp}

@app.post("/verify-otp")
def verify_otp(data: OTPVerifyModel, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.otp_verified = True
    user.otp_code = None
    db.commit()

    token = create_token({"sub": user.email})

    return {"access_token": token}

@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.otp_verified:
        raise HTTPException(status_code=400, detail="Verify OTP first")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = create_token({"sub": user.email})

    return {"access_token": token}

@app.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}

# -----------------------------
# PROJECTS CRUD
# -----------------------------
@app.post("/projects")
def create_project(data: ProjectModel,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    plan = sub.plan if sub else "free"

    count = db.query(Project).filter(Project.owner_id == current_user.id).count()

    if plan == "free" and count >= 3:
        raise HTTPException(status_code=403, detail="Free plan limit reached")

    project = Project(name=data.name, description=data.description, owner_id=current_user.id)
    db.add(project)

    notification = Notification(
        user_id=current_user.id,
        title="Project Created",
        message=f"{data.name} created"
    )
    db.add(notification)

    db.commit()

    return {"message": "Project created"}

@app.get("/projects")
def get_projects(current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.owner_id == current_user.id).all()

@app.put("/projects/{id}")
def update_project(id: int, data: ProjectModel,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):

    project = db.query(Project).filter(
        Project.id == id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = data.name
    project.description = data.description
    db.commit()

    return {"message": "Project updated"}

@app.delete("/projects/{id}")
def delete_project(id: int,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):

    project = db.query(Project).filter(
        Project.id == id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"message": "Project deleted"}

# -----------------------------
# SUBSCRIPTION
# -----------------------------
@app.post("/subscription")
def create_subscription(current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):

    sub = Subscription(
        user_id=current_user.id,
        plan="free",
        status="active"
    )

    db.add(sub)

    db.add(Notification(
        user_id=current_user.id,
        title="Subscription Created",
        message="Free plan activated"
    ))

    db.commit()

    return {"message": "Free subscription created"}

@app.get("/subscription")
def get_subscription(current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()

    if not sub:
        return {"plan": "free", "status": "active"}

    return {
        "plan": sub.plan,
        "status": sub.status
    }

# -----------------------------
# STRIPE PAYMENT
# -----------------------------
@app.post("/pay")
def pay(current_user: User = Depends(get_current_user)):

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Pro Plan"},
                "unit_amount": 50000,
            },
            "quantity": 1,
        }],
        metadata={"user_id": str(current_user.id)},
        success_url="http://127.0.0.1:8000/docs",
        cancel_url="http://127.0.0.1:8000/docs",
    )

    return {"url": session.url}

# -----------------------------
# WEBHOOK
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]
        user_id = int(session["metadata"]["user_id"])

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return {"error": "User not found"}

        payment = Payment(
            user_id=user.id,
            amount=session["amount_total"] / 100,
            currency=session["currency"],
            payment_status="success"
        )
        db.add(payment)

        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()

        if sub:
            sub.plan = "pro"
            sub.status = "active"
        else:
            sub = Subscription(user_id=user.id, plan="pro", status="active")
            db.add(sub)

        db.add(Notification(
            user_id=user.id,
            title="Payment Successful",
            message="Upgraded to PRO plan"
        ))

        db.commit()

    return {"status": "success"}

# -----------------------------
# USER PAYMENTS & NOTIFICATIONS
# -----------------------------
@app.get("/payments")
def get_payments(current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return db.query(Payment).filter(Payment.user_id == current_user.id).all()

@app.get("/notifications")
def get_notifications(current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == current_user.id).all()

# -----------------------------
# ADMIN APIs
# -----------------------------
@app.get("/admin/users")
def get_all_users(admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/admin/payments")
def get_all_payments(admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    return db.query(Payment).all()

@app.get("/admin/subscriptions")
def get_all_subscriptions(admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    return db.query(Subscription).all()

@app.put("/admin/user/{user_id}/plan")
def update_user_plan(user_id: int, plan: str,
                     admin: User = Depends(get_admin),
                     db: Session = Depends(get_db)):

    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()

    if not sub:
        sub = Subscription(user_id=user_id, plan=plan, status="active")
        db.add(sub)
    else:
        sub.plan = plan

    db.add(Notification(
        user_id=user_id,
        title="Plan Updated",
        message=f"Your plan changed to {plan}"
    ))

    db.commit()

    return {"message": "Plan updated"}

# -----------------------------
# EXTRA ADMIN FEATURES
# -----------------------------
@app.put("/admin/user/{user_id}/activate")
def activate_user(user_id: int, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    user.is_active = True

    db.add(Notification(
        user_id=user.id,
        title="Account Activated",
        message="Your account has been activated by admin"
    ))

    db.commit()
    return {"message": "User activated"}

@app.put("/admin/user/{user_id}/deactivate")
def deactivate_user(user_id: int, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    user.is_active = False

    db.add(Notification(
        user_id=user.id,
        title="Account Deactivated",
        message="Your account has been deactivated by admin"
    ))

    db.commit()
    return {"message": "User deactivated"}

@app.post("/admin/notify")
def send_notification(data: AdminNotificationModel,
                      admin: User = Depends(get_admin),
                      db: Session = Depends(get_db)):

    users = db.query(User).all() if not data.user_id else db.query(User).filter(User.id == data.user_id).all()

    for u in users:
        db.add(Notification(user_id=u.id, title=data.title, message=data.message))

    db.commit()

    return {"message": f"Notification sent to {len(users)} user(s)"}

@app.get("/admin/subscriptions/mapping")
def get_user_subscription_mapping(admin: User = Depends(get_admin),
                                  db: Session = Depends(get_db)):

    subs = db.query(Subscription, User.email).join(User).all()

    result = []
    for sub, email in subs:
        result.append({
            "user": email,
            "plan": sub.plan,
            "status": sub.status,
            "current_period_end": sub.current_period_end
        })

    return result

@app.get("/admin/analytics")
def get_analytics(admin: User = Depends(get_admin),
                  db: Session = Depends(get_db)):

    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_status == "success"
    ).scalar() or 0

    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_revenue": total_revenue
    }