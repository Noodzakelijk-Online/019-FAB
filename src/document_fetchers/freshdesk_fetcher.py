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
        query_params = self.config.get("freshdesk_query_params", {})
        attachments_dir = self.config.get("attachments_save_dir", "/tmp/freshdesk_attachments")
        os.makedirs(attachments_dir, exist_ok=True)

        documents = []
        try:
            # Fetch tickets first
            tickets_url = f"{self.base_url}tickets"
            response = requests.get(tickets_url, auth=self.auth, params=query_params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            tickets = response.json()

            for ticket in tickets:
                ticket_id = ticket["id"]
                # Fetch conversations (replies) for each ticket to get attachments
                conversations_url = f"{self.base_url}tickets/{ticket_id}/conversations"
                conv_response = requests.get(conversations_url, auth=self.auth)
                conv_response.raise_for_status()
                conversations = conv_response.json()

                for conversation in conversations:
                    if "attachments" in conversation:
                        for attachment in conversation["attachments"]:
                            attachment_url = attachment["attachment_url"]
                            file_name = attachment["name"]
                            
                            # Download attachment
                            attachment_content = requests.get(attachment_url, auth=self.auth).content
                            local_path = os.path.join(attachments_dir, file_name)
                            
                            with open(local_path, "wb") as f:
                                f.write(attachment_content)
                            
                            documents.append({
                                "id": f"freshdesk_{ticket_id}_{attachment["id"]}",
                                "source": "freshdesk",
                                "original_filename": file_name,
                                "local_path": local_path,
                                "timestamp": attachment["created_at"],
                                "metadata": {
                                    "ticket_id": ticket_id,
                                    "conversation_id": conversation["id"],
                                    "attachment_id": attachment["id"]
                                }
                            })
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching from Freshdesk: {e}")
        return documents


