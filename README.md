# 댐 열화상 분석 MVP (Dam Thermal MVP)

이 프로젝트는 댐의 열화상 이미지를 분석하여 이상 징후를 감지하고 위험도를 평가하기 위한 MVP(Minimum Viable Product)입니다. 
열화상 이미지 프로세싱과 Blender를 이용한 3D 시각화 기능을 통합하여 제공합니다.


## 📂 프로젝트 구조

- `blender/`: 3D 시각화를 위한 Blender 스크립트 및 씬 파일
- `src/`: 열화상 분석 및 데이터 통합 핵심 로직
- `data/`: 샘플 이미지 및 메타데이터
- `configs/`: 분석 및 위험도 가중치 설정 파일
- `outputs/`: 생성된 JSON 결과물, 스크린샷, 보고서 등


## MVP 실행 흐름

<수동>
1. 1단계: Blender 지형 및 셀 생성
   - Blender에서 `blender/scripts/01_create_dam_cells.py` 스크립트를 실행합니다.
   - ➜ 댐의 기본 구조와 분석용 셀(Cell)들이 생성됩니다.

2. 2단계: 열화상 분석 파이프라인 실행
   - 일반 Python 환경에서 열화상 분석 파이프라인을 실행합니다.
   - ➜ 열화상 이미지를 처리하고 분석 결과인 `thermal_result.json` 파일을 생성합니다.

3. 3단계: 시각화 업데이트
   - Blender에서 `blender/scripts/02_apply_thermal_result.py` 스크립트를 실행합니다.
   - ➜ 분석된 위험도 결과가 3D 셀의 색상으로 반영됩니다.

<자동화 플로우>
python run_pipeline_auto --gui 실행시 바로 blender에 결과를 띄어줌
---



## 🛠 실행 명령어 (Bash)

열화상 분석 파이프라인을 수동으로 실행하려면 아래 명령어를 사용하세요:

```bash
python -m src.thermal.run_pipeline \
  --image data/sample_thermal/thermal_sample_01.png \
  --cell-json outputs/blender_json/dam_attached_body_outer_cells_directional_risk.json \
  --output outputs/thermal_json/thermal_result.json
```

---

## 📊 데이터 포맷 (JSON 통일)

분석 파이프라인과 Blender 시각화 간의 원활한 연동을 위해 다음과 같은 통일된 JSON 구조를 사용합니다:

```json
{
  "metadata": {
    "source": "thermal_sample_01.png",
    "analysis_type": "thermal_moisture_risk",
    "note": "Dummy thermal MVP result"
  },
  "cells": [
    {
      "cell_id": "S03_X02_Z14",
      "slice_id": 3,
      "thermal_mean_temp_c": 22.8,
      "thermal_delta_t_c": -1.6,
      "thermal_anomaly_score": 0.73,
      "seepage_probability": 0.81,
      "moisture_level": "high",
      "thermal_risk_level": 3,
      "thermal_confidence": 0.84
    }
  ]
}
```

---

## 🌐 웹 테스트용 프론트엔드 (Web Testing Frontend)

댐 열화상 분석 및 Blender Headless 3D 렌더링 과정을 웹 브라우저에서 직관적으로 검증할 수 있는 테스트용 대시보드를 제공합니다.

### 1. 가상환경 패키지 설치
웹 서버 구동에 필요한 라이브러리(`fastapi`, `uvicorn`, `python-multipart`, `requests`)를 설치합니다:
```bash
.venv\Scripts\pip install fastapi uvicorn python-multipart requests
```

### 2. 웹 서버 실행
프로젝트 루트에서 다음 명령어를 실행하여 로컬 개발 서버를 구동합니다:
```bash
.venv\Scripts\python web_server.py
```
- 서버 주소: `http://127.0.0.1:8000`

### 3. 기능 안내
- **데이터 업로드**: 드래그 앤 드롭 또는 클릭하여 열화상 이미지를 업로드할 수 있습니다.
- **매티리얼 설정**: 콘크리트(Concrete) 또는 필댐(Earthfill) 재질을 설정할 수 있습니다.
- **실시간 콘솔 로그**: 파이프라인(Blender 셀 생성 ➜ Python 열화상 분석 ➜ Blender 리스크 색상 투영 및 3D 렌더링)의 표준 출력을 웹상의 콘솔 창에서 실시간으로 확인할 수 있습니다.
- **분석 대시보드**: 3D Blender 렌더 이미지와 원본 이미지 탭을 제공하며, 위험도 단계별 셀 개수 및 온도 수치 통계를 대시보드 카드에 자동 시각화합니다.


