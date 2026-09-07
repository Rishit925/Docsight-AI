import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()


class SupabaseStorage:
    """
    Minimal Supabase Storage client using the HTTP API.

    The bucket is private and accessed using the
    Supabase service-role key from environment variables.
    """

    def __init__(self):
        self.base_url = os.getenv("SUPABASE_URL")
        self.service_role_key = os.getenv(
            "SUPABASE_SERVICE_ROLE_KEY"
        )
        self.bucket = os.getenv(
            "SUPABASE_STORAGE_BUCKET",
            "documents",
        )

        if not self.base_url:
            raise ValueError(
                "SUPABASE_URL is not set."
            )

        if not self.service_role_key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY is not set."
            )

        self.base_url = self.base_url.rstrip("/")

    # ==================================================
    # HELPERS
    # ==================================================

    def _object_url(self, storage_path):
        encoded_path = quote(
            str(storage_path),
            safe="/",
        )

        return (
            f"{self.base_url}/storage/v1/object/"
            f"{self.bucket}/{encoded_path}"
        )

    def _headers(self):
        return {
            "Authorization": (
                f"Bearer {self.service_role_key}"
            ),
            "apikey": self.service_role_key,
        }

    # ==================================================
    # UPLOAD
    # ==================================================

    def upload_file(
        self,
        local_path,
        storage_path,
        content_type="application/octet-stream",
    ):
        """
        Upload a local file to Supabase Storage.
        """

        local_path = Path(local_path)

        if not local_path.exists():
            raise FileNotFoundError(
                f"Local file not found: {local_path}"
            )

        with local_path.open("rb") as file:
            data = file.read()

        headers = self._headers()
        headers.update(
            {
                "Content-Type": content_type,
                "x-upsert": "true",
            }
        )

        request = Request(
            self._object_url(storage_path),
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request) as response:
                return response.status in {
                    200,
                    201,
                }

        except HTTPError as error:
            body = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "Supabase Storage upload failed: "
                f"HTTP {error.code} - {body}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                "Supabase Storage upload failed: "
                f"{error}"
            ) from error

    # ==================================================
    # DOWNLOAD
    # ==================================================

    def download_file(
        self,
        storage_path,
        local_path,
    ):
        """
        Download a file from Supabase Storage.
        """

        local_path = Path(local_path)

        local_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        request = Request(
            self._object_url(storage_path),
            headers=self._headers(),
            method="GET",
        )

        try:
            with urlopen(request) as response:
                data = response.read()

            local_path.write_bytes(data)

            return str(local_path)

        except HTTPError as error:
            body = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "Supabase Storage download failed: "
                f"HTTP {error.code} - {body}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                "Supabase Storage download failed: "
                f"{error}"
            ) from error

    # ==================================================
    # DELETE FILE
    # ==================================================

    def delete_file(self, storage_path):
        """
        Delete a single file from Supabase Storage.
        """

        request = Request(
            self._object_url(storage_path),
            headers=self._headers(),
            method="DELETE",
        )

        try:
            with urlopen(request) as response:
                return response.status in {
                    200,
                    204,
                }

        except HTTPError as error:
            body = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "Supabase Storage delete failed: "
                f"HTTP {error.code} - {body}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                "Supabase Storage delete failed: "
                f"{error}"
            ) from error

    # ==================================================
    # DELETE FOLDER
    # ==================================================

    def delete_folder(self, prefix):
        """
        Delete all objects under a storage prefix.

        Supabase Storage bulk deletion uses:

            DELETE /storage/v1/object/{bucket}

        with:

            {
                "prefixes": [...]
            }
        """

        url = (
            f"{self.base_url}/storage/v1/object/"
            f"{self.bucket}"
        )

        data = json.dumps(
            {
                "prefixes": [prefix],
            }
        ).encode("utf-8")

        headers = self._headers()
        headers.update(
            {
                "Content-Type": "application/json",
            }
        )

        request = Request(
            url,
            data=data,
            headers=headers,
            method="DELETE",
        )

        try:
            with urlopen(request) as response:
                return response.status in {
                    200,
                    204,
                }

        except HTTPError as error:
            body = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "Supabase Storage folder delete failed: "
                f"HTTP {error.code} - {body}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                "Supabase Storage folder delete failed: "
                f"{error}"
            ) from error