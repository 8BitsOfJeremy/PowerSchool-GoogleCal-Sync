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
sections.room,PSM_STudentcontact.email as Email_addr,
concat('2022AutoCalendar','-GAM Calendar') as UniqueCalDescription,  -- Add zoom link for specific course
sections.course_number || '.' || sections.section_number as CourseSection
from sections
inner join teachers on sections.teacher = teachers.id
inner join courses on courses.course_number = sections.course_number
inner join section_meeting on section_meeting.sectionid = sections.id
inner join cc on cc.sectionid = sections.id
inner join students on students.id = cc.studentid
inner join sync_studentmap on sync_studentmap.studentsdcid = students.dcid
inner join PSM_STudentcontact on PSM_STudentcontact.STUDENTID = sync_studentmap.STUDENTID
inner join psm_studentcontacttype on PSM_STudentcontact.studentcontacttypeid = psm_studentcontacttype.id and psm_studentcontacttype.name='Self'
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
and cc.dateenrolled <= dates.date_value
and cc.dateleft >= dates.date_value
and sections.schoolid != 1802
and PSM_STudentcontact.email  IS NOT NULL
and PSM_STudentcontact.email = :user_email
and SYSDATE <= dates.date_value + 2 -- # GAM gets the day before as well or else there are same day duplicates
and dates.date_value <= SYSDATE + :days_after_to_sync
order by StartDateTime