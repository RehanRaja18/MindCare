# MINDCARE — MASTER PROJECT CONTEXT & DEVELOPMENT INSTRUCTIONS

## 1. IMPORTANT: READ THIS FIRST

You are working with me on my Final Year Project (FYP), called **MindCare**.

This document contains the current complete vision, architecture, modules, workflows, constraints, and technical direction of the project.

**Treat this document as the shared source of truth for the MindCare project.**

I will create separate conversations with you for different parts of the project, such as:

* MindCare Web — React frontend
* MindCare App — Flutter mobile application
* MindCare IoT — Wearable Band
* MindCare Backend — unified backend/API
* MindCare AI — AI/ML models and AI services

Even though these are separate development conversations, they are all parts of the **same system**.

Therefore:

> **Never design any component as if it exists independently. Always consider how it connects to the complete MindCare ecosystem.**

If I later provide a new requirement, clarification, architectural decision, or feature, treat it as an update to this project context and incorporate it going forward.

Do not silently remove, simplify, replace, or change an existing feature.

If something is ambiguous, technically questionable, unrealistic, unsafe, or contradictory, **tell me clearly and ask for clarification or recommend a better approach rather than silently changing my requirements.**

---

# 2. PROJECT OVERVIEW

## Project Name

**MindCare**

## Core Purpose

MindCare is a technology platform designed to act as a bridge between **patients/users and psychologists**.

The primary goal is to make psychological and mental-health support more accessible and comfortable for people who may hesitate to seek psychological help because of:

* social stigma
* embarrassment
* fear of judgment
* difficulty accessing psychologists
* loneliness
* difficulty continuously monitoring their condition

The system therefore provides a digital ecosystem through which patients can interact with psychologists, receive approved recommendations, monitor relevant health/vital information, journal, receive motivation, participate in communities, and access other support mechanisms.

---

# 3. HIGH-LEVEL SYSTEM ARCHITECTURE

MindCare consists of four major components:

```text
                    ┌─────────────────────────┐
                    │      MindCare AI        │
                    │ AI / ML / Predictions    │
                    │ Recommendations         │
                    │

                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────┐      ┌─────────────────────────┐      ┌──────────────────┐
│ MindCare Flutter │◄────►│   MindCare Backend      │◄────►│  MindCare React  │
│ Mobile App       │      │   Unified Backend/API    │      │   Web Platform   │
│                  │      │                          │      │                  │
│ Patients/Users   │      │ Database                 │      │ Psychologists    │
│                  │      │ Authentication           │      │ Admin            │
│                  │      │ Business Logic           │      │                  │
│                  │      │ Payments                  │      │                  │
│                  │      │ Notifications             │      │                  │
│                  │      │ Wearable Data             │      │                  │
└──────────────────┘      └────────────┬────────────┘      └──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ ESP32 Wearable   │
                              │ MindCare Band    │
                              └──────────────────┘
```

### Important architectural principle

The **mobile app and web application must use the same unified backend**.

The backend should not contain duplicate business logic for mobile and web.

The frontend applications are clients of the backend.

The AI system is another major component/service that interacts with the backend and relevant data.

---

# 4. CURRENT REPOSITORY STRUCTURE

The repository is currently organized as:

```text
MindCare/
│
├── MindCare AI/
│
├── MindCare App/
│
├── MindCare Web/
│
└── MindCare Backend/
```

Purpose of each:

### MindCare AI

Contains the AI/ML work, including:

* dataset preparation
* model training
* anxiety-risk prediction (Low / Medium / High) for psychologist review
* a confident / borderline label on each prediction, so psychologists know which predictions the model is unsure of
* a patient-summary estimate: an estimated severity tier and the matching recommendation bundle from the
  dataset's templates. This is an estimate, not a trained recommendation model (see
  `MindCare AI/reports/recommendation_mapping_investigation.md`)
* inference
* AI services
* model evaluation
* AI-specific experimentation

The emergency/SOS mechanism (§27) and the AI chat assistants (§14) are not part of MindCare AI's
current deliverables.

