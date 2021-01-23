#!/usr/bin/env python3
"""
Tracking time against various projects from the CLI.

Exit codes:

- 0: Time successfully logged
- 1: Stopwatch running when 'start' command issued
- 2: Stopwatch not running when 'stop' command issued
- 3: Interruption attempted with ongoing interruption
- 4: Stopwatch resumption from interruption without ongoing stopwatch
- 5: Attempt to resume from an interruption without an open interruption
- 6: Attempt to log a finite interval neither endpoint was specified
- 7: Attempt to log a finite interval where the start does not strictly precede the end
- 8: Unable to parse a given timespec
- 9: Attempt to edit a record with an ID that doesn't exist.
- 10: A hook failed to execute properly
- 11: A sortkey was specified for `tt ls`, but the key doesn't exist for one or more items in the log
- 127: A dryrun was specified.
"""

import os
import sys
import copy
import json
import time
import base64
from os.path import isdir, isfile  # pylint: disable=C0412
from os.path import join as pathjoin  # pylint: disable=C0412
from argparse import ArgumentParser

try:
    import yaml
except ImportError:
    pass

VALID_RECORD_SORT_KEYS = [
    "CommitTime", "StartTime", "EndTime", "Description", "ID", "Detail"
]


def __record_sort_keys(k):
    if k in VALID_RECORD_SORT_KEYS:
        return k
    print("Sort key must be one of: %s" % str(VALID_RECORD_SORT_KEYS),
          file=sys.stderr)
    raise ValueError("Sort key must be one of: %s" %
                     str(VALID_RECORD_SORT_KEYS))


def __dotdir():
    if sys.platform == "win32":
        return pathjoin(os.environ.get("HOMEDRIVE", ""),
                        os.environ.get("HOMEPATH", ""), ".litt")
    else:
        return pathjoin(os.environ.get("HOME", ""), ".litt")


def check_dotfile():
    """
    Check the dotfiles for an existing database structure.
    """
    try:
        if isdir(__dotdir()):
            if isfile("%s/events.json" % __dotdir()):
                if isfile("%s/config.json" % __dotdir()):
                    return True
        return False
    except:  # pylint: disable=W0702
        return False


def init_dotfiles():
    """
    Initialize the dotfiles for the first time.
    """
    try:
        os.makedirs(__dotdir(), mode=0o755)
    except:  # pylint: disable=W0702
        pass

    with open("%s/events.json" % __dotdir(), "w") as ofp:
        ofp.write(
            json.dumps(
                {
                    "Stopwatch": None,
                    "Interruption": None,
                    "Aliases": dict(),
                    "Records": dict()
                },
                indent=2,
                sort_keys=True))

    with open("%s/config.json" % __dotdir(), "w") as ofp:
        ofp.write(
            json.dumps({"OutputFormat": "json"}, indent=2, sort_keys=True))


def load_hooks():
    """
    List all files in the hook directories, and determine which are suitable for execution as hook
    events.
    """
    from os import listdir, access, X_OK
    hooks = dict(pre_load=list(),
                 pre_commit=list(),
                 post_commit=list(),
                 pre_config_write=list(),
                 post_config_write=list())

    for hook_key, binaries in hooks.items():
        try:
            for hookfile in listdir("%s/hooks/%s" % (__dotdir(), hook_key)):
                hook_fullpath = "%s/hooks/%s/%s" % (__dotdir(), hook_key,
                                                    hookfile)
                if isfile(hook_fullpath) and access(hook_fullpath, X_OK):
                    binaries.append(hook_fullpath)
            binaries.sort()
        except FileNotFoundError:  # pylint: disable=E0602
            pass

    return hooks


def run_hooks(hookevent, hooks, data):
    """
    Run all hooks for a given event name, passing the JSON serialized data into the hook on stdin.
    """
    import subprocess
    for hookfile in hooks[hookevent]:
        proc = subprocess.Popen((hookfile, hookevent),
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=__dotdir())
        proc.stdin.write(json.dumps(data, sort_keys=True).encode("utf-8"))
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            print("%s hook returned non-zero, aborting." % hookevent,
                  file=sys.stderr)
            print(stdout.decode("utf-8"))
            print(stderr.decode("utf-8"))
            sys.exit(10)


def __human_alias(alias):
    # An alias has a limited number of properties right now:
    ret = ""
    if "Description" in alias:
        ret += "    Description: %s\n" % alias["Description"]
    if "Tags" in alias:
        ret += "     Tags: %s\n" % ",".join(alias["Tags"])
    if "Detail" in alias:
        ret += "     Details:\n    %s\n" % alias["Detail"]
    return ret


