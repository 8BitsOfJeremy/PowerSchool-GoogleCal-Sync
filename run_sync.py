import logging
from util import get_sql_results, get_results_from_gam, filter_events_to_add_for_new_only, filter_events_to_delete, delete_events, add_events, filter_events_for_duplicates
from settings import CALENDAR_UNIQUE_DESCRIPTION, days_before_to_sync, days_after_to_sync, emails_to_update_override, sync_room_calendars
import os
import sys
from exclusions import course_section_exclusions

def run_sync():
    logging.basicConfig(
        format='%(asctime)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("GoogleCalendarSync.log"),
            logging.StreamHandler()
        ])

    logging.info('Starting up')
    os.system('set GAM_THREADS=20')

    if emails_to_update_override:
        # Override the list for testing
        emails_to_update = emails_to_update_override
    else:
        # Get a list of all student, teacher email addresses that are active and that we should update
        emails_to_update = get_sql_results("calendars_to_update.sql", {})

    total_additions = 0
    total_deletions = 0
    i = 1
    for email_dict in emails_to_update:
        print(f'Starting {i} out of {len(emails_to_update)}')
        try:
            additions, deletions = update_calendar_for_email(email_dict['EMAIL_ADDR'], email_dict['USER_TYPE'], days_before_to_sync, days_after_to_sync)
            total_additions += additions
            total_deletions += deletions
        except Exception as e:
            logging.error(f"ERROR with {email_dict} error: {e}")
            exception_type, exception_object, exception_traceback = sys.exc_info()
            i += 1
            continue
        i += 1
    logging.info(f'All finished, {total_additions} calendar event additions, {total_deletions} calendar event deletions.')


def update_calendar_for_email(email, user_type, days_before_to_sync, days_after_to_sync):
    # Get a list of all events for this user within the date range
    if user_type == 'teacher':
        data_source_events = get_sql_results("teacher_events.sql", {":user_email": email, ":days_before_to_sync": days_before_to_sync, "days_after_to_sync": days_after_to_sync})
    elif user_type == 'student':
        data_source_events = get_sql_results("student_events.sql", {":user_email": email, ":days_after_to_sync": days_after_to_sync})
    elif user_type == 'room':
        if not sync_room_calendars:
            return 0, 0 + 0
        # Set all room calendars back to the correct timezone or else we will probably make duplicate events
        # Don't modify user calendars because they do travel and might want to change their own timezone
        get_results_from_gam(f'gam calendar {email} modify timezone "Asia/Kuala_Lumpur"')
        logging.info(f'{email}: reset room calendar to KL timezone.')
        data_source_events = get_sql_results("room_events.sql", {":user_email": email, ":days_after_to_sync": days_after_to_sync, "days_before_to_sync": days_before_to_sync})
    else:
        raise Exception(f"Invalid user_type: {user_type} for email: {email}")
    # Check for exclusions that should not appear on the calendar
    if email in course_section_exclusions:
        email_exclusions = course_section_exclusions[email]
    else:
        email_exclusions = []
    data_source_events = list(filter(lambda x: x['COURSESECTION'] not in email_exclusions, data_source_events))
    logging.info(f"{email}: has {len(data_source_events)} events in the database.")

    # Using GAM get a list of all the events that are already on the calendar for this email within the date range
    # Adding 10 hours to the days after because the SQL only looks at the day itself, but GAM/Google +1 day is strickly +24 hours
    current_calendar_events = get_results_from_gam(f'gam calendar {email} printevents after -{days_before_to_sync*24 + 10}h before +{days_after_to_sync*24 + 10}h query "{CALENDAR_UNIQUE_DESCRIPTION}"')
    logging.info(f"{email}: has {len(current_calendar_events)} events currently on the calendar.")

    # Delete any events that on already on the calendar, but are no longer listed in the data source
    events_to_delete = filter_events_to_delete(data_source_events, current_calendar_events)
    logging.info(f"{email}: has {len(events_to_delete)} extra events on their calendar to be deleted.")
    if len(events_to_delete) > 0:
        delete_events(events_to_delete)

    # Remove any events from the current to add list if they are already on the Calendar
    events_to_add = filter_events_to_add_for_new_only(data_source_events, current_calendar_events)
    logging.info(f"{email}: has {len(events_to_add)} new events to add.")
    if len(events_to_add) > 0:
        add_events(events_to_add)

    # Check to see if any duplicate events are left on the calendar
    # these happen sometimes if the sync process has an error when retrieving the current calendars
    # so then it just adds it again
    # Doing it in this order will not check the events that were just added, but that is fine
    # Duplicates aren't a high priority, but should be cleaned eventually
    duplicate_events = filter_events_for_duplicates(current_calendar_events)
    logging.info(f"{email}: has {len(duplicate_events)} duplicate events to remove.")
    if len(duplicate_events) > 0:
        delete_events(duplicate_events)

    logging.info(f"{email} finished with all tasks.")
    return len(events_to_add), len(events_to_delete) + len(duplicate_events)

run_sync()