### MindCare App

Flutter mobile application primarily intended for:

* patients/users
* patient interaction
* journaling
* recommendations
* SOS Button available on all screens
* motivation
* notifications
* community participation
* wearable-related interaction
* appointments/sessions
* payments
* other patient-facing features

### MindCare Web

React web application primarily intended for:

* psychologists
* administrators

The web application provides dashboards and professional management functionality.

### MindCare Backend

The unified backend serving both:

* MindCare Web
* MindCare App

It will contain shared APIs, business logic, authentication, database interaction, payments, notifications, wearable data handling, reports, etc.

---

# 5. USER TYPES / ROLES

The system currently involves several major roles.

## Patient / User

The patient can:

* register/login
* maintain their profile
* interact with psychologists
* request psychologists
* receive approved AI recommendations
* follow exercises
* follow diet plans
* follow sleep schedules
* journal
* Click SOS for emergency use
* use motivation features
* receive notifications
* attend sessions
* use AI chat assistance
* participate in communities
* report inappropriate content
* make payments
* view payment history/invoices
* earn XP and badges
* potentially receive discounts
* interact with the wearable/band
* complete daily challenges if that feature is implemented

---

## Psychologist

The psychologist can:

* register/onboard
* manage their professional profile
* accept or decline patient requests
* manage patients
* maintain patient profiles
* schedule sessions
* amend/accept session schedules
* conduct one-on-one sessions
* use Zoom/Google Meet or similar integrations
* maintain professional notes/journal regarding patients
* monitor patient sensor/vital data
* review AI-generated recommendations
* modify AI recommendations
* approve recommendations before they reach patients
* use AI assistance at a more professional/expert-assistance level
* generate automated patient reports
* review patient history
* review trends and patterns
* interact with relevant patient data

---

## Administrator

The admin has a superior-level view/control of the system.

The admin can manage things such as:

* psychologists
* patients/users
* NGO onboarding
* community creator applications
* moderation/reporting
* platform-level management
* approvals
* other administrative functionality

---

## NGO / Welfare Organization

NGOs can be onboarded through an approval process.

They may participate in emergency assistance and support workflows.

---

## Community Creator / Mentor

Not every user should automatically be allowed to create a community.

A person who wants to create a community must:

1. Apply.
2. Provide their story.
3. Explain how they went through their relevant difficult phase.
4. Provide their motivational story/reason for wanting to help others.
5. Submit the application to the admin.
6. Wait for admin approval.
7. If approved, they can create a community.
8. If declined, they cannot create the community.

This approval mechanism is intentionally part of the platform's safety/moderation design.

---

# 6. USER ONBOARDING & AUTHENTICATION

The system must have a user onboarding/profiling module.

Users should be able to:

* register
* log in
* maintain sessions
* log out
* maintain their profile
* have their relevant activity/data associated with their account

Psychologists have their own onboarding/authentication flow.

The system must distinguish between roles and provide appropriate permissions.

Authentication and authorization should be handled centrally through the unified backend.

---

# 7. PATIENT PROFILING

Psychologists should be able to maintain profiles for their patients.

The psychologist dashboard should allow the psychologist to access relevant information about a specific patient.

Patient information may include:

* profile information
* session history
* recommendations
* adherence/progress
* journal-related information where appropriate
* sensor/vital data
* reports
* relevant activity
* other clinically/relevantly collected information

Do not expose sensitive patient information to unauthorized users.

Role-based access control is important.

---

# 8. PSYCHOLOGIST ↔ PATIENT RELATIONSHIP

Patients can seek/access psychologists through the platform.

The psychologist can:

* accept a patient/client
* decline a patient/client

Once a psychologist accepts a patient, they can manage their relationship through the platform.

The patient may pay for psychological services.

Payment structures may include:

* weekly
* monthly
* other configured periods

The exact business model may evolve later.

---

# 9. APPOINTMENTS & ONE-ON-ONE SESSIONS

MindCare will support psychologist-patient sessions.

The system should allow:

