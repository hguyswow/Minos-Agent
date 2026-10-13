# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: current_time
# AGENT_SKILL_DESC: 현재 날짜와 시간을 반환합니다. 요일, 시간대 정보도 포함됩니다.
# AGENT_SKILL_ARGS: 없음
# AGENT_SKILL_RETURNS: 현재 날짜/시간/요일/시간대
import sys
import datetime

def get_current_time():
    now = datetime.datetime.now()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_str = weekdays[now.weekday()]
    time_str = now.strftime(f"%Y년 %m월 %d일 ({weekday_str}) %p %I시 %M분 %S초").replace("AM", "오전").replace("PM", "오후")
    print(f"현재 시스템 시간: {time_str}")

if __name__ == "__main__":
    get_current_time()