def __seconds_to_hhmmss(seconds):
    if seconds < 60:
        if seconds < 10:
            duration_string = "%.2fs" % seconds
        else:
            duration_string = "%ds" % seconds
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        duration_string = "%dh %02dm" % (hours, minutes)

    return duration_string


def __human_record(record):
    ret = ""
    if "StartTime" in record:
        ret += "Record started at: %s\n" % __timestamp_to_iso(
            record["StartTime"])
    if "EndTime" in record:
        if record["EndTime"] is None:
            ret += "Recording is still ongoing.\n"
            ret += "Elapsed wall-clock time: %s\n" % __seconds_to_hhmmss(
                __parse_time("now") - record["StartTime"])
        else:
            ret += "Record ended at: %s\n" % __timestamp_to_iso(
                record["EndTime"])
            ret += "Elapsed wall-clock time: %s\n" % __seconds_to_hhmmss(
                record["EndTime"] - record["StartTime"])
    if "Description" in record:
        ret += "Description: %s\n" % record["Description"]
    if "Tags" in record:
        ret += "Tags: %s\n" % ",".join(record["Tags"])
    if "Detail" in record:
        ret += "Details:\n    %s\n" % record["Detail"]
    if "StructuredData" in record:
        ret += "StructuredData:\n    %s\n" % record["StructuredData"]
    return ret + "\n"


def __write_output(obj,
                   pargs,
                   config,
                   human_hint,
                   dict_as_entries=False,
                   outfile=sys.stdout):
    fmt = config[
        "OutputFormat"] if pargs.output_format is None else pargs.output_format
    if fmt == "json":
        print(json.dumps(({i["key"]: i["value"]
                           for i in obj} if dict_as_entries else obj),
                         sort_keys=True,
                         indent=4),
              file=outfile)
    elif fmt == "json-compact":
        print(json.dumps(({i["key"]: i["value"]
                           for i in obj} if dict_as_entries else obj),
                         sort_keys=True),
              file=outfile)
    elif fmt == "yaml":
        print(yaml.dump(({i["key"]: i["value"]
                          for i in obj} if dict_as_entries else obj),
                        default_flow_style=False).strip(),
              file=outfile)
    elif fmt == "human":
        # For human readable output, we need to know what the human hint is.
        if human_hint == "ID":
            # It's just an ID string, so just print it out saying so.
            print("Committed Record ID: %s" % obj, file=outfile)
        elif human_hint == "Config":
            # It is the configuration object, so print it in pseudo-yaml
            for k, v in obj.items():
                print("%s: %s" % (str(k), str(v)), file=outfile)
        elif human_hint.startswith("Alias"):
            # This will always be a dictionary mapping alias keys to parameter sets.
            for key, alias in obj.items():
                print("Alias \"%s\"" % key, file=outfile)
                print(__human_alias(alias), file=outfile)
        elif human_hint.startswith("Record"):
            # This will always be a dictionary, or dictionary as entries,
            # but may sometimes be a bare record.
            if "StartTime" in obj:
                print(__human_record(obj), file=outfile)
            else:
                if dict_as_entries:
                    for entry in obj:
                        key = entry["key"]
                        value = entry["value"]
                        print("Record \"%s\"" % key, file=outfile)
                        print(__human_record(value), file=outfile)
                else:
                    for key, value in obj.items():
                        print("Record \"%s\"" % key, file=outfile)
                        print(__human_record(value), file=outfile)
        else:
            raise ValueError("Undefined human hint '%s'" % human_hint)


def __load_state():
    """
    Load time tracking events from the DB in the dotdirectory.
    """
    with open(pathjoin(__dotdir(), "events.json"), "r") as fp:
        state = json.loads(fp.read())
    with open(pathjoin(__dotdir(), "config.json"), "r") as fp:
        config = json.loads(fp.read())

    return state, config


def __write_state(state, hooks):
    """
    Save time tracking events to the dotfile
    """
    with open("%s/events.json" % __dotdir(), "w") as ofp:
        ofp.write(json.dumps(state, indent=2, sort_keys=True))


def __write_config(config, hooks):
    """
    Save the configuration to the persistent file for future invocations.
    """
    run_hooks("pre_config_write", hooks, config)
    with open("%s/config.json" % __dotdir(), "w") as ofp:
        ofp.write(json.dumps(config, indent=2, sort_keys=True))
    run_hooks("post_config_write", hooks, config)