* appointment scheduling
* session scheduling
* accepting/amending mutually agreed times
* appointment/session management
* session details
* session history

For actual video sessions, we may integrate services such as:

* Zoom
* Google Meet
* other suitable video-conferencing APIs

The integration should be designed so the backend can manage the relevant session metadata.

---

# 10. PSYCHOLOGIST NOTES / JOURNAL

During or after sessions, psychologists should be able to maintain professional notes.

This is analogous to how healthcare professionals document observations during assessments.

The psychologist may record:

* observations
* session notes
* relevant information
* assessment-related notes
* progress
* other professional information

These notes are private and must be protected with appropriate access controls.

---

# 11. PATIENT JOURNAL

Patients will also have a journal.

The patient can write down:

* thoughts
* feelings
* experiences
* personal reflections
* other journal entries

The journal should belong to the patient and be appropriately protected.

Do not assume that all journal content should automatically become visible to the psychologist unless we explicitly define such functionality.

---

# 12. AI RECOMMENDATION SYSTEM

This is one of the major features of MindCare.

We have a dataset of approximately **11,000 entries** that we intend to use for training/research.

The AI system is intended to recommend things such as:

* exercises
* diet plans/schedules
* sleep schedules/plans
* other relevant supportive recommendations

### CRITICAL WORKFLOW

The AI must **NOT directly send recommendations to the patient.**

The workflow should be:

```text
Patient Data / Profile
        ↓
      AI Model
        ↓
AI-generated Recommendation
        ↓
Psychologist Dashboard
        ↓
Psychologist Reviews
        ↓
 ┌───────────────┐
 │ Approve       │
 │ OR            │
 │ Modify        │
 └───────────────┘
        ↓
Approved Recommendation
        ↓
Patient App
        ↓
Patient Follows Recommendation
```

The psychologist acts as a human approval layer.

The psychologist should be able to modify an AI recommendation if they believe it is inappropriate or needs adjustment.

---

# 13. AI FEEDBACK / LEARNING LOOP

We want the AI system to improve based on psychologist feedback.

For example:

```text
AI recommends X
       ↓
Psychologist reviews X
       ↓
Psychologist modifies X
       ↓
System records the modification/feedback
       ↓
Future AI development/training can use this feedback
```

The system should consider relevant patient profile information and psychologist feedback.

However, do not blindly implement "continuous self-learning" in production without discussing the technical and safety implications.

The exact mechanism for model retraining, feedback collection, validation, versioning, and deployment must be designed carefully.

---

# 14. AI CHAT ASSISTANT

There will be an AI chat assistant in both the web and mobile applications.

## Patient side

The patient should be able to have basic conversations related to things such as:

* stress
* anxiety
* general supportive information
* basic health-related questions within the system's defined scope

The patient AI should not be presented as a replacement for a psychologist.

---

## Psychologist side

Psychologists will have a more advanced AI assistant intended to assist them professionally.

It can potentially help with:

* organizing information
* summarizing relevant history
* assisting with analysis
* supporting professional workflows
* other appropriate psychologist-assistance tasks

The psychologist remains responsible for professional decisions.

---

# 15. WEARABLE / MINCARE BAND

We are also developing a physical wearable/band.

The current planned hardware direction includes:

**ESP32**

The exact sensors are still to be finalized.

The current primary parameters we want to monitor are:

1. **Breathing rate**
2. **Heart rate**
3. **Motion**

Sweating was previously discussed as a possible parameter, but the current core focus is the three parameters above.

### Important reasoning for motion

Heart rate alone is not sufficient to determine whether a person is experiencing stress/anxiety.

For example:

```text
Heart rate increases
        ↓
Could be anxiety/stress
        OR
Could be physical exercise
```

Therefore, motion data can provide contextual information.

For example:

```text
High heart rate + low movement
        ↓
Potential stress/anxiety signal

High heart rate + high movement
        ↓
Could be physical activity/exercise
```

This is an intended assessment concept, not a claim that these signals alone can medically diagnose anxiety.

---

