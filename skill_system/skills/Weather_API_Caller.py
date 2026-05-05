# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: Weather_API_Caller
# AGENT_SKILL_DESC: 실시간 날씨 정보를 조회합니다. 도시명을 주면 현재 날씨, 기온, 습도를 반환합니다.
# AGENT_SKILL_ARGS: city(str) - 도시명 (기본값: 서울)
# AGENT_SKILL_RETURNS: 현재 기온, 날씨 상태, 습도, 풍속
r"""
Weather_API_Caller: wttr.in API를 이용하여 특정 지역의 현재 날씨, 체감온도, 강수확률, 내일 예보를 조회합니다.
지역명은 한국어 또는 영어 모두 사용 가능합니다. 미입력 시 서울(Seoul) 기준으로 조회합니다.
사용 예: <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\Weather_API_Caller.py</CMD>
         <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\Weather_API_Caller.py "부산"</CMD>
         <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\Weather_API_Caller.py "Tokyo"</CMD>
         <CMD>python C:\ai\Antigravity_Memory_Engine\skill_system\skills\Weather_API_Caller.py "New York"</CMD>
"""
import sys
import io
import warnings
warnings.filterwarnings("ignore")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request
import json

# 한국어 지명 -> wttr.in 검색 가능한 영문명 변환 사전
KO_TO_EN = {
    "서울": "Seoul", "부산": "Busan", "인천": "Incheon", "대구": "Daegu",
    "대전": "Daejeon", "광주": "Gwangju", "울산": "Ulsan", "수원": "Suwon",
    "성남": "Seongnam", "고양": "Goyang", "창원": "Changwon", "용인": "Yongin",
    "구리": "Guri", "강남": "Gangnam,Seoul", "제주": "Jeju", "춘천": "Chuncheon",
    "전주": "Jeonju", "청주": "Cheongju", "여수": "Yeosu", "포항": "Pohang",
    "도쿄": "Tokyo", "오사카": "Osaka", "베이징": "Beijing", "상하이": "Shanghai",
    "뉴욕": "New York", "런던": "London", "파리": "Paris", "시드니": "Sydney",
    "두바이": "Dubai", "방콕": "Bangkok", "싱가포르": "Singapore",
}

DEFAULT_CITY = "Seoul"

def get_weather(city_input: str = DEFAULT_CITY) -> str:
    # 한국어 지명 변환
    city = KO_TO_EN.get(city_input.strip(), city_input.strip())
    city_encoded = city.replace(" ", "+")
    display_name = city_input  # 사용자가 입력한 원래 이름 유지

    url = f"https://wttr.in/{city_encoded}?format=j1"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.64.1'})
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode('utf-8'))

        c = data['current_condition'][0]
        temp_c = c.get('temp_C', '?')
        feels_like = c.get('FeelsLikeC', '?')
        humidity = c.get('humidity', '?')
        wind_kmph = c.get('windspeedKmph', '?')
        desc_en = c.get('weatherDesc', [{}])[0].get('value', '')
        visibility = c.get('visibility', '?')
        uv_index = c.get('uvIndex', '?')

        # 날씨 이모지 매핑
        WEATHER_EMOJI = {
            'sunny': '☀️', 'clear': '☀️', 'cloudy': '☁️', 'overcast': '☁️',
            'rain': '🌧️', 'drizzle': '🌦️', 'snow': '❄️', 'fog': '🌫️',
            'thunder': '⛈️', 'blizzard': '🌨️', 'mist': '🌫️', 'partly': '⛅'
        }
        desc_lower = desc_en.lower()
        emoji = next((v for k, v in WEATHER_EMOJI.items() if k in desc_lower), '🌤️')

        # 오늘/내일 예보
        today = data['weather'][0] if data.get('weather') else {}
        tomorrow = data['weather'][1] if len(data.get('weather', [])) > 1 else {}

        def forecast_str(w):
            if not w:
                return "정보 없음"
            min_t = w.get('mintempC', '?')
            max_t = w.get('maxtempC', '?')
            rain = w.get('hourly', [{}])[0].get('chanceofrain', '?') if w.get('hourly') else '?'
            snow = w.get('hourly', [{}])[0].get('chanceofsnow', '?') if w.get('hourly') else '?'
            return f"{min_t}°C ~ {max_t}°C | 강수 {rain}% | 강설 {snow}%"

        result = (
            f"{emoji} [{display_name} 현재 날씨]\n"
            f"┌ 날씨 상태: {desc_en}\n"
            f"├ 기온: {temp_c}°C (체감 {feels_like}°C)\n"
            f"├ 습도: {humidity}% | 바람: {wind_kmph} km/h\n"
            f"├ 가시거리: {visibility} km | UV 지수: {uv_index}\n"
            f"├ 오늘 예보: {forecast_str(today)}\n"
            f"└ 내일 예보: {forecast_str(tomorrow)}"
        )
        return result

    except Exception as e:
        return (f"[Weather_API_Caller] '{display_name}' 날씨 조회 실패: {e}\n"
                f"영문 지명(예: Seoul, Busan, Tokyo)으로 다시 시도해 주세요.")

if __name__ == "__main__":
    # 인자가 없으면 서울(기본값), 있으면 해당 지역
    if len(sys.argv) < 2:
        city_input = DEFAULT_CITY
        print(f"[INFO] 지역 미입력 → 기본값 '{DEFAULT_CITY}' 조회")
    else:
        city_input = " ".join(sys.argv[1:])

    print(get_weather(city_input))