def cmd_base(pargs, state, config, outfile=sys.stdout):
    """
    Print out the status of any currently running stopwatch or interruption timer.
    """
    if state["Stopwatch"] is not None:
        __write_output(state["Stopwatch"],
                       pargs,
                       config,
                       "Record.Incomplete",
                       outfile=outfile)
        if state["Interruption"] is not None:
            __write_output(state["Interruption"],
                           pargs,
                           config,
                           "Record.Incomplete",
                           outfile=outfile)

    return None


def cmd_config(pargs, _, config, hooks):
    """
    Handle configuration commands include printing the configuration and updating values.
    """
    options = dict(output_format="OutputFormat")

    opts = dict([(optkey, getattr(pargs, optkey))
                 for optkey in options.keys()])  # pylint: disable=C0201

    # If all supported options are None (that is, unspecified), then just print the current
    # configuration
    if set(opts.values()) == set([None]):
        __write_output(config, pargs, config, "Config")
    # Otherwise, for those that are not None, update the values, and write them back to the file.
    else:
        for key, val in opts.items():
            if val is not None:
                config[options[key]] = val
        __write_config(config, hooks)

    return None


def cmd_alias(pargs, state, config):
    """
    Create, modify, delete, and list aliases.
    """
    images = None
    if pargs.key is None:
        __write_output(state["Aliases"], pargs, config, "Alias.List")
    else:
        images = dict()
        alias = dict()
        if pargs.description is not None:
            alias["Description"] = pargs.description
        if pargs.detail is not None:
            alias["Detail"] = pargs.detail
        if pargs.structured_data is not None:
            alias["StructuredData"] = base64.b64encode(pargs.structured_data)
        if pargs.tag != []:
            alias["Tags"] = pargs.tag

        # Track the old image, which is the old alias config. If the alias doesn't exist yet, then
        # the old image value is None
        images["OldImage"] = {pargs.key: state["Aliases"].get(pargs.key, None)}

        # Because len(alias) == 0 as a condition is against PEP8. We were essentially checking that
        # the dictionary had stuff in it, so if it DOES NOT have stuff in it...
        if not alias:
            if pargs.key in state["Aliases"]:
                del state["Aliases"][pargs.key]
            images["NewImage"] = {pargs.key: None}
        else:
            state["Aliases"][pargs.key] = alias
            images["NewImage"] = {pargs.key: alias}

    return images


def __resolve_positional_arg(pargs, state):
    """
    Given the input arguments, determine if there is a position argument, and if so, attempt to
    resolve it to the value of either the description or the alias.
    """
    if pargs.quicktext is not None:
        # Check it against aliases
        if pargs.quicktext in state["Aliases"]:
            pargs.alias = pargs.quicktext
        # If it isn't an alias, use it as the description if --description is not provided
        elif pargs.description is None:
            pargs.description = pargs.quicktext


def __resolve_alias(pargs, state):
    """
    Take the properties defined in the alias, and map them into the record.
    """
    if pargs.alias not in state["Aliases"]:
        return

    alias = state["Aliases"][pargs.alias]
    props = dict(
        description="Description",
        detail="Detail",
        structured_data="StructuredData",
    )

    for key, val in props.items():
        # If the alias property is nonempty, and the property was not specified, then fill in the
        # property value from the alias. If the property WAS specified, then do NOT overwrite it
        # with the alias.
        #
        # Note that not all keys are guaranteed to be in the alias.
        if alias.get(val, None) is not None and getattr(pargs, key) is None:
            setattr(pargs, key, alias[val])

    # Tags are handled separately: append any tags in the alias to the tags in the input, and then
    # remove any from the input's untag property.
    #
    # Note that pargs.tag is guaranteed to be a list, but the alias key doesn't even need to exist,
    # let alone be a list.
    pargs.tag += alias.get("Tags", [])

    if "untag" in dir(pargs):
        pargs.tag = list(set(pargs.tag).difference(set(pargs.untag)))
    else:
        pargs.tag = list(set(pargs.tag))


def __create_record(pargs, state):
    __resolve_positional_arg(pargs, state)

    if pargs.alias is not None:
        __resolve_alias(pargs, state)

    cur_time = time.time()
    record = dict(
        CommitTime=cur_time,
        StartTime=cur_time,
        EndTime=cur_time,
        Tags=pargs.tag,
        Description=pargs.description,
        Detail=pargs.detail,
        StructuredData=pargs.structured_data,
    )

    return record


