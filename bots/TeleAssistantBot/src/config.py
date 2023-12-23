import yaml
import dotenv
from pathlib import Path

config_dir = Path(__file__).parent.parent.resolve() / "config"

# load .env config
config_env = dotenv.dotenv_values(config_dir / "config.env")
mongodb_uri = f"mongodb://{config_env['MONGODB_HOST']}:{config_env['MONGODB_PORT']}"

# load yaml config
with open(config_dir / "config.yml", 'r') as f:
    config_yaml = yaml.safe_load(f)
    
telegram_token = config_yaml['telegram_token']
openai_api_key = config_yaml['openai_api_key']

allowed_user_ids = config_yaml['allowed_user_ids']
system_admin_ids = config_yaml['system_admin_ids']

max_interactions = config_yaml['max_interactions']
max_file_count_per_thread = config_yaml['max_file_count_per_thread']
idle_timeout = config_yaml['idle_timeout']
temperature = config_yaml['temperature']

# load assistant.yml
with open(config_dir / "assistant.yml", 'r') as f:
    assistant_yaml = yaml.safe_load(f)
    
assistant = assistant_yaml['assistant']