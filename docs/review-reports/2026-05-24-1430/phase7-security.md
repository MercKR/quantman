# Phase 7 — 보안

## 1. KIS 자격증명 격리

### 1.1 서버 격리 — ✅

```
grep -i "appkey|appsecret|account_number|kis_token|cano" platform/server
→ 0 매치 (주석·문서 포함)

grep "APP_KEY|APP_SECRET|app_key|app_secret|kis_appkey|kis_appsecret" platform/server
→ 0 매치
```

서버 schema·payload·로그 어디에도 KIS 자격증명 흔적 없음. 직전 cycle과 동일.

### 1.2 로컬 보안 — ✅

| 항목 | 결과 |
|---|---|
| **자격증명 keyring 저장** (`local/localapp/secrets_store.py:22`) | `keyring.set_password(KEYRING_SERVICE, _KIS, ...)` — Windows DPAPI 우회 |
| **device_token도 keyring** (line 41) | ✓ |
| **토큰 파일 ACL** (`file_security.py:44`) | Windows `icacls /inheritance:r /grant:r {user}:F` + Unix `chmod 0o600` |
| **fallback 정당화 주석** (`file_security.py:10-11`) | "실패가 기능을 막지 않도록 예외 삼키고 경고만" — 외부 OS 한계 명시 ✓ |

## 2. 인증 / 세션

### 2.1 JWT secret 길이 — ⚠️ SC-1

위치: `server/app/config.py:8,16`

```python
_DEFAULT_SECRET = "dev-insecure-secret-change-me"  # 29 chars
SECRET_KEY: str = os.getenv("QP_SECRET_KEY", _DEFAULT_SECRET)
```

**pytest 신호:**
```
InsecureKeyLengthWarning: The HMAC key is 29 bytes long,
which is below the minimum recommended length of 32 bytes for SHA256.
```

Production fail-fast (line 45-48)는 default secret 그대로 사용 시 부팅 차단 ✓. 그러나 **사용자가 임의의 29 bytes 이하 시크릿을 환경변수로 넣으면 통과** — RFC 7518 권장 32 bytes 미만 시 보안 약화 가능.

**제안 보강:** `if len(SECRET_KEY.encode()) < 32: raise RuntimeError(...)` production 분기 추가. (직전 cycle 미surface)

### 2.2 Production fail-fast — ✅

- `QP_SECRET_KEY` 미설정 시 부팅 차단
- `QP_HEALTH_TOKEN` 미설정 시 `/health/*/refresh` 호출 보호 부팅 차단

### 2.3 CORS — ✅

`QP_CORS_ORIGINS` 환경변수 default `http://localhost:5173,http://127.0.0.1:5173` — production은 Vercel 도메인 명시 필요. (운영 확인 사항)

## 3. SSRF · 외부 HTTP

이전 cycle test_webhook_ssrf 12 warnings (HMAC key length). functional pass. SSRF 자체 보호 코드 존재 확인됨.

## 4. 의존성 audit

| 명령 | 결과 |
|---|---|
| `npm audit --production` | found 0 vulnerabilities |
| `pip-audit -r server/requirements.txt` | No known vulnerabilities found |
| `pip-audit -r local/requirements.txt` | No known vulnerabilities found |

직전 cycle 동일 — 안정.

## 5. 발견 결함

### Medium

**SC-1 [Medium]** JWT SECRET_KEY 길이 미검증
- 위치: `server/app/config.py`
- 현재 production fail-fast는 "default secret 사용 금지"만 검증. 사용자가 짧은 시크릿 ENV로 설정 시 통과.
- 영향: HMAC SHA256 권장 32 bytes 미달 시 brute force 위험.
- 4원칙: 근본 원인(검증 갭) — fail-fast 패턴 확장. PR-1/2/3 미위반.

### Low

**SC-2 [Low]** pytest InsecureKeyLengthWarning 33건
- test_sync_preview_auth + test_webhook_ssrf의 HMAC key 29 bytes 사용.
- dev/test 환경이라 production 영향 0. SC-1 해소 시 test fixture도 32+ bytes로 교체.

## 6. 4원칙 자기검토 (Phase 7)

| 원칙 | 자기검토 |
|---|---|
| 근본원인 | SC-1은 fail-fast 검증 갭 — 근본 보강 후보 ✅ |
| Over-eng | KIS 격리 (server + local keyring + ACL)는 외부 OS 한계 명시한 정당 fallback ✅ |
| Over-think | grep 한 번 + audit 3개로 완결 ✅ |
| 검증된 해결책 | 명령 출력 직접 인용 + 코드 inspection ✅ |

## 7. Phase 9 전달

- **SC-1** JWT 길이 검증 (Medium, fail-fast 보강)
- **SC-2** test fixture HMAC 32 bytes 교체 (Low, SC-1 후속)
- 직전 cycle 회귀: 0
