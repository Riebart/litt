#!/usr/bin/env python3

import json
import sys
import os
from datetime import datetime
import requests
import time

HARVEST_PERSONAL_ACCESS_TOKEN = os.environ["HARVEST_PERSONAL_ACCESS_TOKEN"]
HARVEST_ACCOUNT_ID = os.environ["HARVEST_ACCOUNT_ID"]

db = json.loads(sys.stdin.read())

aliases = db["Aliases"]


def harvest_param_from_tags(alias_values, param):
    candidates = [
        v for v in alias_values["Tags"] if v.startswith("Harvest" + param)
    ]
    if candidates == []:
        return None
    else:
        v = candidates[0].split(":")[1]
        # Try to numberize it if we can
        try:
            return int(v)
        except:
            return v


def find_alias(record):
    max_intersection = None
    max_intersecting_alias = None
    for alias_name, alias_values in aliases.items():
        intersection = set(alias_values["Tags"]).intersection(
            set(record["Tags"]))
        if max_intersection is None or len(intersection) > max_intersection:
            max_intersection = len(intersection)
            max_intersecting_alias = (alias_name, alias_values)
    return max_intersecting_alias


for record_id, record in db["Records"].items():
    # Don't double-entry
    if [t for t in record["Tags"] if t.startswith("HarvestEntryId")] != []:
        print("Skipping double-entry of %s" % record_id, file=sys.stderr)
        continue

    wall_clock_time = record["EndTime"] - record["StartTime"]
    interruption_time = 0.0
    if record.get("Interruptions", None) is not None:
        for i in record["Interruptions"]:
            interruption_time += db["Records"][
                i["Id"]]["EndTime"] - db["Records"][i["Id"]]["StartTime"]

    actual_time = wall_clock_time - interruption_time
    alias_name, alias_values = find_alias(record)

    # Update the tags to include all of the tags of the alias, since the alias may
    # have been updated since the record was created
    record["Tags"] = sorted(list(set(record["Tags"] + alias_values["Tags"])))

    description = record.get("Description", "")
    if description is None:
        notes = ""
    else:
        notes = description
    detail = record.get("Detail", "")
    if detail is not None and detail != "":
        notes = notes + "\n\n" + detail

    harvest_record = {
        "hours":
        actual_time / 3600.0,
        "project_id":
        harvest_param_from_tags(alias_values, "Project"),
        "task_id":
        harvest_param_from_tags(alias_values, "Task"),
        "spent_date":
        datetime.fromtimestamp(record["StartTime"]).strftime("%Y-%m-%d"),
        "notes":
        notes
    }

    if None in harvest_record.values():
        print(record_id,
              "SKIPPED due to missing Harvest tags",
              file=sys.stderr)
        continue

    record_body = json.dumps(harvest_record)
    print(record_id, file=sys.stderr)

    if HARVEST_ACCOUNT_ID != "" and HARVEST_PERSONAL_ACCESS_TOKEN != "":
        # Rate limit to about 60 requests/15 seconds since the official
        # limit is 100/15 seconds
        time.sleep(0.25)

        r = requests.post("https://api.harvestapp.com/api/v2/time_entries",
                          data=record_body,
                          headers={
                              "Harvest-Account-Id": HARVEST_ACCOUNT_ID,
                              "Authorization":
                              "Bearer %s" % HARVEST_PERSONAL_ACCESS_TOKEN,
                              "User-Agent": "litt sync to Harvest",
                              "Content-Type": "application/json"
                          })

        print(r.status_code, file=sys.stderr)

        try:
            record["Tags"].append("HarvestEntryId:%d" % r.json()["id"])
        except:
            print(r.status_code, file=sys.stderr)
            print(r.text, file=sys.stderr)

with open("events_%d.json" % int(time.time()), "w") as fp:
    fp.write(json.dumps(db))
