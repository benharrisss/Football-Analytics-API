# Football Analytics API

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



## Example requests and expected responses:
- `BASE_URL`="http://127.0.0.1:8000" (local) OR "https://football-analytics-api-vrrp.onrender.com/" (Render)

### 200 OK - Public: league table (No authorisation needed)
Request:
`GET $BASE_URL/api/matches/league_table/?league=E0&season=23/24`  
Expected Response:
```json
[
    {
        "position": 1,
        "team": "Man City",
        "played": 38,
        "wins": 28,
        "draws": 7,
        "losses": 3,
        "goals_for": 96,
        "goals_against": 34,
        "goal_difference": 62,
        "points": 91
    },
    {
        "position": 2,
        "team": "Arsenal",
        "played": 38,
        "wins": 28,
        "draws": 5,
        "losses": 5,
        "goals_for": 91,
        "goals_against": 29,
        "goal_difference": 62,
        "points": 89
    },
    {
        "position": 3,
        "team": "Liverpool",
        "played": 38,
        "wins": 24,
        "draws": 10,
        "losses": 4,
        "goals_for": 86,
        "goals_against": 41,
        "goal_difference": 45,
        "points": 82
    },
    {
        "position": 4,
        "team": "Aston Villa",
        "played": 38,
        "wins": 20,
        "draws": 8,
        "losses": 10,
        "goals_for": 76,
        "goals_against": 61,
        "goal_difference": 15,
        "points": 68
    },
   ...
]
```

### 200 OK - Obtain JWT access token: token
Request:
`GET $BASE_URL/api/token`  
(Enter username and password of an authorised user)  
Expected Response:
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Mzc5NzM3MiwiaWF0IjoxNzczNzEwOTcyLCJqdGkiOiI5ZjRkMzcxNDIyZTQ0ZmIyYTAwNzEzMjFlZTJkYzQwYiIsInVzZXJfaWQiOiIxIn0.F6-jE9hJQoQi3Yg6swt_bE913QXwZSyBPDxuBBDQNIA",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczNzExMjcyLCJpYXQiOjE3NzM3MTA5NzIsImp0aSI6IjkyZGZlNDI1MzhmNTQ1ZjE4MmIzMjJjMWI2NzA4OGFlIiwidXNlcl9pZCI6IjEifQ.2yZjYqTTv9-UiCKZd7aos8g8t8X41aQm8TsXT0D79QM"
}
```
(Note this is not one of the access keys to authorise on the deployed API)  

### 200 OK - Private: best attack (Authorisation needed)
Request:
`GET $BASE_URL/api/teams/best_attack/?league=E0`  
Expected Response:
```json
[
  {
    "club": "Liverpool",
    "games": 941,
    "goals_per_game": 1.86,
    "shots_per_game": 15.59,
    "attack_score": 4.61
  },
  {
    "club": "Man City",
    "games": 903,
    "goals_per_game": 1.91,
    "shots_per_game": 14.86,
    "attack_score": 4.5
  },
  {
    "club": "Chelsea",
    "games": 940,
    "goals_per_game": 1.81,
    "shots_per_game": 14.93,
    "attack_score": 4.44
  },
  {
    "club": "Arsenal",
    "games": 940,
    "goals_per_game": 1.9,
    "shots_per_game": 14.19,
    "attack_score": 4.36
  },
 ...
]
```

### 400 Bad Request - Required 'league' parameter missing: league table
Request:
`GET $BASE_URL/api/matches/league_table/?season=23/24`  
Expected Response:
```json
{
    "error": "League code is required"
}
```

### 401 Unauthorised - Incorrect username and password for JWT access token: token
Request:
`GET $BASE_URL/api/token`  
Expected Response:
```json
{
    "detail": "No active account found with the given credentials"
}
```

### 401 Unauthorised - Access attempted to protected endpoint without token: best attack
Request:
`GET $BASE_URL/api/teams/best_attack/?league=E0`  
Expected Response:
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 404 Not Found - Invalid team IDs: head to head
Request:
`GET $BASE_URL/api/teams/head_to_head/?team1_id=9999&team2_id=6767`  
Expected Response:
```json
{
    "error": "One or both team IDs do not exist."
}
```



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

