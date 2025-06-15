from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseDataEntryHandler(ABC):
    """Abstract base class for all data entry handlers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def enter_data(self, categorized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enters the categorized document data into the target system.

        Args:
            categorized_data: A dictionary containing the categorized document data.

        Returns:
            A dictionary indicating the success/failure status and any relevant messages.
        """
        pass


