from src.config_loader import ConfigLoader
from src.dashboard.app import create_app


if __name__ == "__main__":
    config = ConfigLoader(config_file="config/config.ini").get_all_config()
    app_config = config.get("app", {})
    dashboard_config = config.get("dashboard", {})
    merged_config = {**app_config, **dashboard_config, **config.get("database", {})}

    host = dashboard_config.get("host", "127.0.0.1")
    port = int(dashboard_config.get("port", 5001))
    app = create_app(merged_config)
    app.run(host=host, port=port)
