db_host_ip = "127.0.0.1"
db_host_port = 1521
db_host_service_name = "PSProdDB"
db_user = "dbUser"
db_password = "PSNavigator"

CALENDAR_UNIQUE_DESCRIPTION = "2022AutoCalendar"
days_before_to_sync = 1  # Use 1 day, not 0 or else you will get duplicates for same day, but past time events if syncing during the middle of the day
days_after_to_sync = 90

# Use this list if needed for testing, otherwise leave as None to get the data from SQL
emails_to_update_override = None
# emails_to_update_override = [{
#                             "EMAIL_ADDR": "email@example.com",
#                             "USER_TYPE": "teacher"
#                         }]

# If you want to create events on a room calendar as well, requires U_ROOM_CALENDARS_GOOGLE database extension
# TO DISABLE user.list.sql MUST BE EDITED AS WELL! Just remove the join to the calendar table
sync_room_calendars = True
