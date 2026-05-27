# KIS API Knowledge Base

KIS Open API 호출·결함 진단·새 endpoint 사용 시 **작업 전 반드시 참조**.
시행착오를 코드에 반복하지 않기 위한 single source of truth.

## 구조

```
docs/kis-api/
├── README.md                # 이 파일
├── INDEX.md                 # ⭐ 전체 endpoint 한 줄 색인 (grep용)
├── GOTCHAS.md               # ⭐ 실측 발견사항 — 공식 docs와 다른 동작
├── CHANGELOG.md             # 발견 시계열 (release fix와 연동)
├── raw/                     # 사용자 제공 원본 docs (xlsx, pdf — 변환 안 함)
│   └── 해외주식_기본시세.xlsx
└── endpoints/               # endpoint별 상세 (TR_ID 파일명)
    ├── HHDFS76200200_*.md   # 해외주식 현재가상세
    ├── HHDFS00000300_*.md   # 해외주식 현재체결가
    ├── HHDFS76950200_*.md   # 분봉
    └── ... (14개)
```

## 사용 흐름 — Claude·개발자 모두

1. **INDEX.md에서 endpoint 후보 찾기** — `grep -i "시초가" INDEX.md` 같이
2. **`endpoints/{TR_ID}_*.md` 읽기** — request/response/모의실전/한계
3. **GOTCHAS.md 한 번 훑기** — 실측 결과 (공식 doc과 다른 동작)
4. raw docs (`raw/*.xlsx`) 더 깊은 정보 필요 시 직접 열어 확인

## 작업 중 발견 시 즉시 기록 (자가발전)

| 발견 종류 | 기록 위치 |
|---|---|
| 새 endpoint 사용 | `endpoints/{TR_ID}_*.md` 새 파일 작성 |
| 공식 doc과 실측 다름 | `GOTCHAS.md`에 한 줄 (날짜·증상·원인·해결) |
| 릴리즈 fix | `CHANGELOG.md`에 entry |
| 우리 코드에서 사용 | endpoint .md의 `우리 코드 위치` 섹션에 file:line 추가 |
| doc 자체 부족 | 사용자에게 명시 요청 — "KIS docs '주문' sheet xlsx 필요" |

## 다른 API에도 같은 패턴

```
docs/
├── kis-api/         # 현재
├── yfinance/        # 서버 dataset_fetcher 사용 — TBD
├── ecos/            # 한국은행 매크로 — TBD
└── polygon/         # 향후
```

## 4원칙 측면

이 knowledge base는 **PR-4 (검증 누락) 예방**의 도구. 매 호출마다 실측·검증하지 않아도 누적된 GOTCHAS가 알려진 함정을 알려줌. PR-3 (Overthinking)도 — endpoint 후보 미리 알면 잘못된 endpoint로 돌아가는 시행착오 회피.
