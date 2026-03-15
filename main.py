"""
═══════════════════════════════════════════════════════════════════════════════
                        🌤️ HAVA DURUMU UYGULAMASI 🌤️
                    Professional Weather Application
                    Kendi Veritabanı ile Kimlik Doğrulama
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import secrets
import requests
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

# ═══════════════════════════════════════════════════════════════════════════════
# KONFİGÜRASYON
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Veritabanı URL'si (channel_binding dahil)
DATABASE_URL = 'postgresql://neondb_owner:npg_gOV9pRWXP0KZ@ep-damp-band-adaemlf8-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

# API Anahtarları
WEATHER_API_KEY = "11fd2f3a86a94ff5a52185939260203"
TIME_API_KEY = "a33a0d8c690e4274ab5356b49247a66b"
OPENROUTER_API_KEY = "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"

# ═══════════════════════════════════════════════════════════════════════════════
# VERİTABANI BAĞLANTISI
# ═══════════════════════════════════════════════════════════════════════════════

def get_db_connection():
    """Veritabanı bağlantısı oluşturur"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Kullanıcılar tablosu - name sütunu var mı?
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # ... (user_locations tablosu)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Veritabanı tabloları hazır!")
    print("Bağlanılan DB:", DATABASE_URL)

# ═══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    """Giriş kontrolü decorator'ü"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için lütfen giriş yapın.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_by_id(user_id):
    """ID'ye göre kullanıcı bilgisi getirir"""
    conn = get_db_connection()
    cur = conn.cursor()
    # created_at yerine kayıt tarihi yoksa şimdiki tarihi göster
    cur.execute("SELECT id, email, name, CURRENT_TIMESTAMP as created_at FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

# ═══════════════════════════════════════════════════════════════════════════════
# TÜRK ŞEHİRLERİ
# ═══════════════════════════════════════════════════════════════════════════════

TURKISH_CITIES = [
    {"name": "İstanbul", "lat": 41.0082, "lon": 28.9784},
    {"name": "Ankara", "lat": 39.9334, "lon": 32.8597},
    {"name": "İzmir", "lat": 38.4192, "lon": 27.1287},
    {"name": "Bursa", "lat": 40.1826, "lon": 29.0665},
    {"name": "Antalya", "lat": 36.8969, "lon": 30.7133},
    {"name": "Adana", "lat": 37.0000, "lon": 35.3213},
    {"name": "Konya", "lat": 37.8746, "lon": 32.4932},
    {"name": "Gaziantep", "lat": 37.0662, "lon": 37.3833},
    {"name": "Şanlıurfa", "lat": 37.1674, "lon": 38.7955},
    {"name": "Kocaeli", "lat": 40.8533, "lon": 29.8815},
    {"name": "Mersin", "lat": 36.8121, "lon": 34.6415},
    {"name": "Diyarbakır", "lat": 37.9144, "lon": 40.2306},
    {"name": "Hatay", "lat": 36.4018, "lon": 36.3498},
    {"name": "Manisa", "lat": 38.6191, "lon": 27.4289},
    {"name": "Kayseri", "lat": 38.7322, "lon": 35.4853},
    {"name": "Samsun", "lat": 41.2867, "lon": 36.33},
    {"name": "Balıkesir", "lat": 39.6484, "lon": 27.8826},
    {"name": "Kahramanmaraş", "lat": 37.5847, "lon": 36.9371},
    {"name": "Van", "lat": 38.4891, "lon": 43.4089},
    {"name": "Aydın", "lat": 37.8444, "lon": 27.8458},
    {"name": "Muğla", "lat": 37.2153, "lon": 28.3636},
    {"name": "Tekirdağ", "lat": 40.9781, "lon": 27.5117},
    {"name": "Eskişehir", "lat": 39.7767, "lon": 30.5206},
    {"name": "Trabzon", "lat": 41.0027, "lon": 39.7168},
    {"name": "Erzurum", "lat": 39.9000, "lon": 41.2700},
    {"name": "Malatya", "lat": 38.3552, "lon": 38.3095},
    {"name": "Sivas", "lat": 39.7477, "lon": 37.0179},
    {"name": "Ordu", "lat": 40.9862, "lon": 37.8797},
    {"name": "Rize", "lat": 41.0201, "lon": 40.5234},
    {"name": "Isparta", "lat": 37.7648, "lon": 30.5566},
    {"name": "Denizli", "lat": 37.7765, "lon": 29.0860},
    {"name": "Bodrum", "lat": 37.0344, "lon": 27.4305},
    {"name": "Fethiye", "lat": 36.6211, "lon": 29.1164},
    {"name": "Alanya", "lat": 36.5438, "lon": 31.9989},
    {"name": "Çanakkale", "lat": 40.1467, "lon": 26.4086},
    {"name": "Bayburt", "lat": 40.2556, "lon": 40.2249},
]

# ═══════════════════════════════════════════════════════════════════════════════
# API SERVİSLERİ
# ═══════════════════════════════════════════════════════════════════════════════

class WeatherService:
    """Hava Durumu API Servisi"""
    BASE_URL = "http://api.weatherapi.com/v1"
    
    @staticmethod
    def get_current_weather(city):
        try:
            url = f"{WeatherService.BASE_URL}/current.json"
            params = {'key': WEATHER_API_KEY, 'q': city, 'aqi': 'no', 'lang': 'tr'}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Hava durumu hatası: {e}")
            return None
    
    @staticmethod
    def get_forecast(city, days=7):
        try:
            url = f"{WeatherService.BASE_URL}/forecast.json"
            params = {'key': WEATHER_API_KEY, 'q': city, 'days': days, 'aqi': 'no', 'alerts': 'no', 'lang': 'tr'}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Tahmin hatası: {e}")
            return None


class TimeService:
    """Zaman ve Ezan Saatleri API Servisi"""
    BASE_URL = "https://api.ipgeolocation.io"
    
    @staticmethod
    def get_prayer_times(city, date=None):
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            url = f"{TimeService.BASE_URL}/astronomy"
            params = {'apiKey': TIME_API_KEY, 'location': city}
            response = requests.get(url, params=params, timeout=10)
            astronomy = response.json()
            
            if not astronomy:
                return None
            
            sunrise = astronomy.get('sunrise', '06:00')
            sunset = astronomy.get('sunset', '18:00')
            
            sunrise_hour, sunrise_min = map(int, sunrise.split(':'))
            sunset_hour, sunset_min = map(int, sunset.split(':'))
            
            # Ezan saatleri hesaplama
            imsak_hour = sunrise_hour
            imsak_min = sunrise_min - 20
            if imsak_min < 0:
                imsak_min += 60
                imsak_hour -= 1
            
            sabah_hour = sunrise_hour
            sabah_min = sunrise_min - 5
            if sabah_min < 0:
                sabah_min += 60
                sabah_hour -= 1
            
            aksam_min = sunset_min + 5
            aksam_hour = sunset_hour
            if aksam_min >= 60:
                aksam_min -= 60
                aksam_hour += 1
            
            yatsi_min = aksam_min + 45
            yatsi_hour = aksam_hour + 1
            if yatsi_min >= 60:
                yatsi_min -= 60
                yatsi_hour += 1
            
            return {
                'imsak': f"{max(0, imsak_hour):02d}:{imsak_min:02d}",
                'sabah': f"{max(0, sabah_hour):02d}:{sabah_min:02d}",
                'ogle': "12:30",
                'ikindi': "16:00",
                'aksam': f"{aksam_hour:02d}:{aksam_min:02d}",
                'yatsi': f"{yatsi_hour:02d}:{yatsi_min:02d}",
                'sunrise': sunrise,
                'sunset': sunset,
                'city': city,
                'date': date
            }
        except Exception as e:
            print(f"Ezan saati hatası: {e}")
            return None


class AIService:
    """Yapay Zeka Servisi"""
    BASE_URL = "https://openrouter.ai/api/v1"
    
    @staticmethod
    def get_daily_weather_summary(weather_data, city):
        try:
            if not weather_data:
                return "Hava durumu verisi alınamadı."
            
            current = weather_data.get('current', {})
            forecast = weather_data.get('forecast', {}).get('forecastday', [])
            today = forecast[0] if forecast else {}
            day = today.get('day', {})
            
            prompt = f"""{city} için hava durumu değerlendirmesi yap. Kısa ve öz 3-4 cümle ile:
- Sıcaklık: {current.get('temp_c', 'N/A')}°C
- Hissedilen: {current.get('feelslike_c', 'N/A')}°C  
- Durum: {current.get('condition', {}).get('text', 'N/A')}
- Nem: {current.get('humidity', 'N/A')}%
- Rüzgar: {current.get('wind_kph', 'N/A')} km/s
- Yağış: {day.get('daily_chance_of_rain', 0)}%
Giyim ve dışarı çıkma önerisi ver."""
            
            url = f"{AIService.BASE_URL}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'HTTP-Referer': 'http://localhost:5050'
            }
            data = {
                'model': 'openai/gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'Sen Türkçe konuşan bir hava durumu asistanısın.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 300,
                'temperature': 0.7
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"AI hatası: {e}")
            return "AI değerlendirmesi şu an mevcut değil."