def cmd_start(pargs, state, _, outfile=sys.stdout):
    """
    Start a stopwatch to track time against a task
    """
    if state["Stopwatch"] is not None:
        print("Stopwatch currently running, ignoring current request",
              file=sys.stderr)
        if outfile == sys.stdout:
            sys.exit(1)

    record = __create_record(pargs, state)
    if pargs.start_time is not None:
        record["StartTime"] = __parse_time(pargs.start_time)
    record["EndTime"] = None
    record["CommitTime"] = None
    record["Interruptions"] = []
    state["Stopwatch"] = record
    return None


def __generate_id(state):
    while True:
        id_candidate = time.strftime("%Y%m%d") + (
            "-%s" % "".join([chr(ord('A') + (c % 26)) for c in os.urandom(4)]))
        if id_candidate not in state["Records"]:
            break
    return id_candidate


def __update_record(old_record_prototype, pargs, state):
    # Given an input record, use the values in the pargs value to update any values in the old
    # record, and replace the old record values.

    # Given the pargs value, create the record for it, and then throw away any keys that have a
    # value of None (the sentinel for "not supplied"; don't clobber a value in the old record that
    # was unspecified in the new one).
    new_record = dict([(k, v)
                       for k, v in __create_record(pargs, state).items()
                       if v is not None])

    del new_record["StartTime"]
    old_record = copy.deepcopy(old_record_prototype)
    new_record["Tags"] = list(
        set(old_record["Tags"] + new_record["Tags"]).difference(
            set(pargs.untag)))
    old_record.update(new_record)
    return old_record


def cmd_stop(pargs, state, config):
    """
    Start a stopwatch to track time against a task
    """
    if state["Stopwatch"] is None:
        print("Stopwatch not currently running, ignoring current request",
              file=sys.stderr)
        sys.exit(2)

    if pargs.id is None:
        pargs.id = __generate_id(state)

    record = __update_record(state["Stopwatch"], pargs, state)

    if pargs.end_time is not None:
        record["EndTime"] = __parse_time(pargs.end_time)
    state["Stopwatch"] = None
    state["Records"][pargs.id] = record

    __write_output(pargs.id, pargs, config, "ID")

    # Return the images, with None for the old image.
    return dict(OldImage=None, NewImage={pargs.id: record})


def cmd_sw(pargs, state, config):
    """
    Implements the smart stopwatch command which delegates to the start and stop functions based
    on the current state of the stopwatch.
    """
    # Since this is essentially just start or stop, but context sensitive, determine if there is
    # a stopwatch running, and call the right function.
    if state["Stopwatch"] is None:
        return cmd_start(pargs, state, config)
    else:
        return cmd_stop(pargs, state, config)


def cmd_cancel(pargs, state, config):
    """
    Cancels and cleans up any interruption or stopwatch that are currently active.
    """
    if state["Interruption"] is not None:
        state["Interruption"] = None
    else:
        state["Stopwatch"] = None


def cmd_interrupt(pargs, state, config):
    """
    Interrupt an existing stopwatch with a one-at-a-time interrupt timer.
    """
    if state["Stopwatch"] is None:
        cmd_start(pargs, state, config)
    else:
        # Confirm that there are no ongoing interruptions
        if state["Interruption"] is not None:
            print(
                "Unable to interrupt task, as existing interruption is in progress.",
                file=sys.stderr)
            sys.exit(3)
        # Since at this point, there's no ongoing interruptions, add a new one to the end of the
        # Interruptions list
        record = __create_record(pargs, state)
        record["EndTime"] = None
        record["CommitTime"] = None
        state["Interruption"] = record


def cmd_resume(pargs, state, config):
    """
    Resume an interrupted stopwatch by cleaning up and writing the event to the ledger.
    """
    if state["Stopwatch"] is None:
        print("Unable to resume from interruption with no stopwatch running.",
              file=sys.stderr)
        sys.exit(4)
    else:
        # Confirm that the interruption that's most recent exists and is indeed still open
        if state["Interruption"] is None:
            print("Unable to resume without an open interruption.",
                  file=sys.stderr)
            sys.exit(5)
        # Since there's an open interruption, close it out.
        if pargs.id is None:
            pargs.id = __generate_id(state)
        record = __update_record(state["Interruption"], pargs, state)
        state["Records"][pargs.id] = record
        state["Interruption"] = None
        state["Stopwatch"]["Interruptions"].append(dict(Id=pargs.id))
        __write_output(pargs.id, pargs, config, "ID")
        # Return the images, with None for the old image.
        return dict(OldImage=None, NewImage={pargs.id: record})


