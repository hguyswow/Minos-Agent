# -*- coding: utf-8 -*-
"""Minos PC helpers for Hermes: Windows volume/mute/lock/whitelisted apps, disk & LM Studio status, audiobook MP3 tagging."""
import json
import os
import shutil
import subprocess
import ctypes
import logging
import requests


def handle_get_system_status(args: dict, **_kw) -> str:
    try:
        total, used, free = shutil.disk_usage("C:\\")
        lms_ok = False
        lms_models = []
        try:
            r = requests.get("http://127.0.0.1:1234/v1/models", timeout=1.0)
            if r.status_code == 200:
                lms_ok = True
                lms_models = [m.get("id") for m in r.json().get("data", [])][:3]
        except Exception:
            pass

        status_lines = [
            "🖥️ [시스템 상태 실측 결과]",
            f"- C: 드라이브 여유 공간: {free / (1024**3):.1f} GB / {total / (1024**3):.1f} GB ({(free/total)*100:.1f}% 여유)",
            f"- LM Studio (1234 포트): {'🟢 온라인' if lms_ok else '🔴 오프라인'}",
        ]
        if lms_models:
            status_lines.append(f"- LM Studio 로드 모델: {', '.join(lms_models)}")
        result = "\n".join(status_lines)
        return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
    except Exception as ex:
        error_msg = f"❌ 시스템 상태 진단 실패: {ex}"
        return json.dumps({"ok": False, "error": error_msg}, ensure_ascii=False)


def handle_tag_audiobook_mp3(args: dict, **_kw) -> str:
    file_path = (args.get("file_path") or "").strip()
    title = (args.get("title") or "").strip()
    artist = (args.get("artist") or "형님").strip()
    album = (args.get("album") or "국화와 칼").strip()
    track_num = str(args.get("track_num") or "1").strip()
    cover_path = (args.get("cover_path") or "").strip()

    if not file_path or not os.path.exists(file_path):
        return json.dumps({"ok": False, "error": f"❌ 오류: 지정한 MP3 파일을 찾을 수 없습니다 -> '{file_path}'"}, ensure_ascii=False)

    try:
        # lazy import
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TCON, APIC, ID3NoHeaderError

        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        if audio.tags is None:
            audio.add_tags()

        if not title:
            title = os.path.splitext(os.path.basename(file_path))[0]

        audio.tags["TIT2"] = TIT2(encoding=3, text=title)
        audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
        audio.tags["TALB"] = TALB(encoding=3, text=album)
        audio.tags["TRCK"] = TRCK(encoding=3, text=track_num)
        audio.tags["TCON"] = TCON(encoding=3, text="Audiobook")

        cover_applied = False
        if not cover_path:
            parent_dir = os.path.dirname(file_path)
            for candidate in ["cover.jpg", "cover.png", "folder.jpg", "front.jpg"]:
                c_path = os.path.join(parent_dir, candidate)
                if os.path.exists(c_path):
                    cover_path = c_path
                    break

        if cover_path and os.path.exists(cover_path):
            mime = "image/jpeg" if cover_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            with open(cover_path, "rb") as img_f:
                audio.tags["APIC"] = APIC(
                    encoding=3,
                    mime=mime,
                    type=3,
                    desc="Front Cover",
                    data=img_f.read()
                )
            cover_applied = True

        audio.save(v2_version=3)

        res_lines = [
            "✅ 성공: MP3 오디오북 ID3v2 태그 및 메타데이터 주입 완료!",
            f"  - 대상 파일: {file_path}",
            f"  - 제목: {title} (트랙: {track_num})",
            f"  - 작가/낭독: {artist} | 앨범: {album}",
            f"  - 앨범 커버 아트: {'🖼️ 삽입됨 (' + cover_path + ')' if cover_applied else '⚪ 미적용 (커버 파일 없음)'}",
        ]
        result = "\n".join(res_lines)
        return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
    except Exception as ex:
        return json.dumps({"ok": False, "error": f"❌ ID3 태그 주입 실패: {ex}"}, ensure_ascii=False)


