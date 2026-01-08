from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
from datetime import datetime, timedelta
import pytz
import requests

app = FastAPI(title="Stroomprijs API")

templates_dir = Path(__file__).parent / "templates"


def get_energy_prices():
    current_date = datetime.now(pytz.timezone('Europe/Amsterdam'))
    yesterday = current_date + timedelta(days=-1)

    URL = f"https://api.energyzero.nl/v1/energyprices?fromDate={yesterday.strftime('%Y-%m-%d')}T23:00:00.000Z&tillDate={current_date.strftime('%Y-%m-%d')}T23:00:00.000Z&interval=4&usageType=1&inclBtw=true"
    page = requests.get(URL)

    output_page = page.json()

    output = ""
    average = output_page['average']

    for item in output_page['Prices']:
        hour = int(item['readingDate'].split('T')[-1].replace('Z', '')[:2])
        hour += 1
        if hour == 24:
            hour = 00
        elif hour == 25:
            hour = 1
        output += f"Tijd: {hour} Prijs: {item['price']}"
        output += "\n"

    labels = []
    values = []

    for item in output_page['Prices']:
        labels.append(item['readingDate'].split('T')[-1].replace('Z', '')[:2])
        values.append(item['price'])

    return {
        "text": output,
        "average": average,
        "labels": labels,
        "values": values,
        "prices": output_page['Prices']
    }


def get_price_statistics():
    """Calculate lowest, average, and highest prices with top 6 of each"""
    data = get_energy_prices()

    # Sort prices to get lowest and highest 6
    sorted_prices = sorted(data['prices'], key=lambda x: x['price'])
    lowest_6 = sorted_prices[:6]
    highest_6 = sorted_prices[-6:][::-1]  # Reverse to show highest first

    # Calculate overall statistics
    prices = [item['price'] for item in data['prices']]
    lowest_price = min(prices)
    highest_price = max(prices)
    average_price = data['average']

    # Process lowest 6 hours
    lowest_hours = []
    lowest_hour_numbers = []
    for item in lowest_6:
        hour = int(item['readingDate'].split('T')[-1].replace('Z', '')[:2])
        hour = (hour + 1) % 24
        lowest_hours.append({
            'hour': hour,
            'price': item['price']
        })
        lowest_hour_numbers.append(hour)

    # Process highest 6 hours
    highest_hours = []
    highest_hour_numbers = []
    for item in highest_6:
        hour = int(item['readingDate'].split('T')[-1].replace('Z', '')[:2])
        hour = (hour + 1) % 24
        highest_hours.append({
            'hour': hour,
            'price': item['price']
        })
        highest_hour_numbers.append(hour)

    return {
        "lowest": lowest_price,
        "average": average_price,
        "highest": highest_price,
        "lowest_hours": lowest_hours,
        "highest_hours": highest_hours,
        "lowest_hour_numbers": lowest_hour_numbers,
        "highest_hour_numbers": highest_hour_numbers
    }


