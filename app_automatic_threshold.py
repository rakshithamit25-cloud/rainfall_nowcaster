import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Rainfall Nowcaster", page_icon="🌧️", layout="wide")

st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:1.2rem}
.hero{padding:25px;border-radius:18px;background:linear-gradient(135deg,#0b1f3a,#155e75);color:#ffffff !important;margin-bottom:18px}
.hero h1{margin:0;font-size:34px;color:#ffffff !important}.hero p{margin:7px 0 0;color:#e2e8f0 !important;opacity:1}
.card{background:#ffffff !important;border:1px solid #cbd5e1;border-radius:16px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.12)}
.small{color:#334155 !important;font-size:14px;font-weight:700}.big{color:#0f172a !important;font-size:30px;font-weight:800;margin-top:6px}
.high{color:#dc2626 !important;font-weight:800}.medium{color:#d97706 !important;font-weight:800}.low{color:#16a34a !important;font-weight:800}
.metric-note{color:#475569 !important;font-size:12px;margin-top:4px}
.live-badge{display:inline-block;background:#dcfce7;color:#166534 !important;border-radius:999px;padding:5px 11px;font-weight:700;font-size:13px}
.stMarkdown,.stMarkdown p,.stMarkdown span,.stMarkdown div{color:inherit}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🌧️ AI-Powered Rainfall Nowcaster</h1>
<p>Current-location rainfall prediction for the next 30–120 minutes</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("📍 Current Location")
st.sidebar.caption("Allow browser location access to load live weather.")

geo = get_geolocation()

if not geo or "coords" not in geo:
    st.warning("📍 Please allow Location access in your browser.")
    st.info("If you previously denied permission, refresh the page and allow location access.")
    st.stop()

lat = geo["coords"]["latitude"]
lon = geo["coords"]["longitude"]

st.sidebar.success("Location detected")
st.sidebar.write(f"Latitude: `{lat:.5f}`")
st.sidebar.write(f"Longitude: `{lon:.5f}`")
if st.sidebar.button("🔄 Refresh Live Weather"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=300)
def get_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,pressure_msl,cloud_cover,wind_speed_10m"
        "&hourly=temperature_2m,relative_humidity_2m,pressure_msl,cloud_cover,wind_speed_10m,precipitation_probability"
        "&forecast_days=1&timezone=auto"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def get_place(lat, lon):
    try:
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?format=jsonv2&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
        )
        r = requests.get(url, timeout=10,
                         headers={"User-Agent": "RainfallNowcaster/1.0"})
        r.raise_for_status()
        address = r.json().get("address", {})
        place = (address.get("city") or address.get("town") or
                 address.get("village") or address.get("municipality") or
                 address.get("county") or "Current Location")
        state = address.get("state", "")
        country = address.get("country", "")
        return ", ".join([p for p in [place, state, country] if p])
    except Exception:
        return "Current Location"

try:
    data = get_weather(lat, lon)
except Exception as e:
    st.error(f"Could not load live weather: {e}")
    st.stop()

place = get_place(lat, lon)
current = data["current"]
hourly = data["hourly"]

temp = current["temperature_2m"]
humidity = current["relative_humidity_2m"]
pressure = current["pressure_msl"]
clouds = current["cloud_cover"]
wind = current["wind_speed_10m"]

st.markdown(f"### 📍 {place}")
st.markdown('<span class="live-badge">🟢 LIVE WEATHER DATA</span>', unsafe_allow_html=True)
st.caption(f"GPS coordinates: {lat:.5f}, {lon:.5f}")

st.subheader("Current Weather")
cols = st.columns(5)
items = [
    ("🌡️ Temperature", f"{temp:.1f} °C"),
    ("💧 Humidity", f"{humidity:.0f}%"),
    ("Pressure", f"{pressure:.0f} hPa"),
    ("💨 Wind", f"{wind:.1f} km/h"),
    ("☁️ Cloud Cover", f"{clouds:.0f}%")
]
for c,(label,value) in zip(cols,items):
    with c:
        st.markdown(
            f'<div class="card"><div class="small" style="color:#334155 !important">{label}</div>'
            f'<div class="big" style="color:#0f172a !important">{value}</div>'
            f'<div class="metric-note">Updated from live weather data</div></div>',
            unsafe_allow_html=True
        )

st.subheader("🌧️ Rainfall Nowcast")

times = pd.to_datetime(hourly["time"])
prob = np.array(hourly["precipitation_probability"], dtype=float)
now = pd.Timestamp.now()

def nearest_probability(minutes):
    target = now + pd.Timedelta(minutes=minutes)
    idx = np.argmin(np.abs(times - target))
    return float(prob[idx])

p30,p60,p90,p120 = [nearest_probability(x) for x in (30,60,90,120)]

def risk(p):
    if p >= 60: return "HIGH","high"
    if p >= 30: return "MEDIUM","medium"
    return "LOW","low"

cards = st.columns(4)
for c,mins,p in zip(cards,[30,60,90,120],[p30,p60,p90,p120]):
    r,cls = risk(p)
    with c:
        st.markdown(
            f'<div class="card"><div class="small">NEXT {mins} MINUTES</div>'
            f'<div class="big">{p:.0f}%</div><div class="{cls}">{r} RISK</div></div>',
            unsafe_allow_html=True
        )

left,right = st.columns([1.5,1])
with left:
    st.subheader("📊 Rain Probability")
    fig=go.Figure()
    fig.add_trace(go.Scatter(
        x=["30 min","60 min","90 min","120 min"], y=[p30,p60,p90,p120],
        mode="lines+markers", line=dict(width=4), marker=dict(size=10)
    ))
    fig.update_layout(height=360,yaxis=dict(range=[0,100],title="Probability (%)"))
    st.plotly_chart(fig,use_container_width=True)

with right:
    st.subheader("⚠️ Current Risk")
    r,_=risk(p30)
    if r=="HIGH": st.error("🚨 HIGH RISK — Rain probability is high within 30 minutes.")
    elif r=="MEDIUM": st.warning("⚠️ MEDIUM RISK — Rain is possible within 30 minutes.")
    else: st.success("✅ LOW RISK — Rain probability is currently low.")

st.subheader("📈 Live Weather Trends")
n=min(12,len(times))
trend=pd.DataFrame({
    "Time":times[:n],
    "Temperature":hourly["temperature_2m"][:n],
    "Humidity":hourly["relative_humidity_2m"][:n],
    "Pressure":hourly["pressure_msl"][:n],
    "Wind":hourly["wind_speed_10m"][:n]
})

a,b=st.columns(2)
with a:
    fig=go.Figure(go.Scatter(x=trend["Time"],y=trend["Humidity"],mode="lines+markers"))
    fig.update_layout(title="Humidity",height=300,yaxis_title="%")
    st.plotly_chart(fig,use_container_width=True)
with b:
    fig=go.Figure(go.Scatter(x=trend["Time"],y=trend["Pressure"],mode="lines+markers"))
    fig.update_layout(title="Pressure",height=300,yaxis_title="hPa")
    st.plotly_chart(fig,use_container_width=True)

a,b=st.columns(2)
with a:
    fig=go.Figure(go.Scatter(x=trend["Time"],y=trend["Temperature"],mode="lines+markers"))
    fig.update_layout(title="Temperature",height=300,yaxis_title="°C")
    st.plotly_chart(fig,use_container_width=True)
with b:
    fig=go.Figure(go.Scatter(x=trend["Time"],y=trend["Wind"],mode="lines+markers"))
    fig.update_layout(title="Wind Speed",height=300,yaxis_title="km/h")
    st.plotly_chart(fig,use_container_width=True)

st.subheader("🤖 Prediction Factors")
factors=pd.DataFrame({
    "Factor":["Humidity","Cloud Cover","Pressure","Wind Speed"],
    "Relative Importance":[35,30,22,13]
}).sort_values("Relative Importance")
fig=go.Figure(go.Bar(x=factors["Relative Importance"],y=factors["Factor"],orientation="h"))
fig.update_layout(height=320,xaxis_title="Relative importance (%)")
st.plotly_chart(fig,use_container_width=True)
st.info("These are placeholder feature-importance values. Replace them with real SHAP values after connecting your trained XGBoost model.")

# ---------------- AUTOMATIC ALERT DECISION ----------------
# No manual threshold is required. The dashboard decides the alert
# from the live rain probability and the current weather conditions.
#
# LOW:    < 30%
# MEDIUM: 30–59%
# HIGH:   >= 60%
#
# The same decision is used for the 30-minute smart alert.

def automatic_alert(probability, humidity, cloud_cover, pressure):
    if probability >= 60:
        return "HIGH", "🚨 HIGH RAIN ALERT", (
            "Rain is highly likely within the next 30 minutes."
        )
    elif probability >= 30:
        return "MEDIUM", "⚠️ MEDIUM RAIN ALERT", (
            "Rain is possible within the next 30 minutes. Keep rain protection ready."
        )
    elif humidity >= 85 and cloud_cover >= 75 and pressure <= 1005:
        return "MEDIUM", "⚠️ WEATHER WATCH", (
            "Weather conditions are becoming favorable for rainfall."
        )
    else:
        return "LOW", "✅ LOW RAIN RISK", (
            "No immediate rainfall alert is required."
        )

alert_level, alert_title, alert_message = automatic_alert(
    p30, humidity, clouds, pressure
)

st.subheader("🚨 Smart Alert")

if alert_level == "HIGH":
    st.error(f"{alert_title}\n\n{alert_message}")
elif alert_level == "MEDIUM":
    st.warning(f"{alert_title}\n\n{alert_message}")
else:
    st.success(f"{alert_title}\n\n{alert_message}")

# Show why the system made the decision.
with st.expander("🔎 Why was this alert selected?"):
    st.write(f"30-minute rain probability: **{p30:.0f}%**")
    st.write(f"Humidity: **{humidity:.0f}%**")
    st.write(f"Cloud cover: **{clouds:.0f}%**")
    st.write(f"Pressure: **{pressure:.0f} hPa**")
    st.write(f"Automatic decision: **{alert_level}**")

st.markdown("---")
st.caption("Rainfall Nowcaster • Automatic risk decision • Current Location • Live Weather • 30/60/90/120-minute forecast")
