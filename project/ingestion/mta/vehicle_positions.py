#!/usr/bin/env python
# coding: utf-8

# In[10]:


import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime, timezone
import os


# In[11]:


url = 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz'


# In[12]:


def fetch_feed():
    response = requests.get(url, timeout = 10)
    response.raise_for_status()
    return response.content


# In[13]:


def parse_feed(content):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    return feed


# In[14]:


def save_raw(content):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"project/data/raw/mta/vehicle_positions/vp_{ts}.pb"
    os.makedirs("project/data/raw/mta/vehicle_positions", exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


# In[15]:


def extract_jz_positions(feed):
    records = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        if v.trip.route_id not in ["J", "Z"]:
            continue
        records.append({
            "vehicle_id": entity.id,
            "trip_id": v.trip.trip_id,
            "route_id": v.trip.route_id,
            "stop_id": v.stop_id,
            "current_stop_sequence": v.current_stop_sequence,
            "current_status": v.current_status,        # STOPPED_AT, IN_TRANSIT_TO, INCOMING_AT
            "occupancy_status": v.occupancy_status if v.HasField("occupancy_status") else None,
            "timestamp": v.timestamp,                  # unix timestamp from MTA
            "event_time": datetime.now(timezone.utc).isoformat()
        })
    return records


# In[16]:


def main():
    content = fetch_feed()
    raw_path = save_raw(content)
    feed = parse_feed(content)
    records = extract_jz_positions(feed)
    print(f"Saved: {raw_path}")
    print(f"Total entities in feed: {len(feed.entity)}")
    print(f"J/Z vehicle position records: {len(records)}")
    for r in records[:5]:
        print(r)

    import sys
    sys.path.insert(0, '.')
    from project.storage import upload_file
    upload_file(raw_path, raw_path.replace("project/", ""))

if __name__ == "__main__":
    main()


# In[ ]:




