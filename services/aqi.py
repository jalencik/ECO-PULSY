"""US EPA Air Quality Index calculation.

Uses the official EPA breakpoints for PM2.5 as updated in 2024
(the "Good" band now ends at 9.0 ug/m3 instead of 12.0).
Reference: EPA Technical Assistance Document for Reporting of Daily AQI.
"""

# (conc_low, conc_high, aqi_low, aqi_high, label, css_class, advice)
PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50, "Good", "aqi-good",
     "Air quality is satisfactory. Enjoy outdoor activities."),
    (9.1, 35.4, 51, 100, "Moderate", "aqi-moderate",
     "Acceptable air quality. Unusually sensitive people should consider limiting prolonged outdoor exertion."),
    (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups", "aqi-usg",
     "Children, older adults and people with heart or lung disease should reduce prolonged outdoor exertion."),
    (55.5, 125.4, 151, 200, "Unhealthy", "aqi-unhealthy",
     "Everyone may begin to experience health effects. Sensitive groups should avoid outdoor exertion."),
    (125.5, 225.4, 201, 300, "Very Unhealthy", "aqi-very-unhealthy",
     "Health alert: everyone should avoid prolonged outdoor exertion."),
    (225.5, 500.4, 301, 500, "Hazardous", "aqi-hazardous",
     "Emergency conditions: everyone should stay indoors and keep activity levels low."),
]


def pm25_to_aqi(concentration):
    """Convert a PM2.5 concentration (ug/m3) to the EPA AQI.

    Returns a dict with the AQI value, category label, a CSS class
    used for colour coding, and plain-language health advice.
    Returns None when the concentration is missing.
    """
    if concentration is None:
        return None

    c = max(0.0, float(concentration))
    for c_low, c_high, a_low, a_high, label, css, advice in PM25_BREAKPOINTS:
        if c <= c_high:
            aqi = (a_high - a_low) / (c_high - c_low) * (c - c_low) + a_low
            return {"value": round(aqi), "label": label, "css": css, "advice": advice}

    # Above the highest breakpoint: report the AQI ceiling.
    top = PM25_BREAKPOINTS[-1]
    return {"value": 500, "label": top[4], "css": top[5], "advice": top[6]}