# 16. WEARABLE DATA TRANSMISSION

The ESP32 should not necessarily maintain continuous communication with the backend.

Instead, we are considering a batching approach.

Example:

```text
ESP32
  ↓
Collect sensor data
  ↓
Store locally
  ↓
Collect approximately 32 packets
OR
Wait approximately 3 minutes
  ↓
Send accumulated data
  ↓
Backend
  ↓
Store/process data
  ↓
Reset/continue collecting
```

The exact:

* packet count
* time interval
* storage mechanism
* communication protocol
* transmission frequency

will be finalized during hardware/backend development.

The purpose is to reduce the need for constant communication and make the wearable system more practical.

---

# 17. WEARABLE DATA ON PSYCHOLOGIST DASHBOARD

The psychologist should be able to select a specific patient and view relevant wearable information.

Potential data includes:

* heart rate
* breathing rate
* motion
* trends
* historical data
* relevant graphs
* patterns

The system should allow the psychologist to monitor how the patient is doing based on the collected data.

---

# 19. AUTOMATED REPORT GENERATION

The psychologist should be able to automatically generate a report for a specific patient.

The report should summarize relevant patient information and trends so that the psychologist does not have to manually inspect every historical record.

The psychologist should be able to choose a time period.

Examples:

* 1 week
* 1 month
* 2 months
* 3 months
* 6 months
* other configurable periods

The report may combine relevant information such as:

* patient history
* heart rate
* breathing rate
* sensor trends
* activity
* progress
* relevant recommendations
* adherence
* other relevant collected data

The psychologist should receive the important information and patterns in a concise form.

The system may provide graphs/trends where useful.

---

# 20. MOTIVATION PANEL / MOTIVATION CORNER

The patient application should contain a motivational section.

It may include:

* motivational quotes
* motivational words/messages
* supportive content
* notifications/reminders

The goal is to help users remain motivated and engaged and reduce feelings of being overwhelmed, stressed, or demotivated.

The system can send motivational notifications periodically.

### Religious content

Religious content was discussed as a further extension.

For example, for users who choose it to be religious as well, there will be:

* Quran/Suras
* Hadith
* other religious material

---

# 21. COMMUNITY SUPPORT

MindCare will have a community module.

The motivation behind this is that people experiencing stress/anxiety can become lonely and sometimes do not necessarily want formal psychological intervention at every moment.

Sometimes they may simply want:

* someone to listen
* companionship
* motivation
* social interaction
* someone who understands their experience

The community system is intended to provide a controlled environment for this.

---

# 22. COMMUNITY CREATION SECURITY MODEL

Not every user should automatically be allowed to create a community.

A user who wants to create a community must submit an application.

The application should include their:

* story
* experience
* journey through the relevant difficult phase
* motivation for helping others

The application goes to the administrator.

```text
User
 ↓
Apply to create community
 ↓
Submit story
 ↓
Admin reviews
 ↓
 ┌───────────────┐
 │ APPROVE       │
 │ OR            │
 │ DECLINE       │
 └───────────────┘
 ↓
If approved → community creation privileges
```

This is intentionally designed as a safety/security/moderation layer.

---

# 23. COMMUNITY MODERATION

Users should be able to report inappropriate content.

Potential reportable content includes:

* messages
* images
* videos
* other community content

This creates another safety layer.

The two main safeguards are:

### Layer 1 — Community creator approval

A person must be reviewed before being allowed to create a community.

### Layer 2 — Content reporting

Users can report inappropriate content after communities exist.

The admin/moderation system can then review reported content.

Do not remove either safeguard.

---

# 24. COMMUNITY FEATURES

Approved community creators may be able to:

* create communities
* post content
* interact with members
* provide motivational support

Members may be able to:

* join communities
* post
* receive motivation
* communicate
* report content

We have also discussed possible categorized support/volunteer interactions.

For example, people may volunteer for activities such as:

* going for a walk/hike
* having coffee
* meeting socially
* providing companionship

The user receiving the service may pay for their own + the service provider's expenses, such as:

