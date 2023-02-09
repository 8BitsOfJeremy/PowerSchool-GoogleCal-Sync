select * from(
select distinct
teachers.email_addr as EMAIL_ADDR,
'teacher' as user_type
from teachers
where email_addr is NOT NULL
and status = 1
union
select distinct
U_ROOM_CALENDARS_GOOGLE.Google_Cal_Url as EMAIL_ADDR,
'room' as user_type
from U_ROOM_CALENDARS_GOOGLE
union
select distinct
PSM_STudentcontact.email as EMAIL_ADDR,
'student' as user_type
from students
inner join sync_studentmap on sync_studentmap.studentsdcid = students.dcid
inner join PSM_STudentcontact on PSM_STudentcontact.STUDENTID = sync_studentmap.STUDENTID
inner join psm_studentcontacttype on PSM_STudentcontact.studentcontacttypeid = psm_studentcontacttype.id and psm_studentcontacttype.name='Self'
where PSM_STudentcontact.email  IS NOT NULL
and grade_level > 5
and (enroll_status = 0 or enroll_status = -1)
)
order by user_type desc, email_addr
