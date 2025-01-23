# General integration tests design
* GitHub actions run GKE cli command that starts a new pod with `test_env/Dockerfile` image
* container clones repo into itself
* container runs `tests.py` script

## Running locally
```bash
docker build --tag irio_alerting
```
And then
```bash
docker run 'irio_alerting'
```