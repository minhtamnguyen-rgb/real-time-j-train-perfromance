#!/usr/bin/env python
# coding: utf-8

# In[9]:


import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime, timezone
import os


# In[10]:


URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts"


# In[11]:


def fetch_feed():
    response = requests.get(URL, timeout=10)
    response.raise_for_status()
    return response.content


# In[12]:


def parse_feed(content):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    return feed


# In[13]:


def save_raw(content):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"data/raw/mta/alerts/alerts_{ts}.pb"
    os.makedirs("data/raw/mta/alerts", exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


# In[14]:


def extract_jz_alerts(feed):
    records = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert

        # check if alert affects J or Z
        affects_jz = False
        for informed in alert.informed_entity:
            if informed.route_id in ["J", "Z"]:
                affects_jz = True
                break

        if not affects_jz:
            continue

        # get alert text
        header = ""
        description = ""
        if alert.header_text.translation:
            header = alert.header_text.translation[0].text
        if alert.description_text.translation:
            description = alert.description_text.translation[0].text

        records.append({
            "alert_id": entity.id,
            "route_ids": list(set(e.route_id for e in alert.informed_entity if e.route_id in ["J", "Z"])),
            "header": header,
            "description": description,
            "effect": alert.effect,
            "start_time": alert.active_period[0].start if alert.active_period else None,
            "end_time": alert.active_period[0].end if alert.active_period else None,
            "event_time": datetime.now(timezone.utc).isoformat()
        })
    return records


# In[15]:


def main():
    content = fetch_feed()
    raw_path = save_raw(content)
    feed = parse_feed(content)
    records = extract_jz_alerts(feed)
    print(f"Saved: {raw_path}")
    print(f"Total alerts in feed: {len(feed.entity)}")
    print(f"J/Z alerts: {len(records)}")
    for r in records[:3]:
        print(r)


# In[16]:


if __name__ == "__main__":
    main()


# In[ ]:




