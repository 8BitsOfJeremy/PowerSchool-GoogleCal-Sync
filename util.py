import logging
import settings
import cx_Oracle  # Running on PowerSchool server https://towardsdatascience.com/connecting-python-to-oracle-sql-server-mysql-and-postgresql-ea1e4523b1e9
import os
import csv
import datetime
from subprocess import Popen, PIPE
from threading import Timer
import shlex
import sys


def run(cmd, timeout_sec):
    # Set a timeout to avoid gam just hanging at the end of the process
    # Finished 34281 of 34290 processes.
    # Finished 34281 of 34290 processes.
    # Finished 34281 of 34290 processes.
    # Finished 34281 of 34290 processes.
    # Finished 34281 of 34290 processes.
    # Also, if there is a socket error it just seems to never end, so it is better to sync badly for one user
    # than hang for a day and prevent all updates.

    proc = Popen(shlex.split(cmd))
    timer = Timer(timeout_sec, proc.kill)
    try:
        timer.start()
        stdout, stderr = proc.communicate()
        print(stdout)
        timer.cancel()
    finally:
        timer.cancel()


def get_results_from_gam(gam_command):
    # We can't read directly from the gam output, so save it to a temp CSV
    gam_command = gam_command + " > Temp/temp.csv"
    os.system(gam_command)

    # Read the CSV back into a list of events
    with open('Temp/temp.csv') as f:
        results = [{k: v for k, v in row.items()}
                  for row in csv.DictReader(f, skipinitialspace=True)]
    # TODO delete the temp.csv
    return results


def filter_events_for_duplicates(current_calendar_events: []) -> []:
    duplicates = []
    events_strings = set()
    for event in current_calendar_events:
        # Generate a unique string for each class event
        event_string = event["calendarId"] + event["summary"] + event["description"] + event["end.dateTime"] + event["start.dateTime"] # removed + event["location"] since if the calendar originally declided the invite that would be blank, but then if it created a second entry it would be non-blank and both would stay on the calendar, the other fields are enough to check for uniqueness and the room is already checked when we remove stale events that are no longer in the db
        if "hangoutLink" in event:
            event_string += event["hangoutLink"]
        # If we already have that string in the set, it is a duplicate
        if event_string in events_strings:
            duplicates.append(event)
        # If not mark that event string as used
        else:
            events_strings.add(event_string)

    return duplicates


def filter_events_to_add_for_new_only(events_to_add: [], current_calendar_events: []):
    new_events_to_add = []
    for event in events_to_add:
        if not is_in_event_list(event, current_calendar_events):
            new_events_to_add.append(event)
    return new_events_to_add


def filter_events_to_delete(data_source_events: [], current_calendar_events: []):
    events_to_delete = []
    for event in current_calendar_events:
        if not old_event_is_in_event_list(event, data_source_events):
            events_to_delete.append(event)
    return events_to_delete


def is_in_event_list(event, event_list):
    event_time_start = datetime.datetime.strptime(event['STARTDATETIME'], '%Y-%m-%dT%H:%M:%S%z')
    event_time_end = datetime.datetime.strptime(event['ENDDATETIME'], '%Y-%m-%dT%H:%M:%S%z')
    for old_event in event_list:
        if old_event['status'] == 'cancelled':
            continue  # skip cancelled events that we cannot delete
        if "event_time_start" in old_event and "event_time_end" in old_event:
            old_event_time_start = old_event['event_time_start']
            old_event_time_end = old_event['event_time_end']
        else:
            old_event_time_start = datetime.datetime.strptime(old_event['start.dateTime'], '%Y-%m-%dT%H:%M:%S%z')
            old_event['event_time_start'] = old_event_time_start
            old_event_time_end = datetime.datetime.strptime(old_event['end.dateTime'], '%Y-%m-%dT%H:%M:%S%z')
            old_event['event_time_end'] = old_event_time_end
        if (event_time_start == old_event_time_start and
            event_time_end == old_event_time_end and
            event['WHOLEEVENTTITLE'] == old_event['summary'] and
            event['UNIQUECALDESCRIPTION'].replace('\n', '').replace('\r', '') == old_event['description'].replace('\n', '').replace('\r', '') and
            (event['ROOM'] == old_event['location']
             or event['ROOM'] == (old_event['location'] + ", OIS")
             or (event['ROOM'] + ", OIS") in old_event['location']
            ) and
            event['EMAIL_ADDR'] == old_event['calendarId']):
            return True
    return False


def old_event_is_in_event_list(old_event, event_list):
    if old_event['status'] == 'cancelled':
        return True  # Cannot delete cancelled events anyway
    event_time_start = datetime.datetime.strptime(old_event['start.dateTime'], '%Y-%m-%dT%H:%M:%S%z')
    event_time_end = datetime.datetime.strptime(old_event['end.dateTime'], '%Y-%m-%dT%H:%M:%S%z')

    for event in event_list:
        if "event_time_start" in event and "event_time_end" in event:
            old_event_time_start = event['event_time_start']
            old_event_time_end = event['event_time_end']
        else:
            old_event_time_start = datetime.datetime.strptime(event['STARTDATETIME'], '%Y-%m-%dT%H:%M:%S%z')
            event['event_time_start'] = old_event_time_start
            old_event_time_end = datetime.datetime.strptime(event['ENDDATETIME'], '%Y-%m-%dT%H:%M:%S%z')
            event['event_time_end'] = old_event_time_end
        if (event_time_start.day == 25 and event_time_start.month == 1):
            pass
        # PowerSchool lets you create events without a room, which would crash the below code
        if 'ROOM' not in event or event['ROOM'] is None:
            event['ROOM'] = ''
        if (event_time_start == old_event_time_start and
            event_time_end == old_event_time_end and
            old_event['summary'] == event['WHOLEEVENTTITLE'] and
            old_event['description'].replace('\n', '').replace('\r', '') == event['UNIQUECALDESCRIPTION'].replace('\n', '').replace('\r', '') and
            (old_event['location'] == event['ROOM']
             or (old_event['location']) == (event['ROOM']) + ", OIS"
             or (event['ROOM'] + ", OIS") in old_event['location']) and
            old_event['calendarId'] == event['EMAIL_ADDR']):
            return True
    return False


def write_events_to_temp_csv(events):
    if len(events) == 0:
        raise Exception("No events to write to temp csv")
    # Write the events back to a file, depending on if the event has attendees, it can have different headers
    # So we loop through and get all possible headers, if an event didn't have that header already it will just be blank and that is fine
    all_possible_keys = set()
    for event in events:
        for key in event.keys():
            all_possible_keys.add(key)
    # We want to use gam csv since it is more optimised to rate limit and deal with Google's API in general
    # So we will write back to a csv and then use that
    temp_file = open('Temp/temp.csv', 'w', encoding="utf-8", newline='')
    with temp_file:
        # Write the header, include all possible fields
        writer = csv.DictWriter(temp_file, fieldnames=all_possible_keys)
        writer.writeheader()
        for row in events:
            writer.writerow(row)


def delete_events(events):
    write_events_to_temp_csv(events)
    command = f"gam csv Temp/temp.csv gam calendar ~calendarId deleteevent id ~id doit"
    run(command, 60 + len(events) * 1.0)
    # TODO delete the temp.csv


def add_events(events):
    write_events_to_temp_csv(events)
    command = f"gam csv Temp/temp.csv gam calendar ~EMAIL_ADDR addevent summary ~WHOLEEVENTTITLE start ~STARTDATETIME end ~ENDDATETIME description ~UNIQUECALDESCRIPTION visibility public location ~ROOM noreminders"
    run(command, 60 + len(events) * 1.0)
    # TODO delete the temp.csv


def get_sql_results(sql_file_name: str, replacement_data: {}) -> [{}]:
    """
    Uses a direct ODBC connect to the database configured in the settings.py file.
    The machine running this code must have a support ODBC driver configured already.
    This page shows how to configure cx_Oracle which then can connect directly to the PowerSchool Oracle Database:
    https://towardsdatascience.com/connecting-python-to-oracle-sql-server-mysql-and-postgresql-ea1e4523b1e9.

    :param sql_file_name: Filename and extension for a SQL file that is already located in the SQL folder within this project.
    :return: A list of dictionaries
    """
    file = open(f"SQL\\{sql_file_name}")
    sql = file.read()

    dsn = cx_Oracle.makedsn(
        settings.db_host_ip,
        settings.db_host_port,
        service_name=settings.db_host_service_name
    )
    conn = cx_Oracle.connect(
        user=settings.db_user,
        password=settings.db_password,
        dsn=dsn
    )
    c = conn.cursor()
    c.execute(sql, replacement_data)

    # Turn the tuples into dictionaries for convenience
    # https://cx-oracle.readthedocs.io/en/latest/user_guide/sql_execution.html#rowfactories
    columns = [col[0] for col in c.description]
    c.rowfactory = lambda *args: dict(zip(columns, args))

    result_tuples = c.fetchall()

    conn.close()
    return result_tuples
