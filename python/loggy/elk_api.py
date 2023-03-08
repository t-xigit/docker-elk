import requests
import os
from pathlib import Path
import jinja2
import json
from typing import Union

cert_path = './tls/certs/ca/ca.crt'
cert_path = '/workspaces/docker-elk/loggy_deployment/deployments/loggy_dev/tls/certs/ca/ca.crt'
agent_policy_name = 'ci agent policy 1'
kibana_url = 'http://localhost:5601'
agent_compose_template = './extensions/agent/agent-compose.yml'


def ping_elasticsearch(url: str, ca: Path) -> dict:
    """Queries the Elasticsearch API to check if it is up and running."""
    # Cast the Path object to a string
    _ca = str(ca)
    response = requests.get(url, auth=('elastic', 'changeme'), verify=_ca)
    resp_dict = json.loads(response.text)
    return resp_dict


def check_certificate(path: str) -> bool:
    """Checks if the certificate is created """
    if os.path.isfile(cert_path):
        print("Certificate exists")
        return True
    else:
        print("Certificate does not exist")
        return False


def check_elasticsearch_status(url: str, ca: Path):
    """Checks the Elasticsearch status"""
    response = ping_elasticsearch(url, ca)
    if isinstance(response, dict):
        if response['tagline'] == 'You Know, for Search':
            print("Elasticsearch is up and running")
        else:
            print("Elasticsearch is not running")


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


def render_agent_compose(template_file: str, context: dict) -> str:
    """Loads a Jinja template and returns the rendered template."""
    if not os.path.isfile(template_file):
        raise FileNotFoundError(f"File {template_file} does not exist")
    path = os.path.dirname(template_file)
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(path))
    template = environment.get_template(os.path.basename(template_file))

    deployment = template.render(FleetEnrollmentToken=context['enrollment_token'])
    deployment_file = os.path.join(path, 'agent-compose-deploy.yml')
    with open(deployment_file, mode='w', encoding="utf-8") as f:
        f.write(deployment)
    return deployment_file


# check_elasticsearch_status('https://localhost:9200', cert_path)
# check_certificate(cert_path)
# create_agent_policy(agent_policy_name, 'first policy', kibana_url)
# policy_id = get_agent_policy_id(agent_policy_name, kibana_url)
# print(policy_id)
# enrollment_token = get_enrollment_token(kibana_url, policy_id)
# print(enrollment_token)
#
# render_agent_compose(agent_compose_template, {'enrollment_token': enrollment_token})
