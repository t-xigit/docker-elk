# Loggy Elastic stack (ELK) on Docker

---

## Enroll an Elastic Agent

Create an agent policy in Kibana and enroll an Elastic Agent.
Copy the enrollment token and add it to to the agent-compose.yml, then run the following command:  
`docker-compose --env-file .env -f extensions/agent/agent-compose.yml up`

---
