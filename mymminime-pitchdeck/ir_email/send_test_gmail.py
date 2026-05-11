#!/usr/bin/env python3
"""
IR 이메일 테스트 발송 — Gmail API 사용 (nadalgw@gmail.com)
Usage: python send_test_gmail.py --to nadalgw@gmail.com --lang kr
"""
import argparse
import base64
import sys
from email.utils import formatdate, make_msgid
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GMAIL_EXEC = Path("/Users/andy/Antigravity/2026/2월/자동 마케팅 이메일 발송/execution")
sys.path.insert(0, str(GMAIL_EXEC))

from auth_test import authenticate_google
from googleapiclient.discovery import build


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default="nadalgw@gmail.com")
    parser.add_argument("--lang", choices=["kr", "en"], default="kr")
    args = parser.parse_args()

    template = (SCRIPT_DIR / f"template_{args.lang}.html").read_text(encoding="utf-8")
    html = template.replace("{{VC_NAME}}", "[테스트]")
    html = html.replace("{{PORTFOLIO_NOTE}}", "마이미니미 스튜디오 IR 이메일 테스트 발송입니다")

    if args.lang == "kr":
        subject = "[IR 제안] MyMiniMe Studio — 월 400+ 고객, 3D 디지털 자산 스튜디오 투자 검토 요청"
    else:
        subject = "[Investment Inquiry] MyMiniMe Studio — 400+ monthly customers, Korea's 3D digital asset studio"

    import os
    os.chdir(GMAIL_EXEC)
    creds = authenticate_google()
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    sender = f"MyMiniMe Studio <{profile['emailAddress']}>"

    raw = build_raw(sender, args.to, subject, html)
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✅ 발송 완료 — Message ID: {result['id']}")
    print(f"   수신: {args.to} | 언어: {args.lang}")


if __name__ == "__main__":
    main()
