NAMESPACE  = sdc
IMAGE_NAME = sdc-agents
IMAGE_TAG  = latest

.PHONY: build deploy pull-model ingest url logs logs-ingest logs-ollama status clean help

## ── Build ─────────────────────────────────────────────────────────────────

build:  ## Build the Docker image inside minikube's daemon
	eval $$(minikube docker-env) && docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

## ── Deploy ────────────────────────────────────────────────────────────────

deploy:  ## Apply all K8s manifests in dependency order
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/secret.yaml
	kubectl apply -f k8s/ollama/
	kubectl apply -f k8s/chromadb/
	kubectl apply -f k8s/redis/
	kubectl apply -f k8s/sdc-agents/
	@echo ""
	@echo "Waiting for core pods to be Ready..."
	kubectl wait --for=condition=ready pod -l app=ollama    -n $(NAMESPACE) --timeout=120s
	kubectl wait --for=condition=ready pod -l app=chromadb  -n $(NAMESPACE) --timeout=60s
	kubectl wait --for=condition=ready pod -l app=redis     -n $(NAMESPACE) --timeout=30s
	@echo ""
	@echo "Infrastructure ready. Run 'make pull-model' next (first deploy only)."

## ── One-off jobs ──────────────────────────────────────────────────────────

pull-model:  ## Pull llama3.2 into the Ollama pod (~2 GB, run once)
	kubectl delete job ollama-pull -n $(NAMESPACE) --ignore-not-found
	kubectl apply  -f k8s/jobs/ollama-pull.yaml
	@echo "Waiting for model pull to complete (up to 10 min)..."
	kubectl wait --for=condition=complete job/ollama-pull -n $(NAMESPACE) --timeout=600s
	@echo "Model pull complete. Run 'make ingest' next."

ingest:  ## Populate ChromaDB with runbooks + records (run after pull-model)
	kubectl delete job sdc-ingest -n $(NAMESPACE) --ignore-not-found
	kubectl apply  -f k8s/jobs/ingest.yaml
	@echo "Waiting for ingestion to complete..."
	kubectl wait --for=condition=complete job/sdc-ingest -n $(NAMESPACE) --timeout=300s
	@echo "Ingestion complete. Run 'make url' to get the app URL."

## ── Observe ───────────────────────────────────────────────────────────────

url:  ## Print the NodePort URL for the sdc-agents service
	@minikube service sdc-agents -n $(NAMESPACE) --url

status:  ## Show pod status across the namespace
	kubectl get pods -n $(NAMESPACE) -o wide

logs:  ## Tail sdc-agents logs
	kubectl logs -l app=sdc-agents -n $(NAMESPACE) -f --tail=100

logs-ingest:  ## Tail the ingest job logs
	kubectl logs -l job-name=sdc-ingest -n $(NAMESPACE) --tail=200

logs-ollama:  ## Tail the ollama pod logs
	kubectl logs -l app=ollama -n $(NAMESPACE) -f --tail=50

## ── Teardown ──────────────────────────────────────────────────────────────

clean:  ## Delete the entire sdc namespace (keeps minikube running)
	kubectl delete namespace $(NAMESPACE) --ignore-not-found

## ── Help ──────────────────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
