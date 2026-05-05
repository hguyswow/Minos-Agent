# 🚨 GITHUB_PUSH_CHECKLIST.md
# GitHub 업로드 전 **필수** 체크리스트

> ⚠️ **이 문서는 Anti-Gravity AI Agent의 최우선 보안 수칙입니다.**  
> Git push 전 반드시 아래 항목을 **전부** 확인해야 합니다.  
> **단 하나라도 체크가 안 되면 절대로 push 금지.**

---

## 🔴 1단계: 민감 정보 스캔 실행 (자동화)

```bash
python scratch/check_secrets.py
```

결과가 `[OK] 민감 정보 없음` 이어야만 다음 단계로 진행.

---

## 🔴 2단계: 아래 항목 직접 눈으로 확인 (수동)

### 절대 올라가면 안 되는 파일
| 파일 | 포함 정보 | 상태 |
|------|-----------|------|
| `state/bot_config.json` | Telegram Bot Token | `.gitignore` 적용 확인 |
| `llm_config.json` | API 키, 엔드포인트 | `.gitignore` 적용 확인 |
| `state/user_states.json` | 사용자 대화 기록 | `.gitignore` 적용 확인 |
| `memory_logs/` | 장기 기억 데이터 | `.gitignore` 적용 확인 |
| `tentacles/data/` | 히스토리, 쿨다운 | `.gitignore` 적용 확인 |
| `tentacles/logs/` | 신호 로그 | `.gitignore` 적용 확인 |
| `logs/` | 텐터클 시그널 | `.gitignore` 적용 확인 |
| `*.bak` | 원본 코드 스냅샷 | `.gitignore` 적용 확인 |

### HTML / 소스 코드 내 개인 정보
- [ ] 실제 이메일 주소 (`@` 포함된 것)
- [ ] PayPal / 후원 링크
- [ ] 실제 은행 계좌번호
- [ ] 전화번호
- [ ] 실명
- [ ] 하드코딩된 API 토큰 / Secret Key

### 체크 방법 (grep으로 빠른 스캔)
```bash
python scratch/check_secrets.py
```

---

## 🔴 3단계: git status 확인

```bash
git status --short
```

`??` (untracked) 파일 중 민감 정보가 포함될 수 있는 것이 있으면 `.gitignore`에 추가 후 진행.

---

## ✅ 4단계: 안전 확인 후 push

```bash
git add -A
git commit -m "타입: 변경 요약"
git push origin main
```

---

## 📌 개인정보 플레이스홀더 규칙

| 실제 값 | GitHub에 올릴 값 |
|---------|-----------------|
| 실제 이메일 | `your-email@example.com` |
| PayPal 링크 | `paypal.me/your-username` |
| 계좌번호 | `YOUR-BANK-ACCOUNT-NUMBER` |
| 실명 | `[NAME]` |
| API 토큰 | `YOUR_API_TOKEN_HERE` |

---

> 🤖 **Anti-Gravity AI Agent 강제 수칙**  
> `git push` 명령을 내리기 전, 위 스캔 스크립트를 반드시 먼저 실행한다.  
> 스캔 결과가 `[OK]` 가 아니면 push를 거부하고 즉시 사용자에게 보고한다.
