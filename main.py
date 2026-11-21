import glob
import json
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests

HKT = timezone(timedelta(hours=8))
NOW_HKT = datetime.now(HKT)

# 香港天文台 (HKO) 與 漁護署 (AFCD) 官方數據端點
HKO_RHRREAD_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
HKO_WIND_CSV_URL = "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_10min_wind_uc.csv"
HKO_TIDE_CSV_URL = "https://data.weather.gov.hk/weatherAPI/hko_data/tide/ALL_uc.csv"
AFCD_FCZ_REALTIME_API_URL = os.getenv("AFCD_FCZ_API_URL", "")
AFCD_RED_TIDE_RSS_URL = "https://www.afcd.gov.hk/tc_chi/fisheries/hkredtide/rss/redtide_tc.xml"

# 56個潛點之水文、受風面與養魚區浮標對照表
DIVE_SITE_PROFILES = {
    "9.01-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["NW", "W"], "mud_sensitive": True, "base_score": 76},
    "9.01-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["S", "SW"], "mud_sensitive": True, "base_score": 74},
    "9.01-丙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["E", "SE", "S"], "mud_sensitive": True, "base_score": 73},
    "9.01-丁": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["S", "SW"], "mud_sensitive": False, "base_score": 74},
    "9.02-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["W", "NW"], "mud_sensitive": True, "base_score": 76},
    "9.02-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["W", "SW"], "mud_sensitive": True, "base_score": 74},
    "9.02-丙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["SE", "S", "SW", "W"], "mud_sensitive": True, "base_score": 72},
    "9.03-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["W", "NW"], "mud_sensitive": False, "base_score": 82},
    "9.03-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["E", "SE", "W", "SW"], "mud_sensitive": True, "base_score": 76},
    "9.04-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["N", "NE"], "mud_sensitive": False, "base_score": 78},
    "9.04-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["N", "NE", "E", "SE"], "mud_sensitive": False, "base_score": 77},
    "9.05-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["SW", "W", "NW"], "mud_sensitive": False, "base_score": 83},
    "9.05-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["S", "SW", "W", "NW"], "mud_sensitive": False, "base_score": 82},
    "9.05-丙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 81},
    "9.06-甲": {"region": "西貢", "wind_stn": "橫瀾島", "fcz_buoy": "糧船灣", "exposed": ["NE", "E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 88},
    "9.06-乙": {"region": "西貢", "wind_stn": "橫瀾島", "fcz_buoy": "糧船灣", "exposed": ["N", "NE", "E", "SE"], "mud_sensitive": False, "base_score": 86},
    "9.07-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["SE", "S", "SW"], "mud_sensitive": False, "base_score": 76},
    "9.07-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["SE", "S", "SW"], "mud_sensitive": False, "base_score": 75},
    "9.08-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["NW", "N", "NE", "E"], "mud_sensitive": True, "base_score": 66},
    "9.08-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["NW", "N", "NE", "E"], "mud_sensitive": True, "base_score": 66},
    "9.09-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 70},
    "9.10-甲": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["NW", "N", "NE"], "mud_sensitive": True, "base_score": 70},
    "9.10-乙": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["NE", "E", "SE"], "mud_sensitive": True, "base_score": 71},
    "9.11":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["W", "NW"], "mud_sensitive": True, "base_score": 68},
    "9.12":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "鹽田仔", "exposed": ["E", "SE"], "mud_sensitive": True, "base_score": 65},
    "9.13":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["SE", "S", "SW"], "mud_sensitive": False, "base_score": 80},
    "9.14":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["SE", "S", "SW"], "mud_sensitive": False, "base_score": 82},
    "9.15":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 84},
    "9.16":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 85},
    "9.17":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["N", "E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 85},
    "9.18-甲": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["SW", "W", "NW"], "mud_sensitive": False, "base_score": 79},
    "9.18-乙": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["NW", "N", "NE"], "mud_sensitive": False, "base_score": 79},
    "9.18-丙": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 80},
    "9.19":    {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "較寮灣", "exposed": ["N", "NE"], "mud_sensitive": True, "base_score": 75},
    "9.20-主區": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 68},
    "9.20-乙/分區": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 69},
    "9.21-甲": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["NW", "N", "NE"], "mud_sensitive": False, "base_score": 74},
    "9.21-乙": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["SE", "S"], "mud_sensitive": False, "base_score": 75},
    "9.21-東岸補充": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "往灣", "exposed": ["NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 76},
    "9.22":    {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["N", "NE", "E", "SE"], "mud_sensitive": False, "base_score": 81},
    "9.23-甲": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["N", "NE", "E", "SE"], "mud_sensitive": True, "base_score": 65},
    "9.23-乙": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["SE", "S", "SW"], "mud_sensitive": True, "base_score": 64},
    "9.24":    {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 62},
    "9.25-甲": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NW", "N"], "mud_sensitive": True, "base_score": 66},
    "9.25-乙": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NE", "E"], "mud_sensitive": True, "base_score": 67},
    "9.26-甲": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "吉澳", "exposed": ["NE"], "mud_sensitive": True, "base_score": 62},
    "9.27":    {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "滘西", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 78},
    "9.28-甲": {"region": "大埔", "wind_stn": "塔門", "fcz_buoy": "塔門", "exposed": ["N", "NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 85},
    "9.29-甲": {"region": "離島", "wind_stn": "橫瀾島", "fcz_buoy": "蒲台", "exposed": ["NW", "N", "W"], "mud_sensitive": False, "base_score": 84},
    "9.29-乙": {"region": "離島", "wind_stn": "橫瀾島", "fcz_buoy": "蒲台", "exposed": ["W", "SW", "S"], "mud_sensitive": False, "base_score": 84},
    "9.30":    {"region": "西貢", "wind_stn": "將軍澳", "fcz_buoy": "東龍洲", "exposed": [], "mud_sensitive": False, "base_score": 0, "reclaimed": True},
    "9.32（補充）": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["E", "SE", "S"], "mud_sensitive": False, "base_score": 80},
    "9.33（補充）": {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": ["NE", "E", "SE", "S"], "mud_sensitive": False, "base_score": 83},
    "9.34（補充）": {"region": "離島", "wind_stn": "橫瀾島", "fcz_buoy": "蒲台", "exposed": ["E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 86},
    "9.35（補充）": {"region": "離島", "wind_stn": "橫瀾島", "fcz_buoy": "蒲台", "exposed": ["E", "SE", "S", "SW"], "mud_sensitive": False, "base_score": 86},
    "9.36（補充）": {"region": "離島", "wind_stn": "長洲", "fcz_buoy": "索罟灣", "exposed": ["E", "SE", "S"], "mud_sensitive": True, "base_score": 60},
}

WIND_DIR_MAP = {
    "北": "N", "東北": "NE", "東": "E", "東南": "SE",
    "南": "S", "西南": "SW", "西": "W", "西北": "NW"
}

def fetch_hko_data():
    rainfall_dict, wind_dict, tide_trend = {}, {}, "未知"
    try:
        r = requests.get(HKO_RHRREAD_URL, timeout=15).json()
        for item in r.get("rainfall", {}).get("data", []):
            rainfall_dict[item.get("place", "")] = item.get("max", 0)
    except Exception as e:
        print(f"Rainfall API error: {e}")

    try:
        df_wind = pd.read_csv(HKO_WIND_CSV_URL)
        for _, row in df_wind.iterrows():
            stn = str(row.iloc[1]).strip()
            w_dir_tc = str(row.iloc[2]).strip()
            w_spd = pd.to_numeric(row.iloc[3], errors="coerce")
            wind_dict[stn] = {
                "dir_tc": w_dir_tc,
                "dir_code": WIND_DIR_MAP.get(w_dir_tc, ""),
                "speed_kmh": 0 if pd.isna(w_spd) else float(w_spd)
            }
    except Exception as e:
        print(f"Wind CSV error: {e}")

    try:
        df_tide = pd.read_csv(HKO_TIDE_CSV_URL)
        tmw = df_tide[df_tide.iloc[:, 0].astype(str).str.contains("大廟灣")].tail(2)
        if len(tmw) == 2:
            tide_trend = "漲潮" if float(tmw.iloc[1, 3]) >= float(tmw.iloc[0, 3]) else "退潮"
    except Exception as e:
        print(f"Tide CSV error: {e}")

    return rainfall_dict, wind_dict, tide_trend

def fetch_afcd_buoy_and_redtide():
    buoy_data = {}
    red_tide_text = ""
    try:
        resp_rt = requests.get(AFCD_RED_TIDE_RSS_URL, timeout=12)
        if resp_rt.status_code == 200:
            resp_rt.encoding = "utf-8"
            red_tide_text = resp_rt.text
    except Exception as e:
        print(f"Red Tide RSS warning: {e}")

    if AFCD_FCZ_REALTIME_API_URL:
        try:
            r_fcz = requests.get(AFCD_FCZ_REALTIME_API_URL, timeout=15).json()
            items = r_fcz if isinstance(r_fcz, list) else r_fcz.get("data", [])
            for item in items:
                zone_name = str(item.get("zone") or item.get("fcz_name") or item.get("name", "")).strip()
                turb = pd.to_numeric(item.get("turbidity") or item.get("turbidity_ntu"), errors="coerce")
                chl = pd.to_numeric(item.get("chlorophyll") or item.get("chlorophyll_a"), errors="coerce")
                buoy_data[zone_name] = {
                    "turbidity_ntu": None if pd.isna(turb) else round(float(turb), 2),
                    "chlorophyll_ugl": None if pd.isna(chl) else round(float(chl), 2)
                }
        except Exception as e:
            print(f"AFCD Buoy API warning: {e}")

    for z in ["吉澳", "往灣", "塔門", "較寮灣", "鹽田仔", "滘西", "糧船灣", "東龍洲", "蒲台", "索罟灣"]:
        if z not in buoy_data:
            buoy_data[z] = {"turbidity_ntu": None, "chlorophyll_ugl": None}
        buoy_data[z]["red_tide_alert"] = (z in red_tide_text)

    return buoy_data

def calculate_dive_site_visibility(site_key, rainfall_dict, wind_dict, tide_trend, buoy_data):
    prof = DIVE_SITE_PROFILES.get(site_key, {"region": "西貢", "wind_stn": "西貢", "fcz_buoy": "糧船灣", "exposed": [], "mud_sensitive": False, "base_score": 72})

    if prof.get("reclaimed"):
        return {
            "潛點唯一碼": site_key,
            "預估能見度等級": "不適用（已填海）",
            "預估能見度範圍": "0 米（陸地）",
            "能見度指數_0至100": 0,
            "鄰近養魚區浮標站": "不適用",
            "浮標濁度_NTU": None,
            "浮標葉綠素_ugL": None,
            "紅潮預警": "不適用",
            "當前氣象水文摘要": "該處現已填海成為將軍澳工業邨東南岸，無法進行潛水活動。",
            "影響因子明細": "已填海地點"
        }

    score = prof["base_score"]
    factors = []

    month = NOW_HKT.month
    if 5 <= month <= 9:
        score -= 10
        factors.append("夏季西南流/雨季(-10)")
    elif month in [10, 11, 12, 1, 2]:
        score += 5
        factors.append("秋冬水清期(+5)")

    rain_mm = rainfall_dict.get(prof["region"], 0)
    if rain_mm >= 20:
        score -= 35
        factors.append(f"{prof['region']}暴雨{rain_mm}mm(-35)")
    elif rain_mm >= 5:
        score -= 20
        factors.append(f"{prof['region']}有雨{rain_mm}mm(-20)")
    elif rain_mm > 0:
        score -= 8
        factors.append(f"{prof['region']}微雨{rain_mm}mm(-8)")

    w_info = wind_dict.get(prof["wind_stn"], {"dir_tc": "無風", "dir_code": "", "speed_kmh": 0})
    w_spd = w_info["speed_kmh"]
    is_exposed = w_info["dir_code"] in prof["exposed"]

    if w_spd >= 30:
        penalty = 28 if is_exposed else 15
        score -= penalty
        factors.append(f"{prof['wind_stn']}{w_info['dir_tc']}風{int(w_spd)}km/h(-{penalty})")
    elif w_spd >= 18:
        penalty = 16 if is_exposed else 6
        score -= penalty
        factors.append(f"{prof['wind_stn']}{w_info['dir_tc']}風{int(w_spd)}km/h(-{penalty})")

    if prof["mud_sensitive"] and (rain_mm > 0 or w_spd >= 20):
        score -= 8
        factors.append("沙泥底易揚塵(-8)")

    if tide_trend == "漲潮":
        score += 4
        factors.append("漲潮清流(+4)")
    elif tide_trend == "退潮":
        score -= 4
        factors.append("退潮濁流(-4)")

    fcz_name = prof["fcz_buoy"]
    b_info = buoy_data.get(fcz_name, {})
    turb = b_info.get("turbidity_ntu")
    chl = b_info.get("chlorophyll_ugl")
    rt_alert = b_info.get("red_tide_alert", False)

    if turb is not None:
        if turb >= 10.0:
            score -= 30
            factors.append(f"{fcz_name}高濁度{turb}NTU(-30)")
        elif turb >= 5.0:
            score -= 15
            factors.append(f"{fcz_name}偏濁{turb}NTU(-15)")
        elif turb <= 2.0:
            score += 6
            factors.append(f"{fcz_name}極清{turb}NTU(+6)")

    if chl is not None:
        if chl >= 15.0:
            score -= 28
            factors.append(f"{fcz_name}藻華{chl}ug/L(-28)")
        elif chl >= 8.0:
            score -= 14
            factors.append(f"{fcz_name}葉綠素偏高{chl}ug/L(-14)")

    if rt_alert:
        score -= 25
        factors.append(f"紅潮報告提及{fcz_name}(-25)")

    score = max(10, min(98, score))

    if score >= 75:
        grade, est_meters = "優", "6–10+ 米"
    elif score >= 52:
        grade, est_meters = "良", "3–6 米"
    else:
        grade, est_meters = "差", "< 3 米"

    turb_str = f"{turb} NTU" if turb is not None else "待接入"
    chl_str = f"{chl} ug/L" if chl is not None else "待接入"

    return {
        "潛點唯一碼": site_key,
        "預估能見度等級": grade,
        "預估能見度範圍": est_meters,
        "能見度指數_0至100": score,
        "鄰近養魚區浮標站": f"{fcz_name}養魚區",
        "浮標濁度_NTU": turb,
        "浮標葉綠素_ugL": chl,
        "紅潮預警": "是（水色異常）" if rt_alert else "無",
        "當前氣象水文摘要": f"雨量:{rain_mm}mm | {prof['wind_stn']}:{w_info['dir_tc']}({int(w_spd)}km/h) | 潮汐:{tide_trend} | {fcz_name}濁度:{turb_str} / 葉綠素:{chl_str}",
        "影響因子明細": "；".join(factors) if factors else "海況平穩"
    }

def main():
    candidates = [f for f in glob.glob("*.csv") if f != "live_visibility.csv"]
    if not candidates:
        raise FileNotFoundError("找不到原始潛點 CSV 檔案")
    input_csv = candidates[0]
    df = pd.read_csv(input_csv)

    rainfall_dict, wind_dict, tide_trend = fetch_hko_data()
    buoy_data = fetch_afcd_buoy_and_redtide()
    update_time_str = NOW_HKT.strftime("%Y-%m-%d %H:%M:%S HKT")

    vis_results = []
    for _, row in df.iterrows():
        sub = str(row["分區代號"]).strip() if pd.notna(row["分區代號"]) and str(row["分區代號"]).strip() != "" else ""
        site_key = f"{row['潛點編號']}-{sub}" if sub else str(row["潛點編號"])
        res = calculate_dive_site_visibility(site_key, rainfall_dict, wind_dict, tide_trend, buoy_data)
        res["更新時間"] = update_time_str
        vis_results.append(res)

    df_vis = pd.DataFrame(vis_results)
    df_out = pd.concat([df, df_vis], axis=1)

    # 輸出標準 CSV
    df_out.to_csv("live_visibility.csv", index=False, encoding="utf-8-sig")

    # 輸出 100% 符合 ArcGIS Online 規範的 GeoJSON（確保無 NaN）
    features = []
    for _, row in df_out.iterrows():
        clean_props = {}
        for k, v in row.items():
            if pd.isna(v):
                clean_props[str(k)] = None
            elif hasattr(v, "item"):
                clean_props[str(k)] = v.item()
            else:
                clean_props[str(k)] = v

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["Longitude"]), float(row["Latitude"])]
            },
            "properties": clean_props
        })

    api_payload = {
        "type": "FeatureCollection",
        "features": features
    }

    with open("live_visibility.geojson", "w", encoding="utf-8") as f:
        json.dump(api_payload, f, ensure_ascii=False, allow_nan=False, indent=2)

    print(f"[{update_time_str}] 成功更新 {len(features)} 個潛點！")

if __name__ == "__main__":
    main()