def __parse_time(timespec):
    from dateparser import parse as datetimeparser
    from tzlocal import get_localzone
    dto = datetimeparser(timespec)
    if dto is None:
        print("Unable to parse your timespec \"%s\"." % timespec,
              file=sys.stderr)
        sys.exit(8)
    if dto.tzinfo is None:
        return dto.replace(tzinfo=get_localzone()).timestamp()
    return dto.timestamp()


def cmd_track(pargs, state, config):
    """
    Track a fixed interval of time
    """
    if pargs.id is None:
        pargs.id = __generate_id(state)

    cur_time = time.time()

    if pargs.start_time is None and pargs.end_time is None:
        print(
            "At least one of start and end of a finite interval must be specified.",
            file=sys.stderr)
        sys.exit(6)

    # Since the above check guarantees at least one was specified, set the other to
    # a timezone aware "now" (in UTC).
    if pargs.start_time is None:
        pargs.start_time = "now UTC"
    if pargs.end_time is None:
        pargs.end_time = "now UTC"

    start_time = __parse_time(pargs.start_time)
    end_time = __parse_time(pargs.end_time)

    if end_time - start_time <= 0:
        print(
            "For finite-interval tracking, the end time must be strictly after the start time.",
            file=sys.stderr)
        sys.exit(7)

    record = __create_record(pargs, state)
    record["StartTime"] = start_time
    record["EndTime"] = end_time
    record["CommitTime"] = cur_time

    if pargs.dryrun:
        __write_output(record, pargs, config, "Record.Complete")
        sys.exit(127)
    else:
        state["Records"][pargs.id] = record

    __write_output(pargs.id, pargs, config, "ID")
    # Return the images, with None for the old image.
    return dict(OldImage=None, NewImage={pargs.id: record})


def cmd_amend(pargs, state, config):
    """
    Amend the properties of a tracked record
    """
    # First, check that the ID specified exists.
    if pargs.id not in state["Records"]:
        print("Specified record ID does not exist.", file=sys.stderr)
        sys.exit(9)

    # If the ID exists, create a new record from the arguments, and then clobber the record pulled
    # from the ledger.
    images = dict()
    images["OldImage"] = {pargs.id: copy.deepcopy(state["Records"][pargs.id])}
    old_record = state["Records"][pargs.id]
    record = __update_record(old_record, pargs, state)

    # Reset the timestamps in the record to what the original record was, then we'll replace as
    # necessary based on what is provided in the pargs attributes.
    record["StartTime"] = old_record["StartTime"]
    record["EndTime"] = old_record["EndTime"]

    # Fix the weirdness that's going to go on with the timestamps
    if pargs.start_time is not None:
        record["StartTime"] = __parse_time(pargs.start_time)
    if pargs.end_time is not None:
        record["EndTime"] = __parse_time(pargs.end_time)

    images["NewImage"] = {pargs.id: record}
    state["Records"][pargs.id] = record

    return images


def __check_tag_filter(tags, taglist):
    ret = (tags == taglist or list(set(tags).intersection(set(taglist))) != [])
    return ret


def __check_timespec_filter(timestamp, timespeclist):
    for timespec in timespeclist:
        dto = __parse_time(timespec["Timespec"])
        if eval(repr(timestamp) + timespec["Condition"] + repr(dto)):
            return True
    return False


def __check_regex_filter(stringval, regexlist):
    import re
    if stringval is None:
        return False
    for pattern in regexlist:
        if re.search(pattern, stringval):
            return True
    return False


def __filter_records(sieve, records):
    filters = {
        "Tags": __check_tag_filter,
        "StartTime": __check_timespec_filter,
        "EndTime": __check_timespec_filter,
        "Description": __check_regex_filter,
        "Detail": __check_regex_filter
    }

    results = dict()
    for record_id, record in records.items():
        for k, v in filters.items():
            if k in record and k in sieve and v(record[k], sieve[k]):
                results[record_id] = record

    return results


def __timestamp_to_iso(timestamp):
    from datetime import datetime
    from tzlocal import get_localzone
    return datetime.fromtimestamp(timestamp).replace(
        tzinfo=get_localzone()).strftime("%FT%T%z")


