# Portfolio Manager (Django)

A multi-user portfolio site. Each person registers, builds their own portfolio
(profile, picture, skills, projects, experience, education, CV) and nobody
else can see or change it - except administrators.

Built with Django, SQLite, Crispy Forms and Bootstrap 5.

## Features

| Requirement | Where it lives |
| --- | --- |
| Registration and login with username **or** email | `accounts/` (`RegistrationForm`, `EmailOrUsernameBackend`) |
| Superuser/admin can view, add, edit and delete every portfolio | `/portfolios/` pages and the Django admin |
| User A manages only User A's portfolio | `portfolio/permissions.py`, enforced in every view |
| User B cannot view or edit User A's information | Other people's pages return **403 Forbidden** |
| Profile picture upload | `Profile.profile_picture` (images only, 2 MB max) |
| CV upload (PDF, DOC, DOCX) | `Profile.cv` (5 MB max, content is checked, not just the extension) |
| CV download with ownership permissions | `/portfolios/<id>/cv/` - owner or admin only |
| Skills, projects, experience and education | Add / edit / delete from the portfolio page |
| Django admin dashboard | `/admin/` with inline editing of every section |
| Crispy Forms with Bootstrap 5 | `crispy_forms` + `crispy_bootstrap5`, all forms |
| SQLite, templates, static and media | `config/settings.py` |

## Installation and running on Windows

### 1. Install Python

1. Download Python 3.10 or newer from <https://www.python.org/downloads/windows/>.
2. In the installer, tick **"Add python.exe to PATH"**, then click *Install Now*.
3. Open a new **Command Prompt** or **PowerShell** window and check:

   ```bat
   python --version
   ```

   If `python` is not recognised, try `py --version` and use `py` instead of
   `python` in the commands below.

### 2. Unzip and open the project folder

Unzip `portfolio_manager.zip`, then open Command Prompt or PowerShell in the
folder that contains `manage.py`:

```bat
cd C:\path\to\portfolio_manager
```

### 3. Create and activate a virtual environment

```bat
python -m venv venv
```

Activate it:

* **Command Prompt:** `venv\Scripts\activate`
* **PowerShell:** `venv\Scripts\Activate.ps1`

If PowerShell says that running scripts is disabled, run this once and try
again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Your prompt should now start with `(venv)`.

### 4. Install the dependencies

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Create the database

```bat
python manage.py makemigrations portfolio
python manage.py migrate
```

### 6. Create an administrator (superuser)

```bat
python manage.py createsuperuser
```

Enter a username, an email address and a password when asked.

### 7. Start the server

```bat
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in your browser. Press `Ctrl+C` in the terminal
to stop the server.

> The pages load Bootstrap 5 from a CDN, so the browser needs an internet
> connection the first time a page is opened.

### Run the tests (optional)

```bat
python manage.py test
```

## Using the site

**As a normal user**

1. Click **Register**, choose a username, email and password.
2. You land on your portfolio. Click **Edit profile** to add your name,
   headline, bio, contact details, profile picture and CV.
3. Use **Add skill / project / experience / education** and the *Edit* and
   *Delete* buttons next to each entry.
4. **Download CV** gives you your CV back as a file.

**As an administrator** (the superuser you created, or any user with the
"staff" flag)

* **All portfolios** in the top menu lists every user with search, paging and
  counts. From there you can *View*, *Edit* and *Delete* any portfolio, or
  **Add user & portfolio** to create an account for someone.
* **Django admin** (`/admin/`) offers the same control with inline editing of
  skills, projects, experience and education, plus user and permission
  management. To make someone an administrator, tick *Staff status* (and
  *Superuser status* for full control) on their user page there.

## Who can do what

| Action | Owner | Other user | Administrator |
| --- | :---: | :---: | :---: |
| View portfolio | yes | **no (403)** | yes |
| Edit profile, picture, CV | yes | **no (403)** | yes |
| Add / edit / delete skills, projects, experience, education | yes | **no (403)** | yes |
| Download CV | yes | **no (403)** | yes |
| List all portfolios, add users | no | no | yes |
| Delete a user with their portfolio | no | no | yes (not themselves) |

"Administrator" means `is_superuser` **or** `is_staff`. If you want only
superusers to have this power, edit `is_portfolio_admin()` in
`portfolio/permissions.py`.

## File uploads

* **Profile pictures**: JPG, PNG, GIF or WEBP, up to 2 MB. Stored in `media/`
  under random file names and served at `/media/` while `DEBUG` is on.
* **CVs**: PDF, DOC or DOCX, up to 5 MB. The file's first bytes must match its
  type. Stored in `private_media/`, a folder that is **not** mapped to any URL,
  so the only way to get a CV is the download view, which checks ownership.
  Downloads are sent as attachments.
* Replacing or removing a file deletes the old one from disk, and so does
  deleting a portfolio.
* Change the limits with `CV_MAX_UPLOAD_MB` and `PROFILE_PICTURE_MAX_UPLOAD_MB`
  in `config/settings.py`.

## Project layout

```
portfolio_manager/
|-- manage.py
|-- requirements.txt
|-- config/               settings, root URLs, WSGI/ASGI
|-- accounts/             registration, login (username or email)
|-- portfolio/            models, forms, views, permissions, admin, tests
|-- templates/            base layout and all pages
|-- static/               CSS and the default avatar
|-- media/                uploaded profile pictures (created at runtime)
`-- private_media/        uploaded CVs, never served directly
```

## Configuration

Defaults suit local development. For anything else, set environment
variables before starting the server.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `DJANGO_SECRET_KEY` | built-in dev key | **Required** when `DJANGO_DEBUG` is `False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated host names |

Command Prompt: `set DJANGO_DEBUG=False`  
PowerShell: `$env:DJANGO_DEBUG = "False"`

## Troubleshooting

* **`python` is not recognised** - reinstall Python with *Add python.exe to
  PATH* ticked, or use `py` instead of `python`.
* **`No module named django`** - the virtual environment is not active. Run
  the activation command from step 3 again, then `pip install -r requirements.txt`.
* **`No changes detected` after `makemigrations`** - run
  `python manage.py makemigrations portfolio` (naming the app) and then
  `python manage.py migrate`.
* **Port 8000 is busy** - use `python manage.py runserver 8080`.
* **Pages look unstyled** - Bootstrap is loaded from `cdn.jsdelivr.net`; check
  your internet connection.
* **Start over** - stop the server, delete `db.sqlite3` and the contents of
  `media/` and `private_media/`, then repeat steps 5 and 6.

## Before putting this on a public server

Set `DJANGO_DEBUG=False` and a strong `DJANGO_SECRET_KEY`, list your domain in
`DJANGO_ALLOWED_HOSTS`, serve static files (`python manage.py collectstatic`)
and `/media/` with a real web server, use HTTPS, and consider a production
database such as PostgreSQL instead of SQLite.
