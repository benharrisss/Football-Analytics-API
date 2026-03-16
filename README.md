[API_Documentation_SwaggerUI.pdf](https://github.com/user-attachments/files/26039100/API_Documentation_SwaggerUI.pdf)# Football Analytics API

RESTful API coded in Python using the Django REST Framework providing football match/team analytics over 25 years of English league football data.

## Features 
- Teams + Matches REST endpoints (list/retrieve/update/delete etc.)
- Analytics endpoints (league stats, upsets, head-to-head, team DNA)
- JWT-based authentication (SimpleJWT) for protected endpoints
- OpenAPI documentation (Swagger/Redoc via drf-spectacular)
- PostgreSQL database (production) with Django ORM



## Local Setup (Windows using Bash)

### Prerequisites
- Python 3.x
- PostgreSQL installed
- Git

### 1) Clone GitHub repository and create a virtual environment
```bash
git clone <https://github.com/benharrisss/Football-Analytics-API.git>
cd Football-Analytics-API

python -m venv .venv
source venv/Scripts/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment variables
Create a .env file (or set env vars in the terminal):

- `SECRET_KEY` (e.g. 'thisisbensverysecretkey')
- `DEBUG` (Set True for local development)
- `DATABASE_URL` (e.g. postgres://USER:PASSWORD@localhost:5432/football_api)

### 4) Run migrations
```bash
python manage.py migrate
```

### 5) Create an admin user
```bash
python manage.py createsuperuser
```

### 6) Start the server
```bash
python manage.py runserver
```



## API Documentation

### The generated API documentation PDF generated from Swagger UI:
- [API_Documentation_SwaggerUI.pdf](https://github.com/user-attachments/files/26039112/API_Documentation_SwaggerUI.pdf)

### Example requests and expected responses:





## Authentication (JWT)

### Obtain tokens:
- `POST /api/token/` returns `{ "access": "...", "refresh": "..." }`

### Refresh access:
- `POST /api/token/refresh/`

### Use protected endpoints with:
- `Authorization: Bearer <access_token>` or click the 'Authorize' button and enter the access token if using Swagger UI



## Running Tests
```bash
python manage.py test
```



## Deployment

### Deployed on Render, accessible via:
- https://football-analytics-api-vrrp.onrender.com/

### Check urls.py for relevant routes to access the API:
- https://github.com/benharrisss/Football-Analytics-API/blob/main/core/urls.py



## Alternative API documentation accessed through project routes:

### Swagger UI:
- `swagger/`

### Redoc:
- `redoc/`

### OpenAPI Schema:
- `schema/`

