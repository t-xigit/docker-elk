import requests
import os
import subprocess
from pathlib import Path
import jinja2
import json
from typing import Union
from .utils import assert_is_file


agent_policy_name = 'ci agent policy 1'
kibana_url = 'http://localhost:5601'
agent_compose_template = Path('./loggy_deployment/config/templates/agent/agent-compose.yml')



def ping_elasticsearch(url: str, ca: Path) -> dict:
    """Queries the Elasticsearch API to check if it is up and running."""
    # Cast the Path object to a string
    _ca = str(ca)
    response = requests.get(url, auth=('elastic', 'changeme'), verify=_ca)
    resp_dict = json.loads(response.text)
    return resp_dict


def get_agent_policy_id(name: str, url: str) -> str:
    """Gets the agent policy id"""
    response = requests.get(url + '/api/fleet/agent_policies',
                            auth=('elastic', 'changeme'))
    for policy in response.json()['items']:
        if policy['name'] == name:
            print(policy['id'])
    return policy['id']


def create_agent_policy(name: str, description: str, url: str):
    """Creates an agent policy in Elasticsearch"""
    payload = {
        "name": name,
        "description": description,
        "monitoring_enabled": [
          "logs",
          "metrics"
        ],
        "namespace": "default",
    }
    Headers = {"kbn-xsrf": "true", "Content-Type": "application/json"}
    print("starting to create agent policy")
    response = requests.post(url + '/api/fleet/agent_policies',
                             auth=('elastic', 'changeme'), json=payload,
                             headers=Headers)
    if response.status_code == 409:
        print("Agent policy already exists")
    print(response.json())


def get_enrollment_token(url: str, policy_id: str) -> Union[str, None]:
    """Gets the enrollment token"""
    Headers = {"kbn-xsrf": "xx", "Content-Type": "application/json"}
    api = url + '/api/fleet/enrollment_api_keys'
    response = requests.get(api, headers=Headers,
                            auth=('elastic', 'changeme'))
    print(response.json())
    print(response.status_code)
    if response.status_code == 200:
        for r in response.json()['list']:
            # Find the enrollment token for the agent policy
            if r['policy_id'] == policy_id:
                print(r['api_key'])
        return r['api_key']
    else:
        print("No enrollment token found")
        return None


def render_agent_compose(template_file: Path, deployment_file: Path, context: dict) -> str:
    """Loads a Jinja template and returns the rendered template."""
    if not os.path.isfile(template_file):
        raise FileNotFoundError(f"File {template_file} does not exist")
    path = Path(template_file).resolve().parent
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(path))
    template = environment.get_template(os.path.basename(template_file))
    deployment = template.render(context)
    with open(deployment_file, mode='w', encoding="utf-8") as f:
        f.write(deployment)
    return deployment_file


def get_ca_fingerprint(ca_path: Path) -> str:
    """Updates the ca fingerprint in the agent compose file"""
    assert_is_file(ca_path)
    # Create CA Fingerprint
    ca = subprocess.run(['openssl', 'x509', '-noout', '-fingerprint', '-sha256', '-in', ca_path],
                        capture_output=True, encoding='utf-8')
    # Get everything after the = sign
    ca_fingerprint = str(ca.stdout.split('=')[1].strip())
    # Remove the colons
    ca_fingerprint = ca_fingerprint.replace(':', '')
    # Convert to lowercase
    ca_fingerprint = ca_fingerprint.lower()
    return ca_fingerprint


def add_agent(deployment_file: Path):
    create_agent_policy(agent_policy_name, 'first policy', kibana_url)
    policy_id = get_agent_policy_id(agent_policy_name, kibana_url)
    print(policy_id)
    enrollment_token = get_enrollment_token(kibana_url, policy_id)
    print(enrollment_token)
    context = {'FleetEnrollmentToken': enrollment_token,
               'ELKNetworkforAgent': 'loggy_dev_elk'}
    render_agent_compose(agent_compose_template, deployment_file, context)
