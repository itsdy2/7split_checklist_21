# 세븐스플릿 스크리닝 (7split_checklist_21)

FlaskFarm 플러그인 - 세븐스플릿의 21가지 체크리스트를 기반으로 KOSPI/KOSDAQ 종목을 자동 스크리닝합니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 📊 소개

세븐스플릿 투자 철학에 기반한 **다양한 투자 전략**을 제공하는 FlaskFarm 플러그인입니다. 여러 전략 중 원하는 방식을 선택하여 KOSPI/KOSDAQ 종목을 자동으로 스크리닝할 수 있습니다.

### 주요 기능

- ✅ **4가지 투자 전략 제공**
  - 세븐스플릿 21개 조건 (엄격한 품질 필터링)
  - 세븐스플릿 핵심 10개 (빠른 스크리닝)
  - 배당주 전략 (안정적 배당 수익)
  - 가치투자 전략 (저평가 우량주)
  
- 🎯 **전략 선택 시스템**
  - 전략별 상세 정보 및 조건 확인
  - 기본 전략 설정 기능
  - 전략별 결과 분리 조회
  
- 📈 **다양한 데이터 소스**
  - pykrx: 시장 데이터
  - FinanceDataReader: 재무제표
  - OpenDartReader: 공시 정보

- 📢 **Discord 알림 지원**
  - 스크리닝 시작/완료 알림
  - 통과 종목 요약 전송

- 🕐 **자동 스케줄링**
  - 평일 자동 실행 (시간 설정 가능)
  - 수동 실행 지원

- 📊 **웹 대시보드**
  - 결과 조회 및 필터링
  - 종목 상세 분석
  - 이력 조회 및 통계

## 🔧 설치 방법

### 1. FlaskFarm에서 설치 (권장)

1. FlaskFarm 관리자 페이지 접속
2. **[시스템] → [플러그인]** 메뉴
3. "플러그인 설치" 버튼 클릭
4. GitHub URL 입력:
   ```
   https://github.com/yourusername/7split_checklist_21
   ```
5. 설치 완료 후 자동 재시작

### 2. 수동 설치

```bash
cd /path/to/FlaskFarm/plugin
git clone https://github.com/yourusername/7split_checklist_21.git
cd 7split_checklist_21
pip3 install -r requirements.txt
```

### 3. ARM64 (Oracle Cloud A1) 환경

```bash
# lxml 빌드를 위한 의존성 설치
sudo apt-get update
sudo apt-get install -y libxml2-dev libxslt1-dev python3-dev gcc

# 패키지 설치
pip3 install -r requirements.txt
```

## ⚙️ 초기 설정

### 1. DART API Key 발급 (필수)

1. [DART 홈페이지](https://opendart.fss.or.kr/) 접속
2. 회원가입 후 로그인
3. **오픈API → 인증키 신청/관리**
4. 인증키 발급 (즉시 발급, 무료)

### 2. Discord Webhook 설정 (선택)

1. Discord 서버 → 채널 설정
2. **연동 → 웹후크 → 새 웹후크**
3. 웹후크 URL 복사

### 3. 플러그인 설정

1. FlaskFarm에서 **[세븐스플릿 스크리닝] → [설정]** 메뉴
2. DART API Key 입력
3. Discord Webhook URL 입력 (선택)
4. 자동 실행 시간 설정 (기본: 09:00)
5. 저장

## 📋 21가지 체크리스트

### 제외 조건 (11개)

| 번호 | 조건 | 설명 |
|------|------|------|
| 1-6 | 관리종목, 거래정지, 환기종목, 정리매매, 불성실공시, 상장폐지 | 투자 부적합 종목 제외 |
| 7 | 시가총액 1000억 이상 | 소형주 제외 |
| 8 | 부채비율 300% 미만 | 재무 안정성 |
| 9 | 유보율 100% 이상 | 내부 유보 충분 |
| 10 | 3년 연속 적자 제외 | 수익성 확보 |
| 11 | 거래대금 10억 이상 | 유동성 확보 |

### 선별 조건 (10개)

| 번호 | 조건 | 설명 |
|------|------|------|
| 12 | ROE 3년 평균 15% 이상 | 자기자본 수익성 |
| 13 | PBR 1 이상 | 저평가 배제 |
| 14 | PER 10 이상 | 적정 밸류에이션 |
| 15 | 배당수익률 3% 이상 | 주주 환원 |
| 16 | PCR 10 이상 | 현금흐름 대비 가치 |
| 17 | PSR 1 이상 | 매출액 대비 가치 |
| 18 | F-SCORE 5점 이상 | 피오트로스키 품질 점수 |
| 19 | 최근 1년 CB/BW 미발행 | 주식 희석 우려 배제 |
| 20 | 최근 1년 유상증자 미실시 | 자금 조달 건전성 |
| 21 | 최대주주 지분율 30% 이상 | 지배구조 안정성 |

## 🚀 사용 방법

### 자동 실행

1. 설정에서 "자동 실행 활성화" 체크
2. 실행 시간 설정 (기본: 오전 9시)
3. 평일 자동 실행

### 수동 실행

1. **[수동 실행]** 메뉴 클릭
2. "스크리닝 시작" 버튼 클릭
3. 진행 상황 실시간 확인
4. 완료 후 결과 페이지로 자동 이동

### 결과 조회

1. **[스크리닝 결과]** 메뉴
2. 날짜/시장별 필터링
3. 종목 클릭 → 상세 정보 확인
4. CSV 다운로드 가능

## 📊 데이터 수집 소스

### pykrx
- 시가총액
- 거래대금
- PER, PBR, 배당수익률

### FinanceDataReader
- 재무제표 (보조)
- 가치지표 (보조)

### OpenDartReader (DART API)
- 부채비율, 유보율
- ROE, 당기순이익
- CB/BW 발행 이력
- 유상증자 이력
- 최대주주 지분율

## ⏱️ 성능

- **전체 종목 수**: 약 2,500개 (KOSPI + KOSDAQ)
- **예상 소요 시간**: 30분 ~ 1시간
- **API 제한**: DART API 일일 10,000건 (충분)

## 🐛 문제 해결

### lxml 설치 오류 (ARM64)

```bash
sudo apt-get install -y libxml2-dev libxslt1-dev
pip3 install --no-binary lxml lxml
```

### DART API 오류

- API Key 확인
- 일일 호출 제한 확인 (10,000건)
- 네트워크 연결 확인

### 스크리닝이 멈춤

- 로그 확인: `[로그]` 메뉴
- 실행 이력 확인: `[실행 이력]` 메뉴
- 서버 재시작

## 📝 라이선스

MIT License

Copyright (c) 2024 FlaskFarm Community

## 👨‍💻 개발자

- GitHub: https://github.com/yourusername/7split_checklist_21
- Issues: https://github.com/yourusername/7split_checklist_21/issues

## 🙏 감사의 말

- FlaskFarm 프레임워크
- pykrx, FinanceDataReader, OpenDartReader 개발자분들
- 세븐스플릿 투자 철학

## 📚 참고 자료

- [세븐스플릿 블로그](https://blog.naver.com/7split)
- [DART 오픈API](https://opendart.fss.or.kr/)
- [FlaskFarm 문서](https://github.com/flaskfarm)