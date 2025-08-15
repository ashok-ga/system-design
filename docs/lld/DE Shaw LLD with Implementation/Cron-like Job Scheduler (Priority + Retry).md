# Cron-like Job Scheduler (Priority + Retry)

We will design an in-process job scheduling system that can execute tasks based on various triggers (like cron expressions or intervals), handle execution priorities, and automatically retry failed jobs with a backoff strategy.

### **1. System Overview & Scope Clarification**

This system acts as a background task manager within a single application process. It's a powerful utility for automating recurring tasks, such as sending daily reports, performing data cleanup, or polling external services.

**Functional Requirements (FR):**

- **Job Scheduling:**
    - Schedule jobs to run at a specific time (one-time).
    - Schedule jobs to run at a fixed interval (e.g., every 5 minutes).
    - Schedule jobs using cron expressions for complex schedules (e.g., "at 2 AM on Mondays").
- **Execution Control:**
    - **Priority:** When multiple jobs are due at the same time, the one with the higher priority executes first.
    - **Retries:** If a job fails (throws an exception), it should be automatically retried according to a configurable policy (e.g., "up to 3 times with exponential backoff").
    - **Pause/Resume:** Allow individual jobs or the entire scheduler to be paused and resumed.

**Non-Functional Requirements (NFR):**

- **Accuracy:** Timers should be reasonably accurate, avoiding significant drift.
- **Durability (Persistence):** The scheduler should be able to persist its job definitions, so scheduled tasks are not lost if the application restarts.
- **Resource Management:** Use a managed thread pool to execute jobs, preventing resource exhaustion.

**Scope:**

- This is an **in-process** scheduler, meaning it runs within a single JVM/application instance.
- We will not cover distributed scheduling (which requires coordination, consensus, and distributed state management).

---

### **2. Core Components and Class Design**

The design is centered around a main `Scheduler` loop that manages a priority queue of upcoming jobs and a pool of worker threads to execute them.

- **`Job`:** A simple wrapper for a `Runnable` task, containing a unique ID and metadata like priority.
- **`Trigger`:** An interface that determines the next execution time for a job.
    - Implementations: `CronTrigger`, `IntervalTrigger`, `OneTimeTrigger`.
    - Key method: `Instant getNextFireTime(Instant lastFireTime)`.
- **`RetryPolicy`:** A class defining the retry behavior.
    - Attributes: `maxRetries`, `backoffStrategy` (e.g., FIXED, EXPONENTIAL).
    - Key method: `Duration getNextRetryDelay(int currentAttempt)`.
- **`JobDefinition`:** A container that bundles a `Job`, its `Trigger`, and its `RetryPolicy`. This is what the user provides to the scheduler.
- **`ScheduledJob`:** An internal, stateful object that the scheduler uses. It contains the `JobDefinition`, the calculated `nextFireTime`, and the current retry attempt count. This is the object that will be stored in our priority queue.
- **`JobStore`:** An interface for persistence.
    - Implementations: `InMemoryJobStore`, `JdbcJobStore`.
    - Methods: `save(jobDef)`, `loadAll()`, `delete(jobId)`.
- **`Scheduler`:** The core engine. It contains:
    - A `PriorityBlockingQueue<ScheduledJob>` acting as a min-heap, ordered primarily by `nextFireTime` and secondarily by priority.
    - A `ThreadPoolExecutor` (worker pool).
    - A single "scheduler thread" that pulls jobs from the queue and submits them to the worker pool.

---

### **3. Detailed Class Design**

