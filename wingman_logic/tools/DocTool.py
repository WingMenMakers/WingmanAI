import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from typing import List, Dict, Optional, Tuple, Any

# Custom exception for clarity
class DocToolError(Exception):
    """Base exception for DocTool failures."""
    pass

class DocTool:
    def __init__(self, credentials: Credentials):
        """Initialize with a guaranteed valid Credentials object."""
        self.creds = credentials

    def _build_drive_service(self):
        """Helper to build Drive service."""
        return build("drive", "v3", credentials=self.creds)

    def _build_docs_service(self):
        """Helper to build Docs service."""
        return build("docs", "v1", credentials=self.creds)
    
    def get_recent_google_docs(self, limit: int = 10) -> List[Dict[str, str]]:
        """Fetch metadata for recent Google Docs."""
        service = self._build_drive_service()
        try:
            query = "mimeType='application/vnd.google-apps.document'"
            results = service.files().list(
                q=query,
                orderBy="viewedByMeTime desc",
                pageSize=limit,
                fields="files(id, name, viewedByMeTime)"
            ).execute()
            
            return results.get("files", [])

        except HttpError as error:
            logging.error(f"Google Drive API error: {error}")
            raise DocToolError(f"Drive API error fetching recent files: {error.content}")
    
    def resolve_file_name_to_id(self, file_name: str) -> Optional[str]:
        """
        Resolves a file name to its ID. 
        Returns file ID (str) or None if not found.
        """
        service = self._build_drive_service()
        try:
            # Query for exact name match
            query = f"name = '{file_name}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
            results = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1
            ).execute()
            
            files = results.get("files", [])
            
            if not files:
                # 🎯 CRITICAL FIX: Return None for 'not found'
                return None 

            return files[0]["id"]

        except HttpError as error:
            logging.error(f"Failed to resolve file name: {error}")
            raise DocToolError(f"Drive API error resolving name: {error.content}")
                
    def create_google_doc(self, title: str = "New Document", initial_content: Optional[str] = None) -> Dict[str, str]:
        """Creates a new Google Doc. Returns Dict with id and link."""
        service = self._build_docs_service()
        try:
            document = service.documents().create(body={"title": title}).execute()
            doc_id = document.get("documentId")
            doc_link = f"https://docs.google.com/document/d/{doc_id}"

            if initial_content and doc_id:
                # Use a cleaner way to insert content at the beginning
                requests = [{
                    "insertText": {
                        "location": {"index": 1},
                        "text": f"{initial_content}\n\n"
                    }
                }]
                self._build_docs_service().documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()

            # 🎯 CRITICAL FIX: Return structured Dict
            return {"id": doc_id, "link": doc_link, "title": title}

        except Exception as e:
            logging.error(f"Failed to create document: {e}")
            raise DocToolError(f"Docs API error creating file: {e}")
        
    def get_google_doc_content(self, doc_id: str) -> str:
        """Retrieves and extracts plain text content from a Google Doc."""
        service = self._build_docs_service()
        try:
            doc = service.documents().get(documentId=doc_id).execute()
            content = doc.get("body", {}).get("content", [])

            text = ""
            for element in content:
                if "paragraph" in element:
                    for part in element["paragraph"].get("elements", []):
                        if "textRun" in part:
                            # Added content newline handling for structure
                            text += part["textRun"].get("content", "")

            # Removing excessive whitespace/newlines from the end
            return text.strip()

        except Exception as e:
            logging.error(f"Failed to retrieve document content for ID {doc_id}: {e}")
            # 🎯 CRITICAL FIX: Raise on failure
            raise DocToolError(f"Docs API error retrieving content: {e}")

    def add_to_google_doc(self, doc_id: str, text: str, location: str = "end") -> bool:
        """Appends text to the end of a Google Doc."""
        service = self._build_docs_service()
        try:
            if location == "end":
                # Get the last index of the document body
                doc = service.documents().get(documentId=doc_id, fields="body.content(endIndex)").execute()
                # The final element in content array contains the document length
                end_index = doc.get("body", {}).get("content", [])[-1]["endIndex"] - 1
            else: # Defaults to beginning
                end_index = 1 

            requests = [{
                "insertText": {
                    "location": {"index": end_index},
                    "text": f"\n{text}\n" # Add newlines for separation
                }
            }]

            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()
            
            # 🎯 CRITICAL FIX: Return True on success
            return True

        except Exception as e:
            logging.error(f"Failed to add content to document {doc_id}: {e}")
            raise DocToolError(f"Docs API error appending text: {e}")

    def delete_google_doc(self, doc_id: str) -> bool:
        """Deletes a Google Doc via the Drive API."""
        service = self._build_drive_service()
        try:
            service.files().delete(fileId=doc_id).execute()
            # 🎯 CRITICAL FIX: Return True on success
            return True
        except HttpError as error:
            logging.error(f"Failed to delete document {doc_id}: {error}")
            raise DocToolError(f"Drive API error deleting file: {error.content}")

    def edit_google_doc(self, doc_id: str, text: str) -> bool:
        """Completely replaces the content of a Google Doc with the given text."""
        service = self._build_docs_service()
        try:
            # 1. Get current document length to determine delete range
            doc = service.documents().get(documentId=doc_id, fields="body.content(endIndex)").execute()
            end_index = doc['body']['content'][-1]['endIndex']

            requests = [
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": 1,
                            "endIndex": end_index - 1 # Delete everything except index 0 (which is the document root)
                        }
                    }
                },
                {
                    "insertText": {
                        "location": {"index": 1}, # Start insertion right after the document root
                        "text": text
                    }
                }
            ]

            service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
            
            # 🎯 CRITICAL FIX: Return True on success
            return True
            
        except Exception as e:
            logging.error(f"Failed to replace content in document {doc_id}: {e}")
            raise DocToolError(f"Docs API error replacing content: {e}")
