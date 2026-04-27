import sys
import ctypes

def control_system(action, value=None):
    if action == "lock":
        # 윈도우 화면 잠금
        ctypes.windll.user32.LockWorkStation()
        print("[OK] PC 화면을 잠금 상태로 전환했습니다.")
    elif action == "mute":
        # 음소거 토글 (가상 키코드 이용: VK_VOLUME_MUTE = 0xAD)
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        print("[OK] 시스템 음소거를 토글(ON/OFF)했습니다.")
    elif action == "volume_up":
        # VK_VOLUME_UP = 0xAF
        steps = int(value) if value else 5
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
        print(f"[OK] 시스템 볼륨을 {steps}칸 올렸습니다.")
    elif action == "volume_down":
        # VK_VOLUME_DOWN = 0xAE
        steps = int(value) if value else 5
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
        print(f"[OK] 시스템 볼륨을 {steps}칸 내렸습니다.")
    else:
        print("[ERROR] 알 수 없는 명령입니다. (가능한 명령: lock, mute, volume_up, volume_down)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python system_api_caller.py [명령어] [값]")
        print("예시: python system_api_caller.py volume_up 10")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    value = sys.argv[2] if len(sys.argv) > 2 else None
    control_system(action, value)
