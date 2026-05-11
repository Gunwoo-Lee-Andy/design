#!/usr/bin/env python3
"""
MyMiniMe Studio — VC IR 이메일 발송 스크립트

Usage:
  python send_ir_emails.py --dry_run              # 미리보기만, 실제 발송 안 함
  python send_ir_emails.py --run_id=2026-05-08-001 --priority=3   # ⭐⭐⭐만 발송
  python send_ir_emails.py --run_id=2026-05-08-002               # 전체 발송
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

SCRIPT_DIR   = Path(__file__).parent
RESEND_API   = "https://api.resend.com/emails"
RESEND_KEY   = "re_bW3BJRYb_ASyupt7xBGUyQvFPW5byUDCe"
FROM_EMAIL   = "MyMiniMe Studio <ir@myminime.co.kr>"
DECK_URL     = "https://mymminime-pitchdeck.vercel.app"
DIRECTIVE    = "ir_email/send_ir_emails.py"


def log(run_id: str, result_status: str, error_type=None, **kwargs):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "directive_path": DIRECTIVE,
        "result_status": result_status,
        "error_type": error_type,
    }
    entry.update(kwargs)
    print(json.dumps(entry, ensure_ascii=False), flush=True)


def load_template(lang: str) -> str:
    path = SCRIPT_DIR / f"template_{lang}.html"
    return path.read_text(encoding="utf-8")


def build_html(investor: dict, template_kr: str, template_en: str) -> str:
    lang = investor.get("type", "kr")
    html = template_kr if lang == "kr" else template_en
    html = html.replace("{{VC_NAME}}", investor["name"])
    html = html.replace("{{PORTFOLIO_NOTE}}", investor["portfolio_note"])
    return html


def subject_kr(vc_name: str) -> str:
    return f"[IR 제안] MyMiniMe Studio — 월 400+ 고객, 3D 디지털 자산 스튜디오 투자 검토 요청"


def subject_en(vc_name: str) -> str:
    return f"[Investment Inquiry] MyMiniMe Studio — 400+ monthly customers, Korea's 3D digital asset studio"


def send_email(run_id: str, investor: dict, html: str, subject: str, dry_run: bool) -> bool:
    payload = {
        "from": FROM_EMAIL,
        "to": [investor["email"]],
        "subject": subject,
        "html": html,
        "tags": [
            {"name": "run_id", "value": run_id},
            {"name": "priority", "value": str(investor["priority"])},
        ],
    }

    if dry_run:
        log(run_id, "DRY_RUN", to=investor["email"], name=investor["name"], subject=subject)
        return True

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        RESEND_API,
        data=body,
        headers={
            "Authorization": f"Bearer {RESEND_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    delay = 1.0
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                log(run_id, "SUCCESS", to=investor["email"], name=investor["name"],
                    resend_id=result.get("id"))
                return True
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")
            log(run_id, "ERROR", error_type=f"HTTP_{e.code}",
                to=investor["email"], name=investor["name"],
                detail=body_err, attempt=attempt + 1)
            if e.code in (422, 403):
                return False
        except Exception as e:
            log(run_id, "ERROR", error_type=type(e).__name__,
                to=investor["email"], name=investor["name"],
                detail=str(e), attempt=attempt + 1)

        time.sleep(delay)
        delay = min(delay * 2, 30)

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry_run", action="store_true", help="미리보기만, 실제 발송 안 함")
    parser.add_argument("--run_id", default=None, help="고유 실행 ID (없으면 자동 생성)")
    parser.add_argument("--priority", type=int, default=None, help="최소 우선순위 (3=⭐⭐⭐만, 2=전체)")
    args = parser.parse_args()

    run_id = args.run_id or f"ir-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    investors_path = SCRIPT_DIR / "investors.json"
    investors = json.loads(investors_path.read_text(encoding="utf-8"))

    if args.priority:
        investors = [i for i in investors if i["priority"] >= args.priority]

    template_kr = load_template("kr")
    template_en = load_template("en")

    log(run_id, "START", total=len(investors), dry_run=args.dry_run,
        priority_filter=args.priority)

    ok, fail = 0, 0
    for i, investor in enumerate(investors):
        html    = build_html(investor, template_kr, template_en)
        subject = subject_kr(investor["name"]) if investor["type"] == "kr" else subject_en(investor["name"])

        success = send_email(run_id, investor, html, subject, args.dry_run)
        if success:
            ok += 1
        else:
            fail += 1

        # 발송 간격 2초 (스팸 방지)
        if not args.dry_run and i < len(investors) - 1:
            time.sleep(2)

    log(run_id, "DONE", total=len(investors), ok=ok, fail=fail)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