def check_buy_status():
    """Check if current hour is in the 6 cheapest hours"""
    current_hour = datetime.now(pytz.timezone('Europe/Amsterdam')).hour
    stats = get_price_statistics()

    if current_hour in stats['lowest_hour_numbers']:
        return {
            "status": "OK",
            "action": "kopen",
            "message": "Huidige uur is in de 6 goedkoopste uren - kopen aanbevolen",
            "current_hour": current_hour,
            "current_time": datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('%Y-%m-%d %H:%M:%S')
        }
    elif current_hour in stats['highest_hour_numbers']:
        return {
            "status": "NOT OK",
            "action": "kopen",
            "message": "Huidige uur is in de 6 duurste uren - NIET kopen",
            "current_hour": current_hour,
            "current_time": datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        return {
            "status": "neutraal",
            "action": "kopen",
            "message": "Neutraal - niks doen",
            "current_hour": current_hour,
            "current_time": datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('%Y-%m-%d %H:%M:%S')
        }


def check_sell_status():
    """Check if current hour is in the 6 most expensive hours"""
    current_hour = datetime.now(pytz.timezone('Europe/Amsterdam')).hour
    stats = get_price_statistics()

    if current_hour in stats['highest_hour_numbers']:
        return {
            "status": "OK",
            "action": "verkopen",
            "message": "Huidige uur is in de 6 duurste uren - verkopen aanbevolen",
            "current_hour": current_hour,
            "current_time": datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('%Y-%m-%d %H:%M:%S')
        }
    elif current_hour in stats['lowest_hour_numbers']:
        return {
            "status": "NOT OK",
            "action": "verkopen",
            "message": "Huidige uur is in de 6 goedkoopste uren - NIET verkopen",
            "current_hour": current_hour,
            "current_time": datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        return {
            "status": "neutraal",
            "action": "verkopen",
            "message": "Neutraal - niks doen",
            "current_hour": current_hour,
            "current_time": datetime.now(pytz.timezone('Europe/Amsterdam')).strftime('%Y-%m-%d %H:%M:%S')
        }


@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = (templates_dir / "index.html").read_text()
    return HTMLResponse(content=html_content)


@app.get("/index.html", response_class=HTMLResponse)
async def index():
    html_content = (templates_dir / "index.html").read_text()
    return HTMLResponse(content=html_content)


@app.get("/health", response_class=HTMLResponse)
async def health():
    html_content = (templates_dir / "health.html").read_text()
    return HTMLResponse(content=html_content)


@app.get("/api/prices")
async def get_prices():
    """API endpoint to get energy prices as JSON"""
    return get_energy_prices()


@app.get("/prices", response_class=HTMLResponse)
async def prices_page():
    """HTML page displaying energy prices"""
    data = get_energy_prices()

    # Build price items HTML
    price_items = ""
    for item in data['prices']:
        hour = int(item['readingDate'].split('T')[-1].replace('Z', '')[:2])
        hour += 1
        if hour == 24:
            hour = 0
        elif hour == 25:
            hour = 1

        price_items += f"""
            <div class="price-item">
                <div class="hour">{hour:02d}:00</div>
                <div class="price">€{item['price']:.4f}</div>
            </div>
        """

    # Load template and replace placeholders
    html_content = (templates_dir / "prices.html").read_text()
    html_content = html_content.replace("{average}", f"{data['average']:.4f}")
    html_content = html_content.replace("{price_items}", price_items)

    return HTMLResponse(content=html_content)


@app.get("/gemiddeld", response_class=HTMLResponse)
async def gemiddeld_page():
    """HTML page displaying price statistics"""
    stats = get_price_statistics()
    data = get_energy_prices()

    # Build lowest hours HTML
    lowest_items = ""
    for item in stats['lowest_hours']:
        lowest_items += f"""
            <div class="hour-item">
                <span class="hour">{item['hour']:02d}:00</span>
                <span class="price">€{item['price']:.4f}</span>
            </div>
        """

    # Build highest hours HTML
    highest_items = ""
    for item in stats['highest_hours']:
        highest_items += f"""
            <div class="hour-item">
                <span class="hour">{item['hour']:02d}:00</span>
                <span class="price">€{item['price']:.4f}</span>
            </div>
        """

    # Build chart data
    chart_hours = []
    chart_prices = []
    chart_colors = []
    chart_border_colors = []

    lowest_hour_set = set(stats['lowest_hour_numbers'])
    highest_hour_set = set(stats['highest_hour_numbers'])

    for item in data['prices']:
        hour = int(item['readingDate'].split('T')[-1].replace('Z', '')[:2])
        hour = (hour + 1) % 24

        chart_hours.append(f"{hour:02d}:00")
        chart_prices.append(round(item['price'], 4))

        # Color code based on whether it's in lowest or highest 6
        if hour in lowest_hour_set:
            chart_colors.append('rgba(40, 167, 69, 0.6)')  # Green
            chart_border_colors.append('rgba(40, 167, 69, 1)')
        elif hour in highest_hour_set:
            chart_colors.append('rgba(220, 53, 69, 0.6)')  # Red
            chart_border_colors.append('rgba(220, 53, 69, 1)')
        else:
            chart_colors.append('rgba(33, 150, 243, 0.6)')  # Blue
            chart_border_colors.append('rgba(33, 150, 243, 1)')

    import json
    chart_data_json = json.dumps({
        'hours': chart_hours,
        'prices': chart_prices,
        'colors': chart_colors,
        'borderColors': chart_border_colors
    })

    # Load template and replace placeholders
    html_content = (templates_dir / "gemiddeld.html").read_text()
    html_content = html_content.replace("{lowest}", f"{stats['lowest']:.4f}")
    html_content = html_content.replace("{average}", f"{stats['average']:.4f}")
    html_content = html_content.replace("{highest}", f"{stats['highest']:.4f}")
    html_content = html_content.replace("{lowest_items}", lowest_items)
    html_content = html_content.replace("{highest_items}", highest_items)
    html_content = html_content.replace("{chart_data}", chart_data_json)

    return HTMLResponse(content=html_content)


@app.get("/kopen", response_class=HTMLResponse)
async def kopen_endpoint():
    """Check if current hour is good for buying (in 6 cheapest hours) - HTML page"""
    status_data = check_buy_status()

    # Determine status class and icon
    if status_data["status"] == "OK":
        status_class = "ok"
        status_icon = "✓"
        status_title = "JA - Kopen!"
    elif status_data["status"] == "NOT OK":
        status_class = "not-ok"
        status_icon = "✗"
        status_title = "NEE - Niet Kopen"
    else:  # neutraal
        status_class = "neutraal"
        status_icon = "●"
        status_title = "Neutraal"

    # Load template and replace placeholders
    html_content = (templates_dir / "kopen.html").read_text()
    html_content = html_content.replace("{status_class}", status_class)
    html_content = html_content.replace("{status_icon}", status_icon)
    html_content = html_content.replace("{status_title}", status_title)
    html_content = html_content.replace("{message}", status_data["message"])
    html_content = html_content.replace("{current_time}", status_data["current_time"])
    html_content = html_content.replace("{current_hour}", f"{status_data['current_hour']:02d}")

    return HTMLResponse(content=html_content)


@app.get("/api/kopen")
async def kopen_api_endpoint():
    """Check if current hour is good for buying (in 6 cheapest hours) - JSON API"""
    return check_buy_status()


@app.get("/verkopen", response_class=HTMLResponse)
async def verkopen_endpoint():
    """Check if current hour is good for selling (in 6 most expensive hours) - HTML page"""
    status_data = check_sell_status()

    # Determine status class and icon
    if status_data["status"] == "OK":
        status_class = "ok"
        status_icon = "✓"
        status_title = "JA - Verkopen!"
    elif status_data["status"] == "NOT OK":
        status_class = "not-ok"
        status_icon = "✗"
        status_title = "NEE - Niet Verkopen"
    else:  # neutraal
        status_class = "neutraal"
        status_icon = "●"
        status_title = "Neutraal"

    # Load template and replace placeholders
    html_content = (templates_dir / "verkopen.html").read_text()
    html_content = html_content.replace("{status_class}", status_class)
    html_content = html_content.replace("{status_icon}", status_icon)
    html_content = html_content.replace("{status_title}", status_title)
    html_content = html_content.replace("{message}", status_data["message"])
    html_content = html_content.replace("{current_time}", status_data["current_time"])
    html_content = html_content.replace("{current_hour}", f"{status_data['current_hour']:02d}")

    return HTMLResponse(content=html_content)


@app.get("/api/verkopen")
async def verkopen_api_endpoint():
    """Check if current hour is good for selling (in 6 most expensive hours) - JSON API"""
    return check_sell_status()
