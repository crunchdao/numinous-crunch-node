# numinous crunch node

Numious Subnet on Crunch.

# Running Locally

To run the project locally, run this command:
```bash
make dev build deploy logs
```

This command will:
- `dev`: enable the `.local.dev`
- `build`: build the containers
- `deploy`: run the containers
- `logs`: attach the containers logs so that you can perform a Ctrl+C without killing them.

## Configuration

To configure the local deployment, you only need to amend a few properties in the `.local.dev` file:
- `NUMINOUS_ENV`: can either be `prod` ou `test`
- `NUMINOUS_API_KEY`: Numious' API Key to fetch the events
- `OPENAI_API_KEY`: OpenAI's API Key used to score the reasoning of a prediction

## Dummy model

A dummy model has been configured for use in the `deployment/model-orchestrator-local/data/submissions/numinous-benchmarktracker` directory.

In order for the modifications to be taken into account, you will need to restart the Model Orchestrator. The new version of the model will then be built.

```bash
make dev restart SERVICES=model-orchestrator
```
