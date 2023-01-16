# Loggy Elastic stack (ELK) on Docker

---

## Enroll an Elastic Agent

Create an agent policy in Kibana and enroll an Elastic Agent.
Copy the enrollment token and add it to to the agent-compose.yml, then run the following command:  
`docker-compose --env-file .env -f extensions/agent/agent-compose.yml up`

## Deployment strategies for Loggy

### Data to be considered

configuration.yml files need to be adapted for configurations.
Data within the configuration files:

- URLs/Hostnames
- Tokens
- Flags
- Ports in case of running instances on the same host
- Certificates for the deployment

Managing of configuration files:
Create config templates and use a configuration management tool to deploy the configuration files.
Create the files can be done with ansible or python scripts.

Decide to use Python because of the following reasons:
Since it is more flexible it can also be used to create index and ingest pipelines.
Next steps:

- [ ] Add jinja2 to the tech stack
- [ ] Create a python script to create the configuration files
- [ ] Update the agent-compose.yml to use the configuration files
- [ ] Add python scripts to create the agent policy and enrollment token
- [ ] Add make target for the agent-compose.yml

---
