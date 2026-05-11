#!/usr/bin/env python3
"""
MyMiniMe Studio — IR 이메일 발송 (Gmail API)

Usage:
  python send_ir_gmail.py --dry_run              # 미리보기만, 실제 발송 안 함
  python send_ir_gmail.py --dry_run --priority=3 # ⭐⭐⭐만 미리보기
  python send_ir_gmail.py --run_id=2026-05-08-g01 --priority=3   # ⭐⭐⭐ 발송
  python send_ir_gmail.py --run_id=2026-05-08-g02               # 전체 발송
"""
import argparse
import base64
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from email.utils import formatdate, make_msgid
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GMAIL_EXEC = Path("/Users/andy/Antigravity/2026/2월/자동 마케팅 이메일 발송/execution")
DIRECTIVE = "ir_email/send_ir_gmail.py"
DECK_URL_KR = "https://mymminime-pitchdeck.vercel.app"
DECK_URL_EN = "https://mymminime-pitchdeck.vercel.app/en"

sys.path.insert(0, str(GMAIL_EXEC))
from auth_test import authenticate_google
from googleapiclient.discovery import build


def log(run_id: str, status: str, **kwargs):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "directive_path": DIRECTIVE,
        "result_status": status,
    }
    entry.update(kwargs)
    print(json.dumps(entry, ensure_ascii=False), flush=True)


def encode_subject(subject: str) -> str:
    """RFC 2047 Q-encoding — Gmail API double-mojibake 우회"""
    chunks = []
    for i in range(0, len(subject), 10):
        chunk = subject[i:i + 10]
        utf8 = chunk.encode("utf-8")
        q = "".join(
            f"={b:02X}" if b > 127 or chr(b) in " =?_" else
            "_" if chr(b) == " " else chr(b)
            for b in utf8
        )
        chunks.append(f"=?utf-8?q?{q}?=")
    return " ".join(chunks)


def build_raw(sender: str, to: str, subject: str, html: str) -> str:
    encoded_subject = encode_subject(subject)
    body_b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
    body_lines = "\r\n".join(body_b64[i:i + 76] for i in range(0, len(body_b64), 76))
    raw = (
        f"From: {sender}\r\nTo: {to}\r\nSubject: {encoded_subject}\r\n"
        f"Date: {formatdate(localtime=True)}\r\nMessage-ID: {make_msgid()}\r\n"
        f"MIME-Version: 1.0\r\nContent-Type: text/html; charset=utf-8\r\n"
        f"Content-Transfer-Encoding: base64\r\n\r\n{body_lines}"
    )
    return base64.urlsafe_b64encode(raw.encode("ascii")).decode("ascii")


def load_template(lang: str) -> str:
    return (SCRIPT_DIR / f"template_{lang}.html").read_text(encoding="utf-8")


def build_html(investor: dict, tmpl_kr: str, tmpl_en: str) -> str:
    lang = investor.get("type", "kr")
    html = tmpl_kr if lang == "kr" else tmpl_en
    # 영문 템플릿의 deck URL을 /en 으로 교체
    if lang == "en":
        html = html.replace(DECK_URL_KR, DECK_URL_EN)
    html = html.replace("{{VC_NAME}}", investor["name"])
    html = html.replace("{{PORTFOLIO_NOTE}}", investor["portfolio_note"])
    return html


def subject_kr() -> str:
    return "[IR 제안] MyMiniMe Studio — 월 400+ 고객, 3D 디지털 자산 스튜디오 투자 검토 요청"


def subject_en() -> str:
    return "[Investment Inquiry] MyMiniMe Studio — 400+ monthly customers, Korea's 3D digital asset studio"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--run_id", default=None)
    parser.add_argument("--priority", type=int, default=None, help="최소 우선순위 (3=⭐⭐⭐만, 2=전체)")
    args = parser.parse_args()

    run_id = args.run_id or f"ir-gmail-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    investors = json.loads((SCRIPT_DIR / "investors.json").read_text(encoding="utf-8"))
    if args.priority:
        investors = [i for i in investors if i["priority"] >= args.priority]

    tmpl_kr = load_template("kr")
    tmpl_en = load_template("en")

    log(run_id, "START", total=len(investors), dry_run=args.dry_run, priority_filter=args.priority)

    if not args.dry_run:
        os.chdir(GMAIL_EXEC)
        creds = authenticate_google()
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        sender = f"MyMiniMe Studio <{profile['emailAddress']}>"
        log(run_id, "AUTH_OK", sender=profile["emailAddress"])
    else:
        sender = "MyMiniMe Studio <nadalgw@gmail.com>"

    ok, fail = 0, 0
    for i, inv in enumerate(investors):
        html = build_html(inv, tmpl_kr, tmpl_en)
        subject = subject_kr() if inv["type"] == "kr" else subject_en()

        if args.dry_run:
            log(run_id, "DRY_RUN", to=inv["email"], name=inv["name"],
                priority=inv["priority"], lang=inv["type"])
            ok += 1
            continue

        try:
            raw = build_raw(sender, inv["email"], subject, html)
            result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
            log(run_id, "SUCCESS", to=inv["email"], name=inv["name"],
                message_id=result["id"], priority=inv["priority"])
            ok += 1
        except Exception as e:
            log(run_id, "ERROR", to=inv["email"], name=inv["name"],
                error_type=type(e).__name__, detail=str(e))
            fail += 1

        if i < len(investors) - 1:
            time.sleep(2)

    log(run_id, "DONE", total=len(investors), ok=ok, fail=fail)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
