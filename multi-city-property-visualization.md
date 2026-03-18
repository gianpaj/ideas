# Multi-City Property Visualization

**Status:** Design (revised)  
**Updated:** 2026-03-18

---

## Architecture

### 1. Data Pipeline (Python)

- **Scraper:** Crawls multiple real estate sites with location + property type aware parsing
- **Data model:** Each property record captures:
  - Address, lat/lon, price, €/m², property type (apt, house, commercial, etc.)
  - Bedrooms/apartments count, year built, condition, etc.
- **Aggregator:** Groups by city + district → calculates stats per neighborhood-property-type combo
- **Output:** Structured JSON per city (e.g., madrid.json, barcelona.json) with nested stats

### 2. 3D Frontend (Three.js web app)

- City selector dropdown (Madrid, Barcelona, Valencia, etc.)
- Property type filter (Residential, Commercial, etc.)
- Secondary filters: price range, year built, apartment count
- Each neighborhood cube dynamically recalculates based on active filters
- Cube height/color still tied to €/m² but now filtered view

### 3. Database/Config

- **Cities config file:** city name, bounds, OSM query, scraper sources
- **Property types taxonomy:** standardize across different scraper sources
- **Filter definitions:** which filters apply to which property types

---

## Data Structure (JSON)

```json
{
  "city": "madrid",
  "updated": "2026-03-17",
  "neighborhoods": [
    {
      "name": "Chamberí",
      "lat": 40.43,
      "lon": -3.71,
      "stats_by_type": {
        "residential_apt": {
          "avg_price_per_sqm": 8500,
          "price_range": [7000, 12000],
          "count": 245,
          "year_built_avg": 1965,
          "apartments_avg": 3.2
        },
        "commercial": { }
      }
    }
  ]
}
```

---

## MVP Scope (revised)

1. Scraper for Madrid + 1-2 property types
2. City selector (hardcoded to 1 city initially, structure supports N cities)
3. Property type + price range filters working
4. Future hooks: year built, apartment count filters (UI wired, backend ready)
5. Scalable aggregation logic
