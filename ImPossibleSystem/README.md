# ParkSense System

A parking management system built with Django.

## Setup Instructions

### Windows
1. Install Python 3.x from [python.org](https://python.org)
2. Open Command Prompt as Administrator
3. Create a virtual environment:
```cmd
python -m venv env
```
4. Activate the virtual environment:
```cmd
env\Scripts\activate
```
5. Install dependencies:
```cmd
pip install -r requirements.txt
```
6. Run migrations:
```cmd
python manage.py migrate
```
7. Create a superuser:
```cmd
python manage.py createsuperuser
```
8. Run the development server:
```cmd
python manage.py runserver
```

### Linux/Mac
1. Install Python 3.x:
```bash
# Ubuntu/Debian
sudo apt install python3 python3-venv

# Mac
brew install python3
```
2. Create a virtual environment:
```bash
python3 -m venv env
```
3. Activate the virtual environment:
```bash
source env/bin/activate
```
4. Install dependencies:
```bash
pip install -r requirements.txt
```
5. Run migrations:
```bash
python manage.py migrate
```
6. Create a superuser:
```bash
python manage.py createsuperuser
```
7. Run the development server:
```bash
python manage.py runserver
```

## Accessing the Application
- Main application: http://127.0.0.1:8000/
- Admin interface: http://127.0.0.1:8000/admin/

## Project Structure
- `ImPossibleSystem/` - Main project directory
  - `static/` - Static files (CSS, JavaScript, Images)
  - `templates/` - HTML templates
- `app1/` - Main application code
- `env/` - Virtual environment (not tracked in git)
- `manage.py` - Django management script
- `requirements.txt` - Project dependencies

## Development Notes
- Always use the virtual environment
- Use `python` on Windows and `python3` on Linux/Mac
- Static files are served automatically in development
- For production deployment, run `python manage.py collectstatic`
