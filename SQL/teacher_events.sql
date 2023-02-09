select distinct Results.* from
(
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
sections.room,teachers.Email_addr,
concat('2022AutoCalendar','-GAM Calendar')  as UniqueCalDescription,
sections.course_number || '.' || sections.section_number as CourseSection
from SectionTeacher
inner join sections on sections.id = SectionTeacher.sectionid
inner join teachers on SectionTeacher.teacherid = teachers.id
inner join courses on courses.course_number = sections.course_number
inner join section_meeting on section_meeting.sectionid = sections.id
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
and terms.firstday <= dates.date_value
and terms.lastday >= dates.date_value
and (dates.date_value  >= SectionTeacher.start_date - 1 and dates.date_value <= SectionTeacher.end_date)
and SYSDATE <= dates.date_value + :days_before_to_sync + 1
and dates.date_value <= SYSDATE + :days_after_to_sync
and teachers.email_addr = :user_email
-- If we are in July or August it is needed to put classes on the calendar whether or not they have students
-- Otherwise if no kids are enrolled it often means that we had to move when that section is taught
-- And you cannot move a section once attendance data was taken, so we create brand new sections
-- So there are sometimes sections in the middle of the year with teachers, but no students
-- CORE is the elementary course that is just used to get something useful onto teacher's calendars since subjects are taught at a specific time
and (to_char(SYSDATE,'MM') in ('07','08') or sections.no_of_students > 0 or sections.course_number = 'CORE')
) Results
order by StartDateTime