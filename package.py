import os
import shutil
import zipfile
import datetime

class PackageBuilder:
    """Builds deployable packages for the automated bookkeeping solution."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.dist_dir = os.path.join(self.base_dir, "dist")
        os.makedirs(self.dist_dir, exist_ok=True)

    def build_local_package(self, output_name: str = "automated_bookkeeping_local") -> str:
        """Builds a zip package for local deployment."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{output_name}_{timestamp}.zip"
        zip_filepath = os.path.join(self.dist_dir, zip_filename)

        files_to_include = [
            "src",
            "config",
            "requirements.txt",
            "Dockerfile",
            "README.md",
            "docs",
            "tests",
            "src/main.py",
            "src/cloud_functions.py",
            "package.py"
        ]

        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in files_to_include:
                item_path = os.path.join(self.base_dir, item)
                if os.path.exists(item_path):
                    if os.path.isfile(item_path):
                        zipf.write(item_path, os.path.basename(item_path))
                    elif os.path.isdir(item_path):
                        for root, _, files in os.walk(item_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, self.base_dir) # Relative path in zip
                                zipf.write(file_path, arcname)
                else:
                    print(f"Warning: {item_path} not found, skipping.")

        print(f"Local package built successfully: {zip_filepath}")
        return zip_filepath

    def build_cloud_package(self, output_name: str = "automated_bookkeeping_cloud") -> str:
        """Builds a zip package suitable for cloud deployment (e.g., Google Cloud Functions)."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{output_name}_{timestamp}.zip"
        zip_filepath = os.path.join(self.dist_dir, zip_filename)

        # For cloud functions, we typically only need the source code and requirements
        files_to_include = [
            "src",
            "config",
            "requirements.txt",
            "src/main.py", # If main.py is the entry point
            "src/cloud_functions.py" # If cloud_functions.py is the entry point
        ]

        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in files_to_include:
                item_path = os.path.join(self.base_dir, item)
                if os.path.exists(item_path):
                    if os.path.isfile(item_path):
                        zipf.write(item_path, os.path.basename(item_path))
                    elif os.path.isdir(item_path):
                        for root, _, files in os.walk(item_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, self.base_dir) # Relative path in zip
                                zipf.write(file_path, arcname)
                else:
                    print(f"Warning: {item_path} not found, skipping.")

        print(f"Cloud package built successfully: {zip_filepath}")
        return zip_filepath

if __name__ == "__main__":
    builder = PackageBuilder(base_dir=os.path.dirname(os.path.abspath(__file__)))
    # Example usage:
    local_package_path = builder.build_local_package()
    cloud_package_path = builder.build_cloud_package()


