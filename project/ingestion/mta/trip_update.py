#!/usr/bin/env python
# coding: utf-8

# In[2]:

# In[81]:


#ingestion mta
'''Exactly — this script is one step in a pipeline, not the whole pipeline itself.
Right now what you’ve built is:
a single ingestion task that you will later schedule and orchestrate'''
import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import os
from datetime import datetime, timezone


# In[82]:


url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz"


# In[83]:


def fetch_feed():
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.content


# In[84]:


def parse_feed(content):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    return feed


# In[85]:


def save_raw(content):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"project/data/raw/mta/trip_updates/jz_{ts}.pb"
    os.makedirs("project/data/raw/mta/trip_updates", exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


# In[86]:


def extract_jz(feed):
    records = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip = entity.trip_update
        if trip.trip.route_id not in ["J", "Z"]:
            continue
        for stu in trip.stop_time_update:
            records.append({
                "vehicle_id": entity.id,
                "trip_id": trip.trip.trip_id,
                "route_id": trip.trip.route_id,
                "stop_id": stu.stop_id,
                "arrival_delay": stu.arrival.delay if stu.HasField("arrival") else None,
                "departure_delay": stu.departure.delay if stu.HasField("departure") else None,
                "event_time": datetime.now(timezone.utc).isoformat()
            })
    return records


# In[87]:


def main():
    content = fetch_feed()
    raw_path = save_raw(content)
    feed = parse_feed(content)
    print(f"Saved: {raw_path}")
    print(f"Entities in feed: {len(feed.entity)}")


# In[88]:


if __name__ == "__main__":
    main()


# In[89]:


content = fetch_feed()
feed = parse_feed(content)
records = extract_jz(feed)
for r in records[:5]:
    print(r)


# In[ ]:




