import json
import subprocess
import sys
import unittest


class TestLazyProcessingDependencies(unittest.TestCase):
    def test_read_only_operations_import_does_not_load_ocr_or_ml_stacks(self):
        script = """
import json
import sys
import src.operations.local_api
print(json.dumps({
    'numpy': 'numpy' in sys.modules,
    'sklearn': 'sklearn' in sys.modules,
    'scipy': 'scipy' in sys.modules,
    'pandas': 'pandas' in sys.modules,
    'cv2': 'cv2' in sys.modules,
    'googleapiclient': 'googleapiclient' in sys.modules,
    'processor_pipeline': 'src.document_processors.processor_pipeline' in sys.modules,
}, sort_keys=True))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "cv2": False,
                "googleapiclient": False,
                "numpy": False,
                "pandas": False,
                "processor_pipeline": False,
                "scipy": False,
                "sklearn": False,
            },
        )

    def test_worker_import_does_not_load_disabled_provider_or_ocr_stacks(self):
        script = """
import json
import sys
import src.run_worker
print(json.dumps({
    'numpy': 'numpy' in sys.modules,
    'pandas': 'pandas' in sys.modules,
    'cv2': 'cv2' in sys.modules,
    'pytesseract': 'pytesseract' in sys.modules,
    'googleapiclient': 'googleapiclient' in sys.modules,
    'workflow_controller': 'src.workflow.controller' in sys.modules,
    'connector_intake': 'src.operations.local_connector_intake' in sys.modules,
}, sort_keys=True))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "connector_intake": False,
                "cv2": False,
                "googleapiclient": False,
                "numpy": False,
                "pandas": False,
                "pytesseract": False,
                "workflow_controller": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
