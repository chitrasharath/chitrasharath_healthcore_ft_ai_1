# ✅ What We Will Evaluate

- [ ] Redis runs in Docker and workers connect to it without configuration errors.
- [ ] The modified endpoint returns `202 Accepted` with `task_id` in under 200ms, regardless of the task duration.
- [ ] `GET /tasks/{task_id}` returns the correct status at each phase of the task lifecycle.
- [ ] Automatic retries are configured with backoff: no immediate retry after a failure.
- [ ] After three consecutive failures, the task appears in the DLQ with `task_id`, attempt number, and error message recorded in the database.
- [ ] The worker is a separate process: stopping the API does not stop the worker or lose queued messages.
- [ ] Messages in the queue contain only identifiers or references — no large data payloads.
- [ ] Flower is running and shows at least one completed task and one failed task during the demonstration.