* dinner
* coffee
* other outing expenses

After an interaction/outing, the participant may rate their experience.

Ratings may contribute to the person's profile/reputation/categorization.

This feature should be treated carefully from a safety and moderation perspective.

---

# 25. PAYMENT SYSTEM

MindCare will have a payment module.

The current payment gateway under consideration is:

**Stripe**

The payment system should support relevant payment functionality for patients and psychologists.

We also want:

* payment history
* transaction records
* invoices
* previous payment information
* wallet/balance concepts if implemented
* relevant payment records

The exact payment architecture will be finalized during backend development.

---

# 26. NGO ONBOARDING

MindCare will support NGO onboarding.

The workflow is:

```text
NGO
 ↓
Submit onboarding request
 ↓
Admin reviews
 ↓
Approve / Reject
 ↓
If approved → NGO onboarded
```

NGOs may be involved in emergency assistance/support.

---

# 27. EMERGENCY ASSISTANCE

There should be an emergency-support mechanism.

A patient may be able to request emergency assistance through the app.

We have also discussed a wearable-triggered emergency concept.

If wearable data suggests that the user's condition is becoming concerning, the system may potentially trigger an emergency workflow.

If the user has provided trusted/close-relative contact information, relevant relatives may be contacted.

Relevant NGOs, welfare organizations, emergency services, or other configured organizations may potentially be alerted according to the region.

The purpose is to enable assistance as quickly as possible.

The exact emergency detection thresholds, escalation rules, responsible parties, and notification mechanisms must be designed carefully and should not be invented without confirmation.

---

# 28. ENGAGEMENT & REWARD SYSTEM

MindCare will have a gamified engagement/reward system.

The purpose is to encourage users to consistently follow healthy/supportive routines.

For example, users may receive XP for:

* completing recommended exercises
* following breathing exercises
* following anti-stress techniques
* completing relevant activities
* maintaining engagement
* doing daily game challenges if that is implemented at the end
* other approved behaviors

XP can lead to:

```text
XP
 ↓
Badges / Levels
 ↓
Rewards / Benefits
```

One planned benefit is possible discounts/concessions.

For example, badges could potentially provide:

* discounts on psychologist fees
* other platform benefits

Some modules may eventually be premium.

However:

> **The exact premium model has NOT been finalized.**

Do not assume which modules are premium unless I explicitly decide it.

---

# 29. DAILY CHALLENGES — POSSIBLE FINAL FEATURE

At the very end of development, **if time permits**, we may introduce daily challenges.

This is NOT currently a core requirement.

The idea came from discussions with psychologists.

We originally considered adding games to help users:

* engage
* release stress
* distract themselves
* have fun

However, psychologists raised an important concern:

> We do not want users to significantly increase their screen time.

Therefore, if daily challenges are implemented, they should be designed to:

* be short
* require minimal screen time
* encourage engagement
* provide a small sense of achievement
* potentially involve simple games/challenges
* avoid turning MindCare into a high-screen-time entertainment application

Example concept:

```text
Daily Challenge
      ↓
1–3 attempts
      ↓
Score / completion
      ↓
Reward / XP
```

Again, this feature should only be implemented if the core system is complete and time remains.

---

# 30. NOT A REPLACEMENT FOR PROFESSIONAL CARE

MindCare is intended to support the relationship between patients and psychologists.

AI, wearable sensors, reports, communities, and recommendations should not automatically be treated as definitive medical diagnoses.

The psychologist remains an important human decision-maker, particularly for AI-generated recommendations.

The system should be designed with appropriate privacy, security, safety, and access-control considerations, always taking in consideration that system is in compliance with HIPPA policies.

---

# 31. CORE DATA FLOW

A simplified example of the complete system:

