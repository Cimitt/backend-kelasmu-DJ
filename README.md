# How to run

---

## Tech Stack & Dependencies

- Django==5.2.9
- django-cors-headers==4.9.0
- django-environ==0.12.0
- djangorestframework==3.16.1
- djangorestframework_simplejwt==5.5.1
- black==25.11.0
- channels==4.3.2
- channels_redis==4.3.0
- psycopg2-binary==2.9.11
- PyJWT==2.10.1
- pillow==12.0.0

---

## Instalation guide

### Clone Repository

```bash
git@github.com:KaramelDev/peprpus-app-backend.git
cd perpus-app-backend
```

## Make Venv
```bash
- python -m venv venv
- source venv/bin/activate        # Mac / Linux
- venv\Scripts\activate           # Windows
```

## Install ruquirement.txt
```bash
pip install -r requirements.txt
```
## Setup Env
```bash
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=*

DATABASE_URL=psql://postgresuser:postgrespass@127.0.0.1:5432/postgresdb
# DATABASE_URL=sqlite://../db.sqlite3

STATIC_DIR=static
MEDIA_DIR=media

DJANGO_SUPERUSER_USERNAME=example
DJANGO_SUPERUSER_EMAIL=example@gmail.com
DJANGO_SUPERUSER_PASSWORD=example123
```
## Run Project
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```
