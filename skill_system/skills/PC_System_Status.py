# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: PC_System_Status
# AGENT_SKILL_DESC: 현재 PC의 CPU 사용률, RAM 사용량, 디스크 공간, GPU 온도 등 시스템 상태를 조회합니다.
# AGENT_SKILL_ARGS: 없음 (인수 불필요)
# AGENT_SKILL_RETURNS: CPU%, RAM%, 디스크%, GPU 온도 등 시스템 리소스 현황
"""
[스킬 이름]: PC_System_Status
[용도]: 현재 윈도우 PC의 CPU, 메모리(RAM) 사용량, 디스크 여유 공간을 빠르게 요약하여 출력합니다.
[실행]: <CMD>python C:\\ai\\Antigravity_Memory_Engine\\skill_system\\skills\\PC_System_Status.py</CMD>
"""
import shutil
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import psutil
    
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_used = ram.used / (1024**3)
    ram_total = ram.total / (1024**3)
    ram_pct = ram.percent
    
    disk = shutil.disk_usage("C:\\")
    disk_free = disk.free / (1024**3)
    disk_total = disk.total / (1024**3)
    
    print(f"===== PC 상태 요약 =====")
    print(f"CPU 사용률   : {cpu:.1f}%")
    print(f"RAM 사용량   : {ram_used:.1f}GB / {ram_total:.1f}GB ({ram_pct:.0f}%)")
    print(f"C드라이브 여유: {disk_free:.1f}GB / {disk_total:.1f}GB")
    
except ImportError:
    # psutil이 없을 경우 기본 cmd 방식으로 대체
    print("[안내] psutil 라이브러리가 없어 기본 정보만 출력합니다.")
    disk = shutil.disk_usage("C:\\")
    disk_free = disk.free / (1024**3)
    disk_total = disk.total / (1024**3)
    print(f"C드라이브 여유 공간: {disk_free:.1f}GB / {disk_total:.1f}GB")
