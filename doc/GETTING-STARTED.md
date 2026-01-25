# Getting Started

This guide will help you set up and run this Django application locally on your machine.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd plachtis
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**On Linux/Mac:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Set Up the Database

```bash
python manage.py migrate
```

### 6. Create a Superuser (Optional)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 7. Run the Development Server

```bash
python manage.py runserver
```

### 8. Access the Application

Open your browser and navigate to:
- Application: `http://127.0.0.1:8000/`
- Admin panel: `http://127.0.0.1:8000/admin/`

## Troubleshooting

- If you encounter dependency issues, ensure your Python version is up to date
- Make sure the virtual environment is activated before running commands
- Check that port 8000 is not already in use

## Next Steps

- Explore the admin panel to manage data
- Read the project documentation for more details
- Start developing new features