def __csv_format(records, allrecords, pargs, outfile=sys.stdout):
    from collections import Counter
    from csv import DictWriter
    # Print out a CSV with the following header structure
    # RecordID StartTime EndTime CommitTime Duration InterruptionDuration Description Detail [StructuredData] Tag1 Tag2 ...
    #
    # Tags that appear in all records are omitted, and 'x' is placed in the column for rows that
    # have that tag.
    #
    # Timestamps are converted from UTC Unix tiemstamps to ISO timestamps in the local timezone.
    #
    # For records with interruptions, the time will be subtracted from the Duration value, so
    # the duration may not match the difference between start and end time.

    tags = list()
    rows = copy.deepcopy(records)

    # The input is always a list of dictionary items as entries of the form
    #   [{"key": ..., "value": ...}, ...]
    for entry in rows:
        key = entry["key"]
        val = entry["value"]
        val["RecordId"] = key
        val["Duration"] = (val["EndTime"] - val["StartTime"]) / 3600
        val["InterruptionDuration"] = 0.0
        for event in val.get("Interruptions", []):
            val["InterruptionDuration"] += (
                allrecords[event["Id"]]["EndTime"] -
                allrecords[event["Id"]]["StartTime"]) / 3600
        val["Duration"] -= val["InterruptionDuration"] / 3600
        val["StartTime"] = __timestamp_to_iso(val["StartTime"])
        val["EndTime"] = __timestamp_to_iso(val["EndTime"])
        val["CommitTime"] = __timestamp_to_iso(val["CommitTime"])
        if "Tags" in val:
            tags += val["Tags"]
            for tag in val["Tags"]:
                val[tag] = "x"
            del val["Tags"]

    tag_counts = Counter(tags)
    ignored_tags = [k for k, v in tag_counts.items() if v == len(records)]
    tag_columns = sorted(
        list(set(list(tag_counts.keys())).difference(set(ignored_tags))))

    column_names = [
        "RecordId", "StartTime", "EndTime", "CommitTime", "Duration",
        "InterruptionDuration", "Description"
    ] + ([] if pargs.without_detail else ["Detail"]) + (
        ["StructuredData"] if pargs.with_structured_data else []) + tag_columns
    csv = DictWriter(outfile, column_names)
    csv.writeheader()
    csv.writerows([{
        col_name: entry["value"].get(col_name, "")
        for col_name in column_names
    } for entry in rows])


def cmd_ls(pargs, state, config, outfile=sys.stdout):
    """
    Retrieve and filter the records based on the input options, sorting the output by the provided
    sorting key.
    """
    if pargs.pos_id is not None:
        pargs.id.append(pargs.pos_id)

    if pargs.id != []:
        results = {
            rid: copy.deepcopy(state["Records"].get(rid, None))
            for rid in pargs.id if rid in state["Records"]
        }
    else:
        results = copy.deepcopy(state["Records"])
        for sieve in pargs.filter:
            results = __filter_records(sieve, results)

        if not pargs.with_structured_data:
            for _, val in results.items():
                if "StructuredData" in val:
                    del val["StructuredData"]
    if pargs.without_detail:
        for _, val in results.items():
            if "Detail" in val:
                del val["Detail"]

    results_list = [{"key": k, "value": v} for k, v in results.items()]
    try:
        results_list.sort(key=lambda d: d["value"][pargs.sort_by]
                          if pargs.sort_by != "ID" else d["key"])
    except Exception as e:
        print("Error sorting log output.", repr(e), file=sys.stderr)
        sys.exit(12)

    if pargs.csv:
        __csv_format(results_list, state["Records"], pargs, outfile)
    else:
        __write_output(results_list,
                       pargs,
                       config,
                       "Record.Complete.List",
                       dict_as_entries=True,
                       outfile=outfile)

    return None


def cmd_serve(pargs, state, config):
    import tt_serve
    server = tt_serve.create_server(pargs.preshared_key)
    server.run(port=pargs.port)


def __positional_argument(parser):
    parser.add_argument(
        default=None,
        nargs="?",
        dest="quicktext",
        help=
        """Positional argument that is first checked as an alias key and, failing that, used as the
        description.""")


def __property_options(parser):
    parser.add_argument(
        "-d",
        "--description",
        required=False,
        default=None,
        metavar="<description>",
        help="""A short description of the work done during the time tracked."""
    )
    parser.add_argument(
        "-D",
        "--detail",
        required=False,
        default=None,
        metavar="<detail>",
        help=
        """A detailed description of the work done during the time tracked.""")
    parser.add_argument(
        "-t",
        "--tag",
        action="append",
        required=False,
        default=[],
        metavar="<tag>",
        help=
        """Include a tag for the tracked unit of time. Specify multiple times to include multiple
        tags.""")
    parser.add_argument(
        "-S",
        "--structured-data",
        required=False,
        default=None,
        metavar="<data>",
        help=
        """Arbitrary data to associate with the time record, base64 encoded before storing."""
    )


def __alias_option(parser):
    parser.add_argument(
        "-a",
        "--alias",
        required=False,
        default=None,
        metavar="<alias key>",
        help=
        """The key for an alias to use to fill in properties. An error is returned if the alias
        does not exist. Only valid if starting a stopwatch or tracking a finite interval, ignored
        otherwise.""")
    __positional_argument(parser)