```text
                    PATIENT
                       │
                       ▼
                Flutter Mobile App
                       │
                       ▼
                Unified Backend
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    Database         AI System      Wearable
                       │              │
                       │              ▼
                       │           ESP32
                       │              │
                       │        Sensor Data
                       │              │
                       └──────► Backend
                                      │
                                      ▼
                              Psychologist Web
                                      │
                                      ▼
                           Review / Analyze / Approve
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                  AI Recommendation          Patient Data
                         │
                         ▼
                   Psychologist
                         │
                  Approve / Modify
                         │
                         ▼
                      Patient
```

---

# 32. WEB APPLICATION

The web application is being built in **React**.

It is primarily intended for:

* psychologists
* administrators

The web application will include appropriate dashboards.

Psychologist functionality should include things such as:

* dashboard
* patients
* patient profiles
* appointments
* sessions
* patient notes
* AI recommendations
* AI assistant
* sensor monitoring
* reports
* relevant payment information
* other professional functionality

Admin functionality should include things such as:

* user management
* psychologist management
* NGO onboarding/approval
* community creator approval
* moderation/reporting
* platform management
* other administrative functionality

---

# 33. MOBILE APPLICATION

The mobile application will be built using **Flutter**.

It is primarily intended for patients/users.

It should eventually contain relevant patient-facing features such as:

* authentication
* profile
* psychologist interaction
* appointments
* sessions
* AI-approved recommendations
* exercises
* diet plans
* sleep schedules
* patient journal
* AI chat
* motivation panel
* notifications
* wearable information
* payments
* payment history
* invoices
* community
* reporting
* rewards/badges
* daily challenges if implemented
* emergency assistance

---

# 34. UNIFIED BACKEND

The backend is shared between the React web application and Flutter mobile application.

It should provide centralized functionality for:

* authentication
* authorization
* users
* psychologists
* patient profiles
* appointments
* sessions
* video meeting metadata
* patient notes
* journals
* AI recommendations
* AI feedback
* AI chat integration
* wearable data
* sensor processing/storage
* reports
* payments
* invoices
* notifications
* communities
* moderation
* NGO onboarding
* rewards
* emergency workflows
* other shared business logic

The exact backend technology stack can be selected/developed separately.

---

# 35. AI SYSTEM

The AI folder/system should be treated as an independent AI component that integrates with the backend.

Potential AI responsibilities include:

1. Recommendation model
2. Recommendation processing
3. AI feedback loop
4. Patient-side AI assistant
5. Psychologist-side AI assistant
6. Other ML functionality we explicitly add later

The AI system should communicate with the backend through a clearly defined interface/API rather than creating tightly coupled dependencies.

---

# 36. DATABASE / DATA OWNERSHIP PRINCIPLE

The backend should be the central authority for application data.

The React frontend and Flutter frontend should not independently maintain separate copies of the application's authoritative business data.

The backend should manage:

```text
Authentication
       ↓
Authorization
       ↓
Business Logic
       ↓
Database
       ↓
APIs
       ↓
Web / Mobile / AI / Wearable
```

---

# 37. SECURITY & PRIVACY

MindCare handles sensitive personal and potentially health-related information.

Therefore, security must be treated as a first-class requirement.

Important considerations include:

* authentication
* authorization
* role-based access control
* secure API design
* secure password handling
* secure session/token handling
* patient data protection
* psychologist-only access to appropriate patient data
* secure journal handling
* secure payment handling
* secure wearable data
* secure AI data handling
* community moderation
* auditability where appropriate

Do not expose private patient information merely because it is technically available in the backend.

---

# 38. DEVELOPMENT PHILOSOPHY

When helping me develop MindCare:

### DO:

* Think like a senior software architect.
* Think about the complete system.
* Consider scalability.
* Consider security.
* Consider maintainability.
* Consider database relationships.
* Consider API contracts.
* Consider HIPPA compliance
* Consider rights and privacy.
* Consider frontend/backend boundaries.
* Consider AI/backend integration.
* Explain architectural decisions.
* Point out problems before they become expensive.
* Preserve existing functionality.
* Ask questions when requirements are ambiguous.
* Give practical implementation steps.
* Prefer clean, maintainable code over unnecessarily complicated code.
* Keep the FYP's realistic scope in mind.

### DO NOT:

