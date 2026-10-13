# -*- coding: utf-8 -*-
# AGENT_SKILL_NAME: process_manager
# AGENT_SKILL_DESC: 실행 중인 프로세스를 조회하거나 종료합니다. CPU/메모리를 많이 사용하는 프로세스 관리에 활용합니다.
# AGENT_SKILL_ARGS: action(str) - list/kill, process_name(str) - 프로세스명(kill 시)
# AGENT_SKILL_RETURNS: 프로세스 목록 또는 종료 결과
import sys
import psutil

def list_processes():
    print("[현재 실행 중인 주요 프로세스 (메모리 사용량 Top 10)]\n")
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            procs.append(p.info)
        except:
            pass
    
    procs = sorted(procs, key=lambda x: x['memory_info'].rss if x['memory_info'] else 0, reverse=True)
    
    for i, p in enumerate(procs[:10], 1):
        mem_mb = p['memory_info'].rss / (1024 * 1024) if p['memory_info'] else 0
        print(f"{i}. PID: {p['pid']} | 이름: {p['name']} | 메모리: {mem_mb:.1f} MB")

def kill_process(name_or_pid):
    killed = False
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if str(p.info['pid']) == str(name_or_pid) or name_or_pid.lower() in str(p.info['name']).lower():
                p.kill()
                print(f"[OK] 프로세스 강제 종료 성공: {p.info['name']} (PID: {p.info['pid']})")
                killed = True
        except psutil.AccessDenied:
            print(f"[ERROR] 프로세스 종료 권한 없음: {p.info['name']} (PID: {p.info['pid']})")
        except Exception as e:
            pass
            
    if not killed:
        print(f"프로세스를 찾을 수 없습니다: {name_or_pid}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        list_processes()
    elif sys.argv[1] == "kill" and len(sys.argv) > 2:
        kill_process(sys.argv[2])
    else:
        print("사용법:")
        print("- 목록 조회: python process_manager.py")
        print("- 강제 종료: python process_manager.py kill \"프로세스이름 또는 PID\"")
