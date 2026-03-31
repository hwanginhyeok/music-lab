"""
Google Drive 업로더 — WAV/MP3 파일 업로드 + 공유 링크 생성

Google Drive API v3 사용. 서비스 계정 인증.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("music-lab")


class DriveError(Exception):
    """Drive 관련 에러."""


class DriveUploader:
    """Google Drive 파일 업로더."""

    def __init__(
        self,
        credentials_path: str | None = None,
        folder_id: str | None = None,
    ):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        self._service = None

    def _get_service(self):
        """Google Drive API 서비스 lazy init."""
        if self._service is None:
            if not self.credentials_path:
                raise DriveError("GOOGLE_CREDENTIALS_PATH 환경변수가 설정되지 않았습니다")
            if not Path(self.credentials_path).exists():
                raise DriveError(f"인증 파일이 없습니다: {self.credentials_path}")

            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/drive.file"],
            )
            self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def upload(self, local_path: str, filename: str | None = None) -> str:
        """파일 업로드 → 공유 링크 반환."""
        path = Path(local_path)
        if not path.exists():
            raise DriveError(f"파일이 없습니다: {local_path}")

        name = filename or path.name
        mime = "audio/mpeg" if path.suffix == ".mp3" else "audio/wav"

        from googleapiclient.http import MediaFileUpload

        service = self._get_service()

        file_metadata: dict = {"name": name}
        if self.folder_id:
            file_metadata["parents"] = [self.folder_id]

        media = MediaFileUpload(
            str(path),
            mimetype=mime,
            resumable=True,
        )

        logger.info("Drive 업로드: %s (%.1fMB)", name, path.stat().st_size / 1024 / 1024)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
        ).execute()

        file_id = file["id"]

        # 링크가 있는 사람은 누구나 볼 수 있게 공유
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        link = file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
        logger.info("Drive 업로드 완료: %s", link)
        return link

    def list_songs(self, limit: int = 20) -> list[dict]:
        """Drive 폴더의 오디오 파일 목록."""
        service = self._get_service()
        query = f"'{self.folder_id}' in parents and trashed=false" if self.folder_id else "trashed=false"
        query += " and (mimeType='audio/mpeg' or mimeType='audio/wav')"

        results = service.files().list(
            q=query,
            fields="files(id, name, webViewLink, size, createdTime)",
            orderBy="createdTime desc",
            pageSize=limit,
        ).execute()

        return [
            {
                "id": f["id"],
                "name": f["name"],
                "link": f.get("webViewLink", ""),
                "size_mb": int(f.get("size", 0)) / 1024 / 1024,
                "created": f.get("createdTime", ""),
            }
            for f in results.get("files", [])
        ]
