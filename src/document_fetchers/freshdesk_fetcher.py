import requests
from typing import List, Dict, Any
import os

from src.document_fetchers.base import BaseFetcher

class FreshdeskFetcher(BaseFetcher):
    """Fetches documents (attachments) from Freshdesk based on specified criteria."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.config.get("freshdesk_api_key")
        self.domain = self.config.get("freshdesk_domain")
        self.base_url = f"https://{self.domain}.freshdesk.com/api/v2/"
        self._authenticate()

    def _authenticate(self):
        if not self.api_key or not self.domain:
            raise ValueError("Freshdesk API key or domain not configured.")
        # Freshdesk API uses Basic Authentication with API key as username and password as 'X'
        self.auth = (self.api_key, "X")

    def fetch_documents(self) -> List[Dict[str, Any]]:
        self._start_run()
        configured_params = self.config.get("freshdesk_query_params", {})
        query_params = dict(configured_params) if isinstance(configured_params, dict) else {}
        attachments_dir = self.config.get("freshdesk_download_dir") or self.config.get("attachments_save_dir", "/tmp/freshdesk_attachments")
        os.makedirs(attachments_dir, exist_ok=True)
        max_pages = _bounded_int(self.config.get("freshdesk_max_pages"), 50, 1, 500)
        per_page = _bounded_int(self.config.get("freshdesk_page_size"), 100, 1, 100)
        timeout = self._request_timeout()

        documents = []
        skipped = 0
        pages = 0
        try:
            tickets_url = f"{self.base_url}tickets"
            tickets = []
            for page in range(1, max_pages + 1):
                response = requests.get(
                    tickets_url,
                    auth=self.auth,
                    params={**query_params, "page": page, "per_page": per_page},
                    timeout=timeout,
                )
                response.raise_for_status()
                payload = response.json()
                page_tickets = payload.get("tickets", payload) if isinstance(payload, dict) else payload
                page_tickets = page_tickets if isinstance(page_tickets, list) else []
                pages += 1
                tickets.extend(page_tickets)
                if len(page_tickets) < per_page:
                    break

            for ticket in tickets:
                ticket_id = ticket["id"]
                conversations = [ticket] if ticket.get("attachments") else []
                conversations_url = f"{self.base_url}tickets/{ticket_id}/conversations"
                conv_response = requests.get(
                    conversations_url,
                    auth=self.auth,
                    timeout=timeout,
                )
                conv_response.raise_for_status()
                conversation_payload = conv_response.json()
                if isinstance(conversation_payload, list):
                    conversations.extend(conversation_payload)

                seen_attachments = set()
                for conversation in conversations:
                    if isinstance(conversation, dict) and "attachments" in conversation:
                        for attachment in conversation.get("attachments") or []:
                            attachment_url = attachment["attachment_url"]
                            file_name = attachment["name"]
                            attachment_id = attachment["id"]
                            document_id = f"freshdesk_{ticket_id}_{attachment_id}"
                            if document_id in seen_attachments:
                                skipped += 1
                                continue
                            seen_attachments.add(document_id)
                            attachment_response = requests.get(
                                attachment_url,
                                auth=self.auth,
                                timeout=timeout,
                            )
                            attachment_response.raise_for_status()
                            attachment_content = attachment_response.content
                            local_path = self._content_download_path(
                                attachments_dir,
                                file_name,
                                document_id,
                                attachment_content,
                            )

                            with open(local_path, "wb") as f:
                                f.write(attachment_content)

                            documents.append({
                                "id": document_id,
                                "source": "freshdesk",
                                "original_filename": file_name,
                                "mime_type": attachment.get("content_type"),
                                "local_path": local_path,
                                "timestamp": attachment.get("created_at", ""),
                                "metadata": {
                                    "ticket_id": ticket_id,
                                    "conversation_id": conversation.get("id"),
                                    "attachment_id": attachment_id,
                                    "attachment_size": attachment.get("size"),
                                }
                            })
            self._finish_run(len(documents), skipped=skipped, pages=pages)
        except Exception as error:
            self._fail_run(error, fetched=len(documents), skipped=skipped, pages=pages)
        return documents


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


