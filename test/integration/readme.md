# General integration tests design
* GitHub actions run GKE cli command that starts a new pod with `test_env/Dockerfile` image
* container clones repo into itself
* container runs `tests.py` script

## Running locally
```bash
docker build -f Dockerfile_integration -t irio_test:latest . --build-arg SMTP_USERNAME="alertingplatformirio@localhost"  --build-arg SMTP_SERVER="localhost" --build-arg SMTP_PORT="1025"
```
Create directory 'logs'
And then
```bash
docker run 'irio_alerting' --vm logs:/app/logs
```
NOTE: in my local env tests are failing due to the `setup_logging()` function being stuck. temp workaround: add `assert False` after `try:` line in that function