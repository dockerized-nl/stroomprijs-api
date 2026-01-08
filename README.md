# Stroomprijs API

A FastAPI application for electricity pricing in the Netherlands, fetching data from EnergyZero API.

## Features

- View electricity prices for 24 hours
- Statistics showing lowest, average, and highest prices
- Visual chart showing price distribution
- Buy/Sell recommendations based on 6 cheapest and 6 most expensive hours
- Both HTML and JSON API endpoints

## Endpoints

- `/` - Home page with all available endpoints
- `/prices` - View all electricity prices (HTML)
- `/gemiddeld` - View price statistics with chart (HTML)
- `/kopen` - Check if current hour is good for buying (HTML)
- `/verkopen` - Check if current hour is good for selling (HTML)
- `/api/prices` - Get prices as JSON
- `/api/kopen` - Get buying status as JSON
- `/api/verkopen` - Get selling status as JSON
- `/health` - Health check endpoint
- `/docs` - Interactive API documentation (Swagger UI)

## Running with Docker

### Build and run using Docker:

```bash
docker build -t stroomprijs-api .
docker run -d -p 8000:8000 --name stroomprijs stroomprijs-api
```

### Or use Docker Compose:

```bash
docker-compose up -d
```

### Stop the container:

```bash
docker-compose down
```

### View logs:

```bash
docker-compose logs -f
```

## Running Locally (without Docker)

### 1. Create virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Run the application:

```bash
uvicorn main:app --reload
```

### 4. Access the application:

Open your browser and go to:
- http://localhost:8000 - Home page
- http://localhost:8000/docs - API documentation

## Docker Commands Reference

### Build the image:
```bash
docker build -t stroomprijs-api .
```

### Run the container:
```bash
docker run -d -p 8000:8000 --name stroomprijs stroomprijs-api
```

### Stop the container:
```bash
docker stop stroomprijs
```

### Start the container:
```bash
docker start stroomprijs
```

### Remove the container:
```bash
docker rm stroomprijs
```

### View container logs:
```bash
docker logs stroomprijs
docker logs -f stroomprijs  # Follow logs
```

### Access container shell:
```bash
docker exec -it stroomprijs /bin/bash
```

## Environment

The application uses the Amsterdam timezone (Europe/Amsterdam) for all time-based calculations.

## API Response Examples

### `/api/kopen` - Buy Status
```json
{
  "status": "OK",
  "action": "kopen",
  "message": "Huidige uur is in de 6 goedkoopste uren - kopen aanbevolen",
  "current_hour": 3,
  "current_time": "2026-01-08 03:45:12"
}
```

### `/api/verkopen` - Sell Status
```json
{
  "status": "neutraal",
  "action": "verkopen",
  "message": "Neutraal - niks doen",
  "current_hour": 12,
  "current_time": "2026-01-08 12:30:45"
}
```

## Technology Stack

- FastAPI - Modern web framework
- Uvicorn - ASGI server
- Chart.js - Data visualization
- EnergyZero API - Price data source
- Python 3.11
- Docker & Docker Compose
