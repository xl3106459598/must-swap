# 🔄 MUST Swap

A campus second-hand trading platform for students of Macau University of Science and Technology (MUST), built with **Flask** and **MySQL / SQLite**.

> **Based on the open-source project [College-Marketplace](https://github.com/kaustubh29032004/College-Marketplace)**
> by **kaustubh29032004**, released under the [MIT License](LICENSE).
> MUST Swap reuses and extends that project for the MUST community. We keep the original MIT notice
> and credit the original author; see the [License](#license) section below.

---

## ✨ Features (base project)

- 🔐 **Authentication & Security**: Student registration and login with secure **bcrypt** password hashing and session-based auth.
- 📦 **Product Management (CRUD)**: Create, view, update, delete listings, and toggle status between active and sold.
- 🖼️ **Image Uploads**: Secure file upload handling with format verification and unique filenames.
- 🔍 **Search & Category Filters**: Real-time keyword search, category filtering (Books, Electronics, Stationery, Furniture, Sports, Clothing, Other), and price range filtering.
- 🤝 **Peer-to-Peer Contact**: Contact modal with direct phone call and one-click WhatsApp chat integration.
- 👤 **Student Profiles & Dashboards**: Dedicated "My Listings" dashboard to manage active/sold items.
- 🔄 **Dual Database Engine**: Automatically tries **MySQL** connection pool; gracefully and seamlessly falls back to local **SQLite** if MySQL is unavailable, allowing instant zero-config setup!
- 🎨 **Modern Responsive UI**: Clean, accessible, mobile-friendly interface styled with modern CSS.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **Database**: MySQL (Production / Local) with automatic SQLite fallback
- **Security**: bcrypt (password hashing), dotenv (environment management)
- **Frontend**: HTML5, Vanilla CSS3, JavaScript, Jinja2 Templates

---

## 📁 Project Structure

```
MUST Swap/
├── app.py                  # Main Flask application and route handlers
├── db.py                   # Database abstraction layer (MySQL + SQLite fallback)
├── init_db.py              # Database initialization and demo seeding script
├── schema.sql              # MySQL schema definition
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables configuration template
├── .gitignore              # Git ignore rules
├── static/
│   ├── css/                # Custom CSS stylesheets
│   ├── js/                 # Client-side JavaScript
│   └── uploads/            # Uploaded product images
└── templates/              # Jinja2 HTML templates
    ├── base.html           # Base layout with navigation and footer
    ├── index.html          # Marketplace homepage with browse/search/filter
    ├── product_detail.html # Product details and seller contact
    ├── add_product.html    # Form to list a new item
    ├── edit_product.html   # Form to edit an existing item
    ├── my_listings.html    # Student's listings management dashboard
    ├── login.html          # Login page
    ├── register.html       # Registration page
    └── profile.html        # User profile view
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/xl3106459598/must-swap.git
cd must-swap
```

### 2. Create and Activate Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to configure your settings (optional if running SQLite mode):

```env
SECRET_KEY=your-secret-key-here
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=college_marketplace
```

> **Note**: If MySQL is not running or unconfigured, the application will automatically fall back to SQLite (`college_marketplace.db`).

### 5. Initialize the Database & Seed Demo Data

Run the database setup script:

```bash
python init_db.py
```

This will create tables and seed realistic demo products and student accounts.

#### Demo Credentials:
- **Email**: `alex@college.edu` | **Password**: `password123`
- **Email**: `priya@college.edu` | **Password**: `password123`
- **Email**: `rahul@college.edu` | **Password**: `password123`

### 6. Run the Application

```bash
python app.py
```

Open your browser and navigate to: `http://localhost:5000`

---

## 📄 License

This project builds on [College-Marketplace](https://github.com/kaustubh29032004/College-Marketplace)
by **kaustubh29032004**, which is released under the MIT License. We keep the original copyright and
permission notice and credit the original author. The full license text is in [LICENSE](LICENSE).