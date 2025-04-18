# NBA Prop Betting Predictor

A full-stack web application that predicts the probability of NBA player props (specifically, points scored) hitting on FanDuel.

## Project Structure

- `frontend/`: Next.js frontend application
- `backend/`: Flask backend API and ML pipeline
- `docker-compose.yml`: Docker Compose configuration for running the entire stack

## Features (Planned)

- Display a ranked list of today's NBA player props from most likely to least likely to hit
- Search for specific player props
- View historical accuracy of predictions
- Analyze trends in player performances

## Technology Stack

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: Flask with SQLAlchemy and Flask-Migrate
- **Database**: PostgreSQL
- **Data Sources**: NBA API for historical data, Odds API for live prop lines
- **ML Pipeline**: XGBoost binary classifier

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js (for local frontend development)
- Python 3.11+ (for local backend development)

### Running with Docker Compose

```bash
# Clone the repository
git clone <repository-url>
cd nba-prop-predictor

# Start all services
docker-compose up
```

The frontend will be available at http://localhost:3000 and the backend API at http://localhost:5000.

### Local Development

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up the database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run the development server
python app.py
```

## License

MIT 