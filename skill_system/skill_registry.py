import os

class SkillRegistry:
    """
    안티그래비티 절차적 기억 (스킬) 관리 모듈
    무거운 파이썬 코드는 skills 폴더에 저장하고, 가벼운 설명만 인덱스에 저장합니다.
    """
    def __init__(self, system_dir: str):
        self.system_dir = system_dir
        self.skills_dir = os.path.join(self.system_dir, "skills")
        self.index_file = os.path.join(self.system_dir, "skills_index.txt")
        
        os.makedirs(self.skills_dir, exist_ok=True)
        
        # 인덱스 파일이 없으면 초기화 (이미 있으면 덮어쓰지 않음)
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                f.write("현재 등록된 스킬이 없습니다.\n")

    def get_skills_index_text(self) -> str:
        """가벼운 스킬 요약 목록(인덱스)을 텍스트로 반환합니다."""
        if not os.path.exists(self.index_file):
            return "현재 등록된 스킬이 없습니다."
            
        with open(self.index_file, "r", encoding="utf-8") as f:
            return f.read().strip()

    def save_skill(self, name: str, description: str, code: str) -> str:
        """
        봇이 작성한 파이썬 스크립트를 파일로 저장하고, 인덱스를 업데이트합니다.
        """
        # 안전한 파일명 생성
        safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-'))
        if not safe_name:
            safe_name = "unknown_skill"
            
        file_path = os.path.join(self.skills_dir, f"{safe_name}.py")
        
        # 코드 저장 (무거운 파이썬 스크립트)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # 인덱스에 한 줄 요약 추가 (가벼운 기억)
        # 만약 "현재 등록된 스킬이 없습니다."가 있으면 덮어쓰고, 아니면 추가
        current_index = self.get_skills_index_text()
        new_entry = f"- {safe_name}: {description} (실행: <CMD>python {file_path}</CMD>)"
        
        if "현재 등록된 스킬이 없습니다" in current_index:
            new_index = new_entry + "\n"
        else:
            # 중복 체크 방지 (단순화를 위해 일단 append)
            if safe_name not in current_index:
                new_index = current_index + "\n" + new_entry + "\n"
            else:
                new_index = current_index # 이미 있으면 인덱스 수정 안함 (코드만 덮어씀)
                
        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write(new_index.strip() + "\n")
            
        return f"[시스템]: '{safe_name}' 스킬이 영구 저장소에 성공적으로 등록되었습니다! 이제 <CMD>python {file_path}</CMD> 명령어로 언제든 꺼내 쓸 수 있습니다."
