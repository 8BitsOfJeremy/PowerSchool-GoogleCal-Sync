select * from(
select distinct
concat(concat(concat(to_char(dates.date_value,'yyyy-mm-dd'),'T')
,to_char(to_date(bell_schedule_items.start_time,'sssss'),'hh24:mi:ss')
),'+08:00'
) as StartDateTime,
concat(concat(concat(to_char(dates.date_value,'yyyy-mm-dd'),'T')
,to_char(to_date(bell_schedule_items.end_time,'sssss'),'hh24:mi:ss')
),'+08:00'
) as EndDateTime,
case sections.schoolid
when 1803 then 
    case SUBSTR(sections.external_expression,1,2)
    when 'B1' then 'B1' || ' - ' || courses.course_name
    else SUBSTR(sections.external_expression,1, INSTR(sections.external_expression,'(',1)+1) || ') - ' || courses.course_name
    end 
when 1804 then SUBSTR(sections.external_expression,1, INSTR(sections.external_expression,'(',1)+1) || ') - ' || courses.course_name
else courses.course_name
end as WholeEventTitle,
TO_CHAR(U_ROOM_CALENDARS_GOOGLE.ROOM_NUMBER) as room,
U_ROOM_CALENDARS_GOOGLE.Google_Cal_Url as "EMAIL_ADDR",
concat('2022AutoCalendar','-GAM Calendar')  as UniqueCalDescription,
sections.course_number || '.' || sections.section_number as CourseSection
from sections
inner join teachers on sections.teacher = teachers.id
inner join courses on courses.course_number = sections.course_number
inner join section_meeting on section_meeting.sectionid = sections.id

-- Rooms 418, 417, and the soccer field (600) should also be booked if the Gym (405) is booked
inner join U_ROOM_CALENDARS_GOOGLE on 
(
    sections.room = U_ROOM_CALENDARS_GOOGLE.Room_Number
    OR (sections.room = 405 AND U_ROOM_CALENDARS_GOOGLE.Room_Number in (418,417,600))
)
inner join terms on (terms.id = sections.termid
    and sections.schoolid = terms.schoolid)
inner join period on (period.period_number = section_meeting.period_number
    and period.schoolid = section_meeting.schoolid
    and period.year_id = section_meeting.year_id)
inner join
(select date_value, bell_schedule_id, abbreviation, day_name, cycle_day.letter as letter from calendar_day
inner join cycle_day on cycle_day.id = calendar_day.cycle_day_id
where insession = 1
) dates
on dates.letter = section_meeting.cycle_day_letter
inner join bell_schedule_items on (bell_schedule_items.bell_schedule_id = dates.bell_schedule_id
    and bell_schedule_items.period_id = period.id)
where terms.yearid = 32
and sections.external_expression NOT LIKE '%HR(Mon-Fri)%'
and sections.external_expression NOT LIKE '%HR-S1A(Mon-Fri)%'
and terms.firstday <= dates.date_value
and terms.lastday >= dates.date_value
and SYSDATE <= dates.date_value + 2
and dates.date_value <= SYSDATE + :days_after_to_sync
union
select distinct
concat(concat(concat(to_char(dates.date_value,'yyyy-mm-dd'),'T')
,to_char(to_date(bell_schedule_items.start_time,'sssss'),'hh24:mi:ss')
),'+08:00'
) as StartDateTime,
concat(concat(concat(to_char(dates.date_value,'yyyy-mm-dd'),'T')
,to_char(to_date(bell_schedule_items.end_time,'sssss'),'hh24:mi:ss')
),'+08:00'
) as EndDateTime,
CONCAT(teachers.last_name,' Core Classes')
as WholeEventTitle,sections.room, U_ROOM_CALENDARS_GOOGLE.Google_Cal_Url as "EMAIL_ADDR",
concat('2022AutoCalendar','-GAM Calendar')  as UniqueCalDescription,
sections.course_number || '.' || sections.section_number as CourseSection
from sections
inner join teachers on sections.teacher = teachers.id
inner join courses on courses.course_number = sections.course_number
inner join section_meeting on section_meeting.sectionid = sections.id
inner join U_ROOM_CALENDARS_GOOGLE on sections.room = U_ROOM_CALENDARS_GOOGLE.Room_Number
inner join terms on (terms.id = sections.termid
    and sections.schoolid = terms.schoolid)
inner join period on (period.period_number = section_meeting.period_number
    and period.schoolid = section_meeting.schoolid
    and period.year_id = section_meeting.year_id)
inner join
(select date_value, bell_schedule_id, abbreviation, day_name, cycle_day.letter as letter from calendar_day
inner join cycle_day on cycle_day.id = calendar_day.cycle_day_id
where insession = 1
) dates
on dates.letter = section_meeting.cycle_day_letter
inner join bell_schedule_items on (bell_schedule_items.bell_schedule_id = dates.bell_schedule_id
    and bell_schedule_items.period_id = period.id)
where terms.yearid = 32
and
(sections.external_expression LIKE '%HR(Mon-Fri)%'
or
 sections.external_expression LIKE '%HR-S1A(Mon-Fri)%')
and terms.firstday <= dates.date_value
and terms.lastday >= dates.date_value
and SYSDATE <= dates.date_value + 2
and dates.date_value <= SYSDATE + :days_after_to_sync
)
where "EMAIL_ADDR" = :user_email
order by StartDateTime, Room