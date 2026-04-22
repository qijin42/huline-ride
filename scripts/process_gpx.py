#!/usr/bin/env python3
"""
process_gpx.py
Reads all GPX files from the gpx/ directory,
computes stats, and writes docs/ride_data.json.
"""

import os
import json
import math
import glob
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

GPX_DIR  = "gpx"
OUT_FILE = "docs/ride_data.json"

NS = {"gpx": "http://www.topografix.com/GPX/1/1"}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def parse_gpx(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()

    points = []
    for trkpt in root.findall(".//gpx:trkpt", NS):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        ele_el = trkpt.find("gpx:ele", NS)
        ele = float(ele_el.text) if ele_el is not None else None
        time_el = trkpt.find("gpx:time", NS)
        time_str = time_el.text if time_el is not None else None
        points.append({"lat": lat, "lon": lon, "ele": ele, "time": time_str})

    if not points:
        for wpt in root.findall(".//gpx:wpt", NS):
            lat = float(wpt.attrib["lat"])
            lon = float(wpt.attrib["lon"])
            ele_el = wpt.find("gpx:ele", NS)
            ele = float(ele_el.text) if ele_el is not None else None
            points.append({"lat": lat, "lon": lon, "ele": ele, "time": None})

    if not points:
        return None

    total_dist = 0.0
    for i in range(1, len(points)):
        total_dist += haversine(
            points[i-1]["lat"], points[i-1]["lon"],
            points[i]["lat"],   points[i]["lon"]
        )

    total_elev = 0.0
    for i in range(1, len(points)):
        if points[i]["ele"] is not None and points[i-1]["ele"] is not None:
            delta = points[i]["ele"] - points[i-1]["ele"]
            if delta > 0:
                total_elev += delta

    coords = [[p["lat"], p["lon"]] for p in points]
    if len(coords) > 2000:
        step = len(coords) // 2000
        coords = coords[::step]

    fname = os.path.basename(filepath)
    date_str = ""
    name = fname.replace(".gpx", "")
    parts = fname.split("_", 1)
    if len(parts) >= 1 and len(parts[0]) == 10:
        try:
            datetime.strptime(parts[0], "%Y-%m-%d")
            date_str = parts[0]
            name = parts[1].replace(".gpx", "").replace("_", " ") if len(parts) > 1 else parts[0]
        except ValueError:
            pass

    return {
        "file": fname,
        "date": date_str,
        "name": name,
        "distance": round(total_dist, 2),
        "elevation": round(total_elev, 1),
        "coords": coords,
        "pointCount": len(points),
    }


def main():
    gpx_files = sorted(glob.glob(os.path.join(GPX_DIR, "*.gpx")))
    print(f"Found {len(gpx_files)} GPX file(s)")

    tracks = []
    total_dist  = 0.0
    total_elev  = 0.0

    for fpath in gpx_files:
        print(f"  Processing: {fpath}")
        result = parse_gpx(fpath)
        if result:
            tracks.append(result)
            total_dist += result["distance"]
            total_elev += result["elevation"]
        else:
            print(f"    -> No track points found, skipping")

    total_days = len(tracks)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = {
        "totalDistance":  round(total_dist, 2),
        "totalElevation": round(total_elev, 1),
        "totalDays":      total_days,
        "lastUpdate":     now,
        "tracks":         tracks,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