# ═══════════════════════════════════════════════════════════════════════════════
# HTML ŞABLONLARI
# ═══════════════════════════════════════════════════════════════════════════════

# (BASE_STYLES, AUTH_TEMPLATE, LOADING_TEMPLATE, DASHBOARD_TEMPLATE, PROFILE_TEMPLATE aynen kalacak, ancak küçük düzeltmeler yapılacak)
# NOT: Şablonların içindeki Jinja2 kodları doğru şekilde kaçışlanmıştır. 
# Sadece profile template'de kullanılmayan alanlar (emailVerified vb.) kaldırılacak veya varsayılan atanacak.

BASE_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #0a1628 0%, #1a2a4a 50%, #0d1f3c 100%);
        min-height: 100vh;
        color: #ffffff;
        overflow-x: hidden;
    }
    
    .bg-animation {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        overflow: hidden;
    }
    
    .bg-animation::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 20% 80%, rgba(30, 144, 255, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(0, 191, 255, 0.1) 0%, transparent 50%);
        animation: bgMove 20s ease-in-out infinite;
    }
    
    @keyframes bgMove {
        0%, 100% { transform: translate(0, 0) rotate(0deg); }
        50% { transform: translate(30px, -30px) rotate(120deg); }
    }
    
    .clouds {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        pointer-events: none;
    }
    
    .cloud {
        position: absolute;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 50%;
        animation: cloudFloat linear infinite;
    }
    
    @keyframes cloudFloat {
        from { transform: translateX(-100%); }
        to { transform: translateX(100vw); }
    }
    
    .stars {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -2;
        pointer-events: none;
    }
    
    .star {
        position: absolute;
        width: 2px;
        height: 2px;
        background: white;
        border-radius: 50%;
        animation: twinkle 3s ease-in-out infinite;
    }
    
    @keyframes twinkle {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
    }
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        position: relative;
        z-index: 1;
    }
    
    .btn {
        padding: 12px 24px;
        border: none;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
    }
    
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(30, 144, 255, 0.6);
    }
    
    .btn-danger {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
    }
    
    .btn-secondary {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .form-group {
        margin-bottom: 20px;
    }
    
    .form-label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .form-control {
        width: 100%;
        padding: 14px 18px;
        background: rgba(10, 22, 40, 0.8);
        border: 2px solid rgba(77, 166, 255, 0.3);
        border-radius: 12px;
        color: white;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .form-control:focus {
        outline: none;
        border-color: #4da6ff;
        box-shadow: 0 0 20px rgba(77, 166, 255, 0.3);
    }
    
    .alert {
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .alert-success { background: rgba(46, 204, 113, 0.2); border: 1px solid rgba(46, 204, 113, 0.5); color: #2ecc71; }
    .alert-danger { background: rgba(231, 76, 60, 0.2); border: 1px solid rgba(231, 76, 60, 0.5); color: #e74c3c; }
    .alert-warning { background: rgba(241, 196, 15, 0.2); border: 1px solid rgba(241, 196, 15, 0.5); color: #f1c40f; }
</style>
"""

AUTH_TEMPLATE = BASE_STYLES + """
<style>
    .auth-container {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }
    
    .auth-card {
        background: rgba(15, 30, 55, 0.9);
        backdrop-filter: blur(30px);
        border-radius: 30px;
        border: 1px solid rgba(77, 166, 255, 0.3);
        padding: 50px;
        width: 100%;
        max-width: 450px;
        position: relative;
        overflow: hidden;
        animation: fadeInUp 0.6s ease;
    }
    
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .auth-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #1e90ff, #00bfff, #1e90ff);
        background-size: 200% 100%;
        animation: shimmer 3s linear infinite;
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .auth-logo {
        text-align: center;
        margin-bottom: 40px;
    }
    
    .auth-logo i {
        font-size: 4rem;
        color: #4da6ff;
        animation: floatIcon 3s ease-in-out infinite;
    }
    
    @keyframes floatIcon {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    .auth-logo h1 {
        font-size: 1.8rem;
        margin-top: 15px;
        background: linear-gradient(135deg, #ffffff 0%, #4da6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .auth-logo p {
        color: rgba(255, 255, 255, 0.6);
        margin-top: 5px;
    }
    
    .auth-tabs {
        display: flex;
        margin-bottom: 30px;
        background: rgba(10, 22, 40, 0.5);
        border-radius: 15px;
        padding: 5px;
    }
    
    .auth-tab {
        flex: 1;
        padding: 12px;
        text-align: center;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .auth-tab.active {
        background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
    }
    
    .auth-form {
        display: none;
    }
    
    .auth-form.active {
        display: block;
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    .form-icon {
        position: relative;
    }
    
    .form-icon i {
        position: absolute;
        left: 15px;
        top: 50%;
        transform: translateY(-50%);
        color: rgba(77, 166, 255, 0.7);
        transition: color 0.3s ease;
    }
    
    .form-icon input {
        padding-left: 45px;
    }
    
    .password-toggle {
        position: absolute;
        right: 15px;
        top: 50%;
        transform: translateY(-50%);
        cursor: pointer;
        color: rgba(255, 255, 255, 0.5);
        transition: color 0.3s ease;
    }
    
    .password-toggle:hover {
        color: #4da6ff;
    }
    
    .btn-auth {
        width: 100%;
        padding: 15px;
        font-size: 1.1rem;
        margin-top: 10px;
    }
</style>

<div class="bg-animation"></div>
<div class="clouds">
    <div class="cloud" style="width: 100px; height: 40px; top: 10%; left: -100px; animation-duration: 30s;"></div>
    <div class="cloud" style="width: 150px; height: 60px; top: 25%; left: -150px; animation-duration: 40s; animation-delay: 5s;"></div>
</div>
<div class="stars" id="stars"></div>

<div class="auth-container">
    <div class="auth-card">
        <div class="auth-logo">
            <i class="fas fa-cloud-sun"></i>
            <h1>Hava Durumu</h1>
            <p>Hesabınızla giriş yapın</p>
        </div>
        
        <div class="auth-tabs">
            <div class="auth-tab active" onclick="showTab('login')">Giriş Yap</div>
            <div class="auth-tab" onclick="showTab('register')">Kayıt Ol</div>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <!-- Giriş Formu -->
        <form id="login-form" class="auth-form active" method="POST" action="{{ url_for('login') }}">
            <div class="form-group">
                <label class="form-label">E-posta</label>
                <div class="form-icon">
                    <input type="email" name="email" class="form-control" placeholder="email@example.com" required>
                    <i class="fas fa-envelope"></i>
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">Şifre</label>
                <div class="form-icon">
                    <input type="password" name="password" class="form-control" id="login-password" placeholder="••••••••" required>
                    <i class="fas fa-lock"></i>
                    <span class="password-toggle" onclick="togglePassword('login-password', this)">
                        <i class="fas fa-eye"></i>
                    </span>
                </div>
            </div>
            
            <button type="submit" class="btn btn-primary btn-auth">
                <i class="fas fa-sign-in-alt"></i> Giriş Yap
            </button>
        </form>
        
        <!-- Kayıt Formu -->
        <form id="register-form" class="auth-form" method="POST" action="{{ url_for('register') }}">
            <div class="form-group">
                <label class="form-label">Ad Soyad</label>
                <div class="form-icon">
                    <input type="text" name="name" class="form-control" placeholder="Adınız Soyadınız" required>
                    <i class="fas fa-user"></i>
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">E-posta</label>
                <div class="form-icon">
                    <input type="email" name="email" class="form-control" placeholder="email@example.com" required>
                    <i class="fas fa-envelope"></i>
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">Şifre</label>
                <div class="form-icon">
                    <input type="password" name="password" class="form-control" id="register-password" placeholder="En az 6 karakter" required minlength="6">
                    <i class="fas fa-lock"></i>
                    <span class="password-toggle" onclick="togglePassword('register-password', this)">
                        <i class="fas fa-eye"></i>
                    </span>
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">Şifre Tekrar</label>
                <div class="form-icon">
                    <input type="password" name="password_confirm" class="form-control" placeholder="Şifrenizi tekrar girin" required>
                    <i class="fas fa-lock"></i>
                </div>
            </div>
            
            <button type="submit" class="btn btn-primary btn-auth">
                <i class="fas fa-user-plus"></i> Kayıt Ol
            </button>
        </form>
    </div>
</div>

<script>
    function createStars() {
        const starsContainer = document.getElementById('stars');
        for (let i = 0; i < 100; i++) {
            const star = document.createElement('div');
            star.className = 'star';
            star.style.left = Math.random() * 100 + '%';
            star.style.top = Math.random() * 100 + '%';
            star.style.animationDelay = Math.random() * 3 + 's';
            starsContainer.appendChild(star);
        }
    }
    createStars();
    
    function showTab(tab) {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(tab + '-form').classList.add('active');
    }
    
    function togglePassword(inputId, toggleBtn) {
        const input = document.getElementById(inputId);
        const icon = toggleBtn.querySelector('i');
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
    
    document.getElementById('register-form').addEventListener('submit', function(e) {
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.querySelector('[name="password_confirm"]').value;
        if (password !== confirmPassword) {
            e.preventDefault();
            alert('Şifreler eşleşmiyor!');
        }
    });
</script>
"""

LOADING_TEMPLATE = BASE_STYLES + """
<style>
    .loading-container {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    
    .loading-weather {
        position: relative;
        width: 200px;
        height: 200px;
        margin-bottom: 40px;
    }
    
    .sun {
        position: absolute;
        width: 80px;
        height: 80px;
        background: linear-gradient(135deg, #ffd700 0%, #ff8c00 100%);
        border-radius: 50%;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        box-shadow: 0 0 60px rgba(255, 215, 0, 0.6);
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: translate(-50%, -50%) scale(1); }
        50% { transform: translate(-50%, -50%) scale(1.1); }
    }
    
    .loading-text {
        font-size: 1.5rem;
        color: #4da6ff;
        margin-bottom: 20px;
        animation: fadeInOut 2s ease-in-out infinite;
    }
    
    @keyframes fadeInOut {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }
    
    .loading-progress {
        width: 300px;
        height: 6px;
        background: rgba(77, 166, 255, 0.2);
        border-radius: 3px;
        overflow: hidden;
    }
    
    .loading-progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #1e90ff, #00bfff, #1e90ff);
        background-size: 200% 100%;
        animation: progress 2s ease-in-out infinite, shimmer 2s linear infinite;
        border-radius: 3px;
    }
    
    @keyframes progress {
        0% { width: 0%; }
        100% { width: 100%; }
    }
</style>

<div class="bg-animation"></div>
<div class="stars" id="stars"></div>

<div class="loading-container">
    <div class="loading-weather">
        <div class="sun"></div>
    </div>
    <div class="loading-text" id="loading-text">Hava durumu verileri yükleniyor...</div>
    <div class="loading-progress">
        <div class="loading-progress-bar"></div>
    </div>
</div>

<script>
    const messages = ['Hava durumu verileri yükleniyor...', 'Konum bilgisi alınıyor...', 'Yapay zeka analiz yapıyor...', 'Ezan saatleri hesaplanıyor...', 'Uygulama hazırlanıyor...'];
    let currentIndex = 0;
    const loadingText = document.getElementById('loading-text');
    
    setInterval(() => {
        currentIndex = (currentIndex + 1) % messages.length;
        loadingText.style.opacity = 0;
        setTimeout(() => {
            loadingText.textContent = messages[currentIndex];
            loadingText.style.opacity = 1;
        }, 300);
    }, 1500);
    
    const starsContainer = document.getElementById('stars');
    for (let i = 0; i < 100; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        starsContainer.appendChild(star);
    }
    
    setTimeout(() => { window.location.href = "{{ redirect_url }}"; }, 4000);
</script>
"""

DASHBOARD_TEMPLATE = BASE_STYLES + """
<style>
    .navbar {
        background: rgba(10, 22, 40, 0.8);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(30, 144, 255, 0.2);
        padding: 15px 0;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
        animation: slideDown 0.5s ease;
    }
    
    @keyframes slideDown {
        from { transform: translateY(-100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    .navbar-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
    }
    
    .navbar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #ffffff;
        text-decoration: none;
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    .navbar-brand i {
        color: #4da6ff;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
    
    .user-menu {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 15px;
        background: rgba(77, 166, 255, 0.15);
        border-radius: 25px;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        color: white;
    }
    
    .user-menu:hover {
        background: rgba(77, 166, 255, 0.25);
    }
    
    .user-avatar {
        width: 35px;
        height: 35px;
        background: linear-gradient(135deg, #1e90ff, #00bfff);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
    }
    
    .section {
        padding: 100px 0 40px;
        min-height: 100vh;
    }
    
    .location-selector {
        background: rgba(15, 30, 55, 0.8);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 30px;
        border: 1px solid rgba(77, 166, 255, 0.3);
        animation: fadeInUp 0.6s ease;
    }
    
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .location-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 20px;
    }
    
    .location-title i {
        color: #4da6ff;
    }
    
    .city-select {
        width: 100%;
        padding: 15px 20px;
        background: rgba(10, 22, 40, 0.8);
        border: 2px solid rgba(77, 166, 255, 0.3);
        border-radius: 12px;
        color: white;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .city-select:focus {
        outline: none;
        border-color: #4da6ff;
    }
    
    .city-select option {
        background: #0a1628;
    }
    
    .current-weather {
        background: linear-gradient(135deg, rgba(30, 144, 255, 0.3) 0%, rgba(0, 191, 255, 0.2) 100%);
        backdrop-filter: blur(20px);
        border-radius: 30px;
        padding: 40px;
        margin-bottom: 30px;
        border: 1px solid rgba(77, 166, 255, 0.4);
        animation: fadeInUp 0.8s ease;
    }
    
    .weather-main {
        display: flex;
        align-items: center;
        gap: 30px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    
    .weather-icon {
        font-size: 6rem;
        color: #ffd700;
        text-shadow: 0 0 30px rgba(255, 215, 0, 0.5);
    }
    
    .weather-temp {
        font-size: 5rem;
        font-weight: 700;
        line-height: 1;
        background: linear-gradient(135deg, #ffffff 0%, #4da6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .weather-condition {
        font-size: 1.5rem;
        color: rgba(255, 255, 255, 0.9);
        margin-top: 5px;
    }
    
    .weather-location {
        font-size: 1.2rem;
        color: #4da6ff;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .weather-details {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 20px;
        margin-top: 30px;
    }
    
    .weather-detail {
        background: rgba(10, 22, 40, 0.5);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
    }
    
    .weather-detail i {
        font-size: 1.5rem;
        color: #4da6ff;
        margin-bottom: 10px;
    }
    
    .weather-detail-value {
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    .weather-detail-label {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.6);
        margin-top: 5px;
    }
    
    .forecast-section {
        margin-top: 30px;
        animation: fadeInUp 1s ease;
    }
    
    .forecast-title {
        font-size: 1.5rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
    }
    
    .forecast-title i {
        color: #4da6ff;
    }
    
    .forecast-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 15px;
    }
    
    .forecast-card {
        background: rgba(20, 40, 70, 0.6);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        border: 1px solid rgba(77, 166, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .forecast-card:hover {
        transform: translateY(-5px);
        border-color: rgba(77, 166, 255, 0.5);
    }
    
    .forecast-card.today {
        background: linear-gradient(135deg, rgba(30, 144, 255, 0.4) 0%, rgba(0, 191, 255, 0.3) 100%);
        border-color: rgba(77, 166, 255, 0.5);
    }
    
    .forecast-day {
        font-weight: 600;
        margin-bottom: 10px;
    }
    
    .forecast-icon {
        font-size: 2.5rem;
        margin: 10px 0;
    }
    
    .forecast-temps {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin-top: 10px;
    }
    
    .temp-high {
        font-weight: 600;
        color: #ff6b6b;
    }
    
    .temp-low {
        color: rgba(255, 255, 255, 0.6);
    }
    
    .ai-section {
        background: linear-gradient(135deg, rgba(138, 43, 226, 0.2) 0%, rgba(75, 0, 130, 0.2) 100%);
        border-radius: 25px;
        padding: 30px;
        margin-top: 30px;
        border: 1px solid rgba(138, 43, 226, 0.3);
        animation: fadeInUp 1.2s ease;
    }
    
    .ai-header {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 20px;
    }
    
    .ai-icon {
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, #8a2be2, #4b0082);
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    
    .ai-title {
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    .ai-content {
        background: rgba(10, 22, 40, 0.5);
        border-radius: 15px;
        padding: 20px;
        font-size: 1.1rem;
        line-height: 1.8;
    }
    
    .prayer-section {
        background: linear-gradient(135deg, rgba(46, 204, 113, 0.2) 0%, rgba(39, 174, 96, 0.2) 100%);
        border-radius: 25px;
        padding: 30px;
        margin-top: 30px;
        border: 1px solid rgba(46, 204, 113, 0.3);
        animation: fadeInUp 1.4s ease;
    }
    
    .prayer-header {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 25px;
    }
    
    .prayer-icon {
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, #2ecc71, #27ae60);
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    
    .prayer-title {
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    .prayer-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
    }
    
    .prayer-card {
        background: rgba(10, 22, 40, 0.5);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .prayer-card:hover {
        background: rgba(10, 22, 40, 0.7);
        transform: translateY(-3px);
    }
    
    .prayer-name {
        font-size: 1rem;
        font-weight: 600;
        color: #2ecc71;
        margin-bottom: 8px;
    }
    
    .prayer-time {
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .footer {
        text-align: center;
        padding: 40px 20px;
        margin-top: 50px;
        border-top: 1px solid rgba(77, 166, 255, 0.2);
    }
    
    .footer p {
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.9rem;
    }
</style>

<div class="bg-animation"></div>
<div class="clouds">
    <div class="cloud" style="width: 100px; height: 40px; top: 10%; left: -100px; animation-duration: 30s;"></div>
    <div class="cloud" style="width: 150px; height: 60px; top: 25%; left: -150px; animation-duration: 40s; animation-delay: 5s;"></div>
</div>
<div class="stars" id="stars"></div>

<!-- Navbar -->
<nav class="navbar">
    <div class="navbar-content">
        <a href="{{ url_for('dashboard') }}" class="navbar-brand">
            <i class="fas fa-cloud-sun"></i>
            <span>Hava Durumu</span>
        </a>
        <a href="{{ url_for('profile') }}" class="user-menu">
            <div class="user-avatar">{{ user.name[0]|upper if user.name else 'U' }}</div>
            <span>{{ user.name or user.email }}</span>
        </a>
    </div>
</nav>

<div class="section">
    <div class="container">
        <!-- Location Selector -->
        <div class="location-selector">
            <div class="location-title">
                <i class="fas fa-map-marker-alt"></i>
                <span>Konum Seçin</span>
            </div>
            <select class="city-select" id="citySelect" onchange="changeCity(this.value)">
                <option value="">-- Şehir Seçin --</option>
                {% for city in cities %}
                    <option value="{{ city.name }}" {% if city.name == selected_city %}selected{% endif %}>{{ city.name }}</option>
                {% endfor %}
            </select>
        </div>
        
        <!-- Current Weather -->
        <div class="current-weather" id="currentWeather">
            <div class="weather-main">
                <div class="weather-icon" id="weatherIcon"><i class="fas fa-sun"></i></div>
                <div class="weather-info">
                    <div class="weather-temp" id="weatherTemp">--°C</div>
                    <div class="weather-condition" id="weatherCondition">Yükleniyor...</div>
                    <div class="weather-location">
                        <i class="fas fa-map-marker-alt"></i>
                        <span id="weatherLocation">{{ selected_city }}</span>
                    </div>
                </div>
            </div>
            <div class="weather-details" id="weatherDetails"></div>
        </div>
        
        <!-- Forecast -->
        <div class="forecast-section">
            <div class="forecast-title">
                <i class="fas fa-calendar-week"></i>
                <span>7 Günlük Tahmin</span>
            </div>
            <div class="forecast-grid" id="forecastGrid"></div>
        </div>
        
        <!-- AI Section -->
        <div class="ai-section">
            <div class="ai-header">
                <div class="ai-icon"><i class="fas fa-robot"></i></div>
                <div class="ai-title">AI Günlük Değerlendirme</div>
            </div>
            <div class="ai-content" id="aiContent">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>AI analiz yapıyor...</span>
                </div>
            </div>
        </div>
        
        <!-- Prayer Times -->
        <div class="prayer-section">
            <div class="prayer-header">
                <div class="prayer-icon"><i class="fas fa-mosque"></i></div>
                <div>
                    <div class="prayer-title">Ezan Saatleri</div>
                    <div style="font-size: 0.9rem; color: rgba(255,255,255,0.6);">{{ today_date }}</div>
                </div>
            </div>
            <div class="prayer-grid" id="prayerGrid"></div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p>© 2024 Hava Durumu Uygulaması | Veritabanı ile Kimlik Doğrulama</p>
            <p style="margin-top: 10px;">
                <a href="{{ url_for('profile') }}" style="color: #4da6ff; text-decoration: none; margin-right: 20px;">
                    <i class="fas fa-user"></i> Profil
                </a>
                <a href="{{ url_for('logout') }}" style="color: #ff6b6b; text-decoration: none;">
                    <i class="fas fa-sign-out-alt"></i> Çıkış Yap
                </a>
            </p>
        </div>
    </div>
</div>

<script>
    // Stars
    const starsContainer = document.getElementById('stars');
    for (let i = 0; i < 80; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        starsContainer.appendChild(star);
    }
    
    const weatherIcons = {
        'Sunny': '<i class="fas fa-sun" style="color: #ffd700;"></i>',
        'Clear': '<i class="fas fa-moon" style="color: #f0e68c;"></i>',
        'Partly cloudy': '<i class="fas fa-cloud-sun" style="color: #87ceeb;"></i>',
        'Cloudy': '<i class="fas fa-cloud" style="color: #b0c4de;"></i>',
        'Overcast': '<i class="fas fa-cloud" style="color: #778899;"></i>',
        'Mist': '<i class="fas fa-smog" style="color: #a9a9a9;"></i>',
        'Rain': '<i class="fas fa-cloud-rain" style="color: #4682b4;"></i>',
        'Light rain': '<i class="fas fa-cloud-rain" style="color: #87ceeb;"></i>',
        'Heavy rain': '<i class="fas fa-cloud-showers-heavy" style="color: #4169e1;"></i>',
        'Snow': '<i class="fas fa-snowflake" style="color: #e0ffff;"></i>',
        'Thunder': '<i class="fas fa-bolt" style="color: #ffd700;"></i>',
        'default': '<i class="fas fa-cloud-sun" style="color: #4da6ff;"></i>'
    };
    
    function getWeatherIcon(condition) {
        return weatherIcons[condition] || weatherIcons['default'];
    }
    
    function changeCity(city) {
        if (city) {
            window.location.href = "{{ url_for('dashboard') }}?city=" + encodeURIComponent(city);
        }
    }
    
    document.addEventListener('DOMContentLoaded', function() {
        loadWeatherData();
        loadPrayerTimes();
        loadAISummary();
    });
    
    async function loadWeatherData() {
        try {
            const response = await fetch('/api/weather/{{ selected_city }}');
            const data = await response.json();
            
            if (data.error) {
                console.error(data.error);
                return;
            }
            
            const current = data.current;
            document.getElementById('weatherIcon').innerHTML = getWeatherIcon(current.condition.text);
            document.getElementById('weatherTemp').textContent = current.temp_c + '°C';
            document.getElementById('weatherCondition').textContent = current.condition.text;
            document.getElementById('weatherLocation').textContent = current.location;
            
            document.getElementById('weatherDetails').innerHTML = `
                <div class="weather-detail"><i class="fas fa-temperature-low"></i><div class="weather-detail-value">${current.feelslike_c}°C</div><div class="weather-detail-label">Hissedilen</div></div>
                <div class="weather-detail"><i class="fas fa-tint"></i><div class="weather-detail-value">${current.humidity}%</div><div class="weather-detail-label">Nem</div></div>
                <div class="weather-detail"><i class="fas fa-wind"></i><div class="weather-detail-value">${current.wind_kph} km/s</div><div class="weather-detail-label">Rüzgar</div></div>
                <div class="weather-detail"><i class="fas fa-compress-arrows-alt"></i><div class="weather-detail-value">${current.pressure_mb} mb</div><div class="weather-detail-label">Basınç</div></div>
                <div class="weather-detail"><i class="fas fa-eye"></i><div class="weather-detail-value">${current.vis_km} km</div><div class="weather-detail-label">Görüş</div></div>
                <div class="weather-detail"><i class="fas fa-sun"></i><div class="weather-detail-value">${current.uv}</div><div class="weather-detail-label">UV</div></div>
            `;
            
            const days = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
            let forecastHTML = '';
            
            data.forecast.forEach((day, index) => {
                const date = new Date(day.date);
                const dayName = index === 0 ? 'Bugün' : days[date.getDay()];
                
                forecastHTML += `
                    <div class="forecast-card ${index === 0 ? 'today' : ''}">
                        <div class="forecast-day">${dayName}</div>
                        <div class="forecast-icon">${getWeatherIcon(day.day.condition.text)}</div>
                        <div class="forecast-temps">
                            <span class="temp-high">${Math.round(day.day.maxtemp_c)}°</span>
                            <span class="temp-low">${Math.round(day.day.mintemp_c)}°</span>
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('forecastGrid').innerHTML = forecastHTML;
            
        } catch (error) {
            console.error('Hava durumu yükleme hatası:', error);
        }
    }
    
    async function loadPrayerTimes() {
        try {
            const response = await fetch('/api/prayer/{{ selected_city }}');
            const data = await response.json();
            
            if (data.error) {
                console.error(data.error);
                return;
            }
            
            const prayers = [
                { key: 'imsak', name: 'İmsak' },
                { key: 'sabah', name: 'Sabah' },
                { key: 'ogle', name: 'Öğle' },
                { key: 'ikindi', name: 'İkindi' },
                { key: 'aksam', name: 'Akşam' },
                { key: 'yatsi', name: 'Yatsı' }
            ];
            
            let html = '';
            prayers.forEach(p => {
                html += `<div class="prayer-card"><div class="prayer-name">${p.name}</div><div class="prayer-time">${data[p.key]}</div></div>`;
            });
            
            document.getElementById('prayerGrid').innerHTML = html;
            
        } catch (error) {
            console.error('Ezan saati yükleme hatası:', error);
        }
    }
    
    async function loadAISummary() {
        try {
            const response = await fetch('/api/ai-summary/{{ selected_city }}');
            const data = await response.json();
            document.getElementById('aiContent').innerHTML = '<p>' + data.summary + '</p>';
        } catch (error) {
            console.error('AI yükleme hatası:', error);
            document.getElementById('aiContent').innerHTML = '<p>AI değerlendirmesi şu an mevcut değil.</p>';
        }
    }
</script>
"""

PROFILE_TEMPLATE = BASE_STYLES + """
<style>
    .profile-container {
        padding-top: 100px;
        min-height: 100vh;
    }
    
    .profile-header {
        text-align: center;
        margin-bottom: 40px;
        animation: fadeInUp 0.6s ease;
    }
    
    .profile-avatar {
        width: 120px;
        height: 120px;
        background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3rem;
        font-weight: 700;
        margin: 0 auto 20px;
        box-shadow: 0 10px 30px rgba(30, 144, 255, 0.3);
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .profile-name {
        font-size: 2rem;
        font-weight: 600;
        margin-bottom: 5px;
    }
    
    .profile-email {
        color: rgba(255, 255, 255, 0.6);
    }
    
    .profile-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 40px;
    }
    
    .stat-card {
        background: rgba(20, 40, 70, 0.6);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        border: 1px solid rgba(77, 166, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        border-color: rgba(77, 166, 255, 0.5);
    }
    
    .stat-icon {
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, rgba(30, 144, 255, 0.3) 0%, rgba(0, 191, 255, 0.2) 100%);
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin: 0 auto 15px;
        color: #4da6ff;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #4da6ff;
    }
    
    .stat-label {
        color: rgba(255, 255, 255, 0.6);
        margin-top: 5px;
    }
    
    .account-section {
        background: rgba(20, 40, 70, 0.6);
        backdrop-filter: blur(20px);
        border-radius: 25px;
        padding: 30px;
        border: 1px solid rgba(77, 166, 255, 0.2);
    }
    
    .account-header {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 25px;
    }
    
    .account-icon {
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, rgba(231, 76, 60, 0.3) 0%, rgba(192, 57, 43, 0.2) 100%);
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        color: #e74c3c;
    }
    
    .account-title {
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    .btn-group {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .navbar {
        background: rgba(10, 22, 40, 0.8);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(30, 144, 255, 0.2);
        padding: 15px 0;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
    }
    
    .navbar-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
    }
    
    .navbar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #ffffff;
        text-decoration: none;
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    .navbar-brand i {
        color: #4da6ff;
    }
    
    .user-menu {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 15px;
        background: rgba(77, 166, 255, 0.15);
        border-radius: 25px;
        text-decoration: none;
        color: white;
    }
    
    .user-avatar {
        width: 35px;
        height: 35px;
        background: linear-gradient(135deg, #1e90ff, #00bfff);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
    }
</style>

<div class="bg-animation"></div>
<div class="stars" id="stars"></div>

<nav class="navbar">
    <div class="navbar-content">
        <a href="{{ url_for('dashboard') }}" class="navbar-brand">
            <i class="fas fa-cloud-sun"></i>
            <span>Hava Durumu</span>
        </a>
        <a href="{{ url_for('profile') }}" class="user-menu">
            <div class="user-avatar">{{ user.name[0]|upper if user.name else 'U' }}</div>
            <span>{{ user.name or user.email }}</span>
        </a>
    </div>
</nav>

<div class="container profile-container">
    <div class="profile-header">
        <div class="profile-avatar">{{ user.name[0]|upper if user.name else 'U' }}</div>
        <h1 class="profile-name">{{ user.name or 'Kullanıcı' }}</h1>
        <p class="profile-email">{{ user.email }}</p>
    </div>
    
    <div class="profile-stats">
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-map-marker-alt"></i></div>
            <div class="stat-value">{{ locations_count }}</div>
            <div class="stat-label">Kayıtlı Konum</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-calendar-alt"></i></div>
           <div class="stat-value">{{ user.created_at.strftime('%Y-%m-%d') if user.created_at else '-' }}</div>
            <div class="stat-label">Üyelik Tarihi</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
            <div class="stat-value">Aktif</div>
            <div class="stat-label">Hesap Durumu</div>
        </div>
    </div>
    
    <div class="account-section">
        <div class="account-header">
            <div class="account-icon"><i class="fas fa-cog"></i></div>
            <div class="account-title">Hesap İşlemleri</div>
        </div>
        <div class="btn-group">
            <a href="{{ url_for('dashboard') }}" class="btn btn-primary">
                <i class="fas fa-home"></i> Ana Sayfaya Dön
            </a>
            <a href="{{ url_for('logout') }}" class="btn btn-danger">
                <i class="fas fa-sign-out-alt"></i> Çıkış Yap
            </a>
        </div>
    </div>
</div>

<script>
    const starsContainer = document.getElementById('stars');
    for (let i = 0; i < 80; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        starsContainer.appendChild(star);
    }
</script>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return render_template_string(AUTH_TEMPLATE)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            flash(f'Hoş geldiniz, {user["name"] or user["email"]}!', 'success')
            return redirect(url_for('loading'))
        else:
            flash('E-posta veya şifre hatalı.', 'danger')
    
    return render_template_string(AUTH_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if not all([name, email, password, password_confirm]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return render_template_string(AUTH_TEMPLATE)
        
        if password != password_confirm:
            flash('Şifreler eşleşmiyor.', 'danger')
            return render_template_string(AUTH_TEMPLATE)
        
        if len(password) < 6:
            flash('Şifre en az 6 karakter olmalıdır.', 'warning')
            return render_template_string(AUTH_TEMPLATE)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # E-posta daha önce kayıtlı mı?
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            flash('Bu e-posta adresi zaten kayıtlı.', 'danger')
            return render_template_string(AUTH_TEMPLATE)
        
        # Yeni kullanıcı ekle
        password_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s) RETURNING id, email, name",
            (email, password_hash, name)
        )
        user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            flash('Kayıt başarılı! Hoş geldiniz!', 'success')
            return redirect(url_for('loading'))
        else:
            flash('Kayıt sırasında bir hata oluştu.', 'danger')
    
    return render_template_string(AUTH_TEMPLATE)

@app.route('/loading')
def loading():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template_string(LOADING_TEMPLATE, redirect_url=url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    selected_city = request.args.get('city', 'İstanbul')
    user = {
        'id': session['user_id'],
        'email': session['user_email'],
        'name': session.get('user_name')
    }
    today_date = datetime.now().strftime('%d %B %Y')
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        cities=TURKISH_CITIES,
        selected_city=selected_city,
        today_date=today_date,
        user=user
    )

@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('login'))
    
    # Kullanıcının lokasyon sayısını al
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM user_locations WHERE user_id = %s", (user_id,))
    locations_count = cur.fetchone()['count']
    cur.close()
    conn.close()
    
    return render_template_string(PROFILE_TEMPLATE, user=user, locations_count=locations_count)

@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('login'))

# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/weather/<city>')
def api_weather(city):
    try:
        current_data = WeatherService.get_current_weather(city)
        forecast_data = WeatherService.get_forecast(city, days=7)
        
        if not current_data or not forecast_data:
            return jsonify({'error': 'Hava durumu verisi alınamadı.'})
        
        return jsonify({
            'current': {
                'temp_c': current_data['current']['temp_c'],
                'feelslike_c': current_data['current']['feelslike_c'],
                'humidity': current_data['current']['humidity'],
                'wind_kph': current_data['current']['wind_kph'],
                'pressure_mb': current_data['current']['pressure_mb'],
                'vis_km': current_data['current']['vis_km'],
                'uv': current_data['current']['uv'],
                'condition': {
                    'text': current_data['current']['condition']['text'],
                    'icon': current_data['current']['condition']['icon']
                },
                'location': f"{current_data['location']['name']}, {current_data['location']['country']}"
            },
            'forecast': [
                {
                    'date': day['date'],
                    'day': {
                        'maxtemp_c': day['day']['maxtemp_c'],
                        'mintemp_c': day['day']['mintemp_c'],
                        'condition': {
                            'text': day['day']['condition']['text'],
                            'icon': day['day']['condition']['icon']
                        }
                    }
                }
                for day in forecast_data['forecast']['forecastday']
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/prayer/<city>')
def api_prayer(city):
    try:
        prayer_times = TimeService.get_prayer_times(city)
        if not prayer_times:
            return jsonify({'error': 'Ezan saatleri alınamadı.'})
        return jsonify(prayer_times)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/ai-summary/<city>')
def api_ai_summary(city):
    try:
        weather_data = WeatherService.get_forecast(city, days=1)
        summary = AIService.get_daily_weather_summary(weather_data, city)
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'summary': 'AI değerlendirmesi şu an mevcut değil.'})

# ═══════════════════════════════════════════════════════════════════════════════
# ANA FONKSİYON
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    print("\n" + "="*60)
    print("   🌤️  HAVA DURUMU UYGULAMASI  🌤️")
    print("="*60)
    print("\n📍 Uygulama: http://localhost:5050")
    print("📍 Veritabanı: Neon PostgreSQL")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5050, debug=True)
