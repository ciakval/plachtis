# plachtis
PlachtIS - Information system for SkaRe and other Czech water scout events

## Setup

### Prerequisites
- Python 3.12 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ciakval/plachtis.git
cd plachtis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Create a superuser (for admin access):
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

6. Access the application:
- Hello World view: http://localhost:8000/
- Hello World list: http://localhost:8000/list/
- Admin panel: http://localhost:8000/admin/

## Project Structure

- `plachtis/` - Main Django project settings
- `core/` - Core Django app with HelloWorld model and views
- `manage.py` - Django management script
- `requirements.txt` - Python dependencies

## Features

- **HelloWorld Model**: A simple model to store greeting messages
- **Hello World View**: Simple view displaying a greeting message
- **List View**: Template-based view showing all greeting messages
- **Admin Interface**: Django admin for managing HelloWorld messages

