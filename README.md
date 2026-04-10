SaaS Project Management Backend

📌 Overview

This project is a backend system for a subscription-based SaaS Project Management platform built using FastAPI. It supports user and admin functionalities including authentication, project management, subscription handling, payments, and notifications.

⸻

🛠️ Tech Stack
	•	FastAPI
	•	SQLAlchemy
	•	MySQL
	•	Alembic (Database Migrations)
	•	JWT Authentication
	•	OTP Verification
	•	Stripe (Payments & Webhooks)

⸻

⚙️ Features

👤 User Features
	•	User Registration with Email OTP verification
	•	Login with JWT Authentication
	•	Create, update, delete projects
	•	View projects
	•	Subscription management (Free & Pro)
	•	Stripe payment integration
	•	View payment history
	•	In-app notifications

⸻

👨‍💼 Admin Features
	•	View all users
	•	Activate/Deactivate users
	•	View all subscriptions
	•	Manage user subscription plans
	•	View all payments
	•	Send notifications to users
	•	View platform analytics

⸻

🔐 Authentication & Security
	•	Password hashing using bcrypt
	•	JWT-based authentication
	•	Role-based access control (User/Admin)
	•	Environment variables for sensitive data


📦 Project Structure
saas_app/
│── main.py
│── auth.py
│── models.py
│── database.py
│── alembic/
│── .env
│── .gitignore
│── README.md


⸻

🧪 API Documentation
Swagger UI available at:
http://127.0.0.1:8000/docs

💳 Stripe Integration
	•	Stripe Checkout for payments
	•	Webhook handling with signature verification
	•	Updates subscription status on successful payment

⸻

🔔 Notification System

Notifications are triggered for:
	•	Project creation
	•	Successful payments
	•	Subscription upgrades
	•	Admin actions

⸻

⚡ Setup Instructions

1️⃣ Clone Repository
git clone https://github.com/yaseen276/saas-backend.git
cd saas-backend

2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   (Windows)

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Setup Environment Variables
Create a .env file:
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret

5️⃣ Run Database Migrations
alembic upgrade head

6️⃣ Run Server
uvicorn main:app --reload


⸻

🧠 Business Logic

Free Plan
	•	Maximum 3 projects

Pro Plan
	•	Unlimited projects

⸻

📊 Admin Capabilities
	•	Monitor users and subscriptions
	•	Manage plans dynamically
	•	Track payments and revenue

⸻

✅ Completed Requirements
	•	User & Admin Authentication
	•	Project CRUD Operations
	•	Subscription Management
	•	Stripe Payment Integration
	•	Webhook Handling
	•	Notification System
	•	Role-Based Access Control
	•	Alembic Migrations
	•	Secure Environment Variables

⸻

📌 Notes
	•	Secrets are managed using environment variables
	•	.env is excluded from version control for security
	•	Clean and modular code structure followed
