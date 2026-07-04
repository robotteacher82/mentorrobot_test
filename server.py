import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, send_from_directory

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TOKENS_FILE = BASE_DIR / "tokens.json"
RESERVATIONS_FILE = DATA_DIR / "reservations.json"

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_REDIRECT_URI = os.getenv(
    "KAKAO_REDIRECT_URI", "http://localhost:8080/auth/kakao/callback"
)

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_tokens():
    if not TOKENS_FILE.exists():
        return None
    with TOKENS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_tokens(tokens):
    with TOKENS_FILE.open("w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def refresh_access_token(tokens):
    if not tokens or not tokens.get("refresh_token"):
        return None

    response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "refresh_token": tokens["refresh_token"],
        },
        timeout=10,
    )
    if response.status_code != 200:
        return None

    refreshed = response.json()
    tokens["access_token"] = refreshed["access_token"]
    if refreshed.get("refresh_token"):
        tokens["refresh_token"] = refreshed["refresh_token"]
    tokens["updated_at"] = datetime.now().isoformat()
    save_tokens(tokens)
    return tokens


def send_kakao_memo(message):
    tokens = load_tokens()
    if not tokens:
        return False, "카카오 로그인이 필요합니다. /auth/kakao 에서 연동해 주세요."

    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    }
    template = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "http://localhost:8080/#reservation",
            "mobile_web_url": "http://localhost:8080/#reservation",
        },
        "button_title": "예약 확인",
    }
    data = {"template_object": json.dumps(template, ensure_ascii=False)}

    response = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers=headers,
        data=data,
        timeout=10,
    )

    if response.status_code == 401:
        refreshed = refresh_access_token(tokens)
        if not refreshed:
            return False, "카카오 토큰이 만료되었습니다. /auth/kakao 에서 다시 연동해 주세요."
        headers["Authorization"] = f"Bearer {refreshed['access_token']}"
        response = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers=headers,
            data=data,
            timeout=10,
        )

    if response.status_code == 200:
        return True, "알림 전송 완료"

    try:
        error = response.json()
    except ValueError:
        error = {"message": response.text}
    return False, f"카카오 알림 전송 실패: {error}"


def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if not re.fullmatch(r"01[016789]\d{7,8}", digits):
        return None
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"


def save_reservation(payload):
    ensure_data_dir()
    records = []
    if RESERVATIONS_FILE.exists():
        with RESERVATIONS_FILE.open(encoding="utf-8") as f:
            records = json.load(f)

    payload["created_at"] = datetime.now().isoformat()
    records.append(payload)

    with RESERVATIONS_FILE.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def build_kakao_message(data):
    return "\n".join(
        [
            "[멘토로봇코딩교육원 상담예약]",
            "",
            f"보호자: {data['parent_name']}",
            f"연락처: {data['phone']}",
            f"학생 학년: {data['student_grade']}",
            f"희망 상담일: {data['preferred_date']}",
            f"희망 시간: {data['preferred_time']}",
            f"문의 내용: {data['message'] or '없음'}",
            "",
            f"접수: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ]
    )


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    file_path = BASE_DIR / path
    if file_path.is_file():
        return send_from_directory(BASE_DIR, path)
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/auth/kakao")
def kakao_login():
    if not KAKAO_REST_API_KEY:
        return (
            "KAKAO_REST_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.",
            500,
        )

    params = urlencode(
        {
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "response_type": "code",
            "scope": "talk_message",
        }
    )
    return redirect(f"https://kauth.kakao.com/oauth/authorize?{params}")


@app.route("/auth/kakao/callback")
def kakao_callback():
    code = request.args.get("code")
    if not code:
        return "카카오 인증에 실패했습니다.", 400

    response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code,
        },
        timeout=10,
    )

    if response.status_code != 200:
        return f"토큰 발급 실패: {response.text}", 400

    tokens = response.json()
    tokens["connected_at"] = datetime.now().isoformat()
    save_tokens(tokens)

    return """
    <html><body style="font-family:sans-serif;text-align:center;padding:40px;">
      <h2>카카오톡 알림 연동 완료</h2>
      <p>이제 상담예약이 접수되면 카카오톡으로 알림이 전송됩니다.</p>
      <p><a href="/">랜딩페이지로 돌아가기</a></p>
    </body></html>
    """


@app.route("/api/kakao-status")
def kakao_status():
    tokens = load_tokens()
    return jsonify({"connected": bool(tokens and tokens.get("access_token"))})


@app.route("/api/reservation", methods=["POST"])
def create_reservation():
    data = request.get_json(silent=True) or {}

    parent_name = (data.get("parent_name") or "").strip()
    phone = normalize_phone(data.get("phone") or "")
    student_grade = (data.get("student_grade") or "").strip()
    preferred_date = (data.get("preferred_date") or "").strip()
    preferred_time = (data.get("preferred_time") or "").strip()
    message = (data.get("message") or "").strip()
    privacy_agree = data.get("privacy_agree")

    if not parent_name:
        return jsonify({"ok": False, "error": "보호자 이름을 입력해 주세요."}), 400
    if not phone:
        return jsonify({"ok": False, "error": "올바른 연락처를 입력해 주세요."}), 400
    if not student_grade:
        return jsonify({"ok": False, "error": "학생 학년을 선택해 주세요."}), 400
    if not preferred_date:
        return jsonify({"ok": False, "error": "희망 상담일을 선택해 주세요."}), 400
    if not preferred_time:
        return jsonify({"ok": False, "error": "희망 시간을 선택해 주세요."}), 400
    if not privacy_agree:
        return jsonify({"ok": False, "error": "개인정보 수집에 동의해 주세요."}), 400

    payload = {
        "parent_name": parent_name,
        "phone": phone,
        "student_grade": student_grade,
        "preferred_date": preferred_date,
        "preferred_time": preferred_time,
        "message": message,
    }

    save_reservation(payload)

    kakao_message = build_kakao_message(payload)
    sent, detail = send_kakao_memo(kakao_message)

    if sent:
        return jsonify({"ok": True, "message": "상담예약이 접수되었습니다. 곧 연락드리겠습니다."})

    return jsonify(
        {
            "ok": True,
            "message": "상담예약은 접수되었습니다. (카카오 알림: " + detail + ")",
            "warning": detail,
        }
    )


if __name__ == "__main__":
    ensure_data_dir()
    app.run(host="0.0.0.0", port=8080, debug=True)