* Remove features without telling me.
* Replace requirements with your own assumptions.
* Pretend a feature is easy when it is technically complex.
* Build isolated functionality that conflicts with the rest of MindCare.
* Assume AI output is automatically correct.
* Treat AI as a replacement for psychologists.
* Introduce unnecessary technologies just because they are popular.
* Over-engineer simple functionality.
* Change the architecture without explaining why.

---

# 39. IMPORTANT RULE FOR SEPARATE CLAUDE CHATS

This prompt is the **shared context**.

I may now create separate conversations such as:

### CHAT 1 — MINDCARE WEB

You should focus primarily on:

```text
React
UI/UX
Components
Pages
Dashboards
Routing
Frontend state
API integration
Psychologist interface
Admin interface
```

But remember the unified backend and complete MindCare architecture.

---

### CHAT 2 — MINDCARE APP

Focus primarily on:

```text
Flutter
Mobile UI
Patient experience
Navigation
State management
API integration
Notifications
Wearable integration
Patient features
```

But remember the unified backend and complete MindCare architecture.

---

### CHAT 3 — MINDCARE BACKEND

Focus primarily on:

```text
Backend architecture
API design
Database
Authentication
Authorization
Business logic
Payments
Appointments
Sessions
Wearables
Notifications
Reports
Communities
Admin functionality
AI integration
```

But remember that both the Flutter app and React web application depend on this backend.

---

### CHAT 4 — MINDCARE AI

Focus primarily on:

```text
Dataset
Data preprocessing
Feature engineering
Model selection
Training
Evaluation
Anxiety-risk prediction
Confident/borderline prediction label
Patient-summary estimate
Recommendation system
Inference
AI/backend integration
```

---

### CHAT 5 — MINDCARE IoT

You should focus primarily on:

```text
ESP32
Microcontrollers
Wearable hardware
Sensors
Heart-rate monitoring
Breathing-rate monitoring
Motion/activity monitoring
Sensor data acquisition
Sensor calibration
Signal processing
Embedded programming
ESP32 firmware
Bluetooth / Wi-Fi communication
Local data storage
Data batching
Packet design
Power optimization
Backend communication
IoT security
Sensor data transmission
Wearable-to-backend integration
Wearable-to-mobile integration if required
Testing and debugging
```

But remember that AI recommendations go through psychologist approval before reaching patients.

---

# 40. WHEN I ASK YOU TO CODE

Before implementing a significant feature:

1. Understand which component it belongs to.
2. Understand its relationship with the rest of MindCare.
3. Identify required backend APIs/data structures.
4. Identify dependencies on other components.
5. Tell me about important architectural implications.
6. Then implement it.

Do not blindly write code without understanding the system.

If I ask for code for one component but the feature requires another component, clearly tell me what the dependency is.

---

# 41. WHEN REQUIREMENTS CHANGE

MindCare is an evolving FYP.

I may later:

* add features
* remove features
* modify workflows
* change technologies
* change database design
* change UI
* change AI approach
* change business rules

When I provide an update:

1. Treat it as a project update.
2. Preserve everything that is not explicitly changed.
3. Identify conflicts with previous requirements.
4. Ask me if the conflict is ambiguous.
5. Do not silently overwrite important architectural decisions.

---

# 42. FINAL INSTRUCTION

You are not merely a code generator for this project.

Act as my:

* Senior Software Architect
* Full-Stack Engineer
* AI/ML Engineer
* System Designer
* Technical Advisor
* Code Reviewer
* Development Mentor
* Electrical Engineer

Your responsibility is to help me turn the above MindCare concept into a **realistic, maintainable, secure, integrated FYP system**.

Always keep the complete ecosystem in mind. Always make the system comply with HIPPA policies.

If I am making a technically bad decision, **tell me directly and explain why**.

If there is a better architecture, explain it before changing anything.

If something is unclear, ask me instead of guessing.

Most importantly:

> **Do not forget any of the features, workflows, roles, architectural decisions, or constraints described above.**

This is the current master context for **MindCare**.
