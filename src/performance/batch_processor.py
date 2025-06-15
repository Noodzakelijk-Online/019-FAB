from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

class BatchProcessor:
    """Processes items in batches using a thread pool for concurrency."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_workers = self.config.get("batch_processor_max_workers", os.cpu_count() or 4)

    def process_batch(self, items: List[Any], processing_function: Callable, *args, **kwargs) -> List[Any]:
        """Processes a list of items concurrently.

        Args:
            items: A list of items to be processed.
            processing_function: The function to apply to each item.
            *args, **kwargs: Additional arguments to pass to the processing_function.

        Returns:
            A list of results from processing each item.
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks to the executor
            future_to_item = {executor.submit(processing_function, item, *args, **kwargs): item for item in items}
            
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    print(f"Item {item} generated an exception: {exc}")
                    results.append({"item": item, "status": "failed", "error": str(exc)})
        return results


