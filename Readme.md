# Commerce Management

라이브 커머스 운영 과정에서 발생하는 주문/상담 흐름을 정리하고, 내부 담당자가 처리할 수 있도록 돕는 서비스입니다.

## 목적

1. 채팅 주문 정보 정규화
   - 라이브 커머스 채팅에서 공유되는 불규칙한 사용자 주문 정보를 정규화된 포맷으로 정리합니다.
   - 채팅 내역은 사람이 입력/정리하고, 포맷 정의는 AI가 보조합니다.
2. 주문 진행/출고 확인 챗봇
   - 챗봇 기반으로 주문 진행 상황과 출고 제품 여부를 확인합니다.
   - 라이브 커머스 회사별 특수 기능을 고려해 대화 흐름을 설계합니다.
   - 사용자 불만 사항이 발생하면 내부 담당자에게 전달합니다.

## 시스템 구성

- API 서버: FastAPI 기반 단일 엔드포인트 제공
- LLM 클라이언트: OpenAI API 호출을 통한 의도 분류
- 서비스 계층: 의도 분류 후 핸들러로 라우팅
- 모델: 요청/응답 스키마 정의
- 테스트: API 라우팅 기본 검증

## 디렉터리 구조

```
app/
  api/v1/route.py          # /api/v1/chat 엔드포인트
  client/llm/chatgpt.py    # LLM 호출
  config/config.py         # 의도 목록
  model/chat/              # 요청/응답 모델
  service/chat/chat.py     # 의도 분류 및 핸들러
tests/
  api/v1/                  # API 테스트
```

## 설치

로컬 개발용 파이썬 환경을 준비한 뒤, 필요한 패키지를 설치합니다.

```
pip install fastapi uvicorn openai python-dotenv pydantic pytest
```

## 환경 변수

`.env` 파일에 아래 값을 설정합니다.

```
OPENAI_API_KEY=YOUR_KEY
MODEL=gpt-4
```

## 실행

```
uvicorn app.main:app --reload
```

## API 사용 예시

요청:

```
POST /api/v1/chat
Content-Type: application/json

{
  "session_id": "session-123",
  "message": "배송 언제 돼요?",
  "context": ["이전 대화"]
}
```

응답:

```
{
  "session_id": "session-123",
  "reply": "배송 상태 조회를 진행할게요. 주문번호나 운송장 번호를 알려주세요.",
  "usage": []
}
```

## 동작 흐름

1. 사용자가 메시지를 전송합니다.
2. LLM이 의도를 분류합니다.
3. 의도에 맞는 핸들러가 응답을 생성합니다.

## 로드맵

- 채팅 주문 정보 정규화 포맷 설계 및 저장소 연동
- 주문/배송 조회를 위한 외부 시스템 연동
- 불만/이슈 접수 자동화 및 내부 알림 연동
- 상담 기록 및 상태 추적 대시보드

## 테스트

```
pytest
```