def __commit_time_options(parser):
    parser.add_argument(
        "-i",
        "--id",
        required=False,
        metavar="<identifier>",
        default=None,
        help=
        """A unique identifier by which the task will be identified. If one is not provided
        one will be generated. This is output on stdout when the time period is successfully
        logged. Only used when stopping a stopwatch, and ignored otherwise.""")
    parser.add_argument(
        "-u",
        "--untag",
        action="append",
        required=False,
        default=[],
        metavar="<tag>",
        help="""List of tags to remove, if they exist, from the time record."""
    )


def __timespec_options(parser, start=True, end=True):
    if start:
        parser.add_argument(
            "-s",
            "--start-time",
            required=False,
            default=None,
            metavar="<timespec>",
            help=
            """A specification for the start time of the interval to log.""")

    if end:
        parser.add_argument(
            "-e",
            "--end-time",
            required=False,
            default=None,
            metavar="<timespec>",
            help="""A specification for the end time of the interval to log."""
        )


def __dryrun_option(parser):
    parser.add_argument(
        "--dryrun",
        required=False,
        action='store_true',
        help=
        """Print out the interpreted date-time values parsed from the given arguments."""
    )


def __main():  # pylint: disable=R0915
    if not check_dotfile():
        print("Dotfiles are missing, performing first-time setup.",
              file=sys.stderr)
        init_dotfiles()

    ################ tt
    parser = ArgumentParser(description="""
    Track time on projects, tasks, and other items via the CLI.
    """)
    parser.add_argument(
        "--output-format",
        required=False,
        choices=(["human", "json", "json-compact"] +
                 (["yaml"] if "yaml" in sys.modules.keys() else [])),
        default=None,
        help="""
    The output format to use for commands that produce output.
    """)

    subparsers = parser.add_subparsers(
        title="Supported time tracking commands", dest="command")

    ################ tt config
    subparsers.add_parser("config",
                          help="""
    Set or dump persistent configuration values.
    """)

    ################ tt sw
    cmd = subparsers.add_parser("sw",
                                help="""
    Start or stop a stopwatch based on whether one is running or not
    """)
    __property_options(cmd)
    __alias_option(cmd)
    __commit_time_options(cmd)
    __timespec_options(cmd)

    ################ tt cancel
    cmd = subparsers.add_parser("cancel",
                                help="""
    Stop the currently running stopwatch or interruption without committing the time to the ledger.
    """)

    ################ tt start
    cmd = subparsers.add_parser("start",
                                help="""
    Start a stopwatch to track time.
    """)
    __property_options(cmd)
    __alias_option(cmd)
    __timespec_options(cmd, True, False)

    ################ tt stop
    cmd = subparsers.add_parser("stop",
                                help="""
    Stop the running stopwatch.
    """)
    __property_options(cmd)
    __alias_option(cmd)
    __commit_time_options(cmd)
    __timespec_options(cmd, False, True)

    ################ tt interrupt
    cmd = subparsers.add_parser(
        "interrupt",
        aliases=["i"],
        help="""Temporarily interrupt a running stopwatch.""")
    __property_options(cmd)
    __alias_option(cmd)

    ################ tt resume
    cmd = subparsers.add_parser("resume",
                                aliases=["r"],
                                help="""Resume an interrupted stopwatch.""")
    __property_options(cmd)
    __alias_option(cmd)
    __commit_time_options(cmd)

    ################ tt track
    cmd = subparsers.add_parser("track",
                                help="""Track a closed interval of time.""")
    __timespec_options(cmd)
    __property_options(cmd)
    __alias_option(cmd)
    __commit_time_options(cmd)
    __dryrun_option(cmd)

    ################ tt amend
    cmd = subparsers.add_parser(
        "amend",
        help=
        """Amend a given tracked time interval to change one of the parameters."""
    )
    cmd.add_argument(
        "-i",
        "--id",
        required=True,
        metavar="<identifier>",
        default=None,
        help="""The unique identifier of the ledger entry to modify.""")
    __property_options(cmd)
    __timespec_options(cmd)
    __alias_option(cmd)
    cmd.add_argument(
        "-u",
        "--untag",
        action="append",
        required=False,
        default=[],
        metavar="<tag>",
        help="""List of tags to remove, if they exist, from the time record."""
    )
    __dryrun_option(cmd)

    ################ tt alias
    cmd = subparsers.add_parser("alias",
                                help="""
    Create an alias between a string and a set of options. Running this again with the same alias id
    will overwrite any existing parameters for that alias.
    """)
    cmd.add_argument(
        "-k",
        "--key",
        required=False,
        metavar="<alias key>",
        help="""A specification for the start time of the interval to log.""")
    __property_options(cmd)

    ################ tt ls
    cmd = subparsers.add_parser("ls",
                                help="""
    List and filter the reports based on the filters provided, and format the output in a useful
    way.""")
    cmd.add_argument(
        default=None,
        nargs="?",
        dest="pos_id",
        help="""Positional argument for quickly specifying a single ID.""")
    cmd.add_argument("-s",
                     "--sort-by",
                     required=False,
                     metavar="<sortkey>",
                     type=__record_sort_keys,
                     default="CommitTime",
                     help="""
        The record key to use to sort records by. The default is to sort by CommitTime. If an invalid sort key is used, no results are shown and an error is printed showing valid choices."
        """)
    cmd.add_argument(
        "-i",
        "--id",
        required=False,
        metavar="<identifier>",
        default=[],
        action="append",
        help=
        """A unique identifier for the specific report to retrieve. Can be repeated multiple
        times.""")
    cmd.add_argument(
        "-f",
        "--filter",
        required=False,
        metavar="<filter spec>",
        default=[],
        type=json.loads,
        action="append",
        help=
        """A unique identifier for the specific report to retrieve. Can be repeated multiple
        times.""")
    cmd.add_argument(
        "-o",
        "--outfile",
        required=False,
        metavar="<path to output file>",
        help="""The path to the file that output should be directed to.""")
    cmd.add_argument(
        "-c",
        "--csv",
        required=False,
        default=False,
        action="store_true",
        help=
        """Indicates that the results should be output in a CSV suitable for an Excel timesheet"""
    )
    cmd.add_argument(
        "-w",
        "--with-structured-data",
        required=False,
        default=False,
        action="store_true",
        help=
        """Include structured data, if present, for each record. The default is not to include the
        structured data properties.""")
    cmd.add_argument("-D",
                     "--without-detail",
                     required=False,
                     default=False,
                     action="store_true",
                     help="""Exclude the detailed text field in the output.""")
    __dryrun_option(cmd)

    ################ tt serve
    cmd = subparsers.add_parser(
        "serve",
        help=
        """Serve up an HTTP API that can be used by a webapp or mobile app""")
    cmd.add_argument("-p",
                     "--port",
                     required=False,
                     default=9872,
                     type=int,
                     help="""Port to serve the API on""")
    cmd.add_argument(
        "-k",
        "--preshared-key",
        required=False,
        default=None,
        type=str,
        help=
        """Pre-shared key string to use to ensure that clients are authenticated. If not specified, then the API is unauthenticated. If provided, then this must be provided as an Authentication HTTP header, as `Bearer ${PreSharedKey}`"""
    )

    pargs = parser.parse_args()

    hooks = load_hooks()
    run_hooks("pre_load", hooks, None)

    state, config = __load_state()

    # When records are added, edited, or removed, the images (OldImage and NewImage) are kept
    # for passing into the hooks.
    images = None

    if pargs.command is None:
        cmd_base(pargs, state, config)
    elif pargs.command == "config":
        cmd_config(pargs, state, config, hooks)
    elif pargs.command == "alias":
        images = cmd_alias(pargs, state, config)
    elif pargs.command == "start":
        cmd_start(pargs, state, config)
    elif pargs.command == "stop":
        images = cmd_stop(pargs, state, config)
    elif pargs.command == "sw":
        images = cmd_sw(pargs, state, config)
    elif pargs.command == "cancel":
        cmd_cancel(pargs, state, config)
    elif pargs.command in ["i", "interrupt"]:
        cmd_interrupt(pargs, state, config)
    elif pargs.command in ["r", "resume"]:
        images = cmd_resume(pargs, state, config)
    elif pargs.command == "track":
        images = cmd_track(pargs, state, config)
    elif pargs.command == "amend":
        images = cmd_amend(pargs, state, config)
    elif pargs.command == "ls":
        cmd_ls(pargs, state, config)
    elif pargs.command == "serve":
        cmd_serve(pargs, state, config)
        # Because the state was modified out of band of this process,
        # we need to reload it ot to ensure that this in-line __write_state()
        # doesn't clobber it with our initially loaded state
        state, config = __load_state()

    run_hooks("pre_commit", hooks, images)
    __write_state(state, hooks)
    run_hooks("post_commit", hooks, images)


if __name__ == "__main__":
    __main()
