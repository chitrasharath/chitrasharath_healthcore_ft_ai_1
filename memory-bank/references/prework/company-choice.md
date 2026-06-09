## Company Choice

    I chose HealthCore.  This is because LLMs have become very good at providing health advice based on symptoms. LLMs will be a great resource for a medical practice. There are several AI agents that can be built for HealthCore.

## Departments with interesting challenges

    The two departments that have the most interesting challenges are Clinical operations and Patient Experience and Access.  I am especially interested in solving for the 22% no-show rate.  Improving this metric will help both departments.

## Automation that I want to build

    I would like to build the following automation:

### No-Show Prevention Agent

        Predicts no-show risk per patient and automates reminders, rebooking nudges, and outreach priority queues.


## My AI Agent Idea

### No-Show Prevention Agent

        There are 5 parts:
        1.  Risk scoring model - score patient as a high and low risk for cancellation 
        2.  Intervention selection - based on risk score what are interventions that need to be put into place
        3.  Workflow automation 
        4.  Human in the loop console
        5.  Waitlist Intelligence

        **Data required:**
        1.  Appointment details: date/time, clinic, provider, specialty, visit type, lead time.
        2.  Patient behavior: prior no-shows, late cancellations, confirmation history.
        3.  Access factors: distance/travel time, day/time preference, language.
        4.  Operational context: weather, holiday, wait time, booking channel (phone/manual/online).
        5.  Outcome label: attended / no-show / cancelled with notice.

        **Risk model:**
        1.  Start with gradient boosting (XGBoost/LightGBM) on tabular features.
        2.  Output a calibrated probability of no-show (not just yes/no).
        3.  Set risk bands:
                Low: <20%
                Medium: 20-45%
                High: >45%
        4.  Keep explainability (top contributing factors per prediction).

        **Intervention Policy:**
        1.  Low risk: standard reminder (e.g. 48h).
        2.  Medium risk: reminder + one-click confirm/reschedule link.
        3.  High risk: early outreach, reschedule option, waitlist backfill trigger, optional human call.
        4.  Make outreach channel and timing adaptive (language, past response behavior, local time window).

        **Workflow Automation:**
        1.  Score all appointments
        2.  Write actions into a task queue for patient access team
        3.  Send reminders automatically where allowed
        4.  If no confirmation by cutoff, escalate and offer easy rebooking
        5.  If cancellation/no response, notify waitlist fill service

        **Human in the loop console:**
        1.  Queue view: “high-risk appointments for tomorrow”.
        2.  Suggested script for outreach (multilingual).
        3.  Action buttons: confirmed, rescheduled, unreachable, wrong number.
        4.  Feedback captured to retrain model and policy.

        **Waitlist intelligence:**
        1.  Maintain ranked waitlist by specialty, geography, and time preference.
        2.  When high-risk slot opens, auto-offer to best candidate.
        3.  Track fill-time and acceptance rate as core ROI metrics.