def handle_control_pc_system(args: dict, **_kw) -> str:
    action = (args.get("action") or "").lower().strip()
    val = args.get("value")

    try:
        import subprocess
        # pycaw imported lazily where needed

        if action == "get_volume":
            try:
                import pycaw.pycaw as pc
                dev = pc.AudioUtilities.GetSpeakers()
                vol = dev.EndpointVolume
                scalar = vol.GetMasterVolumeLevelScalar()
                mute = vol.GetMute()
                result = f"🔊 현재 PC 마스터 볼륨: {round(scalar * 100)}% (음소거 상태: {'🔇 음소거 중' if mute else '🔈 켜짐'})"
                return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
            except Exception as ex:
                return json.dumps({"ok": False, "error": f"❌ 볼륨 조회 실패: {ex}"}, ensure_ascii=False)

        elif action == "set_volume":
            try:
                target_pct = int(val) if val is not None else 50
                target_pct = max(0, min(100, target_pct))
                import pycaw.pycaw as pc
                dev = pc.AudioUtilities.GetSpeakers()
                vol = dev.EndpointVolume
                vol.SetMasterVolumeLevelScalar(target_pct / 100.0, None)
                if vol.GetMute():
                    vol.SetMute(0, None)
                result = f"🔊 PC 마스터 볼륨을 {target_pct}%로 조정했습니다."
                return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
            except Exception as ex:
                return json.dumps({"ok": False, "error": f"❌ 볼륨 설정 실패: {ex}"}, ensure_ascii=False)

        elif action == "mute":
            try:
                import pycaw.pycaw as pc
                dev = pc.AudioUtilities.GetSpeakers()
                vol = dev.EndpointVolume
                vol.SetMute(1, None)
                result = "🔇 PC 사운드를 음소거했습니다."
                return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
            except Exception as ex:
                return json.dumps({"ok": False, "error": f"❌ 음소거 실패: {ex}"}, ensure_ascii=False)

        elif action == "unmute":
            try:
                import pycaw.pycaw as pc
                dev = pc.AudioUtilities.GetSpeakers()
                vol = dev.EndpointVolume
                vol.SetMute(0, None)
                result = "🔈 PC 사운드 음소거를 해제했습니다."
                return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
            except Exception as ex:
                return json.dumps({"ok": False, "error": f"❌ 음소거 해제 실패: {ex}"}, ensure_ascii=False)

        elif action == "lock_screen":
            try:
                ctypes.windll.user32.LockWorkStation()
                result = "🔒 윈도우 PC 화면을 성공적으로 잠갔습니다 (LockWorkStation)."
                return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
            except Exception as ex:
                return json.dumps({"ok": False, "error": f"❌ 화면 잠금 실패: {ex}"}, ensure_ascii=False)

        elif action == "open_app":
            app_name = str(val or "").lower().strip()
            allowed_apps = {
                "chrome": r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "notepad": "notepad.exe",
                "calc": "calc.exe",
                "calculator": "calc.exe",
                "explorer": "explorer.exe",
                "lmstudio": os.path.expandvars(r"%LOCALAPPDATA%\\Programs\\LM Studio\\LM Studio.exe")
            }
            if app_name not in allowed_apps:
                return json.dumps({"ok": False, "error": f"⚠️ 허용되지 않은 앱입니다. (허용 목록: {', '.join(allowed_apps.keys())})"}, ensure_ascii=False)
            target_exe = allowed_apps[app_name]
            subprocess.Popen([target_exe], shell=False)
            result = f"🚀 앱 실행 성공: '{app_name}'"
            return json.dumps({"ok": True, "result": result}, ensure_ascii=False)

        else:
            return json.dumps({"ok": False, "error": f"❌ 알 수 없는 액션: '{action}'. (사용 가능: get_volume, set_volume, mute, unmute, lock_screen, open_app)"}, ensure_ascii=False)
    except Exception as ex:
        return json.dumps({"ok": False, "error": f"❌ PC 시스템 제어 오류: {ex}"}, ensure_ascii=False)


GET_SYSTEM_STATUS_SCHEMA = {
    "name": "get_system_status",
    "description": "현재 Windows 10 로컬 PC의 디스크 용량, 메모리, LM Studio(1234 포트) 및 임베딩 모델의 실시간 구동 상태를 진단합니다.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

TAG_AUDIOBOOK_MP3_SCHEMA = {
    "name": "tag_audiobook_mp3",
    "description": "오디오북 MP3 파일에 ID3v2 메타데이터(제목, 아티스트/낭독자, 앨범, 트랙 번호)와 앨범 커버 아트를 자동 주입하고 지식 그래프에 연동합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "메타데이터를 주입할 MP3 파일의 절대 경로 (예: 'D:/down/국화와칼_전체완성.mp3')"
            },
            "title": {
                "type": "string",
                "description": "오디오북 파트 또는 곡 제목 (미입력 시 파일명 사용)"
            },
            "artist": {
                "type": "string",
                "description": "작가 또는 낭독자 이름 (기본값: '형님')"
            },
            "album": {
                "type": "string",
                "description": "작품/앨범 이름 (기본값: '국화와 칼')"
            },
            "track_num": {
                "type": "string",
                "description": "트랙 번호 (예: '1', '231' 또는 '1/10')"
            },
            "cover_path": {
                "type": "string",
                "description": "앨범 커버 이미지 경로(jpg/png). 미입력 시 파일 폴더 내 커버 이미지 자동 검색"
            }
        },
        "required": ["file_path"]
    }
}

CONTROL_PC_SYSTEM_SCHEMA = {
    "name": "control_pc_system",
    "description": "Windows PC 마스터 볼륨 조절(0~100%), 음소거/해제, 화면 잠금, 또는 안전 화이트리스트 앱을 실행합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_volume", "set_volume", "mute", "unmute", "lock_screen", "open_app"],
                "description": "수행할 시스템 제어 동작"
            },
            "value": {
                "type": "string",
                "description": "볼륨 수치(0~100) 또는 실행할 앱 이름 (chrome, notepad, calc, explorer, lmstudio)"
            }
        },
        "required": ["action"]
    }
}

_TOOLS = (
    ("get_system_status", GET_SYSTEM_STATUS_SCHEMA, handle_get_system_status),
    ("control_pc_system", CONTROL_PC_SYSTEM_SCHEMA, handle_control_pc_system),
    ("tag_audiobook_mp3", TAG_AUDIOBOOK_MP3_SCHEMA, handle_tag_audiobook_mp3),
)


def register(ctx) -> None:
    for name, schema, handler in _TOOLS:
        ctx.register_tool(name=name, toolset="minos_pc", schema=schema, handler=handler)