```java
// Job.java
public class Job {
    private final String id;
    private final Runnable task;
    private final int priority;

    // constructor, getters
}

// Trigger.java
public interface Trigger {
    Instant getNextFireTime(Instant lastFireTime);
}

// CronTrigger.java
public class CronTrigger implements Trigger {
    private final String cronExpression;

    // constructor
    public Instant getNextFireTime(Instant lastFireTime) {
        // parse cronExpression and calculate next fire time
    }
}

// IntervalTrigger.java
public class IntervalTrigger implements Trigger {
    private final Duration interval;

    // constructor
    public Instant getNextFireTime(Instant lastFireTime) {
        // calculate next fire time based on interval
    }
}

// OneTimeTrigger.java
public class OneTimeTrigger implements Trigger {
    private final Instant fireTime;

    // constructor
    public Instant getNextFireTime(Instant lastFireTime) {
        return fireTime;
    }
}

// RetryPolicy.java
public class RetryPolicy {
    private final int maxRetries;
    private final BackoffStrategy backoffStrategy;

    // constructor, getters
    public Duration getNextRetryDelay(int currentAttempt) {
        // calculate delay based on strategy
    }
}

// JobDefinition.java
public class JobDefinition {
    private final Job job;
    private final Trigger trigger;
    private final RetryPolicy retryPolicy;

    // constructor, getters
}

// ScheduledJob.java
public class ScheduledJob implements Comparable<ScheduledJob> {
    private final JobDefinition jobDefinition;
    private Instant nextFireTime;
    private int retryAttempt;

    // constructor, getters, compareTo
}

// JobStore.java
public interface JobStore {
    void save(JobDefinition jobDef);
    List<JobDefinition> loadAll();
    void delete(String jobId);
}

// InMemoryJobStore.java
public class InMemoryJobStore implements JobStore {
    private final Map<String, JobDefinition> store = new HashMap<>();

    public void save(JobDefinition jobDef) {
        store.put(jobDef.getJob().getId(), jobDef);
    }
    public List<JobDefinition> loadAll() {
        return new ArrayList<>(store.values());
    }
    public void delete(String jobId) {
        store.remove(jobId);
    }
}

// JdbcJobStore.java
public class JdbcJobStore implements JobStore {
    private final DataSource dataSource;

    // constructor
    public void save(JobDefinition jobDef) {
        // JDBC code to save jobDef
    }
    public List<JobDefinition> loadAll() {
        // JDBC code to load all jobDefs
    }
    public void delete(String jobId) {
        // JDBC code to delete jobDef by jobId
    }
}

// Scheduler.java
public class Scheduler {
    private final PriorityBlockingQueue<ScheduledJob> jobQueue;
    private final ThreadPoolExecutor workerPool;
    private final List<ScheduledJob> scheduledJobs;

    public Scheduler(int poolSize) {
        this.jobQueue = new PriorityBlockingQueue<>();
        this.workerPool = (ThreadPoolExecutor) Executors.newFixedThreadPool(poolSize);
        this.scheduledJobs = new ArrayList<>();
    }

    public void schedule(JobDefinition jobDef) {
        // calculate initial nextFireTime
        ScheduledJob scheduledJob = new ScheduledJob(jobDef, nextFireTime, 0);
        jobQueue.add(scheduledJob);
        scheduledJobs.add(scheduledJob);
    }

    public void start() {
        // start the scheduler thread
    }

    public void stop() {
        // stop the scheduler and worker pool
    }

    private void executeJob(ScheduledJob scheduledJob) {
        // job execution logic, including retry handling
    }
}
```

---

### **4. Sequence Diagram: Scheduling a Job**

```
User -> Scheduler: schedule(jobDef)
Scheduler -> JobQueue: add(scheduledJob)
Scheduler -> WorkerPool: submit(job)
```

---

### **5. Sequence Diagram: Job Execution and Retry**

```
Scheduler -> JobQueue: poll()
JobQueue -> WorkerPool: take(scheduledJob)
WorkerPool -> Job: run()
alt job fails
    Scheduler -> ScheduledJob: incrementRetry()
    alt max retries not reached
        Scheduler -> JobQueue: add(scheduledJob)
    else
        Scheduler -> JobStore: delete(jobId)
    end
end
```

---

### **6. Considerations for Distributed System Extension**

- Introduce a consensus mechanism (e.g., ZooKeeper, Raft) for job coordination.
- Store job definitions and states in a distributed database.
- Ensure exactly-once execution semantics, possibly using unique job tokens.

---

### **7. Potential Enhancements**

- **Dynamic Scaling:** Adjust the pool size of the worker threads based on the system load.
- **Job Priority Inversion Handling:** Implement measures to prevent low-priority jobs from starving high-priority ones.
- **More Triggers:** Add triggers like `DailyTrigger`, `MonthlyTrigger`, or custom cron-like expressions.
- **Web Interface:** A simple UI to monitor and manage scheduled jobs.
- **Alerting:** Notify users/administrators of job failures or retries.

---

### **8. Conclusion**

This document describes a robust cron-like job scheduler's design, focusing on priority-based execution and retry mechanisms. The proposed system is flexible, allowing various job triggers and providing strong guarantees on job execution. With careful consideration of the requirements and a clear design, this scheduler can be a vital component in any Java application needing background task processing.
